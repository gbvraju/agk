"""Adapter-started builders run on the model their brief's kind needs (brief #1252, ADR-0530).

REQ-052. `launch.py` hands the launch adapter `AGK_MODEL` (the tier's name from `[models.names]`)
and `AGK_EFFORT`. Both adapter templates pass `--model <name>` to `claude` when `AGK_MODEL` is set,
and `--effort <level>` beside it when `AGK_EFFORT` is set too; with no `AGK_MODEL` they pass no
flag, today's command. The POSIX adapter runs with a `claude` test double on PATH, in the
background (no desktop); the Windows wrapper runs under `pwsh` where it is installed, with its
PATH reset removed (the reset reads the Windows registry). `doctor.py` warns `model-names` when
`auto_start` is on and `launch_adapter` is set without `[models.names]`. No terminal, no network.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POSIX = ROOT / "kit" / "templates" / "start-session-local.sh"
WINDOWS = ROOT / "kit" / "templates" / "start-session-windows.ps1"
MODEL = "example-mid-1"


def git_in(where: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=where, check=True, capture_output=True, text=True
    )
    return done.stdout


def double(folder: Path) -> Path:
    """A `claude` test double that writes each of its arguments on a line of $CLAUDE_SEEN."""
    folder.mkdir(exist_ok=True)
    claude = folder / "claude"
    claude.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CLAUDE_SEEN"\nexit 0\n', encoding="utf-8"
    )
    claude.chmod(claude.stat().st_mode | stat.S_IXUSR)
    return folder


@pytest.fixture
def posix(tmp_path):
    """A clone with an origin, the POSIX adapter in it, and the `claude` double on PATH."""
    if shutil.which("bash") is None:
        pytest.skip("needs bash")
    origin, work = tmp_path / "origin.git", tmp_path / "proj"
    git_in(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git_in(tmp_path, "clone", "-q", str(origin), str(work))
    for args in (
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "t"],
        ["config", "commit.gpgsign", "false"],
        ["commit", "-q", "--allow-empty", "-m", "first"],
        ["push", "-q", "origin", "HEAD:main"],
    ):
        git_in(work, *args)
    (work / "start-session-local.sh").write_text(POSIX.read_text(encoding="utf-8"), "utf-8")
    fake = double(tmp_path / "bin")
    drop = ("DISPLAY", "WAYLAND_DISPLAY", "AGK_MODEL", "AGK_EFFORT", "AGK_TIER", "AGK_KIND")
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(
        PATH=f"{fake}{os.pathsep}{env['PATH']}",
        AGK_SESSION="builder-m",
        CLAUDE_SEEN=str(tmp_path / "seen.txt"),
    )
    return {"work": work, "env": env, "worktree": tmp_path / "agk-builder-m", "tmp": tmp_path}


def run_posix(posix, **extra: str) -> list[str]:
    """Start the adapter with EXTRA in its environment; the arguments `claude` was given."""
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", str(posix["work"] / "start-session-local.sh")], cwd=posix["work"],
        input="build it", text=True, env={**posix["env"], **extra}, capture_output=True,
        timeout=60,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    exit_file = posix["worktree"] / ".agk-session-exit"
    for _ in range(300):
        if exit_file.exists() and "ended_utc=" in exit_file.read_text(encoding="utf-8"):
            break
        time.sleep(0.1)
    assert exit_file.read_text(encoding="utf-8").splitlines()[0] == "exit_code=0"
    return (posix["tmp"] / "seen.txt").read_text(encoding="utf-8").splitlines()


def test_the_posix_adapter_passes_the_model_and_effort_when_the_model_is_set(posix):
    """REQ-052: brief #1252 answers 1 and 4 (`--model <name>` when `AGK_MODEL` is set)."""
    got = run_posix(posix, AGK_MODEL=MODEL, AGK_EFFORT="low", AGK_TIER="mid")
    assert got == ["--model", MODEL, "--effort", "low", "-p", "build it"]


def test_the_posix_adapter_passes_the_model_alone_without_an_effort(posix):
    """REQ-052: brief #1252 answer 1."""
    assert run_posix(posix, AGK_MODEL=MODEL) == ["--model", MODEL, "-p", "build it"]


@pytest.mark.parametrize("extra", [{}, {"AGK_EFFORT": "high", "AGK_TIER": "strongest"}])
def test_the_posix_adapter_passes_no_flag_without_a_model(posix, extra):
    """REQ-052: brief #1252 answers 1 and 4 (no `AGK_MODEL`: today's command, no flag)."""
    assert run_posix(posix, **extra) == ["-p", "build it"]


# --- the Windows adapter -----------------------------------------------------------------------


def wrapper_of(script: str) -> str:
    found = re.search(r"@'\n(.*?)\n'@", script, re.S)
    assert found, "the adapter writes no wrapper"
    return found.group(1)


def test_the_windows_adapter_hands_the_model_and_effort_to_its_tab():
    """REQ-052: brief #1252 answer 1 (the tab starts from the terminal's environment, so the
    model and effort travel as arguments of the wrapper, as the session and brief do)."""
    script = WINDOWS.read_text(encoding="utf-8")
    wrapper = wrapper_of(script)
    assert wrapper.splitlines()[0] == "param($Worktree, $PromptFile, $LongTemp, $Session, $Brief, $Model, $Effort)"
    assert "& claude @flags $prompt" in wrapper
    assert "& claude $prompt" not in wrapper
    tab = script[script.find("wt -w 0 new-tab") :]
    assert "@extra" in tab and "$env:AGK_MODEL" in script


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="needs PowerShell 7 (pwsh)")
@pytest.mark.parametrize(
    "model, effort, expected",
    [
        (MODEL, "medium", ["--model", MODEL, "--effort", "medium", "build it"]),
        (MODEL, None, ["--model", MODEL, "build it"]),
        (None, None, ["build it"]),
    ],
)
def test_the_windows_wrapper_passes_the_model_only_when_set(tmp_path, model, effort, expected):
    """REQ-052: brief #1252 answers 1 and 4 (the wrapper run with the `claude` double)."""
    lines = wrapper_of(WINDOWS.read_text(encoding="utf-8")).splitlines()
    kept, skip = [], False
    for line in lines:  # the PATH reset reads the Windows registry: drop its two lines
        if line.startswith("$env:Path ="):
            skip = True
            continue
        if skip:
            skip = False
            continue
        kept.append(line)
    run = tmp_path / "run.ps1"
    run.write_text("\n".join(kept) + "\n", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("build it", encoding="utf-8")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    fake = double(tmp_path / "bin")
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"}
    env["CLAUDE_SEEN"] = str(tmp_path / "seen.txt")
    args = [str(worktree), str(prompt), str(tmp_path), "builder-w", "1252"]
    args += [a for a in (model, effort) if a]
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["pwsh", "-NoProfile", "-File", str(run), *args], env=env, capture_output=True,
        text=True, timeout=120,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "seen.txt").read_text(encoding="utf-8").splitlines() == expected


# --- doctor ------------------------------------------------------------------------------------


def write_toml(root: Path, text: str) -> None:
    (root / "agk.toml").write_text(text, encoding="utf-8")


ADAPTER_LINE = 'launch_adapter = "bash scripts/start-session-local.sh"\n'


def test_doctor_warns_when_adapter_started_builders_have_no_model_names(tmp_path):
    """REQ-052: brief #1252 answer 3 (one `warn` line naming the table, never a value)."""
    import doctor

    write_toml(tmp_path, "[flow]\nauto_start = true\n" + ADAPTER_LINE)
    res = doctor.model_names_result(tmp_path)
    assert res.status == "fail" and "[models.names]" in res.message
    assert "start-session-local" not in res.message
    assert doctor.CHECKS["model-names"][0] == "warn"
    assert "local-mode.md" in doctor.CHECKS["model-names"][3]


def test_doctor_is_quiet_with_model_names(tmp_path):
    """REQ-052: brief #1252 answer 3."""
    import doctor

    write_toml(
        tmp_path, f'[flow]\nauto_start = true\n{ADAPTER_LINE}[models.names]\nmid = "{MODEL}"\n'
    )
    res = doctor.model_names_result(tmp_path)
    assert res.status == "ok" and MODEL not in res.message


@pytest.mark.parametrize(
    "text", ["", "[flow]\nauto_start = true\n", "[flow]\nauto_start = false\n" + ADAPTER_LINE]
)
def test_doctor_asks_for_model_names_only_with_auto_start_and_an_adapter(tmp_path, text):
    """REQ-052: brief #1252 answer 3 (only `auto_start` on with `launch_adapter` set)."""
    import doctor

    write_toml(tmp_path, text)
    assert doctor.model_names_result(tmp_path).status == "ok"


def test_doctor_names_a_refused_models_table_by_its_setting(tmp_path):
    """REQ-052: principle 8 (a refused table names the setting, never the value)."""
    import doctor

    write_toml(tmp_path, f'[flow]\nauto_start = true\n{ADAPTER_LINE}[models]\nnames = "x-odd"\n')
    res = doctor.model_names_result(tmp_path)
    assert res.status == "fail" and "models.names" in res.message and "x-odd" not in res.message


def test_the_local_mode_guide_names_the_model_table_and_the_conductors_model():
    """REQ-052: brief #1252 answer 2."""
    guide = (ROOT / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    part = guide[guide.find("## Running unattended") :]
    part = part[: part.find("\n## ", 5)]
    assert "[models.names]" in part
    assert 'strongest = "<the project\'s strongest model name>"' in part
    assert 'mid = "<its mid model name>"' in part
    assert "conductor" in part and "strongest model" in part
