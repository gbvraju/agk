"""doctor passes a correct clean-layout project (brief #1668, ADR-0695; REQ-078 AC1 and AC5).

With `[kit] layout = "plugin"` the doctor checks the files that layout keeps (SPEC-0071 rule 2:
`CLEAN_KEEPS`, `CLEAN_KEEPS_UNDER` and the short `CLAUDE.md` from `kit/templates/clean-claude.md`)
and reports an absent drift-audit workflow as `ok (layout: plugin...)`; an installed project keeps
today's checks; another `layout` value fails the `layout` line naming the setting. Temporary
folders and the kit checkout only; no network; invented data only (example.com)."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import doctor  # noqa: E402
import init  # noqa: E402
import upgrade  # noqa: E402

if not (ROOT / "kit" / "manifest.json").is_file():  # an install, or a copy of the kit's tests
    pytest.skip("reads the kit's own files (kit/ is kit-only)", allow_module_level=True)

DOCTOR = ROOT / "scripts" / "agk" / "doctor.py"
KIT_IDS = ("layout", "drift-workflow-file", "kit-version", "vendored-missing", "vendored-differs")


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)  # nosec B603 B607 - fixed git, no shell


def project(tmp_path: Path, tool: str, *flags: str) -> Path:
    """A fresh `init` or `adopt` project with the setup login, as the steward makes one."""
    target = tmp_path / "shop-example"
    git("init", "-q", "-b", "main", str(target))
    if tool == "adopt":
        (target / "README.md").write_text("# shop\n", encoding="utf-8")
        (target / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        git("-C", str(target), "add", "-A")
        git("-C", str(target), "-c", "user.email=a@example.com", "-c", "user.name=a", "commit",
            "-qm", "one")
    env = {**os.environ, "AGK_SETUP_LOGIN": "octo-example"}
    script = ROOT / "scripts" / "agk" / f"{tool}.py"
    proc = subprocess.run(  # nosec B603 - a kit script with fixed arguments, no shell
        [sys.executable, str(script), str(target), "--unreleased", "--login-from-env", *flags],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    git("-C", str(target), "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return target


def clean(tmp_path: Path, tool: str = "init") -> Path:
    return project(tmp_path, tool, "--layout", "plugin", "--rehearsal")


def run(target: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    api = tmp_path / "api"
    api.mkdir(exist_ok=True)
    args = ["--kit-root", str(ROOT), "--api-dir", str(api), "--repo", "example-owner/example-repo"]
    return subprocess.run(  # nosec B603 - the doctor with fixed arguments, no shell
        [sys.executable, str(DOCTOR), *args, "--json", str(target)],
        capture_output=True, text=True, cwd=target,
    )


def report(target: Path, tmp_path: Path) -> dict[str, dict]:
    proc = run(target, tmp_path)
    assert proc.stdout.startswith("{"), proc.stdout + proc.stderr
    return {c["id"]: c for c in json.loads(proc.stdout)["checks"]}


def kit_checks(target: Path) -> dict[str, tuple[str, str]]:
    """The five kit lines as (status, message) from the functions, without a run."""
    config = doctor.read_config(target)
    results, _ = doctor.kit_results(target, ROOT, config)
    results["drift-workflow-file"] = doctor.drift_file_result(target, config)
    results["layout"] = doctor.layout_result(config)
    return {n: (results[n].status, results[n].message) for n in KIT_IDS}


def edit_toml(target: Path, old: str, new: str) -> None:
    path = target / "agk.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


@pytest.mark.parametrize("tool", ["init", "adopt"])
def test_req078_ac1_a_fresh_clean_project_has_no_fail_line(tool, tmp_path):
    checks = report(clean(tmp_path, tool), tmp_path)
    assert [i for i, c in checks.items() if c["status"] == "fail"] == []
    assert "(layout: plugin" in checks["drift-workflow-file"]["message"]
    assert checks["layout"]["status"] == "ok" and "(layout: plugin)" in checks["layout"]["message"]
    for name in ("vendored-missing", "vendored-differs", "kit-version"):
        assert checks[name]["status"] == "ok"


def test_req078_the_projects_own_rules_below_the_short_claude_md_pass(tmp_path):
    target = clean(tmp_path)
    with (target / "CLAUDE.md").open("a", encoding="utf-8") as fh:
        fh.write("\n1. Every page loads in under one second (example.com).\n")
    assert kit_checks(target)["vendored-differs"][0] == "ok"


@pytest.mark.parametrize("rel", ["LICENSE-AGK", ".github/PULL_REQUEST_TEMPLATE.md", "CLAUDE.md"])
@pytest.mark.parametrize("tool", ["init", "adopt"])
def test_req078_a_changed_kept_file_fails_vendored_differs(tool, rel, tmp_path):
    target = clean(tmp_path, tool)
    path = target / rel
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("\n", "\nA changed line (example.com).\n", 1), encoding="utf-8")
    status, message = kit_checks(target)["vendored-differs"]
    assert status == "fail" and rel in message


def test_req078_a_missing_kept_file_fails_vendored_missing(tmp_path):
    target = clean(tmp_path)
    (target / "LICENSE-AGK").unlink()
    (target / "CLAUDE.md").unlink()
    status, message = kit_checks(target)["vendored-missing"]
    assert status == "fail" and "LICENSE-AGK" in message and "CLAUDE.md" in message


def test_req078_a_present_drift_file_in_a_clean_project_is_checked_as_today(tmp_path):
    target = clean(tmp_path)
    workflow = target / doctor.DRIFT_WORKFLOW
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("on:\n  workflow_dispatch:\n", encoding="utf-8")
    assert kit_checks(target)["drift-workflow-file"][0] == "fail"
    workflow.write_text("on:\n  schedule:\n    - cron: '0 6 * * 1'\n", encoding="utf-8")
    assert kit_checks(target)["drift-workflow-file"] == ("ok", "")


def test_req078_an_installed_project_keeps_todays_checks(tmp_path):
    target = project(tmp_path, "init")
    checks = kit_checks(target)
    assert checks["layout"] == ("ok", " (layout: installed)")
    assert all(checks[n][0] == "ok" for n in KIT_IDS)
    (target / doctor.DRIFT_WORKFLOW).unlink()
    (target / ".claude" / "agents" / "builder.md").unlink()
    checks = kit_checks(target)
    assert checks["drift-workflow-file"][0] == "fail"
    assert checks["vendored-missing"][0] == "fail"
    assert ".claude/agents/builder.md" in checks["vendored-missing"][1]
    with (target / "agk.toml").open("a", encoding="utf-8") as fh:
        fh.write('\n[kit]\nlayout = "installed"\n')
    assert kit_checks(target)["drift-workflow-file"][0] == "fail"


def test_req078_another_layout_value_fails_the_layout_line_naming_the_setting(tmp_path):
    target = clean(tmp_path)
    edit_toml(target, '[kit]\nlayout = "plugin"', '[kit]\nlayout = "vendored-example"')
    checks = report(target, tmp_path)
    line = checks["layout"]
    assert line["status"] == "fail" and line["severity"] == "error"
    assert "[kit] layout" in line["message"] and "vendored-example" not in json.dumps(line)


def test_req078_a_plugin_version_that_is_not_the_running_plugin_is_refused(tmp_path):
    target = clean(tmp_path)
    version = tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))["kit"]
    assert report(target, tmp_path)["layout"]["status"] == "ok"  # the pin matches
    edit_toml(target, f'plugin_version = "{version["plugin_version"]}"', 'plugin_version = "0.0.1"')
    proc = run(target, tmp_path)
    assert proc.returncode != 0
    assert "setting: plugin_version" in proc.stdout + proc.stderr
    assert "0.0.1" not in proc.stdout + proc.stderr


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('execution = "local"', 'execution = "hosted"'),
        ('review_mode = "team"', 'review_mode = "solo"'),
    ],
)
def test_req078_execution_and_review_mode_give_the_same_kit_lines(old, new, tmp_path):
    target = clean(tmp_path)
    before = kit_checks(target)
    edit_toml(target, old, new)
    assert kit_checks(target) == before
    assert all(status == "ok" for status, _ in before.values())


def test_req078_ac5_a_planted_kit_file_keeps_the_kit_in_repository_warning(tmp_path):
    target = clean(tmp_path)
    planted = target / "scripts" / "agk" / "doctor.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("print('example')\n", encoding="utf-8")
    assert doctor.kit_in_repository_lines(target, ROOT)
    assert kit_checks(target)["vendored-missing"][0] == "ok"


def test_req078_doctor_keeps_the_same_files_as_init_and_the_migration():
    kept = {r for r in upgrade.CLEAN_KEPT if r != "agk.toml"}
    assert set(init.CLEAN_KEPT) == set(upgrade.CLEAN_KEPT)
    assert {*doctor.CLEAN_KEEPS, *doctor.CLEAN_KEEPS_UNDER} == kept
    assert doctor.CLEAN_TEMPLATE == upgrade.CLEAN_TEMPLATE == init.CLEAN_TEMPLATE
