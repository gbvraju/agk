"""Kit-only tests of the shadow role file (SPEC-0035 rules 1 and 2; REQ-042 AC2 and AC8)."""

from __future__ import annotations

import re

from conftest import KIT_ROOT, manifest

ROLE = KIT_ROOT / ".claude" / "agents" / "shadow.md"
ARCHITECT = KIT_ROOT / ".claude" / "agents" / "architect.md"
PROTOCOL = re.compile(r"<!-- protocol -->\n(.*?)<!-- /protocol -->", re.S)


def split() -> tuple[str, str]:
    _, front, body = ROLE.read_text(encoding="utf-8").split("---", 2)
    return front, " ".join(body.split())


def test_ac2_the_front_matter_gives_read_tools_and_the_guard_in_shadow_mode():
    """REQ-042 AC2"""
    front, _ = split()
    assert re.search(r"(?m)^name: shadow$", front)
    tools = re.search(r"(?m)^tools: (.*)$", front).group(1)
    assert {t.strip() for t in tools.split(",")} == {"Read", "Grep", "Glob", "Bash", "Write"}
    assert re.search(r"conductor_guard\.py\s+--shadow", front)
    assert "Edit|Write|MultiEdit|NotebookEdit|Bash" in front and "architect_guard" not in front


def test_ac2_the_protocol_is_the_architects_verbatim():
    """REQ-042 AC2"""
    text = ROLE.read_text(encoding="utf-8")
    assert PROTOCOL.search(text).group(1) == PROTOCOL.search(ARCHITECT.read_text("utf-8")).group(1)


def test_ac2_the_role_states_the_comment_the_heads_and_the_blindness():
    """REQ-042 AC2: rules 1 and 2."""
    _, body = split()
    for phrase in (
        "Shadow: #<pr> <sha> cleared",
        "fix list",
        "rejected",
        "`S1.`",
        "the path and the line",
        "one open issue labelled `agk-shadow`",
        "every head",
        "each fix list and each re-push",
        "never the verdict comments of the conductor",
        "before you post",
    ):
        assert phrase in body, phrase


def test_ac2_ac8_the_role_posts_no_verdict_and_controls_no_session():
    """REQ-042 AC2 and AC8: nothing in the shadow review starts, stops, reviews or merges."""
    _, body = split()
    for phrase in (
        "post no verdict",
        "edit no file",
        "never merge",
        "tag",
        "auto-merge",
        "start, stop or review no session",
        "never write a `Marks:` comment",
        "config/session-rules.md",
    ):
        assert phrase in body, phrase


def test_ac2_the_role_names_no_catch_rate_and_no_project():
    """REQ-042 AC7"""
    _, body = split()
    assert "never state a catch rate" in body
    assert not re.search(r"\d+\s*%", body)


def test_ac2_the_shadow_role_is_installed_verbatim():
    """REQ-042 AC2"""
    assert ".claude/agents/shadow.md" in manifest()["verbatim"]
