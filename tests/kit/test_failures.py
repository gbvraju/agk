"""The failure signature, the cleaned evidence and the `[failures]` setting (SPEC-0046 rules 2, 3, 5).

REQ-053 AC1 and AC2, brief #634 (build (b) of SPEC-0046, ADR-0303). `config.failures_settings`
reads the optional `[failures]` table; `failures.py signature`, `evidence` and `issue-body` read
files, print and write nothing. Fixtures in `tmp_path`, saved issue lists, invented data
(`example.com`), no network. The tests were written first (answer 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
import failures

ODD = "zz-odd-zz"  # an invented value that a refusal must never echo
JUNIT = """<?xml version="1.0"?><testsuites><testsuite name="pytest">
<testcase classname="tests.test_shop" name="test_cart" time="0.1"/>
<testcase classname="tests.test_shop.TestPay" name="test_card[2]" time="0.2">
<failure message="AssertionError: assert 3 == 4">trace</failure></testcase>
</testsuite></testsuites>"""
SUMMARY = (
    "tests/test_shop.py::test_cart PASSED\n"
    "FAILED tests/test_shop.py::TestPay::test_card[2] - AssertionError: assert 3 == 4\n"
)


def project(tmp_path: Path, text: str, monkeypatch) -> Path:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write(tmp_path: Path, name: str, text: str) -> str:
    (tmp_path / name).write_text(text, encoding="utf-8")
    return str(tmp_path / name)


# --- rule 2: the setting --------------------------------------------------------------------------


def test_no_table_is_off(tmp_path, monkeypatch):
    """REQ-053 AC1: rule 2, without the table nothing is on."""
    root = project(tmp_path, 'default_branch = "main"\n', monkeypatch)
    assert config.failures_settings(root) == {"issues": False, "artifacts": False, "artifact_paths": []}


def test_a_full_table_is_read(tmp_path, monkeypatch):
    """REQ-053 AC1: rule 2, the three keys."""
    text = '[failures]\nissues = true\nartifacts = true\nartifact_paths = ["shots/*.png"]\n'
    root = project(tmp_path, text, monkeypatch)
    assert config.failures_settings(root) == {
        "issues": True, "artifacts": True, "artifact_paths": ["shots/*.png"]
    }


@pytest.mark.parametrize(
    ("body", "setting"),
    [
        (f'issues = "{ODD}"', "failures.issues"),
        (f'artifacts = "{ODD}"', "failures.artifacts"),
        (f'artifact_paths = "{ODD}"', "failures.artifact_paths"),
        (f'artifact_paths = ["/{ODD}"]', "failures.artifact_paths"),
        (f'artifact_paths = ["../{ODD}"]', "failures.artifact_paths"),
        (f'{ODD.replace("-", "_")} = true', "failures"),
    ],
)
def test_a_malformed_table_is_refused_naming_the_setting(tmp_path, monkeypatch, body, setting):
    """REQ-053 AC1: rule 2, refused naming the setting, never the value."""
    root = project(tmp_path, f"[failures]\n{body}\n", monkeypatch)
    with pytest.raises(config.FailuresSettingError) as exc:
        config.failures_settings(root)
    assert f"(setting: {setting})" in str(exc.value)
    assert ODD not in str(exc.value) and ODD.replace("-", "_") not in str(exc.value)


@pytest.mark.parametrize("text", ['default_branch = "main"\n', "[failures]\nissues = false\n"])
def test_off_opens_nothing(tmp_path, monkeypatch, capsys, text):
    """REQ-053 AC1: rule 2, no table and `issues = false` open nothing."""
    project(tmp_path, text, monkeypatch)
    assert failures.main(["issue-body", "--signature", "0" * 12, "--test", "t::a"]) == 0
    assert capsys.readouterr().out == "action: none (setting: failures.issues)\n"


# --- rule 3: the signature ------------------------------------------------------------------------


def test_junit_and_summary_give_the_same_test_ids(tmp_path, monkeypatch):
    """REQ-053 AC1: rule 3, one JUnit report and one runner summary."""
    project(tmp_path, '[testing]\njunit = "report.xml"\n', monkeypatch)
    out = write(tmp_path, "out.txt", SUMMARY)
    from_summary = failures.failed_tests(SUMMARY, None)
    write(tmp_path, "report.xml", JUNIT)
    from_junit = failures.failed_tests(SUMMARY, tmp_path / "report.xml")
    assert [t for t, _ in from_junit] == [t for t, _ in from_summary]
    assert from_junit[0][0] == "tests/test_shop.py::TestPay::test_card[2]"
    assert failures.main(["signature", "--output", out]) == 0


def test_one_failure_on_two_commits_gives_one_signature():
    """REQ-053 AC1: rule 3, other paths, shas, times and numbers normalise away."""
    one = "Error: /tmp/tmpab12cd/x.py at 2026-11-06T10:01:02Z sha 1a2b3c4d5e6f run 41"
    two = "error: /home/ci/tmpzz99yy/x.py at 2026-11-07T23:59:59Z sha 9f8e7d6c5b4a run 7"
    assert failures.normalise(one) == failures.normalise(two)
    assert failures.normalise(one) == "error: <path> at <time> sha <hex> run <n>"
    assert failures.signature("t::a", one) == failures.signature("t::a", two)
    assert len(failures.signature("t::a", one)) == 12
    assert failures.normalise("x" * 300) == "x" * 200


def test_two_first_lines_give_two_signatures():
    """REQ-053 AC1: rule 3."""
    assert failures.signature("t::a", "keyerror: cart") != failures.signature("t::a", "valueerror")


def test_a_step_with_no_test_id(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 3, a failed step with no readable test id is `step:<name>`."""
    project(tmp_path, 'default_branch = "main"\n', monkeypatch)
    out = write(tmp_path, "out.txt", "building\nError: lint found 3 problems\n")
    assert failures.main(["signature", "--output", out, "--step", "lint"]) == 0
    sig = failures.signature("step:lint", "Error: lint found 3 problems")
    assert capsys.readouterr().out == f"{sig} step:lint\n"


def saved(tmp_path: Path, issues: list[dict]) -> str:
    return write(tmp_path, "issues.json", json.dumps(issues))


def issue(number: int, state: str, sig: str) -> dict:
    return {
        "number": number, "state": state, "labels": [{"name": "found-bug"}],
        "body": f"Failure-signature: {sig}\nTest: t::a\n",
    }


def test_an_open_issue_gets_a_comment_and_no_second_issue(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 3."""
    project(tmp_path, "[failures]\nissues = true\n", monkeypatch)
    sig = "a1" * 6
    path = saved(tmp_path, [issue(9, "closed", sig), issue(12, "open", sig)])
    assert failures.main(["issue-body", "--signature", sig, "--test", "t::a", "--issues", path]) == 0
    assert capsys.readouterr().out == "action: comment #12\n"


def test_a_closed_issue_gives_a_new_issue_naming_it(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 3, never reopened; the new issue names the old one as seen before."""
    project(tmp_path, "[failures]\nissues = true\n", monkeypatch)
    sig = "b2" * 6
    path = saved(tmp_path, [issue(5, "closed", sig), issue(8, "closed", "c3" * 6)])
    assert failures.main(["issue-body", "--signature", sig, "--test", "t::a", "--issues", path]) == 0
    assert capsys.readouterr().out == (
        f"action: open\nFailure-signature: {sig}\nTest: t::a\nseen before: #5\n"
    )


# --- rule 5: the evidence -------------------------------------------------------------------------


def evidence(tmp_path, monkeypatch, capsys, text: str, toml: str = "") -> str:
    project(tmp_path, toml or 'default_branch = "main"\n', monkeypatch)
    assert failures.main(["evidence", "--output", write(tmp_path, "out.txt", text)]) == 0
    return capsys.readouterr().out


def test_evidence_with_an_example_address_passes(tmp_path, monkeypatch, capsys):
    """REQ-053 AC2: rule 5."""
    text = "E   assert user == 'dev@example.com'\n"
    assert evidence(tmp_path, monkeypatch, capsys, text) == text


def test_a_planted_token_is_redacted(tmp_path, monkeypatch, capsys):
    """REQ-053 AC2: rule 5, the log reader redacts, then the scan finds nothing."""
    planted = "ghp_" + "a1B2c3D4e5" * 4
    out = evidence(tmp_path, monkeypatch, capsys, f"E   sent {planted}\n")
    assert planted not in out and "[SECRET-1]" in out


def test_text_that_still_has_a_finding_is_withheld_with_counts(tmp_path, monkeypatch, capsys):
    """REQ-053 AC2: rule 5, a finding after redaction withholds the whole text."""
    planted = "ghp_" + "a1B2c3D4e5" * 4
    toml = '[guard]\npatterns = [{ name = "label", regex = "SECRET-[0-9]" }]\n'
    out = evidence(tmp_path, monkeypatch, capsys, f"E   sent {planted}\n", toml)
    assert out == "evidence withheld: CUSTOM-label 1\n"


def test_text_over_the_limit_is_withheld(tmp_path, monkeypatch, capsys):
    """REQ-053 AC2: rule 5, at most 60,000 characters."""
    out = evidence(tmp_path, monkeypatch, capsys, ("x" * 400 + "\n") * 199)
    assert out == "evidence withheld: too long\n"


def test_only_the_last_200_lines_of_the_test_section(tmp_path, monkeypatch, capsys):
    """REQ-053 AC2: rule 5, that test's failure output, its last 200 lines, never the raw log."""
    body = "".join(f"line {i}\n" for i in range(250))
    text = f"____ TestPay.test_card[2] ____\n{body}____ test_other ____\nother\n= 1 failed =\n"
    project(tmp_path, 'default_branch = "main"\n', monkeypatch)
    path = write(tmp_path, "out.txt", text)
    test_id = "tests/test_shop.py::TestPay::test_card[2]"
    assert failures.main(["evidence", "--output", path, "--test", test_id]) == 0
    out = capsys.readouterr().out
    assert out.splitlines() == [f"line {i}" for i in range(50, 250)]


def test_nothing_is_written(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1 and AC2: rules 3 and 5, the commands read files, print and write nothing."""
    project(tmp_path, "[failures]\nissues = true\n", monkeypatch)
    out = write(tmp_path, "out.txt", SUMMARY)
    before = sorted(p.name for p in tmp_path.iterdir())
    failures.main(["signature", "--output", out])
    failures.main(["evidence", "--output", out])
    failures.main(["issue-body", "--signature", "d4" * 6, "--test", "t::a"])
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_a_usage_error_names_the_option(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: an unreadable output file exits 2, naming the option and not the path."""
    project(tmp_path, 'default_branch = "main"\n', monkeypatch)
    assert failures.main(["signature", "--output", str(tmp_path / ODD)]) == 2
    out = capsys.readouterr().out
    assert "(option: --output)" in out and ODD not in out
