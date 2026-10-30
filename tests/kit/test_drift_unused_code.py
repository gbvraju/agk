"""The optional unused-code and coverage commands of the weekly audit (REQ-039, brief 244 build b).

SPEC-0004 rule 25 (amendment 87, ADR-0177): two settings of `agk.toml`, `unused_code` and
`coverage`, empty by default, each a shell command like `project_tests`. When one is set, the report
run of the drift audit runs it and adds one finding D9 for it: the unused-code lines, capped, with
the count; the coverage number with its change since the previous audit. They never block. A
command that fails or prints nothing readable reads `unknown`, never zero, and the report never
shows the command itself. The kit ships no tool and installs none."""

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


@pytest.fixture
def repo(tmp_path):
    return fx.base(tmp_path / "repo")


def configure(repo, **settings: str) -> None:
    text = BASE_TOML + "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    repo.write("agk.toml", text)
    repo.commit(1)


def d9(root, *extra: str) -> dict[str, tuple[str, str]]:
    """subject -> (rule, sentence) of the D9 findings."""
    return {f[1]: (f[2], f[3]) for f in findings(root, *extra) if f[0] == "D9"}


def summary_d9(root, *extra: str) -> str:
    match = SUMMARY.match(audit(root, *extra).stdout.splitlines()[0])
    assert match
    return match.group(13)


# --- the settings (answer 5) --------------------------------------------------------------------


def test_both_settings_are_empty_by_default():
    assert common.DEFAULT_CONFIG["unused_code"] == ""
    assert common.DEFAULT_CONFIG["coverage"] == ""


@pytest.mark.parametrize(
    "rel", ["agk.toml", "kit/templates/agk.toml", "kit/templates/agk.adopt.toml"]
)
def test_every_shipped_configuration_names_both_settings_empty(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert re.search(r'^unused_code = ""$', text, flags=re.M)
    assert re.search(r'^coverage = ""$', text, flags=re.M)


def test_the_settings_are_read_from_agk_toml(repo):
    configure(repo, unused_code="echo one", coverage="echo 50")
    cfg = common.load_config(repo.root)
    assert cfg["unused_code"] == "echo one" and cfg["coverage"] == "echo 50"


# --- no setting: no finding (answer 8) -----------------------------------------------------------


def test_with_no_setting_there_is_no_finding_and_the_summary_counts_zero(repo):
    assert d9(repo.root) == {}
    assert summary_d9(repo.root) == "0"


def test_an_empty_setting_is_no_setting(repo):
    configure(repo, unused_code="  ", coverage="")
    assert d9(repo.root) == {}


# --- unused code (answers 5, 6 and 8) ----------------------------------------------------------


def test_the_unused_code_lines_are_listed_with_their_count(repo):
    configure(repo, unused_code=r'printf "a.py:1: unused x\nb.py:2: unused y\n"')
    found = d9(repo.root)
    rule, sentence = found["unused_code"]
    assert rule == RULE
    assert sentence == "2 unused-code findings: a.py:1: unused x; b.py:2: unused y"
    assert summary_d9(repo.root) == "1"


def test_the_listing_is_capped_and_says_how_many_more(repo):
    configure(repo, unused_code='for i in $(seq 1 25); do echo "f$i.py: unused"; done')
    _, sentence = d9(repo.root)["unused_code"]
    assert sentence.startswith("25 unused-code findings: f1.py: unused; ")
    assert "f20.py: unused and 5 more" in sentence and "f21.py" not in sentence


def test_one_line_reads_in_the_singular(repo):
    configure(repo, unused_code="echo only.py: unused")
    assert d9(repo.root)["unused_code"][1] == "1 unused-code finding: only.py: unused"


def test_a_tool_that_exits_non_zero_on_findings_still_lists_them(repo):
    """The usual tools signal findings by their exit code (ADR-0177 reading)."""
    configure(repo, unused_code="echo x.py: unused; exit 3")
    assert d9(repo.root)["unused_code"][1] == "1 unused-code finding: x.py: unused"


def test_the_error_stream_is_not_read_as_findings(repo):
    configure(repo, unused_code="echo noise >&2; echo y.py: unused")
    assert d9(repo.root)["unused_code"][1] == "1 unused-code finding: y.py: unused"


@pytest.mark.parametrize(
    "command", ["exit 1", "echo only-noise >&2; exit 2", "no-such-tool-anywhere --x"]
)
def test_a_failing_command_that_prints_no_line_reads_unknown_never_zero(repo, command):
    configure(repo, unused_code=command)
    _, sentence = d9(repo.root)["unused_code"]
    assert sentence.startswith("unknown")
    assert not re.search(r"\b0\b", sentence)


def test_a_clean_run_that_exits_0_and_prints_nothing_reads_zero(repo):
    """Q-U244-1, answered by the conductor on #313: a tool that finds nothing exits 0."""
    configure(repo, unused_code="true")
    assert d9(repo.root)["unused_code"][1] == "0 unused-code findings (the command exited 0)"


def test_a_project_that_has_not_opted_in_is_not_failed_by_another_setting(repo):
    """Verdict on e67c989, item 1: with no command set, `proof_timeout` is never read."""
    repo.write("agk.toml", BASE_TOML + "proof_timeout = 0\n")
    repo.commit(1)
    proc = audit(repo.root)
    assert proc.returncode == 0, proc.stdout
    assert summary_d9(repo.root) == "0"


# --- coverage (answers 5, 6 and 8) ---------------------------------------------------------------


def previous(tmp_path, covered: str | None) -> str:
    """A previous audit report as the open audit issue holds it."""
    line = f"- D9 coverage | {RULE} | covered {covered}%, change since the previous audit: unknown"
    body = "agk drift audit 2026-10-08 (window 2026-10-01 to 2026-10-08): findings=1\n\n"
    body += (line if covered is not None else "No findings.") + "\n"
    path = tmp_path / "previous.md"
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_the_coverage_number_is_read_from_the_last_line(repo):
    configure(repo, coverage=r'printf "Name Stmts Miss Cover\nTOTAL 200 37 81.5%%\n81.5\n"')
    rule, sentence = d9(repo.root)["coverage"]
    assert rule == RULE
    assert sentence == "covered 81.5%, change since the previous audit: unknown"


def test_a_percent_sign_on_the_last_line_is_accepted(repo):
    configure(repo, coverage="echo 77%")
    assert d9(repo.root)["coverage"][1].startswith("covered 77%")


def test_the_change_is_computed_from_the_previous_audit(repo, tmp_path):
    configure(repo, coverage="echo 81.5")
    up = d9(repo.root, "--previous", previous(tmp_path, "80"))["coverage"][1]
    assert up == "covered 81.5%, change since the previous audit: +1.5"
    configure(repo, coverage="echo 79.25")
    down = d9(repo.root, "--previous", previous(tmp_path, "80"))["coverage"][1]
    assert down.endswith("change since the previous audit: -0.75")


def test_a_real_report_fed_back_as_previous_gives_the_change(repo, tmp_path):
    """The line the report writes is the line the next audit reads (format kept in step)."""
    configure(repo, coverage="echo 70")
    first = tmp_path / "first.md"
    first.write_text(audit(repo.root).stdout, encoding="utf-8")
    configure(repo, coverage="echo 72.5")
    sentence = d9(repo.root, "--previous", str(first))["coverage"][1]
    assert sentence == "covered 72.5%, change since the previous audit: +2.5"


def test_a_previous_audit_without_a_number_leaves_the_change_unknown(repo, tmp_path):
    configure(repo, coverage="echo 60")
    for path in (previous(tmp_path, None), str(tmp_path / "missing.md")):
        sentence = d9(repo.root, "--previous", path)["coverage"][1]
        assert sentence == "covered 60%, change since the previous audit: unknown"


def test_a_previous_unknown_coverage_leaves_the_change_unknown(repo, tmp_path):
    configure(repo, coverage="echo 60")
    path = tmp_path / "previous.md"
    path.write_text(f"- D9 coverage | {RULE} | unknown: the command failed\n", encoding="utf-8")
    assert d9(repo.root, "--previous", str(path))["coverage"][1].endswith("audit: unknown")


@pytest.mark.parametrize(
    "command",
    ["echo 81; exit 1", "true", "echo fine", "echo 81.5; echo done", "echo 101", "echo -3"],
)
def test_a_failing_or_unreadable_coverage_command_reads_unknown(repo, command):
    configure(repo, coverage=command)
    _, sentence = d9(repo.root)["coverage"]
    assert sentence.startswith("unknown") and "covered" not in sentence


def test_a_command_that_runs_too_long_reads_unknown_naming_the_setting(repo):
    repo.write("agk.toml", BASE_TOML + "proof_timeout = 1\ncoverage = 'sleep 5; echo 90'\n")
    repo.commit(1)
    _, sentence = d9(repo.root)["coverage"]
    assert sentence.startswith("unknown") and "proof_timeout" in sentence


# --- what the report never does ----------------------------------------------------------------


def test_the_report_never_shows_the_command(repo):
    canary = "COMMAND-TEXT-NOT-TO-BE-ECHOED"
    configure(repo, unused_code=f"true {canary}", coverage=f"echo 50 # {canary}")
    out = audit(repo.root).stdout
    assert canary not in out
    assert set(d9(repo.root)) == {"unused_code", "coverage"}


def test_both_findings_sort_after_the_others_and_the_report_still_ends_with_the_marker(repo):
    configure(repo, unused_code="echo z.py: unused", coverage="echo 50")
    lines = audit(repo.root).stdout.rstrip("\n").splitlines()
    finding_lines = [ln for ln in lines if ln.startswith("- D")]
    assert finding_lines[-2].startswith("- D9 coverage") and finding_lines[-1].startswith(
        "- D9 unused_code"
    )
    assert lines[-1] == "<!-- agk-drift-audit -->"
    assert summary_d9(repo.root) == "2"


def test_only_the_report_run_starts_the_commands(repo):
    """The action and the title come from the settings alone; the facts never run a command."""
    configure(repo, unused_code="touch ran-unused; echo a.py: unused", coverage="touch ran-cov")
    assert audit(repo.root, "--print-action").stdout.strip() == "create"
    assert audit(repo.root, "--print-title").returncode == 0
    drift_audit.audit(repo.root, fx.TODAY, "main", [])
    assert not (repo.root / "ran-unused").exists() and not (repo.root / "ran-cov").exists()
    audit(repo.root)
    assert (repo.root / "ran-unused").exists() and (repo.root / "ran-cov").exists()


def test_without_a_setting_a_clean_repository_still_asks_for_no_issue(repo):
    assert audit(repo.root, "--print-action").stdout.strip() == "none"


def test_a_set_command_always_gives_the_report_a_finding_so_the_issue_is_written(repo):
    configure(repo, coverage="exit 1")
    assert audit(repo.root, "--print-action", "--open-issues", "7").stdout.strip() == "update 7"


# --- the workflow and the guide (answers 5 and 6) -----------------------------------------------


def test_the_workflow_hands_the_previous_report_to_the_audit_with_a_read_only_call():
    text = (ROOT / ".github" / "workflows" / "drift-audit.yml").read_text(encoding="utf-8")
    assert "--previous" in text
    reads = [ln for ln in text.splitlines() if "--json number,body" in ln]
    assert reads and all("gh issue list" in ln for ln in reads)


def test_the_guide_gives_examples_for_two_languages_and_says_the_kit_installs_none():
    text = (ROOT / "docs" / "guides" / "existing-codebase.md").read_text(encoding="utf-8")
    assert "unused_code" in text and "coverage" in text
    assert "vulture" in text and "knip" in text
    assert "installs none" in text and "unknown" in text
