"""Tests of `design.py inventory` on an existing inventory (SPEC-0037 rule 3; REQ-044 AC2).

Brief #1185: `design.py inventory` on a new inventory writes the skeleton as before, and on an
existing one keeps every line the person wrote and only appends a `### REQ-<n> — <title>` section,
with `- Specs:` and an empty `- Screens:`, for each requirement that has none, in number order,
printing one `added REQ-<n>` line each; it never removes or rewrites a section. In both cases a kit
requirement (REQ-001 to REQ-099) gets `- Screens: no screen: a rule of the kit` instead of an empty
slot, so `check_design.py` passes after the plan's intake once the new slots are filled (ADR-0504).
Invented data only (example.com), in `tmp_path`; files only, no network and no model.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "design.py"
CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
INVENTORY = "docs/design/inventory.md"
KIT_REASON = "- Screens: no screen: a rule of the kit"

KIT_REQS = """### REQ-001 — The kit keeps its rules

- Acceptance: AC1 a rule is checked
- Status: done

### REQ-002 — The kit records decisions

- Acceptance: AC1 a decision is an ADR
- Status: done

### REQ-003 — The kit traces requirements

- Acceptance: AC1 a test names its requirement
- Status: done
"""

PROJECT_REQ = """
### REQ-{n} — {title}

- Acceptance: AC1 a visitor of example.com sees it
- Status: planned
"""

STATES = ("default", "empty", "loading", "error", "no-permission", "long-content", "success")


def write_requirements(root: Path, project: dict[int, str]) -> None:
    text = "# Requirements\n\n" + KIT_REQS
    for n, title in sorted(project.items()):
        text += PROJECT_REQ.format(n=n, title=title)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "requirements.md").write_text(text, encoding="utf-8")
    specs = root / "docs" / "specs"
    specs.mkdir(exist_ok=True)
    (specs / "0101-the-shop.md").write_text(
        "# SPEC-0101: The shop\n\n- Status: Draft\n- Requirements: REQ-101, REQ-102\n",
        encoding="utf-8",
    )


def screen(name: str) -> str:
    lines = [f"### {name}", "", "- Flow: browse", "- Pattern: detail", "- Links to: none"]
    lines += [f"- State {state}: yes" for state in STATES]
    return "\n".join(lines) + "\n"


def filled_inventory() -> str:
    """An inventory written by hand: the kit's three, REQ-101 with a screen, and a note."""
    return (
        "# Design inventory\n\nThe person's own note about example.com.\n\n## Requirements\n\n"
        "### REQ-001 — The kit keeps its rules\n\n- Specs: none\n- Screens: no screen: kit\n\n"
        "### REQ-002 — The kit records decisions\n\n- Specs: none\n- Screens: no screen: kit\n\n"
        "### REQ-003 — The kit traces requirements\n\n- Specs: none\n- Screens: no screen: kit\n\n"
        "### REQ-101 — A visitor browses the shop\n\n- Specs: SPEC-0101\n- Screens: catalogue\n\n"
        "## Screens\n\n" + screen("catalogue")
    )


def design(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, str(SCRIPT), "inventory", *args, "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def section(text: str, req: str) -> list[str]:
    """The `- ` lines of one requirement's section."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("### "):
            inside = line[4:].startswith(req)
        elif line.startswith("## "):
            inside = False
        elif inside and line.startswith("- "):
            out.append(line)
    return out


def test_ac2_a_new_inventory_gives_the_kit_requirements_no_screen(tmp_path):
    """REQ-044 AC2: brief #1185 test (a), a kit requirement is never an empty slot."""
    write_requirements(tmp_path, {101: "A visitor browses the shop"})
    proc = design(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"wrote {INVENTORY}" in proc.stdout
    text = (tmp_path / INVENTORY).read_text(encoding="utf-8")
    for req in ("REQ-001", "REQ-002", "REQ-003"):
        assert section(text, req) == ["- Specs: none", KIT_REASON], req
    assert section(text, "REQ-101") == ["- Specs: SPEC-0101", "- Screens:"]


def test_ac2_an_existing_inventory_gains_only_the_missing_requirement(tmp_path):
    """REQ-044 AC2: brief #1185 test (b), every line the person wrote is kept byte for byte."""
    write_requirements(tmp_path, {101: "A visitor browses the shop", 102: "A visitor pays"})
    path = tmp_path / INVENTORY
    path.parent.mkdir(parents=True)
    before = filled_inventory()
    path.write_text(before, encoding="utf-8")
    proc = design(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == ["added REQ-102"]
    after = path.read_text(encoding="utf-8")
    added = "### REQ-102 — A visitor pays\n\n- Specs: SPEC-0101\n- Screens:\n\n"
    head, tail = before.split("## Screens", 1)
    assert after == head + added + "## Screens" + tail
    assert section(after, "REQ-001") == ["- Specs: none", "- Screens: no screen: kit"]


def test_ac2_new_sections_are_appended_in_number_order_kit_ones_with_no_screen(tmp_path):
    """REQ-044 AC2: brief #1185 answers 1 and 2, number order and the kit reason on update."""
    write_requirements(
        tmp_path,
        {101: "A visitor browses the shop", 102: "A visitor pays", 103: "A visitor leaves"},
    )
    path = tmp_path / INVENTORY
    path.parent.mkdir(parents=True)
    text = filled_inventory()
    text = text.replace(
        "### REQ-002 — The kit records decisions\n\n- Specs: none\n- Screens: no screen: kit\n\n",
        "",
    )
    path.write_text(text, encoding="utf-8")
    proc = design(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == ["added REQ-002", "added REQ-102", "added REQ-103"]
    after = path.read_text(encoding="utf-8")
    assert section(after, "REQ-002") == ["- Specs: none", KIT_REASON]
    assert after.index("### REQ-002") < after.index("### REQ-102") < after.index("### REQ-103")
    assert after.index("### REQ-101") < after.index("### REQ-002") < after.index("## Screens")


def test_ac2_a_second_run_adds_nothing(tmp_path):
    """REQ-044 AC2: brief #1185 test (c), the update is idempotent."""
    write_requirements(tmp_path, {101: "A visitor browses the shop", 102: "A visitor pays"})
    path = tmp_path / INVENTORY
    path.parent.mkdir(parents=True)
    path.write_text(filled_inventory(), encoding="utf-8")
    assert design(tmp_path).returncode == 0
    once = path.read_text(encoding="utf-8")
    proc = design(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "added" not in proc.stdout
    assert path.read_text(encoding="utf-8") == once


def test_ac2_the_check_passes_once_the_new_slot_is_filled(tmp_path):
    """REQ-044 AC2: brief #1185 test (d), only the new Screens slot is left to fill."""
    write_requirements(tmp_path, {101: "A visitor browses the shop", 102: "A visitor pays"})
    path = tmp_path / INVENTORY
    path.parent.mkdir(parents=True)
    path.write_text(filled_inventory(), encoding="utf-8")
    assert design(tmp_path).returncode == 0
    failing = check(tmp_path)
    assert failing.returncode == 1
    assert f"rule 3: {INVENTORY}: REQ-102: the slot Screens is empty" in failing.stdout
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "- Specs: SPEC-0101\n- Screens:\n", "- Specs: SPEC-0101\n- Screens: catalogue\n"
        )
    )
    passing = check(tmp_path)
    assert passing.returncode == 0, passing.stdout + passing.stderr


def test_ac2_a_new_inventory_of_kit_and_filled_slots_passes_the_check(tmp_path):
    """REQ-044 AC2: brief #1185 answer 2, the kit's three need no hand edit on a new inventory."""
    write_requirements(tmp_path, {101: "A visitor browses the shop"})
    assert design(tmp_path).returncode == 0
    path = tmp_path / INVENTORY
    text = path.read_text(encoding="utf-8").replace(
        "- Specs: SPEC-0101\n- Screens:\n", "- Specs: SPEC-0101\n- Screens: catalogue\n"
    )
    path.write_text(text + "\n" + screen("catalogue"), encoding="utf-8")
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ac2_an_existing_file_without_a_requirements_part_is_refused_unchanged(tmp_path):
    """REQ-044 AC2: brief #1185 answer 1, a section is never removed or rewritten (Q-1185-1)."""
    write_requirements(tmp_path, {101: "A visitor browses the shop"})
    path = tmp_path / INVENTORY
    path.parent.mkdir(parents=True)
    path.write_text("# Design inventory\n\nfilled by hand\n", encoding="utf-8")
    proc = design(tmp_path)
    assert proc.returncode == 1
    assert "FAIL design: rule 3:" in proc.stdout
    assert "Requirements part" in proc.stdout
    assert path.read_text(encoding="utf-8") == "# Design inventory\n\nfilled by hand\n"
