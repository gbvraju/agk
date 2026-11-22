"""SPEC-0041 build (l): the user-scope plugin, upgrade, detach with the hook (brief #1506).

Advances REQ-048 (AC1). Rule 26: the sidecar records the plugin version and `doctor.py` on a
sidecar reports each pinned file that differs from `kit/hashes.json` for it. Rule 27: `personal.py
upgrade` moves `[personal] schema` one step and one sidecar commit at a time and refuses a newer
schema; `detach` removes the hook only when its bytes are what `hook install` wrote. Rule 19:
`personal.py hook install|remove`, the one write under `.git/`. Rule 28: on Windows `doctor.py`
says it did not check the permissions. The walk proves the product clone and every file under its
`.git/` unchanged through attach, survey, the gate, report, upgrade and detach. Invented
repositories and sidecars in `tmp_path`, a stub gitleaks, no network.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import doctor  # noqa: E402
import personal  # noqa: E402
import personal_state as ps  # noqa: E402

PERSON = "member-example-1"
ORIGIN = "https://example.com/team/demo-shop.git"
RUNNER = """import pathlib, runpy, sys
sys.path.insert(0, ".")
bad = 0
for path in sorted(pathlib.Path("tests").glob("test_*.py")):
    try:
        runpy.run_path(str(path))
    except AssertionError:
        bad += 1
sys.exit(1 if bad else 0)
"""
POSIX = pytest.mark.skipif(os.name == "nt", reason="a POSIX shell runs the hook here")


def plugin_version() -> str:
    """The plugin's version, read when a test runs (a copied kit may have no plugin folder)."""
    return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))["version"]


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(root: Path, subject: str) -> str:
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", subject)  # fmt: skip
    return git(root, "rev-parse", "HEAD")


def make_clone(tmp_path: Path) -> Path:
    """`main` has one passing test; `work` changes the code and adds a test red on `main`."""
    clone = tmp_path / "clone"
    (clone / "tests").mkdir(parents=True)
    git(clone, "init", "-q", "-b", "main")
    git(clone, "remote", "add", "origin", ORIGIN)
    (clone / "run_tests.py").write_text(RUNNER, encoding="utf-8")
    (clone / "shop.py").write_text("TOTAL = 2\n", encoding="utf-8")
    (clone / "tests" / "test_old.py").write_text("import shop\nassert shop.TOTAL > 0\n", "utf-8")
    commit(clone, "base")
    git(clone, "checkout", "-q", "-b", "work")
    (clone / "shop.py").write_text("TOTAL = 3\n", encoding="utf-8")
    (clone / "tests" / "test_total.py").write_text("import shop\nassert shop.TOTAL == 3\n", "utf-8")
    commit(clone, "the total counts every item")
    return clone


def env_for(home: Path, path: str | None = None) -> dict[str, str]:
    skip = ("CLAUDECODE", "AGK_HOME", "AGK_BASE", "GITHUB_BASE_REF", "CI")
    env = {k: v for k, v in os.environ.items() if k not in skip}
    env.update({"AGK_HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1"})
    if path:
        env["PATH"] = path
    return env


def run(script: str, *args: str, env: dict, stdin: str | None = None):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, env=env, input=stdin,
    )  # fmt: skip


def attached(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    clone, home = make_clone(tmp_path), tmp_path / "state"
    env = env_for(home)
    done = run("personal_state.py", "attach", "--person", PERSON, "--clone", str(clone), env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    (side,) = (home / "projects").iterdir()
    return clone, home, side, env


def own_table(tmp_path: Path, source: Path = ROOT) -> Path:
    """A copy of the kit's scripts whose `kit/hashes.json` row for the plugin version holds the
    digests of the pinned files under `source`, this checkout by default (brief #1704): the
    doctor's comparison is proved on any change to a pinned file between releases, not the release
    table's freshness (session rule 14: a build never edits `kit/hashes.json`)."""
    plugin = tmp_path / "plugin"
    script = plugin / "scripts" / "agk" / "doctor.py"
    if script.is_file():
        return script
    shutil.copytree(SCRIPTS, plugin / "scripts" / "agk",
                    ignore=shutil.ignore_patterns("__pycache__"))  # fmt: skip
    verbatim = {
        rel: [hashlib.sha256((source / rel).read_bytes()).hexdigest()]
        for rel in common.PERSONAL_PINNED
    }
    table = {"releases": {plugin_version(): {"verbatim": verbatim}}}
    (plugin / "kit").mkdir()
    (plugin / "kit" / "hashes.json").write_text(json.dumps(table), encoding="utf-8")
    return script


def doctor_of(tmp_path: Path, side: Path, env: dict, source: Path = ROOT):
    """`doctor.py` on the sidecar, run from the copy of `own_table`."""
    script = own_table(tmp_path, source)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), str(side)], capture_output=True, text=True, env=env
    )  # fmt: skip


def scanner(tmp_path: Path) -> str:
    """A PATH with git and python and a stub gitleaks that finds nothing."""
    folder = tmp_path / "bin"
    folder.mkdir()
    for tool in ("git", "sh"):
        found = shutil.which(tool)
        assert found
        (folder / tool).symlink_to(found)
    stub = folder / "gitleaks"
    stub.write_text(f"#!{sys.executable}\nraise SystemExit(0)\n", encoding="utf-8")
    stub.chmod(0o755)
    return str(folder)


def product(clone: Path) -> tuple:
    """The clone's status and every file under `.git/` by path, size and SHA-256 (rule 27)."""
    files = {}
    for path in sorted((clone / ".git").rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            files[path.relative_to(clone).as_posix()] = (
                len(data),
                hashlib.sha256(data).hexdigest(),
            )
    status = git(clone, "--no-optional-locks", "status", "--porcelain")
    tree = sorted(
        p.relative_to(clone).as_posix() for p in clone.rglob("*") if ".git" not in p.parts
    )
    return status, files, tree


def hook_of(clone: Path) -> Path:
    return clone / ".git" / "hooks" / "pre-push"


def settings(side: Path, old: str, new: str) -> None:
    toml = side / "agk.toml"
    text = toml.read_text(encoding="utf-8")
    assert old in text
    toml.write_text(text.replace(old, new), encoding="utf-8")
    commit(side, "settings")


# Rule 26: the user-scope plugin, the plugin version and the pinned files.


def test_rule26_attach_records_the_plugin_version_and_no_script(tmp_path):
    """REQ-048 AC1: rule 26 (the sidecar stores the plugin version and never a script)."""
    _, _, side, _ = attached(tmp_path)
    table = common.personal_table(side)
    assert table is not None and table["plugin_version"] == plugin_version()
    tracked = git(side, "ls-files").splitlines()
    assert not [p for p in tracked if p.endswith((".py", ".sh"))]


def test_rule26_doctor_on_a_fresh_sidecar_finds_the_pinned_files_unchanged(tmp_path):
    """REQ-048 AC1: rule 26 (the four pinned files match `kit/hashes.json` for the version)."""
    _, _, side, env = attached(tmp_path)
    done = doctor_of(tmp_path, side, env)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert lines[0] == "personal mode: forge files, level light, disclosure both"
    assert f"pinned: {len(common.PERSONAL_PINNED)} files match kit/hashes.json" in lines


def test_rule26_doctor_reports_a_pinned_file_changed_by_hand(tmp_path):
    """REQ-048 AC1: rule 26 and Q-S0041-14 (a changed copy is reported, its text never shown)."""
    _, _, side, env = attached(tmp_path)
    law = side / "constitution" / "principles.md"
    law.write_text(law.read_text(encoding="utf-8") + "13. A rule of my own.\n", encoding="utf-8")
    done = doctor_of(tmp_path, side, env)
    assert "pinned: constitution/principles.md differs from kit/hashes.json" in done.stdout
    assert "A rule of my own" not in done.stdout
    assert "config/core-rules.md differs" not in done.stdout
    (side / "config" / "core-rules.md").unlink()
    done = doctor_of(tmp_path, side, env)
    assert "pinned: config/core-rules.md is missing" in done.stdout


def test_rule26_doctor_passes_a_pinned_file_changed_between_releases(tmp_path):
    """REQ-048 AC1: rule 26 and brief #1704 (a pull request that changes a pinned file: the copy
    matches the plugin's own table, and the released row still reports it)."""
    _, _, side, env = attached(tmp_path)
    rules = side / "config" / "session-rules.md"
    rules.write_text(rules.read_text(encoding="utf-8") + "A word.\n", encoding="utf-8")
    done = doctor_of(tmp_path, side, env, source=side)
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"pinned: {len(common.PERSONAL_PINNED)} files match kit/hashes.json" in done.stdout
    done = run("doctor.py", str(side), env=env)
    assert "pinned: config/session-rules.md differs from kit/hashes.json" in done.stdout


def test_rule26_doctor_says_when_it_cannot_check_the_pinned_files(tmp_path):
    """REQ-048 AC1: rule 26 (no version recorded, or none in the table: not checked, by setting)."""
    _, _, side, env = attached(tmp_path)
    settings(side, f'plugin_version = "{plugin_version()}"', 'plugin_version = "0.0.0-example"')
    done = run("doctor.py", str(side), env=env)
    assert done.returncode == 0
    assert "pinned: not checked: kit/hashes.json has no row for the recorded version " \
        "(setting: personal.plugin_version)" in done.stdout  # fmt: skip
    assert "0.0.0-example" not in done.stdout
    settings(side, 'plugin_version = "0.0.0-example"\n', "")
    done = run("doctor.py", str(side), env=env)
    assert "pinned: not checked: no plugin version is recorded " \
        "(setting: personal.plugin_version)" in done.stdout  # fmt: skip


def test_rule28_doctor_on_windows_says_it_did_not_check_the_permissions(tmp_path):
    """REQ-048 AC1: rule 28 (Windows inherits the profile's permissions; doctor says so)."""
    _, _, side, _ = attached(tmp_path)
    code, text = doctor.personal_line(side, osname="nt")
    assert code == 0
    assert doctor.WINDOWS_PERMISSIONS in text.splitlines()
    code, text = doctor.personal_line(side, osname="posix")
    assert doctor.WINDOWS_PERMISSIONS not in text


# Rule 27: upgrade, one step and one sidecar commit at a time.


def subjects(side: Path) -> list[str]:
    return git(side, "log", "--format=%s").splitlines()


def test_rule27_upgrade_on_the_current_schema_changes_nothing(tmp_path, capsys):
    """REQ-048 AC1: rule 27 (nothing to migrate: no commit)."""
    _, _, side, _ = attached(tmp_path)
    before = subjects(side)
    assert personal.main(["upgrade", "--sidecar", str(side)]) == 0
    assert f"upgrade: schema {ps.PLUGIN_SCHEMA} is current" in capsys.readouterr().out
    assert subjects(side) == before


def test_rule27_upgrade_refuses_a_schema_newer_than_the_plugins(tmp_path, capsys):
    """REQ-048 AC1: rule 27 (a newer schema is refused, naming the setting)."""
    _, _, side, _ = attached(tmp_path)
    settings(side, "schema = 1", f"schema = {ps.PLUGIN_SCHEMA + 1}")
    before = subjects(side)
    assert personal.main(["upgrade", "--sidecar", str(side)]) == 1
    out = capsys.readouterr().out
    assert "refused:" in out and "setting: personal.schema" in out
    assert subjects(side) == before


def test_rule27_upgrade_takes_two_steps_as_two_commits(tmp_path, monkeypatch, capsys):
    """REQ-048 AC1: rule 27 (each step its own sidecar commit, the schema raised by one)."""
    _, _, side, _ = attached(tmp_path)

    def step(name: str):
        def migrate(sidecar: Path) -> list[str]:
            (sidecar / "records" / f"{name}.txt").write_text(name + "\n", encoding="utf-8")
            return [f"records/{name}.txt"]

        return migrate

    monkeypatch.setattr(ps, "PLUGIN_SCHEMA", 3)
    monkeypatch.setattr(ps, "MIGRATIONS", {1: step("one"), 2: step("two")})
    assert personal.main(["upgrade", "--sidecar", str(side)]) == 0
    out = capsys.readouterr().out
    assert "upgrade: schema 1 to 2" in out and "upgrade: schema 2 to 3" in out
    assert subjects(side)[:2] == [
        "personal: upgrade schema 2 to 3",
        "personal: upgrade schema 1 to 2",
    ]
    assert git(side, "show", "--name-only", "--format=", "HEAD~1").splitlines() == [
        "agk.toml", "records/one.txt",
    ]  # fmt: skip
    assert common.personal_table(side)["schema"] == 3
    assert git(side, "status", "--porcelain") == ""


def test_rule27_upgrade_refuses_a_sidecar_with_uncommitted_changes(tmp_path, monkeypatch, capsys):
    """REQ-048 AC1: rule 27 (a step's commit holds the step only)."""
    _, _, side, _ = attached(tmp_path)
    monkeypatch.setattr(ps, "PLUGIN_SCHEMA", 2)
    monkeypatch.setattr(ps, "MIGRATIONS", {1: lambda sidecar: []})
    (side / "records" / "draft.txt").write_text("draft\n", encoding="utf-8")
    assert personal.main(["upgrade", "--sidecar", str(side)]) == 1
    assert "uncommitted" in capsys.readouterr().out
    assert common.personal_table(side)["schema"] == 1


# Rule 19: the opt-in pre-push hook, the one write under `.git/`.


def hook(clone: Path, env: dict, action: str):
    return run("personal.py", "hook", action, "--clone", str(clone), env=env)


def test_rule19_hook_install_writes_the_one_file_under_git(tmp_path):
    """REQ-048 AC1: rule 19 (untracked `.git/hooks/pre-push`, executable, calling the gate)."""
    clone, _, _, env = attached(tmp_path)
    before = product(clone)
    done = hook(clone, env, "install")
    assert done.returncode == 0, done.stdout + done.stderr
    after = product(clone)
    assert after[0] == "" and after[2] == before[2]
    assert set(after[1]) - set(before[1]) == {".git/hooks/pre-push"}
    assert {k: v for k, v in after[1].items() if k != ".git/hooks/pre-push"} == before[1]
    text = hook_of(clone).read_text(encoding="utf-8")
    assert ps.HOOK_MARK in text and " gate " in text and "--approve" in text
    assert str(SCRIPTS / "personal.py") in text
    if os.name != "nt":
        assert os.access(hook_of(clone), os.X_OK)
    assert hook_of(clone).read_bytes() == ps.hook_text(str(SCRIPTS / "personal.py"))


def test_rule19_hook_install_is_refused_with_core_hookspath_set(tmp_path):
    """REQ-048 AC1: rule 19 (`core.hooksPath` set: refused naming the setting, nothing written)."""
    clone, _, _, env = attached(tmp_path)
    git(clone, "config", "core.hooksPath", "example-hooks")
    before = product(clone)
    done = hook(clone, env, "install")
    assert done.returncode == 1
    assert "setting: core.hooksPath" in done.stdout and "example-hooks" not in done.stdout
    assert product(clone) == before


def test_rule19_hook_install_is_refused_over_an_existing_pre_push(tmp_path):
    """REQ-048 AC1: rule 19 (an existing `pre-push` is refused and left byte for byte)."""
    clone, _, _, env = attached(tmp_path)
    hook_of(clone).parent.mkdir(exist_ok=True)
    hook_of(clone).write_bytes(b"#!/bin/sh\nexit 0\n")
    before = product(clone)
    done = hook(clone, env, "install")
    assert done.returncode == 1 and "pre-push" in done.stdout
    assert product(clone) == before


def test_rule19_hook_install_is_refused_on_a_clone_not_attached(tmp_path):
    """REQ-048 AC1: rule 19 (the hook calls the gate, which needs the sidecar)."""
    clone = make_clone(tmp_path)
    before = product(clone)
    done = hook(clone, env_for(tmp_path / "state"), "install")
    assert done.returncode == 1 and "not attached" in done.stdout
    assert product(clone) == before


@POSIX
def test_rule19_the_hook_fails_closed_when_its_plugin_path_is_gone(tmp_path):
    """REQ-048 AC1: rule 19 (one line, exit 1, when the recorded plugin path no longer exists)."""
    clone, _, _, _ = attached(tmp_path)
    hook_of(clone).parent.mkdir(exist_ok=True)
    hook_of(clone).write_bytes(ps.hook_text(str(tmp_path / "gone" / "personal.py")))
    hook_of(clone).chmod(0o755)
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [str(hook_of(clone)), "origin", ORIGIN], cwd=clone, capture_output=True, text=True,
        input="", env={"PATH": scanner(tmp_path)},
    )  # fmt: skip
    assert done.returncode == 1
    assert done.stderr.strip().splitlines() == [ps.HOOK_GONE]


def test_rule19_hook_remove_removes_only_the_hook_it_wrote(tmp_path):
    """REQ-048 AC1: rule 19 (an unedited hook goes; an edited one stays and is named)."""
    clone, _, _, env = attached(tmp_path)
    before = product(clone)
    assert hook(clone, env, "install").returncode == 0
    done = hook(clone, env, "remove")
    assert done.returncode == 0, done.stdout
    assert product(clone) == before
    assert hook(clone, env, "install").returncode == 0
    with hook_of(clone).open("a", encoding="utf-8") as edited:
        edited.write("# my own line\n")
    done = hook(clone, env, "remove")
    assert done.returncode == 1 and "changed by hand" in done.stdout
    assert hook_of(clone).is_file()


# Rule 27: detach with the hook.


def test_rule27_detach_removes_the_hook_only_when_its_bytes_are_unchanged(tmp_path):
    """REQ-048 AC1: rule 27 (the export line first; the unedited hook removed)."""
    clone, home, _, env = attached(tmp_path)
    before = product(clone)
    assert hook(clone, env, "install").returncode == 0
    done = run("personal_state.py", "detach", "--clone", str(clone), env=env)
    assert done.returncode == 0, done.stdout
    assert done.stdout.splitlines()[0] == ps.EXPORT_LINE
    assert "detach: removed the pre-push hook" in done.stdout
    assert product(clone) == before
    assert ps.registry(home) == {}


def test_rule27_detach_leaves_a_hook_edited_by_hand_and_says_so(tmp_path):
    """REQ-048 AC1: rule 27 (a hook edited by hand stays, byte for byte)."""
    clone, home, _, env = attached(tmp_path)
    assert hook(clone, env, "install").returncode == 0
    with hook_of(clone).open("a", encoding="utf-8") as edited:
        edited.write("# my own line\n")
    kept = hook_of(clone).read_bytes()
    done = run("personal_state.py", "detach", "--clone", str(clone), env=env)
    assert done.returncode == 0
    assert "detach: the pre-push hook was changed by hand; left in place" in done.stdout
    assert hook_of(clone).read_bytes() == kept
    assert ps.registry(home) == {}


def test_rule27_detach_leaves_a_pre_push_it_did_not_write(tmp_path):
    """REQ-048 AC1: rule 27 (a hook without the mark is not the kit's and is not named)."""
    clone, _, _, env = attached(tmp_path)
    hook_of(clone).parent.mkdir(exist_ok=True)
    hook_of(clone).write_bytes(b"#!/bin/sh\nexit 0\n")
    done = run("personal_state.py", "detach", "--clone", str(clone), env=env)
    assert done.returncode == 0 and "pre-push" not in done.stdout
    assert hook_of(clone).read_bytes() == b"#!/bin/sh\nexit 0\n"


class FakeTerminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_rule27_delete_state_with_the_hook_refused_or_mistyped_deletes_nothing(
    tmp_path, monkeypatch, capsys
):
    """REQ-048 AC1: rule 27 (an agent session or a mistyped id: the state and the hook stay)."""
    clone, home, side, env = attached(tmp_path)
    assert hook(clone, env, "install").returncode == 0
    monkeypatch.setenv("AGK_HOME", str(home))
    args = ["detach", "--delete-state", "--clone", str(clone)]
    monkeypatch.setenv("CLAUDECODE", "1")
    assert ps.main(args, stdin=FakeTerminal(side.name + "\n")) == 1
    monkeypatch.delenv("CLAUDECODE")
    assert ps.main(args, stdin=FakeTerminal("demo-shop-000000000000\n")) == 1
    assert "nothing deleted" in capsys.readouterr().out
    assert side.is_dir() and ps.registry(home) and hook_of(clone).is_file()
    assert ps.main(args, stdin=FakeTerminal(side.name + "\n")) == 0
    assert not side.exists() and not hook_of(clone).exists()


# Rule 27: the product-untouched walk.


def test_rule27_the_product_is_untouched_through_the_whole_life_of_a_sidecar(
    tmp_path, monkeypatch, capsys
):
    """REQ-048 AC1: rules 4 and 27 (status empty, every `.git/` file unchanged, end to end)."""
    clone, home, side, env = attached(tmp_path)
    before = product(clone)
    assert before[0] == ""
    command = f"{shlex.quote(sys.executable)} run_tests.py"
    settings(side, 'level = "light"', f'level = "light"\ntest_command = {json.dumps(command)}')
    assert product(clone) == before
    path = scanner(tmp_path)
    done = run("survey.py", "--clone", str(clone), "--today", "2026-11-20", env=env_for(home, path))
    assert done.returncode == 0, done.stdout + done.stderr
    assert product(clone) == before
    gated = run("personal.py", "gate", "--clone", str(clone), "--base", "main", "--approve",
                env=env_for(home, path))  # fmt: skip
    assert gated.returncode == 0, gated.stdout + gated.stderr
    assert "gate: passed" in gated.stdout
    assert product(clone) == before
    done = run("personal.py", "report", "--clone", str(clone), env=env_for(home, path))
    assert done.returncode == 0, done.stdout + done.stderr
    assert product(clone) == before
    monkeypatch.setenv("AGK_HOME", str(home))
    monkeypatch.setattr(ps, "PLUGIN_SCHEMA", 2)
    monkeypatch.setattr(ps, "MIGRATIONS", {1: lambda sidecar: []})
    assert personal.main(["upgrade", "--clone", str(clone)]) == 0
    assert "upgrade: schema 1 to 2" in capsys.readouterr().out
    assert product(clone) == before
    done = run("personal_state.py", "detach", "--clone", str(clone), env=env)
    assert done.returncode == 0, done.stdout
    assert product(clone) == before
