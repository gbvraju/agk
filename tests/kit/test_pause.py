"""Pause and resume (brief #348 build (a), answers 1 and 5; ADR-0196; REQ-009).

`paused = true` in agk.toml makes governance and proof report success with the one line
"agk paused", the router write nothing, the conductor and builder roles stop with that line, and
the doctor report `paused`; removing the line resumes. No network: `gh` is a stub that records
every call.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from common import CheckError, paused

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
DOCTOR = SCRIPTS / "doctor.py"
ROUTE = SCRIPTS / "route.py"
WORKFLOWS = ROOT / ".github" / "workflows"
LINE = "agk paused"
BASE_TOML = 'version = "0.59.0"\ndefault_branch = "main"\n'
PAUSED_TOML = BASE_TOML + "paused = true\n"
REPO = "owner/proj"


def clean_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env.update(extra)
    return env


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    (root / "config").mkdir()
    (root / "config" / "reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [maintainer]\n", encoding="utf-8"
    )
    (root / "agk.toml").write_text(BASE_TOML, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def stub_gh(tmp: Path) -> Path:
    """A `gh` that records every call and fails, so a run that reads or writes GitHub shows it."""
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp / "gh-calls"
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit 1\n', encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    return log


def run(script: Path, *args: str, cwd: Path, path: str | None = None, **extra: str):
    env = clean_env(**extra)
    if path is not None:
        env["PATH"] = f"{path}{os.pathsep}{env['PATH']}"
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


# --- the setting (answer 1) ---------------------------------------------------------------------


def test_the_setting_is_off_when_absent_and_on_only_for_true(proj):
    """REQ-009: answer 1 (`paused = true` pauses; absent or false does not)."""
    assert paused(proj) is False
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    assert paused(proj) is True
    (proj / "agk.toml").write_text(BASE_TOML + "paused = false\n", encoding="utf-8")
    assert paused(proj) is False
    (proj / "agk.toml").unlink()
    assert paused(proj) is False


def test_a_value_that_is_not_a_boolean_is_refused_by_the_setting_name(proj):
    """REQ-009: answer 1 (a refusal names the setting, never the value)."""
    (proj / "agk.toml").write_text(BASE_TOML + 'paused = "sesame"\n', encoding="utf-8")
    with pytest.raises(CheckError) as err:
        paused(proj)
    assert "setting: paused in agk.toml" in str(err.value) and "sesame" not in str(err.value)


def test_a_paused_line_inside_a_table_does_not_pause(proj):
    """REQ-009: answer 1 (the setting is a top-level line of agk.toml)."""
    (proj / "agk.toml").write_text(BASE_TOML + "[flow]\npaused = true\n", encoding="utf-8")
    assert paused(proj) is False


def test_the_setting_is_read_at_a_commit_when_a_ref_is_given(proj):
    """REQ-009: answer 1 (a pull request is judged by its base: the pausing one in full)."""
    base = git(proj, "rev-parse", "HEAD").strip()
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    git(proj, "commit", "-q", "-am", "pause")
    head = git(proj, "rev-parse", "HEAD").strip()
    assert paused(proj, base) is False
    assert paused(proj, head) is True
    git(proj, "rm", "-q", "agk.toml")
    git(proj, "commit", "-q", "-m", "no agk.toml")
    assert paused(proj, "HEAD") is False


# --- the doctor (answer 5) ----------------------------------------------------------------------


def test_doctor_paused_prints_the_one_line_and_resumes_when_the_line_is_removed(proj, tmp_path):
    """REQ-009: answers 1 and 5 (the query form reads only the file: no `gh` call)."""
    log = stub_gh(tmp_path)
    proc = run(DOCTOR, "--paused", cwd=proj, path=str(tmp_path / "bin"))
    assert (proc.returncode, proc.stdout) == (0, "agk not paused\n"), proc.stdout + proc.stderr
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    proc = run(DOCTOR, "--paused", cwd=proj, path=str(tmp_path / "bin"))
    assert (proc.returncode, proc.stdout) == (0, LINE + "\n"), proc.stdout + proc.stderr
    (proj / "agk.toml").write_text(BASE_TOML, encoding="utf-8")
    proc = run(DOCTOR, "--paused", str(proj), cwd=tmp_path, path=str(tmp_path / "bin"))
    assert (proc.returncode, proc.stdout) == (0, "agk not paused\n"), proc.stdout + proc.stderr
    assert not log.exists()


def test_doctor_paused_reads_the_ref_it_is_given(proj, tmp_path):
    """REQ-009: answers 1 and 5 (`--ref` reads agk.toml at that commit, not the work tree)."""
    base = git(proj, "rev-parse", "HEAD").strip()
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    git(proj, "commit", "-q", "-am", "pause")
    assert run(DOCTOR, "--paused", "--ref", base, cwd=proj).stdout == "agk not paused\n"
    assert run(DOCTOR, "--paused", "--ref", "HEAD", cwd=proj).stdout == LINE + "\n"
    proc = run(DOCTOR, "--paused", "--ref", "no-such-ref", cwd=proj)
    assert proc.returncode != 0 and "no-such-ref" not in proc.stdout


def test_doctor_paused_refuses_a_bad_value_by_the_setting_name(proj):
    """REQ-009: answer 5 (a refusal names the setting, never the value)."""
    (proj / "agk.toml").write_text(BASE_TOML + "paused = 1\n", encoding="utf-8")
    proc = run(DOCTOR, "--paused", cwd=proj)
    assert proc.returncode == 1 and "setting: paused in agk.toml" in proc.stdout


def test_the_doctor_report_shows_paused_as_its_own_state(proj, tmp_path):
    """REQ-009: answer 5 (reported `paused`, not failed; nothing is read from GitHub)."""
    log = stub_gh(tmp_path)
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    proc = run(DOCTOR, cwd=proj, path=str(tmp_path / "bin"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "agk doctor 0.59.0"
    assert lines[1].startswith("paused agk paused")
    assert "paused = true" in proc.stdout and "FAIL" not in proc.stdout
    assert lines[-1] == "summary: paused"
    proc = run(DOCTOR, "--json", cwd=proj, path=str(tmp_path / "bin"))
    data = json.loads(proc.stdout)
    assert proc.returncode == 0
    assert data["state"] == "paused" and data["checks"] == [] and data["doctor"] == "0.59.0"
    assert not log.exists()


def test_the_doctor_report_runs_its_checks_again_once_resumed(proj, tmp_path):
    """REQ-009: answer 5 (removing the line resumes the usual report)."""
    stub_gh(tmp_path)
    proc = run(DOCTOR, "--json", cwd=proj, path=str(tmp_path / "bin"))
    data = json.loads(proc.stdout)
    assert "state" not in data and data["checks"], proc.stdout


# --- the router (answer 1) ----------------------------------------------------------------------


def route(proj: Path, tmp_path: Path, *args: str):
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "pull_request": {"number": 7},
                "repository": {"full_name": REPO, "default_branch": "main"},
            }
        ),
        encoding="utf-8",
    )
    return run(
        ROUTE,
        *args,
        cwd=proj,
        path=str(tmp_path / "bin"),
        GITHUB_EVENT_NAME="pull_request",
        GITHUB_EVENT_PATH=str(event),
        GITHUB_REPOSITORY=REPO,
    )


@pytest.mark.parametrize("args", [(), ("--all",), ("--branch",), ("--pr", "7")])
def test_a_paused_router_writes_no_label_and_reads_nothing(proj, tmp_path, args):
    """REQ-009: answer 1 (the router writes no label while paused, whatever it routes)."""
    log = stub_gh(tmp_path)
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    proc = route(proj, tmp_path, *args)
    assert (proc.returncode, proc.stdout) == (0, LINE + "\n"), proc.stdout + proc.stderr
    assert not log.exists()


def test_a_resumed_router_routes_again(proj, tmp_path):
    """REQ-009: answer 1 (removing the line resumes: the router calls GitHub again)."""
    log = stub_gh(tmp_path)
    proc = route(proj, tmp_path)
    assert LINE not in proc.stdout
    assert log.exists() and log.read_text(encoding="utf-8").strip()


# --- governance and proof (answer 1) ------------------------------------------------------------


def workflow(name: str) -> str:
    """Read when a test runs: a copy of the kit tests in a project may have no workflows."""
    path = WORKFLOWS / name
    if not path.is_file():
        pytest.skip(f"{name} is not installed here")
    return path.read_text(encoding="utf-8")


def step_blocks(text: str) -> list[tuple[str, str]]:
    """(name or `uses`, block) of each step of the one job, in order."""
    out = []
    for block in re.split(r"(?m)^      - ", text.split("    steps:\n", 1)[1])[1:]:
        named = re.search(r"(?m)^(?:\s*)name: (.+)$", block)
        uses = re.match(r"uses: (\S+)", block)
        label = named.group(1).strip().strip('"') if named else (uses.group(1) if uses else "")
        if uses and not block.startswith("name:"):
            label = uses.group(1)
        out.append((label, block))
    return out


def condition(block: str) -> str:
    found = re.search(r"(?m)^        if: (.+)$", block)
    return found.group(1) if found else ""


@pytest.mark.parametrize("name", ["governance.yml", "proof.yml"])
def test_every_step_after_the_paused_step_is_skipped_while_paused(name):
    """REQ-009: answer 1 (success: the Paused step runs and every later step is skipped)."""
    blocks = step_blocks(workflow(name))
    labels = [label for label, _ in blocks]
    assert "Paused" in labels
    at = labels.index("Paused")
    assert [label.split("@")[0] for label in labels[:at]] == [
        "actions/checkout",
        "Base of the merge ref",
        "actions/setup-python",
    ]
    assert "id: paused" in blocks[at][1] and not condition(blocks[at][1])
    for label, block in blocks[at + 1 :]:
        cond = condition(block)
        if label == "outcome: skipped":
            assert "steps.paused.outputs.paused == 'true'" in cond, label
        else:
            assert "steps.paused.outputs.paused != 'true'" in cond, label


def paused_step(name: str) -> str:
    block = dict(step_blocks(workflow(name)))["Paused"]
    script = block.split("run: |\n", 1)[1]
    lines = [
        line[10:] if line.startswith(" " * 10) else line.strip() for line in script.splitlines()
    ]
    text = "\n".join(lines)
    return text.replace("python3 scripts/agk/doctor.py", f'"{sys.executable}" "{DOCTOR}"')


def run_step(name: str, proj: Path, tmp_path: Path, base: str | None):
    out, summary = tmp_path / "out", tmp_path / "summary"
    out.write_text("", encoding="utf-8")
    summary.write_text("", encoding="utf-8")
    env = clean_env(GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(summary))
    if base is not None:
        env["AGK_BASE"] = base
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", "-e", "-c", paused_step(name)], cwd=proj, capture_output=True, text=True, env=env
    )
    return proc, out.read_text(encoding="utf-8"), summary.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["governance.yml", "proof.yml"])
def test_the_paused_step_reads_the_base_of_a_pull_request(name, proj, tmp_path):
    """REQ-009: answer 1 (a paused base: one line; the pausing pull request is checked in full)."""
    unpaused = git(proj, "rev-parse", "HEAD").strip()
    (proj / "agk.toml").write_text(PAUSED_TOML, encoding="utf-8")
    git(proj, "commit", "-q", "-am", "pause")
    pausing = git(proj, "rev-parse", "HEAD").strip()
    proc, out, summary = run_step(name, proj, tmp_path, base=unpaused)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "paused=false" in out and LINE not in proc.stdout
    proc, out, summary = run_step(name, proj, tmp_path, base=pausing)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == LINE + "\n" and "paused=true" in out and LINE in summary
    proc, out, _ = run_step(name, proj, tmp_path, base=None)  # a push: the commit pushed
    assert proc.stdout == LINE + "\n" and "paused=true" in out


@pytest.mark.parametrize("name", ["governance.yml", "proof.yml"])
def test_the_paused_step_fails_on_a_bad_value(name, proj, tmp_path):
    """REQ-009: answer 1 (a value that is not a boolean fails the job; it never skips a check)."""
    (proj / "agk.toml").write_text(BASE_TOML + 'paused = "yes"\n', encoding="utf-8")
    proc, out, _ = run_step(name, proj, tmp_path, base=None)
    assert proc.returncode != 0 and "paused=true" not in out
    # the verdict on f66c933, finding 1: the step says why it failed, by the setting's name
    assert "setting: paused in agk.toml" in proc.stdout and "yes" not in proc.stdout
    git(proj, "commit", "-q", "-am", "a bad value")
    proc, out, _ = run_step(name, proj, tmp_path, base=git(proj, "rev-parse", "HEAD").strip())
    assert proc.returncode != 0 and "paused=true" not in out
    assert "setting: paused in agk.toml" in proc.stdout


# --- the roles (answer 1) -----------------------------------------------------------------------


def test_the_session_rules_stop_a_paused_builder():
    """REQ-009: answer 1 (the builder role stops with the one line)."""
    text = (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    rule = next(line for line in text.splitlines() if "doctor.py --paused" in line)
    assert LINE in rule and "stops" in rule and "posts nothing" in rule
    # the verdict on f66c933, finding 2: the default branch is read after a fetch, not the
    # session's own branch, so a pause merged after the branch was made is seen
    assert "git fetch origin <default branch>" in rule
    assert "doctor.py --paused --ref origin/<default branch>" in rule


def test_the_conductor_role_stops_when_paused():
    """REQ-009: answer 1 (the conductor role stops with the one line)."""
    path = ROOT / ".claude" / "agents" / "conductor.md"
    if not path.is_file():
        pytest.skip("the conductor role is not installed here")
    text = path.read_text(encoding="utf-8")
    assert "paused = true" in text and f"`{LINE}`" in text
    # the verdict on f66c933, finding 2: read at the default branch after a fetch, by the two
    # commands its guard allows
    para = next(line for line in text.splitlines() if line.startswith("Paused ("))
    # the verdict on c5fffcf: one GET that reads the default branch directly, and that the guards
    # allow, so the role and the guard cannot drift apart
    command = (
        'gh api -H "Accept: application/vnd.github.raw" repos/{owner}/{repo}/contents/agk.toml'
    )
    assert f"`{command}`" in para and "git show" not in para
    hooks = ROOT / ".claude" / "hooks"
    if not (hooks / "conductor_guard.py").is_file():
        pytest.skip("the guards are not installed here")
    sys.path.insert(0, str(hooks))
    import architect_guard
    import conductor_guard

    real = command.replace("{owner}/{repo}", REPO)
    assert conductor_guard.bash_allowed(real) and architect_guard.bash_allowed(real)
    rules = (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    rule = next(line for line in rules.splitlines() if "doctor.py --paused" in line)
    assert f"`{command}`" in rule and "git show" not in rule
