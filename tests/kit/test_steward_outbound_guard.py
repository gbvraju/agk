"""Tests of scripts/agk/steward_outbound.py and its denial in .claude/hooks/steward_guard.py
(SPEC-0059 rules 6 and 11, brief #1324, ADR-0561; REQ-066 AC4).

A text bound for the kit repository is refused, fail closed, when it holds a token of the project's
neutrality list, a value the data guard's detectors find, a URL of the project's hosts or a
repository name other than the kit's, and when a list cannot be read; each refusal names the
setting and the class, never the value. A clean invented text passes. No network; data invented.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import steward_outbound as outbound  # noqa: E402

PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

SCRIPT = ROOT / "scripts" / "agk" / "steward_outbound.py"
HOOK = ROOT / ".claude" / "hooks" / "steward_guard.py"
KIT = outbound.repo_name(str(PLUGIN["repository"]).split("github.com", 1)[1])
PLANTED_NAME = "zephyrcorp"
REMOTE = "https://git.example.test/team/portal.git"
CLEAN = (
    f"Title: the plan check reads a blank milestone as none\n\n"
    f"Seen in a project at https://{KIT.split('/')[0]}.example.com and in {KIT}#1324: "
    "the check prints nothing for a milestone with no title. Steps: run `make plan`.\n"
)
PLANTED = {
    "neutrality token": f"The {PLANTED_NAME.capitalize()} team saw the plan check fail.",
    "EMAIL": "Write to pat@example.test about the plan check.",
    "PHONE": "Call +44 20 7946 0958 about the plan check.",
    "project host URL": "See https://git.example.test/wiki/plan for the plan check.",
    "another repository name": "The plan check fails in other-org/other-app#12 as well.",
}


def project(tmp_path: Path, tokens: str = PLANTED_NAME, remote: str = REMOTE) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "config" / "neutrality.txt").write_text(f"# tokens\n{tokens}\n", encoding="utf-8")
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    git = ["git", "-C", str(root)]
    subprocess.run([*git, "init", "-q"], check=True)  # nosec B603 - fixed argument list
    subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*git, "remote", "add", "origin", remote], check=True
    )
    return root


def run_cli(root: Path, text: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "check", "--root", str(root), "--text", text],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("kind", sorted(PLANTED))
def test_req066_each_planted_value_is_refused_by_class(tmp_path, kind):
    """REQ-066 AC4: rule 6, each planted value refuses naming the class and never the value."""
    root = project(tmp_path)
    text = CLEAN + PLANTED[kind]
    lines = outbound.check(text, root)
    assert lines, kind
    assert any(kind in line and "setting:" in line for line in lines), lines
    for value in (PLANTED_NAME, "pat@example.test", "7946", "git.example.test", "other-org"):
        assert value not in "\n".join(lines).lower()
    proc = run_cli(root, text)
    assert proc.returncode == 2
    assert kind in proc.stdout and PLANTED_NAME not in proc.stdout.lower()


def test_req066_project_remote_repository_name_is_refused(tmp_path):
    """REQ-066 AC4: rule 6, the project's own repository name never leaves the project."""
    root = project(tmp_path, remote="git@github.com:example-org/portal.git")
    lines = outbound.check(CLEAN + "Seen in example-org/portal on Monday.", root)
    assert any("another repository name" in line for line in lines), lines
    lines = outbound.check(CLEAN + "See https://github.com/example-org/portal/pull/3.", root)
    assert any("project host URL" in line for line in lines), lines


def test_req066_a_clean_invented_text_passes(tmp_path):
    """REQ-066 AC4: rule 6, a clean invented text that names only the kit is filed."""
    root = project(tmp_path)
    assert outbound.check(CLEAN, root) == []
    proc = run_cli(root, CLEAN)
    assert proc.returncode == 0 and proc.stdout.strip() == "ok outbound"


@pytest.mark.parametrize("how", ["missing", "folder"])
def test_req066_an_unreadable_list_refuses(tmp_path, how):
    """REQ-066 AC4: rule 6, a list that cannot be read refuses, fail closed."""
    root = project(tmp_path)
    path = root / "config" / "neutrality.txt"
    path.unlink()
    if how == "folder":
        path.mkdir()
    lines = outbound.check(CLEAN, root)
    assert lines == [
        "outbound guard: SPEC-0059 rule 6 refuses a text it cannot check "
        "(setting: config/neutrality.txt)"
    ]
    assert run_cli(root, CLEAN).returncode == 2


def test_req066_remotes_that_cannot_be_read_refuse(tmp_path):
    """REQ-066 AC4: rule 6, a folder whose git remotes cannot be read refuses."""
    root = tmp_path / "plain"
    (root / "config").mkdir(parents=True)
    (root / "config" / "neutrality.txt").write_text("", encoding="utf-8")
    lines = outbound.check(CLEAN, root)
    assert lines and "cannot check" in lines[0] and "git remotes" in lines[0]


def test_req066_the_kit_repository_is_read_from_the_plugin_or_the_settings(tmp_path):
    """REQ-066 AC4: the kit repository is the plugin file's, else the settings' marketplace."""
    assert outbound.kit_repo(ROOT) == KIT
    root = project(tmp_path)
    (root / ".claude").mkdir()
    settings = {"extraKnownMarketplaces": {"agk": {"source": {"source": "github", "repo": KIT}}}}
    (root / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    assert outbound.kit_repo(root) == KIT


def test_req066_with_no_kit_named_every_repository_name_is_refused(tmp_path):
    """REQ-066 AC4: a kit that cannot be named makes every repository another's, fail closed."""
    root = project(tmp_path)
    lines = outbound.check(CLEAN, root, kit="")
    assert any("another repository name" in line for line in lines), lines


# --- the guard's denial (rule 11) ----------------------------------------------------------------


def hook(root: Path, command: str) -> dict | None:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(root)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root), "HOME": str(root)},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None


def posts(root: Path, text: str) -> list[str]:
    body = root / "body.md"
    body.write_text(text, encoding="utf-8")
    return [
        f"gh issue create -R {KIT} --title 'plan check' --body-file {body}",
        f"gh issue comment 5 --repo={KIT} --body-file {body}",
        f"gh api -X POST repos/{KIT}/issues -f title='plan check' -F body=@{body}",
        f"gh api --method POST repos/{KIT}/issues/5/comments -F body=@{body}",
    ]


@pytest.mark.parametrize("kind", sorted(PLANTED))
def test_req066_guard_denies_a_kit_post_the_outbound_guard_matches(tmp_path, kind):
    """REQ-066 AC4: rule 11, a post to the kit repository with a planted value is denied."""
    root = project(tmp_path)
    for command in posts(root, CLEAN + PLANTED[kind]):
        out = hook(root, command)
        assert out and out["permissionDecision"] == "deny", command
        reason = out["permissionDecisionReason"]
        assert "SPEC-0059 rule 11" in reason and kind in reason, reason
        assert PLANTED_NAME not in reason.lower() and "example.test" not in reason


def test_req066_guard_allows_a_clean_kit_post_and_denies_an_unreadable_list(tmp_path):
    """REQ-066 AC4: rule 11, a clean post passes; a list that cannot be read is denied."""
    root = project(tmp_path)
    for command in posts(root, CLEAN):
        assert hook(root, command) is None, command
    (root / "config" / "neutrality.txt").unlink()
    for command in posts(root, CLEAN):
        out = hook(root, command)
        assert out and "cannot check" in out["permissionDecisionReason"], command


def test_req066_guard_leaves_other_targets_and_the_kit_itself_alone(tmp_path):
    """REQ-066 AC4: the outbound guard judges only a text that leaves the project for the kit."""
    root = project(tmp_path)
    text = PLANTED["EMAIL"]
    assert hook(root, f"gh api -X POST repos/o/r/issues/9/comments -f body='{text}'") is None
    assert hook(root, f"gh pr comment 9 --body '{text}'") is None
    kit = project(tmp_path / "kit", remote=f"https://github.com/{KIT}.git")
    assert hook(kit, f"gh issue comment 5 -R {KIT} --body '{text}'") is None
