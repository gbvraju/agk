"""SPEC-0041 build (j): `pr-summary`, `ai_disclosure` and the trailer warning (brief #1505).

Advances REQ-048 (AC6). Rule 21: `personal.py pr-summary` prints, and never posts, a plain
description of the change from the gate record: the tests, the proof where the level ran it,
whether a review was done, and the disclosure line; no REQ, SPEC or ADR id unless `team_refs`.
Rule 22: `ai_disclosure` is `commit-trailer`, `pr-note` or `both` (the default); `none` or any
other value is refused naming the setting; the gate warns of a branch commit without the trailer;
no personal script amends, rebases, filters or annotates a commit; `status` prints the disclosure.
Invented repositories and sidecars in `tmp_path`, a stub gitleaks, no network.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_personal_gate import (  # noqa: E402
    SCRIPTS,
    clone_of,
    commit,
    gate,
    git,
    prepared,
    scanner,
    sidecar_of,
)

LINE = "This change was made with the help of an AI coding assistant."
SETTING = "setting: personal.ai_disclosure"
TRAILER = "\n\nCo-Authored-By: assistant-example <assistant@example.com>"


def personal(*args: str) -> subprocess.CompletedProcess:
    skip = ("AGK_HOME", "AGK_BASE", "GITHUB_BASE_REF", "CI")
    env = {k: v for k, v in os.environ.items() if k not in skip}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "personal.py"), *args],
        capture_output=True, text=True, env=env,
    )  # fmt: skip


def summary(clone: Path, side: Path) -> subprocess.CompletedProcess:
    return personal("pr-summary", "--clone", str(clone), "--sidecar", str(side))


def set_disclosure(side: Path, value: str) -> None:
    toml = side / "agk.toml"
    text = toml.read_text(encoding="utf-8").replace('ai_disclosure = "both"\n', "")
    toml.write_text(text + f'ai_disclosure = "{value}"\n', encoding="utf-8")
    commit(side, "disclosure")


def gated_summary(tmp_path: Path, level: str, value: str | None = None):
    clone, side = prepared(tmp_path, level)
    if value is not None:
        set_disclosure(side, value)
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 0, done.stdout + done.stderr
    return clone, side, summary(clone, side)


# --- rule 21: the summary of the gate record ----------------------------------------------------


def test_req_048_pr_summary_prints_the_tests_and_the_disclosure_line(tmp_path):
    """REQ-048 AC6: rule 21 (the tests from the record and, by default, the disclosure line)."""
    clone, side, done = gated_summary(tmp_path, "light")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Secret scan: passed" in done.stdout
    assert "No test that passed before fails now: passed" in done.stdout
    assert "Tests written first: not run at this level" in done.stdout
    assert "Review: not done at this level" in done.stdout
    assert done.stdout.rstrip().splitlines()[-1] == LINE


def test_req_048_pr_summary_names_the_proof_and_the_review_where_the_level_ran_them(tmp_path):
    """REQ-048 AC6: rule 21 (the proof result and a review done, at the `review` level)."""
    _, _, done = gated_summary(tmp_path, "review")
    assert "Tests written first: passed (red before the change, green after)" in done.stdout
    assert "Review: done (passed)" in done.stdout


def test_req_048_pr_summary_posts_nothing_and_writes_nothing(tmp_path):
    """REQ-048 AC6: rules 4 and 21 (printed only: the sidecar and the clone are unchanged)."""
    clone, side = prepared(tmp_path, "light")
    gate(clone, side, scanner(tmp_path), "--approve")
    before = (git(side, "status", "--porcelain"), git(side, "rev-parse", "HEAD"))
    done = summary(clone, side)
    assert done.returncode == 0
    assert "nothing is posted" in done.stdout
    assert (git(side, "status", "--porcelain"), git(side, "rev-parse", "HEAD")) == before
    assert git(clone, "status", "--porcelain") == ""


def test_req_048_pr_summary_without_a_gate_record_says_so(tmp_path):
    """REQ-048 AC6: rule 21 (no record: said, and no result is invented)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "light")
    done = summary(clone, side)
    assert done.returncode == 1
    assert "no gate record for the head" in done.stdout
    for word in ("passed", "failed"):
        assert word not in done.stdout


def record_with_an_id(tmp_path: Path, extra: str = "") -> tuple[Path, Path]:
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "light", extra)
    gate(clone, side, scanner(tmp_path), "--approve")
    path = side / "records" / "gates" / f"{git(clone, 'rev-parse', 'HEAD')}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["steps"].append({"name": "spec SPEC-0001 for REQ-001 by ADR-0001", "outcome": "ok"})
    path.write_text(json.dumps(record), encoding="utf-8")
    return clone, side


def test_req_048_team_refs_off_leaves_an_id_of_the_record_out(tmp_path):
    """REQ-048 AC6: rule 21 (no REQ, SPEC or ADR id with `team_refs` off)."""
    done = summary(*record_with_an_id(tmp_path))
    assert done.returncode == 0, done.stdout
    for word in ("SPEC-0001", "REQ-001", "ADR-0001"):
        assert word not in done.stdout


def test_req_048_team_refs_on_keeps_the_ids(tmp_path):
    """REQ-048 AC6: rule 21 (`team_refs = true` names the ids)."""
    done = summary(*record_with_an_id(tmp_path, "team_refs = true\n"))
    assert "SPEC-0001" in done.stdout


# --- rule 22: the disclosure values -------------------------------------------------------------


@pytest.mark.parametrize("value", ["commit-trailer", "pr-note", "both"])
def test_req_048_each_disclosure_value_is_printed_and_the_line_follows_it(tmp_path, value):
    """REQ-048 AC6: rule 22 (in force in `pr-summary`; the line only with `pr-note` or `both`)."""
    _, _, done = gated_summary(tmp_path, "light", value)
    assert f"Disclosure in force: {value} ({SETTING})" in done.stdout
    ends = done.stdout.rstrip().splitlines()[-1] == LINE
    assert ends == (value != "commit-trailer")


@pytest.mark.parametrize("value", ["commit-trailer", "pr-note", "both"])
def test_req_048_status_prints_the_disclosure_in_force(tmp_path, value):
    """REQ-048 AC6: rule 22 (`status` prints the disclosure in force)."""
    side = sidecar_of(tmp_path, "light")
    set_disclosure(side, value)
    done = personal("status", "--sidecar", str(side))
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"disclosure {value}" in done.stdout


@pytest.mark.parametrize("value", ["none", "hidden"])
@pytest.mark.parametrize("command", ["status", "pr-summary"])
def test_req_048_none_and_an_unknown_value_are_refused_naming_the_setting(tmp_path, value, command):
    """REQ-048 AC6: rule 22 (there is no `none`; the refusal names the setting, never the value)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "light")
    set_disclosure(side, value)
    done = personal(command, "--clone", str(clone), "--sidecar", str(side))
    assert done.returncode == 1
    assert "personal.ai_disclosure" in done.stdout
    assert value not in done.stdout


# --- rule 22: the trailer warning of the gate ---------------------------------------------------


@pytest.mark.parametrize("value", ["commit-trailer", "both"])
def test_req_048_a_commit_without_the_trailer_is_warned(tmp_path, value):
    """REQ-048 AC6: rule 22 (the gate warns, naming the setting, and amends nothing)."""
    clone = clone_of(tmp_path)
    head = git(clone, "rev-parse", "HEAD")
    side = sidecar_of(tmp_path, "light")
    set_disclosure(side, value)
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert f"gate: warning: commit {head[:12]} has no Co-Authored-By trailer" in done.stdout
    assert SETTING in done.stdout
    assert git(clone, "rev-parse", "HEAD") == head


def test_req_048_a_commit_with_the_trailer_is_not_warned(tmp_path):
    """REQ-048 AC6: rule 22 (the trailer present: no warning)."""
    clone = clone_of(tmp_path, body=TRAILER)
    done = gate(clone, sidecar_of(tmp_path, "light"), scanner(tmp_path), "--approve")
    assert "Co-Authored-By trailer" not in done.stdout


def test_req_048_pr_note_alone_gives_no_trailer_warning(tmp_path):
    """REQ-048 AC6: rule 22 (the warning is for `commit-trailer` and `both` only)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "light")
    set_disclosure(side, "pr-note")
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert "Co-Authored-By trailer" not in done.stdout


# --- rule 22: no personal script strips attribution ---------------------------------------------


def test_req_048_no_personal_script_amends_rebases_filters_or_annotates():
    """REQ-048 AC6: rule 22 (no `--amend`, `rebase`, `filter-branch` or `notes` in an argument
    list of any `personal*.py`)."""
    scripts = sorted(SCRIPTS.glob("personal*.py"))
    assert len(scripts) >= 2
    for path in scripts:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        words = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)}
        for word in ("--amend", "amend", "rebase", "filter-branch", "notes"):
            assert word not in words, f"{path.name}: {word}"
