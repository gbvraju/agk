"""Each role file that has Bash names the governance command its own guard allows, in both layouts
(brief #1841, ADR-0772; REQ-078).

Every role file under `.claude/agents/` whose tools include Bash (a file with no `tools:` line has
every tool) holds one line starting `Governance:` with two forms in code spans: the installed one
first, then the clean one (`[kit] layout = "plugin"`), `<plugin>` standing for the plugin's folder
written out, since no shipped file names the plugin variable (ADR-0630). In a stub installed project the installed
form runs through the role's guard as its frontmatter hook runs it (the builder has none: the data
guard of `.claude/settings.json`); in a stub clean project made by `init.py --layout plugin
--rehearsal`, the clean form, `<plugin>` the stub plugin's folder, runs through `plugin_hooks.py pre` with `agent_type`
`agk:<role>`. Each must be allowed; the clean form with the variable typed in stays denied for the
four reviewing roles (ADR-0736 decision 4). Failures name the path class and the file, never the
line. Temporary folders and the kit checkout only; no network; invented data only (example.com).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT

AGENTS = KIT_ROOT / ".claude" / "agents"
CLASS = ".claude/agents/"
PLUGIN = "<plugin>"  # the plugin's folder written out (ADR-0630: no shipped file names the variable)
VARIABLE = "${CLAUDE_PLUGIN_ROOT}"
SCRATCH = "<scratch>"
SPAN = re.compile(r"`([^`]*kit_root\.py[^`]*)`")
# The guard each role's frontmatter hook runs; the builder's is the project's data guard.
GUARDS = {
    "steward": ("steward_guard.py",),
    "builder": ("data_guard.py",),
    "architect": ("architect_guard.py",),
    "architect-review": ("architect_guard.py", "--review"),
    "conductor": ("conductor_guard.py",),
    "shadow": ("conductor_guard.py", "--shadow"),
}
SCRATCH_ROLES = ("conductor", "shadow")
VARIABLE_DENIED = ("architect", "architect-review", "conductor", "shadow")


def frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
    return "\n".join(lines[1:end])


def has_bash(text: str) -> bool:
    tools = re.search(r"^tools:\s*(.*)$", frontmatter(text), re.M)
    return tools is None or "Bash" in re.split(r"[,\s]+", tools.group(1))


def bash_roles() -> list[str]:
    return sorted(p.stem for p in AGENTS.glob("*.md") if has_bash(p.read_text(encoding="utf-8")))


def governance_forms(text: str) -> tuple[str, str] | None:
    """(installed, clean) of the one `Governance:` line, or None."""
    lines = [line for line in text.splitlines() if line.startswith("Governance:")]
    if len(lines) != 1:
        return None
    spans = SPAN.findall(lines[0])
    return (spans[0], spans[1]) if len(spans) == 2 else None


def missing_lines(texts: dict[str, str]) -> list[str]:
    return [
        f"{CLASS}: {CLASS}{role}.md has Bash and no governance line (setting: tools)"
        for role, text in sorted(texts.items())
        if has_bash(text) and governance_forms(text) is None
    ]


# --- the stubs ------------------------------------------------------------------------------------


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)  # nosec B603 B607 - a fixed git init, no shell
    return path


@pytest.fixture(scope="module")
def plugin(tmp_path_factory) -> Path:
    stub = tmp_path_factory.mktemp("plugin")
    for part in (".claude-plugin", ".claude/hooks", ".claude/agents", "scripts/agk"):
        shutil.copytree(KIT_ROOT / part, stub / part, ignore=shutil.ignore_patterns("__pycache__"))
    return stub.resolve()


@pytest.fixture(scope="module")
def systmp(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("systmp").resolve()


@pytest.fixture(scope="module")
def installed(tmp_path_factory) -> Path:
    root = git_repo(tmp_path_factory.mktemp("installed") / "shop-example")
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    for part in (".claude/hooks", "scripts/agk"):
        shutil.copytree(KIT_ROOT / part, root / part, ignore=shutil.ignore_patterns("__pycache__"))
    return root.resolve()


@pytest.fixture(scope="module")
def clean(tmp_path_factory) -> Path:
    root = git_repo(tmp_path_factory.mktemp("clean") / "shop-example")
    args = [str(root), "--unreleased", "--layout", "plugin", "--rehearsal"]
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "init.py"), *args],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (root / "agk.mk").exists() and not (root / "scripts" / "agk").exists()
    return root.resolve()


def scratch(systmp: Path, role: str) -> str:
    folder = systmp / f"agk-conductor-{role}"
    folder.mkdir(exist_ok=True)
    return str(folder)


def allowed(script: Path, args: tuple[str, ...], root: Path, systmp: Path, plugin: Path,
            command: str, agent: str | None = None) -> bool:  # fmt: skip
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(root),
    }
    if agent:
        payload["agent_type"] = agent
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "CLAUDE_PROJECT_DIR": str(root),
        "CLAUDE_PLUGIN_ROOT": str(plugin),
        "TMPDIR": str(systmp),
        "HOME": str(systmp),
    }
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), *args],
        input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=str(root),
    )  # fmt: skip
    assert proc.returncode in (0, 2), proc.stderr
    if proc.returncode == 2:
        return False
    if not proc.stdout.strip():
        return True
    out = json.loads(proc.stdout).get("hookSpecificOutput", {})
    return out.get("permissionDecision") != "deny"


def filled(form: str, role: str, systmp: Path, plugin: Path | None) -> str:
    """The named form as run: `<scratch>` the run's folder, `<plugin>` the plugin's folder, or,
    without `plugin`, the variable typed into the shell in its place."""
    text = form.replace(SCRATCH, scratch(systmp, role))
    return text.replace(PLUGIN, str(plugin) if plugin else VARIABLE)


def role_forms(role: str) -> tuple[str, str]:
    forms = governance_forms((AGENTS / f"{role}.md").read_text(encoding="utf-8"))
    assert forms, f"{CLASS}: {CLASS}{role}.md has no governance line (setting: tools)"
    return forms


def installed_allows(role, installed, systmp, plugin, command) -> bool:
    guard, *args = GUARDS[role]
    script = installed / ".claude" / "hooks" / guard
    return allowed(script, tuple(args), installed, systmp, plugin, command)


def clean_allows(role, clean, systmp, plugin, command) -> bool:
    script = plugin / ".claude" / "hooks" / "plugin_hooks.py"
    return allowed(script, ("pre",), clean, systmp, plugin, command, agent=f"agk:{role}")


# --- the checks of the check ----------------------------------------------------------------------


def test_req078_a_bash_role_without_the_line_is_caught():
    """REQ-078: the check of the check; a file with no `tools:` line has every tool."""
    one = "Governance: `python3 scripts/agk/kit_root.py governance`"
    two = one + '; `python3 "x/kit_root.py" governance`.'
    texts = {
        "a": "---\nname: a\ntools: Read, Bash\n---\nno line",
        "b": "---\nname: b\n---\nno line",
        "c": "---\nname: c\ntools: Read, Grep\n---\nno line",
        "d": f"---\nname: d\ntools: Bash\n---\n{two}",
        "e": f"---\nname: e\ntools: Bash\n---\n{one}.",
        "f": f"---\nname: f\ntools: Bash\n---\n{two}\n{two}",
    }
    found = missing_lines(texts)
    assert [line.split()[1] for line in found] == [f"{CLASS}{r}.md" for r in ("a", "b", "e", "f")]
    assert all(line.startswith(CLASS) and "`" not in line for line in found)


def test_req078_the_roles_with_bash_are_the_six_the_brief_names():
    """REQ-078: brief #1841 answer 1: the files without Bash get no line."""
    assert bash_roles() == sorted(GUARDS)


def test_req078_every_role_with_bash_names_both_forms():
    """REQ-078: brief #1841 answer 1: one `Governance:` line with the installed and clean form."""
    texts = {p.stem: p.read_text(encoding="utf-8") for p in AGENTS.glob("*.md")}
    assert missing_lines(texts) == []
    for role in bash_roles():
        installed_form, clean_form = role_forms(role)
        assert PLUGIN not in installed_form and PLUGIN in clean_form, f"{CLASS}{role}.md"
        assert "CLAUDE_PLUGIN" not in installed_form + clean_form, f"{CLASS}{role}.md"
        assert (SCRATCH in clean_form) == (role in SCRATCH_ROLES), f"{CLASS}{role}.md"


# --- each named form through its own guard --------------------------------------------------------


@pytest.mark.parametrize("role", sorted(GUARDS))
def test_req078_the_installed_form_is_allowed_by_the_roles_guard(role, installed, systmp, plugin):
    """REQ-078: brief #1841 answer 3: the installed form, through the frontmatter hook's guard."""
    command = filled(role_forms(role)[0], role, systmp, None)
    assert installed_allows(role, installed, systmp, plugin, command), f"{CLASS}{role}.md"


@pytest.mark.parametrize("role", sorted(GUARDS))
def test_req078_the_clean_form_is_allowed_through_the_plugin_hook(role, clean, systmp, plugin):
    """REQ-078: brief #1841 answer 3: the clean form, the plugin's folder written out, through
    `plugin_hooks.py pre` with `agent_type` `agk:<role>`."""
    command = filled(role_forms(role)[1], role, systmp, plugin)
    assert clean_allows(role, clean, systmp, plugin, command), f"{CLASS}{role}.md"


@pytest.mark.parametrize("role", VARIABLE_DENIED)
def test_req078_the_variable_typed_into_the_shell_stays_denied(role, clean, systmp, plugin):
    """REQ-078: brief #1841 answer 3, ADR-0736 decision 4: the variable left in is denied."""
    command = filled(role_forms(role)[1], role, systmp, None)
    assert VARIABLE in command
    assert not clean_allows(role, clean, systmp, plugin, command), f"{CLASS}{role}.md"


@pytest.mark.parametrize("role", VARIABLE_DENIED)
def test_req078_an_agk_base_before_the_reviewing_forms_stays_allowed(role, clean, systmp, plugin):
    """REQ-078: brief #1841 answer 4: one `AGK_BASE=<sha>` before the command, as today."""
    command = filled(role_forms(role)[1], role, systmp, plugin)
    sha = "a1b2c3d4e5" * 4
    if role in SCRATCH_ROLES:
        command = command.replace("python3 -I ", f"AGK_BASE={sha} python3 -I ", 1)
    else:
        command = f"AGK_BASE={sha} {command}"
    assert clean_allows(role, clean, systmp, plugin, command), f"{CLASS}{role}.md"


def test_req078_the_conductors_make_form_cannot_run_in_a_clean_project(clean):
    """REQ-078: brief #1841 answer 2: the clean stub has no `agk.mk`, so conductor.md names the
    resolver's form first and keeps the make forms only for an installed project."""
    assert not (clean / "agk.mk").exists() and not (clean / "Makefile").exists()
    text = (AGENTS / "conductor.md").read_text(encoding="utf-8")
    run = next(line for line in text.splitlines() if line.startswith("- Run only "))
    assert run.index("kit_root.py governance") < run.index("make -C <scratch>")
    assert "installed project" in run and "the kit's own file in every project" not in run
    shadow = (AGENTS / "shadow.md").read_text(encoding="utf-8")
    assert "word for word" in shadow


# --- the settings of answer 4 ---------------------------------------------------------------------


def gate(root: Path, kit: Path, plugin_env: str) -> subprocess.CompletedProcess:
    """`python3 <kit>/kit_root.py governance` in `root`, for a refusal only (never a full gate)."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": plugin_env}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(kit / "kit_root.py"), "governance"],
        capture_output=True, text=True, env=env, cwd=str(root), timeout=60,
    )  # fmt: skip


def with_toml(clean: Path, tmp_path: Path, old: str, new: str) -> Path:
    root = tmp_path / "shop-example"
    shutil.copytree(clean, root)
    path = root / "agk.toml"
    text = path.read_text(encoding="utf-8")
    assert re.search(old, text, re.M), old
    path.write_text(re.sub(old, new, text, count=1, flags=re.M), encoding="utf-8")
    return root


def test_req078_another_layout_is_refused_before_any_gate(clean, tmp_path, plugin):
    """REQ-078: brief #1841 answer 4: `[kit] layout` neither value: refused naming `layout`."""
    root = with_toml(clean, tmp_path, r'^layout = "plugin"$', 'layout = "other"')
    proc = gate(root, plugin / "scripts" / "agk", str(plugin))
    assert proc.returncode == 1 and "(setting: layout)" in proc.stdout + proc.stderr
    assert '"other"' not in proc.stdout + proc.stderr


def test_req078_a_pin_not_the_plugins_stops_the_gate_and_the_guard_still_allows(
    clean, tmp_path, systmp, plugin
):
    """REQ-078: brief #1841 answer 4: `[kit] plugin_version` not the running plugin's: the gate
    refuses naming `plugin_version`; the guards still allow the named form."""
    root = with_toml(clean, tmp_path, r"^plugin_version = .*$", 'plugin_version = "0.0.1"')
    proc = gate(root, plugin / "scripts" / "agk", str(plugin))
    assert proc.returncode == 1 and "(setting: plugin_version)" in proc.stdout + proc.stderr
    for role in VARIABLE_DENIED:
        command = filled(role_forms(role)[1], role, systmp, plugin)
        assert clean_allows(role, root, systmp, plugin, command), f"{CLASS}{role}.md"


def test_req078_a_plugin_root_naming_no_plugin_is_refused(clean, tmp_path):
    """REQ-078: brief #1841 answer 4: `CLAUDE_PLUGIN_ROOT` naming no plugin, and the folder the
    script sits in no plugin either: refused, exit 1, naming the setting (the code names
    `plugin_version`, the pin it cannot check; Decisions taken)."""
    kit = tmp_path / "not-a-plugin" / "scripts" / "agk"
    shutil.copytree(KIT_ROOT / "scripts" / "agk", kit, ignore=shutil.ignore_patterns("__pycache__"))
    proc = gate(clean, kit, str(tmp_path / "none"))
    assert proc.returncode == 1 and "(setting: plugin_version)" in proc.stdout + proc.stderr
    assert str(tmp_path) not in proc.stdout + proc.stderr
