"""A heavy run started under `lock.py run` passes its lock to everything it starts (brief #505,
ADR-0254).

`lock.py run --name heavy` gives the command it starts `AGK_LOCK_TOKEN` (the token of the slot
taken) and `AGK_LOCK_NAME`, beside `AGK_LOCK_SESSION`, and every process below it inherits them.
`prepush.py` treats a slot whose owner's token equals `AGK_LOCK_TOKEN`, under the name
`AGK_LOCK_NAME`, on this host, as its caller's, however many wrapper processes sit between them;
the direct-parent rule stays. A slot held in another process by the same non-empty `AGK_SESSION`,
without a matching token, fails at once with one line naming the fix; another session's slot is
waited for as before.

Every test uses a fake lock folder under `tmp_path`; no test waits for a real lock.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import lock
import prepush
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
PY = sys.executable
CALLER = "lock heavy: held by this run's caller (lock.py run); not taken again"
SELF = (
    "lock heavy: held by this session (builder-a) in another process; run prepush directly "
    "under lock.py run --name heavy, or end that run first"
)


def plant(folder: Path, *, session: str, token: str, pid: int | None = None, **extra) -> Path:
    """A slot as `lock.py` writes it, held by a live process (this test's own by default)."""
    held = folder / "agk-lock-heavy"
    held.mkdir(parents=True)
    owner = {
        "session": session,
        "pid": os.getpid() if pid is None else pid,
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
        **extra,
    }
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    return held


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A fake lock folder for `prepush.take_lock`, and a fake `take` that records its calls."""
    folder = tmp_path / "locks"
    calls: list[dict] = []

    def take(held, name, owner, limit, timeout, slots=1, **_):
        calls.append({"held": held, "name": name, "owner": owner})
        return held

    monkeypatch.setattr(lock, "lock_folder", lambda root, name: folder / f"agk-lock-{name}")
    monkeypatch.setattr(lock, "stale_minutes", lambda root: 120)
    monkeypatch.setattr(lock, "slots_setting", lambda root: 1)
    monkeypatch.setattr(lock, "take", take)
    # A parent pid that is not the holder's, so the direct-parent rule does not apply by accident.
    monkeypatch.setattr(prepush.os, "getppid", lambda: 1)
    for name in ("AGK_LOCK_TOKEN", "AGK_LOCK_NAME", "AGK_LOCK_SESSION", "AGK_SESSION"):
        monkeypatch.delenv(name, raising=False)
    return folder, calls


def test_a_matching_token_in_the_environment_is_not_taken_again(fake, monkeypatch, capsys):
    """REQ-040: brief #505 answer 2 (a token that matches means the caller's slot)."""
    folder, calls = fake
    token = uuid.uuid4().hex
    plant(folder, session="builder-a", token=token, pid=999_999_001)
    monkeypatch.setenv("AGK_LOCK_TOKEN", token)
    monkeypatch.setenv("AGK_LOCK_NAME", "heavy")
    monkeypatch.setenv("AGK_SESSION", "builder-a")
    assert prepush.take_lock(Path("/nonexistent")) is None
    assert calls == []
    assert CALLER in capsys.readouterr().out


@pytest.mark.parametrize(
    ("with_token", "name"),
    [
        (False, "heavy"),  # no token
        (True, "other"),  # another lock's token
        (True, None),  # no name
    ],
)
def test_a_token_counts_only_with_the_lock_name(fake, monkeypatch, with_token, name):
    """REQ-040: brief #505 answer 2 (the token and the name both match)."""
    folder, calls = fake
    token = uuid.uuid4().hex
    plant(folder, session="builder-other", token=token, pid=999_999_002)
    if with_token:
        monkeypatch.setenv("AGK_LOCK_TOKEN", token)
    if name is not None:
        monkeypatch.setenv("AGK_LOCK_NAME", name)
    assert prepush.caller_slot(folder / "agk-lock-heavy", 1) is None


def test_a_matching_token_from_another_host_does_not_count(fake, monkeypatch):
    """REQ-040: brief #505 answer 2 (on the same host)."""
    folder, _ = fake
    token = uuid.uuid4().hex
    held = plant(folder, session="builder-a", token=token, pid=999_999_003)
    owner = json.loads((held / "owner.json").read_text(encoding="utf-8"))
    owner["host"] = "elsewhere.example.com"
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    monkeypatch.setenv("AGK_LOCK_TOKEN", token)
    monkeypatch.setenv("AGK_LOCK_NAME", "heavy")
    assert prepush.caller_slot(held, 1) is None


def test_a_different_token_from_another_session_waits(fake, monkeypatch, capsys):
    """REQ-040: brief #505 answer 3 (another session's run waits as today: `take` is called)."""
    folder, calls = fake
    plant(folder, session="builder-b", token=uuid.uuid4().hex)
    monkeypatch.setenv("AGK_LOCK_TOKEN", uuid.uuid4().hex)
    monkeypatch.setenv("AGK_LOCK_NAME", "heavy")
    monkeypatch.setenv("AGK_SESSION", "builder-a")
    taken = prepush.take_lock(Path("/nonexistent"))
    assert taken is not None
    assert len(calls) == 1
    assert calls[0]["owner"]["session"] == "builder-a"
    assert CALLER not in capsys.readouterr().out


def test_the_same_session_without_a_matching_token_fails_at_once(fake, monkeypatch):
    """REQ-040: brief #505 answer 3 (same session, no matching token: one line naming the fix,
    and no wait)."""
    folder, calls = fake
    plant(folder, session="builder-a", token=uuid.uuid4().hex)
    monkeypatch.setenv("AGK_SESSION", "builder-a")
    with pytest.raises(prepush.HeldBySession) as caught:
        prepush.take_lock(Path("/nonexistent"))
    assert str(caught.value) == SELF
    assert calls == []


def test_the_tests_step_reports_the_same_session_failure_as_one_line(fake, monkeypatch):
    """REQ-040: brief #505 answer 3 (the tests step fails with that one line)."""
    folder, _ = fake
    plant(folder, session="builder-a", token=uuid.uuid4().hex)
    monkeypatch.setenv("AGK_SESSION", "builder-a")
    shown = {"runs": [], "regression": {"table": True}}

    def run(cmd, cwd, env=None):
        return 0, json.dumps(shown)

    monkeypatch.setattr(prepush, "run", run)
    monkeypatch.setattr(prepush, "proof_timeout", lambda root: 60)
    monkeypatch.setattr(prepush, "impact", lambda root, mb, head: {})
    monkeypatch.setattr(prepush, "proof_areas", lambda root: [])
    monkeypatch.setattr(prepush, "gate", lambda *a: pytest.fail("the gate ran"))
    step = prepush.tests(SCRIPTS.parents[1], "HEAD", quick=False)
    assert step.outcome == "FAIL"
    assert step.text == SELF


def test_an_empty_session_never_fails_on_an_empty_owner_session(fake, monkeypatch):
    """REQ-040: brief #505 answer 3 (only a non-empty `AGK_SESSION` counts as the same)."""
    folder, calls = fake
    plant(folder, session="", token=uuid.uuid4().hex)
    taken = prepush.take_lock(Path("/nonexistent"))
    assert taken is not None
    assert len(calls) == 1


def test_the_direct_parent_case_is_unchanged(fake, monkeypatch, capsys):
    """REQ-040: brief #505 answer 2 (the direct-parent rule stays: no token in the environment)."""
    folder, calls = fake
    plant(folder, session="builder-a", token=uuid.uuid4().hex, pid=424_242)
    monkeypatch.setattr(prepush.os, "getppid", lambda: 424_242)
    monkeypatch.setenv("AGK_SESSION", "builder-a")
    assert prepush.take_lock(Path("/nonexistent")) is None
    assert calls == []
    assert CALLER in capsys.readouterr().out


def test_the_direct_child_case_is_unchanged(fake, monkeypatch):
    """REQ-040: brief #505 answer 2 (the recorded command pid is this process)."""
    folder, _ = fake
    held = plant(
        folder, session="builder-a", token=uuid.uuid4().hex, pid=424_243, child=os.getpid()
    )
    assert prepush.caller_slot(held, 1) == held


def settings(repo, folder: Path) -> None:
    repo.commit({"agk.toml": f"lock_dir = '{folder}'\n"}, "settings")


def test_lock_run_gives_its_command_the_token_and_the_name(repo, tmp_path):
    """REQ-040: brief #505 answer 1 (`AGK_LOCK_TOKEN` is the token of the slot taken, beside
    `AGK_LOCK_NAME` and `AGK_LOCK_SESSION`; the token is never printed by lock.py)."""
    folder = tmp_path / "locks"
    settings(repo, folder)
    probe = (
        "import json,os,sys; owner = json.load(open(sys.argv[1]));"
        "print('SAME' if os.environ['AGK_LOCK_TOKEN'] == owner['token'] else 'DIFFERENT');"
        "print('NAME=' + os.environ['AGK_LOCK_NAME']);"
        "print('SESSION=' + os.environ['AGK_LOCK_SESSION'])"
    )
    owner = folder / "agk-lock-heavy" / "owner.json"
    proc = repo.run(
        "lock.py", "run", "--name", "heavy", "--session", "builder-a", "--",
        PY, "-c", probe, str(owner),
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == ["SAME", "NAME=heavy", "SESSION=builder-a"]


def test_prepush_inside_a_wrapper_under_lock_run_never_waits_on_itself(repo, tmp_path):
    """REQ-040: brief #505 answers 1 and 2 (#478: a wrapper process sits between lock.py and
    prepush; prepush finds its caller's slot by the token and does not take it again)."""
    folder = tmp_path / "locks"
    settings(repo, folder)
    inner = (
        "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]);"
        "import prepush; print('TAKEN=' + repr(prepush.take_lock(Path(sys.argv[2]))))"
    )
    wrapper = (
        "import subprocess,sys;"
        "sys.exit(subprocess.run([sys.executable, '-c', sys.argv[1], *sys.argv[2:]],"
        " timeout=20).returncode)"
    )
    proc = repo.run(
        "lock.py", "run", "--name", "heavy", "--session", "builder-a", "--",
        PY, "-c", wrapper, inner, str(SCRIPTS), str(repo.root),
        AGK_SESSION="builder-a",
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert CALLER in proc.stdout
    assert "TAKEN=None" in proc.stdout
    assert "held by this session" not in proc.stdout


def test_the_session_rules_say_wrappers_are_allowed():
    """REQ-040: brief #505 answer 5 (session rule 31 gains one sentence)."""
    text = (SCRIPTS.parents[1] / "config" / "session-rules.md").read_text(encoding="utf-8")
    rule = next(line for line in text.splitlines() if line.startswith("31. "))
    assert "wrapper" in rule
    assert "AGK_LOCK_TOKEN" in rule
