"""The optional mutation-testing command of the weekly audit (REQ-011, brief 449, ADR-0240).

SPEC-0004 rule 25 (amendment 106, proposed): a third setting of `agk.toml`, `mutation`, empty by
default, a shell command like `coverage`. When it is set, the report run of the drift audit runs it
with `AGK_CHANGED_FILES` naming a file that lists the code files changed on the default branch in
the last 7 days (at most 20, the first by name), reads the score, a percentage, from the last line
of its output and lists it under D9 as `killed <n>% of injected faults in <k> files` with the change
since the previous audit. A missing number reads `unknown`; a failure is listed, never blocking; no
changed code file means the command is not run, and the line says so. The kit ships no tool."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import drift_fixtures as fx
import pytest
from test_drift_audit import SUMMARY, audit, findings

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import common  # noqa: E402
import drift_audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE_TOML = 'default_branch = "main"\ntest_dirs = ["tests"]\n'
RULE = "SPEC-0004 rule 25"
NOT_RUN = "not run: no code file changed on the default branch in the last 7 days"


@pytest.fixture
def repo(tmp_path):
    return fx.base(tmp_path / "repo")


def configure(repo, days_ago: int = 30, **settings: str) -> None:
    text = BASE_TOML + "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    repo.write("agk.toml", text)
    repo.commit(days_ago)


def change_code(repo, *paths: str, days_ago: int = 1) -> None:
    for rel in paths:
        repo.write(rel, f"value = {len(rel)}  # {days_ago}\n")
    repo.commit(days_ago, "change code")


def d9(root, *extra: str) -> dict[str, tuple[str, str]]:
    """subject -> (rule, sentence) of the D9 findings."""
    return {f[1]: (f[2], f[3]) for f in findings(root, *extra) if f[0] == "D9"}


def mutation(root, *extra: str) -> str:
    rule, sentence = d9(root, *extra)["mutation"]
    assert rule == RULE
    return sentence


def previous(tmp_path, killed: str | None) -> str:
    """A previous audit report as the open audit issue holds it."""
    line = (
        f"- D9 mutation | {RULE} | killed {killed}% of injected faults in 3 files, "
        "change since the previous audit: unknown"
    )
    body = "agk drift audit 2026-10-08 (window 2026-10-01 to 2026-10-08): findings=1\n\n"
    body += (line if killed is not None else "No findings.") + "\n"
    path = tmp_path / "previous.md"
    path.write_text(body, encoding="utf-8")
    return str(path)


# --- the setting (answers 1 and 5: the setting unset) -------------------------------------------


def test_the_setting_is_empty_by_default_next_to_coverage():
    assert common.DEFAULT_CONFIG["mutation"] == ""
    keys = list(common.DEFAULT_CONFIG)
    assert keys.index("mutation") == keys.index("coverage") + 1


@pytest.mark.parametrize("rel", ["kit/templates/agk.toml", "kit/templates/agk.adopt.toml"])
def test_both_templates_name_the_setting_empty(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert re.search(r'^mutation = ""$', text, flags=re.M)
    assert "AGK_CHANGED_FILES" in text


def test_the_setting_is_read_from_agk_toml(repo):
    configure(repo, mutation="echo 50")
    assert common.load_config(repo.root)["mutation"] == "echo 50"


def test_with_the_setting_unset_there_is_no_mutation_line(repo):
    change_code(repo, "app/a.py")
    assert "mutation" not in d9(repo.root)
    match = SUMMARY.match(audit(repo.root).stdout.splitlines()[0])
    assert match and match.group(13) == "0"


def test_an_empty_setting_is_no_setting(repo):
    configure(repo, mutation="  ")
    change_code(repo, "app/a.py")
    assert d9(repo.root) == {}
    assert audit(repo.root, "--print-action").stdout.strip() == "none"


# --- a score (answers 1, 2 and 5) --------------------------------------------------------------


def test_a_score_is_read_from_the_last_line_with_the_number_of_files(repo):
    configure(repo, mutation=r'printf "survived 3\nkilled 9 of 12\n75\n"')
    change_code(repo, "app/a.py", "app/b.py")
    assert mutation(repo.root) == (
        "killed 75% of injected faults in 2 files, change since the previous audit: unknown"
    )


def test_a_percent_sign_and_a_fraction_are_accepted_and_one_file_reads_singular(repo):
    configure(repo, mutation="echo 62.5%")
    change_code(repo, "app/a.py")
    assert mutation(repo.root).startswith("killed 62.5% of injected faults in 1 file, ")


def test_the_change_is_computed_from_the_previous_audit(repo, tmp_path):
    configure(repo, mutation="echo 81.5")
    change_code(repo, "app/a.py")
    up = mutation(repo.root, "--previous", previous(tmp_path, "80"))
    assert up.endswith("change since the previous audit: +1.5")
    configure(repo, days_ago=0, mutation="echo 79.25")
    down = mutation(repo.root, "--previous", previous(tmp_path, "80"))
    assert down.endswith("change since the previous audit: -0.75")


def test_a_real_report_fed_back_as_previous_gives_the_change(repo, tmp_path):
    """The line the report writes is the line the next audit reads (format kept in step)."""
    configure(repo, mutation="echo 70")
    change_code(repo, "app/a.py")
    first = tmp_path / "first.md"
    first.write_text(audit(repo.root).stdout, encoding="utf-8")
    configure(repo, days_ago=0, mutation="echo 72.5")
    assert mutation(repo.root, "--previous", str(first)).endswith("previous audit: +2.5")


def test_the_coverage_line_of_the_previous_audit_is_not_read_as_the_mutation_score(repo, tmp_path):
    configure(repo, mutation="echo 60")
    change_code(repo, "app/a.py")
    path = tmp_path / "previous.md"
    path.write_text(
        f"- D9 coverage | {RULE} | covered 90%, change since the previous audit: unknown\n",
        encoding="utf-8",
    )
    assert mutation(repo.root, "--previous", str(path)).endswith("previous audit: unknown")


def test_a_previous_audit_without_a_score_leaves_the_change_unknown(repo, tmp_path):
    configure(repo, mutation="echo 60")
    change_code(repo, "app/a.py")
    for path in (previous(tmp_path, None), str(tmp_path / "missing.md")):
        assert mutation(repo.root, "--previous", path).endswith("previous audit: unknown")


# --- the changed code files (answer 1) ---------------------------------------------------------


def seen_list(repo, tmp_path) -> Path:
    seen = tmp_path / "seen.txt"
    configure(repo, mutation=f'cp "$AGK_CHANGED_FILES" {seen}; echo 50')
    return seen


def test_the_command_reads_the_changed_code_files_by_name(repo, tmp_path):
    seen = seen_list(repo, tmp_path)
    change_code(repo, "src/z.py", "app/b.py", days_ago=2)
    change_code(repo, "app/a.py", days_ago=1)
    audit(repo.root)
    assert seen.read_text(encoding="utf-8").splitlines() == ["app/a.py", "app/b.py", "src/z.py"]


def test_the_list_holds_at_most_20_files_the_first_by_name(repo, tmp_path):
    seen = seen_list(repo, tmp_path)
    change_code(repo, *[f"app/m{i:02d}.py" for i in range(25)])
    sentence = mutation(repo.root)
    listed = seen.read_text(encoding="utf-8").splitlines()
    assert listed == [f"app/m{i:02d}.py" for i in range(20)]
    assert "in 20 files" in sentence


def test_documents_tests_deleted_files_and_older_changes_are_not_listed(repo, tmp_path):
    seen = seen_list(repo, tmp_path)
    change_code(repo, "app/old.py", days_ago=20)
    repo.write("docs/guide.md", "words\n")
    repo.write("README.md", "words\n")
    repo.write("tests/test_new.py", '"""REQ-001 AC1"""\n')
    change_code(repo, "app/kept.py", "app/gone.py", days_ago=2)
    (repo.root / "app" / "gone.py").unlink()
    repo.commit(1, "remove a file")
    audit(repo.root)
    assert seen.read_text(encoding="utf-8").splitlines() == ["app/kept.py"]


def test_the_list_file_is_outside_the_checkout_and_removed_after_the_run(repo, tmp_path):
    where = tmp_path / "where.txt"
    configure(repo, mutation=f'echo "$AGK_CHANGED_FILES" > {where}; echo 50')
    change_code(repo, "app/a.py")
    before = fx.snapshot(repo.root)
    audit(repo.root)
    assert fx.snapshot(repo.root) == before
    path = Path(where.read_text(encoding="utf-8").strip())
    assert path.is_absolute() and repo.root not in path.parents
    assert not path.exists()


# --- no number, a failure, no changed file (answers 2, 3 and 5) --------------------------------


@pytest.mark.parametrize(
    "command",
    ["echo 81; exit 1", "true", "echo fine", "echo 81.5; echo done", "echo 101", "exit 3"],
)
def test_no_number_or_a_failing_command_reads_unknown_and_is_listed(repo, command):
    configure(repo, mutation=command)
    change_code(repo, "app/a.py")
    sentence = mutation(repo.root)
    assert sentence.startswith("unknown") and "killed" not in sentence
    proc = audit(repo.root)
    assert proc.returncode == 0


def test_a_command_that_runs_too_long_reads_unknown_naming_the_setting(repo):
    repo.write("agk.toml", BASE_TOML + "proof_timeout = 1\nmutation = 'sleep 5; echo 90'\n")
    repo.commit(30)
    change_code(repo, "app/a.py")
    sentence = mutation(repo.root)
    assert sentence.startswith("unknown") and "proof_timeout" in sentence


def test_no_changed_code_file_means_the_command_is_not_run_and_the_line_says_so(repo, tmp_path):
    ran = tmp_path / "ran"
    configure(repo, mutation=f"touch {ran}; echo 50")
    repo.write("docs/only.md", "words\n")
    repo.commit(1, "docs only")
    assert mutation(repo.root) == NOT_RUN
    assert not ran.exists()


def test_a_set_command_always_gives_the_report_a_finding_so_the_issue_is_written(repo):
    configure(repo, mutation="exit 1")
    assert audit(repo.root, "--print-action", "--open-issues", "7").stdout.strip() == "update 7"


# --- what the report never does ----------------------------------------------------------------


def test_the_report_never_shows_the_command(repo):
    canary = "COMMAND-TEXT-NOT-TO-BE-ECHOED"
    configure(repo, mutation=f"echo 50 # {canary}")
    change_code(repo, "app/a.py")
    assert canary not in audit(repo.root).stdout
    assert mutation(repo.root).startswith("killed 50%")


def test_only_the_report_run_starts_the_command(repo, tmp_path):
    ran = tmp_path / "ran"
    configure(repo, mutation=f"touch {ran}; echo 50")
    change_code(repo, "app/a.py")
    assert audit(repo.root, "--print-action").stdout.strip() == "create"
    drift_audit.audit(repo.root, fx.TODAY, "main", [])
    assert not ran.exists()
    audit(repo.root)
    assert ran.exists()


def test_the_three_lines_sort_by_setting_name(repo):
    configure(repo, unused_code="echo z.py: unused", coverage="echo 50", mutation="echo 40")
    change_code(repo, "app/a.py")
    lines = [ln for ln in audit(repo.root).stdout.splitlines() if ln.startswith("- D9")]
    assert [ln.split()[2] for ln in lines] == ["coverage", "mutation", "unused_code"]


# --- the guide and the amendment (answers 4 and 6) ---------------------------------------------


def test_the_testing_guide_names_the_setting_with_an_invented_example():
    text = (ROOT / "docs" / "guides" / "testing.md").read_text(encoding="utf-8")
    assert "mutation" in text and "AGK_CHANGED_FILES" in text
    assert "never blocking" in text and "installs none" in text


def test_the_spec_amendment_names_the_mutation_line_under_rule_25():
    text = (ROOT / "docs" / "runs" / "proposed-spec-amendments-106.md").read_text(encoding="utf-8")
    assert text.startswith("# Proposed spec amendments 106 (SPEC-0004; REQ-011)")
    assert "rule 25" in text and "killed <n>% of injected faults in <k> files" in text
    assert "ADR-0240" in text
