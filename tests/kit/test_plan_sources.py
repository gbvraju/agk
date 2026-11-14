"""Tests of the planning sources of a project that starts from an idea (SPEC-0043 rules 2a and 2b as
amendment 174 proposes; REQ-050; brief #1216, ADR-0515).

`plan_sources.py vision` writes once, as a new file, `docs/sources/vision.md` (`Kind: charter`) from
`constitution/vision.md` and the Accepted charter ADR `docs/adr/<n>-project-charter.md`, every
heading kept; `plan_sources.py architecture` writes once `docs/sources/architecture.md`
(`Kind: other`) from the Accepted stack ADR `docs/adr/<n>-stack-options.md`. Each refuses a Proposed
(or missing) ADR, a missing vision and an existing file, writing nothing. With a signed-off kit
version turned into a design source (`design_import.py source --version v<n>`), `plan_intake.py
states` and `check_plan.py` read the three files as sources. Invented data only (example.com), in
`tmp_path`; no network.
"""

from __future__ import annotations

import re
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_plan  # noqa: E402
import design_signoff as ds  # noqa: E402

try:
    import plan_sources as ps  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    ps = None

SCRIPTS = KIT_ROOT / "scripts" / "agk"
PLAN_SOURCES = SCRIPTS / "plan_sources.py"
DESIGN_IMPORT = SCRIPTS / "design_import.py"
PLAN_INTAKE = SCRIPTS / "plan_intake.py"
CHECK_PLAN = SCRIPTS / "check_plan.py"
VISION_SOURCE = "docs/sources/vision.md"
ARCH_SOURCE = "docs/sources/architecture.md"
CHARTER = "docs/adr/0002-project-charter.md"
STACK = "docs/adr/0003-stack-options.md"
KIT_SOURCE = "docs/sources/shop-prototype-v1.md"
HEAD = "0123456789abcdef0123456789abcdef01234567"
LINK = "https://example.com/acme/shop/pull/12#issuecomment-345"

VISION = """# Vision

## What this is for

A small shop at shop.example.com lets its customers see their orders.

## Who it serves

The customers of the shop and the person who runs it.

## How success is measured

Every order placed shows in the list within one minute.

## Out of scope

Payments and returns.
"""

CHARTER_TEXT = """# ADR-0002: Project charter

- Status: {status}
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001
- Protected classes: `constitution/`

## Context

The shop wants one list of orders.

## Decision

1. **Discovery**
   - users: the customers of the shop
2. **Milestones**
   - M1 the order list; exit: every order placed shows in the list
3. **Non-goals**: payments.
4. **Done means**: the list is in use.

## Consequences

One list to keep.

## Residual

- 2026-11-10: none.
"""

STACK_TEXT = """# ADR-0003: Stack options

- Status: {status}
- Date: 2026-11-11
- Deciders: maintainers
- Related: ADR-0002
- Requirements: REQ-001

## Context

The shop needs a stack.

## Decision

1. **Options**
   - Option A — a small web server. Trade-offs: simple. Practices: pinned actions.
2. **Practices**
   - pinned actions: check (step: pins)
3. **Chosen**: Option A — the smallest that serves the list

## Consequences

One server.

## Residual

- 2026-11-11: none.
"""

INVENTORY = """# Design inventory

## Screens

### orders

- Flow: see the orders
- State default: yes
- State empty: yes
- State error: yes
- State loading: n/a: read at once
"""

PAGES = {
    "orders--default.html": "<title>Orders</title><h1>Your orders</h1><p>Two orders.</p>\n",
    "orders--empty.html": "<title>No orders</title><p>You have no orders yet.</p>\n",
    "orders--error.html": '<title>Error</title><div role="status">The list did not load.</div>\n',
}


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(tmp_path: Path, charter: str = "Accepted", stack: str = "Accepted") -> Path:
    root = tmp_path / "proj"
    write(root, "constitution/vision.md", VISION)
    write(root, CHARTER, CHARTER_TEXT.format(status=charter))
    write(root, STACK, STACK_TEXT.format(status=stack))
    return root


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, *args], capture_output=True, text=True, check=False
    )


def sources(root: Path, command: str) -> subprocess.CompletedProcess:
    return run(str(PLAN_SOURCES), command, "--root", str(root))


def headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("#")]


def tree(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    }


# --- the vision source ----------------------------------------------------------------------------


def test_the_vision_source_is_written_once_with_every_heading_kept(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, `Kind: charter` from the vision and the charter ADR."""
    root = project(tmp_path)
    proc = sources(root, "vision")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.startswith(f"wrote {VISION_SOURCE}")
    text = (root / VISION_SOURCE).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "Source: vision and project charter ADR-0002"
    assert lines[1] == "Kind: charter"
    assert lines[2] == f"Version: ADR-0002 {ds.digest(root, ['constitution/vision.md', CHARTER])}"
    assert re.fullmatch(r"Date: \d{4}-\d{2}-\d{2}", lines[3]) and lines[4] == ""
    body = headings(text)
    for heading in headings(VISION) + headings(CHARTER_TEXT.format(status="Accepted")):
        assert heading in body
    assert VISION in text and CHARTER_TEXT.format(status="Accepted") in text
    assert check_plan.source_problems(root) == []
    assert check_plan.location_problem(root, f"{VISION_SOURCE}#How success is measured") is None
    assert check_plan.location_problem(root, f"{VISION_SOURCE}#Decision") is None


def test_a_second_vision_run_refuses_the_existing_file_and_leaves_it(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, written once, never over an existing file."""
    root = project(tmp_path)
    assert sources(root, "vision").returncode == 0
    before = (root / VISION_SOURCE).read_bytes()
    proc = sources(root, "vision")
    assert proc.returncode == 1
    assert "rule 2b" in proc.stdout and VISION_SOURCE in proc.stdout
    assert (root / VISION_SOURCE).read_bytes() == before


def test_a_proposed_charter_is_refused_writing_nothing(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, only an Accepted charter ADR is a source."""
    root = project(tmp_path, charter="Proposed")
    proc = sources(root, "vision")
    assert proc.returncode == 1
    assert "rule 2b" in proc.stdout and CHARTER in proc.stdout and "Accepted" in proc.stdout
    assert not (root / "docs" / "sources").exists()


def test_the_newest_charter_is_read_and_a_proposed_newer_one_refuses(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, the highest-numbered charter ADR is the charter."""
    root = project(tmp_path)
    newer = "docs/adr/0007-project-charter.md"
    write(root, newer, CHARTER_TEXT.format(status="Proposed").replace("0002", "0007"))
    proc = sources(root, "vision")
    assert proc.returncode == 1 and newer in proc.stdout
    (root / newer).write_text(CHARTER_TEXT.format(status="Accepted"), encoding="utf-8")
    assert sources(root, "vision").returncode == 0
    assert "ADR-0007" in (root / VISION_SOURCE).read_text(encoding="utf-8").splitlines()[0]


def test_no_charter_or_no_vision_is_refused_writing_nothing(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, both files are needed."""
    root = project(tmp_path)
    (root / CHARTER).unlink()
    proc = sources(root, "vision")
    assert proc.returncode == 1 and "rule 2b" in proc.stdout and "charter" in proc.stdout
    root = project(tmp_path / "second")
    (root / "constitution" / "vision.md").unlink()
    proc = sources(root, "vision")
    assert proc.returncode == 1 and "constitution/vision.md" in proc.stdout
    assert not (root / "docs" / "sources").exists()


# --- the architecture source ----------------------------------------------------------------------


def test_the_architecture_source_is_written_once_from_the_accepted_stack(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, `Kind: other` from the Accepted stack ADR."""
    root = project(tmp_path)
    proc = sources(root, "architecture")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (root / ARCH_SOURCE).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[:2] == ["Source: stack ADR-0003", "Kind: other"]
    assert lines[2] == f"Version: ADR-0003 {ds.digest(root, [STACK])}"
    assert STACK_TEXT.format(status="Accepted") in text
    assert check_plan.source_problems(root) == []
    again = sources(root, "architecture")
    assert again.returncode == 1 and ARCH_SOURCE in again.stdout


def test_a_proposed_or_missing_stack_is_refused_writing_nothing(tmp_path):
    """REQ-050 AC1: amendment 174 item 2, the stack ADR must be Accepted."""
    root = project(tmp_path, stack="Proposed")
    proc = sources(root, "architecture")
    assert proc.returncode == 1 and STACK in proc.stdout and "Accepted" in proc.stdout
    (root / STACK).unlink()
    proc = sources(root, "architecture")
    assert proc.returncode == 1 and "rule 2b" in proc.stdout and "stack" in proc.stdout
    assert not (root / "docs" / "sources").exists()


@pytest.mark.parametrize("args", [[], ["other"], ["vision", "--root"], ["vision", "--x", "y"]])
def test_a_malformed_command_exits_2_with_the_usage(tmp_path, args):
    """REQ-050 AC1: amendment 174 item 2, the two commands and `--root` only."""
    proc = run(str(PLAN_SOURCES), *args)
    assert proc.returncode == 2
    assert "usage: plan_sources.py" in proc.stderr


def test_no_connection_is_made_and_the_text_only_reads(tmp_path, monkeypatch):
    """REQ-050 AC2: no network (a socket guard); `vision_text` writes nothing."""
    assert ps is not None, "scripts/agk/plan_sources.py is missing"
    root = project(tmp_path)

    def refuse(*args, **kwargs):
        raise AssertionError("plan_sources opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    before = tree(root)
    text = ps.vision_text(root, today="2026-11-14")
    assert text.splitlines()[3] == "Date: 2026-11-14"
    assert ps.architecture_text(root, today="2026-11-14").splitlines()[1] == "Kind: other"
    assert tree(root) == before
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:subprocess|webbrowser|socket|urllib|http\b|requests|ssl)\b",
        PLAN_SOURCES.read_text(encoding="utf-8"),
        re.M,
    )


# --- the path from an idea: the planning commands read them as sources ----------------------------


def idea_project(tmp_path: Path, pages: dict[str, str] = PAGES) -> Path:
    """A project from an idea: vision, charter and stack Accepted, a signed-off kit version v1."""
    root = project(tmp_path)
    write(root, "docs/design/inventory.md", INVENTORY)
    for name, text in pages.items():
        write(root, f"docs/design/prototype/v1/{name}", text)
    write(
        root,
        ds.SIGNOFFS,
        "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
        f"|---|---|---|---|---|---|\n| design | v1 | {ds.version_digest(root, 'v1')} | {HEAD} |"
        f" 2026-11-12 | {LINK} |\n",
    )
    write(root, "scripts/agk/guard.py", "# the data guard (a placeholder of the fixture)\n")
    write(root, ".claude/hooks/data_guard.py", "# the read hook (a placeholder of the fixture)\n")
    for command in ("vision", "architecture"):
        proc = sources(root, command)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = run(str(DESIGN_IMPORT), "source", "--version", "v1", "--slug", "shop", "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root


def test_states_and_check_plan_read_the_three_sources(tmp_path):
    """REQ-050 AC1: amendment 174 item 3, `plan_intake.py states` and `check_plan.py` read them."""
    root = idea_project(tmp_path)
    states = run(str(PLAN_INTAKE), "states", "--root", str(root))
    assert states.returncode == 0, states.stdout + states.stderr
    assert states.stdout == "ok states (none to ask)\n"
    plan = run(str(CHECK_PLAN), "--root", str(root))
    assert plan.returncode == 0, plan.stdout + plan.stderr
    assert "ok plan (no plan)" in plan.stdout
    kinds = {
        p.relative_to(root).as_posix(): check_plan.header(p.read_text(encoding="utf-8"))["Kind"]
        for p in check_plan.source_files(root)
    }
    assert kinds == {VISION_SOURCE: "charter", ARCH_SOURCE: "other", KIT_SOURCE: "design"}
    assert check_plan.design_source(root)


def test_states_asks_for_a_yes_state_the_kit_version_does_not_draw(tmp_path):
    """REQ-050 AC1: amendment 174 item 3, the kit source's headings are what `states` reads."""
    pages = {k: v for k, v in PAGES.items() if k != "orders--error.html"}
    root = idea_project(tmp_path, pages)
    states = run(str(PLAN_INTAKE), "states", "--root", str(root))
    assert states.returncode == 0, states.stdout + states.stderr
    assert states.stdout.splitlines() == [f"{KIT_SOURCE}#orders/default error (verify)"]
