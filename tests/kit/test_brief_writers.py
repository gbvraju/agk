"""Every writer of a brief runs the one brief check with its study (brief #1813, ADR-0756; REQ-037).

`check_brief.brief_result` is the one reading of a brief: the shape and the root's rules, then the
study of `brief_study.study_result`, with the protected-path warnings. No script or hook reads a
brief with a part of `check_brief.py` alone, and every body a writer makes passes it with the
study's day in the past. Invented data only (example.com); no network.
"""

from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

import brief_study
import check_brief
import plan_intake
import pytest
from test_plan_intake import GOOD, PRD, PRD_TEXT, SOW, SOW_TEXT, write

KIT_ROOT = Path(__file__).resolve().parents[2]
PARTS = ("body_problems", "brief_problems", "absent_requirements", "screens_problems",
         "touch_problems")  # fmt: skip
PAST = "2000-01-01"
REQUIREMENTS = "# Requirements\n\n### REQ-101 — Example orders\n\n- Status: planned\n"
REQUIREMENTS += f"- Source: `{PRD}:8`\n"
SHAPE = (
    'Sentence: "A team can run a thing."\nAnswers:\n1. one\n2. two\nSize: M\n'
    "Advances: REQ-101\nTouches: docs/x.md\nPriority: 1\n"
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)


@pytest.fixture
def past(monkeypatch):
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: PAST)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write(root, "scripts/agk/guard.py", "# the data guard (a placeholder of the fixture)\n")
    write(root, ".claude/hooks/data_guard.py", "# the read hook (a placeholder of the fixture)\n")
    write(root, SOW, SOW_TEXT)
    write(root, PRD, PRD_TEXT)
    write(root, "docs/requirements.md", REQUIREMENTS)
    write(root, "docs/x.md", "x\n")
    write(root, "docs/specs/TEMPLATE.md", (KIT_ROOT / "docs/specs/TEMPLATE.md").read_text("utf-8"))
    return root


def rendered(root: Path) -> list[str]:
    data = copy.deepcopy(GOOD)
    path = root.parent / "proposals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert plan_intake.main(["render", "--proposals", str(path), "--root", str(root)]) == 0
    bodies = []
    for brief in sorted((root / "docs/plan/briefs").rglob("*.md")):
        body = re.sub(r"(?m)^Advances: .*$", "Advances: REQ-101", brief.read_text("utf-8"))
        bodies.append(re.sub(r"(?m)^Depends-on: .*$", "Depends-on: #12", body))
    return bodies


def readers(path: Path) -> list[str]:
    """Each read of a part of `check_brief.py`: `check_brief.<part>` or `from check_brief`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr in PARTS
            and isinstance(node.value, ast.Name)
            and node.value.id == "check_brief"
        ):
            found.append(f"{path.name}:{node.lineno} check_brief.{node.attr}")
        if isinstance(node, ast.ImportFrom) and node.module == "check_brief":
            found += [f"{path.name}:{node.lineno} from check_brief import {a.name}"
                      for a in node.names if a.name in PARTS or a.name == "*"]  # fmt: skip
    return found


def test_ac4_no_writer_reads_a_brief_with_a_part_of_the_check():
    """REQ-037 AC4: brief #1813 answer 7 (no new writer checks the shape and skips the study)."""
    files = sorted((KIT_ROOT / "scripts" / "agk").glob("*.py"))
    files += sorted((KIT_ROOT / ".claude" / "hooks").glob("*.py"))
    found = [r for f in files if f.name != "check_brief.py" for r in readers(f)]
    assert found == [], found


def test_ac4_the_scan_finds_a_read_of_a_part(tmp_path):
    """REQ-037 AC4: brief #1813 answer 7 (the scan itself: an attribute read and an import)."""
    path = tmp_path / "writer.py"
    path.write_text(
        "import check_brief\nfrom check_brief import touch_problems\n"
        "x = check_brief.screens_problems\ny = check_brief.open_holders\n",
        encoding="utf-8",
    )
    assert sorted(r.split(" ", 1)[1] for r in readers(path)) == [
        "check_brief.screens_problems", "from check_brief import touch_problems",
    ]  # fmt: skip


def test_ac4_brief_result_is_the_shape_then_the_study(repo, past):
    """REQ-037 AC4: brief #1813 answer 1 (a shape failure first; the study only on a pass)."""
    failures, warnings = check_brief.brief_result('Sentence: "x"\n', repo)
    assert failures and not any(f.startswith("study:") for f in failures) and warnings == []
    failures, _ = check_brief.brief_result(SHAPE, repo)
    assert any(f.startswith("study: exactly one line Class:") for f in failures), failures
    assert check_brief.brief_result(SHAPE, None) == ([], [])


def test_ac4_brief_result_warns_before_the_day(repo, monkeypatch):
    """REQ-037 AC4: brief #1813 answer 5 (no day set: warnings only; brief #1815 answer 1)."""
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: None)
    failures, warnings = check_brief.brief_result(SHAPE, repo)
    assert failures == [] and any(w.startswith("study: exactly one line Class:") for w in warnings)


def test_ac4_the_study_day_ships_unset():
    """REQ-037 AC4: brief #1813 answer 5; brief #1815 answers 1 and 6 (the day is a setting of
    agk.toml, no constant, and no project template sets one)."""
    assert not hasattr(brief_study, "STUDY_FAILS_FROM")
    import config

    for name in ("agk.toml", "agk.adopt.toml", "personal.toml"):
        text = (KIT_ROOT / "kit" / "templates" / name).read_text(encoding="utf-8")
        assert "brief_study_fails_from" not in text, name
    assert config.brief_study_fails_from(KIT_ROOT) is not None  # the kit's own day (answer 6)


def test_ac4_every_rendered_brief_passes_the_full_check_on_a_past_day(repo, past):
    """REQ-037 AC4: brief #1813 answers 2, 3 and 7 (`brief_text` and `issue_body`)."""
    bodies = rendered(repo)
    assert len(bodies) == 1
    for body in bodies:
        failures, warnings = check_brief.brief_result(body, repo)
        assert failures == [], failures
        names = ("Speed", "Quality", "GitHub", "Cost", "Tests", "Wiring", "Prior", "Class")
        for name in names:
            assert f"study: the {name} line is the render's placeholder" in warnings, warnings
        brief = {"key": "B1", "body": body, "milestone": "M1"}
        failures, _ = check_brief.brief_result(plan_intake.issue_body(brief, {"M1": 3}), repo)
        assert failures == [], failures


def test_ac4_the_rendered_study_lines_follow_contexts(repo):
    """REQ-037 AC4: brief #1813 answer 2 (the lines and their placeholders, in order)."""
    (body,) = rendered(repo)
    lines = body.splitlines()
    at = next(i for i, x in enumerate(lines) if x.startswith("Contexts:"))
    assert lines[at + 1 : at + 10] == [
        "Impact:",
        "Speed: (verify) for the person to state",
        "Quality: (verify) for the person to state",
        "GitHub: (verify) for the person to state",
        "Cost: (verify) for the person to state",
        "Tests: (verify) for the person to state",
        "Wiring: none: (verify) for the person to state",
        "Prior: none: (verify) for the person to state; brief_study.py lists the candidates",
        "Class: (verify) for the person to state; seen 0 (verify)",
    ]


def test_ac4_a_placeholder_warns_on_any_day_and_never_fails(repo, monkeypatch):
    """REQ-037 AC4: brief #1813 answer 3 (a placeholder is never taken for a study)."""
    (body,) = rendered(repo)
    for day in (None, PAST, "2999-01-01"):
        monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root, day=day: day)
        failures, warnings = brief_study.study_result(body, repo)
        assert failures == []
        assert "study: the Class line is the render's placeholder" in warnings


def template_block() -> str:
    text = (KIT_ROOT / "docs" / "briefs" / "TEMPLATE.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = lines.index("Impact:")
    end = next(i for i, x in enumerate(lines) if x.startswith("Class:"))
    return "\n".join(lines[start : end + 1]) + "\n"


def test_ac4_the_templates_study_block_passes_on_a_past_day(repo, past):
    """REQ-037 AC4: brief #1813 answers 4 and 7 (the lines in the form the check reads)."""
    block = template_block()
    assert [x.split(":")[0] for x in block.splitlines()] == [
        "Impact", "Speed", "Quality", "GitHub", "Cost", "Tests", "Wiring", "Prior", "Class",
    ]  # fmt: skip
    assert all("(verify)" in x for x in block.splitlines()[1:])
    failures, warnings = check_brief.brief_result(SHAPE + block, repo)
    assert failures == [], failures
    assert "study: the Wiring line is the render's placeholder" in warnings


def test_ac4_the_template_keeps_one_example_each_below_the_block():
    """REQ-037 AC4: brief #1813 answer 4 (examples in the comment, none read as a study line)."""
    text = (KIT_ROOT / "docs" / "briefs" / "TEMPLATE.md").read_text(encoding="utf-8")
    below = text[text.index("Class:") :]
    comment = below[below.index("<!--") : below.index("-->")]
    for name in ("Impact", "Speed", "Quality", "GitHub", "Cost", "Tests", "Wiring", "Prior",
                 "Class"):  # fmt: skip
        assert f"- {name}: e.g." in comment, name
    assert not re.search(r"(?m)^(Wiring|Prior|Class):", comment)
