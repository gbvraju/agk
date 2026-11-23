"""check_brief.py and the study lines of a brief (brief #1800, ADR-0752; REQ-037)."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import brief_study  # noqa: E402

SHIPPED = brief_study.STUDY_FAILS_FROM  # what a child process reads, before any monkeypatch

SHAPE = (
    'Sentence: "A team can run a thing."\nAnswers:\n1. one\n2. two\nSize: M\n'
    "Advances: new\nTouches: scripts/agk/tool.py, docs/x.md\nPriority: 1\n"
    "Contexts: kit (x); github (x); local (x); personal (x); stacks (x)\n"
)
IMPACT = (
    "Impact:\nSpeed: 2 minutes more per brief (measured on three briefs)\n"
    "Quality: a missed decision fails on the brief\nGitHub: none: no workflow change\n"
    "Cost: none: file-only check\nTests: one new test file\n"
)
WIRING = "Wiring: scripts/agk/tool.py:main called by skills/brief/SKILL.md\n"
PRIOR = "Prior: none: searched docs/adr and docs/specs for tool.py\n"
CLASS = "Class: a missed earlier decision; seen 0 (searched docs/adr)\n"
STUDIED = SHAPE + IMPACT + WIRING + PRIOR + CLASS
BEFORE = "2026-11-24"
AFTER = "2099-01-01"


@pytest.fixture(autouse=True)
def switch_day(monkeypatch):
    """The roll-in's switch day as the maintainers would set it (Q-1800-1)."""
    monkeypatch.setattr(brief_study, "STUDY_FAILS_FROM", "2026-12-01")


def tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / "scripts" / "agk" / "tool.py").write_text("def main():\n    return 0\n", "utf-8")
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "runs").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001\n", "utf-8")
    return root


def result(body: str, root: Path | None, today: str = AFTER) -> tuple[list[str], list[str]]:
    return brief_study.study_result(body, root, today=today)


def cli(tmp_path: Path, body: str, root: Path):
    (tmp_path / "brief.md").write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "check_brief.py"),
            str(tmp_path / "brief.md"),
            "--root",
            str(root),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_ac4_a_studied_brief_passes_before_and_after_the_roll_in(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    assert result(STUDIED, root, BEFORE) == ([], [])
    assert result(STUDIED, root, AFTER) == ([], [])


def test_ac4_a_brief_without_its_study_warns_during_the_roll_in_and_fails_after(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    failed, warned = result(SHAPE, root, BEFORE)
    assert failed == [] and len(warned) == 4 and all(w.startswith("study: ") for w in warned)
    failed, warned = result(SHAPE, root, AFTER)
    assert len(failed) == 4 and warned == []
    joined = " ".join(failed)
    assert all(name in joined for name in ("Impact:", "Wiring:", "Prior:", "Class:"))


def test_ac4_the_roll_in_is_one_dated_constant(monkeypatch):
    """REQ-037 AC4"""
    assert brief_study.enforced("2026-12-01") and not brief_study.enforced("2026-11-30")
    monkeypatch.setattr(brief_study, "STUDY_FAILS_FROM", None)
    assert not brief_study.enforced("2099-01-01")


def test_ac4_the_cli_prints_a_study_warning_and_still_passes_in_the_roll_in(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    if SHIPPED is not None and brief_study.enforced(None):
        pytest.skip("the shipped switch day has passed; the failure is tested in-process")
    out = cli(tmp_path, SHAPE, root)
    lines = out.stdout.splitlines()
    assert out.returncode == 0 and lines[-1] == "ok brief"
    assert any(x.startswith("warning: study: ") for x in lines)
    assert cli(tmp_path, STUDIED, root).stdout.strip() == "ok brief"


@pytest.mark.parametrize("name", brief_study.IMPACT_NAMES)
def test_ac4_each_impact_name_missing_is_named(tmp_path, name):
    """REQ-037 AC4"""
    body = STUDIED.replace(
        next(x for x in IMPACT.splitlines() if x.startswith(name + ":")) + "\n", ""
    )
    failed, _ = result(body, tree(tmp_path))
    assert any(f"{name}:" in p for p in failed), failed


def test_ac4_impact_names_out_of_order_are_named(tmp_path):
    """REQ-037 AC4"""
    body = STUDIED.replace("Speed: 2 minutes", "Quality: x\nSpeed: 2 minutes", 1).replace(
        "Quality: a missed decision fails on the brief\n", ""
    )
    failed, _ = result(body, tree(tmp_path))
    assert any("Speed:" in p for p in failed) and any("Quality:" in p for p in failed)


def test_ac4_an_impact_line_with_no_text_fails(tmp_path):
    """REQ-037 AC4"""
    failed, _ = result(STUDIED.replace("Cost: none: file-only check", "Cost:"), tree(tmp_path))
    assert any("Cost:" in p for p in failed)


@pytest.mark.parametrize(
    "wiring",
    [
        "Wiring: scripts/agk/missing.py:main called by x\n",
        "Wiring: scripts/agk/tool.py:gone called by x\n",
        "Wiring: scripts/agk/tool.py main\n",
    ],
)
def test_ac4_wiring_with_a_missing_file_or_function_fails(tmp_path, wiring):
    """REQ-037 AC4"""
    failed, _ = result(STUDIED.replace(WIRING, wiring), tree(tmp_path))
    assert any(p.startswith("study: the Wiring line") for p in failed), failed


def test_ac4_wiring_finds_a_top_level_name(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    (root / "scripts" / "agk" / "tool.py").write_text("NAME = 'x'\n", "utf-8")
    body = STUDIED.replace("tool.py:main", "tool.py:NAME")
    assert result(body, root) == ([], [])


def test_ac4_class_seen_before_needs_the_closing_item(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    seen = STUDIED.replace("seen 0 (searched docs/adr)", "seen 2 times (#1, #2)")
    failed, _ = result(seen, root)
    assert any("The class stays closed." in p for p in failed)
    closed = seen.replace(
        "2. two", "2. **The class stays closed.** A guard test fails the next one."
    )
    assert result(closed, root) == ([], [])


def test_ac4_a_prior_reference_that_does_not_exist_fails(tmp_path):
    """REQ-037 AC4"""
    failed, _ = result(
        STUDIED.replace(PRIOR, "Prior: ADR-0999 (the earlier one)\n"), tree(tmp_path)
    )
    assert any("ADR-0999" in p for p in failed)


def test_ac4_prior_leaving_out_an_accepted_adr_that_names_a_touched_path_warns(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    (root / "docs" / "adr" / "0007-tool.md").write_text(
        "# ADR-0007: tool\n\n- Status: Accepted\n\nIt changes `scripts/agk/tool.py`.\n", "utf-8"
    )
    failed, warned = result(STUDIED, root)
    assert failed == [] and any("ADR-0007" in w for w in warned)
    named = STUDIED.replace(PRIOR, "Prior: ADR-0007 (Accepted)\n")
    assert result(named, root) == ([], [])


def test_ac4_a_red_branch_brief_is_held_only_to_class_and_prior(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    zero = SHAPE.replace("Priority: 1", "Priority: 0") + PRIOR + CLASS
    assert result(zero, root) == ([], [])
    failed, _ = result(SHAPE.replace("Priority: 1", "Priority: 0"), root)
    assert len(failed) == 2


def test_ac4_the_routers_own_red_brief_is_not_held(tmp_path):
    """REQ-037 AC4"""
    body = SHAPE.replace("Advances: new", "Advances: none").replace("Priority: 1", "Priority: 0")
    assert result(body, tree(tmp_path)) == ([], [])


def test_ac4_without_root_the_study_is_not_read(tmp_path):
    """REQ-037 AC4"""
    assert result(SHAPE, None) == ([], [])


def test_ac4_a_text_fix_may_say_none_everywhere(tmp_path):
    """REQ-037 AC4"""
    body = (
        SHAPE
        + (
            "Impact:\nSpeed: none: text\nQuality: none: text\nGitHub: none: text\n"
            "Cost: none: text\nTests: none: text\nWiring: none: a text fix\n"
        )
        + PRIOR
        + CLASS
    )
    assert result(body, tree(tmp_path)) == ([], [])


def test_ac4_an_event_carries_the_study_warnings_in_the_roll_in(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    if SHIPPED is not None and brief_study.enforced(None):
        pytest.skip("the shipped switch day has passed; the failure is tested in-process")
    payload = {
        "action": "opened",
        "issue": {"number": 9, "body": SHAPE, "labels": [{"name": "agk-brief"}]},
    }
    (tmp_path / "event.json").write_text(json.dumps(payload), encoding="utf-8")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "check_brief.py"),
            "--event",
            str(tmp_path / "event.json"),
            "--root",
            str(root),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    found = json.loads(out.stdout)
    assert found["action"] == "pass" and len(found["warnings"]) == 4
