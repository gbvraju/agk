"""Tests of `touched_files` (SPEC-0072 rule 7, proposed amendment; REQ-079 AC5; brief #1844,
ADR-0773).

An adopted project with `touched_files = "meet"` holds each file its change edits to the standards
pack in full: a baselined file edited with its finding left fails the pack step, naming the setting
and never the file; with `"hold"` or the key absent the step keeps rule 7's no-rise. The files a
change touches are those from the merge base of the resolved base to the working tree, less
deletions. With no base outside CI, or a tree with no `.git` (the personal floor's), the touched
rule is `not run`; in CI with no base it is one failure row. Only the pack's `lint`, `format` and
`type` steps are judged: the floors and the counted gates of rules 3 and 5 keep no-rise. A stub
pack whose tally the test gives stands in for the tools: git repositories in `tmp_path`, invented
data only (example.com), no network.
"""

from __future__ import annotations

import shutil
import socket
import subprocess  # nosec B404 - the test drives git with fixed argument lists
import sys
import types
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_playbooks  # noqa: E402
import run_gates  # noqa: E402

RESULTS = run_gates.results  # the real runner and composer, before the stubs replace them
STANDARD = check_playbooks.standard
HOME = "src/pages/home.ts"
ABOUT = "src/pages/about.ts"
FORMAT_FILE = "config/agk-baseline/standards-stub-format.txt"
TOUCHED = (
    "standards stub format: SPEC-0072 rule 7: a file this change touches must meet the pack "
    "(setting: touched_files)"
)
NO_BASE = "standards touched: no base (setting: touched_files)"
REFUSED = "not an accepted value (setting: touched_files)"
FINDINGS: dict[str, dict[str, int]] = {}


def _stub() -> types.ModuleType:
    """A pack module whose per-file tally is FINDINGS: no tool runs."""
    mod = types.ModuleType("gates.stub_pack")
    mod.STACKS = ("stub",)
    mod.STEP_NAMES = ("stub-lint", "stub-format", "stub-type")
    mod.on = lambda _root: True

    def run(_root: Path, _entry: dict, tally: dict | None = None) -> list:
        own = {s: dict(FINDINGS.get(s, {})) for s in ("floor", "lint", "format", "type")}
        if tally is not None:
            tally.update(own)
        return [
            (
                s,
                [f"SPEC-0072 rule 6: {s} rule x (path class: product code)"]
                if any(c.values())
                else [],
            )
            for s, c in own.items()
        ]

    mod.run = run
    return mod


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the touched rule opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(sys.modules, "gates.stub_pack", _stub())
    monkeypatch.setattr(run_gates, "PACKS", ("stub_pack",))
    entry = {"stack": "stub", "lint": "stub-lint", "format": "stub-format", "type": "stub-type"}
    monkeypatch.setattr(check_playbooks, "standard", lambda _p, _r: ({}, [entry], []))
    monkeypatch.setattr(
        run_gates,
        "results",
        lambda root, write=False: run_gates.pack_results(Path(root), Path(root), write),
    )
    FINDINGS.clear()
    FINDINGS["format"] = {HOME: 1, ABOUT: 1}


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def commit(root: Path, files: dict[str, str], msg: str = "change") -> None:
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg)


def project(tmp_path: Path, setting: str | None = '"meet"', mode: str = "adopt") -> Path:
    """An adopted project on `main` with two baselined files, then a branch `feature`."""
    root = tmp_path / "p"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    line = "" if setting is None else f"touched_files = {setting}\n"
    commit(
        root,
        {
            "agk.toml": f'mode = "{mode}"\n{line}',
            HOME: "export const site = 'https://example.com'\n",
            ABOUT: "export const about = 1\n",
            FORMAT_FILE: f"{ABOUT} 1\n{HOME} 1\n",
        },
        "adopt",
    )
    git(root, "checkout", "-q", "-b", "feature")
    return root


def edit(root: Path, rel: str = HOME, msg: str = "edit") -> None:
    commit(root, {rel: (root / rel).read_text(encoding="utf-8") + "export const x = 2\n"}, msg)


def gates(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    return code, capsys.readouterr().out


def test_meet_fails_an_edited_baselined_file_with_its_finding_left(tmp_path, capsys) -> None:
    """REQ-079 AC5: the failure of AD-09, named by the setting and never the file."""
    root = project(tmp_path)
    edit(root)
    code, out = gates(root, capsys)
    assert code == 1, out
    assert f"FAIL gates: {TOUCHED}" in out
    for value in ("home", "about", "example.com"):
        assert value not in out
    assert (root / FORMAT_FILE).read_text(encoding="utf-8") == f"{ABOUT} 1\n{HOME} 1\n"


@pytest.mark.parametrize("setting", ['"hold"', None])
def test_hold_or_absent_keeps_no_rise(setting, tmp_path, capsys) -> None:
    """REQ-079 AC5: today's `(baseline)` pass, the default."""
    root = project(tmp_path, setting)
    edit(root)
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "touched" not in out and "ok standards stub" in out


def test_meet_passes_an_untouched_baselined_file(tmp_path, capsys) -> None:
    """REQ-079 AC5: untouched files keep their lines."""
    root = project(tmp_path)
    commit(root, {"README.md": "an example.com readme\n"})
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "ok standards stub" in out


def test_meet_passes_a_touched_file_made_clean_and_notes_the_fall(tmp_path, capsys) -> None:
    """REQ-079 AC5: a touched clean file passes; its line falls."""
    root = project(tmp_path)
    edit(root)
    FINDINGS["format"] = {ABOUT: 1}
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "baseline standards stub format: a count fell in 1 file" in out


def test_meet_judges_an_uncommitted_edit(tmp_path, capsys) -> None:
    """REQ-079 AC5: the working tree is read."""
    root = project(tmp_path)
    (root / HOME).write_text("export const site = 3\n", encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 1 and TOUCHED in out, out


def test_meet_fails_a_touched_file_not_in_the_baseline_as_today(tmp_path, capsys) -> None:
    """REQ-079 AC5: a new file counts from 0, with today's rule 7 line."""
    root = project(tmp_path)
    commit(root, {"src/pages/new.ts": "export const n = 1\n"})
    FINDINGS["format"] = {HOME: 1, ABOUT: 1, "src/pages/new.ts": 1}
    code, out = gates(root, capsys)
    assert code == 1
    assert "standards stub format: SPEC-0072 rule 7: a finding is new" in out


def test_meet_on_the_adoption_run_writes_the_baseline_and_is_green(tmp_path, capsys) -> None:
    """REQ-079 AC5: the first run of rule 7 is green under either value."""
    root = project(tmp_path)
    (root / FORMAT_FILE).unlink()
    git(root, "commit", "-q", "-am", "no baseline yet")
    edit(root)
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "baseline standards stub format: written" in out


def test_meet_in_init_mode_has_no_baseline_and_no_effect(tmp_path, capsys) -> None:
    """REQ-079 AC5: init has an empty baseline; the findings fail as before."""
    root = project(tmp_path, mode="init")
    (root / FORMAT_FILE).unlink()
    git(root, "commit", "-q", "-am", "init")
    code, out = gates(root, capsys)
    assert code == 1
    assert "touched" not in out and "rule 6: format rule x" in out


@pytest.mark.parametrize("value", ['"Meet"', '"strict"', "true", "1", '["meet"]'])
def test_another_value_is_refused_naming_the_setting(value, tmp_path, capsys) -> None:
    """REQ-079: refused naming the setting, never the value."""
    root = project(tmp_path, value)
    code, out = gates(root, capsys)
    assert code == 1
    assert f"FAIL gates: {REFUSED}" in out
    assert value.strip('"[]').lower() not in out.lower().replace("not an accepted", "")


def test_no_base_outside_ci_is_not_run_and_no_rise_holds(tmp_path, capsys) -> None:
    """REQ-079: nothing resolves; the touched rule is never `ok`."""
    root = project(tmp_path)
    edit(root)
    git(root, "branch", "-q", "-D", "main")
    code, out = gates(root, capsys)
    assert code == 0, out
    assert f"not run {NO_BASE}" in out
    assert out.rstrip().endswith("not run: standards touched)")


def test_a_tree_with_no_git_folder_is_not_run(tmp_path, capsys) -> None:
    """REQ-079: the personal floor's tree from `git archive`."""
    root = project(tmp_path)
    edit(root)
    shutil.rmtree(root / ".git")
    code, out = gates(root, capsys)
    assert code == 0, out
    assert f"not run {NO_BASE}" in out


def test_no_base_in_ci_is_one_failure_row(tmp_path, capsys, monkeypatch) -> None:
    """REQ-079: today's CI line, as a row of the runner, never a crash."""
    root = project(tmp_path)
    edit(root)
    git(root, "branch", "-q", "-D", "main")
    monkeypatch.setenv("CI", "true")
    code, out = gates(root, capsys)
    assert code == 1
    assert "FAIL gates: standards touched: no base ref resolves in CI" in out


def test_a_file_changed_only_on_the_default_branch_is_not_touched(tmp_path, capsys) -> None:
    """REQ-079: a stale base; the merge base, not the base's tip, starts the diff."""
    root = project(tmp_path)
    commit(root, {"README.md": "an example.com readme\n"})
    git(root, "checkout", "-q", "main")
    edit(root, msg="main edits home")
    git(root, "checkout", "-q", "feature")
    code, out = gates(root, capsys)
    assert code == 0, out


def test_the_merge_refs_first_parent_is_the_base(tmp_path, capsys, monkeypatch) -> None:
    """REQ-079 (ADR-0111): CI checks out the merge ref; AGK_BASE is its first parent."""
    root = project(tmp_path)
    edit(root)
    git(root, "checkout", "-q", "main")
    git(root, "merge", "-q", "--no-ff", "-m", "merge ref", "feature")
    monkeypatch.setenv("AGK_BASE", "HEAD^1")
    code, out = gates(root, capsys)
    assert code == 1 and TOUCHED in out, out


def test_the_floor_keeps_no_rise_under_meet(tmp_path, capsys) -> None:
    """REQ-079 (Q-HK-3): only lint, format and type are judged; a touched configuration's held
    floor stays held."""
    root = project(tmp_path)
    commit(
        root,
        {
            "config/agk-baseline/standards-stub-floor.txt": "eslint.config.js 1\n",
            "eslint.config.js": "export default []\n",
        },
        "floor",
    )
    git(root, "checkout", "-q", "main")
    git(root, "merge", "-q", "feature")
    git(root, "checkout", "-q", "-b", "next")
    commit(root, {"eslint.config.js": "export default [{}]\n"})
    FINDINGS["floor"] = {"eslint.config.js": 1}
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "standards stub floor (baseline): 1 held" in out


def test_the_counted_gates_of_rules_3_and_5_keep_no_rise(tmp_path, capsys, monkeypatch) -> None:
    """REQ-079 AC5 (Q-HK-3): the layers gate holds an edited baselined file to its line."""
    root = tmp_path / "p"
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    root.mkdir(exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    TOML = 'mode = "adopt"\ntouched_files = "meet"\n'  # noqa: N806
    bad = "from api import routes\n"  # data may not import api (the api-service playbook)
    commit(
        root,
        {
            "agk.toml": TOML + '\n[delivery]\nwork_type = "api-service"\n',
            "api/__init__.py": "",
            "api/routes.py": "",
            "domain/__init__.py": "",
            "domain/rules.py": "",
            "data/__init__.py": "",
            "data/store.py": bad,
        },
    )
    FINDINGS.clear()
    monkeypatch.setattr(run_gates, "results", RESULTS)
    monkeypatch.setattr(check_playbooks, "standard", STANDARD)
    assert gates(root, capsys)[0] == 0
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "baselines written")
    git(root, "checkout", "-q", "-b", "feature")
    commit(root, {"data/store.py": bad + "X = 1\n"})
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "ok layers (baseline)" in out and "touched" not in out
