"""Tests of .claude/agents/steward.md and its wiring (SPEC-0059 rules 2, 15 and 19; brief #1320,
ADR-0557; REQ-066 AC1).

The role runs on the strongest tier at high effort, names its guard, starts on demand and names no
watch, loop or lease command; it carries the stage-to-skill table; the kit installs its files; and
principle 7 and `CLAUDE.md item 1` carry the one class of rule 15. No network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / ".claude" / "agents" / "steward.md"
FILES = (".claude/agents/steward.md", ".claude/hooks/steward_guard.py", "scripts/agk/steward.py")
SKILLS = (
    "start",
    "vision",
    "scope-review",
    "design",
    "stack",
    "plan-intake",
    "scope-lock",
    "brief",
    "issue",
    "board",
    "launch",
    "review",
    "doctor",
    "upgrade",
)


def front_matter(text: str) -> str:
    found = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert found, "the agent file has front matter"
    return found.group(1)


def test_req066_the_agent_file_names_its_tier_and_its_guard():
    """REQ-066 AC1: rule 2, `design` on the `strongest` tier at `high`; the guard is its hook."""
    text = AGENT.read_text(encoding="utf-8")
    head = front_matter(text)
    assert re.search(r"^name: steward$", head, re.M)
    assert "PreToolUse" in head and ".claude/hooks/steward_guard.py" in head
    assert "the `strongest` tier at `high` effort" in text
    assert "kind `design`" in text
    assert "claude --agent steward" in text and "(verify" in text


def test_req066_the_agent_runs_no_watch_loop_or_lease():
    """REQ-066 AC1: rule 2, on demand only; rule 18, no step sleeps, polls or renews a lease."""
    text = AGENT.read_text(encoding="utf-8")
    assert "ScheduleWakeup" not in front_matter(text)
    for command in ("session.py watch", "conductor.py watch", "lease renew", "sleep "):
        assert command not in text, command
    assert "never `/loop`" in text
    assert "steward.py start --session" in text and "steward.py end --session" in text


def test_req066_the_agent_names_each_stage_skill_of_the_table():
    """REQ-066 AC1: rule 19, each stage and step names its kit skill."""
    text = AGENT.read_text(encoding="utf-8")
    rows = re.findall(r"^\| [^|]+ \| (.+) \|$", text, re.M)
    named = set(re.findall(r"`([a-z-]+)`", " ".join(rows)))
    for skill in SKILLS:
        assert skill in named, skill
        assert (ROOT / "skills" / skill / "SKILL.md").is_file(), skill


def test_req066_the_kit_installs_the_steward_files():
    """REQ-066 AC1: rule 2, the manifest lists the agent, the guard and the memory script."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    for rel in FILES:
        assert rel in manifest["verbatim"], rel
        assert (ROOT / rel).is_file(), rel


def test_req066_principle_7_and_claude_item_1_carry_the_steward_class():
    """REQ-066 AC1: rule 15, the one class is added; principles 1 and 2 keep their text."""
    principles = (ROOT / "constitution" / "principles.md").read_text(encoding="utf-8")
    seven = re.search(r"^7\. (.+)$", principles, re.M).group(1)
    assert "steward" in seven and "evidence" in seven and "(verify)" in seven
    for n in (1, 2):
        assert "steward" not in re.search(rf"^{n}\. (.+)$", principles, re.M).group(1)
    core = (ROOT / "config" / "core-rules.md").read_text(encoding="utf-8")
    item = core.split("\n1. You implement;", 1)[1].split("\n\n", 1)[0]
    assert "steward" in item and "SPEC-0059 rule 3" in item and "owner" in item
