"""Kit-only tests of the conductor role file (SPEC-0030 rule 6; REQ-037 AC5)."""

from __future__ import annotations

import json
import re

from conftest import KIT_ROOT, manifest

ROLE = KIT_ROOT / ".claude" / "agents" / "conductor.md"
ARCHITECT = KIT_ROOT / ".claude" / "agents" / "architect.md"
PROTOCOL = re.compile(r"<!-- protocol -->\n(.*?)<!-- /protocol -->", re.S)


def split() -> tuple[str, str]:
    text = ROLE.read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    return front, body


def test_ac5_the_front_matter_gives_read_tools_and_the_conductor_guard():
    """REQ-037 AC5"""
    front, _ = split()
    assert re.search(r"(?m)^name: conductor$", front)
    tools = re.search(r"(?m)^tools: (.*)$", front).group(1)
    assert {t.strip() for t in tools.split(",")} == {"Read", "Grep", "Glob", "Bash"}
    assert "PreToolUse:" in front and "conductor_guard.py" in front
    assert "Edit|Write|MultiEdit|NotebookEdit|Bash" in front
    assert "architect_guard" not in front


def test_ac5_the_protocol_is_the_architects_verbatim():
    """REQ-037 AC5"""
    _, body = split()
    assert PROTOCOL.search(body).group(1) == PROTOCOL.search(ARCHITECT.read_text("utf-8")).group(1)


def test_ac5_the_role_states_the_queue_the_verdict_and_the_limits():
    """REQ-037 AC5"""
    _, body = split()
    for phrase in (
        "every open pull request",
        "Verdict: cleared <sha>",
        "Verdict: fix list <sha>",
        "Verdict: rejected <sha>",
        "Final:",
        "real path",
        "Depends-on",
        "edit no file",
        "never merge",
        "tag",
        "auto-merge",
        "verdict_authors",
        "config/session-rules.md",
        "check_brief.py",
    ):
        assert phrase in body, phrase


def test_ac5_the_role_runs_the_seven_steps_before_every_verdict_in_order():
    """REQ-037 AC5 (the steps added to the brief of issue 163 by the architect)"""
    _, body = split()
    steps = body.split("Before every verdict", 1)[1].split("What you never do", 1)[0]
    marks = [
        "check runs of the exact head",
        "mergeable_state",
        "after the last verdict",
        "Real paths only",
        "AGK_BASE",
        "renumber",
        "--merged",
    ]
    at = [steps.find(m) for m in marks]
    assert all(i >= 0 for i in at) and at == sorted(at), at
    assert re.findall(r"(?m)^(\d)\. ", steps) == list("1234567")


def test_ac5_the_conductor_files_are_installed_verbatim():
    """REQ-037 AC5"""
    listed = manifest()["verbatim"]
    assert ".claude/agents/conductor.md" in listed and ".claude/hooks/conductor_guard.py" in listed
    hashes = (KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8")
    assert ".claude/agents/conductor.md" in json.dumps(json.loads(hashes))
