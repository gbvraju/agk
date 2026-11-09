"""The evidence pack's form, its release test, its offline check and `make` from git (SPEC-0052).

    python3 scripts/agk/release_pack.py check <out>/<tag>
    python3 scripts/agk/release_pack.py make --tag <tag> --out DIR [--api-dir DIR]
        [--repo OWNER/REPO]

A pack is one folder named by a release tag with exactly six files: the five parts `tests.json`,
`scans.json`, `coverage.json`, `bom.json`, `decisions.json` and the index `pack.json` (rule 2).
`check` reads the folder and the repository's git only, with no network call, and prints `ok pack`,
or one `FAIL pack: <part> <reason>` line per problem and exits 1, naming the part and never a value
(rule 10); a digest line is left out only when a form line already explains it. A required check
`failure` or `unknown`, or a scan `failed` or `unknown`, is one `warn pack:` line and does not fail:
the pack records the release, it does not judge it.

The release test (rule 4) is `check_tag.failure` on the tagged commit, in a throwaway clone that
shares the repository's objects, so the work tree, refs and worktree list stay as they are. A tag
that fails it, or that is not in the repository, is one `refused:` line. A repository without
`kit/manifest.json` and `check_tag.py` at the tag has no release test yet and is refused naming the
path class. `check_tag.py` is kit-only and this script is installed, so it is imported only after
those files are found.

`make` (build (c), rules 3, 8 and 9) applies the release test and the folder refusals, then writes
`bom.json` and `decisions.json` to `<out>/<tag>/` with no network: it reads the tagged commit with
local `git`, never checks it out over the work tree, posts nothing and changes no file of the
repository. Build (d) adds `tests.json` and `scans.json` (rules 5 and 6), read with
`gh api --method GET` only, or from saved responses with `--api-dir` as `scorecard.py` takes them:
what cannot be read is `unknown`, never a pass. `coverage.json`, the fields of `decisions.json` read
from GitHub and the index are still to come; until then `check` fails such a folder, naming them.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard
import metrics
import scorecard
from common import (
    REQUIREMENTS,
    CheckError,
    block_source,
    git,
    load_config,
    parse_requirements,
    repo_root,
    run,
    show,
)

NAME = "pack"
USAGE = (
    "usage: release_pack.py check <out>/<tag> | "
    "make --tag <tag> --out DIR [--api-dir DIR] [--repo OWNER/REPO]"
)
INDEX = "pack.json"
UNKNOWN = "unknown"
NO_RELEASE_TEST = "refused: this repository has no release test (path class kit/)"
NOT_RELEASE = "refused: the tag is not a release ({})"
FIELD = "has a missing or extra field"
SCHEMA = "has a schema other than 1"
RELEASE_FILES = ("kit/manifest.json", "scripts/agk/check_tag.py")
NO_FILE = "refused: a file the bill names cannot be read (path class {})"
IN_REPO = "refused: the folder is inside the repository (path class <out>)"
EXISTS = "refused: the folder exists already (path class <out>/<tag>)"
NO_FOLDER = "refused: the folder cannot be written (path class <out>)"
GOVERNANCE = ".github/workflows/governance.yml"
ABSENT = "none"  # a requirement's status where the requirement does not exist (Q-820-3)
RELEASE_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
# scorecard.PIN and scorecard.EXACT with the groups the bill needs too (a test binds them).
ACTION = re.compile(
    r"^\s*(?:-\s+)?uses:\s*([\w.-]+/[\w.-]+)(?:/\S*)?@([0-9a-f]{40})\s+#\s*(\S+)", re.MULTILINE
)
PINNED = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*==(?!=)\s*([^\s;,]+)")
SCANNER = re.compile(r"^\s*GITLEAKS_VERSION:\s*(\S+)", re.MULTILINE)
SCAN_CHECK, SECRET_STEP = "governance", "Secret scan"  # the job and step that run the secret scan
# SPEC-0052 rule 1's measurement: the dependency scanners no file configures today.
DEPENDENCY = re.compile(r"(?<![\w-])(pip-audit|osv-scanner|dependency-review|trivy|grype)(?![\w-])")
RUN_ID = re.compile(r"/actions/runs/(\d+)(?:/|$)")
COUNTS = {
    word: re.compile(rf"(?<![\w.])(\d+) {word}\b") for word in ("passed", "failed", "skipped")
}
CONCLUSION = re.compile(r"[a-z_]{1,32}")  # a conclusion GitHub gives; anything else is unknown
OUTCOME = {"success": "passed", "failure": "failed", "skipped": "not run"}
# Each part's fields beside `schema`: None is one value, a type a list of it, a tuple a list of
# objects with exactly those fields.
FORMS: dict[str, dict[str, Any]] = {
    "tests.json": {"checks": ("name", "conclusion", "passed", "failed", "skipped")},
    "scans.json": {"scans": ("kind", "scanner", "version", "outcome")},
    "coverage.json": {"covered": None, "date": None},
    "bom.json": {
        "kit_version": None,
        "files": ("path", "sha256"),
        "tools": ("name", "pin"),
        "actions": ("name", "tag", "sha"),
    },
    "decisions.json": {
        "adrs": int,
        "requirements": ("id", "from", "to"),
        "failure_issues": ("number", "state"),
        "scorecard_week": ("metric", "value"),
        "skipped_tags": str,
    },
}
INDEX_FIELDS = {"schema", "tag", "commit", "date", "parts"}
WARN = {"tests.json": ("checks", "name", "conclusion", ("failure", UNKNOWN))}
WARN["scans.json"] = ("scans", "kind", "outcome", ("failed", UNKNOWN))


def is_one(value: object) -> bool:
    return type(value) is int and value == 1


def scalar(value: object) -> bool:
    """One value of a part: a number, or printable text (so that no value can forge a line)."""
    if isinstance(value, str):
        return value.isprintable()
    return type(value) in (int, float)


def shaped(value: object, form: Any) -> bool:
    if form is None:
        return scalar(value)
    if not isinstance(value, list):
        return False
    if isinstance(form, type):
        return all(type(item) is form and scalar(item) for item in value)
    return all(
        isinstance(item, dict) and set(item) == set(form) and all(map(scalar, item.values()))
        for item in value
    )


def form_problems(name: str, data: object) -> list[str]:
    """Why a part is not of its form, one entry per problem, naming no field or value."""
    if not isinstance(data, dict):
        return ["is not JSON of its form"]
    form = FORMS[name]
    found = [FIELD] * len(set(data) ^ {"schema", *form})
    if "schema" in data and not is_one(data["schema"]):
        found.append(SCHEMA)
    for key, shape in form.items():
        if key not in data or (key == "scorecard_week" and data[key] == UNKNOWN):
            continue
        if not shaped(data[key], shape):
            found.append("has a field that is not of its form")
    return found


def read(path: Path) -> tuple[bytes | None, object, str | None]:
    """(bytes, parsed JSON, problem) of one file of the folder; a link is never followed."""
    if path.is_symlink():
        return None, None, "is not a file of the folder"
    if not path.is_file():
        return None, None, "is missing"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, None, "cannot be read"
    try:
        return raw, json.loads(raw.decode("utf-8")), None
    except (UnicodeDecodeError, ValueError, RecursionError):
        return raw, None, "is not JSON"


def guard_problems(raw: bytes | None) -> list[str]:
    """The guard's line for bytes that could be read, whatever their form."""
    if raw is None or not guard.scan_text(raw.decode("utf-8", errors="replace")):
        return []
    return ["holds data the guard refuses"]


def index_problems(data: object, tag: str, commit: str) -> list[str]:
    """Why the index is not of its form, one entry per problem."""
    if not isinstance(data, dict):
        return [FIELD]
    found = [FIELD] * len(set(data) ^ INDEX_FIELDS)
    if "schema" in data and not is_one(data["schema"]):
        found.append(SCHEMA)
    if "tag" in data and data["tag"] != tag:
        found.append("names another tag")
    if "commit" in data and data["commit"] != commit:
        found.append("names another commit")
    if "parts" in data and not digests_of(data):
        found.append("does not list the five parts")
    return found


def digests_of(index: object) -> dict[str, object]:
    """The index's digests, when it lists exactly the five parts."""
    parts = index.get("parts") if isinstance(index, dict) else None
    return parts if isinstance(parts, dict) and set(parts) == set(FORMS) else {}


def part_problems(path: Path, name: str, digests: dict[str, object]) -> tuple[object, list[str]]:
    """(parsed JSON, problems) of one part; a form line already explains a digest that differs."""
    raw, data, problem = read(path)
    found = [problem] if problem else form_problems(name, data)
    if raw is not None and not found and digests:
        if hashlib.sha256(raw).hexdigest() != digests.get(name):
            found.append("does not match its digest in the index")
    return data, found + guard_problems(raw)


def warnings(name: str, data: object) -> list[str]:
    """The `warn pack:` lines of one good part; the pack records a result, it does not judge it."""
    if name not in WARN or not isinstance(data, dict):
        return []
    field, who, what, bad = WARN[name]
    return [f"warn pack: {name} {e[who]} {e[what]}" for e in data[field] if e[what] in bad]


def check_folder(pack: Path, tag: str, commit: str) -> list[str]:
    """The `warn pack:` and `FAIL pack:` lines of the folder, in the order of its files."""
    six = {*FORMS, INDEX}
    stray = "FAIL pack: folder holds a file that is not one of the six"
    lines = [stray for item in pack.iterdir() if item.name not in six]
    raw, index, problem = read(pack / INDEX)
    found = [problem] if problem else index_problems(index, tag, commit)
    lines += [f"FAIL pack: {INDEX} {reason}" for reason in found + guard_problems(raw)]
    digests = digests_of(index)
    for name in FORMS:
        data, found = part_problems(pack / name, name, digests)
        lines += [f"FAIL pack: {name} {reason}" for reason in found] or warnings(name, data)
    return lines


def release_refusal(root: Path, tag: str, commit: str) -> str | None:
    """The one `refused:` line of rule 4 for the tagged commit, or None when it is a release."""
    if not commit:
        return NOT_RELEASE.format("the tag is not in this repository")
    if any(show(root, commit, rel) is None for rel in RELEASE_FILES):
        return NO_RELEASE_TEST
    try:
        check_tag = importlib.import_module("check_tag")
    except ImportError:
        return NO_RELEASE_TEST
    with tempfile.TemporaryDirectory(prefix="agk-release-pack-") as place:
        tree = Path(place) / "tree"
        git(root, "clone", "-q", "--shared", "--no-checkout", "--", ".", str(tree))
        git(tree, "checkout", "-q", "--detach", commit)
        try:
            found = check_tag.failure(tree, tag)
        except (CheckError, OSError, ValueError):
            found = "the tag's files cannot be read"
    return NOT_RELEASE.format(found) if found else None


class Refused(Exception):
    """One `refused:` line, and no pack."""


def blob(root: Path, commit: str, rel: str, where: str) -> bytes:
    """A file's bytes at the commit, by `git show`; refused naming WHERE, its path class."""
    kit_hashes = importlib.import_module("kit_hashes")  # kit-only, and found by the release test
    try:
        return kit_hashes.git_out(root, "show", f"{commit}:{rel}")
    except CheckError:
        raise Refused(NO_FILE.format(where)) from None


def text_at(root: Path, commit: str, rel: str, where: str) -> str:
    return blob(root, commit, rel, where).decode("utf-8", "replace")


def installed(manifest: dict) -> list[str]:
    """The repository's files that an installer writes from, as `kit_hashes.snapshot_of` hashes."""
    adopt = manifest.get("adopt") or {}
    rendered = set(manifest.get("rendered") or [])
    paths = {*manifest.get("verbatim", []), *manifest.get("experimental", [])}
    paths |= {*manifest.get("templates", {}).values(), *(adopt.get("templates") or {}).values()}
    paths |= {block_source(manifest, rel) for rel in set(adopt.get("blocks") or {}) - rendered}
    return sorted(paths)


def python_tools(text: str) -> set[tuple[str, str]]:
    """(name, pin) of the `==` pins of `pyproject.toml`, from the groups `python_pins` reads."""
    try:
        data = tomllib.loads(text)
    except ValueError:
        raise Refused(NO_FILE.format("pyproject.toml")) from None
    found = data.get("project")
    project: dict = found if isinstance(found, dict) else {}
    groups = [project.get("dependencies")]
    for table in (project.get("optional-dependencies"), data.get("dependency-groups")):
        groups += list(table.values()) if isinstance(table, dict) else []
    items = [i for g in groups if isinstance(g, list) for i in g if isinstance(i, str)]
    return {(m[1], m[2]) for i in items if (m := PINNED.match(i))}


def tools_at(root: Path, commit: str) -> list[dict[str, str]]:
    """The pinned tools: the CI tools, the `==` pins of `pyproject.toml`, the pinned scanner."""
    lines = text_at(root, commit, "config/ci-tools.txt", "config/").splitlines()
    found = {(m[1], m[2]) for line in lines if (m := PINNED.match(line))}
    found |= python_tools(text_at(root, commit, "pyproject.toml", "pyproject.toml"))
    found |= {("gitleaks", pin) for pin in SCANNER.findall(text_or_empty(root, commit, GOVERNANCE))}
    return [{"name": name, "pin": pin} for name, pin in sorted(found)]


def text_or_empty(root: Path, commit: str, rel: str) -> str:
    """A file that may be absent at the commit; its absence is no refusal."""
    try:
        return text_at(root, commit, rel, rel)
    except Refused:
        return ""


def actions_at(root: Path, commit: str) -> list[dict[str, str]]:
    """Each SHA-pinned action of the workflows, once, as `scorecard.action_pins` reads them."""
    found = {match for text in workflow_texts(root, commit) for match in ACTION.findall(text)}
    return [{"name": n, "tag": tag, "sha": sha} for n, sha, tag in sorted(found)]


def bill(root: Path, commit: str) -> dict[str, Any]:
    """`bom.json` (rule 8), every value read at the tagged commit."""
    try:
        manifest = json.loads(text_at(root, commit, "kit/manifest.json", "kit/"))
        files = [
            {"path": rel, "sha256": hashlib.sha256(blob(root, commit, rel, "kit/")).hexdigest()}
            for rel in installed(manifest)
        ]
        version = manifest["kit_version"]
    except (ValueError, TypeError, KeyError, AttributeError):
        raise Refused(NO_FILE.format("kit/")) from None
    return {
        "schema": 1,
        "kit_version": version,
        "files": files,
        "tools": tools_at(root, commit),
        "actions": actions_at(root, commit),
    }


def adr_statuses(root: Path, rev: str) -> dict[int, str]:
    """The first `- Status:` of each ADR at the commit, by number."""
    found: dict[int, str] = {}
    listing = git(root, "grep", "-E", "^- Status:", rev, "--", "docs/adr/", check=False)
    for line in listing.splitlines():
        path, _, text = line[len(rev) + 1 :].partition(":")
        number = re.match(r"docs/adr/(\d+)-[^/]*\.md$", path)
        if number:
            found.setdefault(int(number.group(1)), text.removeprefix("- Status:").strip())
    return found


def requirement_statuses(root: Path, rev: str) -> dict[str, str | None]:
    text = text_or_empty(root, rev, REQUIREMENTS)
    return {r["id"]: r["status"] for r in parse_requirements(text)}


def version_of(tag: str) -> tuple[int, ...] | None:
    found = RELEASE_TAG.fullmatch(tag)
    return tuple(map(int, found.groups())) if found else None


def commit_of(root: Path, tag: str) -> str:
    ref = f"refs/tags/{tag}^{{commit}}"
    return git(root, "rev-parse", "-q", "--verify", ref, check=False).strip()


def previous_release(root: Path, tag: str, commit: str) -> tuple[str, list[str]]:
    """(the commit of the highest lower release or else the first commit, the tags skipped)."""
    below = version_of(tag) or ()
    tags = ((version_of(name), name) for name in git(root, "tag", "--list").split())
    skipped: list[str] = []
    for _, name in sorted(((v, t) for v, t in tags if v and v < below), reverse=True):
        found = commit_of(root, name)
        if release_refusal(root, name, found) is None:
            return found, skipped
        skipped.append(name)
    return git(root, "rev-list", "--max-parents=0", commit).split()[-1], skipped


def decisions(root: Path, tag: str, commit: str) -> dict[str, Any]:
    """`decisions.json` (rule 9) without the fields read from GitHub, which are build (d)'s."""
    before, skipped = previous_release(root, tag, commit)
    old = adr_statuses(root, before)
    new = adr_statuses(root, commit)
    adrs = [n for n in sorted(new) if new[n] == "Accepted" != old.get(n)]
    was, now = requirement_statuses(root, before), requirement_statuses(root, commit)
    changed = [
        {"id": rid, "from": was.get(rid) or ABSENT, "to": now.get(rid) or ABSENT}
        for rid in sorted({*was, *now})
        if was.get(rid) != now.get(rid)
    ]
    return {"schema": 1, "adrs": adrs, "requirements": changed, "skipped_tags": skipped}


class Live(scorecard.Live):
    """The scorecard's GET-only reader; a machine without `gh` reads nothing, so `unknown`."""

    def raw(self, endpoint: str) -> str | None:
        try:
            return super().raw(endpoint)
        except OSError:
            return None


def as_int(value: object) -> int:
    return value if type(value) is int else 0


def check_runs(src: Any, commit: str) -> list[dict]:
    data = src.get("check-runs", f"repos/{{repo}}/commits/{commit}/check-runs?per_page=100")
    runs = data.get("check_runs") if isinstance(data, dict) else None
    return [r for r in runs if isinstance(r, dict)] if isinstance(runs, list) else []


def latest_run(runs: list[dict], name: str) -> dict | None:
    named = [r for r in runs if r.get("name") == name]
    return max(named, key=lambda r: as_int(r.get("id")), default=None)


def required_contexts(data: Any) -> list[str] | None:
    """The required checks of the branch's rules, or None when the response is not of that form."""
    try:
        names = [
            entry["context"]
            for rule in data
            if rule["type"] == "required_status_checks"
            for entry in rule["parameters"]["required_status_checks"]
        ]
    except (TypeError, KeyError):
        return None
    return (
        sorted(set(names)) if all(isinstance(n, str) and n.isprintable() for n in names) else None
    )


def check_entry(name: str, run: dict | None) -> dict[str, Any]:
    """One required check: its name, its conclusion and the counts its run's output states."""
    found = (run or {}).get("conclusion")
    usable = isinstance(found, str) and CONCLUSION.fullmatch(found)
    output = (run or {}).get("output")
    fields = output if isinstance(output, dict) else {}
    text = " ".join(str(fields.get(key) or "") for key in ("title", "summary", "text"))
    entry: dict[str, Any] = {"name": name, "conclusion": found if usable else UNKNOWN}
    for word, pattern in COUNTS.items():
        stated = {int(number) for number in pattern.findall(text)}
        entry[word] = stated.pop() if len(stated) == 1 else UNKNOWN
    return entry


def tests_part(src: Any, branch: str, runs: list[dict]) -> dict[str, Any]:
    """`tests.json` (rule 5); rules that cannot be read are one `unknown` entry, never no entry."""
    rules = src.get("rules-branch", f"repos/{{repo}}/rules/branches/{branch}")
    names = required_contexts(rules)
    return {
        "schema": 1,
        "checks": [
            check_entry(n, latest_run(runs, n)) for n in ([UNKNOWN] if names is None else names)
        ],
    }


def step_outcome(src: Any, runs: list[dict]) -> str:
    """The secret scan's outcome: its step in the newest attempt of the run on the tagged commit."""
    run = latest_run(runs, SCAN_CHECK) or {}
    found = RUN_ID.search(str(run.get("details_url") or ""))
    jobs = metrics.jobs_of(src, found[1]) if found else None
    if jobs is None:
        return UNKNOWN
    newest = sorted(jobs, key=lambda job: as_int(job.get("run_attempt")))
    steps = [
        step
        for job in newest
        if isinstance(job.get("steps"), list)
        for step in job["steps"]
        if isinstance(step, dict) and step.get("name") == SECRET_STEP
    ]
    return OUTCOME.get(str(steps[-1].get("conclusion")), UNKNOWN) if steps else UNKNOWN


def workflow_texts(root: Path, commit: str) -> list[str]:
    listing = git(root, "ls-tree", "--name-only", commit, ".github/workflows/").split("\n")
    names = [name for name in listing if name.endswith(".yml")]
    return [text_at(root, commit, rel, ".github/workflows/") for rel in names]


def scan_entry(kind: str, scanner: str, version: str, outcome: str) -> dict[str, str]:
    return {"kind": kind, "scanner": scanner, "version": version, "outcome": outcome}


def scans_part(root: Path, commit: str, src: Any, runs: list[dict]) -> dict[str, Any]:
    """`scans.json` (rule 6): what no file configures is `not run` with the scanner `none`."""
    pins = set(SCANNER.findall(text_or_empty(root, commit, GOVERNANCE)))
    secret = scan_entry("secret", "none", "none", "not run")
    if pins:
        version = next(iter(pins)) if len(pins) == 1 else UNKNOWN
        secret = scan_entry("secret", "gitleaks", version, step_outcome(src, runs))
    named = sorted({m for text in workflow_texts(root, commit) for m in DEPENDENCY.findall(text)})
    dependency = scan_entry("dependency", "none", "none", "not run")
    if named:
        dependency = scan_entry("dependency", named[0], UNKNOWN, UNKNOWN)
    return {"schema": 1, "scans": [secret, dependency]}


def folder_refusal(root: Path, target: Path) -> str | None:
    """Why `<out>/<tag>/` may not be written; every file of a pack must be ignored by git."""
    if os.path.lexists(target):
        return EXISTS
    if not target.is_relative_to(root.resolve()):
        return None
    inside = target.relative_to(root.resolve())
    names = (str(inside / name) for name in (*FORMS, INDEX))
    return None if all(git(root, "check-ignore", "--", n, check=False) for n in names) else IN_REPO


def write_parts(target: Path, parts: dict[str, dict[str, Any]]) -> str | None:
    """The parts, in a folder this call creates; a folder it cannot finish it removes."""
    try:
        target.mkdir(parents=True)
    except FileExistsError:
        return EXISTS if os.path.lexists(target) else NO_FOLDER
    except OSError:
        return NO_FOLDER
    try:
        for name, data in parts.items():
            (target / name).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    except OSError:
        shutil.rmtree(target, ignore_errors=True)
        return NO_FOLDER
    return None


def source(options: dict[str, str]) -> Any:
    """The saved responses of `--api-dir`, or the live GET-only reader of `--repo` or `origin`."""
    if "--api-dir" in options:
        return metrics.ApiDir(Path(options["--api-dir"]))
    return Live(options.get("--repo") or metrics.origin_repo())


def make(tag: str, out: str, options: dict[str, str]) -> int:
    root = repo_root()
    commit = commit_of(root, tag)
    target = Path(out).resolve() / tag
    refusal = release_refusal(root, tag, commit) or folder_refusal(root, target)
    parts: dict[str, dict[str, Any]] = {}
    if refusal is None:
        try:
            src = source(options)
            runs = check_runs(src, commit)
            parts = {
                "tests.json": tests_part(src, load_config(root)["default_branch"], runs),
                "scans.json": scans_part(root, commit, src, runs),
                "bom.json": bill(root, commit),
                "decisions.json": decisions(root, tag, commit),
            }
            refusal = write_parts(target, parts)
        except Refused as exc:
            refusal = str(exc)
    if refusal:
        print(refusal)
        return 1
    missing = " ".join(name for name in (*FORMS, INDEX) if name not in parts)
    print(f"made {' '.join(parts)}; not yet made: {missing}")
    return 0


def check(arg: str) -> int:
    pack = Path(arg).resolve()
    if not pack.is_dir():
        print("FAIL pack: folder is missing")
        return 1
    root = repo_root()
    tag = pack.name
    commit = commit_of(root, tag)
    refusal = release_refusal(root, tag, commit)
    if refusal:
        print(refusal)
        return 1
    lines = check_folder(pack, tag, commit)
    print("\n".join([*lines, *([] if any(ln.startswith("FAIL") for ln in lines) else ["ok pack"])]))
    return 1 if any(ln.startswith("FAIL") for ln in lines) else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    pairs = list(zip(args[1::2], args[2::2], strict=False)) if len(args) % 2 else []
    options = dict(pairs)
    allowed = {"--tag", "--out", "--api-dir", "--repo"}
    if (
        args[:1] == ["make"]
        and len(options) == len(pairs)
        and {"--tag", "--out"} <= set(options) <= allowed
    ):
        return make(options["--tag"], options["--out"], options)
    if len(args) != 2 or args[0] != "check":
        print(USAGE)
        return 2
    return check(args[1])


if __name__ == "__main__":
    sys.exit(run(NAME, main))
