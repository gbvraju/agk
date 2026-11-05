"""`--queue` on prepush.py and the proof run, and `status --ticket T --head H` (brief #566,
SPEC-0040 build (c), rules 9 and 10).

REQ-047. With `[locks] queue = true`, `prepush.py --record FILE --queue [--body FILE]` and
`proof.py --queue [its options]` submit the same command without `--queue`, with the body, record
and manifest paths made absolute, as one heavy job of kind `prepush` or `proof`, taking `--brief`
from the body's `Brief: #n` line, and return at once, running no step of their own. `lock.py
status --ticket T --head H` exits 0 only for a passed result of that exact head. Every test points
`lock_dir` at its own folder, answers the one brief read from a fake `gh` on PATH and makes no
network call; data is invented (example.com).
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path

import heavy_queue
import pytest

PY = sys.executable
QUEUED = re.compile(r"queued (heavy-\d{6}-[0-9a-f]{4}) position 1 of 1 \(head ([0-9a-f]{12})\)")
SHA_A = "a" * 40
SHA_B = "b" * 40


def outside(tmp_path: Path, name: str) -> Path:
    folder = tmp_path.parent / f"{tmp_path.name}-{name}"
    folder.mkdir(exist_ok=True)
    return folder


def configure(repo, tmp_path: Path, locks: str | None = "queue = true\n") -> Path:
    folder = outside(tmp_path, "locks")
    text = f"lock_dir = '{folder.as_posix()}'\n" + (f"[locks]\n{locks}" if locks else "")
    repo.commit({"agk.toml": text}, "settings")
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    return folder


def fake_gh(tmp_path: Path) -> str:
    """A `gh` on PATH that answers brief 7 with `Priority: 1` and fails everything else."""
    bin_dir = outside(tmp_path, "bin")
    script = bin_dir / "gh"
    script.write_text(
        f"#!{PY}\nimport json, sys\n"
        "path = next((a for a in sys.argv[1:] if a.startswith('repos/')), '')\n"
        "if not path.endswith('/issues/7'):\n"
        "    sys.stderr.write('HTTP 404: Not Found\\n'); sys.exit(1)\n"
        "print(json.dumps({'number': 7, 'body': 'Why: x\\nPriority: 1\\n'}))\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


def run(repo, tmp_path, script: str, *args: str, session: str | None = "b566"):
    env = {"PATH": fake_gh(tmp_path), "AGK_SESSION": session or ""}
    return repo.run(script, *args, **env)


def jobs(folder: Path) -> list[dict]:
    box = folder / ".agk-lock-heavy.queue" / "jobs"
    files = sorted(box.glob("*.json")) if box.is_dir() else []
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def body_file(tmp_path: Path, text: str = "Brief: #7\nSummary: x\n") -> Path:
    path = outside(tmp_path, "out") / "body.md"
    path.write_text(text, encoding="utf-8")
    return path


def hold_lock(folder: Path) -> Path:
    held = folder / "agk-lock-heavy"
    held.mkdir(parents=True)
    owner = {
        "session": "other", "pid": os.getpid(), "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "token": "t" * 8,
    }  # fmt: skip
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    return held


# --- rule 9: prepush.py --queue -------------------------------------------------------------------


def test_prepush_queue_submits_one_job_and_runs_no_step(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rules 3, 6 and 9; it returns while the heavy lock is held."""
    folder = configure(repo, tmp_path)
    held = hold_lock(folder)
    rel = os.path.relpath(body_file(tmp_path), repo.root)
    record = os.path.join(os.path.relpath(outside(tmp_path, "out"), repo.root), "rec.json")
    proc = run(repo, tmp_path, "prepush.py", "--body", rel, "--record", record, "--queue")
    match = QUEUED.search(proc.stdout)
    assert proc.returncode == 0 and match, proc.stdout + proc.stderr
    assert "prepush: " not in proc.stdout and held.is_dir()
    [job] = jobs(folder)
    assert job["kind"] == "prepush" and job["brief"] == 7 and job["priority"] == 1
    assert job["session"] == "b566" and job["ticket"] == match.group(1)
    command = job["command"]
    assert "--queue" not in command and "--quick" not in command
    assert Path(command[1]).name == "prepush.py"
    body_at = command[command.index("--body") + 1]
    record_at = command[command.index("--record") + 1]
    assert os.path.isabs(body_at) and Path(body_at) == body_file(tmp_path)
    assert os.path.isabs(record_at) and Path(record_at).name == "rec.json"
    assert not (outside(tmp_path, "out") / "rec.json").exists()


def test_prepush_queue_without_a_brief_line_passes_no_brief(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rule 3 (`--brief` only from a `Brief: #n` line)."""
    folder = configure(repo, tmp_path)
    body = body_file(tmp_path, "Summary: x\n")
    record = outside(tmp_path, "out") / "rec.json"
    proc = run(repo, tmp_path, "prepush.py", "--queue", "--record", str(record), "--body", str(body))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    [job] = jobs(folder)
    assert job["brief"] is None and job["priority"] == "unknown"


def test_prepush_queue_without_record_exits_2_naming_the_option(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rule 9 (a queued run without a record leaves no evidence)."""
    folder = configure(repo, tmp_path)
    proc = run(repo, tmp_path, "prepush.py", "--queue")
    assert proc.returncode == 2 and "(option: --record)" in proc.stdout + proc.stderr
    assert jobs(folder) == [] and "prepush: lint" not in proc.stdout


def test_prepush_quick_is_never_queued(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rule 9 (`--quick` is unchanged and not queued)."""
    folder = configure(repo, tmp_path)
    record = outside(tmp_path, "out") / "rec.json"
    proc = run(repo, tmp_path, "prepush.py", "--quick", "--queue", "--record", str(record))
    assert proc.returncode == 2 and "(option: --quick)" in proc.stdout + proc.stderr
    assert jobs(folder) == []


@pytest.mark.parametrize("locks", [None, "queue = false\n"])
@pytest.mark.parametrize("script", ["prepush.py", "proof.py"])
def test_queue_with_the_setting_off_exits_2_naming_the_setting(repo, tmp_path, locks, script):
    """REQ-047 AC1 and AC7: SPEC-0040 rules 1 and 9; no queue folder is made."""
    folder = configure(repo, tmp_path, locks)
    record = str(outside(tmp_path, "out") / "rec.json")
    args = ["--queue", "--record", record] if script == "prepush.py" else ["--queue"]
    proc = run(repo, tmp_path, script, *args)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 2 and "setting: [locks] queue" in out and "false" not in out
    assert not (folder / ".agk-lock-heavy.queue").exists()


@pytest.mark.parametrize("script", ["prepush.py", "proof.py"])
def test_queue_without_a_session_exits_2_naming_the_setting(repo, tmp_path, script):
    """REQ-047 AC7: SPEC-0040 rule 3 (a job names its session); Q-566-1."""
    folder = configure(repo, tmp_path)
    record = str(outside(tmp_path, "out") / "rec.json")
    args = ["--queue", "--record", record] if script == "prepush.py" else ["--queue"]
    proc = run(repo, tmp_path, script, *args, session=None)
    assert proc.returncode == 2 and "setting: AGK_SESSION" in proc.stdout + proc.stderr
    assert jobs(folder) == []


# --- rule 9: proof.py --queue ---------------------------------------------------------------------


def test_proof_queue_submits_one_job_of_kind_proof(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rules 3, 6 and 9."""
    folder = configure(repo, tmp_path)
    body = os.path.relpath(body_file(tmp_path), repo.root)
    manifest = os.path.join(os.path.relpath(outside(tmp_path, "out"), repo.root), "m.md")
    proc = run(repo, tmp_path, "proof.py", "--queue", "--body", body, "--manifest", manifest)
    assert proc.returncode == 0 and QUEUED.search(proc.stdout), proc.stdout + proc.stderr
    assert "proof:" not in proc.stdout
    [job] = jobs(folder)
    assert job["kind"] == "proof" and job["brief"] == 7
    command = job["command"]
    assert "--queue" not in command and Path(command[1]).name == "proof.py"
    assert os.path.isabs(command[command.index("--body") + 1])
    assert os.path.isabs(command[command.index("--manifest") + 1])


@pytest.mark.parametrize("args", [["--body", "-"], ["--head", "HEAD~1"]])
def test_proof_queue_refuses_what_the_queued_run_cannot_see(repo, tmp_path, args):
    """REQ-047 AC7: SPEC-0040 rules 6 and 10 (the job runs later, on its own head); Q-566-2."""
    folder = configure(repo, tmp_path)
    repo.commit({"a.txt": "a\n"}, "second")
    proc = run(repo, tmp_path, "proof.py", "--queue", *args)
    assert proc.returncode == 2 and f"(option: {args[0]})" in proc.stdout + proc.stderr
    assert jobs(folder) == []


# --- rule 10: status --ticket T --head H ----------------------------------------------------------


def put_result(folder: Path, ticket: str, head: str, outcome: str) -> None:
    box = folder / ".agk-lock-heavy.queue" / "results"
    box.mkdir(parents=True, exist_ok=True)
    data = {"schema": 1, "ticket": ticket, "head": head, "kind": "prepush", "outcome": outcome,
            "exit": 0 if outcome == "passed" else 1, "run_seconds": 12}  # fmt: skip
    (box / f"{ticket}.json").write_text(json.dumps(data), encoding="utf-8")


def put_job(folder: Path, ticket: str, started: bool) -> None:
    box = folder / ".agk-lock-heavy.queue" / "jobs"
    box.mkdir(parents=True, exist_ok=True)
    job = heavy_queue.new_job(
        session="b566", repository="/x", branch="claude/brief-566", head=SHA_A,
        command=["python3", "-c", "pass"], folder=".", kind="prepush", brief=None,
        priority="unknown", submitted=datetime.now(UTC),
    )  # fmt: skip
    job.update({"ticket": ticket, "seq": 1})
    if started:
        job["started"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        job["runner"] = {"pid": os.getpid(), "host": socket.gethostname()}
    (box / f"{ticket}.json").write_text(json.dumps(job), encoding="utf-8")


def status(repo, ticket: str, head: str):
    return repo.run("lock.py", "status", "--name", "heavy", "--ticket", ticket, "--head", head)


def test_status_head_exits_0_only_for_a_passed_result_of_that_head(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rule 10."""
    folder = configure(repo, tmp_path)
    put_result(folder, "heavy-000001-abcd", SHA_A, "passed")
    proc = status(repo, "heavy-000001-abcd", SHA_A)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.startswith("result heavy-000001-abcd passed head aaaaaaaaaaaa")


def test_status_head_reports_stale_for_another_head(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rule 10 (a result for an older head is no evidence)."""
    folder = configure(repo, tmp_path)
    put_result(folder, "heavy-000001-abcd", SHA_A, "passed")
    proc = status(repo, "heavy-000001-abcd", SHA_B)
    assert proc.returncode == 1
    assert proc.stdout == "stale (result for aaaaaaaaaaaa, asked bbbbbbbbbbbb)\n"


@pytest.mark.parametrize("outcome", ["failed (exit 1)", "replaced by heavy-000002-beef"])
def test_status_head_reports_failed_for_a_failed_or_replaced_result(repo, tmp_path, outcome):
    """REQ-047 AC7: SPEC-0040 rule 10."""
    folder = configure(repo, tmp_path)
    put_result(folder, "heavy-000001-abcd", SHA_A, outcome)
    proc = status(repo, "heavy-000001-abcd", SHA_A)
    assert proc.returncode == 1 and proc.stdout.startswith("failed ")


@pytest.mark.parametrize("started, word", [(False, "waiting"), (True, "running")])
def test_status_head_exits_3_while_there_is_no_result(repo, tmp_path, started, word):
    """REQ-047 AC7: SPEC-0040 rule 10."""
    folder = configure(repo, tmp_path)
    put_job(folder, "heavy-000001-abcd", started)
    proc = status(repo, "heavy-000001-abcd", SHA_A)
    assert proc.returncode == 3 and proc.stdout.startswith(word), proc.stdout


def test_status_head_on_an_unknown_ticket_is_no_evidence(repo, tmp_path):
    """REQ-047 AC7: SPEC-0040 rule 10."""
    configure(repo, tmp_path)
    proc = status(repo, "heavy-000009-abcd", SHA_A)
    assert proc.returncode == 1 and proc.stdout == "unknown ticket\n"


@pytest.mark.parametrize(
    "args", [["--head", SHA_A], ["--ticket", "heavy-000001-abcd", "--head", "aaaa"]]
)
def test_status_head_needs_a_ticket_and_a_full_sha(repo, tmp_path, args):
    """REQ-047 AC7: SPEC-0040 rule 10 (exactly that head); Q-566-3."""
    configure(repo, tmp_path)
    proc = repo.run("lock.py", "status", "--name", "heavy", *args)
    assert proc.returncode == 2 and proc.stdout == ""
