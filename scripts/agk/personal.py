"""Personal mode's commands on a sidecar: the baseline of the tests already failing.

    python3 personal.py baseline [--clone DIR] [--sidecar DIR] [--approve]
    python3 personal.py floor [--clone DIR] [--sidecar DIR] [--base REF] [--approve]
    python3 personal.py report [--week YYYY-Www] [--clone DIR] [--sidecar DIR]

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
import xml.parsers.expat
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, personal_table, utf8_output  # noqa: E402
from survey import INVENTORY, find_sidecar, write_private  # noqa: E402

USAGE = (
    "usage: personal.py baseline|floor|report [--clone DIR] [--sidecar DIR] [--base REF] "
    "[--week YYYY-Www] [--approve]"
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


def write_tree(clone: Path, head: str, sidecar: Path) -> Path:
    """The head's tree under the sidecar, from git's object store; the clone is only read."""
    done = _git(clone, "archive", "--format=tar", head)
    if done.returncode != 0:
        raise CheckError("the head tree cannot be archived (option: --clone)")
    tree = sidecar / TREES / head
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


def regression_step(command: str, clone: Path, sidecar: Path, base: str, head: str) -> tuple:
    """Step two: the test command on the base tree and on the head tree, then compared."""
    runs = {}
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
    lines.append(CAUTION)
    return "\n".join(lines)


def parse(args: list[str]) -> dict | None:
    if not args or args[0] not in ("baseline", "floor", "report"):
        return None
    out: dict = {"command": args.pop(0), "clone": ".", "sidecar": None, "base": None}
    out["week"] = None
    out["approve"] = False
    while args:
        flag = args.pop(0)
        if flag == "--approve" and out["command"] != "report":
            out["approve"] = True
        elif flag == "--base" and args and out["command"] == "floor":
            out["base"] = args.pop(0)
        elif flag == "--week" and args and out["command"] == "report":
            out["week"] = args.pop(0)
        elif flag in ("--clone", "--sidecar") and args:
            out[flag[2:]] = args.pop(0)
        else:
            return None
    return out


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        probe = _git(Path(options["clone"]), "rev-parse", "--show-toplevel")
        if probe.returncode != 0:
            raise CheckError("the clone cannot be read as a git repository (option: --clone)")
        clone = Path(probe.stdout.decode("utf-8", "surrogateescape").strip())
        sidecar = Path(options["sidecar"]) if options["sidecar"] else find_sidecar(clone)
        if options["command"] == "baseline":
            print(baseline(clone, sidecar, options["approve"]))
            return 0
        if options["command"] == "report":
            print(report(clone, sidecar, options["week"]))
            return 0
        passed, text = floor(clone, sidecar, options["base"], options["approve"])
        print(text)
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
