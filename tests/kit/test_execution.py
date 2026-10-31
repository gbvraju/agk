"""Tests of scripts/agk/execution.py and common.execution (brief #441, ADR-0237): a project names
where its heavy checks run in one setting, `execution` in agk.toml (hosted, hybrid, pool or local),
and one command prints the setting in force and the profile the kit recommends, with its reason.
Saved API responses (`--api-dir`), no network, no `gh`. REQ-039"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import common
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "execution"
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "execution.py"
KIT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODE = "docs/guides/local-mode.md"
RUNNER_GUIDE = "docs/guides/self-hosted-runner.md"


def case(tmp_path: Path, name: str = "private") -> Path:
    """A copy of a saved case that a test may change."""
    dest = tmp_path / "api"
    shutil.copytree(FIXTURES / name, dest)
    return dest


def save(api: Path, name: str, data) -> None:
    (api / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def refuse(api: Path, name: str, status: int) -> None:
    (api / f"{name}.json").unlink(missing_ok=True)
    (api / f"{name}.status").write_text(f"{status}\n", encoding="utf-8")


def used(api: Path, minutes: int, included: int = 2000) -> None:
    save(api, "billing", {"total_minutes_used": minutes, "included_minutes": included})


def execution(repo, api: Path, *extra: str, toml: str = 'default_branch = "main"\n'):
    repo.write("agk.toml", toml)
    return repo.run("execution.py", "--api-dir", str(api), *extra)


def line(repo, api: Path, **kw) -> str:
    proc = execution(repo, api, **kw)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.splitlines()[0]


def report(repo, api: Path, **kw) -> dict:
    proc = execution(repo, api, "--json", **kw)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def setting(value: str) -> str:
    return f'default_branch = "main"\nexecution = "{value}"\n'


# --- answer 1: the setting --------------------------------------------------------------------


@pytest.mark.parametrize("value", ["hosted", "hybrid", "pool", "local"])
def test_each_value_is_read(tmp_path, value):
    """REQ-039: brief #441 answer 1 (the four values)."""
    (tmp_path / "agk.toml").write_text(setting(value), encoding="utf-8")
    assert common.execution(tmp_path) == value


def test_absent_reads_hosted(tmp_path):
    """REQ-039: brief #441 answer 1 (absent reads hosted; no config at all reads hosted too)."""
    assert common.execution(tmp_path) == "hosted"
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert common.execution(tmp_path) == "hosted"


@pytest.mark.parametrize("bad", ['"cloud"', '"Hosted"', '""', "1", "true", '["hosted"]'])
def test_another_value_is_refused_naming_the_setting(tmp_path, bad):
    """REQ-039: brief #441 answer 1 (another value is refused, naming the setting)."""
    (tmp_path / "agk.toml").write_text(f"execution = {bad}\n", encoding="utf-8")
    with pytest.raises(common.CheckError) as err:
        common.execution(tmp_path)
    assert "(setting: execution)" in str(err.value)
    assert "cloud" not in str(err.value) and "Hosted" not in str(err.value)


def test_no_setting_prints_hosted_in_force(repo, tmp_path):
    """REQ-039: brief #441 answer 4 (no setting)."""
    out = line(repo, case(tmp_path))
    assert out.startswith("execution: hosted (recommended: ")
    assert report(repo, case(tmp_path / "j"))["execution"] == "hosted"


def test_a_refused_value_exits_1_naming_the_setting(repo, tmp_path):
    """REQ-039: brief #441 answer 4 (a refused value)."""
    proc = execution(repo, case(tmp_path), toml=setting("cloud"))
    assert proc.returncode == 1, proc.stdout
    assert "(setting: execution)" in proc.stdout
    assert "cloud" not in proc.stdout


def test_the_setting_in_force_is_printed(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (the line names the setting in force)."""
    out = line(repo, case(tmp_path), toml=setting("local"))
    assert out.startswith("execution: local (recommended: ")


# --- answer 2: the table ----------------------------------------------------------------------


def test_public_repository_recommends_hosted(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (a public repository: hosted, its minutes are not billed)."""
    api = case(tmp_path)
    save(api, "repo", {"full_name": "example/app", "private": False, "owner": {"login": "example"}})
    used(api, 1990)  # a public repository's figures do not move it off hosted
    out = line(repo, api)
    assert out == (
        "execution: hosted (recommended: hosted: a public repository's minutes are not billed)"
    )


def test_private_with_more_than_half_left_recommends_hosted(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (private, more than half of the included minutes left)."""
    out = line(repo, case(tmp_path))
    assert out == (
        "execution: hosted (recommended: hosted: 300 of 2000 included minutes used (15%), "
        "more than half left)"
    )
    data = report(repo, case(tmp_path / "j"))
    assert data["recommended"] == "hosted"
    assert data["used"] == 300 and data["included"] == 2000


def test_private_past_half_recommends_hybrid(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (private, past half of the included minutes)."""
    api = case(tmp_path)
    used(api, 1100)
    out = line(repo, api)
    assert out == (
        "execution: hosted (recommended: hybrid: 1100 of 2000 included minutes used (55%), "
        "past half)"
    )


def test_exactly_half_used_is_past_half(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (half used no longer leaves more than half)."""
    api = case(tmp_path)
    used(api, 1000)
    assert "(recommended: hybrid: " in line(repo, api)


def test_private_past_minutes_warn_recommends_hybrid(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (private, past `minutes_warn`)."""
    api = case(tmp_path)
    used(api, 1700)
    out = line(repo, api)
    assert out == (
        "execution: hosted (recommended: hybrid: 1700 of 2000 included minutes used (85%), "
        "past minutes_warn (80%))"
    )


def test_a_low_minutes_warn_recommends_hybrid_before_half(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (past `minutes_warn` set below half)."""
    api = case(tmp_path)
    used(api, 700)
    toml = 'default_branch = "main"\nminutes_warn = 30\n'
    out = line(repo, api, toml=toml)
    assert out.endswith(
        "(recommended: hybrid: 700 of 2000 included minutes used (35%), past minutes_warn (30%))"
    )


def test_minutes_used_up_recommends_local(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (minutes used up: local, pointing to the local-mode guide)."""
    api = case(tmp_path)
    used(api, 2000)
    out = line(repo, api)
    assert out == (
        "execution: hosted (recommended: local: the included minutes are used up "
        f"(2000 of 2000); see {LOCAL_MODE})"
    )


def test_actions_disabled_recommends_local(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (Actions disabled for the repository: local)."""
    api = case(tmp_path)
    save(api, "permissions", {"enabled": False})
    out = line(repo, api)
    assert out == (
        "execution: hosted (recommended: local: Actions is disabled for this repository; "
        f"see {LOCAL_MODE})"
    )


def test_actions_disabled_wins_over_a_public_repository(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (no hosted runner runs while Actions is disabled)."""
    api = case(tmp_path)
    save(api, "repo", {"full_name": "example/app", "private": False, "owner": {"login": "example"}})
    save(api, "permissions", {"enabled": False})
    assert "(recommended: local: Actions is disabled" in line(repo, api)


@pytest.mark.parametrize("status", [403, 404])
def test_unreadable_actions_permissions_do_not_recommend_local(repo, tmp_path, status):
    """REQ-039: brief #441 answer 2 (an unread permission is not a disabled one; Q-441-1)."""
    api = case(tmp_path)
    refuse(api, "permissions", status)
    assert "(recommended: hosted: 300 of 2000" in line(repo, api)


@pytest.mark.parametrize("status", [401, 403])
def test_a_token_that_cannot_read_billing_recommends_hosted_with_the_reason(repo, tmp_path, status):
    """REQ-039: brief #441 answer 4 (a token that cannot read billing: hosted, with that reason)."""
    api = case(tmp_path)
    refuse(api, "billing", status)
    out = line(repo, api)
    assert out == (
        "execution: hosted (recommended: hosted: the billing reading is unknown "
        "(the token cannot read billing: refused))"
    )
    data = report(repo, api)
    assert data["recommended"] == "hosted" and data["used"] is None


def test_missing_billing_recommends_hosted_with_the_reason(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (the billing reading unknown: missing)."""
    api = case(tmp_path)
    (api / "billing.json").unlink()
    assert line(repo, api).endswith(
        "(recommended: hosted: the billing reading is unknown "
        "(the token cannot read billing: missing))"
    )


def test_a_plan_without_included_minutes_reads_unknown(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (no included minutes to compare against; Q-441-2)."""
    api = case(tmp_path)
    used(api, 50, included=0)
    assert line(repo, api).endswith(
        "(recommended: hosted: the billing reading is unknown "
        "(the plan includes no minutes to compare against))"
    )


def test_an_unreadable_repository_is_refused(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (the repository itself cannot be read)."""
    api = case(tmp_path)
    refuse(api, "repo", 404)
    proc = execution(repo, api)
    assert proc.returncode == 1
    assert "path class: repository" in proc.stdout


# --- answer 3: reports only, and the runner variable --------------------------------------------


@pytest.mark.parametrize("value", ["pool", "hybrid"])
def test_pool_or_hybrid_without_the_variable_points_to_the_runner_guide(repo, tmp_path, value):
    """REQ-039: brief #441 answers 3 and 4 (`pool` set without the variable)."""
    api = case(tmp_path)
    (api / "variable.json").unlink()
    proc = execution(repo, api, toml=setting(value))
    assert proc.returncode == 0, proc.stdout
    lines = proc.stdout.splitlines()
    assert len(lines) == 2
    assert lines[1] == (
        f"execution: {value} runs the heavy checks on a runner named by the repository variable "
        f"AGK_HEAVY_RUNNER, which is not set; see {RUNNER_GUIDE}"
    )


def test_pool_with_an_unreadable_variable_says_so(repo, tmp_path):
    """REQ-039: brief #441 answer 3 (the variable cannot be read: said, with its reason class)."""
    api = case(tmp_path)
    refuse(api, "variable", 403)
    lines = execution(repo, api, toml=setting("pool")).stdout.splitlines()
    assert lines[1] == (
        "execution: pool runs the heavy checks on a runner named by the repository variable "
        f"AGK_HEAVY_RUNNER, which cannot be read (refused); see {RUNNER_GUIDE}"
    )


def test_pool_with_the_variable_prints_one_line_and_never_the_value(repo, tmp_path):
    """REQ-039: brief #441 answer 3 (the variable set: no pointer; its value is never printed)."""
    proc = execution(repo, case(tmp_path), toml=setting("pool"))
    assert proc.stdout.splitlines() == [
        "execution: pool (recommended: hosted: 300 of 2000 included minutes used (15%), "
        "more than half left)"
    ]
    assert "self-hosted" not in proc.stdout


@pytest.mark.parametrize("value", ["hosted", "local"])
def test_hosted_or_local_never_reads_the_variable(repo, tmp_path, value):
    """REQ-039: brief #441 answer 3 (the variable matters only for pool and hybrid)."""
    api = case(tmp_path)
    refuse(api, "variable", 403)
    proc = execution(repo, api, toml=setting(value))
    assert len(proc.stdout.splitlines()) == 1
    assert report(repo, case(tmp_path / "j"), toml=setting(value))["runner"] is None


def test_json_shape(repo, tmp_path):
    """REQ-039: brief #441 answer 2 (`--json`)."""
    api = case(tmp_path)
    (api / "variable.json").unlink()
    data = report(repo, api, toml=setting("hybrid"))
    assert data == {
        "execution": "hybrid",
        "recommended": "hosted",
        "reason": "300 of 2000 included minutes used (15%), more than half left",
        "repository": "example/app",
        "private": True,
        "actions_enabled": True,
        "used": 300,
        "included": 2000,
        "warn_percent": 80,
        "runner": {"variable": "AGK_HEAVY_RUNNER", "state": "not set", "guide": RUNNER_GUIDE},
    }


def test_it_writes_nothing(repo, tmp_path):
    """REQ-039: brief #441 answer 3 (it changes no workflow and writes nothing)."""
    api = case(tmp_path)
    repo.write("agk.toml", setting("pool"))
    repo.write(".github/workflows/proof.yml", "on: push\n")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "seed")
    before = sorted(p.relative_to(repo.root).as_posix() for p in repo.root.rglob("*"))
    proc = repo.run("execution.py", "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout
    after = sorted(p.relative_to(repo.root).as_posix() for p in repo.root.rglob("*"))
    assert after == before
    assert repo.git("status", "--porcelain") == ""


@pytest.mark.parametrize(
    "args", [["--bogus"], ["--repo"], ["--api-dir"], ["--json", "--json", "x"]]
)
def test_usage_errors_exit_2(repo, tmp_path, args):
    """REQ-039: brief #441 answer 2 (usage)."""
    repo.write("agk.toml", 'default_branch = "main"\n')
    proc = repo.run("execution.py", *args)
    assert proc.returncode == 2
    assert "usage: execution.py" in proc.stderr


def test_it_has_no_api_path_of_its_own():
    """REQ-039: brief #441 answer 2 (it reads through minutes.py; no second API path, no write)."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "import subprocess" not in text
    assert "from minutes import" in text
    for verb in ("POST", "PUT", "PATCH", "DELETE"):
        assert f'"{verb}"' not in text


def test_help_runs_without_network(tmp_path):
    """REQ-039: brief #441 answer 4 (the script imports with the standard library only)."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", "-c", f"import runpy; runpy.run_path({str(SCRIPT)!r})"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr


# --- the kit: templates and manifest ----------------------------------------------------------


@pytest.mark.parametrize("template", ["kit/templates/agk.toml", "kit/templates/agk.adopt.toml"])
def test_templates_list_the_setting_commented_out(template):
    """REQ-039: brief #441 answer 1 (the templates list it, off: absent reads hosted)."""
    text = (KIT_ROOT / template).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert '# execution = "hosted"' in lines
    assert not any(ln.startswith("execution") for ln in lines)
    assert "python3 scripts/agk/execution.py" in text
    # still keeps the lock settings of brief #426
    assert "# lock_slots = 1" in lines


def test_the_manifest_installs_the_script():
    """REQ-039: brief #441 (the script is installed with the kit)."""
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/execution.py" in manifest["verbatim"]
