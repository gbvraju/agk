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

SHAPE = (
    'Sentence: "A team can run a thing."\nAnswers:\n1. one\n2. two\nSize: M\n'
    "Advances: REQ-001\nTouches: scripts/agk/tool.py, docs/x.md\nPriority: 1\n"
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
FIX = (  # brief #2095: a Priority 0 brief that is not the router's names its root cause
    "Fix type: root\nRoot cause: a-red-check: a test broke; before: none: searched briefs;"
    " removed by: the fix\n"
)
# Brief #2065 (ADR-0857): a project brief carries the Existing line too, before its Answers.
EXISTING = "Existing:\n- `scripts/agk/tool.py:1` (`main`): the tool; not enough: partial.\n\n"
SHAPE = SHAPE.replace("Answers:\n", EXISTING + "Answers:\n", 1)
STUDIED = SHAPE + IMPACT + WIRING + PRIOR + CLASS
BEFORE = "2026-11-24"
AFTER = "2099-01-01"


@pytest.fixture(autouse=True)
def switch_day(monkeypatch):
    """The roll-in's switch day as a root's `[flow] brief_study_fails_from` would set it (brief
    #1815 answer 1); a child process reads the tree's own agk.toml, which sets none."""
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: "2026-12-01")


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


def test_ac4_the_roll_in_is_one_setting(tmp_path):
    """REQ-037 AC4 (brief #1815 answer 1: the day is `[flow] brief_study_fails_from`)."""
    root = tree(tmp_path)
    (root / "agk.toml").write_text('[flow]\nbrief_study_fails_from = "2026-12-01"\n', "utf-8")
    import config

    assert config.brief_study_fails_from(root).isoformat() == "2026-12-01"
    (root / "agk.toml").write_text("[flow]\n", "utf-8")
    assert config.brief_study_fails_from(root) is None


def test_ac4_the_cli_prints_a_study_warning_and_still_passes_in_the_roll_in(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
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
    zero = SHAPE.replace("Priority: 1", "Priority: 0") + PRIOR + CLASS + FIX  # brief #2095
    assert result(zero, root) == ([], ["study: root causes not read (no plan cache)"])
    failed, _ = result(SHAPE.replace("Priority: 1", "Priority: 0") + FIX, root)
    assert len(failed) == 2


def test_ac4_the_routers_pair_is_held_to_class_and_prior(tmp_path):
    """REQ-037 AC4 (brief #1815 answer 5: held as any `Priority: 0` brief)"""
    body = SHAPE.replace("Advances: REQ-001", "Advances: none").replace(
        "Priority: 1", "Priority: 0"
    )
    root = tree(tmp_path)
    failed, _ = result(body, root)
    assert len(failed) == 2 and "Prior:" in failed[0] and "Class:" in failed[1], failed
    assert result(body + PRIOR + CLASS, root) == ([], [])


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


def accepted(root: Path, number: int, context: str = "", decision: str = "") -> None:
    text = f"# ADR-{number:04d}: x\n\n- Status: Accepted\n\n## Context\n\n{context}\n"
    text += f"\n## Decision\n\n{decision}\n\n## Consequences\n\nNone.\n"
    (root / "docs" / "adr" / f"{number:04d}-x.md").write_text(text, "utf-8")


def prior_lines(warned: list[str]) -> list[str]:
    return [w for w in warned if w.startswith(("study: Prior leaves out", "study: Prior: "))]


def test_ac4_at_most_ten_adrs_are_warned_and_one_line_counts_the_rest(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 2)"""
    root = tree(tmp_path)
    for number in range(100, 115):
        accepted(root, number, decision="It decides `scripts/agk/tool.py`.")
    _, warned = result(STUDIED, root)
    left = [w for w in warned if w.startswith("study: Prior leaves out ADR-")]
    assert len(left) == brief_study.PRIOR_WARNINGS == 10
    assert left[0].startswith("study: Prior leaves out ADR-0114 ")  # the newer first
    assert (
        "study: Prior: 5 more candidates not warned; brief_study.py <file> --root . lists them"
        in warned
    )


def test_ac4_a_cited_strong_adr_is_not_warned_and_leaves_room_under_the_cap(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 2)"""
    root = tree(tmp_path)
    for number in range(100, 111):
        accepted(root, number, decision="It decides `scripts/agk/tool.py`.")
    cited = STUDIED.replace(PRIOR, "Prior: ADR-0110 (Accepted, the same rule)\n")
    _, warned = result(cited, root)
    left = prior_lines(warned)
    assert len(left) == 10 and not any("ADR-0110" in w for w in left), left


def test_ac4_open_brief_warnings_are_all_kept(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 3)"""
    root = tree(tmp_path)
    briefs = [{"number": n, "body": "Touches: scripts/agk/tool.py"} for n in range(500, 512)]
    _, warned = brief_study.study_result(STUDIED, root, today=AFTER, briefs=briefs)
    assert len([w for w in warned if "Prior leaves out brief #" in w]) == 12


def test_ac4_the_class_stays_closed_weak_mentions_never_warn(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 5): a widening of the search fails this guard."""
    root = tree(tmp_path)
    for number in range(200, 240):
        accepted(root, number, context="It mentions `tool.py` and `scripts/agk/tool.py`.")
    _, warned = result(STUDIED, root)
    assert len(prior_lines(warned)) <= 1, warned
    assert not any(w.startswith("study: Prior leaves out ADR-") for w in warned)


def test_ac4_an_adr_whose_decision_names_the_wired_function_is_warned(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 5)"""
    root = tree(tmp_path)
    accepted(root, 300, decision="1. `tool.main` prints the line.")
    _, warned = result(STUDIED, root)
    assert any(w.startswith("study: Prior leaves out ADR-0300 (Accepted)") for w in warned)


def test_ac4_a_prior_that_cites_a_weak_candidate_is_allowed(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 7)"""
    root = tree(tmp_path)
    accepted(root, 301, context="`scripts/agk/tool.py` in passing.")
    body = STUDIED.replace(PRIOR, "Prior: ADR-0301 (Accepted, read)\n")
    assert result(body, root) == ([], [])
    assert result(STUDIED, root) == ([], [])


def test_ac4_the_cap_is_the_flow_setting_brief_prior_warnings(tmp_path):
    """REQ-037 AC4 (brief #1819, Maintainer answer Q-F11-1: a whole number, default 10)"""
    import config

    root = tree(tmp_path)
    for number in range(100, 106):
        accepted(root, number, decision="It decides `scripts/agk/tool.py`.")
    assert (
        config.brief_prior_warnings(root) == 10
        and "brief_prior_warnings" in config.TABLE_KEYS["flow"]
    )
    (root / "agk.toml").write_text("[flow]\nbrief_prior_warnings = 3\n", "utf-8")
    assert config.brief_prior_warnings(root) == 3
    _, warned = result(STUDIED, root)
    assert len([w for w in warned if w.startswith("study: Prior leaves out ADR-")]) == 3
    assert any(w.startswith("study: Prior: 3 more candidates not warned") for w in warned)
    (root / "agk.toml").write_text("[flow]\nbrief_prior_warnings = 0\n", "utf-8")
    _, warned = result(STUDIED, root)
    assert prior_lines(warned) == [
        "study: Prior: 6 more candidates not warned; brief_study.py <file> --root . lists them"
    ]


@pytest.mark.parametrize("value", ["-1", '"10"', "2.5", "true", "[10]"])
def test_ac4_a_brief_prior_warnings_outside_its_form_is_refused_naming_the_setting(tmp_path, value):
    """REQ-037 AC4 (brief #1819, Maintainer answer Q-F11-1)"""
    from common import CheckError

    import config

    root = tree(tmp_path)
    (root / "agk.toml").write_text(f"[flow]\nbrief_prior_warnings = {value}\n", "utf-8")
    with pytest.raises(CheckError) as caught:
        result(STUDIED, root)
    assert "flow.brief_prior_warnings" in str(caught.value) and value not in str(caught.value)
    with pytest.raises(config.BriefPriorSettingError):
        config.brief_prior_warnings(root)
