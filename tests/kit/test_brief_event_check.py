"""check_brief.py --event: what the brief check does for one saved issue event (brief #770).

SPEC-0030 rule 4 and amendment 140; REQ-037; ADR-0357. A saved payload of an `issues` event goes in
and one JSON line comes out: `ignore`, `fail` (the label and the comment naming each failing rule,
never a value) or `pass` (the label and the comment go, and the wave names the milestone). Reads the
files only: no network, invented data."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "check_brief.py"
WORDS = "A person at example.com can open a widget."
GOOD = (
    f'Sentence: "{WORDS}"\n'
    "Answers:\n1. one\n2. two\n"
    "Size: S\nAdvances: new\nTouches: docs/**\nPriority: 1\n"
)
WAVED = GOOD + "Wave: 2\n"
LONG = GOOD.replace(WORDS, "x" * 301)
PLANNED = "[flow]\nplan_issue = 9\n"


def payload(body: str, action: str = "opened", labels=("agk-brief",), **extra) -> dict:
    issue = {
        "number": 12,
        "body": body,
        "labels": [{"name": n} for n in labels],
        "user": {"login": "filer"},
        **extra,
    }
    return {"action": action, "issue": issue}


def event(tmp_path: Path, data: dict, toml: str = "", *extra: str):
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001\n", encoding="utf-8")
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    saved = tmp_path / "event.json"
    saved.write_text(json.dumps(data), encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--event", str(saved), "--root", str(root), *extra],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("action", ["opened", "edited", "labeled"])
def test_a_malformed_brief_gets_the_label_and_a_comment_naming_the_rule(tmp_path, action):
    out = event(tmp_path, payload(LONG, action))
    assert out["action"] == "fail"
    assert out["issue"] == 12
    assert out["label"] == "agk-brief-invalid"
    assert out["problems"] == ["rule 4: the Sentence is not 1 to 300 characters"]
    assert "rule 4: the Sentence is not 1 to 300 characters" in out["comment"]
    assert out["comment"].startswith("<!-- agk-brief-check -->")
    assert "xxx" not in out["comment"]


def test_a_fixed_brief_loses_the_label_and_the_comment(tmp_path):
    out = event(tmp_path, payload(GOOD, "edited", labels=("agk-brief", "agk-brief-invalid")))
    assert out == {"action": "pass", "issue": 12, "label": "agk-brief-invalid", "wave": None}


@pytest.mark.parametrize(
    "data",
    [
        payload("no shape at all", labels=("bug",)),
        payload("no shape at all", action="closed"),
        payload("no shape at all", pull_request={"url": "https://example.com/pull/1"}),
    ],
)
def test_an_issue_that_is_not_a_brief_event_is_ignored(tmp_path, data):
    assert event(tmp_path, data) == {"action": "ignore"}


def test_a_missing_wave_is_refused_when_a_plan_issue_is_set(tmp_path):
    out = event(tmp_path, payload(GOOD), PLANNED)
    assert out["action"] == "fail"
    assert out["problems"] == ["rule 4: exactly one line Wave: n (setting: plan_issue)"]


def test_a_wave_the_plan_does_not_have_is_refused(tmp_path):
    out = event(tmp_path, payload(WAVED), PLANNED, "--waves", "1,3")
    assert out["problems"] == ["rule 4: the Wave line names a wave the plan does not have"]


def test_a_named_wave_passes_and_names_the_milestone(tmp_path):
    out = event(tmp_path, payload(WAVED), PLANNED, "--waves", "1,2")
    assert out == {"action": "pass", "issue": 12, "label": "agk-brief-invalid", "wave": 2}


def test_with_no_plan_issue_the_wave_line_is_optional(tmp_path):
    assert event(tmp_path, payload(GOOD))["action"] == "pass"
    assert event(tmp_path, payload(WAVED))["wave"] == 2


def test_a_saved_brief_file_is_checked_for_the_wave_too(tmp_path):
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text("### REQ-001\n", encoding="utf-8")
    (root / "agk.toml").write_text(PLANNED, encoding="utf-8")
    brief = tmp_path / "brief.md"
    brief.write_text(GOOD, encoding="utf-8")
    run = [sys.executable, str(SCRIPT), str(brief), "--root", str(root)]
    proc = subprocess.run(run, capture_output=True, text=True)  # nosec B603 - fixed list, no shell
    assert proc.returncode == 1
    assert "rule 4: exactly one line Wave: n (setting: plan_issue)" in proc.stdout
    brief.write_text(WAVED, encoding="utf-8")
    proc = subprocess.run(run, capture_output=True, text=True)  # nosec B603 - fixed list, no shell
    assert proc.returncode == 0, proc.stdout
