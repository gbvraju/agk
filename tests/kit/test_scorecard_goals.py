"""The scorecard counts the goals of accepted products still not met (SPEC-0051 rule 9, brief #903,
build (d); REQ-058 AC5).

`goals_not_met` and the line `acceptance: ...` are read from the records of the default branch with
`check_acceptance.py`'s own reader. Fixtures in `tmp_path`, invented data (`example.com`), no
network. The tests were written first (answer 5).
"""

from __future__ import annotations

import socket

import pytest
import scorecard
from test_check_acceptance import ANSWER, DEFINED, Q1, Q2, SLUG, digest_of, discovery, record
from test_scorecard import TODAY, field, project, saved, writer, writes

import config

OTHER = "example-report"
NO_RECORD = ("0", "acceptance: no record")
MET = [f'- G-1: "{Q1}" -> {DEFINED}', f'- G-2: "{Q2}" -> {DEFINED}']
ONE_UNMET = [f'- G-1: "{Q1}" -> {DEFINED}', f'- G-2: "{Q2}" -> not met']
TWO_UNMET = [f'- G-1: "{Q1}" -> not met', f'- G-2: "{Q2}" -> not met']
BASE = {"tests/test_example.py": "def test_signup():\n    assert True\n"}


def record_of(goals: list[str], status: str = "accepted", slug: str = SLUG) -> tuple[str, str]:
    """The path and text of a record whose digest is the current `success` answer's."""
    title = "Example signup" if slug == SLUG else "Example report"
    text = record(digest_of(ANSWER), goals, status, title).replace(SLUG, slug)
    return f"docs/acceptance/{slug}.md", text


def delivered(repo, *records: tuple[str, str]) -> None:
    """Two discovery documents and the given records, committed on the default branch."""
    discovery(repo.root, ANSWER)
    discovery(repo.root, ANSWER, "Example report")
    repo.commit({**BASE, **dict(records)})


def test_ac5_no_record_reads_no_record_and_zero(repo, tmp_path):
    """REQ-058 AC5: rule 9, no record is value 0, the line `no record`, and the default line 0."""
    project(repo)
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, {})))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "| goals_not_met | 0 | 0 |" in proc.stdout
    assert "acceptance: no record" in proc.stdout
    assert scorecard.acceptance(repo.root, "main") == NO_RECORD


def test_ac5_a_mix_of_accepted_and_proposed_counts_only_the_accepted(repo):
    """REQ-058 AC5: rule 9, a proposed record counts in neither number."""
    delivered(repo, record_of(ONE_UNMET), record_of(TWO_UNMET, "proposed", OTHER))
    assert scorecard.acceptance(repo.root, "main") == (
        "1",
        "acceptance: 1 of 2 goals met in 1 records",
    )


def test_ac5_the_counts_add_up_over_accepted_records(repo):
    """REQ-058 AC5: rule 9, met and total are summed over every accepted record."""
    delivered(repo, record_of(MET), record_of(ONE_UNMET, slug=OTHER))
    assert scorecard.acceptance(repo.root, "main") == (
        "1",
        "acceptance: 3 of 4 goals met in 2 records",
    )


def test_ac5_a_stale_record_counts_in_neither_number(repo):
    """REQ-058 AC5: rule 9, a digest that is not the current answer's counts in neither number."""
    rel, text = record_of(TWO_UNMET)
    delivered(repo, (rel, text.replace(digest_of(ANSWER), digest_of("an earlier answer"))))
    assert scorecard.acceptance(repo.root, "main") == (
        "0",
        "acceptance: 0 of 0 goals met in 0 records",
    )


def test_ac5_two_unmet_goals_read_two_and_are_a_level_finding(repo, tmp_path):
    """REQ-058 AC5: rule 9, any unmet goal is above the default line 0, and the section shows it."""
    project(repo)
    delivered(repo, record_of(TWO_UNMET))
    api = str(saved(tmp_path, {}))
    table = repo.run("scorecard.py", "--today", TODAY, "--api-dir", api)
    assert "| goals_not_met | 2 | 0 |" in table.stdout, table.stdout + table.stderr
    proc = repo.run("scorecard.py", "findings", "--today", TODAY, "--api-dir", api)
    assert "finding: goals_not_met level value 2 line 0" in proc.stdout, proc.stdout + proc.stderr
    assert "acceptance: 0 of 2 goals met in 1 records" in proc.stdout


def test_ac5_an_unmet_goal_opens_the_one_reminder_issue(repo, tmp_path_factory):
    """REQ-058 AC5: rule 9, one `scorecard: goals_not_met` issue, never a brief per goal."""
    delivered(repo, record_of(TWO_UNMET))
    proc, calls = writer(repo, tmp_path_factory, "issues")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    posted = writes(calls)
    made = [c for c in posted if c[:4] == ["api", "--method", "POST", "repos/owner/name/issues"]]
    assert len(made) == 1, posted
    assert field(made[0], "title") == "scorecard: goals_not_met"
    assert "labels[]=agk-brief" not in made[0]


def test_ac5_the_line_is_read_from_the_files_with_no_network(repo, monkeypatch):
    """REQ-058 AC5: rule 9, the read opens no socket and uses no saved or live GitHub response."""
    delivered(repo, record_of(ONE_UNMET))

    def refused(*_args, **_kwargs):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refused)
    assert scorecard.acceptance(repo.root, "main")[0] == "1"


def test_ac5_only_the_default_branch_counts(repo):
    """REQ-058 AC5: rule 9, a record on another branch or uncommitted is not counted."""
    delivered(repo)
    repo.branch()
    repo.commit(dict([record_of(TWO_UNMET)]))
    rel, text = record_of(ONE_UNMET, slug=OTHER)
    repo.write(rel, text)
    assert scorecard.acceptance(repo.root, "main") == NO_RECORD


def test_ac5_a_checkout_with_no_default_branch_reads_its_own_files(tmp_path):
    """REQ-058 AC5: the local and personal contexts, no ref reads the records of the checkout."""
    discovery(tmp_path, ANSWER)
    for rel, text in {**BASE, **dict([record_of(ONE_UNMET)])}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    assert scorecard.acceptance(tmp_path, None)[0] == "1"


def test_ac5_a_default_branch_that_cannot_be_read_is_unknown_never_zero(repo):
    """REQ-058 AC5: SPEC-0047 rule 2, inputs that cannot be read are `unknown`, never 0."""
    delivered(repo, record_of(ONE_UNMET))
    assert scorecard.acceptance(repo.root, "no-such-ref") == ("unknown", "acceptance: unknown")


@pytest.mark.parametrize(("toml", "line"), [("", 0), ("[scorecard]\ngoals_not_met = 3\n", 3)])
def test_ac5_the_line_is_a_setting_with_default_zero(tmp_path, toml, line):
    """REQ-058 AC5: SPEC-0047 rule 3, `goals_not_met` is a setting of the table, default 0."""
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    assert config.scorecard_settings(tmp_path)["lines"]["goals_not_met"] == line
