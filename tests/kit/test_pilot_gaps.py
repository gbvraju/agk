"""Brief #263 (REQ-039): the gaps a first organisation project met, as tests of the kit's checks.

Build (b), answer 4: while the default branch is red, the router's red-branch issue is open with the
label `agk-brief`; it is not a brief for SPEC-0034 rule 9, so a body needs no `Brief:` line for it.
"""

from __future__ import annotations

import json

import pytest

BODY = "Advances: REQ-039\nBuild-state row: 2026-10-30 REQ-039 x\nSummary: A change.\n"
RED_BODY = (
    'Sentence: "The default branch is red: the required checks of its head fail."\n'
    "Answers:\n1. Failing check: governance\n2. Head: abc\n3. Run: u\n"
    "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
)


def red(number: int = 9, **change) -> dict:
    item = {
        "number": number,
        "title": "The default branch is red",
        "user": {"login": "github-actions[bot]"},
        "labels": [{"name": "agk-brief"}],
        "body": RED_BODY,
    }
    item.update(change)
    return item


def brief(number: int = 12) -> dict:
    return {
        "number": number,
        "title": "Brief: t",
        "user": {"login": "someone"},
        "labels": [{"name": "agk-brief"}],
        "body": "Sentence: x\nPriority: 1\n",
    }


def checked(repo, issues: list[dict], body: str = BODY):
    repo.write("issues.json", json.dumps(issues))
    return repo.run("check_pr_body.py", "--issues", "issues.json", "-", stdin=body)


def test_answer4_the_red_branch_issue_alone_is_not_a_brief_for_rule_9(repo):
    """REQ-039: brief #263 answer 4."""
    proc = checked(repo, [red()])
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout == "ok pr-body\n"


def test_answer4_another_open_brief_beside_the_red_branch_issue_still_needs_brief(repo):
    """REQ-039: brief #263 answer 4 (only the red-branch issue is left out)."""
    for issues in ([red(), brief()], [brief(), red()]):
        proc = checked(repo, issues)
        assert proc.returncode == 1 and "rule 9" in proc.stdout
        assert checked(repo, issues, BODY + "Brief: #12\n").returncode == 0


@pytest.mark.parametrize(
    "change",
    [
        {"user": {"login": "a-person"}},
        {"title": "The default branch is red (by hand)"},
        {"body": "Sentence: x\nPriority: 1\n"},
    ],
)
def test_answer4_an_issue_of_the_same_shape_not_written_by_the_router_is_a_brief(repo, change):
    """REQ-039: brief #263 answer 4 (the router's own issue only, as `session.is_red` reads it)."""
    proc = checked(repo, [red(**change)])
    assert proc.returncode == 1 and "rule 9" in proc.stdout


def test_answer4_the_message_names_the_rule_and_no_value(repo):
    """REQ-039: brief #263 answer 4 (principle 8)."""
    proc = checked(repo, [brief(), red()])
    assert "github-actions" not in proc.stdout and "#9" not in proc.stdout
    assert "#12" not in proc.stdout


# --- build (a), answer 1: the plan limit on `/rulesets` is named (the doctor) -----------------

PLAN_MESSAGE = "Upgrade to GitHub Pro or make this repository public to enable this feature."
RULESET_CHECKS = {
    "ruleset-missing",
    "ruleset-enforcement",
    "ruleset-bypass",
    "ruleset-target",
    "ruleset-deletion",
    "ruleset-linear-history",
    "ruleset-force-push",
    "ruleset-pull-request",
    "required-check-governance",
}


def live_doctor(tmp_path, admin: bool = True, message: str = PLAN_MESSAGE):
    """The doctor with a `gh` that serves the repository and refuses `/rulesets` with a 403."""
    import os
    import shutil
    import subprocess  # nosec B404 - fixed argument lists only, no shell
    import sys
    from pathlib import Path

    here = Path(__file__).resolve()
    script = here.parents[2] / "scripts" / "agk" / "doctor.py"
    ok = here.parent / "fixtures" / "doctor" / "ok"
    root, kit, bin_dir = tmp_path / "root", tmp_path / "kit", tmp_path / "bin"
    shutil.copytree(ok / "tree", root)
    shutil.copytree(ok / "kit", kit)
    bin_dir.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607
    repo = json.loads((ok / "api" / "repo.json").read_text(encoding="utf-8"))
    repo["permissions"]["admin"] = admin
    (tmp_path / "repo.json").write_text(json.dumps(repo), encoding="utf-8")
    refused = {"message": message, "documentation_url": "https://docs.github.com/rest", "status": "403"}
    (tmp_path / "refused.json").write_text(json.dumps(refused), encoding="utf-8")
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  *"/rulesets"*) cat {tmp_path}/refused.json; echo "gh: {message} (HTTP 403)" >&2; exit 1;;\n'
        f'  *"api --method GET repos/example-owner/example-repo") cat {tmp_path}/repo.json;;\n'
        '  *) echo \'{"message": "Not Found", "status": "404"}\'; echo "gh: Not Found (HTTP 404)" >&2; exit 1;;\n'
        "esac\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    for tool in ("git", "cat"):
        (bin_dir / tool).symlink_to(shutil.which(tool) or tool)
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = str(bin_dir)
    args = ["--repo", "example-owner/example-repo", "--kit-root", str(kit), "--json", str(root)]
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), *args], capture_output=True, text=True, env=env
    )
    return {c["id"]: c for c in json.loads(proc.stdout)["checks"]}


def test_answer1_the_doctor_names_the_plan_limit_of_a_403_on_rulesets(tmp_path):
    """REQ-039: brief #263 answer 1 (live `gh`, an admin on a private repository on GitHub Free)."""
    report = live_doctor(tmp_path)
    assert {report[c]["reason"] for c in RULESET_CHECKS} == {"plan-limit"}


def test_answer1_the_doctor_names_no_admin_only_when_permissions_admin_is_false(tmp_path):
    """REQ-039: brief #263 answer 1."""
    other = "Resource not accessible by integration"
    report = live_doctor(tmp_path / "a", message=other)  # an admin refused for another reason
    assert {report[c]["reason"] for c in RULESET_CHECKS} == {"forbidden"}
    report = live_doctor(tmp_path / "b", admin=False, message=other)
    assert {report[c]["reason"] for c in RULESET_CHECKS} == {"no-admin"}
    report = live_doctor(tmp_path / "c", admin=False)  # the plan limit is the true cause either way
    assert {report[c]["reason"] for c in RULESET_CHECKS} == {"plan-limit"}


def test_answer1_the_hints_say_the_plan_need_and_name_no_value():
    """REQ-039: brief #263 answer 1 (principle 8: the setting, never a value)."""
    from doctor import HINTS

    hint = HINTS["plan-limit"]
    assert "paid plan" in hint and "private repositor" in hint and "branch protection" in hint
    assert "admin" not in hint and "example" not in hint
    assert "admin" in HINTS["forbidden"] and "use an account with admin rights" not in HINTS["forbidden"]
