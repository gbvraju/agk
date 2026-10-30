"""Brief #263 build (a), answers 1 to 3 (REQ-039): plan and protection messages.

Answer 1: a 403 on `/rulesets` whose message is GitHub's plan limit is named as the plan limit, and
`no-admin` is named only when `permissions.admin` is false. Answer 2: the ruleset text printed for
applying by hand follows the phase the plan chose. Answer 3: the getting-started guide states the
plan requirement, the Actions minutes on Free and GNU make on Windows.
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env

SCRIPT = KIT_ROOT / "scripts" / "agk" / "ruleset.py"
OK_API = KIT_ROOT / "tests" / "kit" / "fixtures" / "doctor" / "ok" / "api"
RULES = KIT_ROOT / "kit" / "templates" / "branch-rules.txt"
GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"
REPO = "example-owner/example-repo"
PLAN_MESSAGE = "Upgrade to GitHub Pro or make this repository public to enable this feature."
CHECK = "required status check `governance`"


def error(message: str, status: str = "403") -> dict:
    return {"message": message, "documentation_url": "https://docs.github.com/rest", "status": status}


def api_dir(tmp_path: Path, admin: bool = True, rulesets: object = None, runs=None) -> Path:
    path = tmp_path / "api"
    path.mkdir()
    repo = json.loads((OK_API / "repo.json").read_text(encoding="utf-8"))
    repo["permissions"]["admin"] = admin
    files: dict[str, object] = {
        "repo": repo,
        "rulesets": error(PLAN_MESSAGE) if rulesets is None else rulesets,
    }
    if runs is not None:
        files["governance-runs"] = runs
    for name, data in files.items():
        (path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return path


def plan(path: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "plan", "--repo", REPO, "--api-dir", str(path), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def ruleset_sentence(out: str) -> str:
    return next(ln for ln in out.splitlines() if ln.startswith("The ruleset for the default branch"))


# --- answer 1: the plan limit is named, `no-admin` only when the account is not an admin ------


def test_answer1_a_plan_limit_403_on_rulesets_is_named_as_the_plan_limit(tmp_path):
    """REQ-039: brief #263 answer 1 (a private repository of an organisation on GitHub Free)."""
    proc = plan(api_dir(tmp_path))
    assert proc.returncode == 4
    first = proc.stdout.splitlines()[0]
    assert "(plan-limit)" in first and "no-admin" not in proc.stdout
    assert "paid plan" in proc.stdout and "private repositor" in proc.stdout
    assert "branch protection" in proc.stdout and "make the repository public" in proc.stdout
    assert "gh api --method" not in proc.stdout


def test_answer1_an_admin_refused_for_another_reason_is_not_no_admin(tmp_path):
    """REQ-039: brief #263 answer 1 (`no-admin` only when `permissions.admin` is false)."""
    proc = plan(api_dir(tmp_path, rulesets=error("Resource not accessible by integration")))
    assert proc.returncode == 4
    assert "(forbidden)" in proc.stdout and "no-admin" not in proc.stdout


def test_answer1_no_admin_is_named_when_permissions_admin_is_false(tmp_path):
    """REQ-039: brief #263 answer 1."""
    proc = plan(api_dir(tmp_path, admin=False))
    assert proc.returncode == 4
    assert "(no-admin)" in proc.stdout and "plan-limit" not in proc.stdout


def fake_gh(tmp_path: Path, admin: bool = True) -> Path:
    """A `gh` that serves the repository and refuses `/rulesets` as GitHub Free does."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    repo = json.loads((OK_API / "repo.json").read_text(encoding="utf-8"))
    repo["permissions"]["admin"] = admin
    (tmp_path / "repo.json").write_text(json.dumps(repo), encoding="utf-8")
    (tmp_path / "refused.json").write_text(json.dumps(error(PLAN_MESSAGE)), encoding="utf-8")
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  *"repos/{REPO}/rulesets"*) cat {tmp_path}/refused.json; '
        f'echo "gh: {PLAN_MESSAGE} (HTTP 403)" >&2; exit 1;;\n'
        f'  *"repos/{REPO}/actions/workflows/governance.yml/runs"*) '
        "echo '{\"total_count\": 0}';;\n"
        f'  *"api --method GET repos/{REPO}") cat {tmp_path}/repo.json;;\n'
        '  *) echo \'{"message": "Not Found"}\'; exit 1;;\n'
        "esac\n",
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def test_answer1_live_gh_with_the_plan_message_is_the_plan_limit(tmp_path):
    """REQ-039: brief #263 answer 1 (the message `gh` prints on stdout and stderr)."""
    bin_dir = fake_gh(tmp_path)
    git = shutil.which("git")
    env = {**clean_env(), "PATH": f"{bin_dir}:{Path(git).parent}"}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "plan", "--repo", REPO],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 4
    assert "(plan-limit)" in proc.stdout and "no-admin" not in proc.stdout


# --- answer 2: the hand-apply text follows the phase ------------------------------------------


def test_answer2_the_kit_text_holds_the_phase_2_clause_that_phase_1_leaves_out():
    """REQ-039: brief #263 answer 2 (a guard: the clause the phase 1 text removes exists)."""
    assert f"; {CHECK}." in RULES.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "runs", "phase"),
    [
        ((), {"total_count": 0}, 1),
        ((), None, 1),  # the runs could not be read: auto picks phase 1, as the plan does
        ((), {"total_count": 1}, 2),
        (("--phase", "1"), {"total_count": 1}, 1),
        (("--phase", "2"), {"total_count": 0}, 2),
    ],
)
def test_answer2_the_hand_apply_text_is_the_rules_of_the_phase_chosen(tmp_path, args, runs, phase):
    """REQ-039: brief #263 answer 2."""
    proc = plan(api_dir(tmp_path, rulesets=error("Resource not accessible by integration"), runs=runs), *args)
    assert proc.returncode == 4
    assert f"phase {phase} (" in proc.stdout
    sentence = ruleset_sentence(proc.stdout)
    assert (CHECK in sentence) is (phase == 2)
    assert "block force pushes" in sentence and "require a pull request" in sentence
    if phase == 1:
        later = [ln for ln in proc.stdout.splitlines() if ln.startswith("Phase 2")]
        assert len(later) == 1 and CHECK in later[0]


def test_answer2_phase_2_prints_the_kit_text_exactly(tmp_path):
    """REQ-039: brief #263 answer 2 (phase 2 is the whole of `branch-rules.txt`)."""
    proc = plan(api_dir(tmp_path, admin=False, runs={"total_count": 1}))
    assert RULES.read_text(encoding="utf-8").strip() in proc.stdout


def test_answer2_an_unreadable_repository_prints_phase_1(tmp_path):
    """REQ-039: brief #263 answer 2 (nothing read: the phase that cannot block a first merge)."""
    path = api_dir(tmp_path)
    (path / "repo.json").unlink()
    proc = plan(path)
    assert proc.returncode == 4
    assert CHECK not in ruleset_sentence(proc.stdout)


# --- answer 3: the guide's prerequisites ------------------------------------------------------


def prerequisites() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    return " ".join(text.split("## Before you start", 1)[1].split("\n## ", 1)[0].split())


def test_answer3_the_prerequisites_state_the_plan_requirement_for_private_repositories():
    """REQ-039: brief #263 answer 3."""
    text = prerequisites()
    assert "private repositor" in text and "paid plan" in text
    assert "branch protection" in text and "ruleset" in text


def test_answer3_the_prerequisites_state_that_actions_minutes_are_limited_on_free():
    """REQ-039: brief #263 answer 3."""
    text = prerequisites()
    assert "Actions minutes" in text and "Free" in text


def test_answer3_the_prerequisites_say_how_to_install_gnu_make_on_windows_and_restart():
    """REQ-039: brief #263 answer 3."""
    text = prerequisites()
    assert "winget install ezwinports.make" in text and "Windows" in text
    assert "restart" in text.lower()
