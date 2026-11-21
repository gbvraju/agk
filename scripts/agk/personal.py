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
    python3 personal.py pr-summary [--clone DIR] [--sidecar DIR]
    python3 personal.py status [--clone DIR] [--sidecar DIR]
    python3 personal.py upgrade [--clone DIR] [--sidecar DIR]
    python3 personal.py hook install|remove [--clone DIR]
    python3 personal.py export --target CLONE [--write] [--branch NAME] [--with-notes]
    python3 personal.py export --check [--clone DIR] [--sidecar DIR]

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
`unknown`, never a pass. No setting changes a step; it exits 0 only when both pass. With
`--approve`, after the secret scan, `run_gates.py`'s gates run on the head tree, files only and
with no forge call, at every level; a red gate fails the floor (SPEC-0072 rule 11; brief #1601).

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

`pr-summary` (build (j), rules 21 and 22, brief #1505) prints, and never posts, what the gate
record of the head says: the secret scan, the tests, the proof where the level ran it and whether
a review was done, with no REQ, SPEC or ADR id unless `team_refs = true`; with no record it says
so and invents nothing. It and `status` print the disclosure in force; with `ai_disclosure`
`pr-note` or `both` the summary ends with the disclosure line, and with `commit-trailer` or `both`
the gate warns of each branch commit without a `Co-Authored-By:` trailer. Nothing amends, rewrites
or strips a trailer or a commit.

`change start|review|confirm|finish` (build (i), rules 17 and 29, brief #1507) takes one change
through the level's steps: `start` records the files-forge pull of the branch (refused on the
default branch) and, at `spec` and above, drafts the change's spec; `review` writes the context for
the read-only `personal-reviewer` agent and, with `--report`, keeps the report that
`check_review_report` accepts, as a comment marked as an agent's; `confirm` is the person's
`Verdict: cleared <head>` at a terminal; `finish` runs the gate and prints, never runs, the push.

`upgrade` (build (l), rule 27, brief #1506) raises `[personal] schema` one step at a time to the
plugin's `personal_state.PLUGIN_SCHEMA`, each step its own sidecar commit; it refuses a schema newer
than the plugin's, a sidecar with uncommitted changes and a missing step. `hook install|remove`
(rule 19) writes or removes the opt-in `pre-push` hook that runs `gate --approve`, the one write
under the clone's `.git/`; both are in `personal_state.py`, which a project install does not hold.

`export` (build (m), rules 24 and 25, brief #1508) takes the sidecar's records to a target clone.
Without `--write` it prints the mapping and writes nothing. With it, on a new branch of the target
from its default branch (`--branch`, default `agk/personal-export`; the default branch is refused):
the `adopt.build_plan` files when AGK is not installed there, the requirements, specs, ADRs, open
briefs and decisions-log rows renumbered in one pass (`intake.rewritten`) from the first free ids
(`common.next_free_ids` on the base, or counted over the plan), statuses reset to `planned`,
`Draft` and `Proposed`, each requirement, spec and ADR ending `confirmed by <person> in personal
mode on <date>` when the person confirmed it at a terminal, else `drafted in personal mode, not
confirmed`; and `docs/runs/export-map.json`. A second branch `<branch>-tests` proposes the test map
as `REQ-n ACm` comment markers above each named test. Field notes (`records/notes/`) are withheld
unless `--with-notes`; a record that `guard.scan_text` flags is refused before anything is written,
naming the path class. `gh issue create` is printed for each open brief and never run; nothing is
pushed, the target's checkout is restored and the map is kept as `records/export-map.json` with one
sidecar commit. `export --check` fails unless every record is in that map, mapped or withheld with
a reason, naming the count and the first unmapped id.
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
import tomllib
import xml.parsers.expat
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import run_gates  # noqa: E402  # SPEC-0072 rule 11 (brief #1601): the floor runs the gates
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
    "       personal.py confirm <REQ-nnn|SPEC-nnnn|ADR-nnnn> [--clone DIR] [--sidecar DIR]\n"
    "       personal.py pr-summary|status [--clone DIR] [--sidecar DIR]\n"
    "       personal.py upgrade [--clone DIR] [--sidecar DIR] | hook install|remove [--clone DIR]\n"
    "       personal.py change start <name> [--advances REQ-nnn] [--base REF] | "
    "review [--report FILE] [--base REF] | confirm | finish [--base REF] [--approve]\n"
    "       personal.py export --target CLONE [--write] [--branch NAME] [--with-notes] | "
    "export --check\n"
    "       (each with [--clone DIR] [--sidecar DIR])"
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


GATES_NOT_RUN = (
    "floor: gates not run: would run the gate runner on the head tree; run again with --approve"
)


def gates_step(clone: Path, sidecar: Path, head: str) -> tuple[bool, str]:
    """SPEC-0072 rule 11 (brief #1601, ADR-0681): `run_gates.py` on the head tree after the secret
    scan, at every level; files only, no command, no forge call."""
    rows = run_gates.results(write_tree(clone, head, sidecar, "floor-gates"))
    failed = [line for ok, line in rows if ok is False]
    if failed:
        return False, "floor: gates FAIL: " + "; ".join(failed)
    return True, f"floor: gates ok ({len([r for r in rows if r[0] != run_gates.NOTE])} check gates)"


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
    gated, line = gates_step(clone, sidecar, head) if approve else (False, GATES_NOT_RUN)
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
    passed = scanned and gated and tested
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


DISCLOSURE = "personal.ai_disclosure"
DISCLOSURE_LINE = "This change was made with the help of an AI coding assistant."
TRAILER_KEY = "Co-Authored-By"


def trailer_warnings(clone: Path, base: str, head: str, table: dict) -> list[str]:
    """Rule 22: with `commit-trailer` or `both`, one warning per commit of the branch whose
    message has no `Co-Authored-By:` trailer (git's own trailer reading); nothing is changed."""
    if table["ai_disclosure"] not in ("commit-trailer", "both"):
        return []
    found = []
    for sha in branch_commits(clone, base, head):
        shown = _git(clone, "show", "-s", f"--format=%(trailers:key={TRAILER_KEY},valueonly)", sha)
        if not shown.stdout.strip():
            found.append(
                f"gate: warning: commit {sha[:12]} has no {TRAILER_KEY} trailer; if an agent "
                f"session made it, add the trailer yourself (setting: {DISCLOSURE})"
            )
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
    lines.extend(trailer_warnings(clone, base, head, table))
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


TEAM_IDS = re.compile(r"\s*\b(?:REQ-\d{3}|SPEC-\d{4}|ADR-\d{4})\b")
SUMMARY_STEPS = {
    "secret-scan": "Secret scan",
    "no-regression": "No test that passed before fails now",
    "tests-first": "Tests written first",
    "review": "Review",
}


def disclosure_in_force(table: dict) -> str:
    return f"Disclosure in force: {table['ai_disclosure']} (setting: {DISCLOSURE})"


def status(sidecar: Path) -> str:
    """Rule 22: the settings in force, the disclosure among them; a bad value is refused."""
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    return (f"personal mode: forge {table['forge']}, level {table['level']}, "
            f"disclosure {table['ai_disclosure']}\n{disclosure_in_force(table)}")  # fmt: skip


def summary_lines(record: dict) -> list[str]:
    """What the record's steps say, in plain words; a step the level did not run is said so."""
    steps = record.get("steps")
    steps = steps if isinstance(steps, list) else []
    outcome = {}
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("name"), str):
            outcome[step["name"]] = "passed" if step.get("outcome") == "ok" else "failed"
    lines = [f"{SUMMARY_STEPS[n]}: {outcome[n]}" for n in ("secret-scan", "no-regression")
             if n in outcome]  # fmt: skip
    proof = outcome.get("tests-first")
    if proof is None:
        lines.append("Tests written first: not run at this level")
    else:
        why = " (red before the change, green after)" if proof == "passed" else ""
        lines.append(f"Tests written first: {proof}{why}")
    review = outcome.get("review")
    lines.append("Review: not done at this level" if review is None else f"Review: done ({review})")
    lines.extend(f"Step {n}: {r}" for n, r in outcome.items() if n not in SUMMARY_STEPS)
    level, result = record.get("level"), record.get("result")
    lines.append(f"Gate: {result} at level {level} on {str(record.get('head'))[:12]}")
    return lines


def pr_summary(clone: Path, sidecar: Path) -> tuple[bool, str]:
    """Rule 21: printed for the developer to paste; it posts and writes nothing."""
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    head = head_of(clone)
    lines = ["pr-summary: for you to paste into the team's pull request; nothing is posted"]
    lines.append(disclosure_in_force(table))
    path = sidecar / GATES / f"{head}.json"
    found = path.is_file()
    if not found:
        lines.append(f"pr-summary: no gate record for the head {head[:12]}; run the gate first, "
                     f"no result is shown (path: {GATES})")  # fmt: skip
    else:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CheckError(f"the gate record cannot be read (path: {GATES})") from exc
        if not isinstance(record, dict):
            raise CheckError(f"the gate record cannot be read (path: {GATES})")
        lines.extend(summary_lines(record))
    if table.get("team_refs") is not True:
        lines = [TEAM_IDS.sub("", line) for line in lines]
    if table["ai_disclosure"] in ("pr-note", "both"):
        lines.append(DISCLOSURE_LINE)
    return found, "\n".join(lines)


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


CHANGE_RULE = "SPEC-0041 rule 17"
BRANCH_RULE = "SPEC-0041 rule 6"
CHANGE_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
NO_CHANGE = (
    f"no change is started on this branch; run personal.py change start <name> ({CHANGE_RULE})"
)
REVIEWER = "personal-reviewer"
CONTEXT_SCRIPT = "scripts/agk/review_context.py"
NO_REPORT_CHECK = (
    "the reviewer report check is not installed (path: scripts/agk/check_review_report.py)"
)
SPEC_DRAFT = """# SPEC-{number}: {name} (verify: say what the change does)

- Status: Draft
- Owner: reviewer group (the one person of config/reviewers.yaml)
- Requirements: {advances}

The change `{name}` on the branch `{branch}`. (verify) Write what it does and how a test shows
it, then confirm this spec at your own terminal before the change's first code commit.

## Contexts

- personal: the sidecar holds this spec and the change's records
- kit, github, local, stacks: not applicable: a change of the product, recorded in the sidecar
"""


def current_branch(clone: Path) -> str:
    branch = _git(clone, "symbolic-ref", "--short", "-q", "HEAD").stdout.decode().strip()
    if not branch:
        raise CheckError(f"a change needs a branch, not a detached head ({BRANCH_RULE})")
    return branch


def default_branch(clone: Path, ref: str | None) -> str:
    """The default branch's name: REF, else `refs/remotes/origin/HEAD` read without a fetch."""
    if ref:
        return ref.removeprefix("origin/")
    found = _git(clone, "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD")
    name = found.stdout.decode().strip()
    if found.returncode != 0 or "/" not in name:
        raise CheckError("no default branch is known (option: --base)")
    return name.split("/", 1)[1]


def change_of(sidecar: Path, branch: str) -> dict | None:
    """The newest open pull record titled `change <name>` whose head is BRANCH."""
    found = None
    for path in sorted(
        (sidecar / "forge" / "pulls").glob("[0-9]*.json"), key=lambda p: int(p.stem)
    ):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        title = str(record.get("title") or "")
        ref = (record.get("head") or {}).get("ref")
        if record.get("state") == "open" and title.startswith("change ") and ref == branch:
            found = record
    return found


def started(clone: Path, sidecar: Path) -> tuple[dict, str, dict]:
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    record = change_of(sidecar, current_branch(clone))
    if record is None:
        raise CheckError(NO_CHANGE)
    return record, head_of(clone), table


def commit_sidecar(sidecar: Path, subject: str, paths: list[str]) -> None:
    from reviewers import solo_person  # noqa: PLC0415

    added = _sidecar_git(sidecar, "add", "--", *paths)
    options = commit_options(sidecar, solo_person(sidecar) or "personal")
    done = (
        _sidecar_git(sidecar, *options, "-m", subject, "--", *paths)
        if added.returncode == 0
        else None
    )
    if done is None or done.returncode != 0:
        raise CheckError("the sidecar commit failed (path class: records)")


def change_start(clone: Path, sidecar: Path, name: str, ref: str | None, advances: str | None):
    """Answer 1: the files-forge pull of the branch and, at `spec` and above, the drafted spec."""
    from common import next_free_ids  # noqa: PLC0415
    from forge import FilesForge  # noqa: PLC0415

    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    if not CHANGE_NAME.fullmatch(name):
        raise CheckError(
            f"name the change in lower-case letters, digits and dashes ({CHANGE_RULE})"
        )
    if advances is not None and not re.fullmatch(r"REQ-\d{3}", advances):
        raise CheckError("name the requirement as REQ-nnn (option: --advances)")
    branch, base = current_branch(clone), default_branch(clone, ref)
    if branch == base:
        raise CheckError(f"a change never starts on the default branch ({BRANCH_RULE})")
    if change_of(sidecar, branch) is not None:
        raise CheckError(f"a change is already started on this branch ({CHANGE_RULE})")
    head = head_of(clone)
    lines, body = [], [f"Change: {name}", f"Branch: {branch}"]
    if advances:
        body.append(f"Advances: {advances}")
    if LEVELS.index(table["level"]) >= LEVELS.index("spec"):
        number = next_free_ids(sidecar, "HEAD")["spec"]
        rel = f"docs/specs/{number}-{name}.md"
        if (sidecar / rel).exists():
            raise CheckError(
                f"the change's spec already exists (path class: docs/specs, {CHANGE_RULE})"
            )
        text = SPEC_DRAFT.format(number=number, name=name, branch=branch,
                                 advances=advances or "(verify: name the requirement)")  # fmt: skip
        write_private(sidecar / rel, text)
        commit_sidecar(sidecar, f"personal: draft SPEC-{number} for change {name}", [rel])
        body.append(f"Spec: SPEC-{number}")
        lines.append(f"change: drafted SPEC-{number} in {rel}; write it, then confirm it "
                     "yourself at your terminal before the first code commit: "
                     f"personal.py confirm SPEC-{number}")  # fmt: skip
    pull = FilesForge(sidecar).record_pull(f"change {name}", "\n".join(body), head, branch, base)
    lines.insert(
        0, f"change: started {name} on {branch} (pull {pull}, base {base}, head {head[:12]})"
    )
    return 0, lines


def review_context(clone: Path, sidecar: Path, base: str, head: str, body: str) -> str:
    """Answer 2: the sections of `review_context.assemble`, the diff and the changed files from the
    clone (read-only, the head tree under the sidecar), the records from the sidecar."""
    try:
        # kit-only, guarded: an experimental file (kit/manifest.json), absent from a default install
        import review_context as rc  # noqa: PLC0415 - kit-only
    except ImportError:
        raise CheckError(
            f"the review context builder is not installed (path: {CONTEXT_SCRIPT})"
        ) from None
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"  # rule 4: `review_context`'s git reads lock nothing
    limits, other = rc.caps(sidecar), rc.caps(sidecar)["review_other_cap"]
    listed = _git(clone, "diff", "-z", "--name-status", "--no-renames", base, head)
    tokens = listed.stdout.decode("utf-8", "surrogateescape").split("\0")
    changed = {tokens[i + 1]: tokens[i][:1] for i in range(0, len(tokens) - 1, 2)}
    ids = rc.advanced(body)
    problems = [] if ids else ["the change has no `Advances:` line with a REQ id"]
    hunks = sorted(rc.tracked_hunks(clone, f"{base}..{head}"), key=lambda h: h.file)
    if not hunks:
        problems.append("the diff is empty")
    diff, cut_diff = rc.diff_section(hunks, limits["review_diff_cap"])
    req_text = rc.read_text(sidecar, rc.REQUIREMENTS)
    texts = rc.requirement_texts(req_text or "")
    problems += [f"{req} is not in {rc.REQUIREMENTS}" for req in ids if req not in texts]
    reqs, cut_reqs = rc.requirements_section(sidecar, ids, texts, other)
    docs, doc_problems = rc.referenced_docs(sidecar, body, ids, {})
    docs_lines, cut_docs = rc.documents_section(sidecar, docs, other)
    principles, cut_principles = rc.text_section(rc.read_text(sidecar, rc.PRINCIPLES), other)
    tree = write_tree(clone, head, sidecar, f"review-{head}")
    try:
        files_lines, cut_files = rc.changed_files_section(tree, changed, other)
    finally:
        shutil.rmtree(tree, ignore_errors=True)
    body_lines, cut_body = rc.text_section(body, other)
    cut = (cut_diff, cut_files, cut_reqs, cut_docs, cut_principles, cut_body)
    out = ["# Review context", "", f"Truncated: {'yes' if any(cut) else 'no'}", ""]
    for title, lines in (
        ("Context problems", [f"- {p}" for p in problems + doc_problems] or ["- none"]),
        ("PR body", body_lines),
        ("Diff", diff),
        ("Changed files", files_lines),
        ("Requirements", reqs),
        ("Protected classes touched", ["none (personal mode: the product's paths are the team's)"]),
        ("Referenced specs and ADRs", docs_lines),
        ("Principles", principles),
        ("Operating rules", ["none (personal mode: the sidecar holds the rules)"]),
    ):
        out += [f"## {title}", "", *lines, ""]
    return "\n".join(out)


def change_review(clone: Path, sidecar: Path, ref: str | None, report: str | None):
    """Answer 2: the context for the `personal-reviewer` agent, or its report checked and kept."""
    from forge import FilesForge  # noqa: PLC0415
    from local_mode import SESSION_SETTING  # noqa: PLC0415

    record, head, _ = started(clone, sidecar)
    context = f"{REVIEWS}/{head}.context.md"
    if report is None:
        base = merge_base(clone, ref)
        write_private(sidecar / context, review_context(clone, sidecar, base, head, record["body"]))
        commit_sidecar(sidecar, f"personal: review context {head[:12]}", [context])
        return 0, [f"review: the context of {head[:12]} is in {sidecar / context}",
                   f"review: ask the {REVIEWER} agent to review it, save its answer outside "
                   "the clone, then run: personal.py change review --report FILE"]  # fmt: skip
    try:
        # kit-only, guarded: an experimental file (kit/manifest.json), absent from a default install
        from check_review_report import Context, parse_report, validate  # noqa: PLC0415 - kit-only
    except ImportError:
        raise CheckError(NO_REPORT_CHECK) from None
    if not (sidecar / context).is_file():
        raise CheckError(
            f"no review context for the head; run personal.py change review ({CHANGE_RULE})"
        )
    try:
        text = Path(report).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the report cannot be read (option: --report)") from exc
    parsed = parse_report(text)
    problems = validate(Context((sidecar / context).read_text(encoding="utf-8")), parsed)
    if problems:
        return 1, [f"review: the report does not hold: {problems[0]}; nothing recorded"]
    kept = f"{REVIEWS}/{head}.report.md"
    write_private(sidecar / kept, text)
    commit_sidecar(sidecar, f"personal: review report {head[:12]}", [kept])
    marked = {**os.environ, SESSION_SETTING: "1"}  # the agent's words, always marked (rule 8)
    FilesForge(sidecar, env=marked).comment(record["number"], text)
    verdict = (parsed["verdicts"] or ["none"])[0]
    return 0, [f"review: the report holds (verdict {verdict}); it is advisory ({CHANGE_RULE})",
               "review: your verdict, at your terminal: personal.py change confirm"]  # fmt: skip


def change_confirm(
    clone: Path, sidecar: Path, ask=input, tty=None, env=None
) -> tuple[int, list[str]]:
    """Answer 3: the person's `Verdict: cleared <head>` at a terminal, as the gate reads it."""
    try:
        return _change_confirm(clone, sidecar, ask, tty, env)
    except CheckError as exc:
        return 1, [f"refused: {exc}"]


def _change_confirm(clone: Path, sidecar: Path, ask, tty, env) -> tuple[int, list[str]]:
    from forge import FilesForge  # noqa: PLC0415
    from local_mode import SESSION_SETTING  # noqa: PLC0415

    try:
        # kit-only, guarded: an experimental file (kit/manifest.json), absent from a default install
        from check_review_report import parse_report  # noqa: PLC0415 - kit-only
    except ImportError:
        raise CheckError(NO_REPORT_CHECK) from None
    env = os.environ if env is None else env
    if env.get(SESSION_SETTING):
        raise CheckError(f"confirm runs only at the person's terminal (setting: {SESSION_SETTING})")
    if not (os.isatty(0) if tty is None else tty()):
        raise CheckError("confirm needs a terminal on standard input (SPEC-0041 rule 15)")
    record, head, _ = started(clone, sidecar)
    report = sidecar / REVIEWS / f"{head}.report.md"
    if not report.is_file():
        raise CheckError(
            f"no review report for the head; run personal.py change review ({CHANGE_RULE})"
        )
    verdict = (parse_report(report.read_text(encoding="utf-8"))["verdicts"] or ["none"])[0]
    shown = [f"{record['title']}: pull {record['number']}",
             f"head {head} of {record['head']['ref']}",
             f"review report: {verdict} (advisory)"]  # fmt: skip
    answer = ask("\n".join([*shown, "clear this head? [yes/no] "]))
    if answer.strip().lower() not in ("y", "yes"):
        return 1, [*shown, "change confirm: nothing written"]
    if head_of(clone) != head:
        raise CheckError(
            f"the clone's head moved while confirming; nothing written ({CHANGE_RULE})"
        )
    files = FilesForge(sidecar, env=env)
    body = [f"Confirmed: {head}", f"Verdict: cleared {head}", "Shown:", *shown]
    body.append(f"confirmed by {files.person} at a terminal at {files.now()}")
    files.comment(record["number"], "\n".join(body))
    return 0, [
        *shown,
        f"change confirm: {head[:12]} cleared at a terminal in pull {record['number']}",
    ]


def change_finish(
    clone: Path, sidecar: Path, ref: str | None, approve: bool
) -> tuple[int, list[str]]:
    """Answer 4: the gate of build (h) unchanged; on a pass, the commands for the developer."""
    started(clone, sidecar)
    passed, text = gate(clone, sidecar, ref, approve)
    lines = text.splitlines()
    if passed:
        lines.append("finish: optional, for the team's pull request: personal.py pr-summary")
    return (0 if passed else 1), lines


def parse_change(args: list[str]) -> dict | None:
    if not args or args[0] not in ("start", "review", "confirm", "finish"):
        return None
    out: dict = {"command": "change", "step": args.pop(0), "clone": ".", "sidecar": None}
    out.update(base=None, name=None, advances=None, report=None, approve=False)
    allowed = {"start": ("--base", "--advances"), "review": ("--base", "--report"),
               "finish": ("--base",), "confirm": ()}[out["step"]]  # fmt: skip
    while args:
        flag = args.pop(0)
        if flag in ("--clone", "--sidecar", *allowed) and args:
            out[flag[2:]] = args.pop(0)
        elif flag == "--approve" and out["step"] == "finish":
            out["approve"] = True
        elif out["step"] == "start" and not flag.startswith("-") and out["name"] is None:
            out["name"] = flag
        else:
            return None
    return None if out["step"] == "start" and out["name"] is None else out


def state_module():
    """`personal_state.py`, which the kit and the plugin hold and a project install does not."""
    try:
        import personal_state  # noqa: PLC0415 - kit-only (config/kit-only.txt)
    except ImportError as exc:
        raise CheckError(
            "personal mode's state is not installed here (path class: scripts/agk/)"
        ) from exc
    return personal_state


SCHEMA_LINE = re.compile(r"^schema = [0-9]+[ \t]*$", re.MULTILINE)


def upgrade(sidecar: Path) -> tuple[int, list[str]]:
    """Rule 27: one step and one sidecar commit at a time, up to the plugin's schema."""
    state = state_module()
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    have, want = int(table.get("schema", 1)), state.PLUGIN_SCHEMA
    if have > want:
        raise CheckError(
            "the sidecar's schema is newer than this plugin's (setting: personal.schema)"
        )
    if have == want:
        return 0, [f"upgrade: schema {have} is current"]
    if _sidecar_git(sidecar, "status", "--porcelain").stdout.strip():
        raise CheckError(
            "the sidecar has uncommitted changes; commit them first (path class: sidecar)"
        )
    lines = []
    for step in range(have, want):
        migrate = state.MIGRATIONS.get(step)
        if migrate is None:
            raise CheckError(
                "this plugin has no step from the sidecar's schema (setting: personal.schema)"
            )
        paths = list(migrate(sidecar))
        toml = sidecar / "agk.toml"
        text = toml.read_text(encoding="utf-8")
        line = f"schema = {step + 1}"
        if SCHEMA_LINE.search(text):
            text = SCHEMA_LINE.sub(line, text, count=1)
        else:
            text = text.replace("[personal]\n", f"[personal]\n{line}\n", 1)
        toml.write_text(text, encoding="utf-8")
        commit_sidecar(
            sidecar, f"personal: upgrade schema {step} to {step + 1}", ["agk.toml", *paths]
        )
        lines.append(f"upgrade: schema {step} to {step + 1}")
    return 0, lines


def hook(clone: Path, action: str) -> tuple[int, list[str]]:
    """Rule 19: install refuses a clone with no sidecar, since the hook runs the gate on it."""
    state = state_module()
    if action == "install":
        find_sidecar(clone)
        return 0, [state.install_hook(clone, str(Path(__file__).resolve()))]
    return 0, [state.remove_hook(clone)]


EXPORT_RULE = "SPEC-0041 rule 24"
CHECK_RULE = "SPEC-0041 rule 25"
EXPORT_MAP = "records/export-map.json"
TARGET_MAP = "docs/runs/export-map.json"
EXPORT_BRANCH = "agk/personal-export"
NOTES = "records/notes"
REQ_FILE, LOG_FILE = "docs/requirements.md", "docs/runs/decisions-log.md"
RESET = {"requirement": "planned", "spec": "Draft", "adr": "Proposed"}
FOLDERS = {"spec": "docs/specs", "adr": "docs/adr"}
CLOSED_BRIEF = re.compile(r"^- Status: (?:done|closed|retired)[ \t]*$", re.MULTILINE)
DERIVED = re.compile(r"(?:Approve|Accept|Confirm): [0-9a-f]{40} (\S+)")
NUMBERED = re.compile(r"^(\d{4})-([a-z0-9][a-z0-9-]*)\.md$")
HASH_COMMENT = (".py", ".rb", ".sh", ".pl", ".r", ".ex", ".exs", ".jl", ".cr", ".nim")
NOT_FOUND = "the test is not found in the target's default branch; no marker is proposed"


def kit_module(name: str):
    """A kit script that the plugin holds and a project install does not (`adopt`, `intake`)."""
    try:
        return __import__(name)
    except ImportError as exc:
        raise CheckError(f"export needs the kit's {name}.py (path class: scripts/agk/)") from exc


def req_sections(text: str) -> list[tuple[str, str]]:
    """(id, text) of each `### REQ-nnn` section, up to the next `##` or `###` heading."""
    from common import REQ_HEADER  # noqa: PLC0415

    found: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line in text.splitlines(keepends=True):
        header = REQ_HEADER.match(line)
        if header:
            current = [line]
            found.append((header[1], current))
        elif line.startswith(("## ", "### ")):
            current = None
        elif current is not None:
            current.append(line)
    return [(rid, "".join(lines)) for rid, lines in found]


def log_rows(text: str) -> list[str]:
    """The data rows of the decisions log's table: every `|` line after the header and rule."""
    table = [line for line in text.splitlines() if line.startswith("|")]
    return table[2:]


def sidecar_records(sidecar: Path) -> list[dict]:
    """Every record of rule 25, in order: {id, kind, rel, text}."""
    out: list[dict] = []
    req = sidecar / REQ_FILE
    for rid, text in req_sections(req.read_text(encoding="utf-8") if req.is_file() else ""):
        out.append({"id": rid, "kind": "requirement", "rel": REQ_FILE, "text": text})
    for kind, folder in FOLDERS.items():
        for path in sorted((sidecar / folder).glob("*.md")):
            if NUMBERED.match(path.name):
                rid = f"{'SPEC' if kind == 'spec' else 'ADR'}-{path.name[:4]}"
                rel = path.relative_to(sidecar).as_posix()
                out.append({"id": rid, "kind": kind, "rel": rel, "text": path.read_text("utf-8")})
    for path in sorted((sidecar / "docs" / "briefs").glob("*.md")):
        if path.name != "TEMPLATE.md":
            rel = path.relative_to(sidecar).as_posix()
            out.append(
                {
                    "id": f"brief:{path.stem}",
                    "kind": "brief",
                    "rel": rel,
                    "text": path.read_text(encoding="utf-8"),
                }
            )
    log = sidecar / LOG_FILE
    for n, row in enumerate(log_rows(log.read_text(encoding="utf-8") if log.is_file() else ""), 1):
        out.append({"id": f"log:{n}", "kind": "decisions-log", "rel": LOG_FILE, "text": row})
    for path in sorted(p for p in (sidecar / NOTES).rglob("*") if p.is_file()):
        rel = path.relative_to(sidecar / NOTES).as_posix()
        out.append(
            {
                "id": f"note:{rel}",
                "kind": "field-note",
                "rel": NOTES,
                "text": path.read_text(encoding="utf-8", errors="replace"),
            }
        )
    entries = (
        tomllib.loads((sidecar / "test-map.toml").read_text(encoding="utf-8"))
        if (sidecar / "test-map.toml").is_file()
        else {}
    )
    for key, ids in entries.items():
        for test_id in ids if isinstance(ids, list) else []:
            out.append(
                {
                    "id": f"test-map:{key} {test_id}",
                    "kind": "test-map",
                    "rel": "test-map.toml",
                    "key": key,
                    "test": str(test_id),
                    "text": "",
                }
            )
    return out


def confirmations(sidecar: Path) -> dict[str, tuple[str, str]]:
    """Record id -> (login, date) of each confirmation made at the person's terminal (rule 8)."""
    from common import agent_apps  # noqa: PLC0415
    from reviewers import derived_only, login_of, solo_person  # noqa: PLC0415

    out: dict[str, tuple[str, str]] = {}
    for item in derived_only(sidecar_comments(sidecar), agent_apps(sidecar), solo_person(sidecar)):
        found = DERIVED.fullmatch(str(item.get("body") or ""))
        if found:
            out[found[1]] = (login_of(item), str(item.get("created_at") or "")[:10])
    return out


def reset_status(text: str, new: str) -> str:
    """TEXT with its first `- Status:` line set to NEW (rule 24's reset)."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if STATUS_LINE.match(line.rstrip("\r\n")):
            lines[i] = f"- Status: {new}{line[len(line.rstrip(chr(13) + chr(10))) :]}"
            break
    return "".join(lines)


def with_line(text: str, line: str) -> str:
    return text.rstrip("\n") + f"\n\n{line}\n"


def target_state(target: Path) -> tuple[str, str, bool]:
    """(default branch, base ref, AGK installed on it) of the target, read only."""
    from common import detect_default_branch, show  # noqa: PLC0415

    default = detect_default_branch(target)
    if not default:
        raise CheckError("cannot tell the target's default branch (option: --target)")
    base = f"origin/{default}"
    if _git(target, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        base = default
    if _git(target, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        raise CheckError("the target's default branch has no commit (option: --target)")
    text = show(target, base, "agk.toml")
    try:
        installed = text is not None and "version" in tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        installed = True
    return default, base, installed


def free_ids(target: Path, base: str, plan: dict[str, str]) -> dict[str, int]:
    """The first free number of each kind: `common.next_free_ids` against the base when AGK is
    installed there, else counted over the adopt plan's files, which the branch writes first."""
    from common import NUM_FILE, PROJECT_FIRST_REQ, next_free_ids  # noqa: PLC0415

    if not plan:
        free = next_free_ids(target, base)
        return {"req": int(free["req"][4:]), "spec": int(free["spec"]), "adr": int(free["adr"])}
    reqs = [int(r["id"][4:]) for r in parse_requirements(plan.get(REQ_FILE, ""))]
    out = {"req": max(max(reqs, default=0) + 1, PROJECT_FIRST_REQ)}
    for key, folder in FOLDERS.items():
        nums = [
            int(m[1])
            for rel in plan
            if rel.startswith(folder + "/") and (m := NUM_FILE.match(Path(rel).name))
        ]
        out[key] = max(nums, default=0) + 1
    return out


def adopt_plan(target: Path, today: str) -> dict[str, str]:
    adopt = kit_module("adopt")
    plan, _, _ = adopt.build_plan(target, today)
    clash = [rel for rel, action, _, _ in plan if action == "conflict"]
    if clash:
        raise CheckError("the adopt plan has a conflict in the target (path class: adopt plan)")
    return {rel: content.decode("utf-8") for rel, action, content, _ in plan if action == "create"}


def marked(text: str, name: str, marker: str, suffix: str) -> str | None:
    """TEXT with `<comment> MARKER` above the first line naming the test NAME, else None."""
    word = re.compile(rf"\b{re.escape(name.split('::')[-1].split('.')[-1])}\b")
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if word.search(line):
            lead = "#" if suffix.lower() in HASH_COMMENT else "//"
            note = f"{line[: len(line) - len(line.lstrip())]}{lead} {marker}\n"
            if i and lines[i - 1] == note:
                return text
            return "".join([*lines[:i], note, *lines[i:]])
    return None


def export_plan(sidecar: Path, target: Path, with_notes: bool, today: str) -> dict:
    """What `--write` would write: the files of both branches, the map and the printed commands."""
    from common import show  # noqa: PLC0415

    rewritten = kit_module("intake").rewritten
    default, base, installed = target_state(target)
    plan = {} if installed else adopt_plan(target, today)
    records = sidecar_records(sidecar)
    own: dict[str, list[int]] = {"req": [], "spec": [], "adr": []}
    for r in records:
        key = {"requirement": "req", "spec": "spec", "adr": "adr"}.get(r["kind"])
        number = int(r["id"].split("-")[1]) if key else 0
        if key and not (key == "req" and number < 101):
            own[key].append(number)
    first = free_ids(target, base, plan)
    maps = {k: {n: first[k] + i for i, n in enumerate(sorted(v))} for k, v in own.items()}
    confirmed = confirmations(sidecar)
    files = dict(plan)

    def base_text(rel: str) -> str:
        text = files.get(rel) or show(target, base, rel) or ""
        return text if not text or text.endswith("\n") else text + "\n"

    entries: list[dict] = []
    commands: list[str] = []
    scanned: list[tuple[str, str]] = []
    tests: dict[str, str] = {}
    for r in records:
        rid, kind, entry = r["id"], r["kind"], {"id": r["id"], "kind": r["kind"]}
        line = (
            "confirmed by {} in personal mode on {}".format(*confirmed[rid])
            if rid in confirmed
            else "drafted in personal mode, not confirmed"
        )
        if kind == "requirement" and int(rid[4:]) < 101:
            entry.update(status="withheld", reason="AGK's own requirement (REQ-001 to REQ-099)")
        elif kind == "requirement":
            text = with_line(reset_status(rewritten(r["text"], maps), RESET[kind]), line)
            files[REQ_FILE] = base_text(REQ_FILE).rstrip("\n") + "\n\n" + text
            entry.update(status="mapped", to=rewritten(rid, maps), path=REQ_FILE)
            scanned.append((REQ_FILE, text))
        elif kind in FOLDERS:
            number, slug = r["rel"].rsplit("/", 1)[1][:-3].split("-", 1)
            new = maps[kind][int(number)]
            rel = f"{FOLDERS[kind]}/{new:04d}-{slug}.md"
            files[rel] = with_line(reset_status(rewritten(r["text"], maps), RESET[kind]), line)
            entry.update(status="mapped", to=rewritten(rid, maps), path=rel)
            scanned.append((FOLDERS[kind], files[rel]))
        elif kind == "brief" and CLOSED_BRIEF.search(r["text"]):
            entry.update(status="withheld", reason="a closed brief; no issue is proposed")
        elif kind == "brief":
            files[r["rel"]] = rewritten(r["text"], maps)
            head = files[r["rel"]].splitlines()[0] if files[r["rel"]].strip() else ""
            title = head.removeprefix("# Brief: ").removeprefix("# ").strip() or rid[6:]
            commands.append(
                shlex.join(
                    [
                        "gh",
                        "issue",
                        "create",
                        "--title",
                        title,
                        "--label",
                        "agk-brief",
                        "--body-file",
                        r["rel"],
                    ]
                )
            )
            entry.update(status="mapped", to="an issue, its command printed", path=r["rel"])
            scanned.append(("docs/briefs", files[r["rel"]]))
        elif kind == "decisions-log":
            row = rewritten(r["text"], maps)
            text = base_text(LOG_FILE) or kit_module("adopt").KIT_ROOT.joinpath(
                "kit/templates/decisions-log.md"
            ).read_text(encoding="utf-8")
            files[LOG_FILE] = text.rstrip("\n") + "\n" + row + "\n"
            entry.update(status="mapped", to=f"{LOG_FILE} row", path=LOG_FILE)
            scanned.append((LOG_FILE, row))
        elif kind == "field-note" and not with_notes:
            entry.update(status="withheld", reason="a private field note (Q-S0041-11)")
        elif kind == "field-note":
            rel = f"docs/runs/field-notes/{rid[5:]}"
            files[rel] = r["text"]
            entry.update(status="mapped", to=rel, path=rel)
            scanned.append((NOTES, r["text"]))
        else:
            path, _, name = r["test"].partition("::")
            marker = rewritten(r["key"], maps)
            found = tests.get(path) or show(target, base, path)
            done = marked(found, name, marker, Path(path).suffix) if found and name else None
            if done is None:
                entry.update(status="withheld", reason=NOT_FOUND)
            else:
                tests[path] = done
                entry.update(status="mapped", to=f"{marker} at {r['test']}", path=path)
        entries.append(entry)
    return {
        "default": default,
        "base": base,
        "installed": installed,
        "plan": sorted(plan),
        "files": files,
        "tests": tests,
        "entries": entries,
        "commands": commands,
        "scanned": scanned,
    }


def export_lines(out: dict) -> list[str]:
    plan = out["plan"]
    lines = [
        f"export: target AGK {'installed' if out['installed'] else 'not installed'}"
        + ("" if out["installed"] else f"; the adopt plan adds {len(plan)} files")
    ]
    for e in out["entries"]:
        if e["status"] == "mapped":
            lines.append(f"export: {e['id']} -> {e['to']}")
        else:
            lines.append(f"export: withheld {e['id']} ({e['reason']})")
    lines += [f"export: for the team to run: {c}" for c in out["commands"]]
    mapped = sum(e["status"] == "mapped" for e in out["entries"])
    lines.append(f"export: {mapped} mapped, {len(out['entries']) - mapped} withheld")
    return lines


def _target_git(target: Path, *args: str) -> subprocess.CompletedProcess:
    """A git call that writes in the target, `export --write` only (rule 24); never a push."""
    return subprocess.run(  # nosec B603 B607 - fixed git argument list, no shell
        ["git", "-C", str(target), *args], capture_output=True, check=False
    )


def export(
    sidecar: Path,
    target: Path,
    write: bool = False,
    branch: str | None = None,
    with_notes: bool = False,
) -> tuple[int, list[str]]:
    """Rule 24: a dry run, or with WRITE two new branches of TARGET and the map; never a push."""
    try:
        return _export(sidecar, target, write, branch or EXPORT_BRANCH, with_notes)
    except CheckError as exc:
        return 1, [f"refused: {exc}"]


def _export(sidecar: Path, target: Path, write: bool, branch: str, with_notes: bool):
    from guard import scan_text  # noqa: PLC0415

    today = datetime.now(UTC).date().isoformat()
    out = export_plan(sidecar, target, with_notes, today)
    for cls, text in out["scanned"]:
        if scan_text(text):
            raise CheckError(
                f"a record to export holds a secret pattern; nothing written (path class: {cls})"
            )
    lines = export_lines(out)
    if not write:
        return 0, ["export: dry run; nothing written (pass --write)", *lines]
    tests_branch = f"{branch}-tests"
    if branch in (out["default"], out["base"]) or tests_branch == out["default"]:
        raise CheckError(
            "export writes on a new branch, never the default branch (option: --branch)"
        )
    for name in (branch, tests_branch):
        if _git(target, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
            raise CheckError("the export branch already exists in the target (option: --branch)")
    if _git(target, "status", "--porcelain").stdout.strip():
        raise CheckError("the target's work tree is not clean (option: --target)")
    mapping = {
        "schema": 1,
        "rule": EXPORT_RULE,
        "date": today,
        "base": out["base"],
        "branch": branch,
        "tests_branch": tests_branch,
        "records": out["entries"],
    }
    text = json.dumps(mapping, indent=2) + "\n"
    records = {**out["files"], TARGET_MAP: text}
    back = [_git(target, "symbolic-ref", "--short", "-q", "HEAD").stdout.decode().strip()]
    back = (
        back if back[0] else ["--detach", _git(target, "rev-parse", "HEAD").stdout.decode().strip()]
    )
    made: list[str] = []
    try:
        for name, files, subject in (
            (branch, records, "agk: export personal-mode records to team mode"),
            (tests_branch, out["tests"], "agk: propose the personal test map as test markers"),
        ):
            if _target_git(
                target, "switch", "-q", "--no-track", "-c", name, out["base"]
            ).returncode:
                raise CheckError("the target branch cannot be made (option: --branch)")
            made.append(name)
            for rel, content in files.items():
                (target / rel).parent.mkdir(parents=True, exist_ok=True)
                (target / rel).write_text(content, encoding="utf-8", newline="\n")
            if files and (
                _target_git(target, "add", "--", *files).returncode
                or _target_git(
                    target, "commit", "-q", "-m", f"{subject} ({EXPORT_RULE})"
                ).returncode
            ):
                raise CheckError("the target commit failed (path class: target)")
    except CheckError:
        _target_git(target, "reset", "-q", "--hard")
        _target_git(target, "switch", "-q", "--discard-changes", *back)
        for name in made:
            _target_git(target, "branch", "-q", "-D", name)
        raise
    _target_git(target, "switch", "-q", *back)
    write_private(sidecar / EXPORT_MAP, text)
    commit_sidecar(sidecar, "personal: export map", [EXPORT_MAP])
    done = f"export: wrote the branches {branch} and {tests_branch} in the target; nothing pushed"
    return 0, [*lines, done]


def export_check(sidecar: Path) -> tuple[int, list[str]]:
    """Rule 25: every record of the sidecar is in the map, mapped to a new id or withheld."""
    path = sidecar / EXPORT_MAP
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("records", [])
    except (OSError, ValueError, AttributeError):
        return 1, [
            f"export --check: failed: no readable export-map.json (path: {EXPORT_MAP}, "
            f"{CHECK_RULE}); run export --write first"
        ]
    held = {
        e.get("id")
        for e in entries
        if isinstance(e, dict)
        and (
            (e.get("status") == "mapped" and e.get("to"))
            or (e.get("status") == "withheld" and e.get("reason"))
        )
    }
    missing = [r["id"] for r in sidecar_records(sidecar) if r["id"] not in held]
    if missing:
        word = "record" if len(missing) == 1 else "records"
        return 1, [
            f"export --check: failed: {len(missing)} {word} not in export-map.json, "
            f"first {missing[0]} ({CHECK_RULE})"
        ]
    return 0, [f"export --check: ok ({len(held)} records mapped or withheld)"]


def run_change(clone: Path, sidecar: Path, options: dict) -> tuple[int, list[str]]:
    step = options["step"]
    if step == "start":
        return change_start(clone, sidecar, options["name"], options["base"], options["advances"])
    if step == "review":
        return change_review(clone, sidecar, options["base"], options["report"])
    if step == "confirm":
        return change_confirm(clone, sidecar)
    return change_finish(clone, sidecar, options["base"], options["approve"])


def parse_export(args: list[str]) -> dict | None:
    """`export --target CLONE [--write] [--branch NAME] [--with-notes]` or `export --check`."""
    out: dict = {
        "command": "export",
        "clone": ".",
        "sidecar": None,
        "target": None,
        "write": False,
        "branch": None,
        "with_notes": False,
        "check": False,
    }
    while args:
        flag = args.pop(0)
        if flag in ("--write", "--with-notes", "--check"):
            out[flag[2:].replace("-", "_")] = True
        elif flag in ("--clone", "--sidecar", "--target", "--branch") and args:
            out[flag[2:]] = args.pop(0)
        else:
            return None
    if out["check"]:
        return None if out["write"] or out["target"] or out["branch"] else out
    return out if out["target"] else None


def parse(args: list[str]) -> dict | None:
    if args and args[0] == "export":
        return parse_export(args[1:])
    if args and args[0] == "confirm":
        return parse_confirm(args[1:])
    if args and args[0] == "change":
        return parse_change(args[1:])
    if args and args[0] in ("hook", "upgrade"):
        return parse_upkeep(args)
    if not args or args[0] not in ("baseline", "floor", "gate", "report", "pr-summary", "status"):
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


def parse_upkeep(args: list[str]) -> dict | None:
    """`hook install|remove [--clone DIR]` and `upgrade [--clone DIR] [--sidecar DIR]`."""
    out: dict = {"command": args.pop(0), "clone": ".", "sidecar": None, "action": None}
    if out["command"] == "hook":
        if not args or args[0] not in ("install", "remove"):
            return None
        out["action"] = args.pop(0)
    allowed = ("--clone",) if out["command"] == "hook" else ("--clone", "--sidecar")
    while args:
        flag = args.pop(0)
        if flag not in allowed or not args:
            return None
        out[flag[2:]] = args.pop(0)
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
        if options["command"] == "status" and options["sidecar"]:
            print(status(Path(options["sidecar"])))
            return 0
        if options["command"] == "upgrade" and options["sidecar"]:  # the clone is not read
            code, lines = upgrade(Path(options["sidecar"]))
            print("\n".join(lines))
            return code
        if options["command"] == "export" and options["check"] and options["sidecar"]:
            code, lines = export_check(Path(options["sidecar"]))
            print("\n".join(lines))
            return code
        probe = _git(Path(options["clone"]), "rev-parse", "--show-toplevel")
        if probe.returncode != 0:
            raise CheckError("the clone cannot be read as a git repository (option: --clone)")
        clone = Path(probe.stdout.decode("utf-8", "surrogateescape").strip())
        if options["command"] == "hook":
            code, lines = hook(clone, options["action"])
            print("\n".join(lines))
            return code
        sidecar = Path(options["sidecar"]) if options["sidecar"] else find_sidecar(clone)
        if options["command"] == "upgrade":
            code, lines = upgrade(sidecar)
            print("\n".join(lines))
            return code
        if options["command"] == "export":
            code, lines = (
                export_check(sidecar)
                if options["check"]
                else export(
                    sidecar,
                    Path(options["target"]),
                    options["write"],
                    options["branch"],
                    options["with_notes"],
                )
            )
            print("\n".join(lines))
            return code
        if options["command"] == "change":
            code, lines = run_change(clone, sidecar, options)
            print("\n".join(lines))
            return code
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
        if options["command"] == "status":
            print(status(sidecar))
            return 0
        if options["command"] == "pr-summary":
            passed, text = pr_summary(clone, sidecar)
            print(text)
            return 0 if passed else 1
        run = gate if options["command"] == "gate" else floor
        passed, text = run(clone, sidecar, options["base"], options["approve"])
        print(text)
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
