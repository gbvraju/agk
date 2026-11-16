"""The adapters run jobs in the background with a log each; a tab only with show_jobs (brief #1388).

REQ-071 AC3, SPEC-0064 rules 3 and 5, build (e), ADR-0588. Both adapters start a job headless in its
worktree with no terminal tab and its output in `<worktree>/.agk-session.log`, beside the record and
the exit file; with `[autopilot] show_jobs = true`, which `launch.py` hands the adapter as
`AGK_SHOW_JOBS`, the job also shows in a tab that closes when it ends. The POSIX adapter runs with
a `claude` double and a `gnome-terminal` double on PATH (the double runs its command and returns,
as a tab that closes at the end); the Windows adapter is read as text, and its wrapper runs under
`pwsh` only where it is installed. No terminal, no network, invented data only.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POSIX = ROOT / "kit" / "templates" / "start-session-local.sh"
WINDOWS = ROOT / "kit" / "templates" / "start-session-windows.ps1"
SESSION = "cb-example-1"


def git_in(where: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=where, check=True, capture_output=True, text=True
    )
    return done.stdout


def executable(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def posix(tmp_path):
    """A clone with an origin, the POSIX adapter in it, and the two doubles on PATH."""
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
    fake = tmp_path / "bin"
    fake.mkdir()
    executable(fake / "claude", 'printf "%s\\n" "$@" > "$CLAUDE_SEEN"\necho "job output"\nexit 0\n')
    # A tab that runs its command and closes when it ends: the arguments, then the command after --.
    executable(
        fake / "gnome-terminal",
        'printf "%s\\n" "$@" > "$TAB_SEEN"\nwhile [ "$1" != "--" ]; do shift; done\nshift\n"$@"\n',
    )
    drop = ("DISPLAY", "WAYLAND_DISPLAY", "AGK_MODEL", "AGK_EFFORT", "AGK_SHOW_JOBS")
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(
        PATH=f"{fake}{os.pathsep}{env['PATH']}",
        AGK_SESSION=SESSION,
        CLAUDE_SEEN=str(tmp_path / "seen.txt"),
        TAB_SEEN=str(tmp_path / "tab.txt"),
        DISPLAY=":0",  # a desktop is there: before this build, a tab opened for every job
    )
    return {"work": work, "env": env, "worktree": tmp_path / f"agk-{SESSION}", "tmp": tmp_path}


def run_posix(posix, **extra: str) -> dict:
    env = {**posix["env"], **extra}
    for name, value in extra.items():
        if value is None:
            env.pop(name)
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", str(posix["work"] / "start-session-local.sh")], cwd=posix["work"],
        input="build it", text=True, env=env, capture_output=True, timeout=60,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    exit_file = posix["worktree"] / ".agk-session-exit"
    for _ in range(300):
        if exit_file.exists() and "ended_utc=" in exit_file.read_text(encoding="utf-8"):
            break
        time.sleep(0.1)
    assert exit_file.read_text(encoding="utf-8").splitlines()[0] == "exit_code=0"
    tab = posix["tmp"] / "tab.txt"
    log = posix["worktree"] / ".agk-session.log"
    return {
        "claude": (posix["tmp"] / "seen.txt").read_text(encoding="utf-8").splitlines(),
        "tab": tab.read_text(encoding="utf-8").splitlines() if tab.exists() else None,
        "log": log.read_text(encoding="utf-8") if log.exists() else None,
    }


@pytest.mark.parametrize("show", [None, "false", "", "yes"])
def test_the_posix_adapter_runs_a_job_in_the_background_with_a_log_even_on_a_desktop(posix, show):
    """REQ-071 AC3: rules 3 and 5 (no tab, one log per job, headless; only `true` shows one)."""
    got = run_posix(posix, AGK_SHOW_JOBS=show)
    assert got["tab"] is None  # no terminal tab was opened
    assert got["claude"] == ["-p", "build it"]
    assert "job output" in got["log"]
    status = git_in(posix["worktree"], "status", "--porcelain", "--untracked-files=all")
    assert status == ""  # the log, the record and the exit file stay out of git


def test_the_posix_adapter_shows_a_tab_that_closes_with_show_jobs(posix):
    """REQ-071 AC3: rule 5 (`show_jobs = true`: one tab, the job still headless and logged; the
    tab runs the job's wrapper alone, so it closes when the job ends)."""
    got = run_posix(posix, AGK_SHOW_JOBS="true")
    assert got["tab"] is not None and got["tab"][:3] == ["--tab", "--title", SESSION]
    command = got["tab"][got["tab"].index("--") + 1 :]
    assert command[:2] == ["bash", "-c"] and "exec bash" not in " ".join(command)
    assert got["claude"] == ["-p", "build it"]
    assert "job output" in got["log"]


def test_the_posix_adapter_without_a_desktop_stays_in_the_background_with_show_jobs(posix):
    """REQ-071 AC3: rule 5 (no desktop: no tab can show, the job runs as without the setting)."""
    got = run_posix(posix, AGK_SHOW_JOBS="true", DISPLAY=None)
    assert got["tab"] is None and "job output" in got["log"]


# --- the Windows adapter -----------------------------------------------------------------------


def windows() -> str:
    return WINDOWS.read_text(encoding="utf-8")


def wrapper_of(script: str) -> str:
    found = re.search(r"@'\n(.*?)\n'@", script, re.S)
    assert found, "the adapter writes no wrapper"
    return found.group(1)


def test_the_windows_adapter_starts_a_job_hidden_and_opens_a_tab_only_with_show_jobs():
    """REQ-071 AC3: rules 3 and 5 (no Windows Terminal for a job; `wt` only under show_jobs)."""
    script = windows()
    start = script.find("# 3. ")
    assert start != -1
    tail = script[start:]
    assert "$show = $env:AGK_SHOW_JOBS -eq 'true'" in script[:start]
    show, hidden = tail.find("if ($show) {"), tail.find("} else {")
    assert -1 < show < tail.find("wt -w 0 new-tab") < hidden
    background = tail[hidden:]
    assert "Start-Process" in background and "-WindowStyle Hidden" in background
    assert "wt " not in background
    assert script.count("wt -w 0 new-tab") == 1


def test_the_windows_wrapper_runs_claude_headless_and_writes_the_log():
    """REQ-071 AC3: rule 3 (`-p`, the output in `.agk-session.log`; show_jobs tees to the tab)."""
    wrapper = wrapper_of(windows())
    assert "'.agk-session.log'" in wrapper
    assert "& claude @flags -p $prompt" in wrapper
    assert "Tee-Object" in wrapper and "show.txt" in wrapper
    assert "& claude @flags $prompt" not in wrapper  # no interactive session in a tab


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="needs PowerShell 7 (pwsh)")
@pytest.mark.parametrize("show", ["false", "true"])
def test_the_windows_wrapper_logs_the_job_in_both_modes(tmp_path, show):
    """REQ-071 AC3: rule 3 (the wrapper run with the `claude` double; PATH reset dropped)."""
    lines, kept, skip = wrapper_of(windows()).splitlines(), [], False
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
    (tmp_path / "prompt.txt").write_text("build it", encoding="utf-8")
    (tmp_path / "show.txt").write_text(show, encoding="utf-8")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    fake = tmp_path / "bin"
    fake.mkdir()
    executable(fake / "claude", 'printf "%s\\n" "$@" > "$CLAUDE_SEEN"\necho "job output"\nexit 0\n')
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"}
    env["CLAUDE_SEEN"] = str(tmp_path / "seen.txt")
    args = [str(worktree), str(tmp_path / "prompt.txt"), str(tmp_path), SESSION, "1388"]
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["pwsh", "-NoProfile", "-File", str(run), *args], env=env, capture_output=True,
        text=True, timeout=120,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "seen.txt").read_text(encoding="utf-8").splitlines() == ["-p", "build it"]
    assert "job output" in (worktree / ".agk-session.log").read_text(encoding="utf-8")


# --- launch.py passes the choice -------------------------------------------------------------


@pytest.fixture
def launch_mod():
    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    import launch

    return launch


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", False),
        ("[autopilot]\n", False),
        ("[autopilot]\nshow_jobs = false\n", False),
        ("[autopilot]\nshow_jobs = true\n", True),
    ],
)
def test_show_jobs_is_off_unless_the_autopilot_table_turns_it_on(
    tmp_path, launch_mod, text, expected
):
    """REQ-071 AC3: rule 5 (`[autopilot] show_jobs`, default false)."""
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    assert launch_mod.show_jobs(tmp_path) is expected


def test_show_jobs_of_another_kind_is_refused_naming_the_setting(tmp_path, launch_mod):
    """REQ-071 AC3: principle 8 (the setting is named, never the value)."""
    (tmp_path / "agk.toml").write_text('[autopilot]\nshow_jobs = "x-odd"\n', encoding="utf-8")
    with pytest.raises(launch_mod.CheckError) as raised:
        launch_mod.show_jobs(tmp_path)
    assert "show_jobs" in str(raised.value) and "autopilot" in str(raised.value)
    assert "x-odd" not in str(raised.value)


def env_adapter(tmp_path: Path) -> str:
    """An adapter that writes the AGK_SHOW_JOBS it was given into a file per session."""
    script = tmp_path / "adapter.py"
    script.write_text(
        "import os, pathlib, sys\nsys.stdin.read()\n"
        "out = pathlib.Path(os.environ['SEEN_DIR']) / os.environ['AGK_SESSION']\n"
        "out.write_text(os.environ.get('AGK_SHOW_JOBS', '<unset>'), encoding='utf-8')\n",
        encoding="utf-8",
    )
    return f'"{sys.executable}" "{script}"'


@pytest.mark.parametrize("value, expected", [(None, "false"), ("true", "true")])
def test_launch_hands_show_jobs_to_the_adapter(tmp_path, monkeypatch, launch_mod, value, expected):
    """REQ-071 AC3: rule 5 (`launch.py` passes the choice through the adapter's environment, for a
    builder start and for a role start)."""
    root = tmp_path / "proj"
    root.mkdir()
    table = f"[autopilot]\nshow_jobs = {value}\n" if value else ""
    (root / "agk.toml").write_text(table, encoding="utf-8")
    seen = tmp_path / "seen"
    seen.mkdir()
    monkeypatch.setenv("SEEN_DIR", str(seen))
    monkeypatch.setenv("AGK_SHOW_JOBS", "stale")  # the setting wins over an inherited value
    monkeypatch.chdir(root)
    adapter = env_adapter(tmp_path)
    assert launch_mod.start_with(adapter, [(SESSION, 1388, None)], root=root) == 0
    assert launch_mod.role_main(["role", "--role", "steward", "--session", "cb-example-2",
                                 "--adapter", adapter]) == 0  # fmt: skip
    assert (seen / SESSION).read_text(encoding="utf-8") == expected
    assert (seen / "cb-example-2").read_text(encoding="utf-8") == expected


def test_the_local_mode_guide_names_the_background_mode_the_log_and_show_jobs():
    """REQ-071 AC3: brief #1388 answer 3."""
    guide = (ROOT / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    part = guide[guide.find("## Running unattended") :]
    part = part[: part.find("\n## ", 5)]
    assert "in the background" in part and ".agk-session.log" in part
    assert "[autopilot]" in part and "show_jobs = true" in part
