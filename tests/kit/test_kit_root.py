"""One resolver runs the kit from the plugin or the repository (brief #1453, SPEC-0071 build (a),
ADR-0611; REQ-078).

`scripts/agk/kit_root.py` prints the folder of the kit's scripts: the plugin's in a clean project
(`[kit] layout = "plugin"` in `agk.toml`), the project's own `scripts/agk/` otherwise, and the
command prefix the prompts name. prepush and evidence find the governance gate through it, so a
clean project needs no `agk.mk`. A stub plugin root with its own `.claude-plugin/plugin.json`, saved
git trees in temporary folders and no network; invented data only (example.com, `cb-example-1`)."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "scripts" / "agk"
sys.path.insert(0, str(KIT))

import evidence  # noqa: E402
import kit_root  # noqa: E402
import prepush  # noqa: E402

RUNTIME = ROOT / "kit" / "templates" / "runtime"
PLUGIN_FORM = '"${CLAUDE_PLUGIN_ROOT}/scripts/agk"'


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)  # nosec B603 B607 - local git


def project(tmp: Path, toml: str) -> Path:
    root = tmp / "product-example"
    root.mkdir()
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / "README.md").write_text("A sample product of example.com.\n", encoding="utf-8")
    git(root, "init", "-q")
    return root


def plugin(tmp: Path, version: str = "0.0.1") -> Path:
    """A stub plugin root: its manifest, this kit's resolver and a gate of two stub checks."""
    root = tmp / "plugin-example"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        f'{{"name": "agk", "version": "{version}"}}\n', encoding="utf-8"
    )
    scripts = root / "scripts" / "agk"
    scripts.mkdir(parents=True)
    shutil.copy(KIT / "kit_root.py", scripts / "kit_root.py")
    (scripts / "governance_map.py").write_text(
        "CHECKS = (\n"
        "    ('one', ('scripts/agk/check_one.py',)),\n"
        "    ('two', ('scripts/agk/check_two.py', '--check')),\n"
        ")\n",
        encoding="utf-8",
    )
    for name, code in (("check_one.py", 0), ("check_two.py", 0)):
        (scripts / name).write_text(
            "import pathlib, sys\n"
            f"line = {name!r} + ' ' + ' '.join(sys.argv[1:]) + '\\n'\n"
            "pathlib.Path('ran.txt').open('a').write(line)\n"
            f"sys.exit({code})\n",
            encoding="utf-8",
        )
    return root


# A clean project pins its plugin (brief #1455, ADR-0613): the stub plugin's version.
CLEAN = 'version = "0.0.1"\n\n[kit]\nlayout = "plugin"\nplugin_version = "0.0.1"\n'
INSTALLED = 'version = "0.0.1"\n'


def resolve(root: Path, plug: Path | None, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    if plug is not None:
        env["CLAUDE_PLUGIN_ROOT"] = str(plug)
    script = (plug / "scripts" / "agk" / "kit_root.py") if plug else (KIT / "kit_root.py")
    return subprocess.run(  # nosec B603 - the kit's resolver, no shell
        [sys.executable, str(script), *args], cwd=root, env=env, capture_output=True, text=True
    )


def test_ac1_a_clean_project_resolves_every_script_to_the_plugin(tmp_path):
    """REQ-078 AC1: in a clean project the kit folder and the command form are the plugin's."""
    root, plug = project(tmp_path, CLEAN), plugin(tmp_path)
    (root / "sub").mkdir()
    out = resolve(root / "sub", plug)
    assert out.returncode == 0, out.stderr
    assert Path(out.stdout.strip()) == (plug / "scripts" / "agk").resolve()
    form = resolve(root, plug, "--form")
    assert form.returncode == 0 and form.stdout.strip() == PLUGIN_FORM


def test_ac1_without_the_variable_the_resolver_reads_its_own_plugin(tmp_path):
    """REQ-078 AC1: run by its path in the plugin, the resolver finds that plugin."""
    root, plug = project(tmp_path, CLEAN), plugin(tmp_path)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    out = subprocess.run(  # nosec B603 - the kit's resolver, no shell
        [sys.executable, str(plug / "scripts" / "agk" / "kit_root.py")],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert Path(out.stdout.strip()) == (plug / "scripts" / "agk").resolve()


def test_ac1_an_installed_project_resolves_to_its_own_scripts(tmp_path):
    """REQ-078 AC7: an installed project, plugin or not, runs its own `scripts/agk/` as today."""
    root, plug = project(tmp_path, INSTALLED), plugin(tmp_path)
    for p in (plug, None):
        out = resolve(root, p)
        assert out.returncode == 0, out.stderr
        assert Path(out.stdout.strip()) == (root / "scripts" / "agk").resolve()
    assert resolve(root, plug, "--form").stdout.strip() == "scripts/agk"


def test_ac1_the_kit_repository_keeps_its_layout():
    """REQ-078 AC7: the kit's own repository is an installed project."""
    assert kit_root.layout(ROOT) == "installed"
    assert kit_root.form(ROOT) == "scripts/agk"
    assert kit_root.kit_dir(ROOT) == KIT


def test_ac1_no_plugin_root_is_refused_naming_the_setting(tmp_path):
    """REQ-078 AC1: a clean project with no plugin root is refused, exit 1, naming the setting."""
    root = project(tmp_path, CLEAN)
    stray = tmp_path / "nowhere-example"
    (stray / "scripts" / "agk").mkdir(parents=True)  # a copy outside any plugin
    shutil.copy(KIT / "kit_root.py", stray / "scripts" / "agk" / "kit_root.py")
    out = subprocess.run(  # nosec B603 - the kit's resolver, no shell
        [sys.executable, str(stray / "scripts" / "agk" / "kit_root.py")],
        cwd=root,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(stray)},
        capture_output=True,
        text=True,
    )
    assert out.returncode == 1 and out.stdout == ""
    assert "(setting: CLAUDE_PLUGIN_ROOT)" in out.stderr
    assert str(stray) not in out.stderr


def test_ac1_an_unknown_layout_is_refused_naming_the_setting(tmp_path):
    """REQ-078 AC1: a layout other than `plugin` or `installed` is refused, never quoted."""
    root = project(tmp_path, '[kit]\nlayout = "sideways-example"\n')
    out = resolve(root, plugin(tmp_path))
    assert out.returncode == 1
    assert "(setting: layout)" in out.stderr and "sideways-example" not in out.stderr


def test_ac1_the_gate_runs_from_the_plugin_against_the_project(tmp_path):
    """REQ-078 AC1: with no `agk.mk`, `governance` runs the plugin's checks in the project."""
    root, plug = project(tmp_path, CLEAN), plugin(tmp_path)
    out = resolve(root, plug, "governance")
    assert out.returncode == 0, out.stderr
    assert (root / "ran.txt").read_text() == "check_one.py \ncheck_two.py --check\n"
    assert not (plug / "ran.txt").exists()  # never writes into the plugin's folder


def test_ac1_the_gate_stops_at_the_first_failing_check(tmp_path):
    """REQ-078 AC1: a failing check ends the gate with its exit code, as make does."""
    root, plug = project(tmp_path, CLEAN), plugin(tmp_path)
    one = plug / "scripts" / "agk" / "check_one.py"
    one.write_text(one.read_text().replace("sys.exit(0)", "sys.exit(3)"))
    out = resolve(root, plug, "governance")
    assert out.returncode == 3
    assert (root / "ran.txt").read_text() == "check_one.py \n"


def test_ac1_prepush_finds_the_gate_without_agk_mk(tmp_path, monkeypatch):
    """REQ-078 AC1: the clean-install test's stop (`agk.mk is missing`) is gone when clean."""
    root, plug = project(tmp_path, CLEAN), plugin(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plug))
    step = prepush.governance(root, "origin/main")
    assert step.outcome == "ok", step.text
    assert step.ran.argv[-1] == "governance"
    assert Path(step.ran.argv[-2]) == plug.resolve() / "scripts" / "agk" / "kit_root.py"


def test_ac7_an_installed_project_without_agk_mk_fails_as_today(tmp_path):
    """REQ-078 AC7: an installed sample behaves as today: the same refusal, byte for byte."""
    root = project(tmp_path, INSTALLED)
    step = prepush.governance(root, "origin/main")
    assert step.outcome == "FAIL"
    assert step.text == "agk.mk is missing; governance cannot run (path class: agk.mk)"


def test_ac7_an_installed_project_runs_make_as_today(tmp_path):
    """REQ-078 AC7: the installed gate is the same `make -f agk.mk agk-governance`."""
    root = project(tmp_path, INSTALLED)
    (root / "agk.mk").write_text("agk-governance:\n\t@true\n", encoding="utf-8")
    assert kit_root.gate(root) == ["make", "-f", "agk.mk", "agk-governance"]
    assert kit_root.gate(root) == evidence.GOVERNANCE


def test_ac1_evidence_accepts_only_the_gate_of_the_tree(tmp_path, monkeypatch):
    """REQ-078 AC1: a record's governance argv must be the gate this tree gives (verdict item 2)."""
    make = ["make", "-f", "agk.mk", "agk-governance"]
    plugin_form = ["python3", "<outside>/kit_root.py", "governance"]
    installed = project(tmp_path, INSTALLED)
    assert evidence.known_gate(make, installed)
    assert not evidence.known_gate(plugin_form, installed)
    (tmp_path / "c").mkdir()
    clean, plug = project(tmp_path / "c", CLEAN), plugin(tmp_path / "c")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plug))
    assert evidence.known_gate(plugin_form, clean)
    assert evidence.known_gate(["python3", "scripts/agk/kit_root.py", "governance"], clean)
    assert not evidence.known_gate(make, clean)
    assert not evidence.known_gate(["python3", "<outside>/other.py", "governance"], clean)
    assert not evidence.known_gate([*plugin_form, "--x"], clean)


def test_ac1_without_the_variable_the_form_is_the_found_folder(tmp_path):
    """REQ-078 AC1: with `CLAUDE_PLUGIN_ROOT` unset (Q-1453-1) `--form` prints the plugin's own
    folder, quoted, never a form that expands to `/scripts/agk` (verdict item 1)."""
    root, plug = project(tmp_path, CLEAN), plugin(tmp_path)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    out = subprocess.run(  # nosec B603 - the kit's resolver, no shell
        [sys.executable, str(plug / "scripts" / "agk" / "kit_root.py"), "--form"],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f'"{plug.resolve() / "scripts" / "agk"}"'
    assert "CLAUDE_PLUGIN_ROOT" not in out.stdout


@pytest.mark.parametrize("toml", ["not [valid toml", 'kit = "flat-example"\n'])
def test_ac7_an_unreadable_agk_toml_keeps_the_installed_gate(tmp_path, toml):
    """REQ-078 AC7: an installed project whose `agk.toml` cannot be read, or whose `kit` is not a
    table, runs `make` as before and is never refused (verdict item 3)."""
    root = project(tmp_path, toml)
    (root / "agk.mk").write_text("agk-governance:\n\t@true\n", encoding="utf-8")
    assert kit_root.layout(root) == "installed"
    assert kit_root.gate(root) == ["make", "-f", "agk.mk", "agk-governance"]
    assert prepush.governance(root, "origin/main").ran.argv == kit_root.MAKE_GATE


def test_ac1_the_prompts_name_each_script_through_the_one_form():
    """REQ-078 AC1: the session prompts say `<kit>` once and never repeat the path text."""
    for name in ("builder.txt", "conductor.txt", "launcher.txt"):
        body = (RUNTIME / name).read_text(encoding="utf-8")
        assert "python3 scripts/agk/" not in body, name
        assert "python3 <kit>/" in body, name
        assert body.count("KIT: `<kit>` is ") == 1, name
        assert PLUGIN_FORM in body and "kit_root.py --form" in body, name


@pytest.mark.parametrize("name", ["builder.txt", "conductor.txt", "launcher.txt"])
def test_ac1_the_prompts_carry_no_installed_path_text_twice(name):
    """REQ-078 AC1: answer 5: the repeated `scripts/agk/` text is gone from the command forms."""
    body = (RUNTIME / name).read_text(encoding="utf-8")
    assert body.count("scripts/agk/") <= 2, name
