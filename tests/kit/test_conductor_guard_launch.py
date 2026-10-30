"""The conductor guard and the re-plan at the end of a review pass (brief #331, ADR-0190).

REQ-041. The pass reads the plan with `python3 scripts/agk/session.py plan --json` (answer 1), and
prints the ready-to-paste prompts with `python3 scripts/agk/launch.py prompts --plan <scratch file>`
while `auto_start` is off (answer 2). Only when `[flow] auto_start = true` and `launch_adapter` are
both set in agk.toml does the guard allow the one command that starts sessions,
`python3 scripts/agk/launch.py prompts --plan <scratch file> --adapter <launch_adapter>`, with the
adapter exactly as configured; every other spelling stays denied. No test uses the network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "conductor_guard.py"
RULE = "conductor guard rule 6: this command is not on the conductor's list"
SESSION = "scripts/agk/session.py"
LAUNCH = "scripts/agk/launch.py"
ADAPTER = "scripts/start-session.sh --cloud"


@pytest.fixture
def tmp(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("systmp")
    (root / "agk-conductor-1").mkdir()
    return root


def git(root: Path, *args: str, text: str | None = None) -> str:
    env = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(root),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args],
        input=text,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    ).stdout.strip()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    for name in ("session.py", "launch.py"):
        (root / "scripts" / "agk" / name).write_text("print('x')\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", "https://github.com/o/r.git")
    return root


def commit_with(project: Path, text: str | None, ref: str = "main") -> str:
    """Point `origin/REF` at a commit whose agk.toml is TEXT (None: a commit without agk.toml)."""
    entries = ""
    if text is not None:
        blob = git(project, "hash-object", "-w", "--stdin", text=text)
        entries = f"100644 blob {blob}\tagk.toml\n"
    tree = git(project, "mktree", text=entries)
    commit = git(project, "commit-tree", tree, "-m", ref, text="")
    git(project, "update-ref", f"refs/remotes/origin/{ref}", commit)
    return commit


def settings(project: Path, text: str, default: str | None | bool = True) -> None:
    """The checkout's agk.toml is TEXT; the default branch's is the same unless DEFAULT is given
    (a text, None for a commit without agk.toml, False for no default branch at all)."""
    full = f'default_branch = "main"\n{text}'
    (project / "agk.toml").write_text(full, encoding="utf-8")
    if default is not False:
        commit_with(project, full if default is True else (default or None))


def on(project: Path, adapter: str = ADAPTER) -> None:
    settings(project, f"[flow]\nauto_start = true\nlaunch_adapter = {json.dumps(adapter)}\n")


def plan_file(tmp: Path, name: str = "agk-conductor-1/plan.json") -> Path:
    path = tmp / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"start": []}\n', encoding="utf-8")
    return path


def run_hook(command: str, project: Path, tmp: Path, shadow: bool = False):
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project), "TMPDIR": str(tmp)}
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(project)}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *(["--shadow"] if shadow else [])],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project),
    )


def allowed(out) -> bool:
    return out.returncode == 0 and out.stdout == ""


def denied(out) -> bool:
    if out.returncode != 0 or not out.stdout.strip():
        return False
    found = json.loads(out.stdout)["hookSpecificOutput"]
    return found["permissionDecision"] == "deny" and found["permissionDecisionReason"] == RULE


def start(plan: Path, adapter: str = ADAPTER) -> str:
    return f"python3 {LAUNCH} prompts --plan {plan} --adapter {json.dumps(adapter)}"


# --- answer 1: the plan is read at the end of every pass -----------------------------------------


@pytest.mark.parametrize("toml", ["", "[flow]\nauto_start = true\nlaunch_adapter = 'x'\n"])
def test_the_plan_as_data_is_read_whatever_the_settings(project, tmp, toml):
    """REQ-041: brief #331 answer 1 (the pass runs `session.py plan --json`; it posts nothing)."""
    settings(project, toml)
    assert allowed(run_hook(f"python3 {SESSION} plan --json", project, tmp))


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SESSION} plan",
        f"python3 {SESSION} plan --json --all",
        f"python3 {SESSION} plan -j",
    ],
)
def test_no_other_form_of_the_plan_is_allowed(project, tmp, command):
    """REQ-041: brief #331 answer 2 (nothing else new)."""
    assert denied(run_hook(command, project, tmp))


# --- answer 2: off, the prompts are printed; on, the one configured adapter ---------------------


@pytest.mark.parametrize("toml", ["", "[flow]\nauto_start = false\nlaunch_adapter = 'x'\n"])
def test_with_auto_start_off_the_prompts_are_printed_and_no_adapter_runs(project, tmp, toml):
    """REQ-041: brief #331 answer 2 (off, the pass prints the ready-to-paste prompts)."""
    settings(project, toml)
    plan = plan_file(tmp)
    assert allowed(run_hook(f"python3 {LAUNCH} prompts --plan {plan}", project, tmp))
    assert denied(run_hook(start(plan, "x"), project, tmp))


def test_with_both_settings_the_configured_adapter_is_allowed(project, tmp):
    """REQ-041: brief #331 answer 2 (the guard allows exactly that one command)."""
    on(project)
    plan = plan_file(tmp)
    assert allowed(run_hook(start(plan), project, tmp))
    assert allowed(run_hook(f"python3 {project / LAUNCH} prompts --plan {plan}", project, tmp))


@pytest.mark.parametrize(
    "toml",
    [
        "[flow]\nauto_start = true\n",
        "[flow]\nauto_start = true\nlaunch_adapter = ''\n",
        "[flow]\nauto_start = 'true'\nlaunch_adapter = 'scripts/start-session.sh --cloud'\n",
        "[flow]\nauto_start = 1\nlaunch_adapter = 'scripts/start-session.sh --cloud'\n",
        "[flow]\nauto_start = true\nlaunch_adapter = ['scripts/start-session.sh']\n",
        "auto_start = true\nlaunch_adapter = 'scripts/start-session.sh --cloud'\n",
        "[flow\nauto_start = true\n",
    ],
)
def test_without_both_settings_well_formed_no_adapter_runs(project, tmp, toml):
    """REQ-041: brief #331 answer 2 (both settings, in the flow table; a bad file fails closed)."""
    settings(project, toml)
    assert denied(run_hook(start(plan_file(tmp)), project, tmp))


def test_without_an_agk_toml_no_adapter_runs(project, tmp):
    """REQ-041: brief #331 answer 2 (`auto_start` is false by default)."""
    assert denied(run_hook(start(plan_file(tmp)), project, tmp))


@pytest.mark.parametrize(
    "spelling",
    [
        "python3 {L} prompts --plan {p} --adapter scripts/start-session.sh",
        "python3 {L} prompts --plan {p} --adapter 'scripts/start-session.sh --cloud --x'",
        "python3 {L} prompts --plan {p} --adapter 'scripts/start-session.sh  --cloud'",
        "python3 {L} prompts --plan {p} --adapter other.sh",
        "python3 {L} prompts --adapter 'scripts/start-session.sh --cloud' --plan {p}",
        "python3 {L} prompts --plan {p} --adapter 'scripts/start-session.sh --cloud' --x y",
        "python3 {L} prompts --plan {p} --adapter=scripts/start-session.sh",
        "python3 {L} prompts --plan - --adapter 'scripts/start-session.sh --cloud'",
        "python3 {L} prompts --plan /etc/passwd --adapter 'scripts/start-session.sh --cloud'",
        "python3 {L} prompts --plan {p}x --adapter 'scripts/start-session.sh --cloud'",
        "python3 {L} prompt --plan {p} --adapter 'scripts/start-session.sh --cloud'",
        "python3 -I {L} prompts --plan {p} --adapter 'scripts/start-session.sh --cloud'",
        "python3 scripts/agk/route.py prompts --plan {p} --adapter scripts/start-session.sh",
        "python3 /elsewhere/{L} prompts --plan {p} --adapter 'scripts/start-session.sh --cloud'",
        "env X=1 python3 {L} prompts --plan {p} --adapter 'scripts/start-session.sh --cloud'",
        "python3 {L} prompts --plan {p} --adapter 'scripts/start-session.sh --cloud'; id",
        "python3 {S} plan --json | python3 {L} prompts --plan - --adapter 'x --cloud'",
        "scripts/start-session.sh --cloud",
    ],
)
def test_every_other_spelling_is_denied(project, tmp, spelling):
    """REQ-041: brief #331 answers 2 and 5 (the guard allows only the configured command)."""
    on(project)
    command = spelling.format(L=LAUNCH, S=SESSION, p=plan_file(tmp))
    assert denied(run_hook(command, project, tmp))


def test_a_plan_file_outside_a_scratch_directory_or_through_a_link_is_denied(project, tmp):
    """REQ-041: brief #331 answer 2 (the plan is a regular file of a scratch directory)."""
    on(project)
    outside = tmp / "plan.json"
    outside.write_text("{}", encoding="utf-8")
    link = tmp / "agk-conductor-1" / "link.json"
    link.symlink_to(outside)
    for path in (outside, link, tmp / "agk-conductor-1", tmp / "agk-conductor-1" / "none.json"):
        assert denied(run_hook(start(path), project, tmp)), path
        assert denied(run_hook(f"python3 {LAUNCH} prompts --plan {path}", project, tmp)), path


def test_the_shadow_reviewer_starts_nothing_and_reads_no_plan(project, tmp):
    """REQ-041: brief #331 answer 2 (nothing new for the shadow)."""
    on(project)
    plan = plan_file(tmp)
    for command in (start(plan), f"python3 {LAUNCH} prompts --plan {plan}"):
        assert denied(run_hook(command, project, tmp, shadow=True))
    assert denied(run_hook(f"python3 {SESSION} plan --json", project, tmp, shadow=True))


@pytest.mark.parametrize(
    "command",
    [
        "python3 scripts/agk/session.py claim --session builder-a --brief 9",
        "python3 scripts/agk/session.py next --session builder-a",
    ],
)
def test_the_conductor_never_claims_for_a_started_session(project, tmp, command):
    """REQ-041: brief #331 answer 4 (the `taken:` claim is made by the started session itself)."""
    on(project)
    assert not allowed(run_hook(command, project, tmp))


# --- the default branch decides as well (the verdict on 2d53a5d, item 2) -------------------------

YES = f"[flow]\nauto_start = true\nlaunch_adapter = {json.dumps(ADAPTER)}\n"
OFF = 'default_branch = "main"\n[flow]\nauto_start = false\nlaunch_adapter = "x"\n'


@pytest.mark.parametrize(
    "default",
    [
        OFF,
        f'default_branch = "main"\n[flow]\nlaunch_adapter = {json.dumps(ADAPTER)}\n',
        'default_branch = "main"\n[flow]\nauto_start = true\nlaunch_adapter = "other.sh"\n',
        'default_branch = "main"\n[flow\n',
        None,
    ],
)
def test_a_checkout_that_says_yes_and_a_default_branch_that_says_no_starts_nothing(
    project, tmp, default
):
    """REQ-041: brief #331 answer 2 (the checkout and the default branch both say yes)."""
    on(project)
    commit_with(project, default)
    assert denied(run_hook(start(plan_file(tmp)), project, tmp))
    assert allowed(run_hook(f"python3 {LAUNCH} prompts --plan {plan_file(tmp)}", project, tmp))


def test_without_the_default_branch_no_adapter_runs(project, tmp):
    """REQ-041: brief #331 answer 2 (no `origin/<default branch>` that git can read)."""
    settings(project, YES, default=False)
    assert denied(run_hook(start(plan_file(tmp)), project, tmp))


def test_the_default_branch_is_the_one_agk_toml_names(project, tmp):
    """REQ-041: brief #331 answer 2 (`default_branch` of agk.toml names the branch read)."""
    full = f'default_branch = "trunk"\n{YES}'
    (project / "agk.toml").write_text(full, encoding="utf-8")
    commit_with(project, OFF)
    commit_with(project, full, ref="trunk")
    assert allowed(run_hook(start(plan_file(tmp)), project, tmp))
    commit_with(project, OFF, ref="trunk")
    assert denied(run_hook(start(plan_file(tmp)), project, tmp))


@pytest.mark.parametrize("name", ["-x", "a b", "../x", "x..y", "main:agk.toml", 5])
def test_a_default_branch_that_is_not_a_branch_name_starts_nothing(project, tmp, name):
    """REQ-041: brief #331 answer 2 (a name git would read as an option or a path is refused)."""
    commit_with(project, f"default_branch = {json.dumps(name)}\n{YES}")
    (project / "agk.toml").write_text(f"default_branch = {json.dumps(name)}\n{YES}", "utf-8")
    assert denied(run_hook(start(plan_file(tmp)), project, tmp))
