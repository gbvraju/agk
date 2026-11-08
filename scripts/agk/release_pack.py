"""The evidence pack's form, its release test and its offline check (SPEC-0052 build (b)).

    python3 scripts/agk/release_pack.py check <out>/<tag>

A pack is one folder named by a release tag with exactly six files: the five parts `tests.json`,
`scans.json`, `coverage.json`, `bom.json`, `decisions.json` and the index `pack.json` (rule 2).
`check` reads the folder and the repository's git only, with no network call, and prints `ok pack`,
or one `FAIL pack: <part> <reason>` line for each part with a problem (its first problem) and exits
1, naming the part and never a value (rule 10). A required check `failure` or `unknown`, or a scan
`failed` or `unknown`, is one `warn pack:` line and does not fail: the pack records the release, it
does not judge it.

The release test (rule 4) is `check_tag.failure` on the tagged commit, in a throwaway clone that
shares the repository's objects, so the work tree, refs and worktree list stay as they are. A tag
that fails it, or that is not in the repository, is one `refused:` line. A repository without
`kit/manifest.json` and `check_tag.py` at the tag has no release test yet and is refused naming the
path class. `check_tag.py` is kit-only and this script is installed, so it is imported only after
those files are found. Building a pack (`make`) is SPEC-0052 builds (c) and (d).
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard
from common import CheckError, git, repo_root, run, show

NAME = "pack"
USAGE = "usage: release_pack.py check <out>/<tag>"
INDEX = "pack.json"
UNKNOWN = "unknown"
NO_RELEASE_TEST = "refused: this repository has no release test (path class kit/)"
NOT_RELEASE = "refused: the tag is not a release ({})"
RELEASE_FILES = ("kit/manifest.json", "scripts/agk/check_tag.py")
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


def form_problem(name: str, data: object) -> str | None:
    """Why a part is not of its form, naming no field or value; None when it is."""
    if not isinstance(data, dict):
        return "is not JSON of its form"
    form = FORMS[name]
    if set(data) != {"schema", *form}:
        return "has a missing or extra field"
    if not is_one(data["schema"]):
        return "has a schema other than 1"
    for key, shape in form.items():
        if key == "scorecard_week" and data[key] == UNKNOWN:
            continue
        if not shaped(data[key], shape):
            return "has a field that is not of its form"
    return None


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


def data_problem(raw: bytes) -> str | None:
    found = guard.scan_text(raw.decode("utf-8"))
    return "holds data the guard refuses" if found else None


def index_problem(data: object, tag: str, commit: str) -> str | None:
    if not isinstance(data, dict) or set(data) != INDEX_FIELDS:
        return "has a missing or extra field"
    if not is_one(data["schema"]):
        return "has a schema other than 1"
    if data["tag"] != tag:
        return "names another tag"
    if data["commit"] != commit:
        return "names another commit"
    parts = data["parts"]
    if not isinstance(parts, dict) or set(parts) != set(FORMS):
        return "does not list the five parts"
    return None


def digests_of(index: object) -> dict[str, object]:
    """The index's digests, when it lists exactly the five parts."""
    parts = index.get("parts") if isinstance(index, dict) else None
    return parts if isinstance(parts, dict) and set(parts) == set(FORMS) else {}


def part_problem(path: Path, name: str, digests: dict[str, object]) -> tuple[object, str | None]:
    raw, data, problem = read(path)
    if problem or raw is None:
        return None, problem
    problem = form_problem(name, data)
    if problem is None and digests and hashlib.sha256(raw).hexdigest() != digests.get(name):
        problem = "does not match its digest in the index"
    return data, problem or data_problem(raw)


def warnings(name: str, data: object) -> list[str]:
    """The `warn pack:` lines of one good part; the pack records a result, it does not judge it."""
    if name not in WARN or not isinstance(data, dict):
        return []
    field, who, what, bad = WARN[name]
    return [f"warn pack: {name} {e[who]} {e[what]}" for e in data[field] if e[what] in bad]


def check_folder(pack: Path, tag: str, commit: str) -> list[str]:
    """The `warn pack:` and `FAIL pack:` lines of the folder, in the order of its files."""
    lines = []
    if any(item.name not in {*FORMS, INDEX} for item in pack.iterdir()):
        lines.append("FAIL pack: folder holds a file that is not one of the six")
    raw, index, problem = read(pack / INDEX)
    if problem is None:
        problem = index_problem(index, tag, commit)
    if problem is None and raw is not None:
        problem = data_problem(raw)
    if problem:
        lines.append(f"FAIL pack: {INDEX} {problem}")
    digests = digests_of(index)
    for name in FORMS:
        data, problem = part_problem(pack / name, name, digests)
        lines += [f"FAIL pack: {name} {problem}"] if problem else warnings(name, data)
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


def check(arg: str) -> int:
    pack = Path(arg).resolve()
    if not pack.is_dir():
        print("FAIL pack: folder is missing")
        return 1
    root = repo_root()
    tag = pack.name
    ref = f"refs/tags/{tag}^{{commit}}"
    commit = git(root, "rev-parse", "-q", "--verify", ref, check=False).strip()
    refusal = release_refusal(root, tag, commit)
    if refusal:
        print(refusal)
        return 1
    lines = check_folder(pack, tag, commit)
    print("\n".join([*lines, *([] if any(ln.startswith("FAIL") for ln in lines) else ["ok pack"])]))
    return 1 if any(ln.startswith("FAIL") for ln in lines) else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] != "check":
        print(USAGE)
        return 2
    return check(args[1])


if __name__ == "__main__":
    sys.exit(run(NAME, main))
