"""The failure signature, the cleaned evidence and the `[failures]` setting (SPEC-0046 2, 3, 5).

REQ-053 AC1 and AC2, brief #634 (build (b) of SPEC-0046, ADR-0303). `config.failures_settings`
reads the optional `[failures]` table; `failures.py signature`, `evidence` and `issue-body` read
files, print and write nothing. Fixtures in `tmp_path`, saved issue lists, invented data
(`example.com`), no network. The tests were written first (answer 2)."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import failures
import pytest

import config

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
    assert config.failures_settings(root) == {
        "issues": False,
        "artifacts": False,
        "artifact_paths": [],
    }


def test_a_full_table_is_read(tmp_path, monkeypatch):
    """REQ-053 AC1: rule 2, the three keys."""
    text = '[failures]\nissues = true\nartifacts = true\nartifact_paths = ["shots/*.png"]\n'
    root = project(tmp_path, text, monkeypatch)
    assert config.failures_settings(root) == {
        "issues": True,
        "artifacts": True,
        "artifact_paths": ["shots/*.png"],
    }


@pytest.mark.parametrize(
    ("body", "setting"),
    [
        (f'issues = "{ODD}"', "failures.issues"),
        (f'artifacts = "{ODD}"', "failures.artifacts"),
        (f'artifact_paths = "{ODD}"', "failures.artifact_paths"),
        (f'artifact_paths = ["/{ODD}"]', "failures.artifact_paths"),
        (f'artifact_paths = ["../{ODD}"]', "failures.artifact_paths"),
        (f"{ODD.replace('-', '_')} = true", "failures"),
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
        "number": number,
        "state": state,
        "labels": [{"name": "found-bug"}],
        "body": f"Failure-signature: {sig}\nTest: t::a\n",
    }


def test_an_open_issue_gets_a_comment_and_no_second_issue(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 3."""
    project(tmp_path, "[failures]\nissues = true\n", monkeypatch)
    sig = "a1" * 6
    path = saved(tmp_path, [issue(9, "closed", sig), issue(12, "open", sig)])
    assert (
        failures.main(["issue-body", "--signature", sig, "--test", "t::a", "--issues", path]) == 0
    )
    assert capsys.readouterr().out == "action: comment #12\n"


def test_a_closed_issue_gives_a_new_issue_naming_it(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 3, never reopened; the new issue names the old one as seen before."""
    project(tmp_path, "[failures]\nissues = true\n", monkeypatch)
    sig = "b2" * 6
    path = saved(tmp_path, [issue(5, "closed", sig), issue(8, "closed", "c3" * 6)])
    assert (
        failures.main(["issue-body", "--signature", sig, "--test", "t::a", "--issues", path]) == 0
    )
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


# --- rules 6 and 13: the evidence folder (brief #768, build (h)) ----------------------------------

SIG = "ab" * 6
OTHER = "cd" * 6
SHOTS = '[failures]\nartifact_paths = ["shots/*.png", "traces/**/*.zip"]\n'


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


def evidence_tree(tmp_path: Path, monkeypatch, ignored: bool = True) -> Path:
    """A git work tree with a run folder: two screenshots, a trace and a file nothing matches."""
    root = tmp_path / "work"
    (root / "run" / "shots").mkdir(parents=True)
    (root / "run" / "traces" / "a").mkdir(parents=True)
    git(root, "init", "-q")
    (root / "agk.toml").write_text(SHOTS, encoding="utf-8")
    (root / ".gitignore").write_text(".agk-failures/\n" if ignored else "", encoding="utf-8")
    (root / "run" / "shots" / "one.png").write_text("one", encoding="utf-8")
    (root / "run" / "shots" / "two.png").write_text("two", encoding="utf-8")
    (root / "run" / "shots" / "notes.txt").write_text("https://example.com/", encoding="utf-8")
    (root / "run" / "traces" / "a" / "t.zip").write_text("trace", encoding="utf-8")
    monkeypatch.chdir(root)
    return root


def stored(root: Path, sig: str = SIG) -> list[str]:
    base = root / ".agk-failures" / sig
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())


def copy_files(sig: str = SIG, source: str = "run") -> int:
    return failures.main(["files", "--signature", sig, "--from", source])


def issue_list(tmp_path: Path, *sigs: str, state: str = "open") -> str:
    issues = [
        {
            "number": n,
            "state": state,
            "labels": [{"name": "found-bug"}],
            "body": f"Failure-signature: {sig}\nTest: t::a",
        }
        for n, sig in enumerate(sigs, 1)
    ]
    return write(tmp_path, "issues.json", json.dumps(issues))


def test_only_the_matched_files_are_copied(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3 and AC8: rule 13, what `artifact_paths` matches and nothing else."""
    root = evidence_tree(tmp_path, monkeypatch)
    assert copy_files() == 0
    assert stored(root) == ["shots/one.png", "shots/two.png", "traces/a/t.zip"]
    assert (root / "run" / "shots" / "one.png").exists()  # copied, not moved


def test_the_printed_path_names_no_user(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, the folder is named only by its relative path."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    out = capsys.readouterr().out
    assert out.strip() == f"files: 3 copied to .agk-failures/{SIG}/"
    assert str(root) not in out and str(tmp_path) not in out


def test_the_folder_is_at_the_top_of_the_work_tree(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, from a subfolder the evidence still lands at the top."""
    root = evidence_tree(tmp_path, monkeypatch)
    monkeypatch.chdir(root / "run")
    assert copy_files(source=".") == 0
    assert stored(root) == ["shots/one.png", "shots/two.png", "traces/a/t.zip"]
    assert not (root / "run" / ".agk-failures").exists()


def test_a_second_failure_replaces_the_folder(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, one folder per open failure and not per run."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    (root / "run" / "shots" / "two.png").unlink()
    (root / "run" / "shots" / "one.png").write_text("newer", encoding="utf-8")
    assert copy_files() == 0
    assert stored(root) == ["shots/one.png", "traces/a/t.zip"]
    assert (root / ".agk-failures" / SIG / "shots/one.png").read_text("utf-8") == "newer"


def test_earlier_evidence_is_never_copied_again(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, a pattern that reaches the folder does not feed it from itself."""
    root = evidence_tree(tmp_path, monkeypatch)
    (root / "agk.toml").write_text('[failures]\nartifact_paths = ["**/*.png"]\n', encoding="utf-8")
    copy_files(source=".")
    copy_files(OTHER, source=".")
    assert stored(root, OTHER) == ["run/shots/one.png", "run/shots/two.png"]


def test_a_folder_git_does_not_ignore_is_refused(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, the write is refused naming the path class, and nothing is made."""
    root = evidence_tree(tmp_path, monkeypatch, ignored=False)
    assert copy_files() == 2
    out = capsys.readouterr().out
    assert "path class: .agk-failures/" in out and str(root) not in out
    assert not (root / ".agk-failures").exists()


def test_a_pattern_python_cannot_read_is_refused(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 2, a bad pattern names the setting and leaves the folder as it was."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    capsys.readouterr()

    def refuse(*_args, **_kwargs):  # the pattern an older Python's glob refuses, on any Python
        raise ValueError

    monkeypatch.setattr(failures.Path, "glob", refuse)
    assert copy_files() == 2
    assert "setting: failures.artifact_paths" in capsys.readouterr().out
    assert len(stored(root)) == 3


def test_nothing_shows_in_git_status(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, the folder is never committed."""
    root = evidence_tree(tmp_path, monkeypatch)
    before = git(root, "status", "--porcelain", "--untracked-files=all")
    copy_files()
    assert git(root, "status", "--porcelain", "--untracked-files=all") == before


def test_without_artifact_paths_nothing_happens(tmp_path, monkeypatch, capsys):
    """REQ-053 AC1: rule 2, the default setting copies nothing and needs no ignore line."""
    root = evidence_tree(tmp_path, monkeypatch, ignored=False)
    (root / "agk.toml").write_text("[failures]\nissues = true\n", encoding="utf-8")
    assert copy_files() == 0
    assert capsys.readouterr().out.strip() == "files: none (setting: failures.artifact_paths)"
    assert not (root / ".agk-failures").exists()


def test_a_missing_run_folder_keeps_the_earlier_evidence(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: an unreadable --from is refused before anything is replaced."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    assert copy_files(source=ODD) == 2
    out = capsys.readouterr().out
    assert "(option: --from)" in out and ODD not in out
    assert len(stored(root)) == 3


def test_a_matched_link_is_not_followed(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, a link cannot pull a file from outside the run's folder."""
    root = evidence_tree(tmp_path, monkeypatch)
    outside = tmp_path / "outside.png"
    outside.write_text("private", encoding="utf-8")
    (root / "run" / "shots" / "link.png").symlink_to(outside)
    (root / "run" / "shots" / "dir").symlink_to(tmp_path, target_is_directory=True)
    assert copy_files() == 0
    assert stored(root) == ["shots/one.png", "shots/two.png", "traces/a/t.zip"]


def test_a_linked_evidence_folder_is_refused(tmp_path, monkeypatch, capsys):
    """REQ-053 AC8: rule 13, a link at `.agk-failures` never takes a write or a delete elsewhere."""
    root = evidence_tree(tmp_path, monkeypatch)
    away = tmp_path / "away"
    (away / SIG).mkdir(parents=True)
    (away / SIG / "kept.txt").write_text("kept", encoding="utf-8")
    (root / ".agk-failures").symlink_to(away, target_is_directory=True)
    assert copy_files() == 2
    assert failures.main(["files", "--delete", "--signature", SIG]) == 2
    assert "path class: .agk-failures/" in capsys.readouterr().out
    assert (away / SIG / "kept.txt").exists()


@pytest.mark.parametrize("bad", ["../../etc", "ABCDEF123456", "abc", ""])
def test_a_signature_that_is_no_signature_is_refused(tmp_path, monkeypatch, capsys, bad):
    """REQ-053 AC8: only a 12-hex signature names a folder, so no path can escape."""
    evidence_tree(tmp_path, monkeypatch)
    assert failures.main(["files", "--delete", "--signature", bad]) == 2
    assert copy_files(bad) == 2
    assert "(option: --signature)" in capsys.readouterr().out


def test_delete_removes_only_that_folder(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3: rule 13, the fixed failure's folder goes and nothing else does."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    copy_files(OTHER)
    capsys.readouterr()
    assert failures.main(["files", "--delete", "--signature", SIG]) == 0
    assert capsys.readouterr().out.strip() == f"files: deleted .agk-failures/{SIG}/"
    assert not (root / ".agk-failures" / SIG).exists()
    assert len(stored(root, OTHER)) == 3
    assert (root / "run" / "shots" / "one.png").exists()


def test_delete_of_a_missing_folder_is_quiet(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3: rule 13, a failure that left no folder has nothing to delete."""
    evidence_tree(tmp_path, monkeypatch)
    assert failures.main(["files", "--delete", "--signature", SIG]) == 0
    assert capsys.readouterr().out == ""


def test_prune_removes_folders_with_no_open_issue(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3: rule 13, every signature without an open `found-bug` issue goes."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    copy_files(OTHER)
    capsys.readouterr()
    listing = issue_list(tmp_path, OTHER)
    assert failures.main(["files", "--prune", "--issues", listing]) == 0
    assert capsys.readouterr().out.strip() == f"files: deleted .agk-failures/{SIG}/"
    assert not (root / ".agk-failures" / SIG).exists()
    assert len(stored(root, OTHER)) == 3


def test_prune_counts_only_open_found_bug_issues(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3: rule 13, a closed issue, another label or a pull request keeps nothing."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    body = f"Failure-signature: {SIG}"
    listing = write(
        tmp_path,
        "issues.json",
        json.dumps(
            [
                {"state": "closed", "labels": [{"name": "found-bug"}], "body": body},
                {"state": "open", "labels": [{"name": "other"}], "body": body},
                {
                    "state": "open",
                    "labels": [{"name": "found-bug"}],
                    "body": body,
                    "pull_request": {},
                },
            ]
        ),
    )
    assert failures.main(["files", "--prune", "--issues", listing]) == 0
    assert not (root / ".agk-failures" / SIG).exists()


def test_prune_touches_only_signature_folders(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3: rule 13, a link inside goes without its target; other names stay."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    away = tmp_path / "away"
    away.mkdir()
    (away / "kept.txt").write_text("kept", encoding="utf-8")
    (root / ".agk-failures" / OTHER).symlink_to(away, target_is_directory=True)
    (root / ".agk-failures" / "not-a-signature").mkdir()
    (root / ".agk-failures" / ("ef" * 6)).write_text("a stray file", encoding="utf-8")
    assert failures.main(["files", "--prune", "--issues", issue_list(tmp_path)]) == 0
    assert (away / "kept.txt").exists() and not (root / ".agk-failures" / OTHER).is_symlink()
    assert not (root / ".agk-failures" / SIG).exists()
    assert (root / ".agk-failures" / "not-a-signature").is_dir()
    assert not (root / ".agk-failures" / ("ef" * 6)).exists()
    assert (root / "run" / "shots" / "one.png").exists()


@pytest.mark.parametrize("text", ["not json", '{"message": "x"}', "[1]"])
def test_an_unreadable_issue_list_prunes_nothing(tmp_path, monkeypatch, capsys, text):
    """REQ-053 AC3: rule 13, a list that cannot be read never reads as no open issue."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    listing = write(tmp_path, "issues.json", text)
    assert failures.main(["files", "--prune", "--issues", listing]) == 2
    assert "(option: --issues)" in capsys.readouterr().out
    assert len(stored(root)) == 3


def test_prune_needs_the_issue_list(tmp_path, monkeypatch, capsys):
    """REQ-053 AC3: rule 13, no list is a usage error and no folder goes."""
    root = evidence_tree(tmp_path, monkeypatch)
    copy_files()
    assert failures.main(["files", "--prune"]) == 2
    assert failures.main(["files", "--prune", "--delete", "--signature", SIG]) == 2
    assert len(stored(root)) == 3


@pytest.mark.parametrize("name", ["kit/templates/gitignore", ".gitignore"])
def test_the_ignore_blocks_name_the_folder(name):
    """REQ-053 AC8: rule 13, `adopt.py`'s block and this repository's ignore the folder."""
    file = Path(__file__).resolve().parents[2] / name
    if not file.exists():
        pytest.skip("kit source file, absent in an installed project")
    assert ".agk-failures/" in file.read_text(encoding="utf-8").splitlines()
