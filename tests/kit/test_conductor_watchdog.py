"""Local mode restarts the conductor unattended (brief #1237, ADR-0525).

REQ-039. `python3 scripts/agk/conductor.py watchdog` is one pass, never a loop: it starts the
conductor through `[flow] launch_adapter` when the lease on the plan issue is free or expired,
starts none while a live conductor holds it, and starts none when the machine's free memory is
below one builder (`builder_memory_gb`). `--install` prints the one scheduler line for the
platform and runs nothing. The adapter is a test double that records its call; the `gh` stub
serves saved copies of the GitHub responses: no terminal, no scheduler, no network.
`doctor.py` names a missing adapter, and the kit ships the two adapters as templates.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest
from test_session import REPO, SCRIPTS, Stub, comment, iso

ROOT = SCRIPTS.parents[1]
GIB = 1024**3
PLAN = f"repos/{REPO}/issues/61/comments"
ADAPTER = """import json, os, sys
with open(sys.argv[1], "a", encoding="utf-8") as log:
    env = {k: os.environ.get(k) for k in ("AGK_SESSION", "AGK_ROLE", "AGK_BRIEF", "AGK_TIER")}
    log.write(json.dumps({**env, "prompt": sys.stdin.read()}) + "\\n")
sys.exit(int(os.environ.get("ADAPTER_EXIT", "0")))
"""


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def world(repo, stub, tmp_path, monkeypatch):
    """A project in local mode: `auto_start` on, an adapter double, a plan issue for the lease,
    the same settings on `origin/main`; `gh` is the stub and the memory is plenty."""
    import common

    double = tmp_path / "adapter.py"
    double.write_text(ADAPTER, encoding="utf-8")
    log = tmp_path / "adapter.log"
    adapter = f"{sys.executable} {double} {log}"
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    toml = (
        'default_branch = "main"\n[flow]\nplan_issue = 61\nauto_start = true\n'
        f"launch_adapter = {json.dumps(adapter)}\nbuilder_memory_gb = 4\n"
    )
    repo.commit(
        {
            "config/reviewers.yaml": "version: 1\nverdict_authors: [boss]\nspec_approvers: [o]\n",
            "agk.toml": toml,
        }
    )
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.setenv("PATH", f"{stub.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_STUB_DIR", str(stub.dir))
    monkeypatch.delenv("ADAPTER_EXIT", raising=False)
    monkeypatch.setattr(common, "available_memory", lambda: 16 * GIB)
    return {"repo": repo, "stub": stub, "log": log, "toml": toml}


def watchdog(world, capsys, *args: str) -> tuple[int, str, str]:
    import conductor

    code = conductor.main(["watchdog", *args], root=world["repo"].root)
    out = capsys.readouterr()
    return code, out.out, out.err


def starts(world) -> list[dict]:
    log = world["log"]
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


def marker(minutes: int, who: str = "c1", kind: str = "active") -> dict:
    stamp = iso(timedelta(minutes=-minutes))
    return comment(5, "boss", f"Conductor: {kind} {stamp} {who}", stamp)


def writes(stub) -> list[list]:
    return [c for c in stub.calls() if c[0] != "GET"]


# --- answer 2: one pass, a free lease starts one conductor, a held lease none ----------------


def test_a_free_lease_starts_one_conductor_through_the_adapter(world, capsys):
    """REQ-039: brief #1237 answer 2 (no marker: the lease is free)."""
    world["stub"].serve(PLAN, [comment(1, "builder", "Request: b1 new", iso())])
    code, out, err = watchdog(world, capsys)
    assert code == 0, err
    got = starts(world)
    assert len(got) == 1
    assert got[0]["AGK_SESSION"] == "conductor-local" and got[0]["AGK_ROLE"] == "conductor"
    assert got[0]["AGK_BRIEF"] is None
    assert "conductor.py lease --take conductor-local" in got[0]["prompt"]
    assert ".claude/agents/conductor.md" in got[0]["prompt"]
    assert "watchdog: lease free" in out and "started conductor-local" in out
    assert writes(world["stub"]) == []  # the conductor takes its own lease; the pass posts nothing


@pytest.mark.parametrize("found", [marker(11), marker(3, kind="released")])
def test_an_expired_or_released_lease_starts_one_conductor(world, capsys, found):
    """REQ-039: brief #1237 answer 2 (free or expired)."""
    world["stub"].serve(PLAN, [found])
    code, _, err = watchdog(world, capsys)
    assert code == 0, err
    assert len(starts(world)) == 1


def test_a_held_lease_starts_none(world, capsys):
    """REQ-039: brief #1237 answer 2 (a live conductor holds the lease: nothing to do)."""
    world["stub"].serve(PLAN, [marker(4, who="c1")])
    code, out, _ = watchdog(world, capsys)
    assert code == 0
    assert starts(world) == []
    assert "watchdog: lease held by c1 until " in out and "nothing started" in out


def test_the_session_option_names_the_conductor(world, capsys):
    """REQ-039: brief #1237 answer 2 (`--session NAME`, the name the lease is taken under)."""
    world["stub"].serve(PLAN, [])
    code, _, err = watchdog(world, capsys, "--session", "night-1")
    assert code == 0, err
    got = starts(world)
    assert got[0]["AGK_SESSION"] == "night-1"
    assert "lease --take night-1" in got[0]["prompt"]


@pytest.mark.parametrize("args", [["--session"], ["--session", "-x"], ["--loop"], ["--x", "y"]])
def test_another_form_is_refused_with_the_usage(world, capsys, args):
    """REQ-039: brief #1237 answer 2 (one pass, no loop)."""
    code, _, err = watchdog(world, capsys, *args)
    assert code == 2 and "watchdog" in err
    assert starts(world) == [] and world["stub"].calls() == []


def test_a_failing_adapter_is_reported_and_its_output_never_echoed(world, capsys, monkeypatch):
    """REQ-039: brief #1237 answer 2 (as `launch.py`: a failing adapter is reported once)."""
    world["stub"].serve(PLAN, [])
    monkeypatch.setenv("ADAPTER_EXIT", "3")
    code, out, err = watchdog(world, capsys)
    assert code == 1
    assert "the adapter failed for conductor-local" in err and "started" not in out


# --- answer 3: memory against builder_memory_gb ---------------------------------------------


def test_low_memory_starts_none_and_says_so(world, capsys, monkeypatch):
    """REQ-039: brief #1237 answer 3 (free memory below one builder: a restart waits)."""
    import common

    monkeypatch.setattr(common, "available_memory", lambda: 3 * GIB)
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys)
    assert code == 1
    assert starts(world) == []
    assert "watchdog: memory 3 GB available, builder_memory_gb 4" in out
    assert "nothing started: free memory is below one builder (setting: builder_memory_gb)" in out


def test_enough_memory_is_printed_before_the_start(world, capsys):
    """REQ-039: brief #1237 answer 3 (the figure is printed against the setting)."""
    world["stub"].serve(PLAN, [])
    _, out, _ = watchdog(world, capsys)
    assert "watchdog: memory 16 GB available, builder_memory_gb 4" in out
    assert out.index("watchdog: memory") < out.index("started conductor-local")


def test_memory_that_cannot_be_read_is_said_and_the_start_goes_ahead(world, capsys, monkeypatch):
    """REQ-039: brief #1237 answer 3 (as `launch.py`'s floor: unread memory is a note)."""
    import common

    monkeypatch.setattr(common, "available_memory", lambda: None)
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys)
    assert code == 0 and "watchdog: memory unknown, builder_memory_gb 4" in out
    assert len(starts(world)) == 1


def test_without_builder_memory_gb_the_memory_is_printed_and_does_not_gate(
    world, capsys, monkeypatch
):
    """REQ-039: brief #1237 answer 3 (no setting, no gate)."""
    import common

    repo = world["repo"]
    repo.commit({"agk.toml": world["toml"].replace("builder_memory_gb = 4\n", "")})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.setattr(common, "available_memory", lambda: 1 * GIB)
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys)
    assert code == 0 and "watchdog: memory 1 GB available, builder_memory_gb unset" in out
    assert len(starts(world)) == 1


def test_the_capacity_table_lowers_builder_memory_gb_as_the_plan_reads_it(
    world, capsys, monkeypatch
):
    """REQ-039: brief #1237 answer 3 (`[capacity] builder_memory_gb`, the smaller of the two)."""
    import common

    repo = world["repo"]
    repo.commit({"agk.toml": world["toml"] + "[capacity]\nbuilder_memory_gb = 2\n"})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.setattr(common, "available_memory", lambda: 3 * GIB)
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys)
    assert code == 0 and "builder_memory_gb 2" in out
    assert len(starts(world)) == 1


# --- what stops a pass before the lease is read ---------------------------------------------


@pytest.mark.parametrize(
    "old, new",
    [
        ("auto_start = true", "auto_start = false"),
        ("launch_adapter", "#launch_adapter"),
    ],
)
def test_without_auto_start_and_an_adapter_nothing_starts(world, capsys, old, new):
    """REQ-039: brief #1237 answers 2 and 4 (the adapter and `auto_start`, as the review pass)."""
    world["repo"].commit({"agk.toml": world["toml"].replace(old, new)})
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys)
    assert code == 1 and starts(world) == []
    assert "(settings: auto_start and launch_adapter in the flow table of agk.toml)" in out


def test_auto_start_off_on_the_default_branch_stops_the_start(world, capsys):
    """REQ-039: brief #1237 answer 2 (the default branch says the same, as for the review pass)."""
    repo = world["repo"]
    repo.commit({"agk.toml": world["toml"].replace("auto_start = true", "auto_start = false")})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    repo.commit({"agk.toml": world["toml"]})
    world["stub"].serve(PLAN, [])
    code, _, _ = watchdog(world, capsys)
    assert code == 1 and starts(world) == []


def test_with_the_lease_off_nothing_starts(world, capsys):
    """REQ-039: brief #1237 answer 2 (no lease, no way to tell a live conductor)."""
    toml = world["toml"].replace("plan_issue = 61\n", "")
    world["repo"].commit({"agk.toml": toml})
    world["repo"].git("update-ref", "refs/remotes/origin/main", "HEAD")
    code, out, _ = watchdog(world, capsys)
    assert code == 1 and starts(world) == []
    assert "lease: off (setting: plan_issue in the flow table of agk.toml)" in out


def test_a_paused_project_starts_nothing(world, capsys):
    """REQ-039: brief #1237 answer 2 and session rule 33 (paused on the default branch)."""
    repo = world["repo"]
    repo.commit({"agk.toml": "paused = true\n" + world["toml"]})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys)
    assert code == 0 and starts(world) == []
    assert "watchdog: agk paused; nothing started" in out


# --- answer 2: --install prints the scheduler line and runs nothing --------------------------


@pytest.mark.parametrize(
    "platform, shape",
    [
        ("win32", r'^schtasks /Create /SC MINUTE /MO 30 /TN "AGK conductor watchdog" /TR '),
        ("linux", r"^\*/30 \* \* \* \* cd "),
        ("darwin", r"^\*/30 \* \* \* \* cd "),
    ],
)
def test_install_prints_the_one_line_for_the_platform_and_runs_nothing(
    world, capsys, monkeypatch, platform, shape
):
    """REQ-039: brief #1237 answer 2 (`--install` prints, never runs)."""
    import conductor

    monkeypatch.setattr(conductor.sys, "platform", platform)
    world["stub"].serve(PLAN, [])
    code, out, _ = watchdog(world, capsys, "--install")
    assert code == 0
    lines = out.splitlines()
    assert len(lines) == 1 and re.search(shape, lines[0])
    assert "conductor.py watchdog" in lines[0] and "git fetch -q origin" in lines[0]
    assert str(world["repo"].root) in lines[0]
    assert starts(world) == [] and world["stub"].calls() == []


def test_install_with_a_session_keeps_it_in_the_line(world, capsys, monkeypatch):
    """REQ-039: brief #1237 answer 2 (the scheduled pass starts the same name)."""
    import conductor

    monkeypatch.setattr(conductor.sys, "platform", "linux")
    code, out, _ = watchdog(world, capsys, "--install", "--session", "night-1")
    assert code == 0 and "conductor.py watchdog --session night-1" in out


def test_the_installed_commands_list_names_the_watchdog():
    """REQ-039: brief #1237 answer 2 (the usage names the new form)."""
    import conductor

    assert "conductor.py watchdog [--session NAME] [--install]" in conductor.USAGE


# --- answer 1: the adapters ship, and doctor names a missing one -----------------------------


def manifest() -> dict:
    return json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))


def guide_block(start: str) -> str:
    """The code block of docs/guides/getting-started.md that starts with the comment START."""
    text = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    first = next(i for i, line in enumerate(lines) if line.strip() == start)
    end = next(i for i in range(first, len(lines)) if lines[i].strip() == "```")
    return "\n".join(line[3:] if line.startswith("   ") else line for line in lines[first:end])


def test_the_kit_installs_both_adapters_as_templates():
    """REQ-039: brief #1237 answer 1 (installed files, the project's own once written)."""
    templates = manifest()["templates"]
    adopt = manifest()["adopt"]["templates"]
    for dest, src in (
        ("scripts/start-session-windows.ps1", "kit/templates/start-session-windows.ps1"),
        ("scripts/start-session-local.sh", "kit/templates/start-session-local.sh"),
    ):
        assert templates[dest] == src and adopt[dest] == src
        assert (ROOT / src).is_file()


def test_the_windows_adapter_is_the_guides_example_unchanged():
    """REQ-039: brief #1237 answer 1 (the guide's example, unchanged in behaviour)."""
    template = (ROOT / "kit" / "templates" / "start-session-windows.ps1").read_text(
        encoding="utf-8"
    )
    rendered = template.rstrip("\n")
    shown = guide_block(rendered.splitlines()[0])
    assert rendered.splitlines() == shown.splitlines()


def git_in(where: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=where, check=True, capture_output=True, text=True
    )
    return done.stdout


@pytest.fixture
def posix(tmp_path):
    """A clone with an origin, the POSIX adapter in it, and a `claude` double on PATH."""
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
    template = (ROOT / "kit" / "templates" / "start-session-local.sh").read_text(encoding="utf-8")
    (work / "start-session-local.sh").write_text(template, encoding="utf-8")
    fake = tmp_path / "bin"
    fake.mkdir()
    claude = fake / "claude"
    claude.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$PWD" "$@" >> "$CLAUDE_SEEN"\nexit 0\n',
        encoding="utf-8",
    )
    claude.chmod(claude.stat().st_mode | stat.S_IXUSR)
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    env.update(
        PATH=f"{fake}{os.pathsep}{env['PATH']}",
        AGK_SESSION="builder-x",
        CLAUDE_SEEN=str(tmp_path / "seen.txt"),
        CLAUDE_CODE_CHILD_SESSION="1",
    )
    return {"work": work, "env": env, "worktree": tmp_path / "agk-builder-x", "tmp": tmp_path}


def start_posix(posix, prompt: str = "hello there"):
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", str(posix["work"] / "start-session-local.sh")], cwd=posix["work"], input=prompt,
        text=True, env=posix["env"], capture_output=True, timeout=60,
    )  # fmt: skip


def ended(posix) -> list[str]:
    exit_file = posix["worktree"] / ".agk-session-exit"
    for _ in range(300):
        if exit_file.exists() and "ended_utc=" in exit_file.read_text(encoding="utf-8"):
            break
        time.sleep(0.1)
    return exit_file.read_text(encoding="utf-8").splitlines()


def seen(posix) -> list[str]:
    path = posix["tmp"] / "seen.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_the_posix_adapter_starts_claude_in_a_worktree_and_writes_the_exit_file(posix):
    """REQ-039: brief #1237 answer 1 (the POSIX twin; `claude` is a test double, no terminal)."""
    done = start_posix(posix)
    assert done.returncode == 0, done.stderr
    lines = ended(posix)
    assert lines[0] == "exit_code=0" and re.fullmatch(
        r"ended_utc=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", lines[1]
    )
    got = seen(posix)
    assert Path(got[0]).resolve() == posix["worktree"].resolve() and "hello there" in got[1:]
    status = git_in(posix["worktree"], "status", "--porcelain", "--untracked-files=all")
    assert status == ""  # the exit file and the log stay out of git


def test_the_posix_adapter_reuses_a_clean_worktree_left_by_an_earlier_start(posix):
    """REQ-039: brief #1237 answer 2 and the fix list on 9c496b9 (Q-1237-1): a restart after a
    crash finds the old folder; a clean worktree of the repository is reused on the default
    branch's newest commit."""
    assert start_posix(posix, "first").returncode == 0
    ended(posix)
    (posix["worktree"] / ".agk-session-exit").unlink()
    git_in(posix["work"], "commit", "-q", "--allow-empty", "-m", "second")
    git_in(posix["work"], "push", "-q", "origin", "HEAD:main")
    done = start_posix(posix, "again")
    assert done.returncode == 0, done.stderr
    assert ended(posix)[0] == "exit_code=0"
    assert "again" in seen(posix)
    head = git_in(posix["worktree"], "rev-parse", "HEAD").strip()
    assert head == git_in(posix["work"], "rev-parse", "HEAD").strip()


def test_the_posix_adapter_refuses_a_left_worktree_with_changes(posix):
    """REQ-039: the fix list on 9c496b9 (a worktree that holds changes is never reused)."""
    assert start_posix(posix, "first").returncode == 0
    ended(posix)
    before = seen(posix)
    (posix["worktree"] / "notes.txt").write_text("work in progress\n", encoding="utf-8")
    done = start_posix(posix, "again")
    assert done.returncode == 2
    assert f"{posix['worktree']} is not clean; nothing started" in done.stderr
    time.sleep(0.5)
    assert seen(posix) == before  # claude was not started again


def test_the_posix_adapter_refuses_a_folder_that_is_not_a_worktree(posix):
    """REQ-039: the fix list on 9c496b9 (a folder of another kind is left alone)."""
    posix["worktree"].mkdir()
    (posix["worktree"] / "keep.txt").write_text("x\n", encoding="utf-8")
    done = start_posix(posix)
    assert done.returncode == 2 and "is not a worktree of this repository" in done.stderr
    assert seen(posix) == []


def test_the_windows_adapter_is_this_repositorys_adapter_with_its_reuse():
    """REQ-039: the fix list on 9c496b9 (the template reuses a clean worktree as this
    repository's own script does, ADR-0439; a first start is `git worktree add` as before).
    The two differ only in comment lines; no PowerShell runs here."""

    def code(text: str) -> list[str]:
        return [line for line in text.splitlines() if not line.strip().startswith("#")]

    template = (ROOT / "kit" / "templates" / "start-session-windows.ps1").read_text(
        encoding="utf-8"
    )
    own = (ROOT / "scripts" / "start-session-windows.ps1").read_text(encoding="utf-8")
    assert code(template) == code(own)
    assert "Test-Path -LiteralPath $worktree" in template
    assert "is not clean; nothing started" in template
    assert "worktree add --detach $worktree origin/main" in template


def write_toml(root: Path, text: str) -> None:
    (root / "agk.toml").write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "platform, file, line",
    [
        (
            "win32",
            "scripts/start-session-windows.ps1",
            'launch_adapter = "pwsh -NoProfile -File scripts/start-session-windows.ps1"',
        ),
        (
            "linux",
            "scripts/start-session-local.sh",
            'launch_adapter = "bash scripts/start-session-local.sh"',
        ),
    ],
)
def test_doctor_names_a_missing_adapter_and_the_line_to_set(tmp_path, platform, file, line):
    """REQ-039: brief #1237 answer 1 (auto_start on, no adapter file: doctor names both)."""
    import doctor

    write_toml(tmp_path, "[flow]\nauto_start = true\n")
    res = doctor.launch_adapter_result(tmp_path, platform)
    assert res.status == "fail" and file in res.message and line in res.message
    write_toml(tmp_path, f"[flow]\nauto_start = true\n{line}\n")
    res = doctor.launch_adapter_result(tmp_path, platform)
    assert res.status == "fail" and file in res.message
    (tmp_path / file).parent.mkdir(parents=True)
    (tmp_path / file).write_text("x\n", encoding="utf-8")
    assert doctor.launch_adapter_result(tmp_path, platform).status == "ok"
    assert doctor.CHECKS["launch-adapter"][0] == "warn"


def test_doctor_never_prints_the_projects_own_adapter(tmp_path):
    """REQ-039: brief #1237 answer 1 and principle 8 (the setting is named, never its value)."""
    import doctor

    write_toml(tmp_path, '[flow]\nauto_start = true\nlaunch_adapter = "sh tools/secret-name.sh"\n')
    res = doctor.launch_adapter_result(tmp_path, "linux")
    assert res.status == "fail" and "secret-name" not in res.message


@pytest.mark.parametrize(
    "text", ["", "[flow]\nauto_start = false\n", '[flow]\nlaunch_adapter = "x.sh"\n']
)
def test_doctor_is_quiet_while_auto_start_is_off(tmp_path, text):
    """REQ-039: brief #1237 answer 1 (only `auto_start` on asks for an adapter)."""
    import doctor

    write_toml(tmp_path, text)
    assert doctor.launch_adapter_result(tmp_path, "linux").status == "ok"


def test_doctor_reads_an_adapter_on_path_as_there(tmp_path):
    """REQ-039: brief #1237 answer 1 (a command with no file of the project is not missing)."""
    import doctor

    write_toml(tmp_path, '[flow]\nauto_start = true\nlaunch_adapter = "my-launcher --cloud"\n')
    assert doctor.launch_adapter_result(tmp_path, "linux").status == "ok"
