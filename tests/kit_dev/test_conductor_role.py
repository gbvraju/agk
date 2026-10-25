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
    assert {t.strip() for t in tools.split(",")} == {"Read", "Grep", "Glob", "Bash", "Write"}
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


def test_ac5_the_role_states_the_bounded_run_and_the_trust_rule():
    """REQ-037 AC5 (items 2, 4 and 5 of the verdict on #175)"""
    front, body = split()
    for phrase in (
        'env -i PATH="$PATH" HOME=<scratch>',
        "AGK_BASE=<sha>",
        "can read files by absolute path",
        "not a sandbox",
        "git worktree add <scratch> <sha>",
        "make -C <scratch> test",
        "python3 -I <scratch>/scripts/agk/<name>.py",
        "never a fork",
        "head.repo.full_name",
        "base.repo.full_name",
        "workspace trust dialog",
        "`-p` session does not count as trusted",
        "Never state one; only the shadow review",
    ):
        assert phrase in body, phrase
    assert "(verify:" not in front + body
    assert "kit/hashes.json" not in body and "Claim to catch" not in body


def test_ac5_the_conductor_files_are_installed_verbatim():
    """REQ-037 AC5"""
    listed = manifest()["verbatim"]
    assert ".claude/agents/conductor.md" in listed and ".claude/hooks/conductor_guard.py" in listed
    hashes = (KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8")
    assert ".claude/agents/conductor.md" in json.dumps(json.loads(hashes))


def test_ac6_ac7_the_role_forbids_a_cause_without_a_measured_line_and_states_the_correction():
    """REQ-039 AC6 and AC7: rules 9 and 10 (the conductor's side of the second check)."""
    _, body = split()
    text = " ".join(body.split())
    assert "`Measured:`" in text and "never name a cause" in text
    assert "`Correction: <what was wrong>; <what stands>`" in text
    assert "edited in place" in text and "allows only the comment POST" in text
