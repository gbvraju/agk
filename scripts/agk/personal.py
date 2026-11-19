# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Personal mode's commands on a sidecar: the baseline of the tests already failing.

    python3 personal.py baseline [--clone DIR] [--sidecar DIR] [--approve]
    python3 personal.py floor [--clone DIR] [--sidecar DIR] [--base REF] [--approve]
    python3 personal.py report [--week YYYY-Www] [--clone DIR] [--sidecar DIR]
    python3 personal.py confirm <REQ-nnn|SPEC-nnnn|ADR-nnnn> [--clone DIR] [--sidecar DIR]
    python3 personal.py gate [--clone DIR] [--sidecar DIR] [--base REF] [--approve]

SPEC-0041 build (h), first part, rule 16. `baseline` prints the test command it would run: the
sidecar's `[personal] test_command`, else the one test command the survey's inventory declares
(rule 10), else it refuses naming the setting. Only with `--approve`, which the skill passes after
the person says yes, it runs the command once on the clone's head tree, written with `git archive`
into the sidecar's `cache/trees/` (rule 4: nothing is written in the clone or under its `.git/`),
and records in `records/baseline.json` the head, the command and each test already failing: per
test from a JUnit XML report when the command has the `{junit}` placeholder, else the whole run
(`Q-S0041-19`). Standard library only; no network. Refusals name the setting, never a value.

`floor` (build (h), second part, rule 18) judges the branch from the merge base with `--base`
(else `origin/HEAD`) to the head, at every level: the secret scan is `prepush.secret_scan`
unchanged, and a missing gitleaks fails (`Q-S0041-15`); with `--approve` the test command runs on
the base tree and on the head tree, and a test that passed on the base and fails on the head fails
the floor, or, without `{junit}`, a passing base and a failing head do, and a failing base is
`unknown`, never a pass. No setting changes a step; it exits 0 only when both pass.

Rule 23 (build (k), first part): a floor with `--approve` appends one line `{head, step, result,
time}` to the sidecar's `metrics/events.jsonl`; `report` counts, for one ISO week, the defects the
floor caught before a push (a failed head followed by a passed head that descends from it), with
`unknown` under two events. It reads files and git only; build (k)'s second part adds the rest.

`confirm` (build (g), part 1, rules 8 and 15, brief #1502) is the person's own terminal act: it is
refused while `CLAUDECODE` is set, when standard input is not a terminal and on a sidecar whose work
tree is not clean. It shows three lines, asks yes or no, and on yes writes `forge/pulls/<n>.json`
(head `<C>`, the sidecar's `HEAD`) and the confirmation of rule 8 in `forge/comments-<n>.json`,
moves a spec to `Approved` or an ADR to `Accepted` (a requirement's status does not move), runs the
kind's reader with `--base <C>` and `--comments`, and makes one commit, the child of `<C>`, only
when the reader passes; else it restores the work tree to `<C>` and exits 1 naming the reader.

`gate` (build (h), part 2, rules 17 to 20 and 23, brief #1503) is what `/agk:personal push` runs.
Without `--approve` it runs nothing. With it: the floor at every level, then by `level`:
`tests-first` (the branch's test files placed on the base tree, `proof.decide`: red on the base,
green on the head), `spec` (a spec confirmed at a terminal before the branch's first commit),
`review` (the context and report under `records/reviews/`, `check_review_report`, and the
person's terminal verdict naming the head) and `evidence` (`evidence.parse` and
`evidence.problems` on the record). It writes `records/gates/<head>.json` in the schema of
`prepush.py --record`, one event per step and the gate's, and one sidecar commit; on a pass it
prints the push command for the developer and runs none. With `team_refs` off it warns of a
commit carrying an `Advances:` line or a sidecar path. `report` names each local branch whose head
equals its upstream's remote-tracking ref (no fetch) and has no gate record.
"""

from __future__ import annotations

import io
import json
import os
import re
import shlex
import shutil
import subprocess  # nosec B404 - fixed git argument lists and the person's approved command, no shell
import sys
import tarfile
import tempfile
import xml.parsers.expat
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (  # noqa: E402
    STATUS_LINE,
    CheckError,
    parse_requirements,
    personal_table,
    utf8_output,
)
from survey import INVENTORY, detect_test_files, find_sidecar, write_private  # noqa: E402

USAGE = (
    "usage: personal.py baseline|floor|gate|report [--clone DIR] [--sidecar DIR] [--base REF] "
    "[--week YYYY-Www] [--approve]\n"
    "       personal.py confirm <REQ-nnn|SPEC-nnnn|ADR-nnnn> [--clone DIR] [--sidecar DIR]"
)
SETTING = "personal.test_command"
JUNIT = "{junit}"
BASELINE = "records/baseline.json"
TREES = "cache/trees"
REPORT = "cache/baseline-junit.xml"
GIT = ("git", "--no-optional-locks")
EVENTS = "metrics/events.jsonl"
FIELDS = {"head", "step", "result", "time"}
STAMP = "%Y-%m-%dT%H:%M:%SZ"
WEEK = re.compile(r"([0-9]{4})-W([0-9]{2})")
SECOND_PART = "build (k), second part"
CAUTION = "These numbers show correlation, not causation."


def _git(clone: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed read-only git argument list, no shell
        [*GIT, "-C", str(clone), *args], capture_output=True, check=False
    )


def declared_commands(sidecar: Path) -> list[str]:
    """The distinct test commands of the inventory's manifests, in order; none without it."""
    path = sidecar / INVENTORY
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))["manifests"]
        found = [c for row in rows for c in row["test_commands"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CheckError(f"the inventory cannot be read (path: {INVENTORY})") from exc
    if not all(isinstance(c, str) for c in found):
        raise CheckError(f"the inventory cannot be read (path: {INVENTORY})")
    return list(dict.fromkeys(c for c in found if c.strip()))


def test_command(sidecar: Path) -> str:
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    if "test_command" in table:
        return table["test_command"]
    declared = declared_commands(sidecar)
    if len(declared) != 1:
        raise CheckError(f"no single test command is set or declared (setting: {SETTING})")
    return declared[0]


def head_of(clone: Path) -> str:
    done = _git(clone, "rev-parse", "--verify", "HEAD^{commit}")
    if done.returncode != 0:
        raise CheckError("the clone has no head commit (option: --clone)")
    return done.stdout.decode("ascii").strip()


def write_tree(clone: Path, head: str, sidecar: Path, name: str | None = None) -> Path:
    """The head's tree under the sidecar, from git's object store; the clone is only read."""
    done = _git(clone, "archive", "--format=tar", head)
    if done.returncode != 0:
        raise CheckError("the head tree cannot be archived (option: --clone)")
    tree = sidecar / TREES / (name or head)
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(mode=0o700, parents=True)
    with tarfile.TarFile(fileobj=io.BytesIO(done.stdout)) as archive:
        archive.extractall(tree, filter="data")
    return tree


def junit_failing(data: bytes) -> list[str]:
    """The id `file::name` (the classname when there is no `file`) of each test case with a
    failure or an error, sorted; a document type or an entity is refused."""
    return sorted(i for i, ok in junit_cases(data).items() if not ok)


def junit_cases(data: bytes) -> dict[str, bool]:
    """Each test case's id, true when it has neither a failure nor an error."""
    cases: dict[str, bool] = {}
    case: dict[str, str] = {}

    def refuse(*_args) -> None:
        raise ValueError

    def start(name: str, attrs: dict[str, str]) -> None:
        nonlocal case
        if name == "testcase":
            case = attrs
            cases.setdefault(case_id(case), True)
        elif name in ("failure", "error") and case:
            cases[case_id(case)] = False

    parser = xml.parsers.expat.ParserCreate()
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.StartElementHandler = start
    parser.Parse(data, True)
    return cases


def case_id(case: dict[str, str]) -> str:
    return f"{case.get('file') or case.get('classname', '')}::{case.get('name', '')}"


def run_once(command: str, tree: Path, sidecar: Path, report_name: str = REPORT) -> dict:
    """Run the command once in TREE and say what failed; the person approved it."""
    report = sidecar / report_name
    per_test = JUNIT in command
    try:
        args = [arg.replace(JUNIT, str(report)) for arg in shlex.split(command)]
    except ValueError as exc:
        raise CheckError(f"the test command cannot be split (setting: {SETTING})") from exc
    if not args:
        raise CheckError(f"the test command is empty (setting: {SETTING})")
    report.unlink(missing_ok=True)
    try:
        done = subprocess.run(  # nosec B603 - the person's approved command, no shell
            args, cwd=tree, capture_output=True, check=False
        )
    except OSError as exc:
        raise CheckError(f"the test command cannot be started (setting: {SETTING})") from exc
    failing = cases = None
    if per_test:
        try:
            cases = junit_cases(report.read_bytes())
            failing = sorted(i for i, ok in cases.items() if not ok)
        except (OSError, ValueError, xml.parsers.expat.ExpatError) as exc:
            raise CheckError(
                f"the JUnit report cannot be read (setting: {SETTING}, {JUNIT})"
            ) from exc
    return {
        "run": "passed" if done.returncode == 0 else "failed",
        "per_test": per_test,
        "failing": failing,
        "cases": cases,
    }


def baseline(clone: Path, sidecar: Path, approve: bool) -> str:
    command = test_command(sidecar)
    if not approve:
        return f"baseline: would run: {command}\nbaseline: nothing ran; run again with --approve"
    head = head_of(clone)
    result = run_once(command, write_tree(clone, head, sidecar), sidecar)
    record = {"head": head, "command": command, **{k: v for k, v in result.items() if k != "cases"}}
    write_private(sidecar / BASELINE, json.dumps(record, indent=1, sort_keys=True) + "\n")
    count = "the whole run" if result["failing"] is None else f"{len(result['failing'])} failing"
    return f"baseline: recorded {count} ({result['run']}) at {head[:12]} in {BASELINE}"


def merge_base(clone: Path, ref: str | None) -> str:
    """The merge base of REF (else `origin/HEAD`, the default branch) with the head."""
    done = _git(clone, "merge-base", ref or "refs/remotes/origin/HEAD", "HEAD")
    if done.returncode != 0:
        raise CheckError("no merge base with the default branch (option: --base)")
    return done.stdout.decode("ascii").strip()


def scan_step(clone: Path, base: str) -> tuple[bool, str]:
    """Step one: `prepush.secret_scan` unchanged; no gitleaks fails, with no deferral to CI."""
    if shutil.which("gitleaks") is None:
        return False, "floor: secret scan not run (gitleaks not installed)"
    import prepush  # noqa: PLC0415 - only `floor` needs the scan step

    found = prepush.secret_scan(clone, base)
    if found.outcome == "ok":
        return True, "floor: secret-scan ok"
    return False, f"floor: secret-scan FAIL: gitleaks reported a finding; {prepush.LEAK_RUNBOOK}"


def regression_step(
    command: str, clone: Path, sidecar: Path, base: str, head: str, runs: dict | None = None
) -> tuple:
    """Step two: the test command on the base tree and on the head tree, then compared; RUNS,
    when given, keeps the two runs for the gate's proof step."""
    runs = {} if runs is None else runs
    for name, sha in (("base", base), ("head", head)):
        report = f"cache/floor-{name}-junit.xml"
        runs[name] = run_once(command, write_tree(clone, sha, sidecar), sidecar, report)
    was, now = runs["base"], runs["head"]
    if was["cases"] is not None:
        broken = sorted(i for i, ok in now["cases"].items() if not ok and was["cases"].get(i))
        if broken:
            return False, "floor: no-regression FAIL: passed on the base, failing on the head: " + (
                ", ".join(broken)
            )
        return True, "floor: no-regression ok (per test)"
    if was["run"] == "failed":
        return False, "floor: no-regression unknown: the base run already fails (setting: {junit})"
    if now["run"] == "failed":
        return False, "floor: no-regression FAIL: the base run passes and the head run fails"
    return True, "floor: no-regression ok (whole run)"


def floor(clone: Path, sidecar: Path, ref: str | None, approve: bool) -> tuple[bool, str]:
    """Rule 18: both steps at every level; `level` is only printed."""
    command = test_command(sidecar)
    level = (personal_table(sidecar) or {}).get("level", "light")
    head = head_of(clone)
    base = merge_base(clone, ref)
    lines = [f"floor: level {level}, base {base[:12]}, head {head[:12]}"]
    scanned, line = scan_step(clone, base)
    lines.append(line)
    if approve:
        tested, line = regression_step(command, clone, sidecar, base, head)
    else:
        tested = False
        line = (
            f"floor: no-regression not run: would run {command} on the base tree and on the head "
            "tree; run again with --approve"
        )
    lines.append(line)
    passed = scanned and tested
    lines.append("floor: passed" if passed else "floor: failed")
    if approve:
        lines.extend(append_event(sidecar, head, "floor", "passed" if passed else "failed"))
    return passed, "\n".join(lines)


def append_event(sidecar: Path, head: str, step: str, result: str) -> list[str]:
    """Rule 23: one JSON line, `0600` under `0700` as `write_private`; a failure is one line."""
    stamp = datetime.now(UTC).strftime(STAMP)
    line = json.dumps({"head": head, "step": step, "result": result, "time": stamp})
    path = sidecar / EVENTS
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
    except OSError:
        return [f"floor: the event cannot be written (path: {EVENTS})"]
    return []


def read_events(sidecar: Path) -> tuple[list[dict], int]:
    """The readable events and the count of lines skipped; no file is no event."""
    try:
        text = (sidecar / EVENTS).read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], 0
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"the events cannot be read (path: {EVENTS})") from exc
    events, skipped = [], 0
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
            ok = isinstance(event, dict) and set(event) == FIELDS
            ok = ok and all(isinstance(event[k], str) for k in FIELDS)
            ok = ok and re.fullmatch(r"[0-9a-f]{40}", event["head"]) is not None
            ok = ok and event["result"] in ("passed", "failed")
            if ok:
                event["at"] = datetime.strptime(event["time"], STAMP).replace(tzinfo=UTC)
        except ValueError:
            ok = False
        if ok:
            events.append(event)
        else:
            skipped += 1
    return events, skipped


def week_of(text: str | None) -> tuple[int, int]:
    if text is None:
        year, week, _ = datetime.now(UTC).isocalendar()
        return year, week
    found = WEEK.fullmatch(text)
    try:
        if found is None:
            raise ValueError
        date.fromisocalendar(int(found[1]), int(found[2]), 1)
    except ValueError as exc:
        raise CheckError("the week must have the form YYYY-Www (option: --week)") from exc
    return int(found[1]), int(found[2])


def descends(clone: Path, old: str, new: str) -> bool:
    """A later head of the same branch: NEW is not OLD and OLD is its ancestor; no fetch."""
    return old != new and _git(clone, "merge-base", "--is-ancestor", old, new).returncode == 0


def report(clone: Path, sidecar: Path, week: str | None) -> str:
    """Rule 23, first measure: defects caught before push by the floor, for one ISO week."""
    year, number = week_of(week)
    events, skipped = read_events(sidecar)
    floors = [e for e in events if e["step"] == "floor"]
    in_week = [e for e in floors if tuple(e["at"].isocalendar())[:2] == (year, number)]
    if len(in_week) < 2:
        caught = "unknown"
    else:
        failed = {e["head"]: e["at"] for e in in_week if e["result"] == "failed"}
        passes = [e for e in floors if e["result"] == "passed"]
        caught = str(
            sum(
                any(p["at"] >= at and descends(clone, head, p["head"]) for p in passes)
                for head, at in failed.items()
            )
        )
    lines = [f"report: defects caught before push: {caught} (floor)"]
    if skipped:
        lines.append(f"report: skipped {skipped} unreadable event lines")
    for name in ("review findings accepted", "rework", "time per change"):
        lines.append(f"report: {name}: unknown ({SECOND_PART})")
    lines.append("report: baseline: unknown (the attach time is not recorded)")
    lines.extend(f"report: pushed without a gate: {name}" for name in ungated(clone, sidecar))
    lines.append(CAUTION)
    return "\n".join(lines)


GATES = "records/gates"
REVIEWS = "records/reviews"
LEVELS = ("light", "tests-first", "spec", "review", "evidence")
LEVEL_SETTING = "personal.level"
TEAM_REFS = "personal.team_refs"
LAYOUT = (  # SPEC-0041 rule 2: the sidecar's own paths, which a product commit should not carry
    "agk.toml", "constitution/", "config/", "docs/requirements.md", "docs/specs/", "docs/adr/",
    "docs/briefs/", "docs/runs/decisions-log.md", "forge/", "records/", "metrics/",
    "test-map.toml", "cache/",
)  # fmt: skip
APPROVED_SPEC = re.compile(r"Approve: [0-9a-f]{40} SPEC-(\d{4})")


def ungated(clone: Path, sidecar: Path) -> list[str]:
    """Rule 19: each local branch whose head equals its upstream's remote-tracking ref, read
    without a fetch, and that has no gate record."""
    fmt = "--format=%(refname:short)%00%(objectname)%00%(upstream)"
    rows = _git(clone, "for-each-ref", fmt, "refs/heads").stdout.decode("utf-8", "replace")
    found = []
    for row in rows.splitlines():
        name, sha, upstream = (row.split("\0") + ["", ""])[:3]
        if not upstream:
            continue
        pushed = _git(clone, "rev-parse", "--verify", "-q", f"{upstream}^{{commit}}")
        same = pushed.returncode == 0 and pushed.stdout.decode("ascii").strip() == sha
        if same and not (sidecar / GATES / f"{sha}.json").is_file():
            found.append(name)
    return found


def branch_commits(clone: Path, base: str, head: str) -> list[str]:
    """The branch's own commits, oldest first."""
    done = _git(clone, "rev-list", "--reverse", f"{base}..{head}")
    return done.stdout.decode("ascii").split() if done.returncode == 0 else []


def team_ref_warnings(clone: Path, base: str, head: str, table: dict) -> list[str]:
    """Rule 20: with `team_refs` off, one warning per commit that carries an `Advances:` line or
    a path of the sidecar layout; the warning names the setting, never the line or the path."""
    if table.get("team_refs") is True:
        return []
    found = []
    for sha in branch_commits(clone, base, head):
        message = _git(clone, "show", "-s", "--format=%B", sha).stdout.decode("utf-8", "replace")
        if any(line.startswith("Advances:") for line in message.splitlines()):
            found.append(f"gate: warning: commit {sha[:12]} carries an Advances: line "
                         f"(setting: {TEAM_REFS})")  # fmt: skip
        listed = _git(clone, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", sha)
        paths = [p for p in listed.stdout.decode("utf-8", "replace").split("\0") if p]
        if any(p == x or (x.endswith("/") and p.startswith(x)) for p in paths for x in LAYOUT):
            found.append(f"gate: warning: commit {sha[:12]} carries a path of the sidecar layout "
                         f"(setting: {TEAM_REFS})")  # fmt: skip
    return found


def failed(step: str, why: str) -> tuple[bool, str]:
    return False, f"gate: {step} FAIL: {why} (setting: {LEVEL_SETTING})"


def proof_step(command: str, clone: Path, sidecar: Path, base: str, runs: dict, head: str):
    """`tests-first`: the branch's test files on the base tree, then `proof.decide` (SPEC-0010)."""
    from proof import decide, place_tests  # noqa: PLC0415 - the `tests-first` level only

    listed = _git(clone, "diff", "-z", "--name-status", "--no-renames", base, head)
    tokens = listed.stdout.decode("utf-8", "surrogateescape").split("\0")
    changed = {tokens[i + 1]: tokens[i][:1] for i in range(0, len(tokens) - 1, 2)}
    tests = {row["path"] for row in detect_test_files(changed)}
    files = {path: status for path, status in changed.items() if path in tests}
    if not any(status != "D" for status in files.values()):
        return failed("tests-first", "the change adds or changes no test file")
    tree = write_tree(clone, base, sidecar, f"proof-{base}")
    place_tests(clone, tree, files, head)
    red = run_once(command, tree, sidecar, "cache/proof-base-junit.xml")
    code = {"passed": 0, "failed": 1}
    outcome, reason = decide(code[red["run"]], code[runs["head"]["run"]])
    if outcome == "proven":
        return True, "gate: tests-first ok (red on the base, green on the head)"
    return failed("tests-first", str(reason))


def sidecar_comments(sidecar: Path) -> list[dict]:
    """Every comment of the files forge; a file that cannot be read gives none."""
    found: list[dict] = []
    for path in sorted((sidecar / "forge").glob("comments-*.json")):
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(items, list):
            found.extend(x for x in items if isinstance(x, dict))
    return found


def spec_status(sidecar: Path, number: str) -> str | None:
    paths = sorted((sidecar / "docs" / "specs").glob(f"{number}-*.md"))
    if len(paths) != 1:
        return None
    lines = paths[0].read_text(encoding="utf-8").splitlines()
    return next((m[1] for x in lines if (m := STATUS_LINE.match(x))), None)


def spec_step(clone: Path, sidecar: Path, base: str, head: str) -> tuple[bool, str]:
    """`spec`: a spec of the sidecar, Approved and confirmed at a terminal (ADR-0632) before the
    committer time of the branch's first commit."""
    from common import agent_apps  # noqa: PLC0415 - the `spec` level only
    from reviewers import derived_only, solo_person  # noqa: PLC0415

    commits = branch_commits(clone, base, head)
    if not commits:
        return failed("spec", "the branch has no commit of its own")
    shown = _git(clone, "show", "-s", "--format=%ct", commits[0]).stdout.decode("ascii").strip()
    first = datetime.fromtimestamp(int(shown or "0"), UTC)
    items = derived_only(sidecar_comments(sidecar), agent_apps(sidecar), solo_person(sidecar))
    for item in items:
        found = APPROVED_SPEC.fullmatch(str(item.get("body") or ""))
        try:
            at = datetime.strptime(str(item.get("created_at")), STAMP).replace(tzinfo=UTC)
        except ValueError:
            continue
        if found and at <= first and spec_status(sidecar, found[1]) == "Approved":
            return True, f"gate: spec ok (SPEC-{found[1]} confirmed before the first commit)"
    return failed("spec", "no spec confirmed at a terminal before the change's first commit")


def review_step(sidecar: Path, head: str) -> tuple[bool, str]:
    """`review`: the context and the reviewer report of the head, `check_review_report` unchanged,
    and the person's verdict at a terminal naming the head (advisory in what it finds, rule 17)."""
    try:
        # kit-only, guarded: an experimental file (kit/manifest.json), absent from a default install
        from check_review_report import Context, parse_report, validate  # noqa: PLC0415 - kit-only
    except ImportError:
        return failed("review", "the reviewer report check is not installed "
                      "(path: scripts/agk/check_review_report.py)")  # fmt: skip
    from common import agent_apps  # noqa: PLC0415
    from reviewers import TERMINAL_BY, login_of, solo_person, via_agent  # noqa: PLC0415

    context, report_file = (sidecar / REVIEWS / f"{head}.{x}.md" for x in ("context", "report"))
    if not context.is_file() or not report_file.is_file():
        return failed("review", f"no review context and report for the head (path: {REVIEWS})")
    problems = validate(
        Context(context.read_text(encoding="utf-8")),
        parse_report(report_file.read_text(encoding="utf-8")),
    )
    if problems:
        return failed("review", f"the reviewer report does not hold: {problems[0]}")
    person = (solo_person(sidecar) or "").lstrip("@").lower()
    apps = agent_apps(sidecar)
    for item in sidecar_comments(sidecar):
        lines = [x.strip() for x in str(item.get("body") or "").strip().splitlines()]
        if not person or via_agent(item, apps) or login_of(item) != person or len(lines) < 3:
            continue
        signed = TERMINAL_BY.fullmatch(lines[-1])
        named = lines[:2] == [f"Confirmed: {head}", f"Verdict: cleared {head}"]
        if named and signed and signed[1].lower() == person:
            return True, "gate: review ok (the report holds; the person's verdict names the head)"
    return failed("review", "no verdict confirmed at a terminal names the head")


def step_entry(name: str, ok: bool, line: str, seconds: float) -> dict:
    """One step as `prepush.py --record` writes it (ADR-0208); the gate runs no single argv."""
    from prepush import digest  # noqa: PLC0415

    entry: dict = {"name": name, "outcome": "ok" if ok else "FAIL", "not_run": None, "argv": []}
    entry.update(cwd=".", exit=None, seconds=round(seconds, 3), **digest(line))
    return entry


def evidence_step(path: Path, head: str) -> tuple[bool, str]:
    """`evidence`: the written record read back by `evidence.parse` and `evidence.problems`."""
    import evidence  # noqa: PLC0415 - the `evidence` level only

    try:
        record, _ = evidence.parse(path.read_bytes())
    except (OSError, evidence.Usage) as exc:
        return failed("evidence", f"the record cannot be read ({exc})")
    found = evidence.problems(record, head)
    if found:
        return failed("evidence", "; ".join(found))
    return True, "gate: evidence ok (the record agrees with the head)"


def push_line(clone: Path) -> str:
    """The command the developer runs; the gate runs none (rule 20)."""
    branch = _git(clone, "symbolic-ref", "--short", "-q", "HEAD").stdout.decode().strip()
    remote = _git(clone, "config", "--get", f"branch.{branch}.remote").stdout.decode().strip()
    target = f"{remote or 'origin'} {branch or 'HEAD:<branch>'}"
    return f"gate: the agent pushes nothing; push it yourself: git push {target}"


def gate(clone: Path, sidecar: Path, ref: str | None, approve: bool) -> tuple[bool, str]:
    """Rules 17 to 20: the floor, the steps of the level, the record, the events, one commit."""
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    command, level = test_command(sidecar), table["level"]
    head, base = head_of(clone), merge_base(clone, ref)
    lines = [f"gate: level {level}, base {base[:12]}, head {head[:12]}"]
    lines.extend(team_ref_warnings(clone, base, head, table))
    if not approve:
        lines.append(f"gate: nothing ran: would run {command} on the base and head trees and the "
                     f"steps of level {level}; run again with --approve")  # fmt: skip
        return False, "\n".join(lines)
    import prepush  # noqa: PLC0415

    record = {"schema": prepush.SCHEMA, "head": head, "base": base, "level": level}
    record.update(started=datetime.now(UTC).strftime(STAMP), steps=[], notes=[])
    record["tree_clean"] = _git(clone, "status", "--porcelain").stdout.strip() == b""
    record["versions"] = prepush.versions(clone)
    runs: dict = {}
    rank = LEVELS.index(level)
    steps = [
        ("secret-scan", lambda: scan_step(clone, base)),
        ("no-regression", lambda: regression_step(command, clone, sidecar, base, head, runs)),
        ("tests-first", lambda: proof_step(command, clone, sidecar, base, runs, head)),
        ("spec", lambda: spec_step(clone, sidecar, base, head)),
        ("review", lambda: review_step(sidecar, head)),
    ][: 2 + min(rank, 3)]
    results: dict[str, bool] = {}
    for name, step in steps:
        started = datetime.now(UTC)
        ok, line = step()
        lines.append(line)
        results[name] = ok
        seconds = (datetime.now(UTC) - started).total_seconds()
        record["steps"].append(step_entry(name, ok, line, seconds))
    path = sidecar / GATES / f"{head}.json"
    record["result"] = "passed" if all(results.values()) else "failed"
    write_private(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
    if rank == LEVELS.index("evidence"):
        ok, line = evidence_step(path, head)
        lines.append(line)
        results["evidence"] = ok
        record["steps"].append(step_entry("evidence", ok, line, 0.0))
        record["result"] = "passed" if all(results.values()) else "failed"
        write_private(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
    passed = record["result"] == "passed"
    events = [("floor", results["secret-scan"] and results["no-regression"])]
    events += [(n, ok) for n, ok in results.items() if n not in ("secret-scan", "no-regression")]
    for name, ok in [*events, ("gate", passed)]:
        lines.extend(append_event(sidecar, head, name, "passed" if ok else "failed"))
    lines.extend(commit_gate(sidecar, head))
    lines.append("gate: passed" if passed else "gate: failed")
    if passed:
        lines.append(push_line(clone))
    return passed, "\n".join(lines)


def commit_gate(sidecar: Path, head: str) -> list[str]:
    """One sidecar commit of the record and the events; a failure is one line, never a loss."""
    from reviewers import solo_person  # noqa: PLC0415

    paths = [f"{GATES}/{head}.json", EVENTS]
    added = _sidecar_git(sidecar, "add", "--", *paths)
    options = commit_options(sidecar, solo_person(sidecar) or "personal")
    done = None
    if added.returncode == 0:
        done = _sidecar_git(sidecar, *options, "-m", f"personal: gate {head[:12]}", "--", *paths)
    if done is None or done.returncode != 0:
        return [f"gate: the record is written but not committed (path: {GATES})"]
    return []


RECORD_ID = re.compile(r"(SPEC-(\d{4})|ADR-(\d{4})|REQ-\d{3})")
MOVES = {"SPEC": ("Draft", "Approved"), "ADR": ("Proposed", "Accepted")}
READERS = {"SPEC": "check_specs", "ADR": "check_adrs", "REQ": "check_requirements"}
WORDS = {"SPEC": "Approve", "ADR": "Accept", "REQ": "Confirm"}
MOVED = "the sidecar's head moved while confirming; nothing written (SPEC-0041 rule 8)"
PROVES = (
    "A confirmation typed by the person at their own terminal (SPEC-0041 rules 8 and 15). It "
    "proves that the yes was typed at a terminal with no agent session's mark, and nothing more."
)


def _sidecar_git(sidecar: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed git argument list, no shell
        ["git", *args], cwd=sidecar, capture_output=True, text=True, encoding="utf-8", check=False
    )


def record_of(sidecar: Path, rid: str) -> tuple[str, str, str]:
    """(path, title, status) of a record of the sidecar, else refused naming the rule."""
    found = RECORD_ID.fullmatch(rid)
    if found is None:
        raise CheckError("name a record as REQ-nnn, SPEC-nnnn or ADR-nnnn (SPEC-0041 rule 15)")
    kind = rid.split("-")[0]
    if kind == "REQ":
        rel = "docs/requirements.md"
        text = (sidecar / rel).read_text(encoding="utf-8") if (sidecar / rel).is_file() else ""
        reqs = [r for r in parse_requirements(text) if r["id"] == rid]
        if len(reqs) != 1 or reqs[0]["status_count"] != 1:
            raise CheckError("no such record in the sidecar (SPEC-0041 rule 15)")
        return rel, reqs[0]["title"] or "", reqs[0]["status"]
    folder = "specs" if kind == "SPEC" else "adr"
    paths = sorted((sidecar / "docs" / folder).glob(f"{found[2] or found[3]}-*.md"))
    if len(paths) != 1:
        raise CheckError("no such record in the sidecar (SPEC-0041 rule 15)")
    lines = paths[0].read_text(encoding="utf-8").splitlines()
    title = lines[0].split(": ", 1)[1] if lines and ": " in lines[0] else ""
    status = next((m[1] for x in lines if (m := STATUS_LINE.match(x))), None)
    if status != MOVES[kind][0]:
        raise CheckError(f"only a {MOVES[kind][0]} record can be confirmed (SPEC-0041 rule 15)")
    return paths[0].relative_to(sidecar).as_posix(), title, status


def shown_lines(rid: str, rel: str, title: str, status: str, head: str) -> list[str]:
    """The three lines the person is shown, which the confirmation's `Shown:` lines record."""
    kind = rid.split("-")[0]
    if kind == "REQ":
        move = f"status: {status}, unchanged (the confirmation lets it move to done, rule 14)"
    else:
        move = f"status: {MOVES[kind][0]} -> {MOVES[kind][1]}"
    return [f"{rid}: {title}", f"{rel} at {head}", move]


def confirmation_body(head: str, rid: str, shown: list[str], login: str, at: str) -> str:
    """Rule 8's shape, in order, one item per line."""
    word = WORDS[rid.split("-")[0]]
    return "\n".join(
        [f"Confirmed: {head}", f"Verdict: cleared {head}", f"Record: {rid}", f"{word}: {rid}"]
        + ["Shown:", *shown, f"confirmed by {login} at a terminal at {at}"]
    )


def commit_options(sidecar: Path, person: str) -> list[str]:
    """Signed with the person's own key and git identity only with `[personal] sign = true`
    (off by default); unsigned, the commit takes the files forge's identity, as its writes do."""
    if (personal_table(sidecar) or {}).get("sign") is True:
        return ["commit", "-q", "--no-verify", "-S"]
    identity = ["-c", f"user.name={person}", "-c", f"user.email={person}@personal.invalid"]
    return [*identity, "-c", "commit.gpgsign=false", "commit", "-q", "--no-verify"]


def place(path: Path, value) -> None:
    """One forge file: a temporary file and a rename, as the files forge writes."""
    from forge import dump  # noqa: PLC0415 - `confirm` only

    path.parent.mkdir(mode=0o700, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix="tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(dump(value))
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def move_status(path: Path, old: str, new: str) -> str:
    """Rewrite the first `- Status:` line (read by `STATUS_LINE`, as `record_of` reads it) from
    OLD to `- Status: NEW`, its line ending kept; the text before. Refused when nothing moved."""
    with open(path, encoding="utf-8", newline="") as handle:  # each line ending as it is
        text = handle.read()
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        bare = line.rstrip("\r\n")
        found = STATUS_LINE.match(bare)
        if found:
            if found.group(1) == old:
                lines[i] = f"- Status: {new}{line[len(bare) :]}"
            break
    if "".join(lines) == text:
        raise CheckError(f"the status line did not move to {new} (SPEC-0041 rule 15)")
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return text


def head_of_sidecar(sidecar: Path) -> str:
    return _sidecar_git(sidecar, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()


def confirm(sidecar: Path, rid: str, ask=input, tty=None, env=None) -> tuple[int, list[str]]:
    """Rule 15: the person's yes at a terminal, read by the kind's reader before one commit."""
    try:
        return _confirm(sidecar, rid, ask, tty, env)
    except CheckError as exc:
        return 1, [f"refused: {exc}"]


def _confirm(sidecar: Path, rid: str, ask, tty, env) -> tuple[int, list[str]]:
    """The forge's lock is held from reading `<C>` to the commit, and `HEAD` is read again after
    the yes and before the commit: a commit made meanwhile is refused and never thrown away."""
    from forge import FilesForge  # noqa: PLC0415 - `confirm` only
    from local_mode import SESSION_SETTING  # noqa: PLC0415

    env = os.environ if env is None else env
    if env.get(SESSION_SETTING):
        raise CheckError(f"confirm runs only at the person's terminal (setting: {SESSION_SETTING})")
    if not (os.isatty(0) if tty is None else tty()):
        raise CheckError("confirm needs a terminal on standard input (SPEC-0041 rule 15)")
    files = FilesForge(sidecar, env=env)
    with files.locked():
        state = _sidecar_git(sidecar, "status", "--porcelain")
        head = head_of_sidecar(sidecar)
        if state.returncode != 0 or state.stdout.strip() or not re.fullmatch(r"[0-9a-f]{40}", head):
            raise CheckError(
                "confirm needs a clean sidecar work tree at a commit (SPEC-0041 rule 8)"
            )
        rel, title, status = record_of(sidecar, rid)
        shown = shown_lines(rid, rel, title, status, head)
        answer = ask("\n".join([*shown, f"confirm {rid}? [yes/no] "]))
        if answer.strip().lower() not in ("y", "yes"):
            return 1, [*shown, f"confirm: nothing written for {rid}"]
        if head_of_sidecar(sidecar) != head:
            raise CheckError(MOVED)
        return _write(sidecar, files, rid, rel, shown, head)


def _write(sidecar: Path, files, rid: str, rel: str, shown: list[str], head: str):
    """The two forge files and the status line, the reader, then one commit or a restore."""
    kind = rid.split("-")[0]
    branch = _sidecar_git(sidecar, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or "main"
    number = files.next_number()
    pull = files.base_record(number, f"confirm {rid}", PROVES)
    pull.update(draft=False, merged=False, merged_at=None)
    pull.update(head={"sha": head, "ref": branch}, base={"ref": branch})
    at = files.now()
    body = confirmation_body(head, rid, shown, files.person, at)
    entry = {"id": number * 1_000_000 + 1, "body": body, "user": {"login": files.person}}
    entry.update(created_at=at, updated_at=at, performed_via_github_app=None)
    paths = [f"forge/pulls/{number}.json", f"forge/comments-{number}.json"]
    place(sidecar / paths[0], pull)
    place(sidecar / paths[1], [entry])
    before = None
    try:
        if kind in MOVES:
            before = move_status(sidecar / rel, *MOVES[kind])
            paths.append(rel)
    except CheckError:
        for rel_path in paths[:2]:
            (sidecar / rel_path).unlink(missing_ok=True)
        raise
    reader = READERS[kind]
    script = Path(__file__).resolve().parent / f"{reader}.py"
    check = subprocess.run(  # nosec B603 - the kit's own reader, fixed argument list, no shell
        [sys.executable, str(script), "--base", head, "--comments", paths[1]],
        cwd=sidecar, capture_output=True, text=True, encoding="utf-8", check=False,
    )  # fmt: skip
    same = head_of_sidecar(sidecar) == head
    done = None
    if check.returncode == 0 and same:
        _sidecar_git(sidecar, "add", "--", *paths)
        options = commit_options(sidecar, files.person)
        done = _sidecar_git(sidecar, *options, "-m", f"personal: confirm {rid}", "--", *paths)
    if done is not None and done.returncode == 0:
        return 0, [*shown, f"confirm: {rid} confirmed at a terminal in pull {number}"]
    if same:
        _sidecar_git(sidecar, "reset", "-q", "--hard", head)
    elif before is not None:  # another commit landed: undo only this command's writes
        (sidecar / rel).write_text(before, encoding="utf-8", newline="")
    for rel_path in paths[:2]:
        (sidecar / rel_path).unlink(missing_ok=True)
    if not same:
        raise CheckError(MOVED)
    why = f"the reader {reader} failed" if done is None else "the sidecar commit failed"
    said = [x for x in check.stdout.splitlines() if x.startswith("FAIL ")]
    return 1, [*shown, *said, f"confirm: {why}; nothing committed, the sidecar is at {head}"]


def parse(args: list[str]) -> dict | None:
    if args and args[0] == "confirm":
        return parse_confirm(args[1:])
    if not args or args[0] not in ("baseline", "floor", "gate", "report"):
        return None
    out: dict = {"command": args.pop(0), "clone": ".", "sidecar": None, "base": None}
    out["week"] = None
    out["approve"] = False
    while args:
        flag = args.pop(0)
        if flag == "--approve" and out["command"] != "report":
            out["approve"] = True
        elif flag == "--base" and args and out["command"] in ("floor", "gate"):
            out["base"] = args.pop(0)
        elif flag == "--week" and args and out["command"] == "report":
            out["week"] = args.pop(0)
        elif flag in ("--clone", "--sidecar") and args:
            out[flag[2:]] = args.pop(0)
        else:
            return None
    return out


def parse_confirm(args: list[str]) -> dict | None:
    out: dict = {"command": "confirm", "clone": ".", "sidecar": None, "record": None}
    while args:
        flag = args.pop(0)
        if flag in ("--clone", "--sidecar") and args:
            out[flag[2:]] = args.pop(0)
        elif not flag.startswith("-") and out["record"] is None:
            out["record"] = flag
        else:
            return None
    return out if out["record"] else None


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        if options["command"] == "confirm" and options["sidecar"]:  # the clone is not read
            code, lines = confirm(Path(options["sidecar"]), options["record"])
            print("\n".join(lines))
            return code
        probe = _git(Path(options["clone"]), "rev-parse", "--show-toplevel")
        if probe.returncode != 0:
            raise CheckError("the clone cannot be read as a git repository (option: --clone)")
        clone = Path(probe.stdout.decode("utf-8", "surrogateescape").strip())
        sidecar = Path(options["sidecar"]) if options["sidecar"] else find_sidecar(clone)
        if options["command"] == "baseline":
            print(baseline(clone, sidecar, options["approve"]))
            return 0
        if options["command"] == "confirm":
            code, lines = confirm(sidecar, options["record"])
            print("\n".join(lines))
            return code
        if options["command"] == "report":
            print(report(clone, sidecar, options["week"]))
            return 0
        run = gate if options["command"] == "gate" else floor
        passed, text = run(clone, sidecar, options["base"], options["approve"])
        print(text)
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
