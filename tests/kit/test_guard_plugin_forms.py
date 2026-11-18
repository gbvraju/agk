"""Tests of the plugin's form of the kit commands in the role guards (SPEC-0071 rule 4, brief #1500,
ADR-0631; REQ-078).

In a clean project (`[kit] layout = "plugin"`) the conductor's, the architect's and the steward's
guards allow `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/<script>"` wherever they allow
`python3 scripts/agk/<script>` today, with the same arguments, and nothing more. The plugin is this
repository (it holds `.claude-plugin/plugin.json`); the projects are trees of invented data. No
network, no gh, no model.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
PLUGIN = '"${CLAUDE_PLUGIN_ROOT}/scripts/agk/'
SESSION = PLUGIN + 'session.py"'
FULL = "a1b2c3d4e5" * 4
CLEAN = '[kit]\nlayout = "plugin"\n'
FLOW_ON = '[flow]\nauto_merge = true\nauto_merge_method = "squash"\n'
CONDUCTOR_RULE = "conductor guard rule 6: this command is not on the conductor's list"


def git_in(root: Path, *args: str, text: str | None = None) -> str:
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
        ["git", "-C", str(root), *args], input=text, capture_output=True, text=True, check=True,
        env=env,
    ).stdout.strip()  # fmt: skip


def make_project(tmp_path: Path, toml: str, installed: bool = False) -> Path:
    """A project whose checkout and `origin/main` both hold `toml`; with `installed`, the kit's
    scripts are the project's own (today's layout)."""
    root = tmp_path / ("installed" if installed else "clean") / "project"
    root.mkdir(parents=True)
    git_in(root, "init", "-q")
    git_in(root, "remote", "add", "origin", "https://github.com/o/r.git")
    text = f'default_branch = "main"\n{toml}'
    (root / "agk.toml").write_text(text, encoding="utf-8")
    blob = git_in(root, "hash-object", "-w", "--stdin", text=text)
    tree = git_in(root, "mktree", text=f"100644 blob {blob}\tagk.toml\n")
    commit = git_in(root, "commit-tree", tree, "-m", "main", text="")
    git_in(root, "update-ref", "refs/remotes/origin/main", commit)
    if installed:
        (root / "scripts" / "agk").mkdir(parents=True)
        for name in ("session.py", "merge_cleared.py", "conductor.py"):
            (root / "scripts" / "agk" / name).write_text("print('x')\n", encoding="utf-8")
    return root


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    return make_project(tmp_path, CLEAN + FLOW_ON)


@pytest.fixture
def installed(tmp_path: Path) -> Path:
    return make_project(tmp_path, FLOW_ON, installed=True)


def decision(
    hook: str, root: Path, command: str, *flags: str, plugin: Path = ROOT
) -> dict | None:
    temp = root.parent / "systmp"
    temp.mkdir(exist_ok=True)
    env = {
        "PATH": "/usr/bin:/bin",
        "CLAUDE_PROJECT_DIR": str(root),
        "CLAUDE_PLUGIN_ROOT": str(plugin),
        "TMPDIR": str(temp),
        "HOME": str(temp),
    }
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(root)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOKS / hook), *flags],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None


def denied(found: dict | None) -> bool:
    return found is not None and found["permissionDecision"] == "deny"


def allowed(found: dict | None) -> bool:
    return found is None or found["permissionDecision"] == "allow"


# --- the conductor ---------------------------------------------------------------------------

CONDUCTOR_ALLOWED = [
    "review-queue",
    "review-queue --all",
    "review-queue --fingerprint",
    "queue --role conductor",
    "plan --json",
    "plan --json --if-changed",
    "rollover",
    "tidy --apply",
    "tell --session cb-example-1 --text hello",
]


@pytest.mark.parametrize("args", CONDUCTOR_ALLOWED)
def test_the_conductors_session_commands_pass_in_the_plugin_form(clean, args):
    """REQ-078: brief #1500 answers 1 and 4 (an allowed script in the plugin form passes)."""
    found = decision("conductor_guard.py", clean, f"python3 {SESSION} {args}")
    assert allowed(found), (args, found)


CONDUCTOR_REFUSED = [
    "plan",  # refused today in the installed form (brief #1500 Q-1500-1)
    "review-queue --all --fingerprint",
    "review-queue --json",
    "queue --role builder",
    "queue --role=conductor",
    "watch --pr 7",
    "claim --session cb-example-1 --brief 9",
    "after --session cb-example-1",
    "push-check",
    "ids",
    "",
]


@pytest.mark.parametrize("args", CONDUCTOR_REFUSED)
def test_todays_refusals_hold_in_the_plugin_form(clean, args):
    """REQ-078: brief #1500 answers 2 and 4 (an extra or other argument stays refused)."""
    found = decision("conductor_guard.py", clean, f"python3 {SESSION} {args}".strip())
    assert denied(found) and found["permissionDecisionReason"] == CONDUCTOR_RULE, (args, found)


OTHER_FORMS = [
    'python3 "${HOME}/scripts/agk/session.py" plan --json',
    'python3 "$CLAUDE_PLUGIN_ROOT/scripts/agk/session.py" plan --json',
    "python3 '${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py' plan --json",
    "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py plan --json",
    'python "${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py" plan --json',
    'python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py" plan --json',
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/../agk/session.py" plan --json',
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py"x plan --json',
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py" plan --json; id',
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/session.py" plan --json "${HOME}"',
    f"python3 {ROOT}/scripts/agk/session.py plan --json",
    f'python3 "{ROOT}/scripts/agk/session.py" plan --json',
]


@pytest.mark.parametrize("command", OTHER_FORMS)
def test_no_other_form_of_the_plugin_path_passes(clean, command):
    """REQ-078: brief #1500 answers 1 and 4 (another variable, path or quoting)."""
    assert denied(decision("conductor_guard.py", clean, command)), command


def test_the_plugin_form_is_refused_in_an_installed_project(installed):
    """REQ-078: brief #1500 answer 3 (installed projects are unchanged)."""
    assert denied(decision("conductor_guard.py", installed, f"python3 {SESSION} plan --json"))
    assert allowed(
        decision("conductor_guard.py", installed, "python3 scripts/agk/session.py plan --json")
    )


def test_the_installed_form_is_refused_in_a_clean_project(clean):
    """REQ-078: brief #1500 answer 2 (a clean project has no own scripts to run)."""
    assert denied(
        decision("conductor_guard.py", clean, "python3 scripts/agk/session.py plan --json")
    )


MERGE = f"--pr 7 --sha {FULL}"


def test_the_merge_command_passes_in_both_forms(clean, installed):
    """REQ-078: brief #1500 answer 4 (`merge_cleared.py --pr N --sha S` in both forms)."""
    plugin = decision("conductor_guard.py", clean, f'python3 {PLUGIN}merge_cleared.py" {MERGE}')
    own = decision("conductor_guard.py", installed, f"python3 scripts/agk/merge_cleared.py {MERGE}")
    assert plugin is not None and plugin["permissionDecision"] == "allow", plugin
    assert own is not None and own["permissionDecision"] == "allow", own


@pytest.mark.parametrize(
    "args",
    [
        f"--pr 7 --sha {FULL} --force",
        f"--pr 7 --sha {FULL[:39]}",
        f"--sha {FULL} --pr 7",
        "--pr 7",
    ],
)
def test_nothing_else_of_the_merge_command_passes_in_the_plugin_form(clean, args):
    """REQ-078: brief #1500 answer 4 (the merge command and nothing else)."""
    assert denied(
        decision("conductor_guard.py", clean, f'python3 {PLUGIN}merge_cleared.py" {args}')
    )


def test_the_shadows_slot_passes_in_the_plugin_form(clean):
    """REQ-078: brief #1500 answer 1 (the shadow's two slot forms, as today)."""
    assert allowed(
        decision("conductor_guard.py", clean, f"python3 {SESSION} slot --next s-shadow", "--shadow")
    )
    assert denied(
        decision("conductor_guard.py", clean, f"python3 {SESSION} slot --next s-other", "--shadow")
    )


# --- the architect and the review agent ------------------------------------------------------


@pytest.mark.parametrize(
    "command", [f'python3 {PLUGIN}doctor.py"', f'python3 {PLUGIN}check_specs.py"']
)
def test_the_architects_read_only_scripts_pass_in_the_plugin_form(clean, command):
    """REQ-078: brief #1500 answer 1 (the architect's read-only scripts)."""
    assert allowed(decision("architect_guard.py", clean, command)), command


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SESSION} claim --session cb-example-1 --brief 9",
        f'python3 {PLUGIN}check_specs.py" --write',
        f'python3 {PLUGIN}merge_cleared.py" {MERGE}',
        'python3 "${HOME}/scripts/agk/doctor.py"',
        f"python3 {ROOT}/scripts/agk/doctor.py",
    ],
)
def test_the_architects_refusals_hold_in_the_plugin_form(clean, command):
    """REQ-078: brief #1500 answer 2 (refused today, refused in the plugin form)."""
    assert denied(decision("architect_guard.py", clean, command)), command


def test_the_architect_refuses_the_plugin_form_in_an_installed_project(installed):
    """REQ-078: brief #1500 answer 3."""
    assert denied(decision("architect_guard.py", installed, f'python3 {PLUGIN}doctor.py"'))
    assert allowed(decision("architect_guard.py", installed, "python3 scripts/agk/doctor.py"))


def test_the_reviewers_slot_passes_in_the_plugin_form(clean):
    """REQ-078: brief #1500 answer 1 (the review agent's slot step)."""
    assert allowed(
        decision("architect_guard.py", clean, f"python3 {SESSION} slot --next r1", "--review")
    )
    assert denied(
        decision("architect_guard.py", clean, f"python3 {SESSION} slot --next s1", "--review")
    )


def stub_plugin(tmp_path: Path, link: bool) -> Path:
    """A plugin the resolver accepts whose `doctor.py` and `session.py` are missing, or are links
    to this repository's files."""
    stub = tmp_path / "plugin"
    (stub / ".claude-plugin").mkdir(parents=True)
    (stub / "scripts" / "agk").mkdir(parents=True)
    shutil.copy(ROOT / ".claude-plugin" / "plugin.json", stub / ".claude-plugin" / "plugin.json")
    shutil.copy(ROOT / "scripts" / "agk" / "kit_root.py", stub / "scripts" / "agk" / "kit_root.py")
    if link:
        for name in ("doctor.py", "session.py"):
            (stub / "scripts" / "agk" / name).symlink_to(ROOT / "scripts" / "agk" / name)
    return stub


@pytest.mark.parametrize("link", [False, True])
@pytest.mark.parametrize(
    "hook, command, flags",
    [
        ("architect_guard.py", f'python3 {PLUGIN}doctor.py"', ()),
        ("architect_guard.py", f"python3 {SESSION} slot --next r1", ("--review",)),
        ("conductor_guard.py", f"python3 {SESSION} plan --json", ()),
    ],
)
def test_a_plugin_word_needs_the_plugins_regular_file(tmp_path, clean, link, hook, command, flags):
    """REQ-078: brief #1500 answer 1, verdict on 1b4e725 item 1 (a missing script or a link)."""
    stub = stub_plugin(tmp_path, link)
    assert denied(decision(hook, clean, command, *flags, plugin=stub)), (hook, command, link)


# --- the steward -----------------------------------------------------------------------------


def test_the_steward_allows_the_plugin_form_and_refuses_the_merge_in_it(clean):
    """REQ-078: brief #1500 answers 1 and 2 (the steward refuses a merge in both forms)."""
    assert allowed(decision("steward_guard.py", clean, f"python3 {SESSION} plan"))
    for command in (
        f'python3 {PLUGIN}merge_cleared.py" {MERGE}',
        f"python3 scripts/agk/merge_cleared.py {MERGE}",
    ):
        assert denied(decision("steward_guard.py", clean, command)), command
