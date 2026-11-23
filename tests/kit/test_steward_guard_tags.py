"""Tests of the steward guard's tag rule (SPEC-0059 rule 11, session rule 2, brief #1834, ADR-0763; REQ-066 AC5).

The steward's guard reads a `git push` as git does: a tag's short name, a tag destination, `tag <name>`, an empty
source, a pattern into `refs/tags/`, `--follow-tags`, a push setting, a `git config` or `-c` that writes one, an alias
and `update-ref` of a tag are denied; a work branch push is allowed as before. The same table runs through every role
guard that `plugin_hooks.ROLE_GUARDS` names. Each test builds a scratch repository in `tmp_path` with invented tags
and an `example.com` remote; nothing is pushed and nothing uses the network.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
HOOK = HOOKS / "steward_guard.py"
RULE = "SPEC-0059 rule 11"
GIT = shutil.which("git") or "git"
TAG = "denies a tag (path class: git push)"

sys.path.insert(0, str(HOOKS))
import plugin_hooks  # noqa: E402 - the hook folder, added above

# Every form of the evidence (brief #1834): (command, the end of the denial line).
DENIED = [
    ("git push origin v1.0.0", TAG),
    ("git push origin v1.0.0:v1.0.0", TAG),
    ("git push origin tag v1.0.0", TAG),
    ("git push origin HEAD:v1.0.0", TAG),
    ("git push origin :v1.0.0", TAG),
    ("git push -u origin v1.0.0", TAG),
    ("git push -o ci.skip origin v1.0.0", TAG),
    ("git push --push-option=ci.skip origin v1.0.0", TAG),
    ("git push --atomic origin feature v1.0.0", TAG),
    ("git push origin tags/v1.0.0", TAG),
    ("git push origin v1.1.0", TAG),  # an annotated tag
    ("git push origin release", TAG),  # a branch and a tag of one name
    ("git push origin v1.0.0:refs/heads/x", TAG),  # Q-1834-3: a tag source to a branch
    ("git push origin HEAD:refs/tags/v9", "(path class: default branch)"),
    ("git push origin 'refs/*:refs/*'", TAG),
    ("git push origin '*:*'", TAG),
    ("git push --repo=origin v1.0.0", TAG),
    ("git push --follow-tags origin feature", "(path class: git push)"),
    ("git -c push.followTags=true push origin feature", "(path class: git config)"),
    ("git config push.followTags true", "(path class: git config)"),
    ("git config --add remote.origin.push 'refs/tags/*:refs/tags/*'", "(path class: git config)"),
    ("git config remote.origin.mirror true", "(path class: git config)"),
    ("git config remote.origin.tagOpt --tags", "(path class: git config)"),
    ("git config set push.followtags true", "(path class: git config)"),
    ("git config alias.t tag", "(path class: git config)"),
    ("git config --global alias.p push", "(path class: git config)"),
    ("git -c alias.p=push p origin v1.0.0", "(path class: git config)"),
    ("git --config-env=alias.p=X p origin v1.0.0", "(path class: git config)"),
    ("git update-ref refs/tags/v2 HEAD", "(path class: git update-ref)"),
    ("git update-ref -d refs/tags/v1.0.0", "(path class: git update-ref)"),
    ("git update-ref v1.0.0 HEAD", "(path class: git update-ref)"),
    ("git update-ref --stdin", "(path class: git update-ref)"),
    ("git fetch origin --tags", "(path class: git fetch)"),
    ("git fetch origin 'refs/tags/*:refs/tags/*'", "(path class: git fetch)"),
    ("git tag v2.0.0", "(path class: git tag)"),
    ("git --git-dir .git push origin v1.0.0", TAG),
    ("git.exe push origin v1.0.0", TAG),
    ("env A=1 git push origin v1.0.0", TAG),
    ("timeout 60 git push origin v1.0.0", TAG),
    ("bash -c 'git push origin v1.0.0'", TAG),
    ("git status && git push origin v1.0.0", TAG),
]

ALLOWED = [
    "git push origin feature",
    "git push -u origin feature",
    "git push -o ci.skip origin feature",
    "git push origin HEAD:refs/heads/feature",
    "git push origin HEAD:new-work",  # Q-1834-2: a new branch name, not a local tag
    "git push origin refs/notes/agk-evidence",
    "git push --no-follow-tags origin feature",
    "git fetch origin",
    "git fetch origin main",
    "git tag --list",
    "git config user.name Example",
    "git config --get push.followTags",
    "git config alias.t",
    "git config --list",
    "git update-ref refs/heads/x HEAD",
    "git status",
]


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 - fixed argument list, no shell
        [GIT, "-C", str(root), *args], check=True, capture_output=True, env=git_env(root)
    )


def git_env(home: Path) -> dict:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Example",
        "GIT_AUTHOR_EMAIL": "a@example.com",
        "GIT_COMMITTER_NAME": "Example",
        "GIT_COMMITTER_EMAIL": "a@example.com",
    }


def repo(tmp_path: Path, toml: str = '[kit]\nlayout = "plugin"\n') -> Path:
    """One commit, tags `v1.0.0` (lightweight), `v1.1.0` (annotated) and `release`, branches `feature`, `release`."""
    root = tmp_path / "p"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    git(root, "add", "agk.toml")
    git(root, "commit", "-q", "-m", "one")
    git(root, "tag", "v1.0.0")
    git(root, "tag", "-a", "v1.1.0", "-m", "release one")
    git(root, "tag", "release")
    git(root, "branch", "feature")
    git(root, "branch", "release")
    git(root, "remote", "add", "origin", "https://example.com/o/r.git")
    return root


def run(script: Path, root: Path, command: str, *args: str, path: str | None = None, **env) -> str | None:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(root)}
    full = {**git_env(root), "CLAUDE_PROJECT_DIR": str(root), **env}
    if path is not None:
        full["PATH"] = path
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=full,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return None
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


def bash(root: Path, command: str, **kwargs) -> str | None:
    return run(HOOK, root, command, **kwargs)


def never_a_value(line: str) -> None:
    for value in ("v1.0.0", "v1.1.0", "example.com", "ci.skip", "refs/tags/*"):
        assert value not in line, line


@pytest.mark.parametrize(("command", "ending"), DENIED)
def test_req066_every_tag_form_is_denied_with_its_rule_and_class(tmp_path, command, ending):
    """REQ-066 AC5: rule 11, each way a command makes, moves or deletes a tag is denied (brief #1834)."""
    found = bash(repo(tmp_path), command)
    assert found is not None, command
    assert found.startswith(f"steward guard: {RULE} ") and found.endswith(ending), found
    never_a_value(found)


@pytest.mark.parametrize("command", ALLOWED)
def test_req066_a_work_branch_push_and_the_reads_stay_allowed(tmp_path, command):
    """REQ-066 AC5: rule 11, a work branch push, the evidence note, a fetch and the reads pass as before."""
    assert bash(repo(tmp_path), command) is None, command


@pytest.mark.parametrize(
    ("key", "value", "setting"),
    [
        ("push.followTags", "true", "push.followTags"),
        ("push.followtags", "yes", "push.followTags"),
        ("remote.origin.mirror", "true", "remote.<name>.mirror"),
        ("remote.origin.push", "refs/tags/*:refs/tags/*", "remote.<name>.push"),
        ("remote.origin.push", "v1.0.0", "remote.<name>.push"),
    ],
)
def test_req066_a_push_setting_that_sends_a_tag_denies_naming_the_setting(tmp_path, key, value, setting):
    """REQ-066 AC5: rule 11, `push.followTags` true, a tag push refspec or a mirror remote deny the push."""
    root = repo(tmp_path)
    git(root, "config", key, value)
    found = bash(root, "git push origin feature")
    assert found == f"steward guard: {RULE} denies a tag (setting: {setting})", found
    never_a_value(found)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("push.followTags", "false"),
        ("remote.origin.mirror", "false"),
        ("remote.origin.push", "refs/heads/feature:refs/heads/feature"),
        ("remote.origin.tagOpt", "--tags"),  # it changes a fetch, never a push
    ],
)
def test_req066_a_push_setting_that_sends_no_tag_leaves_the_push_allowed(tmp_path, key, value):
    """REQ-066 AC5: rule 11, `push.followTags` false, a branch refspec and `tagOpt` leave a branch push alone."""
    root = repo(tmp_path)
    git(root, "config", key, value)
    assert bash(root, "git push origin feature") is None


def test_req066_an_alias_is_judged_as_its_expansion(tmp_path):
    """REQ-066 AC5: rule 11, an alias set in the repository is judged as what it runs, one level."""
    root = repo(tmp_path)
    git(root, "config", "alias.t", "tag")
    git(root, "config", "alias.p", "push")
    git(root, "config", "alias.sh", "!git push origin v1.0.0")
    git(root, "config", "alias.st", "status")
    assert bash(root, "git t v2.0.0").endswith("(path class: git tag)")
    assert bash(root, "git p origin v1.0.0").endswith(TAG)
    assert bash(root, "git p --follow-tags origin feature").endswith("(path class: git push)")
    assert bash(root, "git sh").endswith("(path class: git alias)")
    assert bash(root, "git p origin feature") is None
    assert bash(root, "git st") is None
    assert bash(root, "git no-such-command") is None


def test_req066_a_push_it_cannot_judge_is_denied(tmp_path):
    """REQ-066 AC5: rule 11 fails closed, with no git on PATH a push is denied; another command as before."""
    root = repo(tmp_path)
    empty = tmp_path / "no-git"
    empty.mkdir()
    found = bash(root, "git push origin feature", path=str(empty))
    assert found == f"steward guard: {RULE} cannot judge a push (path class: git push)", found
    assert bash(root, "git status", path=str(empty)) is None
    assert bash(root, "git sh", path=str(empty)).endswith("(path class: git alias)")


def test_req066_a_push_outside_a_repository_has_no_tag_to_send(tmp_path):
    """REQ-066 AC5: rule 11, outside a repository git itself refuses the push, so no tag can leave."""
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert bash(tmp_path, "git push origin feature") is None
    assert bash(tmp_path, "git push origin main") is not None


def test_req066_git_dash_c_reads_the_tags_of_that_folder(tmp_path):
    """REQ-066 AC5: rule 11, `git -C <dir> push` judges the tags of `<dir>`."""
    repo(tmp_path)  # the repository is `p` under the folder the command runs in
    assert bash(tmp_path, "git -C p push origin v1.0.0").endswith(TAG)
    assert bash(tmp_path, "git -C p push origin feature") is None


@pytest.mark.parametrize(
    ("toml", "branch"),
    [
        ('[kit]\nlayout = "plugin"\n', "main"),
        ('default_branch = "trunk"\n', "trunk"),
        ("this is = = not toml\n", "main"),
    ],
)
def test_req066_the_default_branch_setting_and_a_tag_of_its_name(tmp_path, toml, branch):
    """REQ-066 AC5: `default_branch` unset, set and unreadable; a tag of the default branch's name is denied."""
    root = repo(tmp_path, toml)
    assert bash(root, f"git push origin HEAD:{branch}") is not None
    git(root, "tag", "trunk")
    assert bash(root, "git push origin trunk") is not None
    assert bash(root, "git push origin feature") is None


@pytest.mark.parametrize(
    "toml",
    [
        'pr_mode = "flow"\nreview_mode = "team"\n',
        'pr_mode = "strict"\nreview_mode = "solo"\nexecution = "local"\n',
        'execution = "pool"\n[steward]\nauto_file = 2\nfix_briefs = true\n',
        'execution = "hybrid"\n[personal]\nforge = "files"\n',
        '[kit]\nlayout = "installed"\n',
    ],
)
@pytest.mark.parametrize("start", [None, "conductor"])
def test_req066_the_modes_and_settings_change_no_tag_rule(tmp_path, toml, start):
    """REQ-066 AC5: `pr_mode`, `review_mode`, `execution`, `[steward]`, personal mode and AGK_STEWARD_START."""
    root = repo(tmp_path, toml)
    env = {"AGK_STEWARD_START": start} if start else {}
    assert run(HOOK, root, "git push origin v1.0.0", **env).endswith(TAG)
    assert run(HOOK, root, "git push origin refs/notes/agk-evidence", **env) is None
    assert run(HOOK, root, "git push origin feature", **env) is None


@pytest.fixture(scope="module")
def plugin(tmp_path_factory) -> Path:
    stub = tmp_path_factory.mktemp("plugin")
    for part in (".claude-plugin", ".claude/hooks", ".claude/agents", "scripts/agk"):
        shutil.copytree(ROOT / part, stub / part, ignore=shutil.ignore_patterns("__pycache__"))
    return stub


@pytest.mark.parametrize("agent", ["agk:steward", "steward"])
def test_req066_the_plugin_hook_denies_a_tag_for_the_steward_in_a_clean_project(tmp_path, plugin, agent):
    """REQ-066 AC5: the clean layout, `plugin_hooks.py pre` runs the same guard for the steward (ADR-0612)."""
    root = repo(tmp_path)
    script = plugin / ".claude" / "hooks" / "plugin_hooks.py"
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(root), "agent_type": agent}
    for command, denied in (("git push origin v1.0.0", True), ("git push origin feature", False)):
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(script), "pre"],
            input=json.dumps({**payload, "tool_input": {"command": command}}),
            capture_output=True,
            text=True,
            env={**git_env(root), "CLAUDE_PROJECT_DIR": str(root)},
            cwd=root,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        if denied:
            assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecisionReason"].endswith(TAG)
        else:
            assert not proc.stdout.strip(), proc.stdout


def test_req066_the_steward_frontmatter_hook_denies_a_tag_in_the_installed_layout(tmp_path):
    """REQ-066 AC5: the installed layout, the steward's own frontmatter command runs the same guard."""
    root = repo(tmp_path, 'version = "0.1.0"\n')
    shutil.copytree(HOOKS, root / ".claude" / "hooks", ignore=shutil.ignore_patterns("__pycache__"))
    head = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8").split("\n---\n", 1)[0]
    command = re.search(r'command: "(.+steward_guard\.py)"', head)[1].replace('\\"', '"')
    for line, denied in (("git push origin v1.0.0", True), ("git push origin feature", False)):
        payload = {"tool_name": "Bash", "tool_input": {"command": line}, "cwd": str(root)}
        proc = subprocess.run(  # nosec B603 B607 - the agent file's fixed command, no user input
            ["bash", "-c", command],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={**git_env(root), "CLAUDE_PROJECT_DIR": str(root)},
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert bool(proc.stdout.strip()) is denied, (line, proc.stdout)


@pytest.mark.parametrize("role", sorted(plugin_hooks.ROLE_GUARDS))
def test_req066_every_role_guard_denies_every_tag_form(tmp_path, role):
    """REQ-066 AC5: the class stays closed, each `ROLE_GUARDS` guard denies each form of the table."""
    root = repo(tmp_path)
    guard, *args = plugin_hooks.ROLE_GUARDS[role]
    for command, _ in DENIED:
        assert run(HOOKS / guard, root, command, *args) is not None, (role, command)


def tools_of(agent: Path) -> str | None:
    head = agent.read_text(encoding="utf-8").split("\n---\n", 1)[0]
    found = re.search(r"^tools:\s*(.+)$", head, re.M)
    return found[1] if found else None


def test_req066_the_builder_is_the_one_role_with_bash_and_no_push_judgement():
    """REQ-066 AC5: Q-1834-1, the builder has Bash and no role guard; a builder guard later removes this row."""
    with_bash = {
        agent.stem
        for agent in (ROOT / ".claude" / "agents").glob("*.md")
        if (tools := tools_of(agent)) is None or "Bash" in [t.strip() for t in tools.split(",")]
    }
    assert with_bash - set(plugin_hooks.ROLE_GUARDS) == {"builder"}
