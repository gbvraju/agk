"""Kit-only tests of the printed pull request bodies (brief #273; REQ-020).

Every command whose work ends in a pull request prints its body as a file path and its text, and
only after the repository's own `check_pr_body.py` passed it in the state the command was given:
`--brief N`, `--brief none` or `--issues FILE`. A change of only the design or only the specs and
requirements carries its none form. The Summary is cut to fit at a word boundary. After the
approving commit of an intake, the next steps print the one `Approve:` line with the full head ID.
Invented repositories in `tmp_path`; no network, no model.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo
from test_engines_stack import GOOD_STACK, OPTION_B, engines, stack_root
from test_intake import draft
from test_intake import repo as intake_repo  # noqa: F401  (the fixture of test_intake)
from test_intake import run as intake_run
from test_intake_final import approve, intake_commit
from test_playbook import good_start
from test_playbook import run as playbook_run
from test_playbook import started as playbook_started  # noqa: F401  (the fixture of test_playbook)
from test_upgrade import init_target
from test_upgrade import kit as upgrade_kit  # noqa: F401  (the fixture of test_upgrade)

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import pr_body  # noqa: E402
import upgrade  # noqa: E402

CHECK = KIT_ROOT / "scripts" / "agk" / "check_pr_body.py"
BRIEFS = [{"number": 7, "labels": [{"name": "agk-brief"}]}]


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


@pytest.fixture
def intake(request):
    return request.getfixturevalue("intake_repo")


def saved(tmp_path, issues) -> str:
    path = tmp_path / "briefs.json"
    path.write_text(json.dumps(issues), encoding="utf-8")
    return str(path)


def body_of(out: str) -> str:
    return out.split("Pull request body:\n\n", 1)[1].split("\n\n", 1)[0] + "\n"


def file_of(out: str) -> str:
    return re.search(r"(?m)^Pull request body file: (.+)$", out).group(1)


def passes(root, body: str, issues: str) -> bool:
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--issues", issues, "-"],
        input=body,
        capture_output=True,
        text=True,
        cwd=root,
        env={**clean_env(), "AGK_BASE": "main"},
    )
    return proc.stdout == "ok pr-body\n"


# --- the Summary is cut at a word boundary (answer 1) -------------------------------------------


def test_a_long_summary_is_cut_at_a_word_boundary_and_a_short_one_is_kept():
    """REQ-020: brief #273 answer 1."""
    words = "The project's stack is chosen: option B, " + "a very long framework name " * 8
    cut = pr_body.fit_summary(words)
    assert len(cut) <= 120 and words.startswith(cut) and words[len(cut)] == " "
    assert not cut.endswith((",", " "))
    assert pr_body.fit_summary("A short one.") == "A short one."
    assert len(pr_body.fit_summary("x" * 300)) == 120


# --- /agk:start (playbook.py next-steps) ---------------------------------------------------------


def start_steps(root, *args):
    return playbook_run(
        "next-steps", "--base", "main", "--date", "2026-10-29", "--root", str(root), *args
    )


def test_start_prints_a_brief_line_the_file_and_a_body_that_passes_with_an_open_brief(
    started, tmp_path
):
    """REQ-020: brief #273 answer 1 (the pilot's body without the Brief line)."""
    good_start(started)
    proc = start_steps(started, "--brief", "7")
    assert proc.returncode == 0, proc.stdout
    body = body_of(proc.stdout)
    assert body.startswith("Brief: #7\n")
    path = file_of(proc.stdout)
    assert ".git" in path and open(path, encoding="utf-8").read() == body
    assert passes(started, body, saved(tmp_path, BRIEFS))
    assert not git_status_shows(started, "pr-body")


def git_status_shows(root, needle: str) -> bool:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    return needle in out.stdout


def test_start_refuses_when_a_brief_is_open_and_none_is_given(started, tmp_path):
    """REQ-020: brief #273 answer 1 (a body that fails is never printed)."""
    good_start(started)
    for args in ((), ("--issues", saved(tmp_path, BRIEFS))):
        proc = start_steps(started, *args)
        assert proc.returncode == 1, proc.stdout
        assert "rule 9" in proc.stdout and "Pull request body:" not in proc.stdout


def test_start_without_an_open_brief_prints_no_brief_line(started, tmp_path):
    """REQ-020: brief #273 answer 1 (the saved copy, or the person's word)."""
    good_start(started)
    for args in (("--issues", saved(tmp_path, [])), ("--brief", "none")):
        proc = start_steps(started, *args)
        assert proc.returncode == 0, proc.stdout
        assert "Brief:" not in body_of(proc.stdout)
        assert passes(started, body_of(proc.stdout), saved(tmp_path, []))


def test_the_repositorys_own_check_decides_and_its_failure_prints_no_body(started):
    """REQ-020: brief #273 answer 1 (the check in the repository's current state)."""
    git(started, "switch", "-q", "main")
    stub = started / "scripts" / "agk" / "check_pr_body.py"
    stub.parent.mkdir(parents=True)
    stub.write_text('print("FAIL pr-body: rule 99: a newer rule")\nraise SystemExit(1)\n')
    git(started, "add", "-A")
    git(started, "commit", "-q", "-m", "a newer check")
    git(started, "switch", "-q", "start/a-reading-list")
    git(started, "reset", "-q", "--hard", "main")
    good_start(started)
    proc = start_steps(started, "--brief", "none")
    assert proc.returncode == 1
    assert "rule 99" in proc.stdout and "Pull request body:" not in proc.stdout


def test_a_bad_brief_value_is_refused_naming_the_option(started):
    """REQ-020: brief #273 (messages name the option, never a value)."""
    good_start(started)
    proc = start_steps(started, "--brief", "seven")
    assert proc.returncode == 1 and "option --brief" in proc.stdout and "seven" not in proc.stdout


# --- /agk:spec (intake.py next-steps) and the Approve line (answers 1 and 3) ---------------------


def test_intake_prints_a_body_that_passes_with_the_brief_it_answers(intake, tmp_path):
    """REQ-020: brief #273 answer 1."""
    draft(intake)
    proc = intake_run(intake, "next-steps", "--base", "main", "--brief", "7")
    assert proc.returncode == 0, proc.stdout
    body = body_of(proc.stdout)
    assert body.startswith("Brief: #7\nAdvances: REQ-004\n")
    assert passes(intake, body, saved(tmp_path, BRIEFS))
    assert not any(line.startswith("Approve: ") for line in proc.stdout.splitlines())


def test_after_the_approving_commit_the_next_steps_print_the_exact_approve_line(intake):
    """REQ-020: brief #273 answer 3 (the full head ID, where to post it, a red check expected)."""
    intake_commit(intake)
    approve(intake)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=intake, capture_output=True, text=True
    ).stdout.strip()
    proc = intake_run(intake, "next-steps", "--base", "main")
    assert proc.returncode == 0, proc.stdout
    lines = proc.stdout.splitlines()
    assert f"Approve: {head} SPEC-0014" in lines
    assert len(head) == 40
    assert "own GitHub account" in proc.stdout and "agent app" in proc.stdout
    assert "final-clearance" in proc.stdout and "expected" in proc.stdout
    assert "Pull request body:" not in proc.stdout


# --- /agk:stack (engines.py stack-next-steps, answer 2) -----------------------------------------


def stack_steps(root, *args):
    return engines(root, "stack-next-steps", "--base", "main", "--date", "2026-10-29", *args)


def test_stack_prints_the_body_of_the_options_pull_request(started, tmp_path):
    """REQ-020: brief #273 answer 2 (the stack gets a next-steps step like the others)."""
    stack_root(started)
    proc = stack_steps(started, "--brief", "7")
    assert proc.returncode == 0, proc.stdout
    body = body_of(proc.stdout)
    assert "Advances: REQ-001\n" in body and "ADR-0002" in body
    assert passes(started, body, saved(tmp_path, BRIEFS))


def test_stack_prints_the_body_of_the_accepting_pull_request_with_a_summary_that_fits(
    started, tmp_path
):
    """REQ-020: brief #273 answers 1 and 2 (the pilot's Summary over 120 characters)."""
    long_name = "a web framework with " + "a very long descriptive name " * 6
    text = (
        GOOD_STACK.replace(OPTION_B, OPTION_B.replace("a web framework", long_name.strip()))
        .replace("- Status: Proposed", "- Status: Accepted")
        .replace("3. **Chosen**: none yet", "3. **Chosen**: Option B — it fits the host")
    )
    stack_root(started, text)
    proc = stack_steps(started, "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    body = body_of(proc.stdout)
    summary = next(ln for ln in body.splitlines() if ln.startswith("Summary: "))
    assert len(summary) - len("Summary: ") <= 120 and "option B" in summary
    assert "ADR-0002 Accepted" in body
    assert passes(started, body, saved(tmp_path, []))


def test_stack_refuses_a_stack_adr_that_fails_its_check_or_names_no_requirement(started):
    """REQ-020: brief #273 answer 1 (nothing printed for work that does not pass)."""
    stack_root(started, GOOD_STACK.replace("3. **Chosen**: none yet", "3. **Chosen**: Option A"))
    proc = stack_steps(started, "--brief", "none")
    assert proc.returncode == 1 and "Pull request body:" not in proc.stdout
    stack_root(started, GOOD_STACK.replace("- Requirements: REQ-001", "- Requirements: none"))
    proc = stack_steps(started, "--brief", "none")
    assert proc.returncode == 1 and "Requirements" in proc.stdout


def test_the_stack_skill_runs_the_next_steps_and_writes_no_body_by_hand():
    """REQ-020: brief #273 answer 2."""
    text = (KIT_ROOT / "skills" / "stack" / "SKILL.md").read_text(encoding="utf-8")
    assert 'engines.py" stack-next-steps' in text
    assert "Summary: The project's stack is chosen" not in text


# --- /agk:design (engines.py design-next-steps): the none form ----------------------------------


def test_design_prints_the_none_form_and_a_body_that_passes_with_an_open_brief(tmp_path):
    """REQ-020: brief #273 answer 1 and the field note (a design change answers no brief)."""
    root = make_repo(tmp_path / "proj")
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "design/home")
    written = subprocess.run(
        [
            sys.executable,
            str(KIT_ROOT / "scripts" / "agk" / "design.py"),
            "write",
            "--name",
            "home",
            "--date",
            "2026-10-29",
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert written.returncode == 0, written.stdout
    issues = saved(tmp_path, BRIEFS)
    proc = engines(
        root, "design-next-steps", "--base", "main", "--req", "REQ-001", "--issues", issues
    )
    assert proc.returncode == 0, proc.stdout
    body = body_of(proc.stdout)
    assert body.startswith("Brief: none (design)\nAdvances: REQ-001\n")
    assert passes(root, body, issues)
    proc = engines(root, "design-next-steps", "--base", "main", "--issues", issues)
    assert proc.returncode == 1 and "option --req" in proc.stdout


# --- /agk:upgrade (upgrade.py TARGET --next-steps) ----------------------------------------------

UPGRADE_ADR = (
    "# ADR-0002: Upgrade agk from 1.0.0 to 2.0.0\n\n- Status: Proposed\n- Date: 2026-10-29\n"
    "- Deciders: maintainers\n- Related: none\n- Requirements: REQ-001\n"
)


def upgrade_steps(capsys, target, *args):
    code = upgrade.main([str(target), "--next-steps", "--date", "2026-10-29", *args])
    return code, capsys.readouterr().out


def test_upgrade_prints_the_body_once_the_upgrade_and_its_adr_are_written(
    tmp_path,
    upgrade_kit,  # noqa: F811
    capsys,
):
    """REQ-020: brief #273 answer 1."""
    target = init_target(tmp_path)
    code, out = upgrade_steps(capsys, target, "--brief", "none")
    assert code == 1 and "Pull request body:" not in out  # not upgraded yet
    assert upgrade.main([str(target)]) == 0
    capsys.readouterr()
    code, out = upgrade_steps(capsys, target, "--brief", "none")
    assert code == 1 and "docs/adr/" in out  # no upgrade ADR yet
    (target / "docs" / "adr" / "0002-upgrade-agk.md").write_text(UPGRADE_ADR, encoding="utf-8")
    code, out = upgrade_steps(capsys, target, "--brief", "7")
    assert code == 0, out
    body = body_of(out)
    assert body.startswith("Brief: #7\nAdvances: REQ-001\n") and "2.0.0" in body
    assert passes(target, body, saved(tmp_path, BRIEFS))


def test_an_intake_without_a_brief_carries_the_spec_form_and_passes_with_an_open_brief(
    intake, tmp_path
):
    """REQ-020: brief #273, Q-273-1 as answered (an intake's ADR stub is a shared document)."""
    draft(intake)
    issues = saved(tmp_path, BRIEFS)
    proc = intake_run(intake, "next-steps", "--base", "main", "--issues", issues)
    assert proc.returncode == 0, proc.stdout
    body = body_of(proc.stdout)
    assert body.startswith("Brief: none (spec)\nAdvances: REQ-004\n")
    assert passes(intake, body, issues)
