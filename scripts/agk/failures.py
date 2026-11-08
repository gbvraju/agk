"""A failure's signature, its cleaned evidence and its issue body (SPEC-0046 rules 2, 3 and 5).

Usage: python3 scripts/agk/failures.py signature --output FILE [--step NAME]
       python3 scripts/agk/failures.py evidence --output FILE [--test ID]
       python3 scripts/agk/failures.py issue-body --signature SIG --test ID [--issues FILE]
       python3 scripts/agk/failures.py seen --signature SIG --test ID

Brief #634, build (b) of SPEC-0046 (ADR-0303). `signature` prints `<sig> <test id>` for each
failed test of a run: the ids come from the JUnit report at `[testing] junit` (relative to the
current folder, the run's folder) when it is set and readable, else from the runner's
`FAILED <id>` lines; a run with neither gets `step:<NAME>`. The signature is the first 12
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
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import xml.parsers.expat
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard_logs
from common import CheckError
from guard import scan_text
from impact import junit_setting

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


def junit_failures(data: bytes) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    case: dict[str, str] = {}

    def refuse(*_args) -> None:
        raise ValueError

    def start(name: str, attrs: dict[str, str]) -> None:
        nonlocal case
        if name == "testcase":
            case = attrs
        elif name in ("failure", "error") and case:
            first = (attrs.get("message") or "").splitlines()
            found.append((junit_id(case), first[0] if first else ""))
            case = {}

    parser = xml.parsers.expat.ParserCreate()
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.StartElementHandler = start
    parser.Parse(data, True)
    return found


def failed_tests(output: str, junit: Path | None) -> list[tuple[str, str]]:
    """(test id, first error line) of each failure: the JUnit report when readable, else the
    runner's `FAILED <id>` lines."""
    if junit is not None:
        try:
            return junit_failures(junit.read_bytes())
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


def command(args: list[str]) -> str:
    root = Path.cwd()
    name, rest = (args[0], args[1:]) if args else ("", [])
    if name == "signature":
        opts = options(rest, {"--output", "--step"})
        output = read(opts, "--output")
        junit = junit_setting(root)
        found = failed_tests(output, root / junit if junit else None)
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
    raise Usage("usage: failures.py signature|evidence|issue-body|seen ...")


def main(argv: list[str] | None = None) -> int:
    try:
        out = command(list(sys.argv[1:] if argv is None else argv))
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
