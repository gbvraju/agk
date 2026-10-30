"""The fast checks before a push (brief #326, ADR-0186).

`scripts/agk/prepush.py` runs, in order, the pull request body check (on a body file when one is
given), `make lint` (where the project's Makefile has the target), the governance checks of
`agk.mk` (`agk-governance`, which need no network), the secret scan over the branch's commits
(gitleaks, when installed) and the tests that `test_plan.py` selects. It stops at the first
failure with that step's message, prints one line per step with its time, and exits 0 only when
every step that ran passed. `--quick` skips the tests.

The fixture repositories here hold a stand-in `agk.mk`, `Makefile` and `gitleaks`, so each step
can be made to pass or fail on its own.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest

GOOD_BODY = (
    "Brief: #1\n"
    "Advances: REQ-001\n"
    "Build-state row: 2026-10-30 REQ-001 (unchanged)\n\n"
    "Summary: A person sees one plain line.\n"
)
TOML = (
    'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
    "project_tests = 'echo RAN_PROJECT_TESTS'\n"
)
MK_OK = "agk-governance:\n\t@echo GOVERNANCE_RAN\n"
MK_FAIL = "agk-governance:\n\t@echo 'FAIL numbers: a number is used twice'; exit 1\n"
LINT_OK = "lint:\n\t@echo LINT_RAN\n"
LINT_FAIL = "lint:\n\t@echo 'E501 line too long'; exit 1\n"


def scanner(folder: Path, code: int) -> Path:
    """A stand-in `gitleaks` that records its arguments and exits with `code`."""
    folder.mkdir(parents=True, exist_ok=True)
    tool = folder / "gitleaks"
    tool.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{folder}/args.txt"\n'
        f'[ {code} -eq 0 ] || echo "leaks found: 1"\n'
        f"exit {code}\n",
        encoding="utf-8",
    )
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return folder


def path_with(folder: Path | None) -> str:
    """PATH with `folder` first, and without any real gitleaks when `folder` is None."""
    parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    parts = [p for p in parts if not (Path(p) / "gitleaks").exists()]
    return os.pathsep.join(([str(folder)] if folder else []) + parts)


def project(repo, mk: str = MK_OK, makefile: str | None = LINT_OK, toml: str = TOML) -> None:
    files = {"agk.toml": toml, "agk.mk": mk, "src/code.txt": "base\n"}
    if makefile is not None:
        files["Makefile"] = makefile
    repo.commit(files, "base")
    repo.branch("feature")
    repo.commit({"src/code.txt": "change\n", "tests/test_new.py": "# new\n"}, "change")


def prepush(repo, *args: str, scan: Path | None = None):
    return repo.run("prepush.py", *args, PATH=path_with(scan))


def steps(out: str) -> dict[str, str]:
    """Step name -> its outcome, from the `prepush: <step> <outcome> (<s>s)` lines."""
    found = re.findall(r"^prepush: (\S+) (ok|FAIL|skipped) \(\d+\.\d+s\)", out, re.M)
    return dict(found)


@pytest.fixture
def body(tmp_path) -> Path:
    path = tmp_path / "body.md"
    path.write_text(GOOD_BODY, encoding="utf-8")
    return path


def test_all_steps_pass_in_order_with_one_timed_line_each(repo, body, tmp_path):
    """REQ-016: brief #326 answer 1 (the order, one line per step with its time, exit 0)."""
    project(repo)
    proc = prepush(repo, "--body", str(body), scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = re.findall(r"^prepush: (\S+) ok \(\d+\.\d+s\)$", proc.stdout, re.M)
    assert names == ["pr-body", "lint", "governance", "secret-scan", "tests"]
    assert "prepush: all steps passed" in proc.stdout
    assert "GOVERNANCE_RAN" not in proc.stdout  # a passing step's own output is not repeated


def test_the_tests_step_runs_what_the_test_plan_selects(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (the tests that `test_plan.py` selects)."""
    project(repo, toml=TOML.replace("echo RAN_PROJECT_TESTS", "echo RAN_PROJECT_TESTS; exit 3"))
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert steps(proc.stdout)["tests"] == "FAIL"
    assert "RAN_PROJECT_TESTS" in proc.stdout
    assert "project_tests" in proc.stdout  # the run that failed is named


def test_a_test_run_is_ended_at_the_proof_timeout(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (the tests step keeps proof's limit, `proof_timeout`)."""
    toml = TOML.replace("echo RAN_PROJECT_TESTS", "sleep 20") + "proof_timeout = 1\n"
    project(repo, toml=toml)
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert steps(proc.stdout)["tests"] == "FAIL"
    assert "proof_timeout" in proc.stdout


def test_no_changed_test_file_means_no_tests_to_run(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (the plan selects nothing: the step passes, says so)."""
    repo.commit({"agk.toml": TOML, "agk.mk": MK_OK, "Makefile": LINT_OK, "a.txt": "a\n"}, "base")
    repo.branch("feature")
    repo.commit({"a.txt": "b\n"}, "change")
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RAN_PROJECT_TESTS" not in proc.stdout
    assert "tests: nothing to run" in proc.stdout


def test_a_bad_body_stops_the_run_with_its_message(repo, tmp_path):
    """REQ-016: brief #326 answers 1 and 4 (the body step fails first; nothing after it runs)."""
    project(repo)
    bad = tmp_path / "bad.md"
    bad.write_text("Advances: REQ-001\nBuild-state row: 2026-10-30 REQ-001 (unchanged)\n")
    proc = prepush(repo, "--body", str(bad), scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 1
    assert steps(proc.stdout) == {"pr-body": "FAIL"}
    assert "Summary" in proc.stdout  # the check's own message
    assert "LINT_RAN" not in proc.stdout and "GOVERNANCE_RAN" not in proc.stdout


def test_no_body_file_skips_the_body_step(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (the body check runs on a body file when one is given)."""
    project(repo)
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert steps(proc.stdout)["pr-body"] == "skipped"
    assert "no body file given" in proc.stdout


def test_a_missing_body_file_is_a_usage_error(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (the exit code of a usage error)."""
    project(repo)
    proc = prepush(repo, "--body", str(tmp_path / "absent.md"), scan=scanner(tmp_path / "b", 0))
    assert proc.returncode == 2
    assert "body" in proc.stdout + proc.stderr


def test_a_lint_failure_stops_the_run_with_its_message(repo, body, tmp_path):
    """REQ-016: brief #326 answer 4 (lint fails: its message, governance does not run)."""
    project(repo, makefile=LINT_FAIL)
    proc = prepush(repo, "--body", str(body), scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 1
    assert steps(proc.stdout) == {"pr-body": "ok", "lint": "FAIL"}
    assert "E501 line too long" in proc.stdout
    assert "GOVERNANCE_RAN" not in proc.stdout


def test_a_project_without_make_lint_skips_the_lint_step(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (a project without `make lint`)."""
    project(repo, makefile="test:\n\t@echo T\n")
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert steps(proc.stdout)["lint"] == "skipped"
    assert "no lint target" in proc.stdout


def test_a_project_without_a_makefile_skips_the_lint_step(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (no Makefile at all is a project without `make lint`)."""
    project(repo, makefile=None)
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert steps(proc.stdout)["lint"] == "skipped"


def test_a_governance_failure_stops_the_run_with_its_message(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (governance fails: its message, the scan does not run)."""
    project(repo, mk=MK_FAIL)
    folder = scanner(tmp_path / "bin", 0)
    proc = prepush(repo, scan=folder)
    assert proc.returncode == 1
    assert steps(proc.stdout)["governance"] == "FAIL"
    assert "secret-scan" not in steps(proc.stdout)
    assert "FAIL numbers: a number is used twice" in proc.stdout
    assert not (folder / "args.txt").exists()


def test_governance_gets_the_base(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (the governance checks judge the branch against its base)."""
    project(repo, mk='agk-governance:\n\t@echo "BASE=$$AGK_BASE"\n\t@exit 1\n')
    base = repo.git("rev-parse", "main").strip()
    proc = prepush(repo, "--quick", scan=scanner(tmp_path / "bin", 0))
    assert f"BASE={base}" in proc.stdout


def test_a_missing_agk_mk_fails_the_governance_step(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (governance is never skipped silently; the path class)."""
    project(repo)
    repo.commit({"agk.mk": None}, "no agk.mk")
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 1
    assert steps(proc.stdout)["governance"] == "FAIL"
    assert "agk.mk" in proc.stdout


def test_a_secret_finding_stops_the_run_with_its_message(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (the scan fails: its message, the tests do not run)."""
    project(repo)
    folder = scanner(tmp_path / "bin", 1)
    proc = prepush(repo, scan=folder)
    assert proc.returncode == 1
    assert steps(proc.stdout)["secret-scan"] == "FAIL"
    assert "tests" not in steps(proc.stdout)
    assert "leaks found: 1" in proc.stdout
    assert "RAN_PROJECT_TESTS" not in proc.stdout


def test_the_scan_covers_the_branch_commits_only(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (the secret scan over the branch: merge base to head)."""
    project(repo)
    folder = scanner(tmp_path / "bin", 0)
    assert prepush(repo, "--quick", scan=folder).returncode == 0
    base = repo.git("merge-base", "main", "HEAD").strip()
    head = repo.git("rev-parse", "HEAD").strip()
    args = (folder / "args.txt").read_text(encoding="utf-8").split("\n")
    assert args[0] == "git" and "--redact" in args and "--exit-code" in args
    assert f"--log-opts={base}..{head}" in args


def test_no_scanner_installed_is_said_and_not_a_pass(repo, tmp_path):
    """REQ-016: brief #326 answer 1 (a scan that cannot run is said, never skipped silently)."""
    project(repo)
    proc = prepush(repo, scan=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert steps(proc.stdout)["secret-scan"] == "skipped"
    assert "gitleaks is not installed" in proc.stdout
    assert "secret scan: not run" in proc.stdout
    assert "prepush: all steps passed" not in proc.stdout
    assert "prepush: passed; not run: secret-scan" in proc.stdout


def test_quick_skips_the_tests(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (`--quick`)."""
    project(repo, toml=TOML.replace("echo RAN_PROJECT_TESTS", "echo RAN_PROJECT_TESTS; exit 3"))
    proc = prepush(repo, "--quick", scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert steps(proc.stdout)["tests"] == "skipped"
    assert "--quick" in proc.stdout
    assert "RAN_PROJECT_TESTS" not in proc.stdout


def test_a_base_that_does_not_resolve_is_refused(repo, tmp_path):
    """REQ-016: brief #326 answer 4 (exit 2, naming the setting, never the value)."""
    project(repo)
    proc = prepush(repo, "--base", "no-such-ref", scan=scanner(tmp_path / "bin", 0))
    assert proc.returncode == 2
    assert "no-such-ref" not in proc.stdout + proc.stderr
    assert "base" in proc.stdout + proc.stderr


def test_an_unknown_option_is_a_usage_error(repo):
    """REQ-016: brief #326 answer 4 (exit 2 and the usage line)."""
    project(repo)
    proc = repo.run("prepush.py", "--fast")
    assert proc.returncode == 2
    assert "usage: prepush.py" in proc.stderr


def test_the_hook_template_calls_prepush_and_installs_nothing():
    """REQ-016: brief #326 answer 2 (an optional hook template; the kit never installs it)."""
    root = Path(__file__).resolve().parents[2]
    hook = root / "kit" / "templates" / "pre-push"
    text = hook.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    assert "scripts/agk/prepush.py" in text
    manifest = (root / "kit" / "manifest.json").read_text(encoding="utf-8")
    assert "pre-push" not in manifest  # never copied into a project by init or upgrade
    for script in (root / "scripts" / "agk").glob("*.py"):
        body = script.read_text(encoding="utf-8")
        assert "hooks/pre-push" not in body and "core.hooksPath" not in body, script.name


def test_the_session_rules_ask_for_prepush_before_each_push():
    """REQ-016: brief #326 answer 3 (rule 31: prepush before each push; rule 7 as SPEC-0033
    rule 1 says, the milestone push only proposed, Q-326-4)."""
    root = Path(__file__).resolve().parents[2]
    rules = (root / "config" / "session-rules.md").read_text(encoding="utf-8")
    lines = [ln for ln in rules.splitlines() if "prepush.py" in ln]
    assert len(lines) == 1 and lines[0].startswith("31. ")
    assert "before each push" in lines[0] and "milestone" not in lines[0]
    seven = next(ln for ln in rules.splitlines() if ln.startswith("7. "))
    assert seven.startswith("7. A builder commits and pushes its branch at every step")
    proposal = root / "docs" / "runs" / "proposed-spec-amendments-101.md"
    text = proposal.read_text(encoding="utf-8")
    assert "SPEC-0033 rule 1" in text and "Session rule 7" in text
    assert "always before it pauses, ends or asks a question" in text
