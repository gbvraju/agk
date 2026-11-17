"""Kit entry points refuse in one plain line, never a Python traceback (brief #1452, ADR-0610).

REQ-071 AC8: *the same in every mode, personal mode too.* `autopilot.py`, `session.py` and
`conductor.py` turn a `CheckError` into one refusal line on a non-zero exit; any other exception
keeps its traceback. In a clone with no `agk.toml` and a sidecar the line ends
`(personal mode: pass --root <the sidecar's folder>)`, naming the option and never the path.
A temporary clone, a fake sidecar under a temporary `AGK_HOME` and a `gh` stub that fails every
call only; invented data (`member-example-1`, `example.com`); no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import autopilot  # noqa: E402
import personal_state as ps  # noqa: E402

HINT = " (personal mode: pass --root <the sidecar's folder>)"
BRIEFS = "rule 3: the open briefs cannot be read"


def git(where: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=where, check=True, capture_output=True)  # nosec B603 B607


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    path = tmp_path / "widgets"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false",
        "commit", "-q", "--allow-empty", "-m", "initial")  # fmt: skip
    git(path, "remote", "add", "origin", "https://github.com/example/widgets.git")
    return path


def env_for(tmp_path: Path) -> dict[str, str]:
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "gh").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (stub / "gh").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "AGK_HOME")}
    env.update(AGK_HOME=str(tmp_path / "home"), GIT_CONFIG_NOSYSTEM="1")
    env["PATH"] = f"{stub}{os.pathsep}{env.get('PATH', '')}"
    return env


def attach(clone: Path, env: dict[str, str]) -> str:
    proc = run(clone, env, "personal_state.py", "attach", "--person", "member-example-1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.split()[-1]


def run(clone: Path, env: dict[str, str], script: str, *args: str):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=clone, env=env, capture_output=True, text=True, timeout=120,
    )  # fmt: skip


def one_line(text: str) -> str:
    assert "Traceback" not in text
    lines = text.strip().splitlines()
    assert len(lines) == 1, text
    return lines[0]


@pytest.mark.skipif(os.name == "nt", reason="the gh stub is a POSIX shell script")
def test_autopilot_next_in_personal_mode_refuses_with_the_root_hint(clone, tmp_path):
    """REQ-071 AC8: answers 1 and 2 (the case that prompted the brief: no `--root`, a sidecar)."""
    env = env_for(tmp_path)
    sidecar = attach(clone, env)
    proc = run(clone, env, "autopilot.py", "next")
    assert proc.returncode == 1
    assert one_line(proc.stderr) == f"refused: {BRIEFS}{HINT}"
    assert sidecar not in proc.stderr + proc.stdout
    assert str(tmp_path) not in proc.stderr + proc.stdout


@pytest.mark.skipif(os.name == "nt", reason="the gh stub is a POSIX shell script")
def test_autopilot_without_a_sidecar_refuses_without_the_hint(clone, tmp_path):
    """REQ-071 AC8: answer 1 (one line in every mode; the hint only where a sidecar exists)."""
    proc = run(clone, env_for(tmp_path), "autopilot.py", "next")
    assert proc.returncode == 1
    assert one_line(proc.stderr) == f"refused: {BRIEFS}"


@pytest.mark.skipif(os.name == "nt", reason="the gh stub is a POSIX shell script")
def test_session_plan_refuses_in_one_line(clone, tmp_path):
    """REQ-071 AC8: answer 4 (a `CheckError` in `session.py plan`)."""
    env = env_for(tmp_path)
    attach(clone, env)
    proc = run(clone, env, "session.py", "plan")
    assert proc.returncode == 2
    assert one_line(proc.stdout) == f"FAIL session: {BRIEFS}{HINT}"
    assert "Traceback" not in proc.stderr


@pytest.mark.skipif(os.name == "nt", reason="the gh stub is a POSIX shell script")
def test_conductor_sweep_refuses_in_one_line(clone, tmp_path):
    """REQ-071 AC8: answer 4 (a `CheckError` in `conductor.py sweep`)."""
    env = env_for(tmp_path)
    attach(clone, env)
    proc = run(clone, env, "conductor.py", "sweep")
    assert proc.returncode == 1
    line = one_line(proc.stderr)
    assert line.startswith("FAIL conductor: ") and line.endswith(HINT)


def test_an_unrelated_exception_keeps_its_traceback(monkeypatch, tmp_path):
    """REQ-071 AC8: answer 1 (any other exception keeps today's behaviour)."""

    def broken(root, brief, now):
        raise RuntimeError("an unrelated fault")

    monkeypatch.setattr(autopilot, "next_command", broken)
    with pytest.raises(RuntimeError, match="unrelated"):
        autopilot.main(["next", "--root", str(tmp_path)])


def test_a_check_error_in_main_is_one_line_with_exit_1(monkeypatch, tmp_path, capsys):
    """REQ-071 AC8: answer 1 (`refused: <message>` on standard error, exit 1, nothing on stdout)."""

    def refusing(root, brief, now):
        raise autopilot.CheckError("the open pull requests and briefs cannot be read")

    monkeypatch.setattr(autopilot, "next_command", refusing)
    assert autopilot.main(["next", "--root", str(tmp_path)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "refused: the open pull requests and briefs cannot be read\n"


def test_no_hint_where_agk_is_installed(clone, tmp_path, monkeypatch):
    """REQ-071 AC8: answer 2 (an `agk.toml` with a version: team mode, no personal-mode tail)."""
    monkeypatch.setenv("AGK_HOME", str(tmp_path / "home"))
    (clone / "agk.toml").write_text('version = "0.0.1"\n', encoding="utf-8")
    assert ps.root_hint(clone) == ""
    assert ps.root_hint(tmp_path / "not-a-clone") == ""
