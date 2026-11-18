"""One plugin version on every machine (brief #1455, SPEC-0071 rule 6 and rule 10, build (c),
ADR-0613; REQ-078 AC2).

In a clean project (`[kit] layout = "plugin"` in `agk.toml`) `[kit] plugin_version` pins the plugin.
Every kit script reads it at start (`common` on import, and the resolver `kit_root.py`) and compares
it with the running plugin's `version` in `.claude-plugin/plugin.json`: no plugin, an older or a
newer one, no pin, or a pin other than `version` (Q-S0071-7) is refused with one line naming
`plugin_version`, never a value, exit 1, before any work. A stub plugin root with its own
`.claude-plugin/plugin.json` (a copy of this kit's scripts), saved git trees in temporary folders, a
`gh` stub that fails and no network; invented data only (example.com, `cb-example-1`)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "scripts" / "agk"
sys.path.insert(0, str(KIT))

import kit_root  # noqa: E402

import config  # noqa: E402

PIN = "0.9.1"
PROBE = "import common\nprint('probe-example worked')\n"


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)  # nosec B603 B607 - local git


def project(tmp: Path, toml: str) -> Path:
    root = tmp / "product-example"
    root.mkdir()
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / "README.md").write_text("A sample product of example.com.\n", encoding="utf-8")
    git(root, "init", "-q")
    return root


def clean(version: str = PIN, pin: str | None = PIN) -> str:
    line = "" if pin is None else f'plugin_version = "{pin}"\n'
    return f'version = "{version}"\n\n[kit]\nlayout = "plugin"\n{line}'


def plugin(tmp: Path, version: str = PIN, name: str = "plugin-example") -> Path:
    """A stub plugin root: its manifest and a copy of this kit's scripts, with one probe script."""
    root = tmp / name
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        f'{{"name": "agk", "version": "{version}"}}\n', encoding="utf-8"
    )
    shutil.copytree(KIT, root / "scripts" / "agk", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "scripts" / "agk" / "probe_example.py").write_text(PROBE, encoding="utf-8")
    return root


def offline(tmp: Path) -> dict[str, str]:
    """The network stub off: a `gh` that fails, no proxy that answers, no CLAUDE_PLUGIN_ROOT."""
    stub = tmp / "bin-example"
    stub.mkdir(exist_ok=True)
    (stub / "gh").write_text("#!/bin/sh\necho gh-called >&2\nexit 99\n", encoding="utf-8")
    (stub / "gh").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    env["PATH"] = f"{stub}{os.pathsep}{env.get('PATH', '')}"
    env["HTTPS_PROXY"] = env["https_proxy"] = "http://127.0.0.1:9"
    return env


def run(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - the kit's own scripts, no shell
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=offline(cwd.parent),
        capture_output=True,
        text=True,
    )


def refused(out: subprocess.CompletedProcess, *values: str) -> None:
    assert out.returncode == 1, out
    assert "worked" not in out.stdout  # no work before the refusal
    lines = out.stderr.strip().splitlines()
    assert len(lines) == 1, out.stderr
    assert "(setting: plugin_version)" in lines[0]
    for value in values:
        assert value not in lines[0]


def probe(plug: Path) -> Path:
    return plug / "scripts" / "agk" / "probe_example.py"


def test_ac2_the_pinned_version_runs_offline(tmp_path):
    """REQ-078 AC2: the pinned plugin runs a kit script with the network stub off."""
    root, plug = project(tmp_path, clean()), plugin(tmp_path)
    out = run(probe(plug), root)
    assert out.returncode == 0, out.stderr
    assert out.stdout == "probe-example worked\n" and "gh-called" not in out.stderr


@pytest.mark.parametrize("running", ["0.9.0", "0.10.0"], ids=["older", "newer"])
def test_ac2_another_plugin_version_is_refused_naming_the_setting(tmp_path, running):
    """REQ-078 AC2: an older or a newer plugin is refused, one line, no value; in team mode the
    teammate whose plugin is older than the pin is the one refused (rule 10)."""
    root, plug = project(tmp_path, clean()), plugin(tmp_path, running)
    refused(run(probe(plug), root), PIN, running)


def test_ac2_no_plugin_is_refused_and_names_the_install_command(tmp_path):
    """REQ-078 AC2: a kit script that no plugin runs (a copy in the project) is refused and the
    teammate is told the one install command (rule 10, Q-S0071-4)."""
    root = project(tmp_path, clean())
    shutil.copytree(KIT, root / "scripts" / "agk", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "scripts" / "agk" / "probe_example.py").write_text(PROBE, encoding="utf-8")
    out = run(root / "scripts" / "agk" / "probe_example.py", root)
    refused(out, PIN)
    assert kit_root.INSTALL in out.stderr


@pytest.mark.parametrize(
    "toml",
    [clean(pin=None), clean(pin=""), clean(version="0.9.0"), clean() + "[other]\n" + "x = 1\n"],
    ids=["no-pin", "empty-pin", "pin-other-than-version", "pinned"],
)
def test_ac2_a_clean_project_must_pin_its_own_version(tmp_path, toml):
    """REQ-078 AC2: no pin, an empty one or one other than `version` (Q-S0071-7) is refused."""
    root, plug = project(tmp_path, toml), plugin(tmp_path)
    out = run(probe(plug), root)
    if toml.startswith(clean()):
        assert out.returncode == 0, out.stderr
    else:
        refused(out, PIN, "0.9.0")


def test_ac2_the_resolver_refuses_another_version_before_the_gate(tmp_path):
    """REQ-078 AC2: `kit_root.py` (the gate's entry, which holds no `common`) checks the pin too."""
    root, plug = project(tmp_path, clean()), plugin(tmp_path, "0.9.0")
    for args in ((), ("--form",), ("governance",)):
        out = run(plug / "scripts" / "agk" / "kit_root.py", root, *args)
        refused(out, PIN, "0.9.0")
        assert out.stdout == ""


def test_ac2_a_second_worktree_reads_the_same_plugin(tmp_path):
    """REQ-078 AC2: a builder worktree of the sample is held to the same pin (rule 10)."""
    root, plug = project(tmp_path, clean()), plugin(tmp_path)
    who = ("-c", "user.name=cb-example-1", "-c", "user.email=cb@example.com")
    git(root, *who, "add", ".")
    git(root, *who, "commit", "-qm", "sample")
    git(root, "worktree", "add", "-q", str(tmp_path / "worktree-example"))
    tree = tmp_path / "worktree-example"
    (tree / "sub").mkdir()
    assert run(probe(plug), tree / "sub").returncode == 0
    refused(run(probe(plugin(tmp_path, "0.9.0", "older-example")), tree), PIN)


@pytest.mark.parametrize("toml", ['version = "0.9.0"\n', ""], ids=["installed", "no-version"])
def test_ac7_an_installed_project_is_not_checked(tmp_path, toml):
    """REQ-078 AC7: an installed sample behaves as today, whatever the plugin's version."""
    root, plug = project(tmp_path, toml), plugin(tmp_path, "0.10.0")
    assert run(probe(plug), root).returncode == 0
    assert kit_root.pin_refusal(root, plug) is None


def test_ac7_the_kit_repository_runs_unpinned():
    """REQ-078 AC7: the kit's own repository keeps its layout and needs no pin."""
    assert kit_root.pin_refusal(ROOT, ROOT) is None
    assert "kit" not in tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))


def test_ac2_the_kit_table_is_a_known_table():
    """REQ-078 AC2: `[kit]` reads `layout` and `plugin_version`; a pin at the top level is named."""
    assert config.TABLE_KEYS["kit"] == frozenset({"layout", "plugin_version"})
    found = config.misplaced_settings({"plugin_version": PIN})
    assert found == [("plugin_version", config.TOP_LEVEL, ("kit",))]


def test_ac2_the_template_documents_the_table_and_leaves_it_off():
    """REQ-078 AC2: the template names the table and its pin, commented out, so `init` and `adopt`
    keep the installed layout (only the migration of rule 8 writes the table)."""
    text = (ROOT / "kit" / "templates" / "agk.toml").read_text(encoding="utf-8")
    assert "# [kit]" in text and '# plugin_version = "' in text
    assert "kit" not in tomllib.loads(re.sub(r"\{\{\w+\}\}", "x", text))
