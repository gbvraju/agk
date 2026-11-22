"""Kit-only tests of `design.py inventory`: the skeleton of the screen and state inventory.

SPEC-0037 rule 3 (REQ-044 AC2, brief #456): the script writes `docs/design/inventory.md` from
`kit/templates/design-inventory.md`, one section for each requirement of `docs/requirements.md`
with its `- Specs:` slot filled from the `Requirements:` lines of `docs/specs/*.md` and every other
slot empty, and an empty `## Screens` part. On an existing file it only appends the missing sections
and refuses, naming the rule, a file with no Requirements part (brief #1185, whose own tests are in
`tests/kit/test_design_inventory_update.py`), and it never fills a project slot: the check, not the
script, decides that the inventory is complete. Invented data only, in `tmp_path`; files only, no
network and no model.
"""

from __future__ import annotations

import re
import subprocess
import sys

from conftest import KIT_ROOT, clean_env

SCRIPT = KIT_ROOT / "scripts" / "agk" / "design.py"
CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "design-inventory.md"
INVENTORY = "docs/design/inventory.md"

REQUIREMENTS = """# Requirements

Each requirement is a `### REQ-nnn` section with a `- Status:` line.

### REQ-101 — A reader keeps a list of books

- Acceptance: AC1 a reader adds a book; AC2 a reader removes a book
- Status: planned

### REQ-102 — A nightly job tidies the list

- Acceptance: AC1 the job removes duplicates
- Status: planned

### REQ-103 — A reader shares a list

- Acceptance: AC1 a reader sends a link on example.com
- Status: planned
"""

SPECS = {
    "0001-the-list.md": "# SPEC-0001: The list\n\n- Status: Draft\n- Requirements: REQ-101\n",
    "0002-the-job.md": (
        "# SPEC-0002: The job\n\n- Status: Approved\n- Requirements: REQ-102, REQ-101\n"
    ),
    "TEMPLATE.md": "# SPEC-nnnn: Title\n\n- Status: Draft\n- Requirements: REQ-nnn\n",
}


def project(root):
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    for name, text in SPECS.items():
        (root / "docs" / "specs" / name).write_text(text, encoding="utf-8")
    return root


def design(root, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def check(root):
    return subprocess.run(
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def sections(text, part):
    """{heading: [lines]} of the `### ` sections of one `## ` part."""
    found: dict[str, list[str]] = {}
    current = None
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == part
            current = None
        elif inside and line.startswith("### "):
            current = found.setdefault(line[4:].strip(), [])
        elif inside and current is not None and line.startswith("- "):
            current.append(line)
    return found


def test_ac2_the_template_fixes_the_shape_of_the_inventory():
    """REQ-044 AC2: SPEC-0037 rule 3 (the two parts and the fields of brief #456 answer 1)."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "## Requirements" in text and "## Screens" in text
    assert text.index("## Requirements") < text.index("## Screens")
    for field in (
        "- Specs:",
        "- Screens:",
        "no screen:",
        "- Flow:",
        "- Pattern:",
        "- Links to:",
        "- State",
        "n/a:",
    ):
        assert field in text, field
    assert "{{requirements}}" in text


def test_ac2_inventory_writes_one_section_for_each_requirement_with_its_specs(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (one section per requirement, headed by its id and title)."""
    project(tmp_path)
    proc = design(tmp_path, "inventory")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"wrote {INVENTORY}" in proc.stdout
    text = (tmp_path / INVENTORY).read_text(encoding="utf-8")
    reqs = sections(text, "Requirements")
    assert list(reqs) == [
        "REQ-101 — A reader keeps a list of books",
        "REQ-102 — A nightly job tidies the list",
        "REQ-103 — A reader shares a list",
    ]
    first, second, third = reqs.values()
    assert first == ["- Specs: SPEC-0001, SPEC-0002", "- Screens:"]
    assert second == ["- Specs: SPEC-0002", "- Screens:"]
    # Q-456-8: a requirement that no spec names gets `none`, so its Specs line is not a slot.
    assert third == ["- Specs: none", "- Screens:"]


def test_ac2_the_screens_part_is_empty_and_every_other_slot_is_empty(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (the script never fills a slot)."""
    project(tmp_path)
    assert design(tmp_path, "inventory").returncode == 0
    text = (tmp_path / INVENTORY).read_text(encoding="utf-8")
    assert sections(text, "Screens") == {}
    after = text[text.index("## Screens") :]
    assert not re.search(r"(?m)^### ", after)
    screens = re.findall(r"(?m)^- Screens:(.*)$", text)
    assert screens and all(value == "" for value in screens)


def test_ac2_the_skeleton_fails_the_check_naming_the_rule_and_the_requirement(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (the check, not the script, decides the inventory is done)."""
    project(tmp_path)
    assert design(tmp_path, "inventory").returncode == 0
    proc = check(tmp_path)
    assert proc.returncode == 1, proc.stdout
    assert f"FAIL design: rule 3: {INVENTORY}: REQ-101: the slot Screens is empty" in proc.stdout


def test_ac2_inventory_refuses_when_the_file_exists_and_changes_nothing(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (never overwritten; brief #1185 appends only)."""
    project(tmp_path)
    path = tmp_path / INVENTORY
    path.parent.mkdir(parents=True)
    path.write_text("# Design inventory\n\nfilled by hand\n", encoding="utf-8")
    proc = design(tmp_path, "inventory")
    assert proc.returncode == 1
    assert "FAIL design: rule 3:" in proc.stdout
    assert "has no Requirements part; it is never rewritten" in proc.stdout
    assert path.read_text(encoding="utf-8") == "# Design inventory\n\nfilled by hand\n"


def test_ac2_inventory_refuses_without_a_requirements_file(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (the skeleton comes from docs/requirements.md)."""
    proc = design(tmp_path, "inventory")
    assert proc.returncode == 1
    assert "FAIL design: rule 3: docs/requirements.md cannot be read" in proc.stdout
    assert not (tmp_path / INVENTORY).exists()


def test_ac2_inventory_takes_no_other_option(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (files only; the command takes only --root)."""
    project(tmp_path)
    proc = design(tmp_path, "inventory", "--name", "home")
    assert proc.returncode == 2
    assert not (tmp_path / INVENTORY).exists()


def test_ac2_the_skill_has_the_inventory_step_and_leaves_agreement_to_the_person():
    """REQ-044 AC2: SPEC-0037 rule 3 (the skill's inventory step; no session posts the line)."""
    text = (KIT_ROOT / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    assert 'design.py" inventory' in text
    assert "Approve: inventory <full head ID>" in text
    assert "check_design.py" in text
    assert re.search(r"never posts? (?:that|the `Approve: inventory`) line", text)


# Brief #1756 (amendment 217 to SPEC-0037 rule 3, ADR-0734): on the path from an idea, with no
# product requirement yet, the skeleton takes one section per milestone of the Accepted charter.

KIT_REQUIREMENTS = """# Requirements

### REQ-001 — The kit keeps its rules

- Acceptance: AC1 a rule is kept
- Status: planned

### REQ-002 — The kit checks its rules

- Acceptance: AC1 a rule is checked
- Status: planned
"""

CHARTER = """# ADR-0002: Project charter

- Status: {status}
- Date: 2026-11-22

## Context

A booking site for rooms on example.com.

## Decision

{milestones}2. **Non-goals**
   - Payments.
3. **Done means**
   - The milestones' exit statements hold.

## Consequences

None.
"""

MILESTONES = """1. **Milestones**
   - M1: a guest books a room. exit: 3 bookings can be made and read back.
   - M2: a host sees the bookings. exit: every booking is listed.
"""

CHARTER_PATH = "docs/adr/0002-project-charter.md"


def discovery(root, name, screens):
    folder = root / "docs" / "discovery"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(
        f"# Discovery: {name}\n\n- Problem: in session 2026-11-22\n- Screens: {screens}\n\n"
        "## Answers\n\n- users: open\n",
        encoding="utf-8",
    )


def idea_project(root, status="Accepted", milestones=MILESTONES, reqs=KIT_REQUIREMENTS):
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text(reqs, encoding="utf-8")
    (root / CHARTER_PATH).write_text(
        CHARTER.format(status=status, milestones=milestones), encoding="utf-8"
    )
    discovery(root, "booking", "yes")
    discovery(root, "reports", "open")
    discovery(root, "nightly", "no")
    return root


def test_ac2_the_idea_path_writes_one_section_per_charter_milestone(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 as amendment 217 proposes (brief #1756 answer 1)."""
    idea_project(tmp_path)
    proc = design(tmp_path, "inventory")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    reqs = sections((tmp_path / INVENTORY).read_text(encoding="utf-8"), "Requirements")
    sources = f"- Sources: {CHARTER_PATH}, docs/discovery/booking.md, docs/discovery/reports.md"
    assert reqs == {
        "REQ-001 — The kit keeps its rules": [
            "- Specs: none",
            "- Screens: no screen: a rule of the kit",
        ],
        "REQ-002 — The kit checks its rules": [
            "- Specs: none",
            "- Screens: no screen: a rule of the kit",
        ],
        "M1 — a guest books a room. exit: 3 bookings can be made and read back.": [
            sources,
            "- Screens:",
        ],
        "M2 — a host sees the bookings. exit: every booking is listed.": [sources, "- Screens:"],
    }


def test_ac2_a_product_requirement_keeps_todays_skeleton(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1756 answer 1: with REQ-101 up, no milestone)."""
    reqs = KIT_REQUIREMENTS + "\n### REQ-101 — A guest books a room\n\n- Status: planned\n"
    idea_project(tmp_path, reqs=reqs)
    assert design(tmp_path, "inventory").returncode == 0
    reqs_found = sections((tmp_path / INVENTORY).read_text(encoding="utf-8"), "Requirements")
    assert [h for h in reqs_found if h.startswith("M")] == []
    assert reqs_found["REQ-101 — A guest books a room"] == ["- Specs: none", "- Screens:"]


def test_ac2_a_proposed_charter_is_not_a_source(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1756 answer 7: only an Accepted charter counts)."""
    idea_project(tmp_path, status="Proposed")
    assert design(tmp_path, "inventory").returncode == 0
    reqs = sections((tmp_path / INVENTORY).read_text(encoding="utf-8"), "Requirements")
    assert list(reqs) == ["REQ-001 — The kit keeps its rules", "REQ-002 — The kit checks its rules"]


def test_ac2_a_charter_with_no_milestones_is_refused_naming_its_path_class(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1756 answer 7: refused, naming `docs/adr/`)."""
    idea_project(tmp_path, milestones="")
    proc = design(tmp_path, "inventory")
    assert proc.returncode == 1
    assert "FAIL design: rule 3:" in proc.stdout and "docs/adr/" in proc.stdout
    assert not (tmp_path / INVENTORY).exists()
