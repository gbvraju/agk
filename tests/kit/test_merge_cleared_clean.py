"""The guarded merge runs governance from the plugin in a clean-layout project (brief #1665,
ADR-0696; REQ-078).

`merge_cleared.governance_argv` builds its command from `kit_root.gate` of the merged tree: an
installed tree runs `make -C <tree> -f agk.mk agk-governance AGK_BASE=<base>` as today, and a clean
tree (`[kit] layout = "plugin"`) runs the plugin's `kit_root.py governance` in that tree, never
`make`, with `AGK_BASE` in its clean environment. `gate_refusal` holds a clean tree with kit_root's
own line before anything runs: a bad `layout`, no plugin (`CLAUDE_PLUGIN_ROOT`) or a pin that does
not match (`plugin_version`). Temporary folders, a fake plugin and invented data only
(example.com); no network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed git and lock.py argument lists, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import kit_root  # noqa: E402
import merge_cleared  # noqa: E402

BASE = "a" * 40
PIN = "9.9.9"
CLEAN = (
    f'version = "{PIN}"\nexecution = "{{execution}}"\n'
    f'[kit]\nlayout = "plugin"\nplugin_version = "{PIN}"\n'
)
FAKE_GATE = (
    "import json, os, sys, tomllib\n"
    "open({seen!r}, 'w').write("
    "json.dumps({{'cwd': os.getcwd(), 'args': sys.argv[1:], "
    "'base': os.environ.get('AGK_BASE')}}))\n"
    "sys.exit({code})\n"
)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)  # nosec B603 B607 - fixed git argv


def plugin(path: Path, version: str = PIN, gate: str = "") -> Path:
    """A fake plugin: its manifest at VERSION and a kit_root.py (GATE, else a stub)."""
    (path / ".claude-plugin").mkdir(parents=True)
    (path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "agk", "version": version}), encoding="utf-8"
    )
    (path / "scripts" / "agk").mkdir(parents=True)
    (path / "scripts" / "agk" / "kit_root.py").write_text(gate or "raise SystemExit(0)\n", "utf-8")
    return path


def clean_tree(path: Path, execution: str = "local") -> Path:
    path.mkdir(parents=True)
    (path / "agk.toml").write_text(CLEAN.format(execution=execution), encoding="utf-8")
    return path


def command(argv: list[str]) -> list[str]:
    return argv[argv.index("--") + 1 :]


def only_env(argv: list[str]) -> dict[str, str]:
    cut = argv.index("--")
    pairs = [argv[at + 1] for at, arg in enumerate(argv[:cut]) if arg == "--only-env"]
    return dict(pair.split("=", 1) for pair in pairs)


@pytest.mark.parametrize("execution", ["local", "hosted"])
def test_req078_a_clean_tree_runs_the_plugins_governance_never_make(
    tmp_path, monkeypatch, execution
):
    """Answer 1 and 3: the plugin's resolver in the merged tree; `execution` reads the same."""
    found = plugin(tmp_path / "plugin")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(found))
    tree, home = clean_tree(tmp_path / "tree", execution), tmp_path / "home"
    argv = merge_cleared.governance_argv(tree, home, home / "pr-body.md", BASE, 60.0)
    run = command(argv)
    assert "make" not in run and "agk.mk" not in run
    assert run[:3] == [sys.executable, "-I", "-c"]
    assert run[4:] == [str(tree), str(found / "scripts" / "agk" / "kit_root.py"), "governance"]
    env = only_env(argv)
    assert env["AGK_BASE"] == BASE
    assert env["AGK_PR_BODY"] == str(home / "pr-body.md")
    assert env["AGK_RECORD_COMMENTS"] == str(home / "record-comments.json")
    assert "CLAUDE_PLUGIN_ROOT" not in env, "the clean environment is kept"
    assert merge_cleared.gate_refusal(tree) is None


@pytest.mark.parametrize(
    "toml", [None, 'layout = "installed"\n', "[kit\nbroken", '[kit]\nlayout = "installed"\n']
)
def test_req078_an_installed_or_unreadable_tree_runs_make_as_today(tmp_path, toml):
    """Answers 3 and 4: `installed` (or no table, or an unreadable agk.toml) keeps today's form."""
    tree, home = tmp_path / "tree", tmp_path / "home"
    tree.mkdir()
    (tree / "agk.mk").write_text("agk-governance:\n\t@true\n", encoding="utf-8")
    if toml is not None:
        (tree / "agk.toml").write_text(toml, encoding="utf-8")
    argv = merge_cleared.governance_argv(tree, home, home / "pr-body.md", BASE, 60.0)
    assert command(argv) == [
        "make", "-C", str(tree), "-f", "agk.mk", "agk-governance", f"AGK_BASE={BASE}",
    ]  # fmt: skip
    assert "AGK_BASE" not in only_env(argv)
    assert merge_cleared.gate_refusal(tree) is None


def test_req078_a_bad_layout_holds_naming_the_setting(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "agk.toml").write_text('[kit]\nlayout = "vendored-example"\n', encoding="utf-8")
    line = merge_cleared.gate_refusal(tree)
    assert line is not None and "(setting: layout)" in line and "vendored-example" not in line


def test_req078_a_pin_that_does_not_match_holds_with_kit_roots_line(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin(tmp_path / "plugin", version="1.0.0")))
    tree = clean_tree(tmp_path / "tree")
    line = merge_cleared.gate_refusal(tree)
    assert line == "agk: the running AGK plugin is not the pinned version (setting: plugin_version)"
    assert PIN not in line and "1.0.0" not in line


def test_req078_no_plugin_holds_naming_claude_plugin_root(tmp_path, monkeypatch):
    """Answer 3: `CLAUDE_PLUGIN_ROOT` set to a folder that is no plugin, and none beside the kit."""
    not_one = tmp_path / "not-a-plugin"
    not_one.mkdir()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(not_one))
    monkeypatch.setattr(kit_root, "HERE", tmp_path / "elsewhere" / "scripts" / "agk")
    line = merge_cleared.gate_refusal(clean_tree(tmp_path / "tree"))
    assert line == "kit_root: no plugin root for this clean project (setting: CLAUDE_PLUGIN_ROOT)"


def test_req078_unset_plugin_root_finds_the_plugin_beside_the_kit(tmp_path, monkeypatch):
    """Answer 3: `CLAUDE_PLUGIN_ROOT` unset, the plugin this kit sits in is the one run."""
    found = plugin(tmp_path / "plugin")
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(kit_root, "HERE", found / "scripts" / "agk")
    tree, home = clean_tree(tmp_path / "tree"), tmp_path / "home"
    assert merge_cleared.gate_refusal(tree) is None
    run = command(merge_cleared.governance_argv(tree, home, home / "pr-body.md", BASE, 60.0))
    assert run[-2:] == [str(found / "scripts" / "agk" / "kit_root.py"), "governance"]


def test_req078_a_refused_clean_tree_runs_nothing(tmp_path, monkeypatch):
    """Answer 1: the hold comes before any process starts, with the refusal as its step."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin(tmp_path / "plugin", version="1.0.0")))

    def no_run(*_args, **_kwargs):
        raise AssertionError("nothing runs")

    monkeypatch.setattr(merge_cleared.subprocess, "Popen", no_run)
    tree, home = clean_tree(tmp_path / "tree"), tmp_path / "home"
    step = merge_cleared.run_governance(tmp_path, tree, home, home / "pr-body.md", BASE, 60.0)
    assert step is not None and step.endswith("(setting: plugin_version)")


@pytest.mark.parametrize(("code", "step"), [(0, None), (1, merge_cleared.GOVERNANCE_STEP)])
def test_req078_the_real_lock_runs_the_plugin_gate_in_the_merged_tree(
    tmp_path, monkeypatch, code, step
):
    """Answer 5: through the real lock.py, the plugin's gate runs with the merged tree as its
    working folder and AGK_BASE set; its exit decides the step."""
    seen = tmp_path / "seen.json"
    found = plugin(tmp_path / "plugin", gate=FAKE_GATE.format(seen=str(seen), code=code))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(found))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "temp"))  # lock.py's folder
    (tmp_path / "temp").mkdir()
    monkeypatch.setattr(merge_cleared, "on_windows", lambda: False)
    checkout, tree, home = tmp_path / "checkout", clean_tree(tmp_path / "tree"), tmp_path / "home"
    checkout.mkdir()
    home.mkdir()
    git(checkout, "init", "-q")
    assert (
        merge_cleared.run_governance(checkout, tree, home, home / "pr-body.md", BASE, 60.0) == step
    )
    got = json.loads(seen.read_text(encoding="utf-8"))
    assert Path(got["cwd"]).resolve() == tree.resolve()
    assert got["args"] == ["governance"] and got["base"] == BASE


def test_req078_a_planted_module_in_the_merged_tree_cannot_make_the_step_pass(
    tmp_path, monkeypatch
):
    """Fix list item 1 on bd4a8f3f: a top-level `tomllib.py` in the pull request's tree that
    exits 0 is never imported by the plugin's gate, which fails, so the step holds."""
    seen = tmp_path / "seen.json"
    found = plugin(tmp_path / "plugin", gate=FAKE_GATE.format(seen=str(seen), code=1))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(found))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "temp"))
    (tmp_path / "temp").mkdir()
    monkeypatch.setattr(merge_cleared, "on_windows", lambda: False)
    checkout, tree, home = tmp_path / "checkout", clean_tree(tmp_path / "tree"), tmp_path / "home"
    checkout.mkdir()
    home.mkdir()
    git(checkout, "init", "-q")
    (tree / "tomllib.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    (tree / "json.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    step = merge_cleared.run_governance(checkout, tree, home, home / "pr-body.md", BASE, 60.0)
    assert step == merge_cleared.GOVERNANCE_STEP
    assert json.loads(seen.read_text(encoding="utf-8"))["args"] == ["governance"]


SETTINGS = [
    "[flow]\nauto_merge = true\n",
    "[flow]\nauto_merge = false\n",
    'review_mode = "solo"\n',
    'review_mode = "team"\n',
    'pr_mode = "strict"\n',
    'pr_mode = "flow"\n',
    'required_checks = ["governance", "proof"]\n',
    "required_checks = []\n",
]


@pytest.mark.parametrize("setting", SETTINGS)
def test_req078_the_other_settings_leave_the_clean_gate_unchanged(tmp_path, monkeypatch, setting):
    """Fix list item 2 on bd4a8f3f (brief answer 3): `[flow] auto_merge`, `review_mode`,
    `pr_mode` and `required_checks` on a clean tree give the same command and no refusal."""
    found = plugin(tmp_path / "plugin")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(found))
    plain, home = clean_tree(tmp_path / "plain"), tmp_path / "home"
    tree = clean_tree(tmp_path / "tree")
    text = (tree / "agk.toml").read_text(encoding="utf-8")
    top, kit = text.split("[kit]\n", 1)
    if setting.startswith("["):
        (tree / "agk.toml").write_text(f"{top}[kit]\n{kit}{setting}", encoding="utf-8")
    else:
        (tree / "agk.toml").write_text(f"{top}{setting}[kit]\n{kit}", encoding="utf-8")
    assert merge_cleared.gate_refusal(tree) is None
    want = command(merge_cleared.governance_argv(plain, home, home / "b.md", BASE, 60.0))
    got = command(merge_cleared.governance_argv(tree, home, home / "b.md", BASE, 60.0))
    assert got == [*want[:3], want[3], str(tree), *want[5:]]
