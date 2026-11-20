"""Tests of SPEC-0062 build (b): in solo mode the steward does the setup for the person and records
each AGK choice as one `Setup:` entry (rules 8, 9 and 11; brief #1599, ADR-0679; REQ-069 AC3 to AC5).

A recorded `gh` double, a stubbed `gh api user` (an invented login) and a stubbed detector stand in
for the runtime, the model and GitHub; no network, invented data only (example.com).
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import adopt  # noqa: E402
import init  # noqa: E402
import steward  # noqa: E402
from test_steward_memory import GitHub  # noqa: E402

LOGIN = "member-example-1"
TODAY = "2026-11-20"
REVIEWERS = "config/reviewers.yaml"
ADR = "docs/adr/0001-adopt-agk.md"
PYTHON = {"rows": [{"name": "python-pyproject", "folder": ".", "file": "pyproject.toml"}]}


class Run:
    """`gh api user` answered with an invented login; every call is kept."""

    def __init__(self, out: str = f"{LOGIN}\n", code: int = 0) -> None:
        self.out, self.code, self.calls = out, code, []

    def __call__(self, args, **_):
        self.calls.append(list(args))
        return subprocess.CompletedProcess(args, self.code, stdout=self.out, stderr="")


def items_of(target: Path, setup: dict | None = None) -> dict[str, str]:
    items, _, _ = init.build_items(target, TODAY, setup)
    return {rel: data.decode("utf-8") for rel, data in items}


def test_req069_ac4_a_fixture_start_settles_each_agk_matter_with_one_setup_entry(tmp_path):
    """REQ-069 AC4: rule 9, every AGK matter is one `Setup:` entry; only plain questions."""
    plan = steward.setup_plan(tmp_path, adopted=False, stack=None)
    matters = [entry.split(":", 2)[1].strip() for entry in plan["entries"]]
    for matter in ("models", "builders", "max_builders", "pr_mode", "reviewers"):
        assert matters.count(matter) == 1, matter
    for entry in plan["entries"]:
        assert entry.startswith("Setup: ") and " because " in entry
        assert steward.SETUP.fullmatch(entry.removeprefix("Setup: "))
    assert plan["ask"] == [steward.ALONE_QUESTION, steward.REST_QUESTION]
    for kit_word in ("review_mode", "agk.toml", "max_builders", "owner_rest_hours", "ADR"):
        assert not any(kit_word in q for q in plan["ask"])


def test_req069_ac4_record_takes_the_setup_kind_in_its_form(tmp_path, monkeypatch):
    """REQ-069 AC4: `record --kind Setup` takes `<matter>: <choice> because <reason>`."""
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    gh = GitHub()
    code, _ = steward.record(tmp_path, "Setup", "pr_mode: strict because the kit default", gh)
    assert code == 0
    body = gh.issues[1]["c"][-1]["body"]
    assert body.startswith("Setup: pr_mode: strict because") and body.endswith(steward.WHO)
    code, lines = steward.record(tmp_path, "Setup", "pr_mode strict", gh)
    assert code == 2 and "Setup entry" in lines[0]


def test_req069_ac5_the_reviewers_file_is_filled_from_the_signed_in_login(tmp_path, capsys):
    """REQ-069 AC5: rule 11, both placeholder lines get the login, which is never printed."""
    run = Run()
    login = init.signed_in_login(run)
    assert login == LOGIN and run.calls == [["gh", "api", "user", "--jq", ".login"]]
    text = items_of(tmp_path, {"login": login})
    assert init.PLACEHOLDER not in text[REVIEWERS]
    assert text[REVIEWERS].count(f"@{LOGIN}") == 2
    assert f"@{LOGIN}" in text[".github/CODEOWNERS"]
    assert LOGIN not in capsys.readouterr().out
    assert init.signed_in_login(Run(out="", code=1)) is None
    assert init.signed_in_login(Run(out="not a login\n")) is None


def test_req069_ac5_init_main_fills_the_login_and_never_prints_it(tmp_path, capsys, monkeypatch):
    """REQ-069 AC5: `init.py TARGET --login-from-gh` writes the file; nothing to edit by hand."""
    monkeypatch.setattr(init, "signed_in_login", lambda run=None: LOGIN)
    assert init.main([str(tmp_path), "--unreleased", "--login-from-gh"]) == 0
    out = capsys.readouterr().out
    assert LOGIN not in out and "placeholder" not in out
    assert (tmp_path / REVIEWERS).read_text(encoding="utf-8").count(f"@{LOGIN}") == 2


def test_req069_ac5_the_alone_answer_sets_solo_only_in_the_install_with_its_adr(tmp_path):
    """REQ-069 AC5: rule 2 as amendment 208 proposes; the install pull request holds the ADR."""
    assert steward.review_choice("Alone") == "solo"
    assert steward.review_choice("with a team") == "team"
    assert steward.review_choice("maybe") is None
    text = items_of(tmp_path, {"login": LOGIN, "solo": True})
    assert tomllib.loads(text["agk.toml"])["review_mode"] == "solo"
    assert "Review mode: `solo`" in text[ADR] and "amendment 208" in text[ADR]
    team = items_of(tmp_path, {"login": LOGIN})
    assert tomllib.loads(team["agk.toml"])["review_mode"] == "team"
    assert "Review mode" not in team[ADR]
    with pytest.raises(init.Refusal, match="setting: review_mode"):
        items_of(tmp_path, {"solo": True})
    code, lines = steward.setup_lines(tmp_path, False, None, "alone")
    assert code == 0 and lines[-1].endswith("--login-from-gh --solo")
    assert any(line.startswith("Setup: review_mode: solo because") for line in lines)


def test_req069_ac5_the_steward_refuses_review_mode_after_setup(tmp_path):
    """REQ-069 AC5: rule 2, the steward never changes `review_mode` once the kit is installed."""
    (tmp_path / "agk.toml").write_text(
        'mode = "init"\nreview_mode = "team"\n', encoding="utf-8"
    )
    code, lines = steward.setup_lines(tmp_path, False, None, "alone")
    assert code == 2 and "setting: review_mode" in lines[0]
    assert not any(line.startswith("run: ") for line in lines)


def test_req069_ac3_an_adopted_project_gets_a_test_command_from_the_detected_stack(tmp_path):
    """REQ-069 AC3: rule 8, the proposal comes from the stack the detector reads."""
    assert steward.proposed_tests(PYTHON) == "python3 -m pytest -q"
    node = {"rows": [{"name": "node", "folder": "web", "file": "web/package.json"}]}
    assert steward.proposed_tests(node) == "(cd web && npm test)"
    assert steward.proposed_tests({"rows": []}) == ""
    plan = steward.setup_plan(tmp_path, adopted=True, stack=PYTHON)
    tests = [e for e in plan["entries"] if e.startswith("Setup: project_tests:")]
    assert tests == [
        "Setup: project_tests: python3 -m pytest -q because the detected stack is python-pyproject"
    ]
    assert steward.test_outcome(0, "") == "passed"
    assert steward.test_outcome(5, "") == "no tests"
    assert steward.test_outcome(1, "") == "failed"
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    plan_rows, _, _ = adopt.build_plan(tmp_path, TODAY, {"project_tests": "python3 -m pytest -q"})
    toml = next(c for rel, _, c, _ in plan_rows if rel == "agk.toml").decode("utf-8")
    assert tomllib.loads(toml)["project_tests"] == "python3 -m pytest -q"


def test_req069_ac5_setup_touches_no_workflow_ruleset_check_or_secret(tmp_path):
    """REQ-069 AC5: rule 11's limits, only the reviewers file, its owners, the settings and the ADR."""
    before = items_of(tmp_path)
    after = items_of(tmp_path, {"login": LOGIN, "solo": True, "project_tests": "make test"})
    changed = sorted(rel for rel in before if before[rel] != after[rel])
    assert changed == [".github/CODEOWNERS", "agk.toml", REVIEWERS, ADR]
    old, new = tomllib.loads(before["agk.toml"]), tomllib.loads(after["agk.toml"])
    assert {k for k in old if old[k] != new[k]} <= {"review_mode", "project_tests"}
    assert old.get("required_checks") == new.get("required_checks")
