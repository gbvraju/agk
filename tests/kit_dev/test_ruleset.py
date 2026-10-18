"""Kit-only tests of scripts/agk/ruleset.py on recorded API responses (SPEC-0013 rules 19-22).

The recorded responses are the doctor's `ok` case. No test writes to GitHub: the script only
prints commands, and a fake `gh` on the PATH records every call it receives.
"""

from __future__ import annotations

import copy
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
REPO = "example-owner/example-repo"


def load(name: str) -> dict:
    return json.loads((OK_API / name).read_text(encoding="utf-8"))


class Api:
    """A copy of the recorded `ok` responses that a test edits."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir(parents=True)
        self.repo = load("repo.json")
        self.ruleset = load("ruleset-1.json")
        self.listing = json.loads((OK_API / "rulesets.json").read_text(encoding="utf-8"))
        self.runs: dict | None = None
        self.extra: dict[str, object] = {}

    def rules(self, *drop: str) -> None:
        self.ruleset["rules"] = [r for r in self.ruleset["rules"] if r["type"] not in drop]

    def params(self, kind: str) -> dict:
        return next(r for r in self.ruleset["rules"] if r["type"] == kind)["parameters"]

    def save(self) -> Path:
        files = {"repo": self.repo, "rulesets": self.listing, "ruleset-1": self.ruleset}
        if self.runs is not None:
            files["governance-runs"] = self.runs
        for name, data in {**files, **self.extra}.items():
            (self.path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
        return self.path


@pytest.fixture
def api(tmp_path) -> Api:
    return Api(tmp_path / "api")


def plan(api_dir: Path, *args: str, repo: str = REPO):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "plan", "--repo", repo, "--api-dir", str(api_dir), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def commands(out: str) -> list[str]:
    return [ln.strip() for ln in out.splitlines() if ln.strip().startswith("gh api")]


def payload(out: str, n: int = 0) -> dict:
    lines = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("payload: ")]
    return json.loads(lines[n].removeprefix("payload: "))


# --- phases and the empty plan --------------------------------------------------------------


def test_ac1_a_complete_repository_has_nothing_to_do_in_both_phases(api):
    """REQ-020 AC1: rule 20 (a plan after it is applied is empty)."""
    for phase in ("1", "2"):
        proc = plan(api.save(), "--phase", phase)
        assert proc.returncode == 0, proc.stdout
        assert "nothing to do" in proc.stdout and not commands(proc.stdout)


def test_ac1_no_ruleset_creates_one_without_the_status_check_in_phase_1(api):
    """REQ-020 AC1: rules 20 and 21 (phase 1: every element but the required check)."""
    api.listing, api.extra = [], {}
    (api.path / "ruleset-1.json").unlink(missing_ok=True)
    proc = plan(api.save(), "--phase", "1")
    assert proc.returncode == 0
    assert commands(proc.stdout) == [
        f"gh api --method POST repos/{REPO}/rulesets --input <payload-1.json>"
    ]
    body = payload(proc.stdout)
    kinds = [r["type"] for r in body["rules"]]
    assert sorted(kinds) == [
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_linear_history",
    ]
    assert body["enforcement"] == "active" and body["bypass_actors"] == []
    assert body["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    pr = next(r for r in body["rules"] if r["type"] == "pull_request")["parameters"]
    assert pr["required_approving_review_count"] == 0 and pr["allowed_merge_methods"] == ["squash"]
    assert pr["dismiss_stale_reviews_on_push"] is True


def test_ac1_phase_2_adds_the_required_check_and_phase_1_does_not(api):
    """REQ-020 AC1: rule 21."""
    api.listing, api.ruleset = [], {}
    api.save()
    (api.path / "ruleset-1.json").unlink()
    body = payload(plan(api.path, "--phase", "2").stdout)
    check = next(r for r in body["rules"] if r["type"] == "required_status_checks")
    assert check["parameters"]["required_status_checks"] == [{"context": "governance"}]


def test_ac1_an_existing_ruleset_without_the_check_gets_it_added_in_phase_2_only(api):
    """REQ-020 AC1: rules 20 and 21 (add-only: the other rules are kept)."""
    api.rules("required_status_checks")
    api.save()
    assert "nothing to do" in plan(api.path, "--phase", "1").stdout
    out = plan(api.path, "--phase", "2").stdout
    assert commands(out) == [
        f"gh api --method PUT repos/{REPO}/rulesets/1 --input <payload-1.json>"
    ]
    body = payload(out)
    assert {r["type"] for r in body["rules"]} >= {"deletion", "non_fast_forward", "pull_request"}
    assert body["rules"][-1]["type"] == "required_status_checks"


def test_ac1_a_ruleset_with_the_check_on_other_contexts_gets_governance_appended(api):
    """REQ-020 AC1: rule 20 (a context is added, none is removed)."""
    api.params("required_status_checks")["required_status_checks"] = [{"context": "lint"}]
    out = plan(api.save(), "--phase", "2").stdout
    contexts = [
        c["context"]
        for r in payload(out)["rules"]
        if r["type"] == "required_status_checks"
        for c in r["parameters"]["required_status_checks"]
    ]
    assert contexts == ["lint", "governance"]


@pytest.mark.parametrize(("runs", "phase"), [({"total_count": 1}, 2), ({"total_count": 0}, 1)])
def test_ac1_auto_picks_the_phase_from_the_governance_runs(api, runs, phase):
    """REQ-020 AC1: rule 21 (`--phase auto`, the default)."""
    api.rules("required_status_checks")
    api.runs = runs
    out = plan(api.save()).stdout
    assert f"phase {phase} (auto" in out
    assert bool(commands(out)) is (phase == 2)


def test_ac1_auto_reads_unknown_runs_as_phase_1(api):
    """REQ-020 AC1: rule 21 (a check that has never run is never required on a guess)."""
    api.rules("required_status_checks")
    out = plan(api.save()).stdout
    assert "phase 1 (auto: the runs of governance could not be read)" in out
    assert not commands(out)


# --- add-only ---------------------------------------------------------------------------------


def test_ac1_a_missing_rule_is_added_and_no_existing_rule_is_removed(api):
    """REQ-020 AC1: rule 20."""
    api.rules("deletion")
    body = payload(plan(api.save()).stdout)
    assert sorted(r["type"] for r in body["rules"]) == sorted(
        [
            "deletion",
            "non_fast_forward",
            "required_linear_history",
            "pull_request",
            "required_status_checks",
        ]
    )


def test_ac1_a_stricter_value_is_left_alone(api):
    """REQ-020 AC1: rule 20 (one required approval)."""
    api.params("pull_request")["required_approving_review_count"] = 1
    for flags in ((), ("--tighten",)):
        out = plan(api.save(), *flags).stdout
        assert "nothing to do" in out, out


def test_ac1_a_looser_value_is_reported_and_changes_only_with_tighten(api):
    """REQ-020 AC1: rule 20 (stale approvals kept; merge commits allowed)."""
    api.params("pull_request")["dismiss_stale_reviews_on_push"] = False
    api.params("pull_request")["allowed_merge_methods"] = ["squash", "merge"]
    api.params("pull_request")["required_approving_review_count"] = 2
    out = plan(api.save()).stdout
    assert "finding: ruleset 'Main': stale approvals are not dismissed on push" in out
    assert "finding: ruleset 'Main': merge methods other than squash are allowed" in out
    assert not commands(out) and "nothing to do" not in out
    tight = plan(api.path, "--tighten").stdout
    assert len(commands(tight)) == 1
    pr = next(r for r in payload(tight)["rules"] if r["type"] == "pull_request")["parameters"]
    assert pr["dismiss_stale_reviews_on_push"] is True and pr["allowed_merge_methods"] == ["squash"]
    assert pr["required_approving_review_count"] == 2  # the stricter value stays


def test_ac1_a_bypass_actor_is_reported_and_removed_only_with_tighten(api):
    """REQ-020 AC1: rule 20."""
    api.ruleset["bypass_actors"] = [{"actor_id": 5, "actor_type": "RepositoryRole"}]
    out = plan(api.save()).stdout
    assert "finding: ruleset 'Main': it has bypass actors" in out and not commands(out)
    assert payload(plan(api.path, "--tighten").stdout)["bypass_actors"] == []


def test_ac1_a_disabled_ruleset_is_reported_and_activated_only_with_tighten(api):
    """REQ-020 AC1: rule 20."""
    api.ruleset["enforcement"] = "disabled"
    out = plan(api.save()).stdout
    assert "enforcement is not active" in out and not commands(out)
    assert payload(plan(api.path, "--tighten").stdout)["enforcement"] == "active"


def test_ac1_the_put_payload_carries_no_read_only_field(api):
    """REQ-020 AC1: rule 19 (a payload is what the API accepts: no id, source, links)."""
    api.rules("deletion")
    body = payload(plan(api.save()).stdout)
    assert set(body) == {"name", "target", "enforcement", "bypass_actors", "conditions", "rules"}
    assert all(set(r) <= {"type", "parameters"} for r in body["rules"])


def test_ac1_missing_repository_settings_are_patched_and_nothing_else(api):
    """REQ-020 AC1: rule 20 (`allow_auto_merge` and `delete_branch_on_merge`)."""
    api.repo["allow_auto_merge"] = False
    api.repo["delete_branch_on_merge"] = False
    out = plan(api.save()).stdout
    assert commands(out) == [f"gh api --method PATCH repos/{REPO} --input <payload-1.json>"]
    assert payload(out) == {"allow_auto_merge": True, "delete_branch_on_merge": True}


def test_ac1_applying_the_plan_makes_the_next_plan_empty(api, tmp_path):
    """REQ-020 AC1: rule 20 (idempotent)."""
    api.listing, api.repo["allow_auto_merge"] = [], False
    api.save()
    (api.path / "ruleset-1.json").unlink()
    first = plan(api.path, "--phase", "2").stdout
    assert len(commands(first)) == 2
    created = {**payload(first, 0), "id": 1, "source": REPO}
    api.listing = [{"id": 1, "target": "branch", "enforcement": "active", "name": created["name"]}]
    api.ruleset = created
    api.repo["allow_auto_merge"] = True
    assert "nothing to do" in plan(api.save(), "--phase", "2").stdout


def test_ac1_rules_of_other_active_rulesets_count(api):
    """REQ-020 AC1: rule 20 (the doctor reads every active ruleset; so does the plan)."""
    second = copy.deepcopy(api.ruleset)
    second.update({"id": 2, "name": "Second"})
    api.rules("deletion")
    second["rules"] = [r for r in second["rules"] if r["type"] == "deletion"]
    api.listing.append({"id": 2, "target": "branch", "enforcement": "active", "name": "Second"})
    api.extra["ruleset-2"] = second
    assert "nothing to do" in plan(api.save()).stdout


# --- cannot apply: nothing but the text ------------------------------------------------------


def test_ac1_not_an_admin_prints_the_ruleset_text_and_the_path_and_nothing_else(api):
    """REQ-020 AC1: rule 19 (exit 4)."""
    api.repo["permissions"] = {"admin": False, "push": True}
    proc = plan(api.save())
    assert proc.returncode == 4
    text = (KIT_ROOT / "kit" / "templates" / "branch-rules.txt").read_text(encoding="utf-8")
    assert text.strip() in proc.stdout and "Settings > Rules > Rulesets" in proc.stdout
    assert "gh api --method" not in proc.stdout


def test_ac1_an_unreadable_repository_is_the_same_exit_4(api):
    """REQ-020 AC1: rule 19 (a missing recorded response is a failed read)."""
    api.save()
    (api.path / "repo.json").unlink()
    assert plan(api.path).returncode == 4


def test_ac1_without_gh_it_prints_the_text_and_exits_4(tmp_path):
    """REQ-020 AC1: rule 19 (no `gh` on the PATH)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "plan", "--repo", REPO],
        capture_output=True,
        text=True,
        env={**clean_env(), "PATH": str(tmp_path)},
    )
    assert proc.returncode == 4 and "The ruleset for the default branch is exactly" in proc.stdout


def test_ac1_a_bad_command_line_is_a_usage_error(api):
    """REQ-020 AC1: rule 19."""
    api.save()
    for args in (["plan", "--phase", "3"], ["apply"], ["plan", "--bogus"], ["plan", "--repo"]):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=clean_env()
        )
        assert proc.returncode == 2, args


# --- it never writes --------------------------------------------------------------------------


def fake_gh(tmp_path: Path) -> tuple[Path, Path]:
    """A `gh` that serves the recorded `ok` responses and logs every call."""
    log = tmp_path / "gh.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> {log}\n'
        'case "$*" in\n'
        f'  *"api --method GET repos/{REPO}/rulesets/1") cat {OK_API}/ruleset-1.json;;\n'
        f'  *"api --method GET repos/{REPO}/rulesets") cat {OK_API}/rulesets.json;;\n'
        f'  *"api --method GET repos/{REPO}/actions/workflows/governance.yml/runs"*) '
        "echo '{\"total_count\": 1}';;\n"
        f'  *"api --method GET repos/{REPO}") cat {OK_API}/repo.json;;\n'
        '  *) echo \'{"message": "Not Found"}\'; exit 1;;\n'
        "esac\n",
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return bin_dir, log


def test_ac1_live_reads_use_get_only_and_never_a_write_method(tmp_path):
    """REQ-020 AC1: rule 19 (the script holds no credential and sends nothing)."""
    bin_dir, log = fake_gh(tmp_path)
    git = shutil.which("git")
    env = {**clean_env(), "PATH": f"{bin_dir}:{Path(git).parent}"}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "plan", "--repo", REPO],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout
    assert "nothing to do" in proc.stdout and "phase 2 (auto" in proc.stdout
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls and all(c.startswith("api --method GET ") for c in calls), calls
    assert all(f"repos/{REPO}" in c for c in calls)


def test_ac1_the_script_has_no_write_call_and_no_credential():
    """REQ-020 AC1: rule 19 (static reading; `--method POST` appears only in printed text)."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "subprocess" not in source and "TOKEN" not in source and "token" not in source
    assert "os.environ" not in source


def test_ac1_payload_dir_receives_the_payload_files_the_commands_name(api, tmp_path):
    """REQ-020 AC1: rule 19 (the skill runs the commands from payload files in a temp dir)."""
    api.repo["allow_auto_merge"] = False
    api.rules("deletion")
    target = tmp_path / "payloads"
    out = plan(api.save(), "--payload-dir", str(target)).stdout
    assert [c.rsplit(" ", 1)[1] for c in commands(out)] == [
        str(target / "payload-1.json"),
        str(target / "payload-2.json"),
    ]
    assert json.loads((target / "payload-2.json").read_text(encoding="utf-8")) == {
        "allow_auto_merge": True
    }
    assert "payload: " not in out


def test_ac1_without_payload_dir_nothing_is_written(api, tmp_path):
    """REQ-020 AC1: rule 19."""
    api.rules("deletion")
    api.save()
    before = sorted(p.name for p in tmp_path.rglob("*"))
    plan(api.path)
    assert sorted(p.name for p in tmp_path.rglob("*")) == before


def test_ac1_the_desired_ruleset_file_is_the_elements_of_adr_0001():
    """REQ-020 AC1: rule 20 (kit/templates/ruleset.json)."""
    want = json.loads((KIT_ROOT / "kit" / "templates" / "ruleset.json").read_text("utf-8"))
    rules = {r["type"] for r in want["ruleset"]["rules"]}
    assert rules == {"deletion", "required_linear_history", "non_fast_forward", "pull_request"}
    assert want["ruleset"]["enforcement"] == "active" and want["ruleset"]["bypass_actors"] == []
    assert want["phase2_rules"][0]["type"] == "required_status_checks"
    assert want["repository_settings"] == {"allow_auto_merge": True, "delete_branch_on_merge": True}
