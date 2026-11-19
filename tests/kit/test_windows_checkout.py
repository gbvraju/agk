"""The guarded merge's check gives the same result on Windows as on Linux (brief #1540, ADR-0648).

On Windows (Git for Windows installs with `core.autocrlf=true`) `merge_cleared.py --pr 1533 --owner`
printed "3 failed, 51 passed" and held, while the same merge passed on Linux: its temporary tree was
checked out with CRLF line ends, its hashes were taken from the bytes on disk, and two kit tests
built names with `\\`. Now every temporary checkout of the kit passes `common.CHECKOUT` (the
committed bytes whatever the person's git configuration says; a project's own `eol` attributes
still win), a hash taken from the working tree is taken as committed (`common.committed_bytes`),
the check's folder and its `TEMP`, `TMP` and `TMPDIR` hold the long name on Windows, and the kit's
tests compare names with `/`.

Windows is simulated on Linux: git honours `core.autocrlf=true` on Linux too, so each CRLF
checkout here is a real one; `os.name` and the long-name call are faked; names go through
`PureWindowsPath`. Invented data only (example.com); no network.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote

import pytest

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import batch  # noqa: E402
import common  # noqa: E402
import design_prototype_check  # noqa: E402
import evidence  # noqa: E402
import impact  # noqa: E402
import kit_hashes  # noqa: E402
import merge_cleared  # noqa: E402
import plan_intake  # noqa: E402

ENV = {
    "GIT_AUTHOR_NAME": "Example",
    "GIT_AUTHOR_EMAIL": "example@example.com",
    "GIT_COMMITTER_NAME": "Example",
    "GIT_COMMITTER_EMAIL": "example@example.com",
}
VERBATIM = "config/signals.toml"
TEMPLATE = "kit/templates/readme.md"
MANIFEST = {
    "kit_version": "1.0.0",
    "verbatim": [VERBATIM, "scripts/agk/tool.py"],
    "experimental": [],
    "templates": {"README.md": TEMPLATE},
    "adopt": {"templates": {}, "blocks": {}},
}
FILES = {
    VERBATIM: "[signals]\nname = \"example\"\nlist = [\"a\", \"b\"]\n",
    "scripts/agk/tool.py": "print('example')\nprint('two')\n",
    TEMPLATE: "# Example\n\nA line.\n",
    "kit/manifest.json": json.dumps(MANIFEST, indent=2) + "\n",
}


def git(root: Path, *args: str, data: bytes | None = None) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, input=data, capture_output=True, check=True,
        env={**os.environ, **ENV},
    ).stdout.decode("utf-8")  # fmt: skip


def kit_repo(root: Path, files: dict[str, str] | None = None) -> Path:
    """A small kit-shaped repository whose blobs are all LF, committed with no line-end setting."""
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "core.autocrlf", "false")
    for rel, text in (files or FILES).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "kit")
    return root


def crlf(root: Path) -> Path:
    """ROOT's own configuration made a Windows person's: `core.autocrlf=true`."""
    git(root, "config", "core.autocrlf", "true")
    return root


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- answer 2: one committed-bytes checkout -------------------------------------------------------


def test_the_checkout_options_live_in_common_and_evidence_uses_them():
    """REQ-046: brief #1540 answer 2 (moved from evidence.py; the value is unchanged)."""
    assert common.CHECKOUT == ("-c", "core.autocrlf=false", "-c", "core.eol=lf")
    assert evidence.CHECKOUT is common.CHECKOUT
    assert "\nCHECKOUT = " not in (SCRIPTS / "evidence.py").read_text(encoding="utf-8")


# The one git call under scripts/agk/ that checks out the person's own clone, not a temporary
# tree: `setup.py` makes the session's branch in the WSL clone it set up (brief #1540 answer 2).
PERSONS_OWN = {("setup.py", "checkout")}


def _argument_lists(tree: ast.AST):
    """Each call's positional arguments and each list or tuple literal, as node lists."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node.lineno, node.args
        elif isinstance(node, ast.List | ast.Tuple):
            yield node.lineno, node.elts


def _words(nodes) -> list[str | None]:
    return [n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None
            for n in nodes]  # fmt: skip


def _passes_checkout(nodes) -> bool:
    for n in nodes:
        if isinstance(n, ast.Starred):
            value = n.value
            name = value.id if isinstance(value, ast.Name) else getattr(value, "attr", "")
            if name == "CHECKOUT":
                return True
    return False


def unguarded_checkouts(folder: Path = SCRIPTS) -> list[str]:
    """`file:line kind` of each git argument list under FOLDER that checks out files (a
    `worktree add`, a `checkout`) without `*CHECKOUT` in the same list."""
    found: list[str] = []
    for path in sorted(folder.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for line, nodes in _argument_lists(tree):
            words = _words(nodes)
            kind = None
            if "checkout" in words:
                kind = "checkout"
            for a, b in zip(words, words[1:], strict=False):
                if (a, b) == ("worktree", "add"):
                    kind = "worktree add"
            if kind and not _passes_checkout(nodes) and (path.name, kind) not in PERSONS_OWN:
                found.append(f"{path.name}:{line} {kind}")
    return found


def test_every_temporary_checkout_of_the_kit_passes_the_checkout_options():
    """REQ-046: brief #1540 answer 2 and edge case 9 (red on main's six sites and the three
    checkouts of a clone)."""
    assert unguarded_checkouts() == []


def test_the_structural_test_finds_an_unguarded_checkout(tmp_path):
    """REQ-046: brief #1540 answer 2 (the test of the test: main's form is found)."""
    (tmp_path / "x.py").write_text(
        'git(root, "worktree", "add", "--detach", "-q", str(tree), ref)\n'
        'git(tree, "checkout", "-q", "--detach", commit)\n'
        'git(root, *CHECKOUT, "worktree", "add", "--detach", "-q", str(tree), ref)\n'
        'quiet_git(tree, *common.CHECKOUT, "checkout", "-q", base)\n',
        encoding="utf-8",
    )
    assert unguarded_checkouts(tmp_path) == ["x.py:1 worktree add", "x.py:2 checkout"]


def test_a_crlf_persons_worktree_holds_the_committed_bytes_only_with_the_options(tmp_path):
    """REQ-046: brief #1540 edge case 9 (CRLF in a verbatim file; the old call is the red-before)."""
    root = crlf(kit_repo(tmp_path / "kit"))
    old, new = tmp_path / "old", tmp_path / "new"
    git(root, "worktree", "add", "--detach", "-q", str(old), "HEAD")
    git(root, *common.CHECKOUT, "worktree", "add", "--detach", "-q", str(new), "HEAD")
    blob = FILES[VERBATIM].encode("utf-8")
    assert (old / VERBATIM).read_bytes() == blob.replace(b"\n", b"\r\n")
    assert (new / VERBATIM).read_bytes() == blob


def test_a_projects_own_eol_attribute_still_wins(tmp_path):
    """REQ-046: brief #1540 answer 2 (attributes win over the options, in the check as in CI)."""
    files = {**FILES, ".gitattributes": "*.bat text eol=crlf\n", "run.bat": "echo one\necho two\n"}
    root = crlf(kit_repo(tmp_path / "kit", files))
    tree = tmp_path / "tree"
    git(root, *common.CHECKOUT, "worktree", "add", "--detach", "-q", str(tree), "HEAD")
    assert (tree / "run.bat").read_bytes() == b"echo one\r\necho two\r\n"
    assert b"\r\n" not in (tree / VERBATIM).read_bytes()


def test_the_batch_tree_is_reset_to_the_committed_bytes(tmp_path):
    """REQ-046: brief #1540 answer 2 (`batch.py` also checks out and resets in its tree)."""
    root = crlf(kit_repo(tmp_path / "kit"))
    tree = tmp_path / "tree"
    git(root, *common.CHECKOUT, "worktree", "add", "--detach", "-q", str(tree), "HEAD")
    (tree / VERBATIM).unlink()
    batch.reset(tree, git(root, "rev-parse", "HEAD").strip())
    assert (tree / VERBATIM).read_bytes() == FILES[VERBATIM].encode("utf-8")


# --- answers 2 and 4: the merge check's own tree and folder ---------------------------------------


def fake_governance(seen: dict):
    def run(root, tree, home, body, base, wait):
        seen["tree"] = tree
        seen["bytes"] = (tree / VERBATIM).read_bytes()
        return None

    return run


def test_the_merge_checks_tree_holds_the_committed_bytes(tmp_path, monkeypatch):
    """REQ-046: brief #1540 answers 2 and 4 (in_worktree in a CRLF person's clone, under a folder
    with a space in its name, the folder made in the long temporary folder)."""
    root = crlf(kit_repo(tmp_path / "My Project"))
    long_folder = tmp_path / "Long Temp"
    long_folder.mkdir()
    monkeypatch.setattr(merge_cleared, "long_temp_dir", lambda: long_folder)
    seen: dict = {}
    monkeypatch.setattr(merge_cleared, "run_governance", fake_governance(seen))
    commit = git(root, "rev-parse", "HEAD").strip()
    assert merge_cleared.in_worktree(root, commit, commit, 1.0, "body\n", "agk-x-") is None
    assert seen["bytes"] == FILES[VERBATIM].encode("utf-8")
    assert seen["tree"].parent.parent == long_folder
    assert list(long_folder.iterdir()) == [], "the folder is removed"


def test_the_merge_checks_runs_get_the_long_temporary_folder_on_windows(tmp_path, monkeypatch):
    """REQ-046: brief #1540 answer 4 and edge case 9 (an 8.3 short path: only the long name)."""
    short, long_name = r"C:\Users\EXAMPL~1\AppData\Local\Temp", r"C:\Users\example\AppData\Local\Temp"
    monkeypatch.setattr(merge_cleared, "on_windows", lambda: True)
    monkeypatch.setattr(common, "on_windows", lambda: True)
    monkeypatch.setattr(common, "long_path_name", lambda path: long_name if path == short else None)
    monkeypatch.setattr(common.tempfile, "gettempdir", lambda: short)
    for name in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.setenv(name, short)
    env = merge_cleared.run_env(tmp_path / "home", {"AGK_KIT_TESTS": "1"})
    assert {env[n] for n in ("TEMP", "TMP", "TMPDIR")} == {long_name}
    assert "EXAMPL~1" not in json.dumps(env)


def test_off_windows_the_runs_environment_is_unchanged(tmp_path, monkeypatch):
    """REQ-046: brief #1540 answer 4 (nothing changes on Linux and macOS)."""
    monkeypatch.setattr(merge_cleared, "on_windows", lambda: False)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    env = merge_cleared.run_env(tmp_path / "home", {})
    assert set(env) == {"PATH", "HOME"}


# --- the end-to-end check: a CRLF person's guarded merge with the pre-merge tests -------------------


BYTES_TEST = '''
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_checkout_holds_the_committed_bytes():
    assert b"\\r\\n" not in (ROOT / "rules.md").read_bytes()
'''


def test_a_crlf_persons_guarded_merge_runs_the_pre_merge_tests_on_committed_bytes(tmp_path):
    """REQ-046: brief #1540 Measured line and edge case 9 (the owner's #1533 case, simulated: a
    pre-merge test that compares bytes, a person with `core.autocrlf=true`, a folder with a
    space; held before the change, merged after)."""
    import test_merge_cleared_pre_tests as pre

    base = tmp_path / "My Project"
    base.mkdir()
    pre_files = {**pre.BASE_FILES, "tests/kit/test_bytes.py": BYTES_TEST}
    setting = '[testing]\npre_merge_tests = ["tests/kit/test_bytes.py"]\n'
    root = pre.repo(base, pre.toml(pre.ON) + setting)
    url = git(root, "remote", "get-url", "origin").strip()
    bare = Path(unquote(url.removeprefix("file://")))
    x = pre.commit_in(bare, pre_files, pre.MERGE, "x")
    main = pre.commit_in(bare, pre.WIDER, x, "main")
    head = pre.commit_in(bare, {"budget.txt": "6\n"}, x, "head")
    git(bare, "update-ref", "refs/heads/main", main)
    git(bare, "update-ref", "refs/pull/7/head", head)
    git(root, "config", "core.autocrlf", "true")
    pull = {**pre.world()["pull"], "head": {"sha": head}}
    commits = [{"sha": head, "commit": {"message": "Example change\n"}}]
    bin_dir, log = pre.fake_gh(
        base, pull=pull, comments=[pre.cleared(head, extra="")], issues=[pre.AUTO_ISSUE],
        commits=commits,
    )  # fmt: skip
    proc = pre.run(root, bin_dir, "--pr", "7", "--sha", head)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert pre.one_line(proc).endswith(f"merged {pre.MERGE[:12]}")


# --- answer 3: hashes as committed --------------------------------------------------------------


def checkout_of(root: Path, where: Path, autocrlf: str) -> Path:
    """A clone of ROOT made with the person's `core.autocrlf` (true: a Windows checkout)."""
    git(root.parent, "-c", f"core.autocrlf={autocrlf}", "clone", "-q", str(root), str(where))
    git(where, "config", "core.autocrlf", autocrlf)
    return where


def test_a_hash_taken_on_a_crlf_checkout_equals_the_committed_hash(tmp_path):
    """REQ-046: brief #1540 answer 3 and edge case 9 (a hash computed on Windows checks on Linux)."""
    root = kit_repo(tmp_path / "kit")
    windows = checkout_of(root, tmp_path / "windows", "true")
    linux = checkout_of(root, tmp_path / "linux", "false")
    assert b"\r\n" in (windows / VERBATIM).read_bytes()
    committed = kit_hashes.snapshot_commit(root, kit_hashes.Blobs(root), "HEAD")
    assert kit_hashes.snapshot_worktree(windows) == committed
    assert kit_hashes.snapshot_worktree(linux) == committed
    assert committed[1]["verbatim"][VERBATIM] == sha(FILES[VERBATIM].encode("utf-8"))


def test_a_file_committed_with_crlf_keeps_its_own_hash(tmp_path):
    """REQ-046: brief #1540 edge case 9 (`committed_bytes` leaves a CRLF blob as it is)."""
    files = {**FILES, VERBATIM: "a = 1\r\nb = 2\r\n"}
    root = kit_repo(tmp_path / "kit", files)
    windows = checkout_of(root, tmp_path / "windows", "true")
    _, snap = kit_hashes.snapshot_worktree(windows)
    assert snap["verbatim"][VERBATIM] == sha(b"a = 1\r\nb = 2\r\n")


def test_a_real_edit_on_a_crlf_checkout_still_changes_the_hash(tmp_path):
    """REQ-046: brief #1540 answer 3 (only a change of line ends alone reads as committed)."""
    root = kit_repo(tmp_path / "kit")
    windows = checkout_of(root, tmp_path / "windows", "true")
    (windows / VERBATIM).write_bytes(b"[signals]\r\nname = \"other\"\r\n")
    _, snap = kit_hashes.snapshot_worktree(windows)
    assert snap["verbatim"][VERBATIM] == sha(b"[signals]\r\nname = \"other\"\r\n")


def test_a_mixed_team_merges_a_verbatim_change_with_no_line_end_change(tmp_path):
    """REQ-046: brief #1540 edge case 9 (a Windows clone commits, a Linux clone merges: the blob
    is LF, and both clones hash it alike)."""
    root = kit_repo(tmp_path / "kit")
    git(root, "config", "receive.denyCurrentBranch", "ignore")
    windows = checkout_of(root, tmp_path / "windows", "true")
    linux = checkout_of(root, tmp_path / "linux", "false")
    (windows / VERBATIM).write_bytes(b"[signals]\r\nname = \"changed\"\r\n")
    git(windows, "commit", "-q", "-am", "change on Windows")
    git(windows, "push", "-q", "origin", "HEAD:refs/heads/windows")
    git(linux, "fetch", "-q", "origin", "windows")
    git(linux, "merge", "-q", "--ff-only", "FETCH_HEAD")
    blob = git(linux, "cat-file", "-p", f"HEAD:{VERBATIM}").encode("utf-8")
    assert blob == b"[signals]\nname = \"changed\"\n"
    assert kit_hashes.snapshot_worktree(windows) == kit_hashes.snapshot_worktree(linux)


# --- answer 3: the plan's re-render -------------------------------------------------------------


PLAN_FILE = f"{plan_intake.PLAN}/scope.md"
PLAN_TEXT = "# Scope\n\nOne line.\nTwo lines.\n"


def rendered(tmp_path: Path, autocrlf: str) -> tuple[Path, dict]:
    """A project whose plan file was rendered (LF, as committed) and then cloned with the
    person's `core.autocrlf`: (the clone, the digest list)."""
    root = kit_repo(tmp_path / "project", {PLAN_FILE: PLAN_TEXT})
    clone = checkout_of(root, tmp_path / f"clone-{autocrlf}", autocrlf)
    listed = {"files": {PLAN_FILE: sha(PLAN_TEXT.encode("utf-8"))}, "specs": {}}
    return clone, listed


def test_a_rendered_plan_file_checked_out_crlf_is_not_kept_as_edited(tmp_path):
    """REQ-046: brief #1540 answer 3 and edge case 9 (a teammate's CRLF checkout)."""
    clone, listed = rendered(tmp_path, "true")
    assert b"\r\n" in (clone / PLAN_FILE).read_bytes()
    write, kept = plan_intake.again_plan(clone, {PLAN_FILE: PLAN_TEXT}, listed)
    assert kept == []
    assert write == [(PLAN_FILE, PLAN_TEXT, "unchanged")]
    write, kept = plan_intake.again_plan(clone, {PLAN_FILE: PLAN_TEXT + "New.\n"}, listed)
    assert kept == [] and write == [(PLAN_FILE, PLAN_TEXT + "New.\n", "rewrote")]


def test_a_plan_file_really_edited_is_still_kept(tmp_path):
    """REQ-046: brief #1540 edge case 9 (a real edit is kept, on either checkout)."""
    for autocrlf in ("true", "false"):
        clone, listed = rendered(tmp_path / autocrlf, autocrlf)
        (clone / PLAN_FILE).write_bytes(b"# Scope\r\n\r\nMy own words.\r\n")
        _, kept = plan_intake.again_plan(clone, {PLAN_FILE: PLAN_TEXT}, listed)
        assert kept == [f"kept {PLAN_FILE}: edited since the last render"]


def test_the_render_writes_lf_on_every_system():
    """REQ-046: brief #1540 answer 3 (the digest recorded at render is of LF bytes)."""
    text = (SCRIPTS / "plan_intake.py").read_text(encoding="utf-8")
    body = text.split("\ndef cmd_render(", 1)[1].split("\ndef ", 1)[0]
    assert 'path.write_text(text, encoding="utf-8", newline="\\n")' in body


# --- Q-1540-4: the prototype runtime's hash --------------------------------------------------------


def test_the_runtime_hash_reads_the_committed_bytes(tmp_path, monkeypatch):
    """REQ-046: brief #1540 Q-4 (a tracked runtime whose blob is LF checks on a CRLF checkout;
    an untracked CRLF runtime still fails rule 5)."""
    runtime = b"// example runtime\nexport const one = 1;\n"
    folder_rel = "docs/design/prototype/v1"
    root = kit_repo(tmp_path / "project", {f"{folder_rel}/{design_prototype_check.RUNTIME}": ""})
    (root / folder_rel / design_prototype_check.RUNTIME).write_bytes(runtime)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "runtime")
    clone = checkout_of(root, tmp_path / "windows", "true")
    monkeypatch.setattr(design_prototype_check, "RUNTIME_HASHES", (sha(runtime),))
    folder = clone / folder_rel
    assert b"\r\n" in (folder / design_prototype_check.RUNTIME).read_bytes()
    rule5 = [p for p in design_prototype_check.folder_problems(folder, folder_rel, {})
             if p.startswith("rule 5")]  # fmt: skip
    assert rule5 == []
    loose = tmp_path / "loose" / "v1"
    loose.mkdir(parents=True)
    (loose / design_prototype_check.RUNTIME).write_bytes(runtime.replace(b"\n", b"\r\n"))
    rule5 = [p for p in design_prototype_check.folder_problems(loose, folder_rel, {})
             if p.startswith("rule 5")]  # fmt: skip
    assert len(rule5) == 1


# --- answer 5: names compare with `/` ------------------------------------------------------------


TEST_FOLDERS = (KIT / "tests" / "kit", KIT / "tests" / "kit_dev")


def str_of_relative_to(folders=TEST_FOLDERS) -> list[str]:
    """`file:line` of each `str(<x>.relative_to(<y>))` under FOLDERS: on Windows it gives `\\`."""
    found: list[str] = []
    for folder in folders:
        for path in sorted(folder.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "str"
                    and len(node.args) == 1
                    and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Attribute)
                    and node.args[0].func.attr == "relative_to"
                ):
                    found.append(f"{path.parent.name}/{path.name}:{node.lineno}")
    return found


def test_the_kits_tests_build_names_with_slashes():
    """REQ-046: brief #1540 answer 5 (red on main's eight helper lines)."""
    assert str_of_relative_to() == []


def test_the_name_test_finds_the_old_helper(tmp_path):
    """REQ-046: brief #1540 answer 5 (the test of the test)."""
    (tmp_path / "test_x.py").write_text(
        "a = str(p.relative_to(ROOT))\nb = p.relative_to(ROOT).as_posix()\n", encoding="utf-8"
    )
    assert str_of_relative_to((tmp_path,)) == [f"{tmp_path.name}/test_x.py:1"]


def test_windows_names_match_the_kits_globs_only_with_slashes():
    """REQ-046: brief #1540 edge case 9 (backslash names: the cause of failures 1 and 2)."""
    root = PureWindowsPath(r"C:\AI Projects\agk")
    script = root / "scripts" / "agk" / "merge_cleared.py"
    pattern = "scripts/agk/*.py"
    rel = script.relative_to(root)
    assert str(rel) == r"scripts\agk\merge_cleared.py"
    assert not impact.matches(str(rel), pattern)
    posix = rel.as_posix()
    assert posix == str(PurePosixPath("scripts/agk/merge_cleared.py"))
    assert impact.matches(posix, pattern)
