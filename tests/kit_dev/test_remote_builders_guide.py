"""Kit-only tests of the remote-builders guide (brief #375, ADR-0216; REQ-040).

The guide says what a builder session needs in a remote development environment, how it starts and
resumes from GitHub alone, what stays on the person's machine, and the safety rules of answer 2. It
names no provider (answer 3). Files only; no network.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "remote-builders.md"
SESSION = KIT_ROOT / "scripts" / "agk" / "session.py"
SECTIONS = (
    "What a remote builder needs",
    "Start and resume",
    "What stays on your machine",
    "Safety rules",
)
# Answer 2, one phrase per rule, as the guide states each.
SAFETY = (
    "no production secret",
    "no admin token",
    "can only push branches and comment",
    "stopped when idle",
    "never copied into it",
)
# Answer 3: names of providers, clouds and tools a guide of the kit could slip into; GitHub is
# the one host the kit is built for.
VENDORS = (
    "gitlab",
    "bitbucket",
    "azure",
    "aws",
    "amazon",
    "google",
    "gcp",
    "codespaces",
    "gitpod",
    "coder",
    "devpod",
    "docker",
    "kubernetes",
    "vagrant",
    "anthropic",
    "claude",
    "openai",
    "slack",
    "microsoft",
    "apple",
)


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def flat() -> str:
    return " ".join(guide().split())


def section(title: str) -> str:
    found = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", guide())
    assert found, f"the guide has no section '{title}'"
    return " ".join(found.group(1).split())


def test_the_guide_exists_with_its_sections():
    """REQ-040: answer 1 (one guide, its parts in order)."""
    text = guide()
    assert text.startswith("# ")
    found = re.findall(r"(?m)^## (.+)$", text)
    assert [t for t in found if t in SECTIONS] == list(SECTIONS)


def test_the_guide_names_what_a_remote_builder_needs():
    """REQ-040: answer 1 (a checkout of its own, python3, `gh` with a builder token, the
    project's toolchain)."""
    needs = section("What a remote builder needs")
    for phrase in ("checkout of its own", "python3", "`gh`", "builder token", "toolchain"):
        assert phrase in needs, phrase
    assert "cannot merge" in needs and "settings" in needs


def test_the_guide_points_to_the_start_and_resume_commands():
    """REQ-040: answer 1 and answer 4 (it starts with `session.py next` and a claim, and
    resumes from GitHub with `session.py after` and `resume`)."""
    start = section("Start and resume")
    for command in (
        "python3 scripts/agk/session.py next --session",
        "python3 scripts/agk/session.py claim --session",
        "python3 scripts/agk/session.py after --session",
        "python3 scripts/agk/session.py resume --pr",
    ):
        assert command in start, command
    assert "GitHub" in start


def test_each_command_the_guide_names_is_a_command_of_session_py():
    """REQ-040: answer 1 (the guide names no command that does not exist)."""
    source = SESSION.read_text(encoding="utf-8")
    for name in set(re.findall(r"scripts/agk/session\.py (\w[\w-]*)", guide())):
        assert re.search(rf'"{re.escape(name)}": ', source), name


def test_review_approval_merge_and_secrets_stay_on_the_persons_machine():
    """REQ-040: answer 1 (what stays with the person)."""
    stays = section("What stays on your machine")
    for word in ("review", "approval", "merge", "secrets"):
        assert word in stays.lower(), word


def test_the_guide_names_each_safety_rule():
    """REQ-040: answer 2 and answer 4 (each safety rule, in the guide's own section)."""
    rules = section("Safety rules")
    for phrase in SAFETY:
        assert phrase in rules, phrase
    assert "sign-in" in rules


def test_the_guide_names_no_provider():
    """REQ-040: answer 3 (generic: each need is a capability, no provider named)."""
    lowered = flat().lower()
    for name in VENDORS:
        assert not re.search(rf"\b{name}\b", lowered), name
