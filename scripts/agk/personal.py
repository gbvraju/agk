# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Personal mode's commands on a sidecar: the baseline of the tests already failing.

    python3 personal.py baseline [--clone DIR] [--sidecar DIR] [--approve]
    python3 personal.py floor [--clone DIR] [--sidecar DIR] [--base REF] [--approve]
    python3 personal.py report [--week YYYY-Www] [--clone DIR] [--sidecar DIR]
    python3 personal.py confirm <REQ-nnn|SPEC-nnnn|ADR-nnnn> [--clone DIR] [--sidecar DIR]

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
from survey import INVENTORY, find_sidecar, write_private  # noqa: E402

USAGE = (
    "usage: personal.py baseline|floor|report [--clone DIR] [--sidecar DIR] [--base REF] "
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


RECORD_ID = re.compile(r"(SPEC-(\d{4})|ADR-(\d{4})|REQ-\d{3})")
MOVES = {"SPEC": ("Draft", "Approved"), "ADR": ("Proposed", "Accepted")}
READERS = {"SPEC": "check_specs", "ADR": "check_adrs", "REQ": "check_requirements"}
WORDS = {"SPEC": "Approve", "ADR": "Accept", "REQ": "Confirm"}
PROVES = (
    "A confirmation typed by the person at their own terminal (SPEC-0041 rules 8 and 15). It "
    "proves that the yes was typed at a terminal with no agent session's mark, and nothing more."
)


def _sidecar_git(sidecar: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed git argument list, no shell
        ["git", *args], cwd=sidecar, capture_output=True, text=True, check=False
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


def commit_options(sidecar: Path) -> list[str]:
    """Signed with the person's own key only with `[personal] sign = true` (off by default)."""
    if (personal_table(sidecar) or {}).get("sign") is True:
        return ["commit", "-q", "--no-verify", "-S"]
    return ["-c", "commit.gpgsign=false", "commit", "-q", "--no-verify"]


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


def move_status(path: Path, old: str, new: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        if STATUS_LINE.match(line.rstrip("\r\n")):
            lines[i] = line.replace(f"- Status: {old}", f"- Status: {new}", 1)
            break
    path.write_text("".join(lines), encoding="utf-8")


def confirm(sidecar: Path, rid: str, ask=input, tty=None, env=None) -> tuple[int, list[str]]:
    """Rule 15: the person's yes at a terminal, read by the kind's reader before one commit."""
    try:
        return _confirm(sidecar, rid, ask, tty, env)
    except CheckError as exc:
        return 1, [f"refused: {exc}"]


def _confirm(sidecar: Path, rid: str, ask, tty, env) -> tuple[int, list[str]]:
    from forge import FilesForge  # noqa: PLC0415 - `confirm` only
    from local_mode import SESSION_SETTING  # noqa: PLC0415

    env = os.environ if env is None else env
    if env.get(SESSION_SETTING):
        raise CheckError(f"confirm runs only at the person's terminal (setting: {SESSION_SETTING})")
    if not (sys.stdin.isatty() if tty is None else tty()):
        raise CheckError("confirm needs a terminal on standard input (SPEC-0041 rule 15)")
    files = FilesForge(sidecar, env=env)
    state = _sidecar_git(sidecar, "status", "--porcelain")
    head = _sidecar_git(sidecar, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    if state.returncode != 0 or state.stdout.strip() or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise CheckError("confirm needs a clean sidecar work tree at a commit (SPEC-0041 rule 8)")
    rel, title, status = record_of(sidecar, rid)
    shown = shown_lines(rid, rel, title, status, head)
    if ask("\n".join([*shown, f"confirm {rid}? [yes/no] "])).strip().lower() not in ("y", "yes"):
        return 1, [*shown, f"confirm: nothing written for {rid}"]
    kind = rid.split("-")[0]
    branch = _sidecar_git(sidecar, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or "main"
    with files.locked():
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
        if kind in MOVES:
            move_status(sidecar / rel, *MOVES[kind])
            paths.append(rel)
        reader = READERS[kind]
        script = Path(__file__).resolve().parent / f"{reader}.py"
        check = subprocess.run(  # nosec B603 - the kit's own reader, fixed argument list, no shell
            [sys.executable, str(script), "--base", head, "--comments", paths[1]],
            cwd=sidecar, capture_output=True, text=True, check=False,
        )  # fmt: skip
        done = None
        if check.returncode == 0:
            identity = ["-c", f"user.name={files.person}"]
            identity += ["-c", f"user.email={files.person}@personal.invalid"]
            _sidecar_git(sidecar, "add", "--", *paths)
            done = _sidecar_git(sidecar, *identity, *commit_options(sidecar),
                                "-m", f"personal: confirm {rid}", "--", *paths)  # fmt: skip
        if done is None or done.returncode != 0:
            _sidecar_git(sidecar, "reset", "-q", "--hard", head)
            for rel_path in paths[:2]:
                (sidecar / rel_path).unlink(missing_ok=True)
            why = f"the reader {reader} failed" if done is None else "the sidecar commit failed"
            said = [x for x in check.stdout.splitlines() if x.startswith("FAIL ")]
            return 1, [
                *shown,
                *said,
                f"confirm: {why}; nothing committed, the sidecar is at {head}",
            ]
    return 0, [*shown, f"confirm: {rid} confirmed at a terminal in pull {number}"]


def parse(args: list[str]) -> dict | None:
    if args and args[0] == "confirm":
        return parse_confirm(args[1:])
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
        passed, text = floor(clone, sidecar, options["base"], options["approve"])
        print(text)
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
