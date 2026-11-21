"""Plain claude opens the steward (SPEC-0066 rules 2, 4, 8 and 11, build (d); brief #1583).

REQ-073 AC1: `init`, `adopt` and `upgrade` write `"agent": "steward"` into the project's copy of
`.claude/settings.json`, one line after its opening brace, which the manifest's `project_keys`
names so that it never reads as a project change of a kit file; the kit's own copy holds no
`agent`; an upgrade that finds another value keeps it and names it in one line. REQ-073 AC4
(rule 11): the upgrade refuses, naming the setting, to write the key while an adapter does not
pass `--agent`. REQ-073 AC3: the plugin's `settings.json` names its steward, served from the one
role file. REQ-073 AC7: outside a git repository each steward script prints one line, exit 3, and
writes nothing; `steward.py first-run` names the first step (the kit, a project, the adopt offer,
the greeting, or a folder already greeted) and writes only the greeting mark, a hash of the folder
and the date, in the person's Claude folder. REQ-073 AC2 (rule 3): off the default branch, behind
`origin` or in another session's worktree the steward's start stops with one line and the fix and
changes nothing, and the start hook that the agent line brings prints the same line. Invented data
only; a local git fixture as `origin`; no network, no model.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import adopt
import common
import doctor
import init
import pytest
import steward
import upgrade

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
if not (ROOT / "kit" / "manifest.json").is_file():  # an install, or a copy of the kit's tests
    pytest.skip("reads the kit's own files (kit/ is kit-only)", allow_module_level=True)
SETTINGS = ".claude/settings.json"
KIT_SETTINGS = (ROOT / SETTINGS).read_bytes()
ROLE = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
FIRST_RUN = "docs/guides/steward-first-run.md"  # named by the role file (the answer on #1612)
GUIDE = (ROOT / FIRST_RUN).read_text(encoding="utf-8")
OUTSIDE = "outside: no project here"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, check=True, capture_output=True
    )


def repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main", cwd=path)
    return path


# --- rule 2: the project's agent line -----------------------------------------------------------


def test_the_kits_own_settings_hold_no_agent_and_the_manifest_names_the_key():
    assert "agent" not in json.loads(KIT_SETTINGS)
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_keys"] == {SETTINGS: ["agent", "hooks.SessionStart"]}
    assert SETTINGS in manifest["verbatim"]


def test_the_agent_line_is_added_read_and_taken_away_byte_for_byte():
    named = common.with_agent(KIT_SETTINGS, "steward")
    assert json.loads(named)["agent"] == "steward"
    assert named.splitlines()[1] == b'  "agent": "steward",'
    assert common.project_agent(named) == "steward"
    assert common.project_agent(KIT_SETTINGS) is None
    assert common.without_agent(SETTINGS, named) == KIT_SETTINGS
    assert common.with_agent(named, "architect") == common.with_agent(KIT_SETTINGS, "architect")
    assert common.without_agent("other.json", named) == named


def test_the_doctor_reads_the_agent_line_as_the_kits(tmp_path):
    named = common.with_agent(KIT_SETTINGS, "steward")
    assert doctor.same_file(SETTINGS, named, KIT_SETTINGS)
    assert not doctor.same_file(SETTINGS, named.replace(b'"Read"', b'"Write"'), KIT_SETTINGS)


def test_init_writes_the_steward_as_the_projects_agent(tmp_path):
    items, _, _ = init.build_items(repo(tmp_path / "p"), "2026-11-20")
    data = dict(items)[SETTINGS]
    assert json.loads(data)["agent"] == "steward"
    assert common.without_agent(SETTINGS, data) == KIT_SETTINGS


def test_adopt_writes_the_steward_as_the_projects_agent(tmp_path):
    plan, _, _ = adopt.build_plan(repo(tmp_path / "p"), "2026-11-20")
    data = next(content for rel, _, content, _ in plan if rel == SETTINGS)
    assert json.loads(data)["agent"] == "steward"


def project(tmp_path: Path, settings: bytes | None) -> Path:
    target = tmp_path / "p"
    (target / ".claude").mkdir(parents=True)
    if settings is not None:
        (target / SETTINGS).write_bytes(settings)
    return target


RELEASED = {hashlib.sha256(KIT_SETTINGS).hexdigest()}


def test_upgrade_writes_the_steward_into_a_released_copy(tmp_path):
    item = upgrade.settings_file(project(tmp_path, KIT_SETTINGS), KIT_SETTINGS, RELEASED, [])
    assert item.action == "replace"
    assert json.loads(item.content)["agent"] == "steward"


def test_upgrade_of_a_named_copy_is_unchanged_and_an_absent_one_is_created(tmp_path):
    named = common.with_agent(KIT_SETTINGS, "steward")
    item = upgrade.settings_file(project(tmp_path / "a", named), KIT_SETTINGS, RELEASED, [])
    assert (item.action, item.detail) == ("unchanged", "")
    item = upgrade.settings_file(project(tmp_path / "b", None), KIT_SETTINGS, set(), [])
    assert item.action == "create" and json.loads(item.content)["agent"] == "steward"


def test_upgrade_keeps_another_agent_and_names_it_in_one_line(tmp_path):
    own = common.with_agent(KIT_SETTINGS, "architect")
    item = upgrade.settings_file(project(tmp_path, own), KIT_SETTINGS, RELEASED, [])
    assert item.action == "unchanged"
    assert item.detail == " (agent kept: architect; setting: agent)"


def test_upgrade_still_refuses_a_settings_file_the_project_changed(tmp_path):
    changed = common.with_agent(KIT_SETTINGS.replace(b'"Read"', b'"Write"'), "steward")
    item = upgrade.settings_file(project(tmp_path, changed), KIT_SETTINGS, RELEASED, [])
    assert item.action == "conflict"


# --- rule 11: no agent while an adapter lacks --agent -------------------------------------------


def test_upgrade_refuses_the_agent_while_a_launch_adapter_lacks_it(tmp_path):
    target = project(tmp_path, KIT_SETTINGS)
    (target / "scripts").mkdir()
    (target / "scripts" / "own-start.sh").write_text('claude -p "$1"\n', encoding="utf-8")
    (target / "agk.toml").write_text(
        '[flow]\nlaunch_adapter = "bash scripts/own-start.sh"\n', encoding="utf-8"
    )
    plan = upgrade.Plan("1.0.0", "1.0.1", "init")
    plan.items = [upgrade.settings_file(target, KIT_SETTINGS, RELEASED, [])]
    upgrade.agent_refusal(target, plan)
    assert plan.items[0].action == "unchanged"
    assert plan.notes == [upgrade.AGENT_REFUSED]
    assert "[flow] launch_adapter" in upgrade.AGENT_REFUSED
    assert "own-start" not in upgrade.AGENT_REFUSED


def test_upgrade_refuses_the_agent_while_a_kept_kit_adapter_lacks_it(tmp_path):
    target = project(tmp_path, KIT_SETTINGS)
    (target / "scripts").mkdir()
    (target / "scripts" / "start-session-local.sh").write_text('claude -p "$p"\n', "utf-8")
    plan = upgrade.Plan("1.0.0", "1.0.1", "init")
    plan.items = [
        upgrade.settings_file(target, KIT_SETTINGS, RELEASED, []),
        upgrade.Item("scripts/start-session-local.sh", "conflict"),
    ]
    upgrade.agent_refusal(target, plan)
    assert plan.items[0].action == "unchanged" and plan.notes == [upgrade.AGENT_REFUSED]


def test_upgrade_writes_the_agent_when_the_new_adapter_passes_it(tmp_path):
    target = project(tmp_path, KIT_SETTINGS)
    new = b'claude --agent "$a" -p "$p"\n'
    plan = upgrade.Plan("1.0.0", "1.0.1", "init")
    plan.items = [
        upgrade.settings_file(target, KIT_SETTINGS, RELEASED, []),
        upgrade.Item("scripts/start-session-local.sh", "replace", content=new),
    ]
    upgrade.agent_refusal(target, plan)
    assert plan.items[0].action == "replace" and plan.notes == []


# --- rule 4: the plugin's default agent ---------------------------------------------------------


def test_the_plugin_names_its_steward_served_from_the_one_role_file():
    settings = json.loads((ROOT / ".claude-plugin" / "settings.json").read_text("utf-8"))
    assert settings == {"agent": "agk:steward"}
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    assert "./.claude/agents/steward.md" in plugin["agents"]
    assert not (ROOT / "agents").exists()


# --- rule 8: no traceback outside a project, and the first run ----------------------------------

OUTSIDE_RUNS = [
    ("steward.py", "start", "--session", "s-example-1"),
    ("steward_daily.py", "daily"),
    ("steward_evidence.py", "stage"),
    ("steward_onboard.py", "onboard"),
    ("steward_owner.py", "defects"),
]


@pytest.mark.parametrize("run", OUTSIDE_RUNS, ids=lambda r: r[0])
def test_each_steward_script_outside_git_prints_one_line_and_writes_nothing(tmp_path, run):
    folder = tmp_path / "empty"
    folder.mkdir()
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / run[0]), *run[1:]],
        cwd=folder,
        env=env,
        capture_output=True,
        text=True,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (3, OUTSIDE + "\n", "")
    assert list(folder.iterdir()) == []


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    claude = tmp_path / "home" / ".claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    return claude


def test_an_empty_folder_is_greeted_once_and_only_the_mark_is_written(tmp_path, home):
    folder = tmp_path / "empty"
    folder.mkdir()
    assert steward.first_run(folder, "2026-11-20") == "greet"
    assert steward.first_run(folder, "2026-11-21") == "greeted"
    assert list(folder.iterdir()) == []
    lines = (home / steward.GREETED).read_text(encoding="utf-8").splitlines()
    key = hashlib.sha256(str(folder.resolve()).encode("utf-8")).hexdigest()
    if sys.platform in ("win32", "darwin"):
        key = hashlib.sha256(str(folder.resolve()).casefold().encode("utf-8")).hexdigest()
    assert lines == [f"{key} 2026-11-20"]
    other = tmp_path / "other"
    other.mkdir()
    assert steward.first_run(other, "2026-11-20") == "greet"


def test_a_repository_without_agk_gets_the_adopt_offer_and_no_mark(tmp_path, home):
    folder = repo(tmp_path / "product")
    (folder / "sub").mkdir()
    assert steward.first_run(folder / "sub", "2026-11-20") == "adopt"
    assert not home.exists()


def test_an_agk_project_and_the_kit_get_no_greeting(tmp_path, home):
    folder = repo(tmp_path / "project")
    (folder / "agk.toml").write_text('mode = "init"\n', encoding="utf-8")
    assert steward.first_run(folder, "2026-11-20") == "project"
    assert steward.first_run(ROOT, "2026-11-20") == "kit"
    assert not home.exists()


def test_first_run_prints_its_step(tmp_path, home, capsys, monkeypatch):
    folder = tmp_path / "empty"
    folder.mkdir()
    monkeypatch.chdir(folder)
    assert steward.main(["first-run"]) == 0
    assert capsys.readouterr().out == "first-run: greet\n"


def greeting() -> list[str]:
    return [ln[2:] for ln in GUIDE.splitlines() if ln.startswith("> ")]


def test_the_role_file_names_the_guide_that_reads_the_outside_line_and_greets():
    assert f"`{FIRST_RUN}`" in ROLE and not [ln for ln in ROLE.splitlines() if ln.startswith("> ")]
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert FIRST_RUN in manifest["verbatim"] and FIRST_RUN in manifest["snapshot"]
    assert OUTSIDE in GUIDE and "python3 <kit>/steward.py first-run" in GUIDE
    lines = greeting()
    assert len(lines) == 3
    assert lines[0].startswith("👋 You've got AGK")
    assert "A · start a new product" in lines[2] and "C · just show me" in lines[2]
    for word in ("`", "/", ".py", "steward", "brief", "spec", "ADR", "pull request", "skill"):
        assert all(word not in line for line in lines), word


def test_the_guide_names_each_first_step():
    for step in ("greet", "greeted", "adopt", "project", "kit"):
        assert f"`{step}`" in GUIDE, step


def test_uninstall_reads_a_named_copy_as_the_kits(tmp_path):
    import uninstall

    table = json.loads((ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))
    released = {h for row in table["releases"].values() for h in row["verbatim"].get(SETTINGS, [])}
    named = common.with_agent(KIT_SETTINGS, "steward")
    assert hashlib.sha256(common.without_agent(SETTINGS, named)).hexdigest() in released | RELEASED
    assert common.without_agent(SETTINGS, named) == KIT_SETTINGS
    assert "without_agent(rel, data)" in (SCRIPTS / "uninstall.py").read_text(encoding="utf-8")
    assert uninstall.without_agent is common.without_agent


# --- rule 3: land on the default branch, or stop ------------------------------------------------

HOOK = ROOT / ".claude" / "hooks" / "branch_check.py"
FIX = "git switch main && git pull --ff-only"


def commit(cwd: Path, name: str) -> None:
    (cwd / name).write_text("example\n", encoding="utf-8")
    git("add", name, cwd=cwd)
    git("-c", "user.name=member-example-1", "-c", "user.email=m1@example.com",
        "commit", "-q", "-m", name, cwd=cwd)  # fmt: skip


@pytest.fixture
def clone(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.delenv("AGK_AGENT", raising=False)
    up = repo(tmp_path / "up")
    commit(up, "a.txt")
    git("clone", "-q", str(up), str(tmp_path / "p"), cwd=tmp_path)
    return tmp_path / "p"


def head(cwd: Path) -> str:
    return common.git(cwd, "rev-parse", "--abbrev-ref", "HEAD").strip()


def test_on_the_default_branch_and_up_to_date_the_steward_goes_on(clone, capsys, monkeypatch):
    assert common.branch_check(clone) is None
    monkeypatch.chdir(clone)
    assert steward.main(["branch"]) == 0
    assert capsys.readouterr().out == "branch: ok\n"


def test_on_another_branch_it_stops_with_the_fix_and_changes_nothing(clone):
    git("switch", "-q", "-c", "feature-example", cwd=clone)
    assert common.branch_check(clone) == f"branch: on feature-example, not main; fix: {FIX}"
    assert head(clone) == "feature-example"


def test_behind_origin_it_offers_the_pull(clone):
    commit(clone.parent / "up", "b.txt")
    assert common.branch_check(clone) == f"branch: main is 1 commit behind origin; fix: {FIX}"
    assert not (clone / "b.txt").exists()


def test_with_uncommitted_changes_it_names_their_count_and_changes_nothing(clone):
    git("switch", "-q", "-c", "feature-example", cwd=clone)
    (clone / "a.txt").write_text("changed\n", encoding="utf-8")
    (clone / "new.txt").write_text("new\n", encoding="utf-8")
    assert common.branch_check(clone) == (
        "branch: on feature-example, not main, with 2 uncommitted changes;"
        f" keep them or set them aside first, then: {FIX}"
    )
    assert (clone / "a.txt").read_text(encoding="utf-8") == "changed\n"


def test_in_a_builders_worktree_it_names_the_owner(clone):
    tree = clone.parent / "agk-cb-example"
    git("worktree", "add", "-q", "-b", "claude/brief-1", str(tree), cwd=clone)
    assert common.branch_check(tree) == (
        "branch: this folder is the worktree of cb-example; open the project's main folder instead"
    )


def test_in_its_own_detached_worktree_it_goes_on(clone):
    tree = clone.parent / "agk-steward"
    git("worktree", "add", "-q", "--detach", str(tree), "origin/main", cwd=clone)
    assert common.branch_check(tree) is None


def test_outside_git_or_with_no_origin_there_is_nothing_to_check(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    (tmp_path / "empty").mkdir()
    assert common.branch_check(tmp_path / "empty") is None
    assert common.branch_check(repo(tmp_path / "new")) is None


def test_start_off_the_default_branch_stops_before_it_writes(clone):
    git("switch", "-q", "-c", "feature-example", cwd=clone)
    code, lines = steward.start(clone, "s-example-1", None, None)  # no GitHub is reached
    assert (code, lines) == (1, [f"branch: on feature-example, not main; fix: {FIX}"])
    assert not (clone / ".agk").exists()


def hook(cwd: Path, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        cwd=cwd,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd), **env},
        input="{}",
        capture_output=True,
        text=True,
    )


def test_the_start_hook_prints_the_line_off_the_default_branch_and_nothing_on_it(clone):
    assert (hook(clone).returncode, hook(clone).stdout) == (0, "")
    git("switch", "-q", "-c", "feature-example", cwd=clone)
    found = hook(clone)
    assert (found.returncode, found.stdout) == (0, f"branch: on feature-example, not main; fix: {FIX}\n")
    assert hook(clone, AGK_AGENT="builder").stdout == ""  # a kit start of another role
    assert head(clone) == "feature-example"


def test_the_agent_line_brings_the_start_hook_and_the_kit_has_none():
    assert "SessionStart" not in json.loads(KIT_SETTINGS)["hooks"]
    named = json.loads(common.with_agent(KIT_SETTINGS, "steward"))
    [entry] = named["hooks"]["SessionStart"]
    assert entry["hooks"][0]["command"].endswith("/.claude/hooks/branch_check.py")
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert ".claude/hooks/branch_check.py" in manifest["verbatim"]
    assert "branch_check" in ROLE
