"""Tests of the lifecycle rules of scripts/agk/check_specs.py and the shared parsers of common.py.

Rule a (an implementation advances an Approved spec) and rule b (no Approved spec with an open
question), and `common.find_questions` and `common.next_free_ids`. Repositories are built in
`tmp_path`; nothing uses the network.
"""

from __future__ import annotations

import common
import pytest

SPEC = "docs/specs/0001-thing.md"
NOTES = "docs/runs/spec-0001-notes.md"
LOG = "docs/runs/decisions-log.md"
ADR = "docs/adr/0001-thing.md"
EMPTY_LOG = "# Decisions log\n\n| Date | Decision |\n| --- | --- |\n"


def spec(status: str = "Approved", reqs: str = "REQ-001", extra: str = "") -> str:
    return (
        f"# SPEC-0001: Thing\n\n- Status: {status}\n- Owner: maintainers\n"
        f"- Requirements: {reqs}\n\n## Rules\n\n1. A rule.\n{extra}"
    )


def adr(reqs: str = "REQ-001") -> str:
    return f"# ADR-0001: Thing\n\n- Status: Accepted\n- Requirements: {reqs}\n"


def body(advances: str = "REQ-001") -> str:
    return f"Advances: {advances}\n\nBuild-state row: 2026-10-18 x\n"


def lifecycle(repo, text: str | None):
    args = ["--base", "main"] + (["--body", "-"] if text is not None else [])
    return repo.run("check_specs.py", *args, stdin=text)


@pytest.fixture
def base(repo):
    repo.commit({"src/a.py": "1\n", LOG: EMPTY_LOG}, "base")
    repo.branch()
    return repo


# --- rule a: an implementation pull request advances an Approved spec ---------------------------


def test_ac1_a_docs_only_pull_request_with_advances_is_not_checked(base):
    """REQ-020 AC1: rule 23 (docs only)."""
    base.commit({"docs/notes.md": "x\n"})
    assert lifecycle(base, body()).stdout.endswith("ok specs\n")


def test_ac1_an_issue_form_change_is_docs_only_and_a_workflow_change_is_not(base):
    """REQ-020 AC1: rule 23 (`.github/ISSUE_TEMPLATE/` is exempt, the rest of `.github/` is not)."""
    base.commit({".github/ISSUE_TEMPLATE/proposal.md": "x\n"})
    assert lifecycle(base, body()).returncode == 0
    base.commit({".github/workflows/x.yml": "x\n"})
    proc = lifecycle(base, body())
    assert proc.returncode == 1 and "REQ-001: no Approved spec names it" in proc.stdout


def test_ac1_an_implementation_that_advances_a_requirement_of_an_approved_spec_passes(base):
    """REQ-020 AC1: rule 23."""
    base.commit({SPEC: spec("Approved"), "src/a.py": "2\n"})
    proc = lifecycle(base, body())
    assert (proc.returncode, proc.stdout.splitlines()[-1]) == (0, "ok specs")


def test_ac1_a_draft_spec_does_not_cover_the_requirement(base):
    """REQ-020 AC1: rule 23 (by a Draft spec only)."""
    base.commit({SPEC: spec("Draft"), "src/a.py": "2\n"})
    proc = lifecycle(base, body())
    assert proc.returncode == 1
    assert "FAIL specs: REQ-001: no Approved spec names it" in proc.stdout


def test_ac1_a_draft_spec_with_an_adr_does_not_exempt(base):
    """REQ-020 AC1: rule 23 (the exemption is for a requirement that no spec names)."""
    base.commit({SPEC: spec("Draft"), ADR: adr(), "src/a.py": "2\n"})
    assert lifecycle(base, body()).returncode == 1


def test_ac1_a_requirement_no_spec_names_and_an_adr_names_is_exempt(base):
    """REQ-020 AC1: rule 23 (it predates specs)."""
    base.commit({ADR: adr(), "src/a.py": "2\n"})
    assert lifecycle(base, body()).returncode == 0


def test_ac1_a_requirement_no_spec_and_no_adr_names_fails(base):
    """REQ-020 AC1: rule 23."""
    base.commit({"src/a.py": "2\n"})
    proc = lifecycle(base, body())
    assert proc.returncode == 1 and "REQ-001" in proc.stdout


def test_ac1_two_requirements_one_failing_names_only_the_failing_one(base):
    """REQ-020 AC1: rule 23."""
    base.commit({SPEC: spec("Approved", "REQ-001"), "src/a.py": "2\n"})
    proc = lifecycle(base, body("REQ-001, REQ-002"))
    assert proc.returncode == 1
    assert "REQ-002: no Approved spec names it" in proc.stdout and "REQ-001:" not in proc.stdout


def test_ac1_without_a_body_the_rule_prints_a_notice_and_is_skipped(base):
    """REQ-020 AC1: rule 23 (outside CI there is no body)."""
    base.commit({"src/a.py": "2\n"})
    for proc in (lifecycle(base, None), lifecycle(base, "\n")):
        assert proc.returncode == 0
        assert "no pull request body" in proc.stdout and proc.stdout.endswith("ok specs\n")


def test_ac1_the_body_is_read_from_a_file_too(base):
    """REQ-020 AC1: rule 23 (`--body FILE`)."""
    base.commit({"src/a.py": "2\n"})
    base.write("body.txt", body())
    proc = base.run("check_specs.py", "--base", "main", "--body", str(base.root / "body.txt"))
    assert proc.returncode == 1
    assert base.run("check_specs.py", "--base", "main", "--body", "missing.txt").returncode == 1


# --- rule b: a spec is not Approved with an open question ---------------------------------------


@pytest.fixture
def draft_spec(repo):
    repo.commit(
        {
            SPEC: spec("Draft", extra="\n## Open questions\n\n- Q-AB-1 which format?\n"),
            LOG: EMPTY_LOG,
        },
        "base",
    )
    repo.branch()
    return repo


def approve(repo, **files):
    text = spec("Approved", extra="\n## Open questions\n\n- Q-AB-1 which format?\n")
    repo.commit({SPEC: text, **files}, "approve")
    return repo.run("check_specs.py", "--base", "main")


def test_ac1_approving_a_spec_with_an_open_question_fails_naming_the_id(draft_spec):
    """REQ-020 AC1: rule 24."""
    proc = approve(draft_spec)
    assert proc.returncode == 1
    assert "FAIL specs: SPEC-0001: Q-AB-1 has no ruling" in proc.stdout
    assert "which format" not in proc.stdout


def test_ac1_a_rulings_row_in_the_notes_file_rules_the_question(draft_spec):
    """REQ-020 AC1: rule 24."""
    notes = "# Notes\n\n## Rulings (maintainers)\n\n| Q | Ruling |\n| --- | --- |\n"
    notes += "| Q-AB-1 ruled | json |\n"
    assert approve(draft_spec, **{NOTES: notes}).returncode == 0


def test_ac1_a_decisions_log_row_rules_the_question(draft_spec):
    """REQ-020 AC1: rule 24."""
    log = EMPTY_LOG + "| 2026-10-18 | Q-AB-1 ruled: json |\n"
    assert approve(draft_spec, **{LOG: log}).returncode == 0


def test_ac1_a_mention_in_prose_is_not_an_asked_question(repo):
    """REQ-020 AC1: rule 24 (only a table row or list item starts a question)."""
    repo.commit({SPEC: spec("Draft", extra="\nSee Q-AB-1 for why.\n"), LOG: EMPTY_LOG}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved", extra="\nSee Q-AB-1 for why.\n")})
    assert repo.run("check_specs.py", "--base", "main").returncode == 0


def test_ac1_a_table_row_in_the_notes_file_asks_a_question(draft_spec):
    """REQ-020 AC1: rule 24 (`| Q-...` in the notes file, no ruling)."""
    notes = "# Notes\n\n## Questions\n\n| Q | Question |\n| --- | --- |\n| Q-AB-2 | which? |\n"
    proc = approve(draft_spec, **{NOTES: notes, LOG: EMPTY_LOG + "| x | Q-AB-1 ruled |\n"})
    assert proc.returncode == 1 and "Q-AB-2 has no ruling" in proc.stdout


def test_ac1_a_ruling_for_another_id_does_not_rule_this_one(draft_spec):
    """REQ-020 AC1: rule 24 (`Q-AB-1` is not `Q-AB-10`)."""
    notes = "# Notes\n\n## Rulings\n\n| Q-AB-10 ruled | x |\n"
    assert approve(draft_spec, **{NOTES: notes}).returncode == 1


def test_ac1_a_spec_already_approved_and_unchanged_in_status_is_not_rechecked(repo):
    """REQ-020 AC1: rule 24 (and the amendment rule of principle 6 still applies)."""
    open_q = "\n## Open questions\n\n- Q-AB-1 which?\n"
    repo.commit({SPEC: spec("Approved", extra=open_q), LOG: EMPTY_LOG}, "base")
    repo.branch()
    repo.commit(
        {
            SPEC: spec("Approved", extra=open_q + "more\n"),
            "docs/runs/proposed-spec-amendments-1.md": SPEC,
        }
    )
    assert repo.run("check_specs.py", "--base", "main").returncode == 0


def test_ac1_a_new_spec_added_as_approved_is_checked(repo):
    """REQ-020 AC1: rule 24 (an added status line counts)."""
    repo.commit({LOG: EMPTY_LOG, "src/a.py": "1\n"}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved", extra="\n## Open questions\n\n- Q-AB-1 x\n")})
    assert repo.run("check_specs.py", "--base", "main").returncode == 1


def test_ac1_an_intake_questions_id_counts(repo):
    """REQ-020 AC1: rule 24 (a `Q-S<spec>-<n>` id of `## Open questions`)."""
    repo.commit({LOG: EMPTY_LOG}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved", extra="\n## Open questions\n\n- Q-S0001-1 x\n")})
    proc = repo.run("check_specs.py", "--base", "main")
    assert proc.returncode == 1 and "Q-S0001-1 has no ruling" in proc.stdout


# --- the shared parsers (rule 25) ---------------------------------------------------------------


def test_ac1_find_questions_reports_ids_files_and_log_state(tmp_path):
    """REQ-020 AC1: rule 25 (`common.find_questions`; facts' goldens show the same parse)."""
    root = tmp_path
    (root / "docs/runs").mkdir(parents=True)
    (root / "docs/runs/a.md").write_text("Q-AB-1 and Q-AB-10 and Q-AB-2\n", encoding="utf-8")
    assert common.find_questions(root) is None  # no log: unknown, never a default
    (root / LOG).write_text("| 1 | Q-AB-1 ruled: yes |\n| 2 | see Q-AB-2 |\n", encoding="utf-8")
    found = {q["id"]: q for q in common.find_questions(root) or []}
    assert found["Q-AB-1"]["ruled"] is True and found["Q-AB-10"]["ruled"] is False
    assert found["Q-AB-2"]["named_in_log"] is True and found["Q-AB-2"]["ruled"] is False
    assert found["Q-AB-1"]["files"] == ["docs/runs/a.md", LOG]
    assert list(found) == sorted(found)


def test_ac1_next_free_ids_come_from_the_ref_not_the_work_tree(repo):
    """REQ-020 AC1: rule 25 (`common.next_free_ids`)."""
    repo.commit(
        {
            "docs/requirements.md": "### REQ-003 — T\n\n- Status: planned\n\n### REQ-001 — U\n",
            "docs/specs/0013-a.md": "x\n",
            "docs/specs/0002-b.md": "x\n",
            "docs/adr/0021-c.md": "x\n",
        },
        "base",
    )
    repo.write("docs/specs/0099-draft.md", "x\n")
    assert common.next_free_ids(repo.root, "main") == {
        "req": "REQ-004",
        "spec": "0014",
        "adr": "0022",
    }
