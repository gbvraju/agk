"""Kit-only tests of the forms of the answers paragraph that `check --final` accepts (SPEC-0027).

The text before the first `## ` heading says when and how the maintainers answered. No network and
no model.
"""

from __future__ import annotations

import pytest
from test_intake import repo as intake_repo  # noqa: F401  (the fixture of test_intake)
from test_intake_final import approve, final, intake_commit, refused


@pytest.fixture
def repo(request):
    return request.getfixturevalue("intake_repo")


REVIEW = "The maintainers answered {n} at review, before approval: a, b.\n\n"
GAVE = "The maintainers gave {n} before it was written, in the issue: a, b.\n\n"


@pytest.mark.parametrize("n", ["1 question", "2 questions", "3 questions"])
def test_ac4_the_review_form_passes_for_one_to_three_questions(repo, n):
    """REQ-034 AC4: rule 4 (b) (answered at review, before approval)."""
    intake_commit(repo, REVIEW.format(n=n))
    approve(repo)
    proc = final(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok intake\n"), proc.stdout


@pytest.mark.parametrize(
    "n", ["1 answer", "2 answers", "3 answers", "4 answers", "7 answers", "12 answers"]
)
def test_ac5_the_gave_form_passes_for_any_number_from_one(repo, n):
    """REQ-034 AC5: rule 4 (c) (answers given in a brief or an issue, no cap of three)."""
    intake_commit(repo, GAVE.format(n=n))
    approve(repo)
    proc = final(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok intake\n"), proc.stdout


@pytest.mark.parametrize(
    "paragraph",
    [
        "The maintainers answered 1 question before it was written: yes.\n\n",
        "The maintainers answered 3 questions before it was written: a, b and c.\n\n",
        "The maintainers answered no questions before it was written; the sentence settled "
        "every point.\n\n",
    ],
)
def test_ac5_the_older_forms_still_pass(repo, paragraph):
    """REQ-034 AC5: rule 4 (a) is unchanged."""
    intake_commit(repo, paragraph)
    approve(repo)
    assert final(repo).stdout == "ok intake\n"


@pytest.mark.parametrize(
    "paragraph",
    [
        REVIEW.format(n="4 questions"),
        REVIEW.format(n="0 questions"),
        REVIEW.format(n="2 question"),
        REVIEW.format(n="1 questions"),
        REVIEW.format(n="two questions"),
        "The maintainers answered 2 questions after approval: a, b.\n\n",
        "The maintainers answered 2 questions at review, after approval: a, b.\n\n",
        "The maintainers answered 2 questions at review: a, b.\n\n",
        "The maintainers answered 4 questions at review, before approval, and one after "
        "approval.\n\n",
        GAVE.format(n="0 answers"),
        GAVE.format(n="1 answers"),
        GAVE.format(n="2 answer"),
        GAVE.format(n="seven answers"),
        "The maintainers gave 3 answers after approval: a, b, c.\n\n",
        "The maintainers gave 3 answers at review, before approval: a, b, c.\n\n",
        "The maintainers gave 3 answers: a, b, c.\n\n",
    ],
)
def test_ac6_another_wording_or_number_or_the_form_for_after_approval_is_refused(repo, paragraph):
    """REQ-034 AC6: rules 4 and 5 (the rule is named and the sentence never printed)."""
    intake_commit(repo, paragraph)
    approve(repo)
    refused(repo, 6)


def test_ac7_an_open_question_is_still_refused_with_the_new_forms(repo):
    """REQ-034 AC7: rule 6 (rule 5 of SPEC-0020 is unchanged)."""
    intake_commit(repo, GAVE.format(n="5 answers"), open_questions="Q-S0014-1 what?\n")
    approve(repo)
    proc = final(repo)
    assert proc.returncode == 1 and "FAIL intake" in proc.stdout


def test_ac7_a_third_changed_line_is_still_refused_with_the_new_forms(repo):
    """REQ-034 AC7: rule 6 (rule 4 of SPEC-0020 is unchanged)."""
    intake_commit(repo, REVIEW.format(n="2 questions"))
    spec = repo / "docs/specs/0014-export.md"
    spec.write_text(spec.read_text(encoding="utf-8") + "\nAn added line.\n", encoding="utf-8")
    approve(repo)
    refused(repo, 4)


def test_ac4_the_skill_names_the_three_forms_and_the_first_line():
    """REQ-034 AC4: rules 1 and 4 (the skill says which form to write, and never after approval)."""
    from conftest import KIT_ROOT

    text = (KIT_ROOT / "skills" / "spec" / "SKILL.md").read_text(encoding="utf-8")
    assert "answered N questions at review, before approval" in text
    assert "gave N answers before it was" in text and "after approval" in text
    assert "intake: kit <version>" in text
    for verb in ("git push", "git commit", "gh pr"):
        assert verb not in text, verb
