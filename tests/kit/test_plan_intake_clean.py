"""In a clean project the kit's scripts find the kit's own files in the plugin (brief #1826,
ADR-0759; SPEC-0043 rule 3, SPEC-0071 rule 2; REQ-078).

A clean project (`[kit] layout = "plugin"`) holds no data guard, no template, no principles and
no stack table: the plugin does. `plan_intake.py` passes its data guard gate on the plugin's guard
and the hook that runs it there, `review_context.assemble` carries the plugin's principles and
`playbook_format.stacks` reads the plugin's table. The clean project is made by `init.py --layout
plugin --rehearsal` in a temporary folder, the kit tree as the plugin; an installed project is
gated as today (`tests/kit/test_plan_intake.py`). Invented data only (example.com); no network.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import plan_intake  # noqa: E402
import playbook_format  # noqa: E402
import review_context  # noqa: E402

COMMANDS = (
    ["states"],
    ["validate", "--proposals", "proposals-example.json"],
    ["render", "--proposals", "proposals-example.json"],
    ["publish", "--comments", "comments-example.json", "--head", "a" * 40],
    ["openspec", "--slug", "orders-example", "--out", "out-example.md"],
    ["openspec-import", "missing-example", "--slug", "orders-example"],
)
PLUGIN_GUARDS = (
    "scripts/agk/guard.py",
    ".claude/hooks/data_guard.py",
    ".claude/hooks/plugin_hooks.py",
)


def environ(plugin: Path | None = KIT_ROOT) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_", "AGK_", "GIT_"))}
    if plugin is not None:
        env["CLAUDE_PLUGIN_ROOT"] = str(plugin)
    return env


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, local git
        ["git", "-c", "user.name=Example", "-c", "user.email=dev@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    """A clean project made by the kit's own `init.py`, the kit tree as the plugin."""
    root = tmp_path / "shop-example"
    root.mkdir()
    git(root, "init", "-q")
    made = subprocess.run(  # nosec B603 - the kit's own installer, no shell
        [sys.executable, str(SCRIPTS / "init.py"), str(root), "--layout", "plugin"]
        + ["--login-from-env", "--solo", "--unreleased", "--rehearsal"],
        cwd=tmp_path,
        env=environ() | {"AGK_SETUP_LOGIN": "example-owner"},
        capture_output=True,
        text=True,
    )
    assert made.returncode == 0, made.stdout + made.stderr
    assert 'layout = "plugin"' in (root / "agk.toml").read_text(encoding="utf-8")
    for rel in (*PLUGIN_GUARDS, "docs/specs/TEMPLATE.md", "constitution/principles.md"):
        assert not (root / rel).exists(), rel  # the clean layout keeps these in the plugin
    return root


def intake(root: Path, *args: str, plugin: Path | None = KIT_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - the kit's own script, no shell
        [sys.executable, str(SCRIPTS / "plan_intake.py"), *args, "--root", str(root)],
        cwd=root,
        env=environ(plugin),
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("args", COMMANDS, ids=lambda a: a[0])
def test_req078_every_command_passes_the_gate_in_a_clean_project(clean: Path, args) -> None:
    """REQ-078: the plugin's guard runs there, so no command stops at the gate."""
    out = intake(clean, *args)
    assert "data guard not installed" not in out.stdout + out.stderr, out.stdout


def test_req078_states_runs_in_a_clean_project(clean: Path) -> None:
    """REQ-078: the brief's measure: `states` prints `ok states (none to ask)`, exit 0."""
    out = intake(clean, "states")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip().splitlines()[-1] == "ok states (none to ask)"


def test_req078_states_runs_without_the_variable(clean: Path) -> None:
    """REQ-078: `CLAUDE_PLUGIN_ROOT` unset: the plugin this script sits in."""
    out = intake(clean, "states", plugin=None)
    assert out.returncode == 0, out.stdout + out.stderr


def test_req078_a_secret_in_a_clean_projects_source_is_refused_never_printed(
    clean: Path,
) -> None:
    """REQ-078, SPEC-0043 rule 3: the guard scans the clean project's sources as an installed
    one's; the value is built here, so no file of the kit holds one."""
    value = "ghp_" + "a1B2c3D4" * 4 + "a1B2"
    source = clean / "docs" / "sources" / "prd.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "Source: Example requirements\nKind: prd\nVersion: 1\nDate: 2026-10-02\n\n"
        f"# Orders\n\nOrders at example.com are listed by {value}.\n",
        encoding="utf-8",
    )
    out = intake(clean, "states")
    assert out.returncode == 1, out.stdout + out.stderr
    assert "docs/sources/prd.md" in out.stdout and "line 8, column " in out.stdout
    assert value not in out.stdout + out.stderr and "ghp_" not in out.stdout + out.stderr


def stub_plugin(tmp_path: Path, missing: str) -> Path:
    """The kit's tree copied as a plugin of the same version, less one file of the guard."""
    plugin = tmp_path / "plugin-example"
    (plugin / ".claude-plugin").mkdir(parents=True)
    shutil.copy(KIT_ROOT / ".claude-plugin" / "plugin.json", plugin / ".claude-plugin")
    for rel in (*PLUGIN_GUARDS, "scripts/agk/kit_root.py"):
        if rel != missing:
            (plugin / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(KIT_ROOT / rel, plugin / rel)
    return plugin


@pytest.mark.parametrize("missing", PLUGIN_GUARDS)
def test_req078_a_plugin_without_a_guard_file_exits_2_naming_it(
    clean: Path, tmp_path: Path, missing: str
) -> None:
    """REQ-078, SPEC-0043 rule 3: whether it is installed, never a setting: a plugin that lacks
    the guard, its hook or the hook that runs it there stops every command, exit 2."""
    plugin = stub_plugin(tmp_path, missing)
    for args in COMMANDS:
        out = intake(clean, *args, plugin=plugin)
        assert out.returncode == 2, (args, out.stdout + out.stderr)
        line = (
            f"data guard not installed: ${{CLAUDE_PLUGIN_ROOT}}/{missing} (setting: [kit] layout)"
        )
        assert out.stdout.strip() == line, out.stdout
        assert str(tmp_path) not in out.stdout + out.stderr


def test_req078_the_installed_gate_is_unchanged(tmp_path: Path, monkeypatch, capsys) -> None:
    """REQ-050 AC1, REQ-078: an installed project checks its own two files, never the plugin's."""
    root = tmp_path / "installed-example"
    root.mkdir()
    (root / "agk.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))
    assert plan_intake.guard_missing(root) == "scripts/agk/guard.py"
    for rel in plan_intake.GUARDS:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("# placeholder\n", encoding="utf-8")
    assert plan_intake.guard_missing(root) is None
    (
        root / ".claude/hooks/data_guard.py"
    ).unlink()  # the plugin's hook runs, still refused (Q-G1-3)
    assert plan_intake.main(["states", "--root", str(root)]) == 2
    assert "data guard not installed: .claude/hooks/data_guard.py" in capsys.readouterr().out


def test_req078_another_layout_is_refused_naming_the_setting(tmp_path: Path, capsys) -> None:
    """REQ-078: another `[kit] layout` value is `kit_root.layout`'s refusal, exit 1."""
    root = tmp_path / "sideways-example"
    root.mkdir()
    (root / "agk.toml").write_text('[kit]\nlayout = "sideways-example"\n', encoding="utf-8")
    assert plan_intake.main(["states", "--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "(setting: layout)" in out and "sideways-example" not in out


def test_req078_the_review_context_carries_the_plugins_principles(clean: Path, monkeypatch) -> None:
    """REQ-078: `/agk:review` in a clean project reads `constitution/principles.md` from the
    plugin, so its context names no missing principles."""
    git(clean, "add", "-A")
    git(clean, "commit", "-q", "-m", "start")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))
    text = review_context.assemble(clean, "HEAD", "Advances: REQ-001\n")
    assert "constitution/principles.md is missing" not in text
    first = (KIT_ROOT / "constitution/principles.md").read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("1. ") and line in text for line in first)


def test_req078_the_stack_table_is_the_plugins_in_a_clean_project(clean: Path, monkeypatch) -> None:
    """REQ-078: `[[standards]]` stacks are checked against the plugin's table, never skipped."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))
    assert playbook_format.stacks(clean) == playbook_format.stacks(KIT_ROOT)
    assert playbook_format.stacks(clean)


def test_req078_an_installed_project_without_a_stack_table_still_skips(tmp_path: Path) -> None:
    """REQ-078: the installed layout reads its own table as today: absent, None."""
    root = tmp_path / "installed-example"
    root.mkdir()
    (root / "agk.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
    assert playbook_format.stacks(root) is None


# --- render names the plugin's playbook (brief #1887, ADR-0781; REQ-078) ---


def designed(root: Path) -> Path:
    """The clean project with the plan sources, an invented design import and a work type."""
    from test_plan_intake import PRD, PRD_TEXT, SOW, SOW_TEXT, write
    from test_plan_render import REQUIREMENTS
    from test_plan_slices import INVENTORY, PARTS, PARTS_TEXT, PROTO, PROTO_TEXT, SIGNOFFS

    for rel, text in (
        (SOW, SOW_TEXT),
        (PRD, PRD_TEXT),
        ("docs/requirements.md", REQUIREMENTS),
        (PROTO, PROTO_TEXT),
        (PARTS, PARTS_TEXT),
        ("docs/design/inventory.md", INVENTORY),
        ("docs/design/signoffs.md", SIGNOFFS),
    ):
        write(root, rel, text)
    config = root / "agk.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + '\n[delivery]\nwork_type = "web-app"\n',
        encoding="utf-8",
    )
    return root


def sliced_file(root: Path) -> Path:
    import json

    from test_plan_slices import sliced

    data = sliced()
    data["briefs"][0]["foundation"] = True  # SPEC-0072 rule 4: a work-type plan's foundation
    # brief #1910: the first milestone ends with one slice brief after the foundation
    cut = {k: v for k, v in data["briefs"][1].items() if k != "screens"}
    data["briefs"].append(cut | {"key": "B3", "milestone": "M1", "depends_on": ["B1"], "slice": True})
    path = root.parent / "proposals-example.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


LINE = (
    "Milestone order for the person: demo value: the joins that show the most in a demo"
    " come first (playbook config/playbooks/web-app.toml)"
)


@pytest.mark.parametrize("plugin", [KIT_ROOT, None], ids=["variable", "unset"])
def test_req078_render_names_the_plugins_playbook_in_a_clean_project(
    clean: Path, plugin: Path | None
) -> None:
    """REQ-078: the brief's measure: with no project `config/playbooks/`, `render` exits 0, prints
    the path class of the plugin's playbook (never the plugin's folder) and writes the plan."""
    designed(clean)
    assert not (clean / "config/playbooks").exists()
    out = intake(clean, "render", "--proposals", str(sliced_file(clean)), plugin=plugin)
    assert out.returncode == 0, out.stdout + out.stderr
    assert LINE in out.stdout.splitlines()
    assert str(KIT_ROOT) not in out.stdout + out.stderr
    assert (clean / "docs/plan/milestones.md").is_file()


def test_req078_render_names_the_projects_own_playbook_the_same_way(clean: Path) -> None:
    """REQ-078, ADR-0697: the project's own `web-app.toml` wins; the line is the same text."""
    designed(clean)
    source = (KIT_ROOT / "config/playbooks/web-app.toml").read_text(encoding="utf-8")
    own = clean / "config/playbooks/web-app.toml"
    own.parent.mkdir(parents=True)
    own.write_text(source, encoding="utf-8")
    assert playbook_format.selected(clean) == own
    out = intake(clean, "render", "--proposals", str(sliced_file(clean)))
    assert out.returncode == 0, out.stdout + out.stderr
    assert LINE in out.stdout.splitlines()


def test_req078_the_line_never_resolves_the_root(tmp_path: Path, monkeypatch) -> None:
    """REQ-078: a plugin on another tree (another drive on Windows) and a relative root: no
    `relative_to` is called, so the text is the forward-slash path class."""
    monkeypatch.chdir(tmp_path)
    other = tmp_path / "elsewhere-example" / "web-app.toml"
    other.parent.mkdir()
    other.write_text('[milestones]\nbatch_by = "demo value"\n', encoding="utf-8")
    monkeypatch.setattr(playbook_format, "split", lambda root: (["line"], []))
    monkeypatch.setattr(playbook_format, "selected", lambda root: other)
    line = plan_intake.milestone_order(Path("."))
    head = "Milestone order for the person: demo value"
    assert line == f"{head} (playbook config/playbooks/web-app.toml)"
