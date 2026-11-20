"""Tests of the `foundation` kind (SPEC-0072 rule 4, build (c); REQ-079 AC3; brief #1587, ADR-0667).

Every shipped playbook's `[split] brief_order` starts with `foundation` (`default.toml`'s is
`["foundation"]`, `pilot.toml`'s starts `foundation` before `intake`, `Q-S0072-11`), and the split
gives each kind that no pair orders a `Depends-on:` the foundation brief. With a declared work type,
`plan_intake.py validate` wants one foundation brief in `M1` that every other `M1` brief depends on,
and `check_plan.py` refuses a brief file of the foundation's milestone without `Depends-on:` it;
with no work type a foundation brief is refused in both, naming the setting (rule 8's hold).
Invented data only (example.com); no network.
"""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import check_plan
import playbook_format
import pytest
from test_plan_intake import BRIEF, PRD, PRD_TEXT, SOW, SOW_TEXT, good, refused, validate, write

KIT_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
SHIPPED = sorted(p.stem for p in PLAYBOOKS.glob("*.toml"))
DECLARED = 'default_branch = "main"\n\n[delivery]\nwork_type = "web-app"\n'
FOUNDATION = "foundation"


def order(name: str) -> list[str]:
    return tomllib.loads((PLAYBOOKS / f"{name}.toml").read_text(encoding="utf-8"))["split"][
        "brief_order"
    ]


# --- the playbooks: foundation first -------------------------------------------------------------


@pytest.mark.parametrize("name", SHIPPED)
def test_ac3_every_shipped_brief_order_starts_with_foundation(name):
    """REQ-079 AC3: SPEC-0072 rule 4 (every playbook's `brief_order` gains `foundation` first)."""
    assert order(name)[0] == FOUNDATION
    assert order(name).count(FOUNDATION) == 1


def test_ac3_default_is_foundation_alone_and_pilot_starts_foundation_then_intake():
    """REQ-079 AC3: SPEC-0072 rule 4 and `Q-S0072-11`."""
    assert order("default") == [FOUNDATION]
    assert order("pilot")[:2] == [FOUNDATION, "intake"]


def test_ac3_the_split_puts_foundation_first_and_every_unordered_kind_depends_on_it(tmp_path):
    """REQ-079 AC3: SPEC-0072 rule 4 (the first milestone's briefs follow the foundation)."""
    folder = tmp_path / "config" / "playbooks"
    folder.mkdir(parents=True)
    shutil.copyfile(PLAYBOOKS / "web-app.toml", folder / "web-app.toml")
    (tmp_path / "agk.toml").write_text(DECLARED, encoding="utf-8")
    lines, problems = playbook_format.split(tmp_path, "Invoices for example.com")
    assert problems == []
    titles = [line for line in lines if line[:1].isdigit()]
    assert titles[0] == "1. Invoices for example.com: foundation"
    text = "\n".join(lines)
    foundation_block = text.split("2. ")[0].split("1. ")[1]
    assert "Depends-on" not in foundation_block
    contract = text.split("2. ")[1].split("3. ")[0]
    assert "   Depends-on: #<foundation brief>" in contract


# --- plan-intake: one foundation brief, every other M1 brief depends on it ----------------------


@pytest.fixture
def intake_repo(tmp_path: Path) -> Path:
    """The fixture of `test_plan_intake.py`: the two guard placeholders and the two sources."""
    root = tmp_path / "repo"
    write(root, "scripts/agk/guard.py", "# the data guard (a placeholder of the fixture)\n")
    write(root, ".claude/hooks/data_guard.py", "# the read hook (a placeholder of the fixture)\n")
    write(root, SOW, SOW_TEXT)
    write(root, PRD, PRD_TEXT)
    return root


def foundation_plan() -> dict:
    data = good()
    first = dict(BRIEF, key="B1", title="Foundation for example.com", foundation=True)
    second = dict(BRIEF, key="B2", depends_on=["B1"])
    data["briefs"] = [first, second]
    return data


def declare(root: Path) -> None:
    write(root, "agk.toml", DECLARED)
    write(root, "config/playbooks/web-app.toml", (PLAYBOOKS / "web-app.toml").read_text("utf-8"))


def test_ac3_plan_intake_accepts_one_foundation_brief_that_m1_depends_on(
    intake_repo,
    capsys,
):
    """REQ-079 AC3: SPEC-0072 rule 4 (`plan-intake` proposes the foundation brief first)."""
    declare(intake_repo)
    code, out = validate(intake_repo, foundation_plan(), capsys)
    assert (code, out.strip()) == (0, "ok proposals"), out


def test_ac3_plan_intake_refuses_a_work_type_plan_without_a_foundation_brief(
    intake_repo,
    capsys,
):
    """REQ-079 AC3: SPEC-0072 rule 4 (one foundation brief per plan)."""
    declare(intake_repo)
    refused(intake_repo, good(), capsys, "rule 5: briefs: no foundation brief (setting: work_type)")


def test_ac3_plan_intake_refuses_an_m1_brief_that_does_not_depend_on_it(
    intake_repo,
    capsys,
):
    """REQ-079 AC3: SPEC-0072 rule 4 (every other first-milestone brief carries `Depends-on`)."""
    declare(intake_repo)
    data = foundation_plan()
    data["briefs"][1]["depends_on"] = []
    refused(intake_repo, data, capsys, "rule 5: briefs B2: depends_on does not name foundation B1")


def test_ac3_plan_intake_refuses_a_foundation_brief_while_no_work_type_is_set(
    intake_repo,
    capsys,
):
    """REQ-079 AC3: SPEC-0072 rules 4 and 8 (the hold until a work type is set)."""
    refused(
        intake_repo,
        foundation_plan(),
        capsys,
        "rule 5: briefs B1: a foundation brief needs a work type (setting: work_type)",
    )


def test_ac3_render_writes_the_kind_line_of_the_foundation_brief():
    """REQ-079 AC3: SPEC-0072 rule 4 (the brief file says `Kind: foundation`)."""
    import plan_intake

    data = foundation_plan()
    assert "\nKind: foundation\n" in plan_intake.brief_text(data, data["briefs"][0])
    assert "Kind:" not in plan_intake.brief_text(data, data["briefs"][1])


# --- check_plan: no feature brief before the foundation --------------------------------------


def brief_file(root: Path, key: str, milestone: str, *lines: str) -> None:
    body = "\n".join([f"# {key}", "", f"Milestone: {milestone}", *lines]) + "\n"
    write(root, f"docs/plan/briefs/{milestone}/{key}.md", body)


def plan_root(tmp_path: Path, declared: bool = True) -> Path:
    root = tmp_path / "proj"
    if declared:
        declare(root)
    write(root, "docs/plan/milestones.md", "# Milestones\n\n### M1 Foundation\n\n### M2 Orders\n")
    return root


def foundation_lines(root: Path) -> list[str]:
    return check_plan.foundation_problems(root)


def test_ac3_check_plan_accepts_briefs_that_depend_on_the_foundation(tmp_path):
    """REQ-079 AC3: SPEC-0072 rule 4."""
    root = plan_root(tmp_path)
    brief_file(root, "B1", "M1", "Kind: foundation")
    brief_file(root, "B2", "M1", "Depends-on: B1")
    brief_file(root, "B3", "M2", "Depends-on: B2")
    assert foundation_lines(root) == []


def test_ac3_check_plan_refuses_a_feature_brief_before_the_foundation(tmp_path):
    """REQ-079 AC3: SPEC-0072 rule 4 (`check_plan.py` refuses a feature brief before it)."""
    root = plan_root(tmp_path)
    brief_file(root, "B1", "M1", "Kind: foundation")
    brief_file(root, "B2", "M1")
    assert foundation_lines(root) == [
        "SPEC-0072 rule 4: B2: runs before the foundation brief (no Depends-on: B1)"
    ]


def test_ac3_check_plan_refuses_a_work_type_plan_with_no_foundation_brief(tmp_path):
    """REQ-079 AC3: SPEC-0072 rule 4."""
    root = plan_root(tmp_path)
    brief_file(root, "B2", "M1")
    assert foundation_lines(root) == [
        "SPEC-0072 rule 4: docs/plan/briefs: no brief is Kind: foundation (setting: work_type)"
    ]


def test_ac3_check_plan_refuses_a_foundation_brief_outside_the_first_milestone(tmp_path):
    """REQ-079 AC3: SPEC-0072 rule 4 (the foundation comes first)."""
    root = plan_root(tmp_path)
    brief_file(root, "B1", "M2", "Kind: foundation")
    brief_file(root, "B2", "M2", "Depends-on: B1")
    assert foundation_lines(root) == [
        "SPEC-0072 rule 4: B1: the foundation brief is not in the first milestone"
    ]


def test_ac3_check_plan_refuses_a_foundation_brief_while_no_work_type_is_set(tmp_path):
    """REQ-079 AC3: SPEC-0072 rules 4 and 8 (held until a work type is set; nothing else held)."""
    root = plan_root(tmp_path, declared=False)
    brief_file(root, "B1", "M1", "Kind: foundation")
    brief_file(root, "B2", "M1")
    assert foundation_lines(root) == [
        "SPEC-0072 rule 4: B1: a foundation brief while no work type is set (setting: work_type)"
    ]


def test_ac3_a_plan_with_no_work_type_and_no_foundation_brief_is_not_held(tmp_path):
    """REQ-079 AC3: `Q-S0072-17` (the kit's own repository and an existing project)."""
    root = plan_root(tmp_path, declared=False)
    brief_file(root, "B2", "M1")
    assert foundation_lines(root) == []


def test_ac3_the_check_prints_the_refusal_in_its_run(tmp_path, capsys):
    """REQ-079 AC3: SPEC-0072 rule 4 (the refusal is a FAIL line of `check_plan.py`)."""
    root = plan_root(tmp_path)
    brief_file(root, "B1", "M1", "Kind: foundation")
    brief_file(root, "B2", "M1")
    assert check_plan.cmd_check(root) == 1
    out = capsys.readouterr().out
    assert "FAIL plan: SPEC-0072 rule 4: B2: runs before the foundation brief" in out
