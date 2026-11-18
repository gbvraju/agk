"""Tests of the plugin's hooks and agents (SPEC-0071 rule 4, brief #1454, ADR-0612; REQ-078).

A stub plugin root is a copy of the plugin's `.claude-plugin/`, `.claude/hooks/` and
`scripts/agk/` in tmp_path; the projects are git-free trees of invented data. No network, no
gh, no model.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SECRET_SAMPLES = (
    ".env",
    ".env.local",
    "x.pem",
    "x.key",
    "x.p12",
    "x.pfx",
    "id_rsa",
    "x.tfstate",
    "x.tfstate.1",
    "secrets.json",
    "x.log",
    "x.log.1",
)  # data_guard.SAMPLES
MATCHER = "Read|Grep|Glob|Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit"
PUSH = "git push origin HEAD:main"


@pytest.fixture(scope="module")
def plugin(tmp_path_factory) -> Path:
    stub = tmp_path_factory.mktemp("plugin")
    for part in (".claude-plugin", ".claude/hooks", ".claude/agents", "scripts/agk"):
        shutil.copytree(ROOT / part, stub / part, ignore=shutil.ignore_patterns("__pycache__"))
    return stub


def project(base: Path, layout: str, plugin: Path | None = None) -> Path:
    """`clean`: `[kit] layout = "plugin"` and no kit file; `installed`: the project's own hooks."""
    root = base / layout
    root.mkdir()
    if layout == "clean":
        (root / "agk.toml").write_text('[kit]\nlayout = "plugin"\n', encoding="utf-8")
    elif layout == "installed":
        (root / "agk.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
        for part in (".claude/hooks", ".claude/agents", "scripts/agk"):
            shutil.copytree(
                plugin / part, root / part, ignore=shutil.ignore_patterns("__pycache__")
            )
    return root


def hook(script: Path, root: Path, payload: dict, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), "HOME": str(root)}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=root,
    )


def pre(root: Path, tool: str, agent: str | None = None, **tool_input) -> dict:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": str(root),
    }
    return {**payload, "agent_type": agent} if agent else payload


def reason(proc: subprocess.CompletedProcess) -> str | None:
    if not proc.stdout.strip():
        return None
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


def plugin_pre(plugin: Path, root: Path, payload: dict) -> subprocess.CompletedProcess:
    return hook(plugin / ".claude" / "hooks" / "plugin_hooks.py", root, payload, "pre")


# --- the registration (rule 4) -------------------------------------------------------------------


def test_ac1_the_plugin_registers_its_hooks_and_the_manifest_agents():
    """REQ-078 AC1: plugin.json runs both hooks from the plugin and lists the manifest's agents."""
    data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    (pre_entry,) = data["hooks"]["PreToolUse"]
    (pre_hook,) = pre_entry["hooks"]
    assert pre_entry["matcher"] == MATCHER
    assert (
        pre_hook["command"] == 'python3 "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/plugin_hooks.py" pre'
    )
    assert pre_hook["timeout"] == 10 and pre_hook["onFailure"] == "block"
    ((stop_hook,),) = [e["hooks"] for e in data["hooks"]["Stop"]]
    assert stop_hook["command"].endswith('/.claude/hooks/plugin_hooks.py" stop')
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    agents = sorted("./" + p for p in manifest["verbatim"] if p.startswith(".claude/agents/"))
    assert sorted(data["agents"]) == agents
    assert all((ROOT / a).is_file() for a in agents)
    assert ".claude/hooks/plugin_hooks.py" in manifest["verbatim"]


def test_ac1_every_guarded_agent_has_its_guard_in_the_plugin_hook():
    """REQ-078 AC1: each agent whose file names a guard is guarded the same way as `agk:<name>`."""
    spec = importlib.util.spec_from_file_location(
        "plugin_hooks", ROOT / ".claude/hooks/plugin_hooks.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        text = path.read_text(encoding="utf-8").split("\n---", 1)[0]
        named = [w for w in text.split('"') if w.startswith("/.claude/hooks/")]
        expected = tuple(named[0].removeprefix("/.claude/hooks/").split()) if named else None
        assert module.ROLE_GUARDS.get(path.stem) == expected, path.name


# --- security first: the data guard in both layouts (answer 3) ----------------------------------


@pytest.mark.parametrize("name", SECRET_SAMPLES)
def test_ac1_the_data_guard_refuses_each_secret_shape_alike_in_both_layouts(tmp_path, plugin, name):
    """REQ-078 AC1: a planted secret file is refused from the plugin exactly as when installed."""
    clean, installed = project(tmp_path, "clean"), project(tmp_path, "installed", plugin)
    seen = []
    for root in (clean, installed):
        (root / name).write_text("invented\n", encoding="utf-8")
        for payload in (
            pre(root, "Read", file_path=str(root / name)),
            pre(root, "Bash", command=f"cat {name}"),
        ):
            if root is clean:
                seen.append(reason(plugin_pre(plugin, root, payload)))
            else:
                seen.append(reason(hook(root / ".claude/hooks/data_guard.py", root, payload)))
    assert seen[:2] == seen[2:] and all(seen), seen
    assert all(line.startswith("data guard: ") and name not in line for line in seen)


def test_ac1_a_key_shaped_value_in_an_example_file_is_refused_in_a_clean_project(tmp_path, plugin):
    """REQ-078 AC1: the guard's content scan runs from the plugin too."""
    root = project(tmp_path, "clean")
    key = "api_key = " + hashlib.sha256(b"brief-1454-1").hexdigest()[:40] + "\n"
    (root / ".env.example").write_text(key, encoding="utf-8")
    line = reason(plugin_pre(plugin, root, pre(root, "Read", file_path=str(root / ".env.example"))))
    assert line and line.startswith("data guard: secret-file")
    (root / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
    assert (
        reason(plugin_pre(plugin, root, pre(root, "Read", file_path=str(root / ".env.example"))))
        is None
    )


@pytest.mark.parametrize("layout", ["installed", "none", "kit"])
def test_ac7_the_plugin_adds_no_second_data_guard_where_the_project_runs_its_own(
    tmp_path, plugin, layout
):
    """REQ-078 AC7: an installed project, a non-agk project and the kit's tree keep their own."""
    root = ROOT if layout == "kit" else project(tmp_path, layout, plugin)
    payload = pre(root, "Bash", command="cat .env")
    proc = plugin_pre(plugin, root, payload)
    assert proc.returncode == 0 and proc.stdout == ""


# --- the agents' guards (fact 2: a plugin agent's frontmatter hooks do not fire) -----------------


@pytest.mark.parametrize("layout", ["clean", "installed"])
def test_ac1_a_plugin_conductor_gets_its_guard_in_both_layouts(tmp_path, plugin, layout):
    """REQ-078 AC1: `agk:conductor` is refused a push; the steward and architect likewise."""
    root = project(tmp_path, layout, plugin)
    for agent in (
        "agk:conductor",
        "agk:shadow",
        "agk:steward",
        "agk:architect",
        "agk:architect-review",
    ):
        line = reason(plugin_pre(plugin, root, pre(root, "Bash", agent, command=PUSH)))
        assert line, agent
    assert reason(plugin_pre(plugin, root, pre(root, "Bash", None, command="git status"))) is None


def test_ac7_a_project_agent_and_an_unguarded_tool_get_no_plugin_guard(tmp_path, plugin):
    """REQ-078 AC7: the project's own `conductor` keeps its own hook; Read is not matched."""
    root = project(tmp_path, "installed", plugin)
    assert reason(plugin_pre(plugin, root, pre(root, "Bash", "conductor", command=PUSH))) is None
    assert (
        reason(plugin_pre(plugin, root, pre(root, "Read", "agk:conductor", file_path="README.md")))
        is None
    )
    assert (
        reason(plugin_pre(plugin, root, pre(root, "Bash", "agk:drift-auditor", command=PUSH)))
        is None
    )


@pytest.mark.parametrize("stdin, event", [("not json", "pre"), ("[]", "pre"), ("{}", "other")])
def test_ac1_input_it_cannot_read_denies(tmp_path, plugin, stdin, event):
    """REQ-078 AC1: the plugin hook fails closed, naming no value."""
    root = project(tmp_path, "clean")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(plugin / ".claude/hooks/plugin_hooks.py"), event],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=root,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)},
    )
    if event == "pre":
        assert reason(proc).startswith("plugin hooks: cannot-judge")
    assert proc.returncode == 0 and stdin not in proc.stdout


# --- the stop check from the plugin ---------------------------------------------------------------


def load_stop(plugin: Path):
    sys.path.insert(0, str(plugin / "scripts" / "agk"))
    spec = importlib.util.spec_from_file_location(
        "stop_check_b", plugin / ".claude/hooks/stop_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ac1_the_stop_check_runs_the_gate_and_scripts_from_the_plugin(
    tmp_path, plugin, monkeypatch
):
    """REQ-078 AC1: in a clean project the gate is the plugin's resolver; installed keeps make."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.delitem(sys.modules, "kit_root", raising=False)  # the stub plugin's own copy
    monkeypatch.setattr(sys, "path", list(sys.path))
    stop = load_stop(plugin)
    clean, installed = project(tmp_path, "clean"), project(tmp_path, "installed", plugin)
    gate, moved = stop.kit_forms(str(clean), [("scripts/agk/check_example.py", "--x")])
    kit = (plugin / "scripts" / "agk").resolve()
    assert gate[1:] == [str(kit / "kit_root.py"), "governance"]
    assert moved == [(str(kit / "check_example.py"), "--x")]
    assert stop.kit_forms(str(installed), None) == (stop.MAKE_GATE, None)
    assert stop.kit_forms(str(installed), [("scripts/agk/a.py",)])[1] == [("scripts/agk/a.py",)]


# --- the fix list on 1e0a895 --------------------------------------------------------------------


@pytest.mark.parametrize("agent", ["conductor", "agk:conductor", "other:conductor"])
def test_ac1_every_spelling_of_a_guarded_role_gets_its_guard_in_a_clean_project(
    tmp_path, plugin, agent
):
    """REQ-078 AC1: bare `--agent conductor` (recorded as `agk:conductor`), any spelling, denies."""
    root = project(tmp_path, "clean")
    assert reason(plugin_pre(plugin, root, pre(root, "Bash", agent, command=PUSH)))


def test_ac1_a_session_in_a_subfolder_of_a_clean_project_gets_the_data_guard(tmp_path, plugin):
    """REQ-078 AC1: the project is the git top level, not the session's folder."""
    root = project(tmp_path, "clean")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    (root / ".env").write_text("invented\n", encoding="utf-8")
    (root / "src").mkdir()
    sub = root / "src"
    payload = pre(sub, "Read", file_path=str(root / ".env"))
    line = reason(hook(plugin / ".claude/hooks/plugin_hooks.py", sub, payload, "pre"))
    assert line and line.startswith("data guard: secret-file")


def fake_plugin(tmp_path: Path, guard: str, body: str | None) -> Path:
    hooks = tmp_path / "fake" / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(ROOT / ".claude/hooks/plugin_hooks.py", hooks / "plugin_hooks.py")
    if body is not None:
        (hooks / guard).write_text(body, encoding="utf-8")
    return hooks / "plugin_hooks.py"


CRASH = "import sys\nsys.exit('a failure at /home/member-example-1/private/path')\n"


@pytest.mark.parametrize("body", [None, CRASH, "import time\ntime.sleep(8)\n"])
def test_ac1_a_missing_crashing_or_slow_guard_denies_with_the_fixed_line(tmp_path, body):
    """REQ-078 AC1: no guard message (or path) is passed on, and the hook stays in its budget."""
    script = fake_plugin(tmp_path, "data_guard.py", body)
    root = project(tmp_path, "clean")
    proc = hook(script, root, pre(root, "Bash", command="ls"), "pre")
    assert reason(proc).startswith("plugin hooks: cannot-judge")
    assert "member-example-1" not in proc.stdout + proc.stderr


STOP = 'import json\nprint(json.dumps({"decision": "block", "reason": "stub stop ran"}))\n'


def test_ac1_the_stop_dispatch_runs_the_stop_check_in_a_clean_project_only(tmp_path, plugin):
    """REQ-078 AC1: the Stop hook reaches the plugin's stop check; installed keeps its own."""
    script = fake_plugin(tmp_path, "stop_check.py", STOP)
    clean, installed = project(tmp_path, "clean"), project(tmp_path, "installed", plugin)
    payload = {"hook_event_name": "Stop", "stop_hook_active": False}
    out = hook(script, clean, {**payload, "cwd": str(clean)}, "stop").stdout
    assert json.loads(out) == {"decision": "block", "reason": "stub stop ran"}
    assert hook(script, installed, {**payload, "cwd": str(installed)}, "stop").stdout == ""


def test_ac1_a_crashing_stop_check_blocks_once(tmp_path):
    """REQ-078 AC1: a stop check that cannot run blocks the stop once, then allows it."""
    script = fake_plugin(tmp_path, "stop_check.py", CRASH)
    root = project(tmp_path, "clean")
    first = hook(script, root, {"stop_hook_active": False, "cwd": str(root)}, "stop").stdout
    assert json.loads(first)["reason"].startswith("plugin hooks: cannot-judge")
    assert hook(script, root, {"stop_hook_active": True, "cwd": str(root)}, "stop").stdout == ""


def test_ac1_the_guards_see_the_top_level_as_the_project(tmp_path):
    """REQ-078 AC1: a stop in a subfolder runs the stop check against the project's top level."""
    body = "import json, os\nprint(json.dumps({'reason': os.environ['CLAUDE_PROJECT_DIR']}))\n"
    script = fake_plugin(tmp_path, "stop_check.py", body)
    root = project(tmp_path, "clean")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    (root / "src").mkdir()
    out = hook(script, root / "src", {"stop_hook_active": False}, "stop").stdout
    assert Path(json.loads(out)["reason"]).resolve() == root.resolve()
