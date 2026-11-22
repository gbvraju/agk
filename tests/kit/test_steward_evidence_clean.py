"""The steward's skill lookup reads the role file from the plugin in a clean project (brief #1667,
ADR-0694; SPEC-0059 rule 19, SPEC-0071 rule 2; REQ-078).

The project's own `.claude/agents/steward.md` wins when it exists; in a clean project
(`[kit] layout = "plugin"`) the plugin's copy is read; when neither can be read the lookup
refuses one line naming the path class `.claude/agents/`, never a traceback. Temporary folders
and invented data only (example.com); no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import kit_root  # noqa: E402
import steward_evidence as ev  # noqa: E402
from common import CheckError, personal_table  # noqa: E402

TABLE = "| Stage or step | Skill |\n|---|---|\n| start | `start-example` |\n"


def plugin_version() -> str:
    """The kit checkout's plugin version, read when a test needs it, never at import: a copy of
    `scripts/agk` and `tests/kit` alone has no `.claude-plugin/` (test_agk_mk AC1, #1676)."""
    manifest = KIT_ROOT / ".claude-plugin" / "plugin.json"
    return json.loads(manifest.read_text("utf-8"))["version"]


def project(tmp_path: Path, layout: str | None = "plugin", pin: str = "0.1.0") -> Path:
    root = tmp_path / "shop-example"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed argv
    kit = "" if layout is None else f'\n[kit]\nlayout = "{layout}"\nplugin_version = "{pin}"\n'
    (root / "agk.toml").write_text(f'version = "{pin}"\n{kit}', encoding="utf-8")
    return root


def plugin(tmp_path: Path, table: str | None = TABLE) -> Path:
    """A stub plugin: its manifest, its resolver and, unless `table` is None, the role file."""
    root = tmp_path / "plugin-example"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"version": "0.1.0"}', "utf-8")
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / "scripts" / "agk" / "kit_root.py").write_text("# stub\n", "utf-8")
    if table is not None:
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / "steward.md").write_text(table, "utf-8")
    return root


def test_req078_a_clean_project_reads_the_plugins_role_file(tmp_path):
    """REQ-078: no role file in the project, so the plugin's table answers."""
    root = project(tmp_path)
    env = {"CLAUDE_PLUGIN_ROOT": str(plugin(tmp_path))}
    assert ev.skill_line(root, "start", env) == "skill: `start-example`"


def test_req078_the_projects_own_role_file_wins(tmp_path):
    """REQ-078: a project that carries the role file reads its own, in either layout."""
    for layout in ("plugin", "installed"):
        root = project(tmp_path / layout, layout)
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / "steward.md").write_text(
            TABLE.replace("start-example", "own-example"), "utf-8"
        )
        env = {"CLAUDE_PLUGIN_ROOT": str(plugin(tmp_path / layout))}
        assert ev.skill_line(root, "start", env) == "skill: `own-example`"


@pytest.mark.parametrize("layout", ["plugin", "installed", None])
def test_req078_neither_role_file_is_one_refusal_naming_the_path_class(tmp_path, layout):
    """REQ-078: a plugin without the role file, or an installed project without it, refuses
    naming `.claude/agents/`."""
    root = project(tmp_path, layout)
    env = {"CLAUDE_PLUGIN_ROOT": str(plugin(tmp_path, table=None))}
    with pytest.raises(CheckError) as found:
        ev.skill_line(root, "start", env)
    assert "(path class: .claude/agents/)" in str(found.value)
    assert str(tmp_path) not in str(found.value)


def test_req078_a_folder_that_is_not_a_plugin_is_refused_naming_the_variable(tmp_path, monkeypatch):
    """REQ-078: `CLAUDE_PLUGIN_ROOT` names a folder that is not a plugin and no plugin holds the
    resolver either, so `kit_root.plugin_root` refuses naming the variable."""
    root = project(tmp_path)
    (tmp_path / "not-a-plugin").mkdir()
    monkeypatch.setattr(kit_root, "HERE", tmp_path / "x" / "y" / "z")
    env = {"CLAUDE_PLUGIN_ROOT": str(tmp_path / "not-a-plugin")}
    with pytest.raises(kit_root.Refused, match=r"\(setting: CLAUDE_PLUGIN_ROOT\)"):
        ev.skill_line(root, "start", env)


def test_req078_another_layout_is_refused_naming_the_setting(tmp_path):
    """REQ-078: a `[kit] layout` that is neither value is refused naming `layout`."""
    root = project(tmp_path, "sideways-x")
    with pytest.raises(kit_root.Refused, match=r"\(setting: layout\)"):
        ev.skill_line(root, "start", {})


def run(root: Path, **env: str) -> subprocess.CompletedProcess:
    full = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"} | env
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "steward_evidence.py"), "skill", "--step", "start"],
        cwd=root,
        capture_output=True,
        text=True,
        env=full,
    )


def test_req078_the_command_reads_the_running_plugins_file_in_a_clean_project(tmp_path):
    """REQ-078 measured: `skill --step start` in a clean project passes (exit 0), with the kit
    checkout as the running plugin."""
    root = project(tmp_path, pin=plugin_version())
    done = run(root, CLAUDE_PLUGIN_ROOT=str(KIT_ROOT))
    assert (done.returncode, done.stdout) == (0, "skill: `start`\n"), done.stderr


def test_req078_the_command_refuses_one_line_and_no_traceback(tmp_path):
    """REQ-078: an installed project without the role file: exit 2, one `refused:` line."""
    root = project(tmp_path, None, plugin_version())
    done = run(root)
    assert done.returncode == 2 and "Traceback" not in done.stderr
    assert done.stderr.splitlines() == [
        "refused: the steward's role file cannot be read (path class: .claude/agents/)"
    ]


def test_req078_another_plugin_version_is_refused_naming_the_setting(tmp_path):
    """REQ-078: a pin that is not the running plugin's stops the command (plugin_version)."""
    root = project(tmp_path, pin="0.0.1")
    done = run(root, CLAUDE_PLUGIN_ROOT=str(KIT_ROOT))
    assert done.returncode == 1 and "(setting: plugin_version)" in done.stderr


def test_req078_with_the_variable_unset_the_running_plugins_file_answers(tmp_path):
    """REQ-078 answer 3: `CLAUDE_PLUGIN_ROOT` unset in a clean project, so `kit_root.plugin_root`
    finds the plugin this script runs from (the kit checkout) and its role file answers."""
    root = project(tmp_path)
    assert ev.skill_line(root, "start", {}) == "skill: `start`"


@pytest.mark.parametrize("own", [True, False])
def test_req078_a_sidecar_reads_the_role_file_the_same_way(tmp_path, own):
    """REQ-078 answer 3, personal mode: a sidecar (a root whose `agk.toml` has a `[personal]`
    table, `common.PERSONAL_TABLE`) reads its own role file, else the plugin's, as a project."""
    root = project(tmp_path)
    with (root / "agk.toml").open("a", encoding="utf-8") as out:
        out.write('\n[personal]\nforge = "files"\n')
    assert personal_table(root) is not None  # the fixture is a sidecar
    if own:
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / "steward.md").write_text(
            TABLE.replace("start-example", "own-example"), "utf-8"
        )
    env = {"CLAUDE_PLUGIN_ROOT": str(plugin(tmp_path))}
    want = "own-example" if own else "start-example"
    assert ev.skill_line(root, "start", env) == f"skill: `{want}`"
