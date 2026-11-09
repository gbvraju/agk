"""The run that stands in for CI when Actions is blocked (SPEC-0046 rules 12 and 14).

REQ-053 AC8, brief #888 (build (i) of SPEC-0046, ADR-0303). `failures.py run --on default|release`
runs the project's full command and reports through a `gh` stub on `PATH` serving saved responses:
each refusal runs nothing and writes nothing; a failure opens one issue and a second run comments
on it; a passing run closes it with its fix record; evidence the guard refuses is never posted.
No network, invented data (`example.com`). The tests were written first (answer 5)."""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import failures
import pytest

REPO = "acme/widgets"
TEST = "tests/test_shop.py::test_cart"
LINE = "AssertionError: assert 3 == 4"
SIG = failures.signature(TEST, LINE)
PLANTED = "zz-planted-zz"
STUB = '''#!/usr/bin/env python3
"""A gh stub: serves GET fixtures by endpoint (query ignored), logs every call and its input."""
import json, os, sys
args = sys.argv[1:]
root = os.environ["GH_STUB_DIR"]
method = args[args.index("--method") + 1] if "--method" in args else "GET"
endpoint = next(a for a in args[1:] if a.startswith("repos/"))
data = json.load(sys.stdin) if "--input" in args else None
with open(os.path.join(root, "calls.log"), "a") as log:
    log.write(json.dumps([method, endpoint, data]) + "\\n")
if method == "POST" and endpoint.endswith("/issues"):
    print(json.dumps({"number": 99}))
    sys.exit(0)
if method != "GET":
    print("{}")
    sys.exit(0)
fixtures = json.load(open(os.path.join(root, "fixtures.json")))
value = fixtures.get(endpoint.split("?")[0])
if value is None:
    sys.stderr.write("gh: Not Found (HTTP 404)\\n")
    sys.exit(1)
print(json.dumps(value))
'''
FAKE_TESTS = """import os, pathlib
pathlib.Path("ran.txt").write_text(str(os.environ.get("EVENT")))
outcome = os.environ["FAKE_OUTCOME"]
fail = '<failure message="{line}">trace</failure>'.format(line=os.environ["FAKE_LINE"])
body = fail if outcome == "fail" else ""
pathlib.Path("report.xml").write_text(
    '<testsuites><testsuite name="pytest">'
    '<testcase classname="tests.test_shop" name="test_cart">' + body + "</testcase>"
    "</testsuite></testsuites>"
)
print("___ test_cart ___")
print(os.environ["FAKE_PRINT"])
print("=== short test summary ===")
raise SystemExit(1 if outcome == "fail" else 0)
"""
SETTINGS = (
    'default_branch = "main"\nproject_tests = "python3 fake_tests.py"\nexecution = "local"\n'
    '[testing]\njunit = "report.xml"\n'
    '[failures]\nissues = true\nartifact_paths = ["shots/*.png"]\n'
)


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )
    return proc.stdout.strip()


def commit_all(root: Path, message: str = "x") -> None:
    git(root, "add", "-A")
    git(root, "-c", "user.name=a", "-c", "user.email=a@example.com", "commit", "-qm", message)


def failure_issue(number: int = 7, state: str = "open", sig: str = SIG, test: str = TEST) -> dict:
    return {
        "number": number,
        "state": state,
        "title": f"Failure: {test}",
        "labels": [{"name": "found-bug"}],
        "body": f"Failure-signature: {sig}\nTest: {test}",
    }


def fixing_pull(number: int = 12, fixes: int = 7) -> dict:
    record = (
        "Symptom: the cart total is off\nCause: discount applied twice\n"
        "Reproduce: run the cart test\nFixed-by: apply the discount once"
    )
    return {
        "number": number,
        "state": "closed",
        "merged_at": "2026-11-01T10:00:00Z",
        "body": f"Summary: fixes the cart\nFixes-failure: #{fixes}\n{record}",
    }


def settle(root: Path) -> None:
    """Commit the work tree and make it the default branch's head as last fetched."""
    commit_all(root)
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")


def set_toml(gh, text: str) -> None:
    (gh.root / "agk.toml").write_text(text, "utf-8")
    settle(gh.root)


class Gh:
    def __init__(self, stub: Path, root: Path, bin_dir: Path) -> None:
        self.dir, self.root, self.bin = stub, root, bin_dir
        self.fixtures: dict = {f"repos/{REPO}": {"full_name": REPO}}
        self.serve()

    def serve(self, issues: list | None = None, pulls: list | None = None, **more) -> None:
        self.fixtures[f"repos/{REPO}/issues"] = issues or []
        self.fixtures[f"repos/{REPO}/pulls"] = pulls or []
        self.fixtures.update(
            {f"repos/{REPO}/issues/{k[1:]}/comments": v for k, v in more.items()}
        )
        self.write()

    def write(self) -> None:
        (self.dir / "fixtures.json").write_text(json.dumps(self.fixtures), encoding="utf-8")

    def calls(self) -> list[list]:
        log = self.dir / "calls.log"
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    def writes(self) -> list[list]:
        return [c for c in self.calls() if c[0] != "GET"]


@pytest.fixture
def gh(tmp_path: Path, monkeypatch) -> Gh:
    stub, bin_dir, root = tmp_path / "stub", tmp_path / "bin", tmp_path / "proj"
    for folder in (stub, bin_dir, root):
        folder.mkdir()
    exe = bin_dir / "gh"
    exe.write_text(STUB, encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    git(root, "init", "-q", "-b", "main")
    git(root, "remote", "add", "origin", f"https://github.com/{REPO}.git")
    (root / "agk.toml").write_text(SETTINGS, encoding="utf-8")
    (root / "fake_tests.py").write_text(FAKE_TESTS, encoding="utf-8")
    (root / ".gitignore").write_text(".agk-failures/\nran.txt\nreport.xml\nshots/\n", "utf-8")
    settle(root)
    monkeypatch.chdir(root)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_STUB_DIR", str(stub))
    monkeypatch.setenv("EVENT", "pull_request")
    monkeypatch.setenv("FAKE_OUTCOME", "fail")
    monkeypatch.setenv("FAKE_LINE", LINE)
    monkeypatch.setenv("FAKE_PRINT", "see https://example.com/help")
    for name in ("CLAUDECODE", "GITHUB_REPOSITORY", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(name, raising=False)
    return Gh(stub, root, bin_dir)


def run(on: str = "default") -> int:
    return failures.main(["run", "--on", on])


def assert_refused(gh: Gh, capsys, named: str) -> None:
    assert run() == 2
    assert named in capsys.readouterr().out
    assert not (gh.root / "ran.txt").exists()
    assert not (gh.root / ".agk-failures").exists()
    assert gh.writes() == []


# --- rule 12: the refusals ----------------------------------------------------------------------


def test_refused_inside_an_agent_session(gh, capsys, monkeypatch):
    """REQ-053 AC8: an agent session runs nothing (Q-S0046-18)."""
    monkeypatch.setenv("CLAUDECODE", "1")
    assert_refused(gh, capsys, "rule 12")
    assert gh.calls() == []


def test_refused_in_a_personal_mode_sidecar(gh, capsys):
    """REQ-053 AC8: a sidecar is refused naming the setting (Q-S0046-20)."""
    text = (gh.root / "agk.toml").read_text("utf-8") + '[personal]\nforge = "files"\n'
    set_toml(gh, text)
    assert_refused(gh, capsys, "personal.forge")
    assert gh.calls() == []


def test_refused_on_a_dirty_work_tree(gh, capsys):
    """REQ-053 AC8: a dirty tree is refused, naming the rule."""
    (gh.root / "stray.txt").write_text("x", "utf-8")
    assert_refused(gh, capsys, "rule 12")


def test_refused_when_head_is_not_the_fetched_head(gh, capsys):
    """REQ-053 AC8: a head that is not the default branch's as last fetched is refused."""
    (gh.root / "new.txt").write_text("x", "utf-8")
    commit_all(gh.root)
    assert_refused(gh, capsys, "rule 12")


@pytest.mark.parametrize("how", ["404", "no connection"])
def test_refused_when_the_repository_does_not_answer(gh, capsys, how):
    """REQ-053 AC8: no 200 from the one GET runs nothing and writes nothing (rule 14)."""
    if how == "404":
        del gh.fixtures[f"repos/{REPO}"]
        gh.write()
    else:
        (gh.bin / "gh").unlink()
    assert_refused(gh, capsys, "rule 14")


@pytest.mark.parametrize("text", ['default_branch = "main"\n', "[failures]\nissues = false\n"])
def test_refused_with_the_setting_off(gh, capsys, text):
    """REQ-053 AC8: without `[failures] issues` the run is refused, naming the setting (rule 2)."""
    set_toml(gh, text)
    assert_refused(gh, capsys, "failures.issues")


def test_refused_while_ci_runs(gh, capsys):
    """REQ-053 AC8: with CI running rule 1's two runs report, so this one is refused (Q-888-1)."""
    text = (gh.root / "agk.toml").read_text("utf-8").replace('execution = "local"\n', "")
    set_toml(gh, text)
    assert_refused(gh, capsys, "rule 12")


def test_a_local_mode_record_issue_is_enough(gh):
    """REQ-053 AC8: the open record issue stands for `execution = "local"`."""
    text = (gh.root / "agk.toml").read_text("utf-8").replace('execution = "local"\n', "")
    set_toml(gh, text)
    gh.serve([{"number": 3, "state": "open", "title": "Local mode since 2026-11-01"}])
    assert run() == 1
    assert (gh.root / "ran.txt").exists()


def test_a_bad_option_runs_nothing(gh, capsys):
    """REQ-053 AC8: only `--on default|release` is accepted."""
    assert failures.main(["run", "--on", "zz-odd-zz"]) == 2
    assert "zz-odd-zz" not in capsys.readouterr().out
    assert not (gh.root / "ran.txt").exists()


# --- the run --------------------------------------------------------------------------------------


def posts(gh: Gh, suffix: str) -> list[dict]:
    return [c[2] for c in gh.writes() if c[0] == "POST" and c[1].endswith(suffix)]


def test_the_full_command_runs_with_event_unset(gh):
    """REQ-053 AC8: `EVENT` is unset, so the project's full command runs as for a push."""
    run()
    assert (gh.root / "ran.txt").read_text("utf-8") == "None"


def test_a_failing_run_opens_one_issue_with_evidence_in_a_comment(gh):
    """REQ-053 AC8: one `found-bug` issue; evidence in its own comment, never in the body."""
    assert run() == 1
    opened = posts(gh, f"repos/{REPO}/issues")
    assert len(opened) == 1
    assert opened[0]["labels"] == ["found-bug"]
    assert f"Failure-signature: {SIG}" in opened[0]["body"].splitlines()
    assert f"Test: {TEST}" in opened[0]["body"].splitlines()
    assert "example.com" not in opened[0]["body"]
    comments = posts(gh, "issues/99/comments")
    assert len(comments) == 1
    assert "example.com/help" in comments[0]["body"]
    assert git(gh.root, "rev-parse", "HEAD") in comments[0]["body"]


def test_the_same_failure_comments_and_opens_no_second_issue(gh):
    """REQ-053 AC8: an open issue of the signature gets one comment and no second issue."""
    gh.serve([failure_issue()])
    assert run() == 1
    assert posts(gh, f"repos/{REPO}/issues") == []
    assert len(posts(gh, "issues/7/comments")) == 1


def test_a_closed_issue_gives_a_new_issue_naming_it(gh):
    """REQ-053 AC1: a returning failure opens a new issue that names the closed one (rule 3)."""
    gh.serve([failure_issue(state="closed")])
    assert run() == 1
    assert "seen before: #7" in posts(gh, f"repos/{REPO}/issues")[0]["body"].splitlines()


def test_a_step_failure_with_no_test_id_is_not_dropped(gh, monkeypatch):
    """REQ-053 AC1: a red run with no test id reports `step:Project tests` (rule 3)."""
    text = (gh.root / "fake_tests.py").read_text("utf-8").replace('"report.xml"', '"other.xml"')
    (gh.root / "fake_tests.py").write_text(text, "utf-8")
    (gh.root / ".gitignore").write_text(".agk-failures/\nran.txt\nother.xml\n", "utf-8")
    settle(gh.root)
    assert run() == 1
    assert "Test: step:Project tests" in posts(gh, f"repos/{REPO}/issues")[0]["body"]


def test_evidence_the_guard_refuses_is_not_posted(gh, monkeypatch):
    """REQ-053 AC2: a finding left after redaction withholds the text, counts only (rule 5)."""
    text = (gh.root / "agk.toml").read_text("utf-8")
    text = text.replace("[testing]", f'[guard]\npatterns = [{{ name = "l", regex = "{PLANTED}" }}]\n[testing]')
    set_toml(gh, text)
    monkeypatch.setenv("FAKE_PRINT", f"user {PLANTED}")
    assert run() == 1
    assert PLANTED not in json.dumps(gh.writes())


def test_a_test_id_with_a_finding_is_withheld(gh, monkeypatch):
    """REQ-053 AC2: a test id the guard refuses is never posted; the failure still opens."""
    text = (gh.root / "agk.toml").read_text("utf-8")
    text = text.replace("[testing]", '[guard]\npatterns = [{ name = "l", regex = "test_cart" }]\n[testing]')
    set_toml(gh, text)
    assert run() == 1
    assert "test_cart" not in json.dumps(gh.writes())
    assert len(posts(gh, f"repos/{REPO}/issues")) == 1


def test_evidence_files_are_copied_and_named_by_relative_path(gh):
    """REQ-053 AC3: screenshots go to the ignored folder; the comment names only its path."""
    (gh.root / "shots").mkdir()
    (gh.root / "shots" / "one.png").write_text("image", "utf-8")
    assert run() == 1
    assert (gh.root / ".agk-failures" / SIG / "shots" / "one.png").is_file()
    assert git(gh.root, "status", "--porcelain") == ""
    body = posts(gh, "issues/99/comments")[0]["body"]
    assert f".agk-failures/{SIG}/" in body
    assert "the machine that ran this run" in body
    assert str(gh.root) not in body


def test_an_unignored_evidence_folder_is_refused_before_the_run(gh, capsys):
    """REQ-053 AC3: the folder not ignored by git is refused naming the path class (rule 13)."""
    (gh.root / ".gitignore").write_text("ran.txt\nreport.xml\nshots/\n", "utf-8")
    settle(gh.root)
    assert_refused(gh, capsys, ".agk-failures/")


# --- closing on green -----------------------------------------------------------------------------


def passing(gh: Gh, monkeypatch, issues: list | None = None, pulls: list | None = None) -> int:
    monkeypatch.setenv("FAKE_OUTCOME", "pass")
    comments = [
        {"id": 41, "body": f"Failure-evidence: {SIG}\ntext"},
        {"id": 42, "body": "a person's note"},
    ]
    gh.serve([failure_issue()] if issues is None else issues, pulls, n7=comments)
    return run()


def test_a_passing_run_closes_the_issue_with_its_record(gh, monkeypatch):
    """REQ-053 AC5: the record goes in the body, evidence comments go, the issue closes."""
    folder = gh.root / ".agk-failures" / SIG
    folder.mkdir(parents=True)
    assert passing(gh, monkeypatch, pulls=[fixing_pull()]) == 0
    patch = [c for c in gh.writes() if c[0] == "PATCH"]
    assert len(patch) == 1 and patch[0][1] == f"repos/{REPO}/issues/7"
    assert patch[0][2]["state"] == "closed" and patch[0][2]["state_reason"] == "completed"
    assert f"Failure-signature: {SIG}" in patch[0][2]["body"].splitlines()
    for line in ("Symptom:", "Cause:", "Reproduce:", "Fixed-by:"):
        assert any(ln.startswith(line) for ln in patch[0][2]["body"].splitlines())
    deleted = [c[1] for c in gh.writes() if c[0] == "DELETE"]
    assert deleted == [f"repos/{REPO}/issues/comments/41"]
    assert not folder.exists()


def test_a_closed_issue_is_readable_by_seen(gh, monkeypatch, capsys):
    """REQ-053 AC6: what the close writes is what `seen` reads back (rule 9)."""
    passing(gh, monkeypatch, pulls=[fixing_pull()])
    body = next(c for c in gh.writes() if c[0] == "PATCH")[2]["body"]
    closed = {**failure_issue(state="closed"), "body": body}
    capsys.readouterr()
    gh.serve([closed], [fixing_pull()])
    assert failures.main(["seen", "--signature", SIG, "--test", TEST]) == 0
    assert capsys.readouterr().out == "seen before: #7 the cart total is off; fixed by #12\n"


def test_no_fixing_pull_request_leaves_it_open(gh, monkeypatch, capsys):
    """REQ-053 AC5: no merged pull request names the issue: it stays open, one line says so."""
    assert passing(gh, monkeypatch) == 0
    assert gh.writes() == []
    assert "#7 stays open" in capsys.readouterr().out


def test_a_test_that_did_not_run_leaves_it_open(gh, monkeypatch):
    """REQ-053 AC5: an issue whose test is not in the report stays open."""
    other = failure_issue(sig="0123456789ab", test="tests/test_shop.py::test_other")
    assert passing(gh, monkeypatch, issues=[other], pulls=[fixing_pull()]) == 0
    assert gh.writes() == []


def test_a_red_run_closes_nothing(gh, monkeypatch):
    """REQ-053 AC5: a red run closes nothing, though another issue's test passed (Q-S0046-8)."""
    monkeypatch.setenv("FAKE_OUTCOME", "fail")
    other = failure_issue(number=8, sig="0123456789ab", test=TEST)
    gh.serve([other], [fixing_pull(fixes=8)])
    assert run() == 1
    assert [c for c in gh.writes() if c[0] == "PATCH"] == []


def test_a_folder_with_no_open_issue_is_pruned(gh, monkeypatch):
    """REQ-053 AC3: the next reporting run deletes a folder with no open issue (rule 13)."""
    stale = gh.root / ".agk-failures" / "0123456789ab"
    stale.mkdir(parents=True)
    assert run() == 1
    assert not stale.exists()


def test_a_failure_writes_the_same_signature_as_the_signature_command(gh, capsys):
    """REQ-053 AC8: the stand-in run and the CI path give one signature (rule 14)."""
    run()
    capsys.readouterr()
    assert f"Failure-signature: {SIG}" in posts(gh, f"repos/{REPO}/issues")[0]["body"]
    output = gh.root / "out.txt"
    output.write_text("", "utf-8")
    assert failures.main(["signature", "--output", str(output)]) == 0
    assert capsys.readouterr().out.split()[0] == SIG


# --- --on release ---------------------------------------------------------------------------------


def release_branch(gh: Gh) -> str:
    git(gh.root, "checkout", "-qb", "rel")
    text = (gh.root / "agk.toml").read_text("utf-8")
    (gh.root / "agk.toml").write_text('version = "9.9.9"\n' + text, "utf-8")
    commit_all(gh.root)
    head = git(gh.root, "rev-parse", "HEAD")
    git(gh.root, "update-ref", "refs/remotes/origin/rel", "HEAD")
    return head


def pr_of(head: str) -> dict:
    return {"number": 5, "head": {"sha": head, "ref": "rel"}, "base": {"ref": "main"}}


def test_release_runs_on_the_head_of_a_release_pull_request(gh):
    """REQ-053 AC8: `--on release` accepts the fetched head of an open release pull request."""
    gh.serve([], [pr_of(release_branch(gh))])
    assert run("release") == 1
    assert len(posts(gh, f"repos/{REPO}/issues")) == 1


def test_release_refuses_a_pull_request_that_raises_no_version(gh, capsys):
    """REQ-053 AC8: a pull request that does not raise `version` is not a release one."""
    git(gh.root, "checkout", "-qb", "rel")
    (gh.root / "a.txt").write_text("x", "utf-8")
    commit_all(gh.root)
    git(gh.root, "update-ref", "refs/remotes/origin/rel", "HEAD")
    gh.serve([], [pr_of(git(gh.root, "rev-parse", "HEAD"))])
    assert run("release") == 2
    assert "rule 12" in capsys.readouterr().out
    assert not (gh.root / "ran.txt").exists()


def test_a_release_run_closes_nothing(gh, monkeypatch):
    """REQ-053 AC5: only a default-branch run closes an issue (rule 8)."""
    head = release_branch(gh)
    monkeypatch.setenv("FAKE_OUTCOME", "pass")
    gh.serve([failure_issue()], [pr_of(head), fixing_pull()])
    assert run("release") == 0
    assert [c for c in gh.writes() if c[0] == "PATCH"] == []
