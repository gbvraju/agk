"""Check a local evidence record against the head and re-run a sample of it (brief #434, ADR-0233).

    python3 scripts/agk/evidence.py check RECORD [--head SHA] [--sample N] [--json]

RECORD is the file that `prepush.py --record` wrote (schema 1, brief #374, ADR-0208). A record of
another schema, or one whose fields are not those of schema 1, is refused (exit 2, naming the field,
never its value). The check reports, in this order:

- `stale` when the record's `head` is not SHA (by default the current `HEAD`);
- `dirty` when its `tree_clean` is false;
- `failed` when a recorded step, or a run of the tests step, did not exit 0.

Any of these is a difference and nothing is re-run. Otherwise it adds a detached worktree of the
head in a new temporary folder, runs `make -f agk.mk agk-governance` there with `AGK_BASE` set to
the record's `base`, and re-runs N recorded steps (default 1) in it: each step's `argv` in its
`cwd`, and each run of the tests step as its shell command. The steps are chosen from the head sha
(a sha256 of the sha and the step's name orders them), so the same head always gives the same
sample. A step whose arguments name a path outside the repository (`<outside>/...`, a body file,
say) cannot be repeated and is listed, not sampled; a tool written `<outside>/<name>` as the command
itself is looked up on PATH. It compares exit codes; a different output digest is a note, never a
failure, since outputs carry timings. Governance and the re-runs hold the heavy-step lock
(`lock.py`, name `heavy`), unless the caller already holds it (`lock.py run --name heavy --
evidence.py ...`). The worktree is removed afterwards, also on a failure or an interrupt.

One line per finding (`evidence: ...`), then one line for the conductor to quote in the verdict:
`Evidence check: agrees|differs, head <sha12>, record <sha12 of the file>, governance <outcome>,
sample <k> of <m> same exit`. `--json` prints one JSON object instead.

Exit 0 when the record agrees, 1 when it differs, 2 on a usage error or a bad record, 3 on an I/O
error (a record that cannot be read, a worktree that cannot be made, make not installed). It posts
nothing, needs no network and changes nothing in the repository but the worktree it removes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock as heavy_lock
from common import CheckError, proof_timeout
from prepush import LOCK, digest, stop_signals, take_lock
from proof import execute

HERE = Path(__file__).resolve().parent
USAGE = "usage: evidence.py check RECORD [--head SHA] [--sample N] [--json]"
SCHEMA = 1
DEFAULT_SAMPLE = 1
SHA = re.compile(r"[0-9a-f]{40}")
OUTSIDE = "<outside>/"


class Usage(Exception):
    """A usage error or a bad record (exit 2)."""


class Unreadable(Exception):
    """An I/O error (exit 3)."""


def parse_args(args: list[str]) -> dict:
    if not args or args[0] != "check":
        raise Usage(USAGE)
    options: dict = {"record": None, "head": None, "sample": DEFAULT_SAMPLE, "json": False}
    i = 1
    while i < len(args):
        arg = args[i]
        if arg in ("--head", "--sample") and i + 1 < len(args):
            value = args[i + 1]
            if arg == "--sample":
                if not value.isdigit() or int(value) < 1:
                    raise Usage(USAGE)
                options["sample"] = int(value)
            else:
                options["head"] = value
            i += 2
        elif arg == "--json":
            options["json"] = True
            i += 1
        elif not arg.startswith("-") and options["record"] is None:
            options["record"] = arg
            i += 1
        else:
            raise Usage(USAGE)
    if options["record"] is None:
        raise Usage(USAGE)
    return options


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8"
    )


def bad(field: str) -> Usage:
    return Usage(f"evidence: the record is not a schema {SCHEMA} record (field: {field})")


def is_exit(value) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def valid_step(item) -> bool:
    if not isinstance(item, dict):
        return False
    if not isinstance(item.get("name"), str) or not isinstance(item.get("cwd"), str):
        return False
    argv = item.get("argv")
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        return False
    if "exit" not in item or not is_exit(item["exit"]):
        return False
    if not isinstance(item.get("output_sha256"), str):
        return False
    runs = item.get("runs")
    if runs is None:
        return True
    return isinstance(runs, list) and all(valid_run(r) for r in runs)


def valid_run(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("command"), str)
        and isinstance(item.get("cwd"), str)
        and "exit" in item
        and is_exit(item["exit"])
    )


def load(path: Path) -> tuple[dict, str]:
    """The record and the sha256 of its bytes. Unreadable on an I/O error, Usage on a bad record."""
    try:
        data = path.read_bytes()
    except OSError:
        raise Unreadable("evidence: the record cannot be read (option: RECORD)") from None
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise bad("schema") from None
    if not isinstance(record, dict):
        raise bad("schema")
    schema = record.get("schema")
    if isinstance(schema, bool) or schema != SCHEMA:
        raise bad("schema")
    for field in ("head", "base"):
        if not isinstance(record.get(field), str) or not SHA.fullmatch(record[field]):
            raise bad(field)
    if not isinstance(record.get("tree_clean"), bool):
        raise bad("tree_clean")
    steps = record.get("steps")
    if not isinstance(steps, list) or not all(valid_step(s) for s in steps):
        raise bad("steps")
    return record, hashlib.sha256(data).hexdigest()


def resolve(root: Path, ref: str | None, given: bool) -> str:
    proc = git(root, "rev-parse", "--verify", "-q", f"{ref or 'HEAD'}^{{commit}}")
    if proc.returncode != 0:
        raise Usage("evidence: the head does not resolve (option: --head)" if given else USAGE)
    return proc.stdout.strip()


def problems(record: dict, head: str) -> list[str]:
    """`stale`, `dirty` and `failed`, each as one line, in that order (answer 1)."""
    found = []
    if record["head"] != head:
        found.append(f"stale: the record is of head {record['head'][:12]}, not {head[:12]}")
    if not record["tree_clean"]:
        found.append("dirty: the record's work tree was not clean (field: tree_clean)")
    for item in record["steps"]:
        if item["exit"] is not None and item["exit"] != 0:
            found.append(f"failed: step {item['name']} exited {item['exit']}")
        for run in item.get("runs") or []:
            if run["exit"] != 0:
                code = "none" if run["exit"] is None else run["exit"]
                found.append(f"failed: run {item['name']}/{run['name']} exited {code}")
    return found


def sample(head: str, names: list[str], count: int) -> list[str]:
    """`count` of `names`, chosen from the head sha alone: the same head, the same steps (answer 2).

    Each name is ranked by the sha256 of `<head>:<name>`; the order of the record does not matter
    and no random generator is involved, so no Python version changes the pick."""

    def rank(name: str) -> str:
        return hashlib.sha256(f"{head}:{name}".encode()).hexdigest()

    return sorted(dict.fromkeys(names), key=rank)[:count]


def units(record: dict) -> tuple[dict[str, dict], list[str]]:
    """The repeatable units by name (a step's argv, or a run of the tests step) and the lines of
    those that cannot be repeated. Governance is always re-run on its own, so it is not sampled."""
    found: dict[str, dict] = {}
    lines: list[str] = []
    for item in record["steps"]:
        if item["exit"] is not None and item["argv"] and item["name"] != "governance":
            if any(OUTSIDE in a for a in item["argv"][1:]):
                lines.append(f"not repeatable: {item['name']} (a path outside the repository)")
            else:
                found[item["name"]] = {"argv": item["argv"], **item}
        for run in item.get("runs") or []:
            name = f"{item['name']}/{run['name']}"
            if OUTSIDE in run["command"]:
                lines.append(f"not repeatable: {name} (a path outside the repository)")
            else:
                found[name] = {**run, "command": run["command"]}
    return found, lines


def real_argv(argv: list[str], cwd: Path) -> list[str]:
    """The recorded argv made runnable: `python3` the running interpreter, a kit script from the
    worktree or else from this kit, a tool written `<outside>/<name>` looked up on PATH."""
    out = []
    for i, arg in enumerate(argv):
        if arg == "python3":
            out.append(sys.executable)
        elif arg.startswith("scripts/agk/") and not (cwd / arg).is_file():
            out.append(str(HERE / arg.split("/", 2)[2]))
        elif i == 0 and arg.startswith(OUTSIDE):
            out.append(shutil.which(arg[len(OUTSIDE) :]) or arg)
        else:
            out.append(arg)
    return out


def inside(tree: Path, cwd: str) -> Path:
    folder = (tree / cwd).resolve()
    try:
        folder.relative_to(tree.resolve())
    except ValueError:
        return tree
    return folder


def rerun(tree: Path, unit: dict, env: dict, limit: int) -> tuple[int | None, str]:
    folder = inside(tree, unit.get("cwd") or ".")
    if "command" in unit:
        code, out, _ = execute(unit["command"], folder, limit)
        return code, out
    try:
        proc = subprocess.run(  # nosec B603 - the recorded argument list, no shell
            real_argv(unit["argv"], folder),
            cwd=folder,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except OSError:
        return 127, ""
    return proc.returncode, (proc.stdout + proc.stderr).rstrip("\n")


def governance(tree: Path, env: dict) -> tuple[int, str]:
    if shutil.which("make") is None:
        raise Unreadable("evidence: make is not installed; governance cannot run (tool: make)")
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", "agk-governance"],
        cwd=tree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return proc.returncode, (proc.stdout + proc.stderr).rstrip("\n")


def remove(root: Path, temp: Path, tree: Path) -> None:
    """Remove the worktree and its temporary folder; prune git's note of it (answer 2)."""
    git(root, "worktree", "remove", "--force", str(tree))
    shutil.rmtree(temp, ignore_errors=True)
    git(root, "worktree", "prune")


def in_worktree(root: Path, record: dict, head: str, count: int) -> dict:
    """Governance and the sample, in a detached worktree of `head`, under the heavy-step lock."""
    try:
        temp = Path(tempfile.mkdtemp(prefix="agk-evidence-"))
    except OSError:
        raise Unreadable(
            "evidence: the temporary folder cannot be made (setting: TMPDIR)"
        ) from None
    tree = temp / "head"
    taken = None
    previous = {sig: signal.signal(sig, heavy_lock.on_signal) for sig in stop_signals()}
    try:
        made = git(root, "worktree", "add", "--detach", "-q", str(tree), head)
        if made.returncode != 0:
            raise Unreadable(
                "evidence: the worktree of the head cannot be made (path class: TMPDIR)"
            )
        try:
            taken = take_lock(root)
        except heavy_lock.Usage as exc:
            raise Usage(f"evidence: {exc}") from None
        except OSError:
            raise Unreadable(
                f"evidence: lock {LOCK}: the lock folder cannot be written (setting: lock_dir)"
            ) from None
        env = {**os.environ, "AGK_BASE": record["base"]}
        code, out = governance(tree, env)
        try:
            limit = proof_timeout(tree)
        except CheckError as exc:
            raise Usage(f"evidence: {exc}") from None
        found, lines = units(record)
        picked = sample(head, list(found), count)
        results = []
        for name in picked:
            unit = found[name]
            got, output = rerun(tree, unit, env, limit)
            same_output = digest(output)["output_sha256"] == unit.get("output_sha256")
            results.append(
                {
                    "name": name,
                    "recorded_exit": unit["exit"],
                    "exit": got,
                    "same_exit": got == unit["exit"],
                    "same_output": same_output,
                }
            )
        return {
            "governance": {"exit": code, "output": out},
            "sample": results,
            "notes": lines,
            "candidates": len(found),
        }
    except heavy_lock.Stopped as exc:
        raise SystemExit(exc.code) from None
    finally:
        if taken is not None:
            heavy_lock.clear_if_same(*taken)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        remove(root, temp, tree)


def report(head: str, sha: str, found: list[str], ran: dict | None, as_json: bool) -> int:
    differs = bool(found)
    gov = "not run"
    same = 0
    total = 0
    lines = [f"evidence: {p}" for p in found]
    if ran is not None:
        ok = ran["governance"]["exit"] == 0
        gov = "ok" if ok else "FAIL"
        differs = differs or not ok
        lines.append(f"evidence: governance {gov} in a clean worktree of {head[:12]}")
        if not ok and not as_json and ran["governance"]["output"]:
            lines.append(ran["governance"]["output"])
        lines.extend(f"evidence: {n}" for n in ran["notes"])
        total = len(ran["sample"])
        for item in ran["sample"]:
            code = "none" if item["exit"] is None else item["exit"]
            was = "none" if item["recorded_exit"] is None else item["recorded_exit"]
            verdict = "same" if item["same_exit"] else "DIFFERS"
            note = "" if item["same_output"] else "; output digest differs (a note)"
            lines.append(
                f"evidence: re-ran {item['name']}: exit {code} (recorded {was}) {verdict}{note}"
            )
            same += item["same_exit"]
            differs = differs or not item["same_exit"]
        if total == 0:
            lines.append("evidence: no repeatable step to re-run")
    result = "differs" if differs else "agrees"
    if as_json:
        data = {
            "result": result,
            "head": head,
            "record_sha256": sha,
            "problems": found,
            "governance": {"exit": ran["governance"]["exit"]} if ran else None,
            "sample": ran["sample"] if ran else [],
            "notes": ran["notes"] if ran else [],
        }
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        for line in lines:
            print(line)
        print(
            f"Evidence check: {result}, head {head[:12]}, record {sha[:12]}, governance {gov}, "
            f"sample {same} of {total} same exit"
        )
    return 1 if differs else 0


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
        top = git(Path.cwd(), "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            raise Usage("evidence: not inside a git work tree (path class: root)")
        root = Path(top.stdout.strip())
        record, sha = load(Path(options["record"]))
        head = resolve(root, options["head"], options["head"] is not None)
        found = problems(record, head)
        ran = None if found else in_worktree(root, record, head, options["sample"])
        return report(head, sha, found, ran, options["json"])
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    except Unreadable as exc:
        print(exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
