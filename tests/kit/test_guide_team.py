# ruff: noqa: F811 - the fixtures of test_session are imported by name
"""The team section of the getting-started guide (brief #1145, REQ-039).

`docs/guides/getting-started.md` has a section `Working as a team`: four people on four laptops,
each with two or three builders, one shared conductor. The tests read the guide and run only
`session.py claim` against a `gh` stub (invented data, example.com, no network).
"""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

from test_session import (  # noqa: F401 - the fixtures and helpers of the session tests
    FREE,
    ISSUES,
    comment,
    iso,
    issue,
    listing,
    proj,
    session,
    stub,
    take,
)

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "getting-started.md"
REFERENCE = ROOT / "docs" / "guides" / "reference.md"
HEADING = "## Working as a team"
NAMED = (
    "/agk:launch",
    "session.py next",
    "claim",
    "resume --pr",
    "max_builders",
    "lease",
)


def section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.find(HEADING)
    assert start != -1, "the guide has no section 'Working as a team'"
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_the_team_section_names_what_a_team_needs():
    """REQ-039"""
    body = section()
    missing = [name for name in NAMED if name not in body]
    assert not missing, f"the section does not name {missing}"


def test_every_command_the_section_shows_exists():
    """REQ-039: a script command exists as a verb of its script; a skill is in the reference."""
    reference = REFERENCE.read_text(encoding="utf-8")
    shown = set(re.findall(r"scripts/agk/(\w+\.py) (\w[\w-]*)", section()))
    assert shown, "the section shows no script command"
    absent = []
    for script, verb in sorted(shown):
        path = ROOT / "scripts" / "agk" / script
        source = path.read_text(encoding="utf-8") if path.exists() else ""
        if f'"{verb}"' not in source:
            absent.append(f"{script} {verb}")
    assert not absent, f"no such command: {absent}"
    for skill in set(re.findall(r"/agk:[\w-]+", section())):
        assert f"`{skill}`" in reference, f"the reference does not list {skill}"


def test_two_claims_of_one_brief_by_two_sessions_leave_one_holder(proj, stub):
    """REQ-039"""
    listing(stub, [issue(5, FREE)])
    first, second = iso(-timedelta(seconds=5)), iso()
    both = [take(1, "ana-b1", first, "ana"), take(2, "ben-b1", second, "ben")]
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", both, nth=2)
    won = session(proj, stub, "claim", "--session", "ana-b1", "--brief", "5")
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", both, nth=2)
    for path in stub.dir.glob("count.*"):
        path.unlink()
    lost = session(proj, stub, "claim", "--session", "ben-b1", "--brief", "5")
    assert won.returncode == 0, won.stdout + won.stderr
    assert lost.returncode != 0 and "ana-b1" in lost.stdout + lost.stderr
