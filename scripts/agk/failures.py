"""A failure's signature, its cleaned evidence and its issue body (SPEC-0046 rules 2, 3 and 5).

Usage: python3 scripts/agk/failures.py signature --output FILE [--step NAME]
       python3 scripts/agk/failures.py evidence --output FILE [--test ID]
       python3 scripts/agk/failures.py issue-body --signature SIG --test ID [--issues FILE]
       python3 scripts/agk/failures.py seen --signature SIG --test ID
       python3 scripts/agk/failures.py files --signature SIG --from DIR
       python3 scripts/agk/failures.py files --delete --signature SIG
       python3 scripts/agk/failures.py files --prune --issues FILE
       python3 scripts/agk/failures.py run --on default|release

Brief #634, build (b) of SPEC-0046 (ADR-0303). `signature` prints `<sig> <test id>` for each
failed test of a run: the ids come from the JUnit reports at `[testing] junit`, a path or a glob
(relative to the current folder, the run's folder) when it is set and readable, else from the
runner's `FAILED <id>` lines; a run with neither gets `step:<NAME>`. An id keeps pytest's form in
a report of pytest (a suite named `pytest`) and is `<classname>::<name>` in any other (SPEC-0055
rule 8). The signature is the first 12
hexadecimal characters of the SHA-256 of the test id and the normalised first error line, joined by
one newline. `evidence` prints the last 200 lines of that test's section of the output, redacted
by the data guard's log reader and scanned again (`guard.scan_text`); a finding left, or more than
60,000 characters, prints only `evidence withheld: ...`. `issue-body` prints `action: none` when
`[failures] issues` is off, `action: comment #<n>` when a saved `found-bug` issue list (`--issues`,
GitHub's issue JSON) holds an open issue with the signature, else `action: open` and the new body,
naming closed issues of the signature as seen before. It reads files, prints and writes nothing;
it opens no socket and runs no program. A usage error or a refused setting exits 2, naming the
option or the setting, never a value.

Brief #756, build (d) (rule 9): `seen` is the one subcommand that calls GitHub, with `gh api` GETs
of the project's own repository only (`GITHUB_REPOSITORY`, else the `origin` remote); it posts
nothing and writes no file. It reads the closed `found-bug` issues whose body holds a fix record
(the four lines of rule 7) and the merged pull requests whose body has the line
`Fixes-failure: #<issue>`, and prints at most three lines
`seen before: #<issue> <symptom>; fixed by #<pull request>`: the exact signature first, then the
same test id, newest issue first within each; an issue that no merged pull request names is
skipped, and nothing is matched by text similarity. No match prints nothing; a read that fails
prints one line naming what could not be read and exits 4.

Brief #768, build (h) (rules 6 and 13): `files` is the one subcommand that writes, and only below
`.agk-failures/` at the top of the work tree. `--from DIR` copies the regular files that
`[failures] artifact_paths` matches below DIR, keeping their relative paths, into
`.agk-failures/<signature>/`, replacing that folder's earlier content; a link is never followed,
and with no patterns set nothing happens. A write is refused, naming the path class, when
`git check-ignore -q .agk-failures/` says the folder is not ignored. `--delete` removes the folder
of a fixed failure; `--prune` removes every signature folder with no open `found-bug` issue in a
saved list, and a list that cannot be read removes nothing. Output names a folder only by its
relative path, so no path names a user.

Brief #888, build (i) (rules 12 and 14): `run` is the run that stands in for CI where none runs, and
the one subcommand that writes to GitHub, with the person's `gh` credential. It runs
`project_tests.py` with `EVENT` unset, on the fetched head of the default branch or of an open
release pull request, and only where local mode is on or `execution = "local"`. It refuses, running
nothing and writing nothing, inside an agent session, in a sidecar, with `[failures] issues` off,
on a dirty work tree or another head, and when `gh api repos/{owner}/{repo}` does not answer.
A failure opens one `found-bug` issue or comments on its open one, the evidence in its own comment.
A green run of the default branch closes an open issue whose test it ran and passed, with the fix
record of the merged pull request naming it, after deleting its evidence comments; with no such
pull request the issue stays open and one line says so. It exits 0 on a green run, 1 on a red one.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import xml.parsers.expat
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard_logs
from common import CheckError, execution, load_config, personal_table, utf8_output
from guard import scan_text
from impact import junit_setting, report_files
from local_mode import RECORD_TITLE, SESSION_SETTING

import config

EVIDENCE_LINES = 200
EVIDENCE_LIMIT = 60_000
LINE_LIMIT = 200
FAILED = re.compile(r"^FAILED (\S+)(?: - (.*))?$", re.M)
HEADER = re.compile(r"^_{3,} (.+?) _{3,}$")
SECTION_END = re.compile(r"^(?:_{3,} .+ _{3,}|={3,}.*)$")
NORMALISE = (  # rule 3, in this order, on the lower-cased line
    (re.compile(r"(?<![\w.])(?:[a-z]:[\\/]|/)[^\s'\"<>,;()\[\]]+"), "<path>"),
    (re.compile(r"\b(?:tmp|pytest-of-)[\w.-]+"), "<path>"),
    (re.compile(r"(?<![a-z0-9])[0-9a-f]{7,}(?![a-z0-9])"), "<hex>"),
    (
        re.compile(
            r"\d{4}-\d{2}-\d{2}(?:[t ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:z|[+-]\d{2}:?\d{2})?)?"
        ),
        "<time>",
    ),
    (re.compile(r"\b\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?\b"), "<time>"),
    (re.compile(r"\d+"), "<n>"),
)


RECORD = ("Symptom:", "Cause:", "Reproduce:", "Fixed-by:")  # rule 7
SEEN_MAX = 3
PAGE = 100
ORIGIN = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
SIGNATURE = re.compile(r"[0-9a-f]{12}")
FOLDER = ".agk-failures"  # rule 13, at the top of the work tree
PATH_CLASS = f"path class: {FOLDER}/"
STEP = "Project tests"  # the workflow's step, so a step failure here and on CI is one (rule 3)
EVIDENCE_MARK = "Failure-evidence:"  # the first line of an evidence comment, deleted on the close


class Usage(Exception):
    """A usage error, an unreadable file or a refused setting (exit 2)."""


class Unreadable(Exception):
    """A GitHub read that failed (exit 4); never printed as no match."""


def normalise(line: str) -> str:
    text = line.lower()[:LINE_LIMIT]
    for regex, placeholder in NORMALISE:
        text = regex.sub(placeholder, text)
    return text


def signature(test_id: str, first_line: str) -> str:
    data = f"{test_id}\n{normalise(first_line)}".encode()
    return hashlib.sha256(data).hexdigest()[:12]


def junit_id(attrs: dict[str, str]) -> str:
    """`file::Class::name` from a testcase; without `file`, the module is the dotted classname up
    to its last part that starts with `test` (pytest's own layout)."""
    parts = [p for p in attrs.get("classname", "").split(".") if p]
    cut = max((i for i, p in enumerate(parts) if p.startswith("test")), default=len(parts) - 1)
    path = attrs.get("file") or "/".join(parts[: cut + 1]) + ".py"
    return "::".join([path, *parts[cut + 1 :], attrs.get("name", "")])


def junit_cases(data: bytes, pytest: bool = False) -> tuple[list[tuple[str, str]], set[str]]:
    """(test id, first error line) of each failure of a report, and the ids that passed. PYTEST
    gives pytest's id whatever the suite is called, for a caller that knows the command was
    pytest."""
    found: list[tuple[str, str]] = []
    passed: set[str] = set()
    case: dict[str, str] = {}
    of_pytest = pytest

    def refuse(*_args) -> None:
        raise ValueError

    def test_of(attrs: dict[str, str]) -> str:
        if of_pytest:
            return junit_id(attrs)
        return f"{attrs.get('classname', '')}::{attrs.get('name', '')}"

    def start(name: str, attrs: dict[str, str]) -> None:
        nonlocal case, of_pytest
        if name == "testsuite":
            of_pytest = pytest or attrs.get("name") == "pytest"
        elif name == "testcase":
            case = attrs
            passed.add(test_of(attrs))
        elif name == "skipped" and case:
            passed.discard(test_of(case))
        elif name in ("failure", "error") and case:
            first = (attrs.get("message") or "").splitlines()
            test = test_of(case)
            passed.discard(test)
            found.append((test, first[0] if first else ""))
            case = {}

    parser = xml.parsers.expat.ParserCreate()
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.StartElementHandler = start
    parser.Parse(data, True)
    return found, passed


def junit_failures(data: bytes, pytest: bool = False) -> list[tuple[str, str]]:
    return junit_cases(data, pytest)[0]


def failed_tests(
    output: str, junit: Path | list[Path] | None, pytest: bool = False
) -> list[tuple[str, str]]:
    """(test id, first error line) of each failure: the JUnit report or reports when all are
    readable, else the runner's `FAILED <id>` lines."""
    reports = [junit] if isinstance(junit, Path) else junit or []
    if reports:
        try:
            return [f for r in reports for f in junit_failures(r.read_bytes(), pytest)]
        except (OSError, ValueError, xml.parsers.expat.ExpatError):
            pass
    return [(m.group(1), m.group(2) or "") for m in FAILED.finditer(output)]


def first_error(output: str) -> str:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    return next(
        (ln for ln in lines if re.search("error|fail", ln, re.I)), lines[-1] if lines else ""
    )


def section(output: str, test_id: str | None) -> str:
    """That test's section of the output (pytest's `___ name ___` header), else all of it."""
    if not test_id:
        return output
    name = ".".join(test_id.split("::")[1:]) or test_id
    lines = output.splitlines(keepends=True)
    for i, line in enumerate(lines):
        match = HEADER.match(line.rstrip("\n"))
        if match and match.group(1) == name:
            end = next(
                (j for j in range(i + 1, len(lines)) if SECTION_END.match(lines[j])), len(lines)
            )
            return "".join(lines[i + 1 : end])
    return output


def evidence(output: str, test_id: str | None, patterns) -> str:
    tail = "".join(section(output, test_id).splitlines(keepends=True)[-EVIDENCE_LINES:])
    redacted, _ = guard_logs.redact(tail, patterns)
    left: dict[str, int] = {}
    for finding in scan_text(redacted, patterns=patterns):
        left[finding.kind] = left.get(finding.kind, 0) + 1
    if left:
        return "evidence withheld: " + ", ".join(f"{k} {n}" for k, n in left.items())
    if len(redacted) > EVIDENCE_LIMIT:
        return "evidence withheld: too long"
    return redacted.rstrip("\n")


def issue_body(sig: str, test_id: str, issues: list) -> str:
    mine = [
        i
        for i in issues
        if isinstance(i, dict)
        and "pull_request" not in i
        and any(
            isinstance(lb, dict) and lb.get("name") == "found-bug" for lb in i.get("labels", [])
        )
        and f"Failure-signature: {sig}" in str(i.get("body") or "").splitlines()
    ]
    open_ones = sorted(i["number"] for i in mine if i.get("state") == "open")
    if open_ones:
        return f"action: comment #{open_ones[-1]}"
    closed = sorted((i["number"] for i in mine if i.get("state") == "closed"), reverse=True)[:3]
    lines = ["action: open", f"Failure-signature: {sig}", f"Test: {test_id}"]
    return "\n".join(lines + [f"seen before: #{n}" for n in closed])


def own_repository(root: Path) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        match = ORIGIN.search(proc.stdout.strip())
        repo = match.group(1) if match else ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise Unreadable("the repository cannot be read (the origin remote)")
    return repo


def gh_pages(endpoint: str, what: str) -> list:
    """Every page of one GET list; any failure raises `Unreadable` naming `what`."""
    found: list = []
    page = 1
    while True:
        try:
            proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
                ["gh", "api", "--method", "GET", f"{endpoint}&per_page={PAGE}&page={page}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            chunk = json.loads(proc.stdout) if proc.returncode == 0 else None
        except (OSError, ValueError):
            chunk = None
        if not isinstance(chunk, list):
            raise Unreadable(f"{what} cannot be read")
        found += chunk
        if len(chunk) < PAGE:
            return found
        page += 1


def body_lines(item: dict) -> list[str]:
    return [ln.strip() for ln in str(item.get("body") or "").splitlines()]


def field(lines: list[str], name: str) -> str | None:
    values = [ln[len(name) :].strip() for ln in lines if ln.startswith(name)]
    return values[0] if len(values) == 1 and values[0] else None


def candidates(sig: str, test_id: str, issues: list) -> list[tuple[int, str]]:
    """(issue, symptom) of the closed `found-bug` issues with a fix record, in rule 9's order:
    the exact signature first, then the same test id, newest issue first within each."""
    exact: list[tuple[int, str]] = []
    same_test: list[tuple[int, str]] = []
    for item in issues:
        if (
            not isinstance(item, dict)
            or "pull_request" in item
            or item.get("state") != "closed"
            or not isinstance(item.get("number"), int)
            or not any(
                isinstance(lb, dict) and lb.get("name") == "found-bug"
                for lb in item.get("labels", [])
            )
        ):
            continue
        lines = body_lines(item)
        if any(field(lines, name) is None for name in RECORD):
            continue
        symptom = field(lines, "Symptom:") or ""
        if scan_text(symptom):
            symptom = "(symptom withheld)"
        if field(lines, "Failure-signature:") == sig:
            exact.append((item["number"], symptom))
        elif field(lines, "Test:") == test_id:
            same_test.append((item["number"], symptom))
    return sorted(exact, reverse=True) + sorted(same_test, reverse=True)


def fixed_by(pulls: list) -> dict[int, int]:
    """Issue number -> the newest merged pull request whose body has `Fixes-failure: #<issue>`."""
    newest: dict[int, tuple[str, int]] = {}
    for pr in pulls:
        if not isinstance(pr, dict) or not pr.get("merged_at"):
            continue
        if not isinstance(pr.get("number"), int):
            continue
        key = (str(pr["merged_at"]), pr["number"])
        for ln in body_lines(pr):
            match = re.fullmatch(r"Fixes-failure: #(\d+)", ln)
            if match:
                n = int(match.group(1))
                newest[n] = max(newest.get(n, key), key)
    return {n: key[1] for n, key in newest.items()}


def seen_before(sig: str, test_id: str, issues: list, pulls: list) -> list[str]:
    fixed = fixed_by(pulls)
    found = [
        f"seen before: #{n} {symptom}; fixed by #{fixed[n]}"
        for n, symptom in candidates(sig, test_id, issues)
        if n in fixed
    ]
    return found[:SEEN_MAX]


def seen_command(root: Path, sig: str, test_id: str) -> str:
    repo = own_repository(root)
    issues = gh_pages(
        f"repos/{repo}/issues?state=closed&labels=found-bug", "the closed found-bug issues"
    )
    if not candidates(sig, test_id, issues):
        return ""
    pulls = gh_pages(f"repos/{repo}/pulls?state=closed", "the merged pull requests")
    return "\n".join(seen_before(sig, test_id, issues, pulls))


def options(args: list[str], allowed: set[str]) -> dict[str, str]:
    opts: dict[str, str] = {}
    for i in range(0, len(args), 2):
        if args[i] not in allowed or i + 1 >= len(args) or args[i] in opts:
            raise Usage(f"usage: see the module text (option: {args[i]})")
        opts[args[i]] = args[i + 1]
    return opts


def read(opts: dict[str, str], option: str) -> str:
    try:
        return Path(opts[option]).read_text(encoding="utf-8", errors="replace")
    except (KeyError, OSError):
        raise Usage(f"the file cannot be read (option: {option})") from None


def work_tree() -> Path:
    """The top of the work tree, where the evidence folder lives (rule 13)."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise Usage(f"the work tree cannot be read ({PATH_CLASS})")
    return Path(proc.stdout.strip())


def evidence_base(root: Path) -> Path:
    """`.agk-failures` of ROOT; a link there would carry a write or a delete elsewhere."""
    base = root / FOLDER
    if base.is_symlink():
        raise Usage(f"the folder is a link ({PATH_CLASS})")
    return base


def is_ignored(root: Path) -> bool:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), "check-ignore", "-q", f"{FOLDER}/"],
        capture_output=True,
    )
    return proc.returncode == 0


def remove(path: Path) -> None:
    """Remove PATH, a folder of the evidence folder; a link goes, never what it points at."""
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError:
        raise Usage(f"the evidence cannot be removed ({PATH_CLASS})") from None


def matched_files(source: Path, patterns: list[str], base: Path) -> list[Path]:
    """The regular files below SOURCE that PATTERNS match: no link, nothing reached through a
    link, nothing already in the evidence folder at BASE."""
    top = source.resolve()
    found: set[Path] = set()
    try:
        paths = [path for pattern in patterns for path in source.glob(pattern)]
    except (ValueError, NotImplementedError):
        raise Usage("a pattern cannot be read (setting: failures.artifact_paths)") from None
    for path in paths:
        resolved = path.parent.resolve() / path.name
        if (
            path.is_file()
            and not path.is_symlink()
            and resolved.is_relative_to(top)
            and not resolved.is_relative_to(base.resolve())
        ):
            found.add(path)
    return sorted(found)


def copy_evidence(root: Path, sig: str, source: Path) -> str:
    """Rule 13: replace `.agk-failures/<sig>/` with the matched files of the run folder SOURCE."""
    patterns = config.failures_settings(root)["artifact_paths"]
    if not patterns:
        return "files: none (setting: failures.artifact_paths)"
    if not source.is_dir():
        raise Usage("the run's folder cannot be read (option: --from)")
    base = evidence_base(root)
    if not is_ignored(root):
        raise Usage(f"the folder is not ignored by git ({PATH_CLASS})")
    files = matched_files(source, patterns, base)
    folder = base / sig
    try:
        if folder.exists() or folder.is_symlink():
            remove(folder)
        for path in files:
            target = folder / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    except OSError:
        raise Usage(f"the evidence cannot be written ({PATH_CLASS})") from None
    return f"files: {len(files)} copied to {FOLDER}/{sig}/"


def open_signatures(issues: list) -> set[str]:
    """The signatures of the open `found-bug` issues of a saved list."""
    found: set[str] = set()
    for item in issues:
        if (
            "pull_request" not in item
            and item.get("state") == "open"
            and any(
                isinstance(lb, dict) and lb.get("name") == "found-bug"
                for lb in item.get("labels", [])
            )
        ):
            found |= {
                ln.split(":", 1)[1].strip()
                for ln in body_lines(item)
                if ln.startswith("Failure-signature:")
            }
    return found


def prune_evidence(root: Path, issues: list) -> str:
    """Rule 13: delete each signature folder with no open issue; other names are left alone."""
    base = evidence_base(root)
    keep = open_signatures(issues)
    gone = (
        [p for p in sorted(base.iterdir()) if SIGNATURE.fullmatch(p.name) and p.name not in keep]
        if base.is_dir()
        else []
    )
    for path in gone:
        remove(path)
    return "\n".join(f"files: deleted {FOLDER}/{p.name}/" for p in gone)


def delete_evidence(root: Path, sig: str) -> str:
    folder = evidence_base(root) / sig
    if not (folder.exists() or folder.is_symlink()):
        return ""
    remove(folder)
    return f"files: deleted {FOLDER}/{sig}/"


def issue_list_for_prune(opts: dict[str, str]) -> list[dict]:
    """The saved list, or a refusal: a list that cannot be read never reads as no open issue."""
    try:
        issues = json.loads(read(opts, "--issues"))
    except ValueError:
        issues = None
    if not isinstance(issues, list) or not all(isinstance(i, dict) for i in issues):
        raise Usage("the issue list cannot be read (option: --issues)")
    return issues


def files_command(rest: list[str]) -> str:
    flags = [a for a in rest if a in ("--delete", "--prune")]
    args = [a for a in rest if a not in ("--delete", "--prune")]
    if len(flags) > 1:
        raise Usage("--delete or --prune, not both (option: --prune)")
    allowed = {"--issues"} if flags == ["--prune"] else {"--signature"}
    opts = options(args, allowed if flags else {"--signature", "--from"})
    if flags == ["--prune"]:
        return prune_evidence(work_tree(), issue_list_for_prune(opts))
    if not SIGNATURE.fullmatch(opts.get("--signature", "")):
        raise Usage("a signature is needed (option: --signature)")
    if flags:
        return delete_evidence(work_tree(), opts["--signature"])
    if "--from" not in opts:
        raise Usage("the run's folder is needed (option: --from)")
    return copy_evidence(work_tree(), opts["--signature"], Path(opts["--from"]))


def refuse(rule: int, what: str) -> Usage:
    return Usage(f"refused (SPEC-0046 rule {rule}): {what}")


def git_out(root: Path, *args: str) -> str:
    """The trimmed output of a git read, empty when it fails."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8"
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def repository_answers(repo: str) -> bool:
    """Rule 14's one GET: `gh` exits 0 with the repository's object only on a 200."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["gh", "api", "--method", "GET", f"repos/{repo}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return proc.returncode == 0 and isinstance(json.loads(proc.stdout), dict)
    except (OSError, ValueError):
        return False


def gh_send(method: str, endpoint: str, data: dict | None, what: str) -> dict:
    """One write through `gh` with the person's credential; a failure raises `Unreadable`."""
    args = ["gh", "api", "--method", method, endpoint]
    try:
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [*args, "--input", "-"] if data is not None else args,
            input=json.dumps(data) if data is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        raise Unreadable(f"{what} cannot be written") from None
    if proc.returncode != 0:
        raise Unreadable(f"{what} cannot be written")
    try:
        answer = json.loads(proc.stdout or "{}")
    except ValueError:
        raise Unreadable(f"{what} cannot be read") from None
    return answer if isinstance(answer, dict) else {}


def release_head(root: Path, repo: str, head: str, base: str) -> bool:
    """HEAD is the fetched head of an open pull request into BASE that changes `version`."""
    from project_tests import toml_version  # only a release run needs it, with prepush behind it

    pulls = gh_pages(f"repos/{repo}/pulls?state=open", "the open pull requests")
    refs = [
        str(p["head"].get("ref"))
        for p in pulls
        if isinstance(p, dict)
        and isinstance(p.get("head"), dict)
        and isinstance(p.get("base"), dict)
        and p["head"].get("sha") == head
        and p["base"].get("ref") == base
    ]
    version = toml_version(git_out(root, "show", "HEAD:agk.toml"))
    return (
        any(
            git_out(root, "rev-parse", "--verify", f"refs/remotes/origin/{r}") == head for r in refs
        )
        and version is not None
        and version != toml_version(git_out(root, "show", f"refs/remotes/origin/{base}:agk.toml"))
    )


def run_gate(root: Path, on: str) -> tuple[str, str]:
    """Every refusal of rules 2, 12, 13 and 14, before anything runs: (repository, head)."""
    if os.environ.get(SESSION_SETTING):
        raise refuse(12, f"a person runs this (environment setting: {SESSION_SETTING})")
    if personal_table(root) is not None:
        raise refuse(12, "a sidecar reports nothing (setting: personal.forge)")
    settings = config.failures_settings(root)
    if not settings["issues"]:
        raise refuse(2, "failure issues are off (setting: failures.issues)")
    if settings["artifact_paths"]:
        evidence_base(root)  # refuses a link there
        if not is_ignored(root):
            raise refuse(13, f"the folder is not ignored by git ({PATH_CLASS})")
    if git_out(root, "status", "--porcelain") or not git_out(root, "rev-parse", "HEAD"):
        raise refuse(12, "the work tree is not clean (path class: work tree)")
    try:
        repo = own_repository(root)
    except Unreadable:
        raise refuse(14, "the repository cannot be read (the origin remote)") from None
    if not repository_answers(repo):
        raise refuse(14, "the repository does not answer (gh api repos/{owner}/{repo})")
    if execution(root) != "local" and not any(
        isinstance(i, dict)
        and "pull_request" not in i
        and str(i.get("title") or "").startswith(RECORD_TITLE)
        for i in gh_pages(f"repos/{repo}/issues?state=open", "the open issues")
    ):
        raise refuse(12, "CI runs here, so its runs report (setting: execution)")
    head = git_out(root, "rev-parse", "HEAD")
    base = load_config(root)["default_branch"]
    fetched = git_out(root, "rev-parse", "--verify", f"refs/remotes/origin/{base}")
    if on == "default" and head != fetched:
        raise refuse(12, "HEAD is not the default branch's head as last fetched")
    if on == "release" and not release_head(root, repo, head, base):
        raise refuse(12, "HEAD is not the fetched head of a release pull request")
    return repo, head


def run_tests(root: Path) -> tuple[int, str]:
    """The project's full command, as for a push: `EVENT` unset. Shown as it runs, and kept."""
    env = {k: v for k, v in os.environ.items() if k != "EVENT"}
    script = Path(__file__).resolve().parent / "project_tests.py"
    lines: list[str] = []
    with subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script)],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as proc:
        for line in proc.stdout or []:
            sys.stdout.write(line)
            lines.append(line)
        return proc.wait(), "".join(lines)


def found_bug(item) -> bool:
    return (
        isinstance(item, dict)
        and "pull_request" not in item
        and isinstance(item.get("number"), int)
        and any(
            isinstance(lb, dict) and lb.get("name") == "found-bug" for lb in item.get("labels", [])
        )
    )


def report_failure(root: Path, repo: str, run: dict, sig: str, test: str, issues: list) -> None:
    """Rules 3, 4, 5 and 13: open the issue or find the open one, then one evidence comment."""
    patterns = config.guard_patterns(root)
    shown = "(test id withheld)" if scan_text(test, patterns=patterns) else test
    lines = issue_body(sig, shown, issues).splitlines()
    if lines[0] == "action: open":
        detail = seen_command(root, sig, test).splitlines()
        named = {ln.split()[2] for ln in detail}
        body = [ln for ln in lines[1:] if ln.removeprefix("seen before: ") not in named] + detail
        made = gh_send(
            "POST",
            f"repos/{repo}/issues",
            {"title": f"Failure: {shown}"[:200], "body": "\n".join(body), "labels": ["found-bug"]},
            "the failure issue",
        )
        number = made.get("number")
        if not isinstance(number, int):
            raise Unreadable("the failure issue cannot be read")
    else:
        number = int(lines[0].rsplit("#", 1)[1])
    copied = copy_evidence(root, sig, root)
    files = (
        [f"files: {FOLDER}/{sig}/ on the machine that ran this run"]
        if " copied to " in copied and not copied.startswith("files: 0 ")
        else []
    )
    text = evidence(run["output"], None if test.startswith("step:") else test, patterns)
    comment = [
        f"{EVIDENCE_MARK} {sig}",
        f"Run: failures.py run --on {run['on']}",
        f"Head: {run['head']}",
        "~~~~~~text",
        text,
        "~~~~~~",
        "artifacts: not uploaded",
        *files,
    ]
    gh_send(
        "POST",
        f"repos/{repo}/issues/{number}/comments",
        {"body": "\n".join(comment)},
        "the evidence comment",
    )
    print(f"failures: {sig} reported on #{number}")


def passed_tests(reports: list[Path]) -> set[str]:
    """The ids a green run passed: its reports' passes and the step itself (rule 8)."""
    passed = {f"step:{STEP}"}
    for report in reports:
        try:
            passed |= junit_cases(report.read_bytes())[1]
        except (OSError, ValueError, xml.parsers.expat.ExpatError):
            continue
    return passed


def close_issue(root: Path, repo: str, item: dict, sig: str, pull: dict) -> None:
    """Rule 8: evidence comments go first, so a failed delete leaves the issue open."""
    number = item["number"]
    lines = body_lines(pull)
    record = [f"{name} {field(lines, name)}" for name in RECORD]
    if any(field(lines, name) is None for name in RECORD) or scan_text(
        "\n".join(record), patterns=config.guard_patterns(root)
    ):
        print(f"failures: #{number} stays open: the pull request's fix record cannot be used")
        return
    comments = gh_pages(f"repos/{repo}/issues/{number}/comments?sort=created", "the comments")
    for comment in comments:
        if isinstance(comment, dict) and str(comment.get("body") or "").startswith(EVIDENCE_MARK):
            gh_send("DELETE", f"repos/{repo}/issues/comments/{comment['id']}", None, "the evidence")
    body = str(item.get("body") or "").rstrip() + "\n" + "\n".join(record)
    gh_send(
        "PATCH",
        f"repos/{repo}/issues/{number}",
        {"body": body, "state": "closed", "state_reason": "completed"},
        "the failure issue",
    )
    delete_evidence(root, sig)
    print(f"failures: #{number} closed")


def close_passed(root: Path, repo: str, issues: list, passed: set[str]) -> None:
    """Rule 8: each open failure issue whose test this green run ran and passed."""
    targets = []
    for item in issues:
        if not found_bug(item) or item.get("state") != "open":
            continue
        lines = body_lines(item)
        sig = field(lines, "Failure-signature:") or ""
        if SIGNATURE.fullmatch(sig) and field(lines, "Test:") in passed:
            targets.append((item, sig))
    if not targets:
        return
    pulls = gh_pages(f"repos/{repo}/pulls?state=closed", "the merged pull requests")
    fixed = fixed_by(pulls)
    by_number = {p["number"]: p for p in pulls if isinstance(p, dict) and "number" in p}
    for item, sig in targets:
        if item["number"] in fixed:
            close_issue(root, repo, item, sig, by_number[fixed[item["number"]]])
        else:
            print(f"failures: #{item['number']} stays open: no merged pull request names it")


def run_command(rest: list[str]) -> int:
    """Rules 12 and 14: the stand-in run; its exit is the run's, 0 green and 1 red."""
    on = options(rest, {"--on"}).get("--on")
    if on not in ("default", "release"):
        raise Usage("--on default or --on release (option: --on)")
    root = work_tree()
    repo, head = run_gate(root, on)
    started = time.time()
    code, output = run_tests(root)
    junit = junit_setting(root)
    reports = report_files(root, junit, started) if junit else []
    endpoint = f"repos/{repo}/issues?state=all&labels=found-bug"
    issues = gh_pages(endpoint, "the found-bug issues")
    reported: dict[str, str] = {}
    if code != 0:
        found = failed_tests(output, reports) or [(f"step:{STEP}", first_error(output))]
        run = {"on": on, "head": head, "output": output}
        for test, line in dict(found).items():
            reported[signature(test, line)] = test
        for sig, test in reported.items():
            report_failure(root, repo, run, sig, test, issues)
    elif on == "default":
        close_passed(root, repo, issues, passed_tests(reports))
    keep = [
        {"state": "open", "labels": [{"name": "found-bug"}], "body": f"Failure-signature: {sig}"}
        for sig in reported
    ]
    pruned = prune_evidence(root, gh_pages(endpoint, "the found-bug issues") + keep)
    if pruned:
        print(pruned)
    return 1 if code != 0 else 0


def command(args: list[str]) -> str:
    root = Path.cwd()
    name, rest = (args[0], args[1:]) if args else ("", [])
    if name == "signature":
        opts = options(rest, {"--output", "--step"})
        output = read(opts, "--output")
        junit = junit_setting(root)
        found = failed_tests(output, report_files(root, junit) if junit else None)
        if not found:
            if "--step" not in opts:
                raise Usage("no test id was found (option: --step)")
            found = [(f"step:{opts['--step']}", first_error(output))]
        seen = dict(found)  # one line per test id, in order
        return "\n".join(f"{signature(t, line)} {t}" for t, line in seen.items())
    if name == "evidence":
        opts = options(rest, {"--output", "--test"})
        output = read(opts, "--output")
        return evidence(output, opts.get("--test"), config.guard_patterns(root))
    if name == "issue-body":
        opts = options(rest, {"--signature", "--test", "--issues"})
        if not re.fullmatch(r"[0-9a-f]{12}", opts.get("--signature", "")) or not opts.get("--test"):
            raise Usage("a signature and a test id are needed (option: --signature)")
        if not config.failures_settings(root)["issues"]:
            return "action: none (setting: failures.issues)"
        issues = []
        if "--issues" in opts:
            try:
                issues = json.loads(read(opts, "--issues"))
            except ValueError:
                raise Usage("the issue list cannot be read (option: --issues)") from None
        return issue_body(
            opts["--signature"], opts["--test"], issues if isinstance(issues, list) else []
        )
    if name == "seen":
        opts = options(rest, {"--signature", "--test"})
        if not re.fullmatch(r"[0-9a-f]{12}", opts.get("--signature", "")) or not opts.get("--test"):
            raise Usage("a signature and a test id are needed (option: --signature)")
        return seen_command(root, opts["--signature"], opts["--test"])
    if name == "files":
        return files_command(rest)
    raise Usage("usage: failures.py signature|evidence|issue-body|seen|files|run ...")


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args[:1] == ["run"]:
            return run_command(args[1:])
        out = command(args)
        if out:
            print(out)
    except (Usage, CheckError) as exc:
        print(f"failures: {exc}")
        return 2
    except Unreadable as exc:
        print(f"failures: {exc}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
