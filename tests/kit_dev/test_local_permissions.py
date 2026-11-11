"""Brief #1029 (REQ-037, ADR-0438): local builders post, mark ready and push without a prompt,
take their next brief at once, and a person's own permissions file stays untracked."""

from __future__ import annotations

import fnmatch
import json
import tomllib

from conftest import KIT_ROOT

SETTINGS = KIT_ROOT / ".claude" / "settings.json"

ALLOW = (
    "Bash(gh api repos/*/issues/*/comments*)",
    "Bash(gh api repos/*/pulls/*/comments*)",
    "Bash(gh api --method POST repos/*/pulls/*/ccr/ready_for_review)",
    "Bash(gh pr ready *)",
    "Bash(gh pr view *)",
    "Bash(git fetch*)",
    "Bash(git switch*)",
    "Bash(git checkout*)",
    "Bash(git merge origin/*)",
    "Bash(git push origin claude/*)",
)
DENY = ("Bash(gh api *merge*)", "Bash(gh api *-X PUT*)", "Bash(gh api *--method PUT*)")


def perms() -> dict:
    return json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]


def matches(rule: str, command: str) -> bool:
    """A `Bash(...)` rule against a command, as the stop-hook tests read it (prefix `:*`, glob `*`)."""
    if not (rule.startswith("Bash(") and rule.endswith(")")):
        return False
    inner = rule[len("Bash(") : -1]
    if inner.endswith(":*"):
        inner = inner[:-2] + " *"
    if inner.endswith(" *") and fnmatch.fnmatchcase(command, inner[:-2]):
        return True
    return fnmatch.fnmatchcase(command, inner)


def test_d_settings_allow_each_local_builder_line():
    """REQ-037 (brief #1029 answer 2, test d)"""
    allow = perms()["allow"]
    for rule in ALLOW:
        assert rule in allow, rule


def test_d_settings_deny_each_merge_line():
    """REQ-037 (brief #1029 answer 2, test d)"""
    deny = perms()["deny"]
    for rule in DENY:
        assert rule in deny, rule


def test_d_no_allow_line_opens_a_merge_and_deny_catches_it():
    """REQ-037 (brief #1029 answer 2, test d): merges stay with merge_cleared.py."""
    p = perms()
    for command in (
        "gh api repos/x/pulls/1/merge -X PUT",
        "gh api --method PUT repos/x/pulls/1/merge",
        "gh api -X PUT repos/x/pulls/1/merge",
    ):
        assert not [r for r in p["allow"] if matches(r, command)], command
        assert [r for r in p["deny"] if matches(r, command)], command


def test_d_deny_does_not_shut_the_allowed_routes():
    """REQ-037 (brief #1029 answer 2): deny beats allow, so no deny line matches a route it opens."""
    deny = perms()["deny"]
    for command in (
        "gh api repos/example/demo/issues/1/comments -F body=@report.md",
        "gh api repos/example/demo/pulls/1/comments",
        "gh api --method POST repos/example/demo/pulls/1/ccr/ready_for_review",
        "gh pr ready 1",
        "gh pr view 1",
        "git fetch origin main",
        "git switch -c claude/brief-1 origin/main",
        "git merge origin/main",
        "git push origin claude/brief-1",
    ):
        assert not [r for r in deny if matches(r, command)], command


def test_e_gitignore_names_the_local_settings():
    """REQ-037 (brief #1029 answer 3, test e)"""
    lines = (KIT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".claude/settings.local.json" in lines


def test_f_this_repository_hands_the_next_brief_at_once():
    """REQ-037 (brief #1029 answer 1, test f); `builder_start` is unchanged."""
    data = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert data["flow"]["assign"] == "next"
    assert data["flow"]["builder_start"] == "assign"
