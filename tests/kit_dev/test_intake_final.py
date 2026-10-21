"""Kit-only tests of `intake.py check --final`, the approving commit of an intake (SPEC-0020)."""

from __future__ import annotations

import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, git
from test_intake import (
    SCRIPT,
    SENTENCE,
    adr_text,
    draft,
    requirement,
    run,
    spec_text,
    write,
)
from test_intake import repo as intake_repo  # noqa: F401  (the fixture of test_intake)


@pytest.fixture
def repo(request):
    return request.getfixturevalue("intake_repo")


SPEC = "docs/specs/0014-export.md"
ADR = "docs/adr/0022-add-req-004-export.md"
SKILL = KIT_ROOT / "skills" / "spec" / "SKILL.md"
ANSWERED = "The maintainers answered 2 questions before it was written: the file is a download.\n\n"
NONE_ASKED = (
    "The maintainers answered no questions before it was written; the sentence settled "
    "every point.\n\n"
)


def commit_all(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def intake_commit(repo, paragraph=ANSWERED, **spec_args):
    """The first commit of the intake pull request: the three files, as `check` accepts them."""
    draft(repo, spec=spec_text(negative=paragraph, **spec_args))
    commit_all(repo, "intake")


def set_status(repo, rel, old, new):
    path = repo / rel
    text = path.read_text(encoding="utf-8")
    assert f"- Status: {old}" in text
    path.write_text(text.replace(f"- Status: {old}", f"- Status: {new}", 1), encoding="utf-8")


def approve(repo, spec_to="Approved", adr_to="Accepted"):
    """The approving commit: the two status lines and nothing else."""
    set_status(repo, SPEC, "Draft", spec_to)
    set_status(repo, ADR, "Proposed", adr_to)
    commit_all(repo, "approve")


def final(repo):
    return run(repo, "check", "--final", "--base", "main")


def refused(repo, rule):
    proc = final(repo)
    assert proc.returncode == 1, proc.stdout
    lines = proc.stdout.splitlines()
    assert any(line.startswith(f"FAIL intake: rule {rule}") for line in lines), proc.stdout
    assert SENTENCE not in proc.stdout
    return proc.stdout


# --- AC1: the approving commit passes (rules 1, 4, 6) -------------------------------------------


@pytest.mark.parametrize(
    "paragraph",
    [
        "The maintainers answered 1 question before it was written: yes.\n\n",
        ANSWERED,
        "The maintainers answered 3 questions before it was written: a, b and c.\n\n",
        NONE_ASKED,
    ],
)
def test_ac1_a_good_draft_with_an_approving_commit_passes(repo, paragraph):
    """REQ-027 AC1: rules 1, 4 and 6 (N of 1 to 3, and the zero form of Q-K4-217)."""
    intake_commit(repo, paragraph)
    approve(repo)
    proc = final(repo)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout == "ok intake\n"


def test_ac1_the_mode_checks_the_commits_and_not_the_work_tree(repo):
    """REQ-027 AC1: rule 1 (it reads HEAD~1 and HEAD; an untracked file does not matter)."""
    intake_commit(repo)
    approve(repo)
    write(repo, "notes.md", "scratch\n")
    assert final(repo).returncode == 0


# --- AC2: the approving commit changes two lines and nothing else (rule 4) ----------------------


def test_ac2_a_third_changed_line_is_refused(repo):
    """REQ-027 AC2: rule 4 (one more line in the spec)."""
    intake_commit(repo)
    spec = repo / SPEC
    spec.write_text(spec.read_text(encoding="utf-8") + "\nAn added line.\n", encoding="utf-8")
    approve(repo)
    refused(repo, 4)


def test_ac2_a_reworded_line_next_to_the_status_is_refused(repo):
    """REQ-027 AC2: rule 4 (a changed rule is not a status line)."""
    intake_commit(repo)
    spec = repo / SPEC
    text = spec.read_text(encoding="utf-8")
    spec.write_text(text.replace("The export lists every item.", "The export lists items."))
    approve(repo)
    refused(repo, 4)


def test_ac2_a_third_file_is_refused(repo):
    """REQ-027 AC2: rule 4 (a file other than the spec and the ADR)."""
    intake_commit(repo)
    write(repo, "docs/runs/decisions-log.md", "| row |\n", "a")
    approve(repo)
    refused(repo, 4)


def test_ac2_the_requirements_file_in_the_approving_commit_is_refused(repo):
    """REQ-027 AC2 and AC6: rule 4 (the requirement stays planned; the file is not touched)."""
    intake_commit(repo)
    path = repo / "docs" / "requirements.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    approve(repo)
    refused(repo, 4)


@pytest.mark.parametrize(
    ("spec_to", "adr_to"),
    [
        ("Accepted", "Accepted"),
        ("Approved", "Approved"),
        ("Approved", "Superseded"),
        ("Draft ", "Accepted"),
        ("approved", "Accepted"),
    ],
)
def test_ac2_a_status_other_than_the_two_is_refused(repo, spec_to, adr_to):
    """REQ-027 AC2: rule 4 (Draft to Approved and Proposed to Accepted, no other value)."""
    intake_commit(repo)
    approve(repo, spec_to, adr_to)
    refused(repo, 4)


def test_ac2_only_one_of_the_two_files_changed_is_refused(repo):
    """REQ-027 AC2: rule 4 (exactly two files)."""
    intake_commit(repo)
    set_status(repo, SPEC, "Draft", "Approved")
    commit_all(repo, "approve the spec only")
    refused(repo, 4)


def test_ac2_a_failure_names_the_rule_and_never_the_sentence(repo):
    """REQ-027 AC2: rule 4 (the message names a rule, never the sentence)."""
    intake_commit(repo)
    approve(repo, "Accepted", "Accepted")
    out = refused(repo, 4)
    assert "Accepted" not in out and "Draft" not in out


# --- AC3: no open question, and the answers written down (rules 5 and 6) ------------------------


def test_ac3_a_spec_with_a_question_id_is_refused(repo):
    """REQ-027 AC3: rule 5 (an open Q-S id; the old two-pull-request path)."""
    intake_commit(
        repo,
        open_questions="- Q-S0014-1 Which file format?\n",
        extra="\n\nAsked: Q-S0014-1.",
    )
    approve(repo)
    refused(repo, 5)


def test_ac3_an_open_questions_section_that_is_not_none_is_refused(repo):
    """REQ-027 AC3: rule 5."""
    intake_commit(repo, open_questions="A question in words.\n")
    approve(repo)
    refused(repo, 5)


@pytest.mark.parametrize(
    "paragraph",
    [
        "",
        "The maintainers answered 0 questions before it was written: none.\n\n",
        "The maintainers answered 4 questions before it was written: many.\n\n",
        "The maintainers answered three questions before it was written: words.\n\n",
        "The maintainers answered 2 questions: they said yes.\n\n",
        "The maintainers answered no questions before it was written.\n\n",
        "The maintainers answered 1 questions before it was written: yes.\n\n",
        "The maintainers answered 2 question before it was written: yes.\n\n",
    ],
)
def test_ac3_a_spec_without_the_answers_paragraph_is_refused(repo, paragraph):
    """REQ-027 AC3: rule 6 (no paragraph, N of 0 in digits, 4, words, another wording)."""
    intake_commit(repo, paragraph)
    approve(repo)
    refused(repo, 6)


def test_ac3_the_paragraph_must_be_in_the_opening_paragraph(repo):
    """REQ-027 AC3: rule 6 (a sentence under a heading does not count)."""
    intake_commit(repo, "", extra="\n\n" + ANSWERED.strip())
    approve(repo)
    refused(repo, 6)


# --- AC4: check without --final is unchanged (rules 1 and 10) -----------------------------------


def test_ac4_check_without_final_prints_what_it_printed_for_a_good_draft(repo):
    """REQ-027 AC4: rules 1 and 10."""
    intake_commit(repo)
    proc = run(repo, "check", "--base", "main")
    assert (proc.returncode, proc.stdout) == (0, "ok intake\n")


def test_ac4_check_without_final_still_refuses_approved_and_accepted(repo):
    """REQ-027 AC4: rules 1 and 10 (C6, as before this change)."""
    intake_commit(repo)
    approve(repo)
    proc = run(repo, "check", "--base", "main")
    assert proc.returncode == 1
    assert "FAIL intake: C6 the spec is not `Draft`" in proc.stdout
    assert "FAIL intake: C6 the ADR is not `Proposed`" in proc.stdout


def test_ac4_final_belongs_to_check_only(repo):
    """REQ-027 AC4: rule 1 (the other commands refuse the flag with the usage exit)."""
    for command in ("ids", "stub", "next-steps"):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--final", "--root", str(repo)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 2, command


# --- AC5: a separate last commit on a good draft (rules 2 and 3) --------------------------------


def test_ac5_a_first_commit_that_already_carries_the_statuses_is_refused(repo):
    """REQ-027 AC5: rules 2 and 3."""
    draft(repo, spec=spec_text(status="Approved", negative=ANSWERED), adr=adr_text("Accepted"))
    commit_all(repo, "intake with the approval")
    write(repo, "docs/runs/decisions-log.md", "| row |\n", "a")
    commit_all(repo, "something else")
    refused(repo, 3)


def test_ac5_a_single_commit_that_is_the_intake_and_the_approval_is_refused(repo):
    """REQ-027 AC5: rule 2 (HEAD~1 is the merge base)."""
    draft(repo, spec=spec_text(status="Approved", negative=ANSWERED), adr=adr_text("Accepted"))
    commit_all(repo, "one commit")
    refused(repo, 2)


def test_ac5_the_commit_before_must_pass_every_check_of_the_draft(repo):
    """REQ-027 AC5: rule 3 (a draft with no negative case and no reason is not repaired)."""
    acceptance = "AC1 Given a list, when exported, then a file is downloaded"
    spec = spec_text(negative=ANSWERED, tests="- Rule 1: test, marker REQ-004 AC1.\n")
    draft(repo, req=requirement(acceptance), spec=spec)
    commit_all(repo, "intake")
    approve(repo)
    refused(repo, 3)


def test_ac5_a_merge_commit_as_the_last_commit_is_refused(repo):
    """REQ-027 AC5: rule 2 (the approving commit has one parent)."""
    intake_commit(repo)
    git(repo, "switch", "-q", "-c", "side")
    write(repo, "side.txt", "x\n")
    commit_all(repo, "side")
    git(repo, "switch", "-q", "intake/req-004-export")
    approve(repo)
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "side")
    refused(repo, 2)


# --- AC6: git and files only; the requirement stays planned (rules 1, 4 and 7) ------------------


def test_ac6_the_requirement_is_planned_at_head_and_the_mode_does_not_change_it(repo):
    """REQ-027 AC6: rules 4 and 7."""
    intake_commit(repo)
    approve(repo)
    before = git(repo, "status", "--porcelain")
    assert final(repo).returncode == 0
    assert git(repo, "status", "--porcelain") == before
    text = (repo / "docs" / "requirements.md").read_text(encoding="utf-8")
    assert text.rstrip().endswith("- Status: planned")


def test_ac6_intake_py_imports_nothing_that_reaches_the_network_or_a_model():
    """REQ-027 AC6: rules 1 and 7."""
    source = (KIT_ROOT / "scripts" / "agk" / "intake.py").read_text(encoding="utf-8")
    imports = set(re.findall(r"(?m)^(?:import|from) ([a-z_]+)", source))
    assert not imports & {"urllib", "socket", "http", "requests", "ssl", "anthropic"}, imports


# --- Rule 8: the skill, the printed steps and the stub ------------------------------------------


def test_ac1_the_skill_says_when_the_answers_go_in_the_paragraph_and_never_commits_it():
    """REQ-027 AC1: rule 8 (the skill text; no forbidden verb is added)."""
    text = SKILL.read_text(encoding="utf-8")
    assert "opening paragraph" in text and "check --final" in text
    assert "The maintainers answered" in text and "no `Q-S` id" in text
    assert "never makes the approving commit" in text
    assert "N as a digit (1, 2 or 3)" in text and "`3 questions`, not `three questions`" in text
    for verb in ("git push", "git commit", "gh pr"):
        assert verb not in text, verb


def test_ac1_next_steps_name_the_final_commit_mode_and_the_two_status_lines(repo):
    """REQ-027 AC1: rule 8."""
    intake_commit(repo)
    proc = run(repo, "next-steps", "--base", "main")
    assert proc.returncode == 0, proc.stdout
    assert "check --final" in proc.stdout
    assert "Status: Draft" in proc.stdout and "Status: Approved" in proc.stdout
    assert "Status: Proposed" in proc.stdout and "Status: Accepted" in proc.stdout


def test_ac1_the_stub_decision_is_true_on_both_paths(repo):
    """REQ-027 AC1: rule 8 (Q-K4-218, ruled)."""
    proc = run(
        repo,
        "stub",
        "--req",
        "REQ-004",
        "--title",
        "Export",
        "--sentence",
        SENTENCE,
        "--ref",
        "main",
    )
    assert proc.returncode == 0, proc.stdout
    stub = repo / proc.stdout.split()[-1]
    body = " ".join(stub.read_text(encoding="utf-8").split())
    assert (
        "stays `Draft` until it is approved, by a later pull request or by this intake's own "
        "final commit" in body
    )
    assert "until its open questions are ruled" not in body
