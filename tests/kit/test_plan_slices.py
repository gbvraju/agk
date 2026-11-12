"""Tests of shared components and demoable slices in the plan (SPEC-0043 rules 4, 5 and 7 with
amendment 164 items 3 and 4, build (r), ADR-0464; REQ-050, REQ-044).

REQ-050 AC2 and AC3; REQ-044.

The proposals may hold `components` (`C1`, `C2`, ...), each with one brief in `M1 Foundation`; a
screen brief names its `screens` and depends directly on the brief of every component those screens
use; with a `Kind: design` source every later milestone names its `screens`, its exit names
`design_compare.py`, `match` and a signed-off version, and every `<screen>/<state>` heading of the
source is in a milestone. `render` writes `Demo:` and `Screens:` lines and prints the playbook's
`batch_by`; `check_plan.py` fails a later milestone without `Demo:` when a design source exists. A
plan with no design source is unchanged. Invented sources only (example.com), no network.
"""

from __future__ import annotations

import copy
import socket
from pathlib import Path

import check_plan
import pytest
from test_plan_intake import SOW, TITLE, refused, validate, write
from test_plan_render import proposals, render
from test_plan_render import repo as repo  # noqa: F401 - the fixture, reused

KIT_ROOT = Path(__file__).resolve().parents[2]
PROTO = "docs/sources/prototype-i1.md"
PARTS = "docs/sources/shop-components-i1.md"
PROTO_TEXT = (
    "Source: Example imported prototype i1\nKind: design\nVersion: i1 " + "a" * 64 + "\n"
    "Date: 2026-11-01\n\n## orders/default\n\nThe order list.\n\n"
    "## order-detail/default\n\nOne order.\n"
)
PARTS_TEXT = (
    "Source: shared components of imported prototype i1\nKind: design\nVersion: i1 " + "a" * 64
) + "\nDate: 2026-11-01\n\n## app-nav\n\nstructure: nav.app-nav: a a a\n- orders/default\n"
PARTS_TEXT += "- order-detail/default\n"
INVENTORY = "# Design inventory\n\n## Requirements\n\n## Screens\n\n"
for _screen in ("orders", "order-detail", "settings"):
    INVENTORY += f"### {_screen}\n\n- Flow: orders\n- Pattern: detail\n- Links to: none\n"
    INVENTORY += "- State default: yes\n- State empty: n/a: never empty\n\n"
SIGNOFFS = (
    "# Sign-offs\n\n| kind | version | digest | head | date | comment |\n"
    "|---|---|---|---|---|---|\n"
    f"| design | i1 | {'b' * 64} | {'c' * 40} | 2026-11-02 | https://example.com/c/1 |\n"
)
EXIT = "every screen and state reads match in design_compare.py against i1"
PAIRS = ["orders/default", "order-detail/default"]
COMPONENT = {"key": "C1", "name": "App navigation", "screens": ["orders", "order-detail"]}
COMPONENT |= {"pattern": None, "sources": [f"{PARTS}#app-nav"]}


@pytest.fixture(autouse=True)
def no_network(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("the plan tools open no socket")

    monkeypatch.setattr(socket, "socket", refuse)


@pytest.fixture
def design(repo: Path) -> Path:  # noqa: F811 - the reused fixture
    """The repository with a prototype source, its components, an inventory and a sign-off."""
    write(repo, PROTO, PROTO_TEXT)
    write(repo, PARTS, PARTS_TEXT)
    write(repo, "docs/design/inventory.md", INVENTORY)
    write(repo, "docs/design/signoffs.md", SIGNOFFS)
    return repo


def sliced() -> dict:
    """M1 Foundation with the component brief B1; M2 a slice whose brief B2 builds the screens."""
    data = proposals()
    data["components"] = [copy.deepcopy(COMPONENT)]
    m1 = data["milestones"][0] | {"title": "Foundation", "exit": "all 1 component briefs merge"}
    m2 = copy.deepcopy(m1) | {"id": "M2", "title": TITLE, "exit": EXIT, "screens": list(PAIRS)}
    m2["sources"] = [f"{PROTO}#{p}" for p in PAIRS]
    data["milestones"] = [m1, m2]
    data["requirements"][0]["milestone"] = "M2"
    data["requirements"][0]["sources"] += [f"{PROTO}#{p}" for p in PAIRS]
    data["briefs"][0]["component"] = "C1"
    data["briefs"][1] |= {"milestone": "M2", "screens": list(PAIRS)}
    return data


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def no_text(out: str) -> None:
    for text in (TITLE, "App navigation", "Foundation", "The order list"):
        assert text not in out, out


# --- rules 4 and 5: components ------------------------------------------------------------------


def test_ac2_components_and_slices_pass(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 4 with amendment 164 items 3 and 4."""
    code, out = validate(design, sliced(), capsys)
    assert code == 0 and out.strip() == "ok proposals", out


def test_ac2_a_screen_brief_must_depend_on_its_components_brief(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 5 with `Q-1089-3`, directly, naming brief, component and its brief."""
    data = sliced()
    data["briefs"][1]["depends_on"] = []
    out = refused(
        design, data, capsys, "rule 5: briefs B2: depends_on does not name B1 of component C1"
    )
    no_text(out)
    data["briefs"].append(copy.deepcopy(data["briefs"][1]) | {"key": "B3", "depends_on": ["B2"]})
    data["briefs"][1]["depends_on"] = ["B1"]
    refused(design, data, capsys, "rule 5: briefs B3: depends_on does not name B1 of component C1")


@pytest.mark.parametrize(
    ("screens", "line"),
    [
        (["orders"], "rule 5: components C1: screens names fewer than two screens"),
        (["orders", "orders"], "rule 5: components C1: screens names fewer than two screens"),
        (["orders", "checkout"], "rule 5: components C1: screens names a screen the inventory"),
    ],
)
def test_ac2_a_component_needs_two_inventory_screens(
    design: Path, screens: list[str], line: str, capsys
) -> None:
    """REQ-044, REQ-050 AC2: rule 5, two or more screens, each one the inventory lists."""
    data = sliced()
    data["components"][0]["screens"] = screens
    no_text(refused(design, data, capsys, line))


def test_ac2_a_component_has_exactly_one_brief_in_m1(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, no brief, two briefs, or a brief outside M1 is refused."""
    data = sliced()
    del data["briefs"][0]["component"]
    refused(design, data, capsys, "rule 5: components C1: no brief in M1")
    data = sliced()
    data["briefs"].append(copy.deepcopy(data["briefs"][0]) | {"key": "B3"})
    refused(design, data, capsys, "rule 5: components C1: more than one brief")
    data = sliced()
    data["briefs"][0]["milestone"] = "M2"
    data["briefs"].append(copy.deepcopy(data["briefs"][1]) | {"key": "B3", "milestone": "M1"})
    del data["briefs"][2]["screens"]
    refused(design, data, capsys, "rule 5: components C1: no brief in M1")


def test_ac2_a_brief_component_must_name_a_component(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a `component` that names nothing."""
    data = sliced()
    data["briefs"][0]["component"] = "C9"
    refused(design, data, capsys, "rule 5: briefs B1: component names nothing")


def test_ac2_m1_is_titled_foundation_and_component_keys_run_in_order(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, `M1` is `Foundation` with `components`; keys run C1, C2, ..."""
    data = sliced()
    data["milestones"][0]["title"] = "Start"
    out = refused(design, data, capsys, "rule 4: milestones M1: title is not Foundation")
    assert "Start" not in out
    data = sliced()
    data["components"][0]["key"] = "C2"
    data["briefs"][0]["component"] = "C2"
    refused(design, data, capsys, "rule 4: components C2: keys run C1, C2, ... in order")
    data = sliced()
    data["components"][0]["shape"] = "nav"
    refused(design, data, capsys, "rule 4: components C1: unknown key shape")
    data = sliced()
    data["components"][0]["pattern"] = 3
    refused(design, data, capsys, "rule 4: components C1: pattern is not text or null")


# --- rule 5: demoable slices, with a design source -----------------------------------------------


def test_ac2_a_later_milestone_without_screens_is_refused(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 5 with amendment 164 item 4."""
    data = sliced()
    del data["milestones"][1]["screens"]
    refused(design, data, capsys, "rule 5: milestones M2: no screens")


@pytest.mark.parametrize(
    "exit_text",
    [
        "every screen reads match against i1",  # no design_compare.py
        "every screen passes design_compare.py against i1",  # no `match`
        "every screen reads match in design_compare.py against i2",  # i2 is not signed off
        "every screen reads match in design_compare.py",  # no version
    ],
)
def test_ac2_a_slice_exit_names_the_comparison_and_a_signed_off_version(
    design: Path, exit_text: str, capsys
) -> None:
    """REQ-044, REQ-050 AC2: rule 5, `design_compare.py`, `match` and a `design` row's version."""
    data = sliced()
    data["milestones"][1]["exit"] = exit_text
    out = refused(
        design, data, capsys, "rule 5: milestones M2: exit does not name design_compare.py"
    )
    assert exit_text not in out


def test_ac2_a_slice_pair_the_inventory_does_not_list_is_refused(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, every pair of a milestone's `screens` is in the inventory."""
    data = sliced()
    data["milestones"][1]["screens"].append("orders/loading")
    refused(design, data, capsys, "rule 5: milestones M2: screens names a pair the inventory")


def test_ac2_a_source_screen_no_milestone_lists_is_refused(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 5 with `Q-1089-6`, naming the source's heading location."""
    data = sliced()
    data["milestones"][1]["screens"] = ["orders/default"]
    refused(
        design,
        data,
        capsys,
        f"rule 5: {PROTO}#order-detail/default: no milestone lists this screen and state",
    )


def test_ac2_without_a_design_source_no_slice_rule_applies(design: Path, capsys) -> None:
    """REQ-050 AC2: a plan with no design source is validated as before."""
    for rel in (PROTO, PARTS):
        (design / rel).unlink()
    data = sliced()
    del data["components"], data["briefs"][0]["component"], data["briefs"][1]["screens"]
    del data["milestones"][1]["screens"]
    data["milestones"][1]["exit"] = "all 2 order screens pass"
    data["milestones"][1]["sources"] = [f"{SOW}#Milestones"]
    data["requirements"][0]["sources"] = data["requirements"][0]["sources"][:2]
    code, out = validate(design, data, capsys)
    assert code == 0 and out.strip() == "ok proposals", out


# --- rule 7: render ------------------------------------------------------------------------------


def test_ac2_render_writes_foundation_and_the_demo_lines(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, `Demo:` after `Exit:`, and the screen brief's `Screens:` line."""
    code, out = render(design, sliced(), capsys)
    assert code == 0, out
    milestones = read(design, "docs/plan/milestones.md")
    assert "### M1 Foundation\n\nExit: all 1 component briefs merge\nDemo: none (foundation)\n" in (
        milestones
    )
    assert f"\nExit: {EXIT}\nDemo: orders/default, order-detail/default\n" in milestones
    screen_brief = read(design, "docs/plan/briefs/M2/B2.md")
    assert "\nScreens: i1 orders/default, order-detail/default\n" in screen_brief
    assert "\nDepends-on: B1\n" in screen_brief
    assert "Screens:" not in read(design, "docs/plan/briefs/M1/B1.md")


def test_ac2_render_prints_the_declared_playbooks_batch_by(design: Path, capsys) -> None:
    """REQ-050 AC2: rule 4 with amendment 164 item 4, `batch_by` read from the playbook."""
    code, out = render(design, sliced(), capsys)
    assert code == 0 and "Milestone order for the person: no playbook declares batch_by" in out
    for rel in ("docs/plan", "docs/specs/0001-orders.md"):
        path = design / rel
        __import__("shutil").rmtree(path) if path.is_dir() else path.unlink()
    write(design, "agk.toml", '[delivery]\nwork_type = "web-app"\n')
    for rel in ("config/playbooks/default.toml", "config/playbooks/web-app.toml"):
        write(design, rel, read(KIT_ROOT, rel))
    code, out = render(design, sliced(), capsys)
    assert code == 0, out
    line = (
        "Milestone order for the person: demo value: the joins that show the most in a demo"
        " come first (playbook config/playbooks/web-app.toml)"
    )
    assert line in out


def test_ac2_render_without_a_design_source_is_unchanged(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050 AC2: no `Demo:` line and no milestone order without a design source."""
    code, out = render(repo, proposals(), capsys)
    assert code == 0, out
    assert "Demo:" not in read(repo, "docs/plan/milestones.md")
    assert "Milestone order" not in out
    assert "Screens:" not in read(repo, "docs/plan/briefs/M1/B2.md")


# --- rule 10: check_plan.py ----------------------------------------------------------------------


def test_ac3_check_plan_fails_a_later_milestone_without_a_demo_line(design: Path, capsys) -> None:
    """REQ-050 AC3: rule 10 with amendment 164 item 4, while a `Kind: design` file exists."""
    assert render(design, sliced(), capsys)[0] == 0
    assert check_plan.main(["--root", str(design)]) == 0, capsys.readouterr().out
    capsys.readouterr()
    rel = "docs/plan/milestones.md"
    text = read(design, rel)
    write(design, rel, text.replace("Demo: orders/default, order-detail/default\n", ""))
    code = check_plan.main(["--root", str(design)])
    out = capsys.readouterr().out
    assert code == 1 and f"FAIL plan: rule 10: {rel}: M2: no Demo: line" in out, out
    assert "M1: no Demo" not in out
    write(design, rel, text.replace("Demo: none (foundation)\n", ""))
    assert check_plan.main(["--root", str(design)]) == 0, capsys.readouterr().out


def test_ac3_check_plan_needs_no_demo_line_without_a_design_source(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050 AC3: rule 10, a plan with no `Kind: design` file is not failed for `Demo:`."""
    data = proposals()
    second = copy.deepcopy(data["milestones"][0]) | {"id": "M2"}
    data["milestones"].append(second)
    data["briefs"][1]["milestone"] = "M2"
    assert render(repo, data, capsys)[0] == 0
    capsys.readouterr()
    assert check_plan.main(["--root", str(repo)]) == 0, capsys.readouterr().out
