"""SPEC-0041 build (h), part 2: the gate of the level, its record, and no push (brief #1503).

Advances REQ-048 (AC5). Rule 19: `personal.py gate` runs the floor of rule 18 and the steps of
rule 17's level on the head, writes `records/gates/<head>.json` in the schema of `prepush.py
--record`, appends one event per step (rule 23), and on a pass prints the `git push` command for
the developer, never pushing (rule 20). `report` flags a branch pushed without a gate record.
Invented repositories and sidecars in `tmp_path`, a stub gitleaks, no network.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import evidence  # noqa: E402
import personal_state as ps  # noqa: E402

PERSON = "member-example-1"
EARLY = "2026-01-01T00:00:00Z"
LATE = "2099-01-01T00:00:00Z"
LEVELS = ["light", "tests-first", "spec", "review", "evidence"]
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
SPEC = "# SPEC-0001: The cart total counts every item\n\n- Status: Approved\n"
CONTEXT = "Truncated: no\n\n## Diff\n"
CLEARED = "Verdict: cleared\nContext truncated: no\n"


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(root: Path, subject: str) -> str:
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", subject)  # fmt: skip
    return git(root, "rev-parse", "HEAD")


def clone_of(tmp_path: Path, test: str | None = "assert shop.TOTAL == 3", body: str = "") -> Path:
    """`main` is the base (TOTAL = 2, one passing test); `work` sets TOTAL = 3 and, unless TEST
    is None, adds `tests/test_total.py`, red on the base and green on the head."""
    clone = tmp_path / "clone"
    (clone / "tests").mkdir(parents=True)
    git(clone, "init", "-q", "-b", "main")
    (clone / "run_tests.py").write_text(RUNNER, encoding="utf-8")
    (clone / "shop.py").write_text("TOTAL = 2\n", encoding="utf-8")
    (clone / "tests" / "test_old.py").write_text("import shop\nassert shop.TOTAL > 0\n", "utf-8")
    commit(clone, "base")
    git(clone, "checkout", "-q", "-b", "work")
    (clone / "shop.py").write_text("TOTAL = 3\n", encoding="utf-8")
    if test is not None:
        (clone / "tests" / "test_total.py").write_text(f"import shop\n{test}\n", "utf-8")
    commit(clone, "the total counts every item" + body)
    return clone


def sidecar_of(tmp_path: Path, level: str, extra: str = "") -> Path:
    side = tmp_path / "side"
    ps.make_sidecar(side, PERSON)
    toml = side / "agk.toml"
    command = f"{shlex.quote(sys.executable)} run_tests.py"
    text = toml.read_text(encoding="utf-8").replace('level = "light"', f'level = "{level}"')
    toml.write_text(text + f"test_command = {json.dumps(command)}\n{extra}", encoding="utf-8")
    commit(side, "settings")
    return side


def scanner(tmp_path: Path, present: bool = True) -> str:
    """A PATH with git and, when PRESENT, a stub gitleaks that finds nothing."""
    folder = tmp_path / ("bin" if present else "bin-none")
    folder.mkdir()
    found = shutil.which("git")
    assert found
    (folder / "git").symlink_to(found)
    if present:
        stub = folder / "gitleaks"
        stub.write_text(f"#!{sys.executable}\nraise SystemExit(0)\n", encoding="utf-8")
        stub.chmod(0o755)
    return str(folder)


def gate(clone: Path, side: Path, path: str, *extra: str) -> subprocess.CompletedProcess:
    skip = ("AGK_HOME", "AGK_BASE", "GITHUB_BASE_REF", "CI", "PATH")
    env = {k: v for k, v in os.environ.items() if k not in skip}
    env["PATH"] = path
    cmd = [sys.executable, str(SCRIPTS / "personal.py"), "gate", "--clone", str(clone)]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*cmd, "--sidecar", str(side), "--base", "main", *extra],
        capture_output=True, text=True, env=env,
    )  # fmt: skip


def gated(tmp_path: Path, level: str, clone: Path | None = None, extra: str = "", path=None):
    clone = clone or clone_of(tmp_path)
    side = sidecar_of(tmp_path, level, extra)
    return clone, side, gate(clone, side, path or scanner(tmp_path), "--approve")


def gate_record(side: Path, head: str) -> dict:
    return json.loads((side / "records" / "gates" / f"{head}.json").read_text(encoding="utf-8"))


def terminal_spec(side: Path, at: str) -> None:
    """An Approved spec and its terminal confirmation of rule 8, made at AT, in the sidecar."""
    (side / "docs" / "specs" / "0001-cart-total.md").write_text(SPEC, encoding="utf-8")
    c = git(side, "rev-parse", "HEAD")
    body = "\n".join(
        [f"Confirmed: {c}", f"Verdict: cleared {c}", "Record: SPEC-0001", "Approve: SPEC-0001",
         "Shown:", "SPEC-0001: The cart total counts every item", "docs/specs at c",
         "status: Draft -> Approved", f"confirmed by {PERSON} at a terminal at {at}"]
    )  # fmt: skip
    item = {"id": 1_000_001, "body": body, "user": {"login": PERSON}, "created_at": at,
            "performed_via_github_app": None}  # fmt: skip
    (side / "forge" / "comments-1.json").write_text(json.dumps([item]), encoding="utf-8")
    commit(side, "spec confirmed")


def review_files(side: Path, head: str, report: str = CLEARED, verdict: bool = True) -> None:
    folder = side / "records" / "reviews"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{head}.context.md").write_text(CONTEXT, encoding="utf-8")
    (folder / f"{head}.report.md").write_text(report, encoding="utf-8")
    if verdict:
        body = "\n".join(
            [f"Confirmed: {head}", f"Verdict: cleared {head}",
             f"confirmed by {PERSON} at a terminal at {EARLY}"]
        )  # fmt: skip
        item = {"id": 2_000_001, "body": body, "user": {"login": PERSON}, "created_at": EARLY,
                "performed_via_github_app": None}  # fmt: skip
        (side / "forge" / "comments-2.json").write_text(json.dumps([item]), encoding="utf-8")
    commit(side, "review")


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def prepared(tmp_path: Path, level: str, clone: Path | None = None) -> tuple[Path, Path]:
    """A clone and a sidecar that hold every record LEVEL needs."""
    clone = clone or clone_of(tmp_path)
    side = sidecar_of(tmp_path, level)
    if LEVELS.index(level) >= 2:
        terminal_spec(side, EARLY)
    if LEVELS.index(level) >= 3:
        review_files(side, git(clone, "rev-parse", "HEAD"))
    return clone, side


# --- rule 17: each level adds its steps, on a passing and a failing change ----------------------


@pytest.mark.parametrize("level", LEVELS)
def test_req_048_each_level_passes_a_change_that_meets_it(tmp_path, level):
    """REQ-048 AC5: rule 17 (each level's steps pass; the gate prints the push for the person)."""
    clone, side = prepared(tmp_path, level)
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "gate: passed" in done.stdout
    assert "git push origin work" in done.stdout
    steps = [s["name"] for s in gate_record(side, git(clone, "rev-parse", "HEAD"))["steps"]]
    expected = ["secret-scan", "no-regression", "tests-first", "spec", "review", "evidence"]
    assert steps == expected[: 2 + LEVELS.index(level)]


@pytest.mark.parametrize("level", LEVELS)
def test_req_048_each_level_fails_a_change_that_breaks_a_passing_test(tmp_path, level):
    """REQ-048 AC5: rules 17 and 18 (the floor fails at every level; no push is printed)."""
    clone, side = prepared(tmp_path, level, clone_of(tmp_path, test="assert shop.TOTAL == 2"))
    (clone / "tests" / "test_old.py").write_text("import shop\nassert shop.TOTAL == 2\n", "utf-8")
    commit(clone, "break the old test")
    if LEVELS.index(level) >= 3:
        review_files(side, git(clone, "rev-parse", "HEAD"))
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 1, done.stdout
    assert "floor: no-regression FAIL" in done.stdout
    assert "gate: failed" in done.stdout
    assert "git push" not in done.stdout


def test_req_048_light_runs_only_the_floor(tmp_path):
    """REQ-048 AC5: rule 17 (`light` adds nothing to the floor: a change with no test passes)."""
    _, _, done = gated(tmp_path, "light", clone_of(tmp_path, test=None))
    assert done.returncode == 0, done.stdout
    assert "tests-first" not in done.stdout


def test_req_048_tests_first_fails_a_change_without_a_test(tmp_path):
    """REQ-048 AC5: rule 17 (`tests-first` with no added test fails naming the step and setting)."""
    _, _, done = gated(tmp_path, "tests-first", clone_of(tmp_path, test=None))
    assert done.returncode == 1
    assert "gate: tests-first FAIL" in done.stdout
    assert "setting: personal.level" in done.stdout


def test_req_048_tests_first_fails_a_test_that_is_green_on_the_base(tmp_path):
    """REQ-048 AC5: rule 17 and SPEC-0010 (`proof.decide`: green on the base is not proven)."""
    _, _, done = gated(tmp_path, "tests-first", clone_of(tmp_path, test="assert shop.TOTAL > 0"))
    assert done.returncode == 1
    assert "gate: tests-first FAIL: green-on-base" in done.stdout


def test_req_048_spec_without_a_confirmed_spec_fails_naming_the_step(tmp_path):
    """REQ-048 AC5: rule 17 (`spec` with no spec confirmed at a terminal fails)."""
    _, _, done = gated(tmp_path, "spec")
    assert done.returncode == 1
    assert "gate: spec FAIL" in done.stdout
    assert "setting: personal.level" in done.stdout


def test_req_048_spec_confirmed_after_the_first_commit_fails(tmp_path):
    """REQ-048 AC5: rule 17 (the spec is confirmed before the change's first code commit)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "spec")
    terminal_spec(side, LATE)
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 1
    assert "gate: spec FAIL" in done.stdout


def test_req_048_review_without_a_confirmed_verdict_fails(tmp_path):
    """REQ-048 AC5: rule 17 (`review` needs the person's verdict naming the head)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "review")
    terminal_spec(side, EARLY)
    review_files(side, git(clone, "rev-parse", "HEAD"), verdict=False)
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 1
    assert "gate: review FAIL" in done.stdout
    assert "verdict" in done.stdout


def test_req_048_review_with_a_malformed_report_fails(tmp_path):
    """REQ-048 AC5: rule 17 (`check_review_report` judges the report unchanged)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "review")
    terminal_spec(side, EARLY)
    review_files(side, git(clone, "rev-parse", "HEAD"), report="Context truncated: no\n")
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 1
    assert "gate: review FAIL" in done.stdout


def test_req_048_evidence_with_a_differing_record_fails(tmp_path):
    """REQ-048 AC5: rule 17 (`evidence.problems`: a record of a dirty tree differs)."""
    clone, side = prepared(tmp_path, "evidence")
    (clone / "notes.txt").write_text("not committed\n", encoding="utf-8")
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 1
    assert "gate: evidence FAIL: dirty" in done.stdout


# --- rule 18: the floor ---------------------------------------------------------------------------


def test_req_048_gitleaks_missing_fails_the_floor_as_today(tmp_path):
    """REQ-048 AC5: rule 18 and Q-S0041-15 (no gitleaks: the gate fails)."""
    _, _, done = gated(tmp_path, "light", path=scanner(tmp_path, present=False))
    assert done.returncode == 1
    assert "floor: secret scan not run (gitleaks not installed)" in done.stdout


def test_req_048_without_approve_nothing_runs_and_nothing_is_written(tmp_path):
    """REQ-048 AC5: rule 16 (the person's yes runs the test command; else nothing is written)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "light")
    done = gate(clone, side, scanner(tmp_path))
    assert done.returncode == 1
    assert "--approve" in done.stdout
    assert not (side / "records" / "gates").exists()


# --- rules 19 and 23: the record, the events and one sidecar commit ------------------------------


def test_req_048_the_record_has_the_schema_of_prepush_record(tmp_path):
    """REQ-048 AC5: rule 19 (`evidence.parse` reads the gate record as a prepush record)."""
    clone, side, done = gated(tmp_path, "light")
    head = git(clone, "rev-parse", "HEAD")
    path = side / "records" / "gates" / f"{head}.json"
    record, _ = evidence.parse(path.read_bytes())
    assert record["head"] == head
    assert record["base"] == git(clone, "rev-parse", "main")
    assert record["result"] == "passed"
    assert record["level"] == "light"
    assert evidence.problems(record, head) == []


def test_req_048_a_failed_gate_still_writes_its_record(tmp_path):
    """REQ-048 AC5: rule 19 (a failure is recorded, never hidden)."""
    clone, side, done = gated(tmp_path, "tests-first", clone_of(tmp_path, test=None))
    assert done.returncode == 1
    assert gate_record(side, git(clone, "rev-parse", "HEAD"))["result"] == "failed"


def test_req_048_one_event_per_step_and_one_sidecar_commit(tmp_path):
    """REQ-048 AC5: rule 23 (one event per step and the gate's; one commit of the two paths)."""
    clone, side = prepared(tmp_path, "tests-first")
    before = git(side, "rev-list", "--count", "HEAD")
    gate(clone, side, scanner(tmp_path), "--approve")
    lines = (side / "metrics" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    steps = [json.loads(x)["step"] for x in lines]
    assert steps == ["floor", "tests-first", "gate"]
    assert int(git(side, "rev-list", "--count", "HEAD")) == int(before) + 1
    head = git(clone, "rev-parse", "HEAD")
    changed = git(side, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert sorted(changed) == sorted([f"records/gates/{head}.json", "metrics/events.jsonl"])


# --- rule 20: it never pushes, and warns of team references -------------------------------------


def test_req_048_no_argument_list_of_personal_holds_push_or_a_rewrite():
    """REQ-048 AC5: rules 20 and 22 (no `push`, `amend`, `rebase`, `filter-branch` or `notes`)."""
    tree = ast.parse((SCRIPTS / "personal.py").read_text(encoding="utf-8"))
    words = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)}
    for word in ("push", "--amend", "rebase", "filter-branch", "notes"):
        assert word not in words


def test_req_048_a_pass_pushes_nothing(tmp_path):
    """REQ-048 AC5: rule 20 (the remote-tracking refs are as before the gate)."""
    clone = clone_of(tmp_path)
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    git(clone, "remote", "add", "origin", str(bare))
    _, _, done = gated(tmp_path, "light", clone)
    assert done.returncode == 0, done.stdout
    assert git(bare, "for-each-ref") == ""


def test_req_048_an_advances_line_with_team_refs_off_warns(tmp_path):
    """REQ-048 AC5: rule 20 (a warning names the setting; the gate still judges the steps)."""
    clone = clone_of(tmp_path, body="\n\nAdvances: REQ-001")
    _, _, done = gated(tmp_path, "light", clone)
    assert "warning" in done.stdout
    assert "setting: personal.team_refs" in done.stdout
    assert "REQ-001" not in done.stdout
    assert done.returncode == 0


def test_req_048_a_sidecar_path_with_team_refs_off_warns(tmp_path):
    """REQ-048 AC5: rule 20 (a path of the sidecar layout in a commit of the branch warns)."""
    clone = clone_of(tmp_path)
    (clone / "test-map.toml").write_text("# invented\n", encoding="utf-8")
    commit(clone, "a map")
    _, _, done = gated(tmp_path, "light", clone)
    assert "setting: personal.team_refs" in done.stdout


def test_req_048_team_refs_on_gives_no_warning(tmp_path):
    """REQ-048 AC5: rule 20 (`team_refs = true` lets the developer keep the references)."""
    clone = clone_of(tmp_path, body="\n\nAdvances: REQ-001")
    _, _, done = gated(tmp_path, "light", clone, extra="team_refs = true\n")
    assert "personal.team_refs" not in done.stdout


# --- rule 19: report flags a branch pushed without a gate ----------------------------------------


def upstream(clone: Path, branch: str) -> None:
    """The branch's upstream is `origin/<branch>` at its head, set without a remote or a fetch."""
    git(clone, "update-ref", f"refs/remotes/origin/{branch}", git(clone, "rev-parse", branch))
    git(clone, "config", f"branch.{branch}.remote", "origin")
    git(clone, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")


def report(clone: Path, side: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPTS / "personal.py"), "report", "--clone", str(clone)]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*cmd, "--sidecar", str(side)], capture_output=True, text=True
    )


def test_req_048_report_flags_a_branch_pushed_without_a_gate(tmp_path):
    """REQ-048 AC5: rule 19 (a pushed head with no gate record is named by its branch)."""
    clone = clone_of(tmp_path)
    side = sidecar_of(tmp_path, "light")
    upstream(clone, "work")
    done = report(clone, side)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "report: pushed without a gate: work" in done.stdout


def test_req_048_report_does_not_flag_a_gated_or_unpushed_branch(tmp_path):
    """REQ-048 AC5: rule 19 (a gated head, and a head ahead of its upstream, are not flagged)."""
    clone, side, done = gated(tmp_path, "light")
    assert done.returncode == 0, done.stdout
    upstream(clone, "work")
    git(clone, "branch", "ahead", "main")
    upstream(clone, "ahead")
    git(clone, "checkout", "-q", "ahead")
    commit_file = clone / "later.txt"
    commit_file.write_text("later\n", encoding="utf-8")
    commit(clone, "ahead of its upstream")
    out = report(clone, side).stdout
    assert "pushed without a gate: work" not in out
    assert "pushed without a gate: ahead" not in out


# --- rule 4: nothing in the product clone ---------------------------------------------------------


@pytest.mark.parametrize("level", ["light", "evidence"])
def test_req_048_the_gate_writes_nothing_in_the_clone_or_its_git_folder(tmp_path, level):
    """REQ-048 AC5: rule 4 (the clone's files and `.git/` are unchanged; its status is empty)."""
    clone, side = prepared(tmp_path, level)
    git(clone, "status", "--porcelain")  # the index is fresh before the snapshot
    before = snapshot(clone)
    done = gate(clone, side, scanner(tmp_path), "--approve")
    assert done.returncode == 0, done.stdout
    assert snapshot(clone) == before
    assert git(clone, "status", "--porcelain") == ""
    assert git(clone, "worktree", "list").count("\n") == 0
