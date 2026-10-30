"""Kit-only tests of scripts/agk/intake.py: ids, sentence, ADR stub (SPEC-0012 1, 2, 8, 16)."""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo, without_version_line

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_adrs  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "intake.py"
SENTENCE = "Let a visitor export their saved list as a file."
BASE_REQS = (
    "# Requirements\n\n### REQ-003 — Three\n\n- Acceptance: AC1 x\n- Status: done\n\n"
    "### REQ-001 — One\n\n- Acceptance: AC1 x\n- Status: planned\n"
)


ACCEPTANCE = (
    "AC1 Given a saved list, when the visitor exports it, then a file with every item is "
    "downloaded; AC2 Given an empty list, when the visitor exports it, then the export is "
    "no file and shows an error message"
)


def marker(req: str, ac: str) -> str:
    return f"@{req[3:]} {ac}".replace("@", "REQ")


def requirement(
    acceptance: str = ACCEPTANCE, status: str = "planned", title: str = "Export"
) -> str:
    return f"\n### REQ-004 — {title}\n\n- Acceptance: {acceptance}\n- Status: {status}\n"


def spec_text(
    status: str = "Draft",
    reqs: str = "REQ-004",
    tests: str | None = None,
    residual: str = "- 2026-10-18: later (due 2027-01-31).\n",
    extra: str = "",
    negative: str = "",
    proof: str = "Rules 1 to 2.\n",
    open_questions: str = "none\n",
) -> str:
    tests = (
        tests
        if tests is not None
        else (
            f"- Rule 1: test, marker {marker('REQ-004', 'AC1')}.\n"
            f"- Rule 2: test, marker {marker('REQ-004', 'AC2')}.\n"
        )
    )
    return (
        f"# SPEC-0014: Export\n\n- Status: {status}\n- Owner: reviewer group\n"
        f"- Requirements: {reqs}\n\n{negative}## Rules\n\n"
        f"1. The export lists every item.{extra}\n\n"
        f"## Tests\n\n{tests}\n## Proof\n\n{proof}\n## Residual\n\n{residual}\n"
        f"## Open questions\n\n{open_questions}"
    )


def adr_text(status: str = "Proposed", classes: str = "`docs/requirements.md`") -> str:
    return (
        (KIT_ROOT / "tests" / "kit_dev" / "intake_adr.txt")
        .read_text(encoding="utf-8")
        .replace("@STATUS@", status)
        .replace("@CLASSES@", classes)
    )


@pytest.fixture
def repo(tmp_path):
    root = make_repo(tmp_path / "proj")
    for rel, text in (
        ("docs/requirements.md", BASE_REQS),
        ("docs/specs/0013-old.md", "# SPEC-0013: Old\n"),
        ("docs/specs/0002-older.md", "# SPEC-0002: Older\n"),
        ("docs/adr/0021-old.md", "# ADR-0021: Old\n"),
        ("docs/adr/0007-older.md", "# ADR-0007: Older\n"),
        ("docs/runs/decisions-log.md", "# Decisions log\n\n| Date | Decision |\n| --- | --- |\n"),
        ("docs/runs/residuals.md", "# Residuals\n\n## Open\n\n## Closed (not findings)\n"),
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "intake/req-004-export")
    return root


def run(repo, *args):
    return without_version_line(
        subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--root", str(repo), "--date", "2026-10-18"],
            capture_output=True,
            text=True,
            env=clean_env(),
        )
    )


def write(repo, rel, text, mode="w"):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(text)


def draft(repo, req=None, spec=None, adr=None):
    write(repo, "docs/requirements.md", req if req is not None else requirement(), "a")
    write(repo, "docs/specs/0014-export.md", spec if spec is not None else spec_text())
    write(repo, "docs/adr/0022-add-req-004-export.md", adr if adr is not None else adr_text())


def check(repo):
    return run(repo, "check", "--base", "main")


# --- ids and the sentence (rules 1, 2) ----------------------------------------------------------


def test_ac1_ids_are_the_next_free_numbers_of_the_base_not_the_work_tree(repo):
    """REQ-019 AC1: rule 2 (gaps; the highest is not the last; leading zeros; independent)."""
    write(repo, "docs/specs/0099-draft-only.md", "# SPEC-0099: x\n")
    proc = run(repo, "ids", "--sentence", SENTENCE, "--ref", "main")
    assert proc.returncode == 0, proc.stdout
    assert json.loads(proc.stdout) == {
        "req": "REQ-004",
        "spec": "0014",
        "adr": "0022",
        "slug": "let-a-visitor-export-their-saved-list-as-a-file",
    }
    assert git_status_unchanged(repo)


def git_status_unchanged(repo) -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    return out.strip() == "?? docs/specs/0099-draft-only.md"


def test_ac1_ids_on_an_empty_base_start_at_one(tmp_path):
    """REQ-019 AC1: rule 2 (an empty requirements file)."""
    root = make_repo(tmp_path / "e")
    write(root, "docs/requirements.md", "# Requirements\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "r")
    proc = run(root, "ids", "--sentence", SENTENCE, "--ref", "main")
    assert json.loads(proc.stdout)["req"] == "REQ-001"
    assert json.loads(proc.stdout)["spec"] == "0001" and json.loads(proc.stdout)["adr"] == "0001"


def test_ac1_ids_read_origin_of_the_default_branch_by_default(repo, tmp_path):
    """REQ-019 AC1: rule 2 (git fetch is the skill's step; the script reads `origin/<default>`)."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(bare)], check=True)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "fetch", "-q", "origin", "main")
    proc = run(repo, "ids", "--sentence", SENTENCE)
    assert proc.returncode == 0 and json.loads(proc.stdout)["req"] == "REQ-004"
    git(repo, "remote", "remove", "origin")
    proc = run(repo, "ids", "--sentence", SENTENCE)
    assert proc.returncode == 1  # no origin/main: nothing is guessed


@pytest.mark.parametrize(
    "sentence",
    ["", "   ", "x" * 301, "One thing. And another thing.", "Line\nbreak", "...", "!!!"],
)
def test_ac1_a_bad_sentence_is_refused_with_the_rule_and_nothing_is_written(repo, sentence):
    """REQ-019 AC1: rule 1 (empty; over 300 characters; more than one sentence)."""
    proc = run(repo, "ids", "--sentence", sentence, "--ref", "main")
    assert proc.returncode == 1 and proc.stdout.startswith("refused: rule 1")
    assert sentence.strip() not in proc.stdout or not sentence.strip()
    stub = run(
        repo, "stub", "--req", "REQ-004", "--title", "T", "--sentence", sentence, "--ref", "main"
    )
    assert stub.returncode == 1 and not list((repo / "docs" / "adr").glob("0022*"))


@pytest.mark.parametrize(
    "sentence",
    [
        "Users can export data, e.g. as CSV.",
        "Users can export data, E.G. as CSV.",
        "Export a list, i.e. all items, to a file.",
        "Export lists, files, etc. to a file.",
        "A list is longer vs. shorter than ten.",
        "The export takes 3.5 seconds.",
    ],
)
def test_ac1_an_abbreviation_or_a_dot_between_digits_does_not_end_the_sentence(repo, sentence):
    """REQ-019 AC1: rule 1 (Q-K4-173 ruled: e.g., i.e., etc., vs. and digit.digit)."""
    assert run(repo, "ids", "--sentence", sentence, "--ref", "main").returncode == 0


@pytest.mark.parametrize(
    "sentence", ["Do X. Do Y.", "Do X! Do Y", "Really? Do Y.", "Use e.g. a. Do Y."]
)
def test_ac1_any_other_sentence_end_followed_by_text_is_a_second_sentence(repo, sentence):
    """REQ-019 AC1: rule 1 (Q-K4-173 ruled)."""
    proc = run(repo, "ids", "--sentence", sentence, "--ref", "main")
    assert proc.returncode == 1 and proc.stdout.startswith("refused: rule 1")


def test_ac1_a_sentence_of_exactly_300_characters_is_accepted(repo):
    """REQ-019 AC1: rule 1 (the limit)."""
    sentence = ("a" * 299) + "."
    assert run(repo, "ids", "--sentence", sentence, "--ref", "main").returncode == 0


def test_ac1_the_slug_is_at_most_60_characters(repo):
    """REQ-019 AC1: rule 2 (the rule of new_spec.py)."""
    out = json.loads(run(repo, "ids", "--sentence", "word " * 40 + "end.", "--ref", "main").stdout)
    assert len(out["slug"]) <= 60 and not out["slug"].endswith("-")


# --- the ADR stub (rule 8) ----------------------------------------------------------------------


def test_ac1_the_stub_passes_check_adrs_names_the_class_and_uses_the_given_date(repo):
    """REQ-019 AC1: rule 8."""
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
    name = "0022-add-req-004-let-a-visitor-export-their-saved-list-as-a-file.md"
    assert proc.stdout == f"created docs/adr/{name}\n"
    text = (repo / "docs" / "adr" / name).read_text(encoding="utf-8")
    assert check_adrs.validate(name, text, {"0021", "0007"}) == []
    assert "- Status: Proposed" in text and "- Date: 2026-10-18" in text
    assert "- Requirements: REQ-004" in text
    assert "Protected classes: `docs/requirements.md`" in text
    assert f"> {SENTENCE}" in text and "SPEC-0014" in text
    assert (
        run(
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
        ).returncode
        == 1
    )


def test_ac1_the_stub_refuses_a_requirement_that_is_not_the_next_free_one(repo):
    """REQ-019 AC1: rules 2 and 8 (ids are read, never guessed)."""
    proc = run(
        repo,
        "stub",
        "--req",
        "REQ-009",
        "--title",
        "Export",
        "--sentence",
        SENTENCE,
        "--ref",
        "main",
    )
    assert proc.returncode == 1 and "REQ-009" not in proc.stdout.replace("--req", "")
    assert not list((repo / "docs" / "adr").glob("0022*"))


def test_ac1_the_stub_refuses_a_title_over_80_characters_or_with_a_semicolon(repo):
    """REQ-019 AC1: rule 5 (the title)."""
    for title in ("x" * 81, "a; b", ""):
        proc = run(
            repo,
            "stub",
            "--req",
            "REQ-004",
            "--title",
            title,
            "--sentence",
            SENTENCE,
            "--ref",
            "main",
        )
        assert proc.returncode == 1, title


# --- the checks C1 to C9 (rule 11) --------------------------------------------------------------


def test_ac1_a_good_draft_passes_the_checks(repo):
    """REQ-019 AC1: rule 11 (all of C1 to C9 pass)."""
    draft(repo)
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok intake\n")


def test_ac1_the_adr_of_a_good_draft_is_the_stub_that_the_script_renders(repo):
    """REQ-019 AC1: rules 8 and 11."""
    run(
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
    stub = next((repo / "docs" / "adr").glob("0022*"))
    adr = stub.read_text(encoding="utf-8")
    stub.unlink()
    draft(repo, adr=adr)
    assert check(repo).stdout == "ok intake\n"


def test_ac1_c2_the_stubs_own_file_name_passes(repo):
    """REQ-019 AC1: rule 4 and C2 (the name `stub` writes is the name `check` accepts)."""
    write(repo, "docs/requirements.md", requirement(), "a")
    write(repo, "docs/specs/0014-export.md", spec_text())
    stub = run(
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
    assert stub.returncode == 0, stub.stdout
    assert "add-req-004-let-a-visitor" in stub.stdout
    assert check(repo).stdout == "ok intake\n"


def failed(repo, code):
    proc = check(repo)
    assert proc.returncode == 1, proc.stdout
    assert any(line.startswith(f"FAIL intake: {code} ") for line in proc.stdout.splitlines()), (
        proc.stdout
    )
    return proc.stdout


def test_ac1_c1_ids_that_are_not_the_next_free_ones_fail(repo):
    """REQ-019 AC1: rule 11 C1."""
    draft(repo)
    (repo / "docs/specs/0014-export.md").rename(repo / "docs/specs/0015-export.md")
    failed(repo, "C1")


def test_ac1_c1_a_requirement_that_skips_a_number_fails(repo):
    """REQ-019 AC1: rule 11 C1."""
    draft(repo, req=requirement().replace("REQ-004", "REQ-006"))
    failed(repo, "C1")


def test_ac1_c2_a_fourth_file_fails(repo):
    """REQ-019 AC1: rule 11 C2 (and rule 4: no notes file, no test, no code)."""
    draft(repo)
    write(repo, "docs/runs/spec-0014-notes.md", "notes\n")
    failed(repo, "C2")


def test_ac1_c2_a_changed_existing_line_of_the_requirements_fails(repo):
    """REQ-019 AC1: rule 11 C2."""
    draft(repo)
    path = repo / "docs/requirements.md"
    path.write_text(path.read_text(encoding="utf-8").replace("Three", "Tres"), encoding="utf-8")
    failed(repo, "C2")


def test_ac1_c2_a_missing_adr_fails(repo):
    """REQ-019 AC1: rule 11 C2."""
    draft(repo)
    (repo / "docs/adr/0022-add-req-004-export.md").unlink()
    failed(repo, "C2")


def test_ac1_c3_the_acceptance_line_forms(repo):
    """REQ-019 AC1: rule 11 C3 (a repeat; a semicolon inside; more than eight; none)."""
    base = "Given a, when b, then c is not allowed"
    cases = {
        "repeat": f"AC1 {base}; AC1 {base}",
        "gap": f"AC1 {base}; AC3 {base}",
        "semicolon": "AC1 Given a; or a2, when b, then c is not allowed",
        "nine": "; ".join(f"AC{i} {base}" for i in range(1, 10)),
        "free text": "it works",
        "not from one": f"AC2 {base}",
    }
    for name, acceptance in cases.items():
        git(repo, "checkout", "-q", "--", ".")
        subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
        tests = "".join(f"- {marker('REQ-004', f'AC{i}')}\n" for i in range(1, 10))
        draft(repo, req=requirement(acceptance), spec=spec_text(tests=tests))
        failed(repo, "C3")
        assert name


def test_ac1_c3_eight_criteria_are_accepted(repo):
    """REQ-019 AC1: rule 11 C3 (the limit)."""
    base = "Given a, when b, then c is not allowed"
    acceptance = "; ".join(f"AC{i} {base}" for i in range(1, 9))
    tests = "".join(f"- {marker('REQ-004', f'AC{i}')}\n" for i in range(1, 9))
    draft(repo, req=requirement(acceptance), spec=spec_text(tests=tests))
    assert check(repo).stdout == "ok intake\n"


def test_ac1_c3_the_title_limits(repo):
    """REQ-019 AC1: rule 5 (80 characters, no semicolon)."""
    draft(repo, req=requirement(title="x" * 81))
    failed(repo, "C3")


def test_ac1_c4_a_criterion_without_then_or_out_of_order_fails(repo):
    """REQ-019 AC1: rule 11 C4 (case-insensitive; each word followed by text)."""
    for bad in ("Given a, when b", "When b, given a, then c is not", "Given a, when, then c no"):
        git(repo, "checkout", "-q", "--", ".")
        subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
        draft(
            repo,
            req=requirement(f"AC1 {bad}"),
            spec=spec_text(tests=f"- {marker('REQ-004', 'AC1')}\n"),
        )
        failed(repo, "C4")
    git(repo, "checkout", "-q", "--", ".")
    subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
    draft(
        repo,
        req=requirement("AC1 GIVEN a, WHEN b, THEN c is never shown"),
        spec=spec_text(tests=f"- {marker('REQ-004', 'AC1')}\n"),
    )
    assert check(repo).stdout == "ok intake\n"


def test_ac1_c5_a_negative_case_or_a_stated_reason(repo):
    """REQ-019 AC1: rule 6 (with and without the reason; the reason is at least 20 characters)."""
    positive = "AC1 Given a, when b, then c is shown"
    tests = f"- {marker('REQ-004', 'AC1')}\n"
    draft(repo, req=requirement(positive), spec=spec_text(tests=tests))
    failed(repo, "C5")
    git(repo, "checkout", "-q", "--", ".")
    subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
    short = spec_text(tests=tests, negative="Negative cases: none, because short\n\n")
    draft(repo, req=requirement(positive), spec=short)
    failed(repo, "C5")
    git(repo, "checkout", "-q", "--", ".")
    subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
    why = "Negative cases: none, because the sentence names no refusal\n\n"
    draft(repo, req=requirement(positive), spec=spec_text(tests=tests, negative=why))
    assert check(repo).stdout == "ok intake\n"


@pytest.mark.parametrize("status", ["done", "in-progress"])
def test_ac1_c6_a_requirement_status_other_than_planned_fails(repo, status):
    """REQ-019 AC1: rule 11 C6."""
    draft(repo, req=requirement(status=status))
    failed(repo, "C6")


def test_ac1_c6_a_spec_approved_or_an_adr_accepted_fails(repo):
    """REQ-019 AC1: rule 11 C6."""
    draft(repo, spec=spec_text(status="Approved"))
    failed(repo, "C6")
    git(repo, "checkout", "-q", "--", ".")
    subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
    draft(repo, adr=adr_text(status="Accepted"))
    failed(repo, "C6")


def test_ac1_c7_requirements_line_and_test_markers(repo):
    """REQ-019 AC1: rule 11 C7 (a missing marker; a stray marker; another requirement)."""
    for spec in (
        spec_text(reqs="REQ-004, REQ-001"),
        spec_text(tests=f"- {marker('REQ-004', 'AC1')}\n"),
        spec_text(tests="".join(f"- {marker('REQ-004', f'AC{i}')}\n" for i in (1, 2, 3))),
        spec_text(tests=f"- {marker('REQ-001', 'AC1')}\n- {marker('REQ-004', 'AC2')}\n"),
    ):
        git(repo, "checkout", "-q", "--", ".")
        subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
        draft(repo, spec=spec)
        failed(repo, "C7")


def test_ac1_c8_sections_due_dates_and_question_ids(repo):
    """REQ-019 AC1: rule 11 C8."""
    good = spec_text()
    cases = {
        "no proof": good.replace("## Proof", "## Evidence"),
        "empty proof": spec_text(proof=""),
        "no residual": good.replace("## Residual", "## Left"),
        "undated bullet": spec_text(residual="- 2026-10-18: later.\n"),
        "empty residual": spec_text(residual=""),
        "no open questions": good.replace("## Open questions", "## Questions"),
        "foreign question": spec_text(open_questions="- Q-S0013-1 which?\n"),
        "family of another": spec_text(extra=" See Q-K4-9."),
    }
    for name, spec in cases.items():
        git(repo, "checkout", "-q", "--", ".")
        subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
        draft(repo, spec=spec)
        failed(repo, "C8")
        assert name
    git(repo, "checkout", "-q", "--", ".")
    subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
    draft(repo, spec=spec_text(open_questions="- Q-S0014-1 which format?\n", residual="none\n"))
    assert check(repo).stdout == "ok intake\n"


@pytest.mark.parametrize("residual", ["- none\n", "- none.\n", "none\n", "none.\n"])
def test_ac1_c8_a_residual_of_none_is_empty_and_passes(repo, residual):
    """REQ-019 AC1: rule 11 C8 (Q-K4-175 ruled: none, - none, with or without a final dot)."""
    draft(repo, spec=spec_text(open_questions="- Q-S0014-1 x?\n", residual=residual))
    assert check(repo).stdout == "ok intake\n"


def test_ac1_c8_a_none_bullet_mixed_with_a_dated_bullet_is_undated_and_fails(repo):
    """REQ-019 AC1: rule 11 C8 (a `none` bullet among others has no due date)."""
    residual = "- none\n- 2026-10-18: later (due 2027-01-31).\n"
    draft(repo, spec=spec_text(residual=residual))
    failed(repo, "C8")


def test_ac1_c2_the_spec_must_be_directly_in_its_folder(repo):
    """REQ-019 AC1: rule 4 and C2 (a subfolder fails; the message names no part of the name)."""
    draft(repo)
    (repo / "docs/specs/sub").mkdir()
    (repo / "docs/specs/0014-export.md").rename(repo / "docs/specs/sub/0014-export.md")
    out = failed(repo, "C2")
    assert "sub" not in out and "0014-export" not in out


def test_ac1_c2_the_adr_name_must_carry_add_and_the_requirement_id(repo):
    """REQ-019 AC1: rule 4 and C2 (no `add-req-nnn-`, a wrong id, a bad slug)."""
    for name in (
        "0022-export.md",
        "0022-add-req-005-export.md",
        "0022-add-req-004-Export_List.md",
        "0022-add-req-004-.md",
    ):
        git(repo, "checkout", "-q", "--", ".")
        subprocess.run(["git", "clean", "-fdq"], cwd=repo, check=True)
        draft(repo)
        (repo / "docs/adr/0022-add-req-004-export.md").rename(repo / "docs/adr" / name)
        out = failed(repo, "C2")
        assert name[5:] not in out


def test_ac1_c2_the_spec_slug_has_only_lowercase_letters_digits_and_hyphens(repo):
    """REQ-019 AC1: rule 4 and C2."""
    draft(repo)
    (repo / "docs/specs/0014-export.md").rename(repo / "docs/specs/0014-Export_List.md")
    failed(repo, "C2")


def test_ac1_c9_the_adr_must_name_the_requirements_file(repo):
    """REQ-019 AC1: rule 11 C9."""
    draft(repo, adr=adr_text(classes="`docs/specs/`"))
    failed(repo, "C9")


def test_ac1_a_failure_names_the_rule_and_never_the_sentence(repo):
    """REQ-019 AC1: rule 11 (messages name the rule, never the sentence)."""
    draft(
        repo, req=requirement("AC1 Given the secret-word-xyz, when b").replace("Export", "Export")
    )
    out = failed(repo, "C4")
    assert "secret-word-xyz" not in out


def test_ac1_check_without_a_base_fails_rather_than_passing(repo):
    """REQ-019 AC1: rule 11 (a check that cannot read its base does not pass)."""
    draft(repo)
    proc = run(repo, "check", "--base", "no-such-ref")
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL intake:")


# --- a draft is not a fact (rule 14) ------------------------------------------------------------

FACTS = KIT_ROOT / "scripts" / "agk" / "facts.py"
REPORT = KIT_ROOT / "scripts" / "agk" / "product_report.py"
SKILL = KIT_ROOT / "skills" / "spec" / "SKILL.md"


def facts_of(root, tmp_path) -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            str(FACTS),
            "--today",
            "2026-10-18",
            "--repo",
            "demo-org/demo-repo",
            str(root),
        ],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (tmp_path / "facts.json").write_text(proc.stdout, encoding="utf-8")
    return json.loads(proc.stdout)


def render(tmp_path, *flags) -> str:
    proc = subprocess.run(
        [sys.executable, str(REPORT), "--facts", str(tmp_path / "facts.json"), *flags],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout
    return proc.stdout


def commit_draft(repo, spec=None):
    draft(repo, spec=spec)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "intake")


def test_ac2_the_facts_of_the_default_branch_do_not_contain_the_draft(repo, tmp_path):
    """REQ-019 AC2: rule 14 (a draft on the intake branch is not in requirements, specs, adrs)."""
    commit_draft(repo)
    git(repo, "switch", "-q", "main")
    doc = facts_of(repo, tmp_path)
    assert "REQ-004" not in [r["id"] for r in doc["requirements"]]
    assert "SPEC-0014" not in [s["id"] for s in doc["specs"]]
    assert not [a for a in doc["adrs"] if a["path"].startswith("docs/adr/0022")]
    assert "REQ-004" not in render(tmp_path) and "SPEC-0014" not in render(tmp_path, "--inbox")
    git(repo, "switch", "-q", "intake/req-004-export")  # the control: the branch itself has it
    assert "REQ-004" in [r["id"] for r in facts_of(repo, tmp_path)["requirements"]]


# --- the next steps (rule 13) -------------------------------------------------------------------


def test_ac1_next_steps_print_the_commit_the_push_and_a_body_that_passes_check_pr_body(repo):
    """REQ-019 AC1: rule 13."""
    draft(repo)
    proc = run(repo, "next-steps", "--base", "main", "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    assert "intake: add REQ-004 Export" in proc.stdout
    assert "git push -u origin HEAD" in proc.stdout
    body = proc.stdout.split("Pull request body:\n\n", 1)[1]
    assert re.search(r"(?m)^Advances: REQ-004$", body)
    assert re.search(r"(?m)^Build-state row: 2026-10-18 ", body)
    for label in ("Decisions taken:", "Questions:", "Verified:"):
        assert label in body
    assert "cannot tell" in proc.stdout
    ok = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "check_pr_body.py"), "-"],
        input=body,
        capture_output=True,
        text=True,
    )
    assert ok.stdout == "ok pr-body\n"


def test_ac1_next_steps_refuse_when_the_checks_fail(repo):
    """REQ-019 AC1: rule 13 (nothing is printed for a draft that fails)."""
    draft(repo, adr=adr_text(status="Accepted"))
    proc = run(repo, "next-steps", "--base", "main")
    assert proc.returncode == 1 and "git push" not in proc.stdout


def test_ac1_next_steps_refuse_on_a_detached_head_or_the_default_branch(repo):
    """REQ-019 AC1: rule 3 (no push of the default branch, no push of nothing)."""
    draft(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "intake")
    git(repo, "switch", "-q", "--detach")
    for _ in range(2):
        proc = run(repo, "next-steps", "--base", "main~1")
        assert proc.returncode == 1 and proc.stdout.startswith("refused: rule 3")
        assert "git push" not in proc.stdout and "main" not in proc.stdout.replace("rule 3", "")
        git(repo, "switch", "-q", "main")
        git(repo, "merge", "-q", "--ff-only", "intake/req-004-export")
    git(repo, "switch", "-q", "intake/req-004-export")
    proc = run(repo, "next-steps", "--base", "main~1", "--brief", "none")
    assert proc.returncode == 0 and "git push -u origin HEAD" in proc.stdout


def test_ac2_after_the_merge_the_requirement_is_planned_and_the_spec_and_adr_wait(repo, tmp_path):
    """REQ-019 AC2: rule 14 (merging approves the requirement; the spec stays Draft)."""
    commit_draft(repo, spec=spec_text(open_questions="- Q-S0014-1 which format?\n"))
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "intake/req-004-export")
    doc = facts_of(repo, tmp_path)
    req = next(r for r in doc["requirements"] if r["id"] == "REQ-004")
    assert req["status"] == "planned"
    spec = next(s for s in doc["specs"] if s["id"] == "SPEC-0014")
    assert spec["status"] == "Draft"
    adr = next(a for a in doc["adrs"] if a["path"].startswith("docs/adr/0022"))
    assert adr["status"] == "Proposed"
    question = next(q for q in doc["questions"] if q["id"] == "Q-S0014-1")
    assert question["open_in"] == ["docs/specs/0014-export.md"] and question["ruled"] is False
    inbox = render(tmp_path, "--inbox")
    assert "SPEC-0014" in inbox and "ADR-0022" in inbox and "Q-S0014-1" in inbox
    report = render(tmp_path)
    delivered = report.split("## Proven")[0]
    assert "REQ-004" not in delivered


# --- the skill (rules 9, 13, 16) ----------------------------------------------------------------


def test_ac1_the_skill_names_no_forbidden_verb_and_the_three_files_only():
    """REQ-019 AC1: rules 4, 13 and 16 (SPEC-0005 rule 10)."""
    text = SKILL.read_text(encoding="utf-8")
    for verb in ("git push", "git commit", "gh pr", "gh issue close", "gh issue comment"):
        assert verb not in text, verb
    files = set(re.findall(r"`(docs/[a-z]+/[^`]*)`", text.split("## One sentence")[1]))
    allowed = {
        "docs/requirements.md",
        "docs/specs/<spec>-<slug>.md",
        "docs/specs/TEMPLATE.md",
    }
    assert files <= allowed, files - allowed
    assert "disable-model-invocation: true" in text
    assert "at most three questions" in text and "Q-S<spec>-<n>" in text


def test_ac1_the_skill_calls_use_the_commands_the_script_has():
    """REQ-019 AC1: rules 2, 8, 11 and 13."""
    text = SKILL.read_text(encoding="utf-8")
    calls = re.findall(r'intake\.py" (ids|stub|check|next-steps)', text)
    assert calls == ["ids", "stub", "check", "next-steps"]
    assert (
        subprocess.run(
            [sys.executable, str(SCRIPT), "bogus"], capture_output=True, text=True
        ).returncode
        == 2
    )


# --- build (e) of SPEC-0034: the numbers of a session and the decisions log ---------------------


def session_ids(tmp_path, **ids):
    """The file `session.py ids` printed: the next free numbers counted with open pull requests."""
    path = tmp_path / "ids.json"
    path.write_text(json.dumps({"req": "REQ-004", "spec": "0014", "adr": "0022", "rule": 5} | ids))
    return path


def test_ac1_c1_with_session_ids_a_number_held_by_an_open_pull_request_fails(repo, tmp_path):
    """Brief #176 (e) 1: the base says 0014 and 0022, an open pull request holds them."""
    draft(repo)
    held = session_ids(tmp_path, req="REQ-005", spec="0015", adr="0023")
    proc = check_with(repo, held)
    assert proc.returncode == 1 and "C1 " in proc.stdout, proc.stdout


def test_ac1_c1_with_session_ids_the_numbers_after_those_of_open_pull_requests_pass(repo, tmp_path):
    """Brief #176 (e) 1: the intake that took the numbers `session.py ids` printed passes."""
    write(repo, "docs/requirements.md", requirement().replace("REQ-004", "REQ-005"), "a")
    write(repo, "docs/specs/0015-export.md", spec_text().replace("REQ-004", "REQ-005"))
    write(repo, "docs/adr/0023-add-req-005-export.md", adr_text())
    held = session_ids(tmp_path, req="REQ-005", spec="0015", adr="0023")
    proc = check_with(repo, held)
    assert (proc.returncode, proc.stdout) == (0, "ok intake\n"), proc.stdout


def test_ac1_c1_without_session_ids_the_numbers_of_the_default_branch_are_used(repo):
    """Brief #176 (e) 1: offline the check is as it was."""
    draft(repo)
    assert check(repo).stdout == "ok intake\n"


@pytest.mark.parametrize("text", ["not json", "[]", '{"req": "REQ-4"}', '{"req": "REQ-004"}'])
def test_ac1_c1_an_ids_file_that_session_py_did_not_print_is_refused(repo, tmp_path, text):
    """Brief #176 (e) 1: the message names the option, never the file's content."""
    draft(repo)
    path = tmp_path / "ids.json"
    path.write_text(text)
    proc = check_with(repo, path)
    assert proc.returncode == 1 and "--ids" in proc.stdout and text not in proc.stdout


def check_with(repo, ids):
    return run(repo, "check", "--base", "main", "--ids", str(ids))


LOG = "docs/runs/decisions-log.md"


def test_ac1_c2_rows_added_to_the_decisions_log_are_allowed(repo):
    """Brief #176 (e) 2: the rulings of the intake's questions are recorded before it flips."""
    draft(repo)
    write(repo, LOG, "| 2026-10-25 | Q-S0014-1 ruled: yes |\n", "a")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok intake\n"), proc.stdout


@pytest.mark.parametrize("how", ["changed", "removed"])
def test_ac1_c2_a_changed_or_removed_row_of_the_decisions_log_fails(repo, how):
    """Brief #176 (e) 2: added rows only."""
    path = repo / LOG
    path.write_text(path.read_text(encoding="utf-8") + "| 2026-10-01 | old row |\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "a row")
    git(repo, "branch", "-f", "main", "HEAD")
    draft(repo)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("old row", "new row")
        if how == "changed"
        else text.replace("| 2026-10-01 | old row |\n", "")
    )
    failed(repo, "C2")


def test_ac1_c2_other_files_under_docs_runs_still_fail(repo):
    """Brief #176 (e) 2: only the decisions log is allowed beside the three files."""
    draft(repo)
    write(repo, "docs/runs/residuals.md", "more\n", "a")
    failed(repo, "C2")
