"""Tests of `front_door.py detect` (SPEC-0057 rules 2 to 4, 6 to 8, 10 and 11, build (b)).

Small git repositories in `tmp_path`, invented data only (`example.com`), no network, no model, and
no test runs a tool of a fixture.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
SCRIPT = SCRIPTS / "front_door.py"
sys.path.insert(0, str(SCRIPTS))

import front_door  # noqa: E402

FIRST = "detect: proposal only; a person confirms it in discovery"
NO_KIND = "work type: default (proposed; no signal of a work type)"
TAIL = ["not detectable from files: cloud-migration", "not detectable from files: pilot"]
REACT = '{"dependencies": {"react-dom": "1.0.0"}}\n'
FLUTTER = "dependencies:\n  flutter:\n    sdk: flutter\n"
GIT = ["git", "-c", "user.name=Ada", "-c", "user.email=ada@example.com", "-c", "commit.gpgsign=false"]


def git(root: Path, *args: str) -> None:
    subprocess.run([*GIT, *args], cwd=root, check=True, capture_output=True)  # nosec B603


def repo(root: Path, files: dict[str, str | bytes] | None = None, commit: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    for rel, body in (files or {}).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
    if commit:
        (root / "README.md").write_text("invented\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "invented")
    return root


def run(root: Path, *extra: str, script: Path = SCRIPT):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(script), "detect", "--root", str(root), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def lines(root: Path) -> list[str]:
    proc = run(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.splitlines()


def snapshot(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def status(root: Path) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True
    )
    return proc.stdout


def test_one_signal_gives_its_work_type_and_stack_and_writes_nothing(tmp_path):
    """REQ-064 AC1: rules 2, 3 and 7."""
    root = repo(tmp_path / "r", {"app/package.json": REACT, "app/yarn.lock": "# lock\n"})
    before = snapshot(root)
    first, second = run(root), run(root)
    assert first.returncode == 0
    assert first.stdout == second.stdout
    assert first.stdout.splitlines() == [
        FIRST,
        'work type: web-app (proposed) file "app/package.json" signal react-dom',
        'stack: node (proposed) folder "app" file "app/package.json" lock "app/yarn.lock"',
        "tests: no signal",
        *TAIL,
    ]
    assert snapshot(root) == before


def test_a_manifest_with_no_lockfile_says_lock_none(tmp_path):
    """REQ-064 AC1: rule 3."""
    root = repo(tmp_path / "r", {"go.mod": "module example.com/a\n"})
    assert 'stack: go-modules (proposed) folder "." file "go.mod" lock none' in lines(root)


def test_json_is_the_same_facts_with_sorted_keys(tmp_path):
    """REQ-064 AC1: rule 3."""
    root = repo(tmp_path / "r", {"package.json": REACT, "yarn.lock": "# lock\n"})
    out = run(root, "--json").stdout
    data = json.loads(out)
    assert out == json.dumps(data, sort_keys=True, indent=1) + "\n"
    assert data["work_type"]["state"] == "proposed"
    assert data["work_type"]["candidates"] == [
        {"file": "package.json", "name": "web-app", "signal": "react-dom"}
    ]
    assert data["stack"]["rows"] == [
        {"file": "package.json", "folder": ".", "lock": "yarn.lock", "name": "node"}
    ]
    assert data["not_detectable"] == ["cloud-migration", "pilot"]
    assert data["notes"] == []


def test_two_work_types_are_mixed_in_path_order_and_none_wins(tmp_path):
    """REQ-064 AC2: rule 4, `Q-S0057-10`."""
    root = repo(tmp_path / "r", {"b/pubspec.yaml": FLUTTER, "a/package.json": REACT})
    out = lines(root)
    assert out[1:4] == [
        "work type: mixed (2 candidates)",
        'candidate: web-app file "a/package.json" signal react-dom',
        'candidate: mobile file "b/pubspec.yaml" signal flutter',
    ]
    assert not [line for line in out if line.startswith("work type: web-app")]
    assert "stack: mixed (2 stacks)" in out
    assert out.index("stack: mixed (2 stacks)") < out.index(
        'stack: dart-pub (proposed) folder "b" file "b/pubspec.yaml" lock none'
    )


@pytest.mark.parametrize("own_playbook", [False, True])
def test_nothing_gives_default_and_pilot_is_never_proposed(tmp_path, own_playbook):
    """REQ-064 AC2: rule 4, `Q-S0057-6`."""
    files = {"config/playbooks/pilot.toml": "format = 1\n"} if own_playbook else {}
    out = lines(repo(tmp_path / "r", files))
    assert out == [FIRST, NO_KIND, "stack: no signal", "tests: no signal", *TAIL]
    assert not [line for line in out if "pilot" in line and line not in TAIL]


def test_a_head_with_no_commit_says_so(tmp_path):
    """REQ-064 AC2: rule 4."""
    root = repo(tmp_path / "r", {"package.json": REACT}, commit=False)
    assert lines(root) == [
        FIRST,
        NO_KIND,
        "stack: no signal",
        "tests: no signal",
        *TAIL,
        "note: no commit at head",
    ]


def test_an_untracked_or_uncommitted_manifest_gives_no_signal(tmp_path):
    """REQ-064 AC3: rule 7, `Q-S0057-12`."""
    root = repo(tmp_path / "r", {"pyproject.toml": "[project]\n"})
    (root / "package.json").write_text(REACT, encoding="utf-8")
    (root / "pyproject.toml").write_text('dependencies = ["django"]\n', encoding="utf-8")
    out = lines(root)
    assert NO_KIND in out
    assert not [line for line in out if '"package.json"' in line]


def test_a_symlink_out_of_the_tree_is_not_followed(tmp_path):
    """REQ-064 AC3: rule 7."""
    outside = tmp_path / "outside.json"
    outside.write_text(REACT, encoding="utf-8")
    root = repo(tmp_path / "r")
    (root / "package.json").symlink_to(outside)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link")
    out = lines(root)
    assert NO_KIND in out and "stack: no signal" in out
    assert 'note: file "package.json" not read (symlink)' in out


def test_a_submodule_gives_no_signal(tmp_path):
    """REQ-064 AC3: rule 7."""
    root = repo(tmp_path / "r")
    git(root, "update-index", "--add", "--cacheinfo", f"160000,{'a' * 40},package.json")
    git(root, "commit", "-q", "-m", "module")
    out = lines(root)
    assert "stack: no signal" in out
    assert 'note: file "package.json" not read (submodule)' in out


def test_a_binary_file_gives_no_signal(tmp_path):
    """REQ-064 AC3: rule 7."""
    out = lines(repo(tmp_path / "r", {"package.json": b"\0" + REACT.encode()}))
    assert NO_KIND in out and "stack: no signal" in out
    assert 'note: file "package.json" not read (binary)' in out


def test_a_file_over_1_mb_is_not_read_and_exactly_1_mb_is(tmp_path):
    """REQ-064 AC3: rule 7."""
    limit = 1024 * 1024
    word = "django\n"
    over = lines(repo(tmp_path / "o", {"requirements.txt": word + "#" * limit}))
    assert NO_KIND in over and "stack: no signal" in over
    assert 'note: file "requirements.txt" not read (over 1 MB)' in over
    exact = lines(repo(tmp_path / "e", {"requirements.txt": word + "#" * (limit - len(word))}))
    assert 'work type: web-app (proposed) file "requirements.txt" signal django' in exact


def test_the_201st_file_gives_the_note(tmp_path):
    """REQ-064 AC3: rule 7."""
    files = {f"p{n:03d}/go.mod": "module example.com/a\n" for n in range(201)}
    out = lines(repo(tmp_path / "r", files))
    assert len([line for line in out if line.startswith("stack: go-modules")]) == 200
    assert not [line for line in out if '"p200/go.mod"' in line]
    assert "note: 200 files read, the proposal is partial" in out


def test_no_note_at_exactly_200_files(tmp_path):
    """REQ-064 AC3: rule 7."""
    files = {f"p{n:03d}/go.mod": "module example.com/a\n" for n in range(200)}
    assert not [line for line in lines(repo(tmp_path / "r", files)) if line.startswith("note:")]


def test_setup_py_is_never_run(tmp_path):
    """REQ-064 AC3: rule 7."""
    code = "from pathlib import Path\nPath('SENTINEL').write_text('run')\n"
    root = repo(tmp_path / "r", {"setup.py": code, "conftest.py": code})
    out = lines(root)
    assert 'stack: python-pip (proposed) folder "." file "setup.py" lock none' in out
    assert not list(tmp_path.rglob("SENTINEL"))


def test_only_git_with_the_allowed_commands_and_no_socket(tmp_path, monkeypatch, capsys):
    """REQ-064 AC3: rule 7."""
    root = repo(tmp_path / "r", {"package.json": REACT})
    seen, env = [], []
    real = subprocess.run

    def record(argv, **kw):
        seen.append(list(argv))
        env.append(kw.get("env") or {})
        return real(argv, **kw)

    def no_socket(*_a, **_k):
        raise AssertionError("network")

    monkeypatch.setattr(front_door.subprocess, "run", record)
    monkeypatch.setattr(socket, "socket", no_socket)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "elsewhere"))
    assert front_door.main(["detect", "--root", str(root)]) == 0
    capsys.readouterr()
    assert seen
    for argv in seen:
        assert argv[:2] == ["git", "--no-optional-locks"]
        assert argv[2] in ("ls-tree", "cat-file")
    assert ["git", "--no-optional-locks", "ls-tree", "-r", "-z", "HEAD"] in seen
    assert all("GIT_DIR" not in item and item.get("GIT_NO_LAZY_FETCH") == "1" for item in env)


def test_a_work_type_is_a_whole_word_never_a_part_of_one(tmp_path):
    """REQ-064 AC1: rule 6."""
    body = '{"dependencies": {"vue-router": "1", "@vue/cli": "1", "my-vue": "1"}}\n'
    assert NO_KIND in lines(repo(tmp_path / "r", {"package.json": body}))


def test_an_ignored_folder_gives_no_signal(tmp_path):
    """REQ-064 AC1: rule 5's `ignore`."""
    out = lines(repo(tmp_path / "r", {"vendor/x/package.json": REACT}))
    assert NO_KIND in out and "stack: no signal" in out


def test_the_table_is_the_kits_and_never_the_repositorys(tmp_path):
    """REQ-064 AC3: rule 7's brief answer 3, `Q-S0057-2`."""
    own = '[[stack]]\nname = "planted"\nmanifests = ["README.md"]\nlocks = []\n'
    out = lines(repo(tmp_path / "r", {"config/stack-signals.toml": own}))
    assert "stack: no signal" in out


def test_a_lockfile_never_suggests_a_work_type(tmp_path, capsys):
    """REQ-064 AC1: rule 6, `Q-S0057-3`, with a table that names a lockfile in a row."""
    root = repo(tmp_path / "r", {"package.json": "{}\n", "yarn.lock": "react-dom\n"})
    kit = tmp_path / "kit"
    (kit / "config").mkdir(parents=True)
    text = (KIT_ROOT / front_door.SIGNALS).read_text(encoding="utf-8")
    row = '\n[[work_type]]\nname = "web-app"\nsignal = "s"\nfile = "yarn.lock"\ncontains = "react-dom"\n'
    (kit / front_door.SIGNALS).write_text(text + row, encoding="utf-8")
    assert front_door.detect(root, kit, as_json=False) == 0
    assert NO_KIND in capsys.readouterr().out.splitlines()


def test_a_broken_table_is_refused_naming_the_setting(tmp_path, capsys):
    """REQ-064 AC8: rule 11."""
    (tmp_path / "config").mkdir()
    (tmp_path / front_door.SIGNALS).write_text("no_signal = [", encoding="utf-8")
    with pytest.raises(front_door.Refusal) as refused:
        front_door.detect(repo(tmp_path / "r"), tmp_path, as_json=False)
    assert refused.value.problems == [f"detect: {front_door.SIGNALS} cannot be read"]
    assert capsys.readouterr().out == ""


def test_the_tests_line_comes_from_detect_tests(tmp_path):
    """REQ-064 AC5: rule 8."""
    out = lines(repo(tmp_path / "r", {"tests/test_a.py": "x = 1\n", "tests/test_b.py": "x = 2\n"}))
    assert 'tests: "tests" patterns test_*.py (from adopt.detect_tests, work tree)' in out


def test_a_patched_detect_tests_shows_the_call(tmp_path, monkeypatch, capsys):
    """REQ-064 AC5: rule 8."""
    root = repo(tmp_path / "r", {"zone/spec_x.check": "x\n"})
    calls = []

    class Fake:
        @staticmethod
        def detect_tests(where):
            calls.append(Path(where))
            return ["zone"], ["spec_*.check"]

    monkeypatch.setitem(sys.modules, "adopt", Fake)
    assert front_door.main(["detect", "--root", str(root)]) == 0
    assert calls == [root]
    want = 'tests: "zone" patterns spec_*.check (from adopt.detect_tests, work tree)'
    assert want in capsys.readouterr().out.splitlines()


def test_a_test_file_only_in_the_work_tree_is_no_signal(tmp_path):
    """REQ-064 AC5: rule 8: an answer counts only for a path of the head tree."""
    root = repo(tmp_path / "r")
    (root / "tests").mkdir()
    (root / "tests/test_a.py").write_text("x = 1\n", encoding="utf-8")
    assert "tests: no signal" in lines(root)


def test_an_import_failure_says_not_read(tmp_path):
    """REQ-064 AC5: rule 8, `Q-S0057-9`: an installed copy has no adopt.py."""
    (tmp_path / "kit/scripts/agk").mkdir(parents=True)
    for name in ("front_door.py", "guard.py", "playbook_format.py"):
        shutil.copy(SCRIPTS / name, tmp_path / "kit/scripts/agk" / name)
    (tmp_path / "kit/config").mkdir()
    shutil.copy(KIT_ROOT / front_door.SIGNALS, tmp_path / "kit" / front_door.SIGNALS)
    root = repo(tmp_path / "r", {"tests/test_a.py": "x = 1\n"})
    out = run(root, script=tmp_path / "kit/scripts/agk/front_door.py").stdout.splitlines()
    assert "tests: not read (adopt.detect_tests cannot be loaded)" in out


def test_front_door_holds_no_test_file_pattern():
    """REQ-064 AC5: rule 8."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "*_test.py" not in text and "test_*.py" not in text


def test_other_commands_do_not_load_adopt():
    """REQ-064 AC5: rule 8: a load failure leaves every other command as it is."""
    code = (
        f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import front_door;"
        " print('adopt' in sys.modules)"
    )
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
    assert proc.stdout.strip() == "False"


@pytest.mark.parametrize("cloned", [False, True])
def test_a_repository_with_no_agk_and_a_clone_stay_unchanged(tmp_path, cloned):
    """REQ-064 AC7: rule 10."""
    root = repo(tmp_path / "r", {"package.json": REACT, "tests/test_a.py": "x = 1\n"})
    if cloned:
        subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "clone", "-q", str(root), str(tmp_path / "c")], check=True, capture_output=True
        )
        root = tmp_path / "c"
    before = snapshot(root)
    assert run(root).returncode == 0
    assert status(root) == ""
    assert snapshot(root) == before
    assert not (root / "agk.toml").exists() and not (root / "scripts").exists()


def test_a_credential_a_dependency_and_a_newline_path_stay_out(tmp_path):
    """REQ-064 AC8: rule 11."""
    plant = "https://user:tok-invented@example.com/simple"
    body = f"--index-url {plant}\nzanzibar-dependency\ndjango\n"
    root = repo(tmp_path / "r", {"a\nFAIL/requirements.txt": body})
    proc = run(root)
    assert "tok-invented" not in proc.stdout and "zanzibar" not in proc.stdout
    assert not [line for line in proc.stdout.splitlines() if line.startswith("FAIL")]
    want = 'work type: web-app (proposed) file "a\\nFAIL/requirements.txt" signal django'
    assert want in proc.stdout.splitlines()


def test_a_folder_that_is_not_a_repository_is_refused_without_its_path(tmp_path):
    """REQ-064 AC8: rule 11."""
    folder = tmp_path / "plain"
    folder.mkdir()
    for root in (folder, tmp_path / "absent"):
        proc = run(root)
        assert proc.returncode == 1
        assert proc.stdout == "FAIL front-door: detect: --root is not a git repository\n"
        assert str(tmp_path) not in proc.stdout + proc.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ["detect", "--apply"],
        ["detect", "--work-type", "web-app"],
        ["detect", "stray"],
        ["detect", "--date", "2026-11-09"],
        ["detect", "--json", "--json"],
        ["status", "--date", "2026-11-09", "--json"],
    ],
)
def test_usage_is_exit_2(argv):
    """REQ-064 AC8: rule 11, rule 2: no option that decides."""
    assert front_door.main(argv) == 2
