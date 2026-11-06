"""Each test run writes to its own dated folder; a failed run's folder is kept (brief #613).

With `[testing] results_dir` set, `prepush.py` sets `AGK_RUN_DIR` for the project's test command
to a new folder `<results root>/<UTC time>-<head sha12>-<kind>` (proof does not: `Q-613-1`); the
results root is that setting, and it git-ignores itself. Without the key prepush does exactly what
the default branch does: no variable and no folder (SPEC-0044 rule 1, the answer to `Q-613-2`).
After the run a passed run's folder is removed unless `[testing] keep_passed = true`, a failed
one is kept, and at most `[testing] keep_runs` folders (20) stay, oldest removed first, never a
failed run's folder of the last 7 days. REQ-051.

The clock is injected; the projects are invented; nothing reaches the network.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import proof as proof_module
import pytest
from common import CheckError
from impact import run_settings
from test_prepush import MK_OK, TOML, path_with, scanner
from test_proof import start

NOW = datetime(2026, 11, 6, 9, 30, 0, tzinfo=UTC)
HEAD = "0123456789abcdef0123456789abcdef01234567"
NAME = "20261106T093000Z-0123456789ab-prepush"
WRITES = 'echo evidence > "$AGK_RUN_DIR/trace.txt"'


def clock(when: datetime = NOW):
    return lambda: when


def folder_name(when: datetime, kind: str = "prepush", sha: str = HEAD) -> str:
    return f"{when.strftime('%Y%m%dT%H%M%SZ')}-{sha[:12]}-{kind}"


def old_run(results: Path, when: datetime, result: str | None, kind: str = "prepush") -> Path:
    path = results / folder_name(when, kind)
    path.mkdir(parents=True)
    if result is not None:
        (path / proof_module.RUN_MARK).write_text(result + "\n", encoding="utf-8")
    return path


ON = 'results_dir = ".agk-runs"\n'  # the one line that turns the run folders on


def settings(tmp_path: Path, testing: str = ON) -> Path:
    (tmp_path / "agk.toml").write_text(
        'default_branch = "main"\n' + (f"[testing]\n{testing}" if testing else ""),
        encoding="utf-8",
    )
    return tmp_path


def test_the_run_gets_its_own_dated_folder_in_agk_run_dir(tmp_path, monkeypatch):
    """REQ-051: brief #613 answer 1 (the folder's name, AGK_RUN_DIR during the run only)."""
    root = settings(tmp_path)
    monkeypatch.setenv("AGK_RUN_DIR", "/elsewhere")
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        assert run.path == root.resolve() / ".agk-runs" / NAME
        assert os.environ["AGK_RUN_DIR"] == str(run.path)
        assert run.path.is_dir()
        run.passed = False
    assert os.environ["AGK_RUN_DIR"] == "/elsewhere"
    assert (root / ".agk-runs" / ".gitignore").read_text(encoding="utf-8") == "*\n"


def test_a_second_run_in_the_same_second_never_shares_a_folder(tmp_path):
    """REQ-051: brief #613 answer 1 (a rerun never overwrites an earlier run's files)."""
    root = settings(tmp_path)
    paths = []
    for _ in range(2):
        with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
            paths.append(run.path)
    assert paths[0] != paths[1]
    assert paths[1].name == NAME + "-2"


def test_the_results_root_is_the_setting(tmp_path):
    """REQ-051: brief #613 answer 1 (`[testing] results_dir`)."""
    root = settings(tmp_path, 'results_dir = "build/runs"\n')
    with proof_module.run_folder(root, HEAD, "proof", now=clock()) as run:
        assert run.path == root.resolve() / "build" / "runs" / folder_name(NOW, "proof")


def test_a_passed_run_is_removed_and_a_failed_run_is_kept(tmp_path):
    """REQ-051: brief #613 answer 2 (passed removed, failed kept with its mark)."""
    root = settings(tmp_path)
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        run.passed = True
    assert not run.path.exists() and run.kept is False
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        (run.path / "shot.png").write_text("x", encoding="utf-8")
    assert run.kept is True
    assert (run.path / "shot.png").is_file()
    assert (run.path / proof_module.RUN_MARK).read_text(encoding="utf-8") == "failed\n"


def test_keep_passed_keeps_a_passed_run(tmp_path):
    """REQ-051: brief #613 answer 2 (`[testing] keep_passed = true`)."""
    root = settings(tmp_path, ON + "keep_passed = true\n")
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        run.passed = True
    assert run.kept is True
    assert (run.path / proof_module.RUN_MARK).read_text(encoding="utf-8") == "passed\n"


def test_at_most_keep_runs_folders_stay_oldest_first(tmp_path):
    """REQ-051: brief #613 answer 2 (keep_runs, oldest removed first)."""
    root = settings(tmp_path, ON + "keep_passed = true\nkeep_runs = 3\n")
    results = root / ".agk-runs"
    olds = [old_run(results, NOW - timedelta(hours=h), "passed") for h in (5, 4, 3)]
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        run.passed = True
    assert not olds[0].exists()
    assert olds[1].exists() and olds[2].exists() and run.path.exists()


def test_a_recent_failed_run_is_never_removed(tmp_path):
    """REQ-051: brief #613 answer 2 (never a failed run's folder of the last 7 days)."""
    root = settings(tmp_path, ON + "keep_runs = 1\n")
    results = root / ".agk-runs"
    recent = old_run(results, NOW - timedelta(days=6, hours=23), "failed")
    unmarked = old_run(results, NOW - timedelta(days=2), None)  # a run still going, or killed
    stale = old_run(results, NOW - timedelta(days=8), "failed")
    passed = old_run(results, NOW - timedelta(days=1), "passed")
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        pass  # failed
    assert recent.exists() and unmarked.exists() and run.path.exists()
    assert not stale.exists() and not passed.exists()


def test_only_the_kits_run_folders_are_ever_removed(tmp_path):
    """REQ-051: brief #613 answer 2 (other files under the results root are left alone)."""
    root = settings(tmp_path, ON + "keep_passed = true\nkeep_runs = 1\n")
    results = root / ".agk-runs"
    mine = results / "notes"
    mine.mkdir(parents=True)
    (results / "README.txt").write_text("a person's file\n", encoding="utf-8")
    old_run(results, NOW - timedelta(days=30), "passed")
    with proof_module.run_folder(root, HEAD, "prepush", now=clock()) as run:
        run.passed = True
    assert mine.is_dir() and (results / "README.txt").is_file()
    runs = [p.name for p in results.iterdir() if proof_module.RUN_NAME.fullmatch(p.name)]
    assert runs == [run.path.name]


def test_the_defaults_without_a_testing_table(tmp_path):
    """REQ-051: brief #613 answers 1 and 2, `Q-613-2` (no results root unless it is set;
    keep_passed false, keep_runs 20)."""
    assert run_settings(settings(tmp_path, "")) == (None, False, 20)
    assert run_settings(settings(tmp_path, 'profile = "balanced"\n')) == (None, False, 20)
    assert run_settings(settings(tmp_path, 'results_dir = "out/"\n')) == ("out", False, 20)


def test_run_folder_refuses_without_the_setting(tmp_path):
    """REQ-051: `Q-613-2` (no folder is made without `[testing] results_dir`)."""
    root = settings(tmp_path, "")
    with pytest.raises(CheckError) as caught:
        with proof_module.run_folder(root, HEAD, "prepush", now=clock()):
            pass
    assert "(setting: testing.results_dir)" in str(caught.value)
    assert list(root.iterdir()) == [root / "agk.toml"]


@pytest.mark.parametrize(
    ("line", "setting"),
    [
        ('results_dir = "../out"\n', "testing.results_dir"),
        ('results_dir = "/tmp/out"\n', "testing.results_dir"),
        ("results_dir = 3\n", "testing.results_dir"),
        ('keep_passed = "yes"\n', "testing.keep_passed"),
        ("keep_runs = 0\n", "testing.keep_runs"),
        ("keep_runs = true\n", "testing.keep_runs"),
        ('results_dir = "."\n', "testing.results_dir"),
        ('results_dir = "a/./b"\n', "testing.results_dir"),
    ],
)
def test_a_bad_setting_is_refused_naming_the_setting(tmp_path, line, setting):
    """REQ-051: brief #613 answers 1 and 2 (a malformed key names the setting, never the value)."""
    with pytest.raises(CheckError) as caught:
        run_settings(settings(tmp_path, ON + line if "results_dir" not in line else line))
    assert f"(setting: {setting})" in str(caught.value)


def prepush_project(repo, command: str, testing: str = "[testing]\n" + ON) -> None:
    toml = TOML.replace("echo RAN_PROJECT_TESTS", command)
    files = {"agk.toml": toml + testing, "agk.mk": MK_OK, "src/code.txt": "base\n"}
    repo.commit(files, "base")
    repo.branch("feature")
    repo.commit({"src/code.txt": "change\n", "tests/test_new.py": "# new\n"}, "change")


def runs_of(root: Path) -> list[Path]:
    results = root / ".agk-runs"
    if not results.is_dir():
        return []
    return sorted(p for p in results.iterdir() if proof_module.RUN_NAME.fullmatch(p.name))


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository, so the records keep its tree clean."""
    return tmp_path_factory.mktemp("outside")


def test_a_failed_prepush_keeps_its_files_and_a_rerun_keeps_both(repo, outside):
    """REQ-051: brief #613 answers 1 to 3 (the pilot's case: a rerun kept the first failure)."""
    prepush_project(repo, f"{WRITES}; exit 3")
    out = outside
    records = []
    for n in (1, 2):
        record = out / f"record{n}.json"
        proc = repo.run("prepush.py", "--record", str(record), PATH=path_with(scanner(out, 0)))
        assert proc.returncode == 1, proc.stdout + proc.stderr
        records.append(json.loads(record.read_text(encoding="utf-8")))
    kept = runs_of(repo.root)
    assert len(kept) == 2
    for path in kept:
        assert (path / "trace.txt").read_text(encoding="utf-8") == "evidence\n"
    named = [r["run_dir"] for r in records]
    assert [n["path"] for n in named] == [p.relative_to(repo.root).as_posix() for p in kept]
    assert all(n["kept"] is True for n in named)
    assert kept[0].name.endswith("-" + records[0]["head"][:12] + "-prepush")
    assert repo.git("status", "--porcelain") == ""  # the results root ignores itself


def test_a_passed_prepush_removes_its_folder(repo, outside):
    """REQ-051: brief #613 answers 2 and 3 (a passed run's folder is removed; the record says)."""
    prepush_project(repo, WRITES)
    record = outside / "record.json"
    proc = repo.run("prepush.py", "--record", str(record), PATH=path_with(scanner(outside, 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert runs_of(repo.root) == []
    data = json.loads(record.read_text(encoding="utf-8"))
    assert data["run_dir"]["kept"] is False
    assert data["run_dir"]["path"].startswith(".agk-runs/")


def test_a_prepush_with_a_testing_table_sets_the_folder_too(repo, tmp_path):
    """REQ-051: brief #613 answers 1 and 2 (the regression path, with keep_passed)."""
    prepush_project(repo, WRITES, '[testing]\nprofile = "thorough"\nkeep_passed = true\n' + ON)
    proc = repo.run("prepush.py", "--no-lock", PATH=path_with(scanner(tmp_path, 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    kept = runs_of(repo.root)
    assert len(kept) == 1 and (kept[0] / "trace.txt").is_file()


@pytest.mark.parametrize("testing", ["", '[testing]\nprofile = "thorough"\n'])
def test_without_results_dir_prepush_sets_no_variable_and_makes_no_folder(repo, outside, testing):
    """REQ-051: `Q-613-2`, SPEC-0044 rule 1 read strictly: with no new key prepush does what the
    default branch does today (no AGK_RUN_DIR, no folder, no `run_dir` in the record)."""
    prepush_project(repo, 'test -z "${AGK_RUN_DIR+set}"', testing)
    record = outside / "record.json"
    args = ["--record", str(record)] + (["--no-lock"] if testing else [])
    proc = repo.run("prepush.py", *args, PATH=path_with(scanner(outside, 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (repo.root / ".agk-runs").exists()
    assert "run_dir" not in json.loads(record.read_text(encoding="utf-8"))
    assert repo.git("status", "--porcelain") == ""


def test_proof_sets_no_run_folder_while_spec_0010_says_so(repo):
    """REQ-051: brief #613 answer 1, the conservative reading of `Q-613-1`: proof changes nothing
    in ROOT's work tree and adds no variable (SPEC-0010 rules 8 and 11), so its command sees no
    AGK_RUN_DIR and no results root is made, until an amendment says otherwise."""
    start(repo, 'test -z "$AGK_RUN_DIR" && test -f feature.txt')
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    proc = repo.run("proof.py", AGK_RUN_DIR="")
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert not (repo.root / ".agk-runs").exists()
