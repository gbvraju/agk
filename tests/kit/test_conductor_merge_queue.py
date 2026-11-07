"""conductor.py merge-queue: the batched merge queue (brief #643 build (b), ADR-0329).

REQ-037. The queue merges every cleared, green, unheld pull request in the order of the verdicts,
each through `merge_cleared.py --pr N --sha <head>` (its own check before the merge stays), with
no wait for the default branch's run between two merges; it stops at the first result that is not
a clean merge (conductor catch log row 3), waits once for the default branch's run on the last
merge and, when that run is red, stops and lists the batch. `--max-batch N` (5 by default) bounds a
batch and `--dry-run` prints the order and merges nothing. The first group replaces the queue's
reads and its merge runs in the test's own process; the last group runs the command against the
saved GitHub answers of the `merge_cleared.py` tests. No network; invented logins."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys

import pytest
from test_merge_cleared_verdict import (
    HEAD,
    MERGE,
    MERGE12,
    ON,
    OWNER,
    REPO,
    SCRIPTS,
    SHA12,
    calls,
    cleared,
    comment,
    fake_gh,
    repo,
    toml,
    world,
)

sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import merge_cleared  # noqa: E402
from common import CheckError  # noqa: E402

BOSS = "boss"
PEOPLE = {"verdict_authors": [f"@{BOSS}"]}
YAML = f'version: 1\nverdict_authors: ["@{OWNER}"]\n'
FAST = "conductor_poll_seconds = 1\n"


def head(n: int) -> str:
    return f"{n:02d}" * 20


def merge_sha(n: int) -> str:
    return f"{n:02d}ee" * 10


def merged_line(n: int) -> str:
    return f"merge-cleared #{n} {head(n)[:12]}: merged {merge_sha(n)[:12]}\n"


def held_line(n: int, why: str = "the merge with the default branch fails governance") -> str:
    return f"merge-cleared #{n} {head(n)[:12]}: held: {why}\n"


class Queue:
    """The queue's world: what each read answers, and every step the queue takes, in order."""

    def __init__(self, tmp_path, monkeypatch) -> None:
        self.root = tmp_path
        self.pulls: list[dict] = []
        self.holds: dict[int, object] = {}
        self.results: dict[int, tuple[int, str]] = {}
        self.states = ["green"]
        self.issues: list[dict] = []
        self.data: dict = {"default_branch": "main"}
        self.steps: list[tuple] = []
        self.clock = 0.0
        rules = merge_cleared.Rules(self.data, PEOPLE, [], [], ["governance"])
        monkeypatch.setattr(merge_cleared, "ruled", lambda root: rules)
        monkeypatch.setattr(merge_cleared, "repo_of", lambda root: REPO)
        monkeypatch.setattr(merge_cleared, "holds", self.hold)
        monkeypatch.setattr(merge_cleared, "read_pages", lambda *a, **k: self.issues)
        monkeypatch.setattr(conductor, "read", lambda endpoint, what: self.pulls)
        monkeypatch.setattr(conductor, "settle", lambda r, n: self.steps.append(("settle", n)))
        monkeypatch.setattr(conductor, "run_merge", self.merge)
        monkeypatch.setattr(conductor, "full_sha", lambda root, short: short + "0" * 28)
        monkeypatch.setattr(conductor, "branch_state", self.state)
        monkeypatch.setattr(conductor.time, "sleep", self.sleep)
        monkeypatch.setattr(conductor.time, "monotonic", lambda: self.clock)

    def add(self, n: int, at: int, outcome: object = None, login: str = BOSS) -> None:
        """An open pull request N whose head was cleared at minute AT, or is held by OUTCOME."""
        self.pulls.append({"number": n, "head": {"sha": head(n)}, "user": {"login": "builder"}})
        verdict = comment(f"Verdict: cleared {head(n)}", login, at)
        self.holds[n] = outcome or ({"number": n}, verdict, [], 40, None)
        self.results[n] = (0, merged_line(n))

    def hold(self, root, repo_name, number, sha, rules):
        assert sha == head(number)
        found = self.holds[number]
        if isinstance(found, Exception):
            raise found
        return found

    def merge(self, root, number: int, sha: str) -> tuple[int, str]:
        self.steps.append(("merge", number, sha))
        code, out = self.results[number]
        print(out, end="")
        return code, out

    def state(self, root, repo_name, branch: str, sha: str) -> str:
        self.steps.append(("state", branch, sha))
        return self.states.pop(0) if len(self.states) > 1 else self.states[0]

    def sleep(self, seconds: float) -> None:
        self.steps.append(("sleep", seconds))
        self.clock += seconds

    def run(self, *args: str) -> int:
        return conductor.main(["merge-queue", *args], root=self.root)

    def kinds(self) -> list[str]:
        return [s[0] for s in self.steps]


@pytest.fixture
def queue(tmp_path, monkeypatch) -> Queue:
    return Queue(tmp_path, monkeypatch)


def lines(capsys) -> list[str]:
    return capsys.readouterr().out.splitlines()


# --- the order, the dry run and what is left out ------------------------------------------------


def test_dry_run_prints_the_order_of_the_verdicts_and_merges_nothing(queue, capsys):
    queue.add(9, at=30)
    queue.add(7, at=10)
    queue.add(8, at=20)
    queue.pulls.append({"number": 6, "draft": True, "head": {"sha": head(6)}})
    queue.holds[6] = merge_cleared.NotCleared("no verdict (rule 3)")
    assert queue.run("--dry-run") == 0
    assert lines(capsys) == [
        f"merge-queue: 1. #7 {head(7)[:12]}",
        f"merge-queue: 2. #8 {head(8)[:12]}",
        f"merge-queue: 3. #9 {head(9)[:12]}",
    ]
    assert queue.steps == [("settle", 9), ("settle", 7), ("settle", 8)]  # a draft is not read


def test_a_pull_request_with_no_clearing_verdict_is_left_out_and_a_held_one_is_named(queue, capsys):
    queue.add(7, at=10, outcome=merge_cleared.NotCleared("no verdict (rule 3)"))
    queue.add(8, at=20, outcome=merge_cleared.Held("spec approval (rule 5)"))
    queue.add(9, at=30, outcome=merge_cleared.Refused("head moved (rule 3)", 3))
    assert queue.run("--dry-run") == 0
    assert lines(capsys) == [
        f"not queued: #8 {head(8)[:12]}: spec approval (rule 5)",
        f"not queued: #9 {head(9)[:12]}: head moved (rule 3)",
        "merge-queue: nothing to merge",
    ]


def test_a_clearing_verdict_by_an_unlisted_author_is_not_queued(queue, capsys):
    queue.add(7, at=10, login="builder")
    assert queue.run() == 0
    out = lines(capsys)
    assert out[0].startswith(f"not queued: #7 {head(7)[:12]}: ")
    assert "verdict_authors" in out[0] and "builder" not in out[0]
    assert "merge" not in queue.kinds()


# --- the batch ----------------------------------------------------------------------------------


def test_the_queue_merges_in_order_with_no_wait_between_and_waits_once_at_the_end(queue, capsys):
    queue.add(9, at=30)
    queue.add(7, at=10)
    queue.add(8, at=20)
    queue.states = ["pending", "pending", "green"]
    assert queue.run() == 0
    last = merge_sha(9)[:12] + "0" * 28
    assert queue.steps == [
        ("settle", 9),  # each open pull request, as listed, before its holds are read
        ("settle", 7),
        ("settle", 8),
        ("merge", 7, head(7)),
        ("settle", 8),  # again before its merge: the merge of #7 moved the default branch
        ("merge", 8, head(8)),
        ("settle", 9),
        ("merge", 9, head(9)),
        ("state", "main", last),
        ("sleep", 60),
        ("state", "main", last),
        ("sleep", 60),
        ("state", "main", last),
    ]
    assert lines(capsys) == [
        merged_line(7).strip(),
        merged_line(8).strip(),
        merged_line(9).strip(),
        f"merge-queue: main green at {last[:12]} after the batch #7 #8 #9",
    ]


def test_the_queue_stops_at_the_first_held_line_and_runs_nothing_after_it(queue, capsys):
    """Catch log row 3: the line that is not a merge is read, and it ends the queue."""
    for n, at in ((7, 10), (8, 20), (9, 30)):
        queue.add(n, at=at)
    queue.results[8] = (3, held_line(8))
    assert queue.run() == 3
    assert [s for s in queue.steps if s[0] == "merge"] == [
        ("merge", 7, head(7)),
        ("merge", 8, head(8)),
    ]
    assert queue.kinds().count("state") == 1  # the one wait, for the run on #7's merge
    assert lines(capsys) == [
        merged_line(7).strip(),
        held_line(8).strip(),
        "merge-queue: stopped at #8 (exit 3); merged: #7",
        f"merge-queue: main green at {merge_sha(7)[:12]} after the batch #7",
    ]


def test_a_refusal_ends_the_queue_and_with_nothing_merged_there_is_no_wait(queue, capsys):
    queue.add(7, at=10)
    queue.add(8, at=20)
    queue.results[7] = (1, f"merge-cleared #7 {head(7)[:12]}: refused: GitHub refused the merge\n")
    assert queue.run() == 1
    assert queue.kinds() == ["settle", "settle", "merge"]
    assert lines(capsys)[-1] == "merge-queue: stopped at #7 (exit 1); merged: none"


def test_a_stopped_line_ends_the_queue_and_lists_the_batch_with_no_wait(queue, capsys):
    for n, at in ((7, 10), (8, 20), (9, 30)):
        queue.add(n, at=at)
    queue.results[8] = (1, "merge-cleared: stopped: default branch red after #8\n")
    assert queue.run() == 1
    assert queue.kinds() == ["settle", "settle", "settle", "merge", "settle", "merge"]
    assert lines(capsys)[-1] == "merge-queue: stopped at #8 (exit 1); merged: #7 #8"


def test_a_merge_whose_record_line_failed_still_counts_for_the_batch(queue, capsys):
    queue.add(7, at=10)
    queue.add(8, at=20)
    queue.results[7] = (1, merged_line(7).strip() + ": the record line cannot be posted\n")
    assert queue.run() == 1
    assert queue.kinds() == ["settle", "settle", "merge", "state"]
    assert lines(capsys)[-2:] == [
        "merge-queue: stopped at #7 (exit 1); merged: #7",
        f"merge-queue: main green at {merge_sha(7)[:12]} after the batch #7",
    ]


def test_a_red_run_of_the_default_branch_stops_and_lists_the_batch(queue, capsys):
    queue.add(7, at=10)
    queue.add(8, at=20)
    queue.states = ["pending", "red"]
    assert queue.run() == 1
    assert queue.kinds().count("state") == 2
    assert lines(capsys)[-1] == (
        f"merge-queue: stopped: main red at {merge_sha(8)[:12]} after the batch #7 #8"
    )


def test_a_run_that_does_not_end_in_time_is_said_and_is_not_green(queue, capsys):
    (queue.root / "agk.toml").write_text("[flow]\nmerge_queue_wait_minutes = 2\n", encoding="utf-8")
    queue.add(7, at=10)
    queue.states = ["pending"]
    assert queue.run() == 3
    assert queue.kinds().count("sleep") == 2
    assert lines(capsys)[-1] == (
        f"merge-queue: the run of main at {merge_sha(7)[:12]} has not ended after 2 minutes; "
        "batch #7"
    )


def test_a_read_of_the_runs_that_fails_is_printed_and_tried_again(queue, capsys, monkeypatch):
    queue.add(7, at=10)
    answers: list = [CheckError("the runs of the default branch cannot be read"), "green"]

    def state(root, repo_name, branch, sha):
        found = answers.pop(0)
        if isinstance(found, Exception):
            raise found
        return found

    monkeypatch.setattr(conductor, "branch_state", state)
    assert queue.run() == 0
    assert "cannot be read; retrying" in capsys.readouterr().err


def test_max_batch_bounds_a_batch_at_five_by_default(queue, capsys):
    for n in range(1, 8):
        queue.add(n, at=n)
    assert queue.run() == 0
    assert [s[1] for s in queue.steps if s[0] == "merge"] == [1, 2, 3, 4, 5]
    assert lines(capsys)[-2:] == [
        "merge-queue: 2 more wait for the next batch",
        f"merge-queue: main green at {merge_sha(5)[:12]} after the batch #1 #2 #3 #4 #5",
    ]


def test_max_batch_is_an_option(queue, capsys):
    for n in range(1, 5):
        queue.add(n, at=n)
    assert queue.run("--dry-run", "--max-batch", "2") == 0
    assert lines(capsys) == [
        f"merge-queue: 1. #1 {head(1)[:12]}",
        f"merge-queue: 2. #2 {head(2)[:12]}",
        "merge-queue: 2 more wait for the next batch",
    ]
    assert queue.run("--max-batch", "2") == 0
    assert [s[1] for s in queue.steps if s[0] == "merge"] == [1, 2]


@pytest.mark.parametrize("local", ["setting", "record issue"])
def test_local_mode_has_no_run_of_the_default_branch_to_wait_for(queue, capsys, local):
    if local == "setting":
        queue.data["execution"] = "local"
    else:
        queue.issues = [{"number": 40, "title": "Local mode since 2026-11-01"}]
    queue.add(7, at=10)
    assert queue.run() == 0
    assert "state" not in queue.kinds()
    assert lines(capsys)[-1] == (
        "merge-queue: local mode, no run of the default branch to wait for; batch #7"
    )


def test_with_nothing_cleared_there_is_nothing_to_merge(queue, capsys):
    assert queue.run() == 0
    assert lines(capsys) == ["merge-queue: nothing to merge"]
    assert queue.steps == []


@pytest.mark.parametrize(
    "args",
    [
        ["--max-batch"],
        ["--max-batch", "0"],
        ["--max-batch", "x"],
        ["--max-batch", "2", "--dry-run"],
        ["--dry-run", "--dry-run"],
        ["--force"],
    ],
)
def test_any_other_form_is_a_usage_error(queue, capsys, args):
    assert queue.run(*args) == 2
    assert "merge-queue [--dry-run] [--max-batch N]" in capsys.readouterr().err
    assert queue.steps == []


# --- the pieces the tests above replace ---------------------------------------------------------


def test_run_merge_runs_the_projects_own_merge_cleared_and_prints_its_line(
    tmp_path, monkeypatch, capsys
):
    seen: list = []

    def fake(argv, **kwargs):
        seen.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 3, stdout=held_line(7))

    monkeypatch.setattr(conductor.subprocess, "run", fake)
    assert conductor.run_merge(tmp_path, 7, head(7)) == (3, held_line(7))
    argv, kwargs = seen[0]
    script = str(SCRIPTS / "merge_cleared.py")
    assert argv == [sys.executable, script, "--pr", "7", "--sha", head(7)]
    assert kwargs["cwd"] == tmp_path and "shell" not in kwargs
    assert capsys.readouterr().out == held_line(7)


def push_run(sha: str, conclusion: str | None, rid: int = 1) -> dict:
    return {
        "id": rid, "display_title": "governance full", "event": "push", "head_sha": sha,
        "status": "completed" if conclusion else "in_progress", "conclusion": conclusion,
        "created_at": f"2026-11-06T10:{rid:02d}:00Z",
    }  # fmt: skip


@pytest.mark.parametrize(
    ("runs", "state"),
    [
        ([push_run(MERGE, "success")], "green"),
        ([push_run(MERGE, "failure")], "red"),
        ([push_run(MERGE, None)], "pending"),
        ([], "pending"),
        ([push_run(MERGE, "cancelled"), push_run(HEAD, "success", 2)], "green"),
        ([push_run(MERGE, "cancelled"), push_run(HEAD, "failure", 2)], "red"),
        ([push_run(MERGE, "cancelled"), push_run(HEAD, None, 2)], "pending"),
    ],
)
def test_the_state_of_the_default_branch_is_the_batched_reading(tmp_path, monkeypatch, runs, state):
    """ADR-0302: a run replaced while it waited is covered by the next one that contains it."""
    asked: list[str] = []

    def gh(endpoint: str):
        asked.append(endpoint)
        return {"workflow_runs": runs}

    monkeypatch.setattr(conductor.session, "gh", gh)
    monkeypatch.setattr(conductor, "contained_in", lambda root: lambda older, newer: True)
    monkeypatch.setattr(merge_cleared, "git_out", lambda root, *args: (0, ""))
    assert conductor.branch_state(tmp_path, REPO, "main", MERGE) == state
    assert asked == [
        f"repos/{REPO}/actions/workflows/governance.yml/runs?branch=main&event=push&per_page=100"
    ]


def test_runs_that_cannot_be_read_are_never_a_state(tmp_path, monkeypatch):
    monkeypatch.setattr(conductor.session, "gh", lambda endpoint: None)
    monkeypatch.setattr(merge_cleared, "git_out", lambda root, *args: (0, ""))
    with pytest.raises(CheckError, match="cannot be read"):
        conductor.branch_state(tmp_path, REPO, "main", MERGE)


def test_settle_reads_again_until_the_mergeable_state_is_known(monkeypatch):
    answers = [{"mergeable_state": "unknown"}, {"mergeable_state": "unknown"}, {}]
    reads: list[str] = []

    def read_json(endpoint, kind, what):
        reads.append(endpoint)
        return answers.pop(0)

    monkeypatch.setattr(merge_cleared, "read_json", read_json)
    monkeypatch.setattr(conductor.time, "sleep", lambda seconds: None)
    answers[-1] = {"mergeable_state": "clean"}
    conductor.settle(REPO, 7)
    assert reads == [f"repos/{REPO}/pulls/7"] * 3


def test_settle_gives_up_after_its_reads_and_leaves_the_judging_to_the_merge(monkeypatch):
    reads: list[str] = []

    def read_json(endpoint, kind, what):
        reads.append(endpoint)
        return {"mergeable_state": "unknown"}

    monkeypatch.setattr(merge_cleared, "read_json", read_json)
    monkeypatch.setattr(conductor.time, "sleep", lambda seconds: None)
    conductor.settle(REPO, 7)
    assert len(reads) == conductor.SETTLE


# --- against the saved answers of the merge_cleared.py tests ------------------------------------


def queue_run(root, bin_dir, *args: str):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    temp = bin_dir.parent / "temp"  # the locks of this test alone
    temp.mkdir(exist_ok=True)
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(temp)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "conductor.py"), "merge-queue", *args],
        cwd=root, capture_output=True, text=True, env=env, timeout=300,
    )  # fmt: skip


def bare(at: int = 5) -> dict:
    return cleared(HEAD, at=at, extra="")


NOT_QUEUED = f"not queued: #7 {SHA12}"


def writes(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if c[c.index("--method") + 1] != "GET"]


def test_the_dry_run_reads_the_holds_of_merge_cleared_and_writes_nothing(tmp_path):
    root = repo(tmp_path, toml(ON), reviewers_yaml=YAML)
    bin_dir, log = fake_gh(tmp_path, comments=[bare()])
    proc = queue_run(root, bin_dir, "--dry-run")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [f"merge-queue: 1. #7 {SHA12}"]
    assert writes(calls(log)) == []


@pytest.mark.parametrize(
    ("pull", "comments", "expected"),
    [
        ({"draft": True}, [bare()], [f"{NOT_QUEUED}: draft (rule 5)"]),
        ({"labels": [{"name": "agk:hold"}]}, [bare()], [f"{NOT_QUEUED}: hold label (rule 5)"]),
        ({}, [], []),
        ({}, [comment(f"Verdict: fix list {HEAD}\n\n1. A finding.", at=5)], []),
    ],
)
def test_the_dry_run_queues_nothing_that_merge_cleared_would_hold(
    tmp_path, pull, comments, expected
):
    root = repo(tmp_path, toml(ON), reviewers_yaml=YAML)
    bin_dir, log = fake_gh(tmp_path, pull={**world()["pull"], **pull}, comments=comments)
    proc = queue_run(root, bin_dir, "--dry-run")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [*expected, "merge-queue: nothing to merge"]
    assert writes(calls(log)) == []


def test_with_auto_merge_off_the_queue_is_refused_before_any_read(tmp_path):
    root = repo(tmp_path, toml(""), reviewers_yaml=YAML)
    bin_dir, log = fake_gh(tmp_path, comments=[bare()])
    for args in ([], ["--dry-run"]):
        proc = queue_run(root, bin_dir, *args)
        assert proc.returncode == 1
        assert "auto_merge" in proc.stderr and proc.stdout == ""
    assert calls(log) == []


def test_a_paused_kit_holds_the_queue(tmp_path):
    root = repo(tmp_path, "paused = true\n" + toml(ON), reviewers_yaml=YAML)
    bin_dir, log = fake_gh(tmp_path, comments=[bare()])
    proc = queue_run(root, bin_dir)
    assert proc.returncode == 3
    assert proc.stdout.strip().startswith("merge-queue: held: paused")
    assert calls(log) == []


def test_the_queue_merges_through_merge_cleared_and_in_local_mode_waits_for_no_run(tmp_path):
    root = repo(tmp_path, toml(ON, local=True), reviewers_yaml=YAML)
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    proc = queue_run(root, bin_dir)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        f"merge-cleared #7 {SHA12}: merged {MERGE12}",
        "merge-queue: local mode, no run of the default branch to wait for; batch #7",
    ]
    made = calls(log)
    assert len([c for c in made if "PUT" in c]) == 1
    assert not any("actions" in a for c in made for a in c)


@pytest.mark.parametrize(
    ("conclusion", "code", "last"),
    [
        ("success", 0, f"merge-queue: main green at {MERGE12} after the batch #7"),
        ("failure", 1, f"merge-queue: stopped: main red at {MERGE12} after the batch #7"),
    ],
)
def test_the_queue_waits_once_for_the_run_of_the_default_branch_on_the_last_merge(
    tmp_path, conclusion, code, last
):
    root = repo(tmp_path, toml(ON + FAST), reviewers_yaml=YAML)
    runs = [push_run(MERGE, conclusion)]
    bin_dir, log = fake_gh(tmp_path, comments=[bare()], branch_runs=runs)
    proc = queue_run(root, bin_dir)
    assert proc.returncode == code, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [f"merge-cleared #7 {SHA12}: merged {MERGE12}", last]
    made = calls(log)
    assert len([c for c in made if any("actions/workflows" in a for a in c)]) == 1
    posts = [c for c in writes(made) if "PUT" not in c]
    assert all("Verdict:" not in a and "Approve:" not in a for c in posts for a in c)


# --- the conductor lease (brief #700, ADR-0330) -------------------------------------------------

LEASE_HELD = "merge-queue: held: another conductor holds the lease until "
LEASE_SETTING = "(setting: plan_issue in the flow table of agk.toml)"


def marker(minutes_ago: int, who: str, kind: str = "active") -> dict:
    from datetime import UTC, datetime, timedelta

    when = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": 5, "user": {"login": "boss"}, "body": f"Conductor: {kind} {when} {who}"}


def with_lease(queue, monkeypatch, comments: list) -> None:
    (queue.root / "agk.toml").write_text("[flow]\nplan_issue = 61\n", encoding="utf-8")
    monkeypatch.setattr(conductor, "plan_comments", lambda repo_name, issue: comments)


def test_the_queue_is_refused_while_another_name_holds_a_valid_lease(queue, capsys, monkeypatch):
    with_lease(queue, monkeypatch, [marker(10, "c1")])
    queue.add(7, at=10)
    for args in ([], ["--dry-run"]):
        assert queue.run(*args) == merge_cleared.EXIT_HELD
        out = lines(capsys)
        assert len(out) == 1 and out[0].startswith(LEASE_HELD) and out[0].endswith(LEASE_SETTING)
        assert "c1" not in out[0]
    assert queue.steps == []


@pytest.mark.parametrize("found", [[], [marker(55, "c1")], [marker(5, "c1", "released")]])
def test_the_queue_runs_when_the_lease_is_free(queue, capsys, monkeypatch, found):
    with_lease(queue, monkeypatch, found)
    queue.add(7, at=10)
    assert queue.run("--dry-run") == 0
    assert lines(capsys) == [f"merge-queue: 1. #7 {head(7)[:12]}"]


def test_the_queue_runs_for_the_holder_of_the_lease(queue, capsys, monkeypatch):
    with_lease(queue, monkeypatch, [marker(10, "c1")])
    (queue.root / ".git" / "agk").mkdir(parents=True)
    (queue.root / ".git" / "agk" / "lease").write_text("c1\n", encoding="utf-8")
    monkeypatch.setattr(conductor, "lease_mark", lambda root: queue.root / ".git" / "agk" / "lease")
    queue.add(7, at=10)
    assert queue.run("--dry-run") == 0
    assert lines(capsys) == [f"merge-queue: 1. #7 {head(7)[:12]}"]


def test_without_the_setting_the_lease_is_off_and_nothing_is_read(queue, capsys, monkeypatch):
    monkeypatch.setattr(
        conductor, "plan_comments", lambda *a: pytest.fail("the plan issue was read")
    )
    queue.add(7, at=10)
    assert queue.run("--dry-run") == 0


def test_a_plan_issue_that_cannot_be_read_holds_the_queue(queue, capsys, monkeypatch):
    def unreadable(repo_name, issue):
        raise CheckError("the comments of #61 cannot be read")

    (queue.root / "agk.toml").write_text("[flow]\nplan_issue = 61\n", encoding="utf-8")
    monkeypatch.setattr(conductor, "plan_comments", unreadable)
    queue.add(7, at=10)
    assert queue.run() == 1
    assert "cannot be read" in capsys.readouterr().err
    assert queue.steps == []
