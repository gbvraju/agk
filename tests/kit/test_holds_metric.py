"""Every hold is measured (amendment 141 item 7, `Q-772-1` as read; SPEC-0007 by item 10).

REQ-057 AC13. `session.py plan --record` appends one line per held brief and holder to
`docs/runs/holds.jsonl`, kept out of git; after both merge one more line marks the hold;
`metrics.py` reads the file and says `unknown` where it is absent. Local git fixtures and a `gh`
stub; invented data only; no network."""

from __future__ import annotations

import json
from datetime import date, timedelta

import metrics as metrics_module
import pytest
import session_plan
from test_metrics import metrics
from test_session import ISSUES, REPO, Stub, comment, iso, issue, listing, posts
from test_session_flow import DAY as TODAY
from test_session_flow import PULLS, brief, pr
from test_session_plan import changed, free, labelled, plan

HOLDS = "docs/runs/holds.jsonl"
DAY = timedelta(days=1)
TEN = "".join(f"line {n}\n" for n in range(1, 11))


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def rows(proj) -> list[dict]:
    path = proj.root / HOLDS
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def seed(proj, *records: dict) -> None:
    proj.write(HOLDS, "".join(json.dumps(r) + "\n" for r in records))


def held_by_pull(stub: Stub) -> None:
    stub.serve(PULLS, [labelled(20, 90, "agk:review")])
    changed(stub, 20, ("modified", "a.py"))
    listing(stub, [issue(5, brief("a.py"))])
    free(stub, 5)


# --- the record --------------------------------------------------------------------------------


def test_ac13_a_recorded_pass_appends_one_line_per_hold(proj, stub):
    """REQ-057 AC13: item 7, the fields; the first record of a pair is minute 0."""
    held_by_pull(stub)
    assert plan(proj, stub, "--record").returncode == 0
    [row] = rows(proj)
    assert {k: row[k] for k in ("brief", "holder", "file", "minutes")} == {
        "brief": 5, "holder": 20, "file": "a.py", "minutes": 0,
    }  # fmt: skip
    assert row["at"].endswith("Z") and len(row["at"]) == 20


@pytest.mark.parametrize("extra", [(), ("--json",)])
def test_ac13_without_the_flag_nothing_is_written(proj, stub, extra):
    """REQ-057 AC13: `Q-772-1` as read, `plan` appends only with `--record`."""
    held_by_pull(stub)
    assert plan(proj, stub, *extra).returncode == 0
    assert not (proj.root / HOLDS).exists()


def test_ac13_the_output_of_a_recorded_pass_is_the_plan(proj, stub):
    """REQ-057 AC13: `--record` changes the file and nothing that is printed."""
    held_by_pull(stub)
    before = plan(proj, stub).stdout
    assert plan(proj, stub, "--record").stdout == before


def test_ac13_minutes_count_from_the_first_record_of_the_pair(proj, stub):
    """REQ-057 AC13: item 7, `minutes` since that pair was first recorded."""
    first = {
        "at": iso(-timedelta(minutes=45)),
        "brief": 5,
        "holder": 20,
        "file": "a.py",
        "minutes": 0,
    }
    seed(proj, first)
    held_by_pull(stub)
    plan(proj, stub, "--record")
    assert 44 <= rows(proj)[-1]["minutes"] <= 46


def test_ac13_lines_are_only_ever_appended(proj, stub):
    """REQ-057 AC13: item 7."""
    seed(proj, {"at": iso(), "brief": 7, "holder": 8, "file": "z.py", "minutes": 0})
    before = (proj.root / HOLDS).read_bytes()
    held_by_pull(stub)
    plan(proj, stub, "--record")
    assert (proj.root / HOLDS).read_bytes().startswith(before)


def test_ac13_a_brief_with_two_holders_has_one_line_each(proj, stub):
    """REQ-057 AC13: `Q-772-6`, one line per pair."""
    stub.serve(PULLS, [labelled(20, 90, "agk:review"), labelled(30, 91, "agk:review")])
    changed(stub, 20, ("modified", "a.py"))
    changed(stub, 30, ("modified", "b.py"))
    listing(stub, [issue(5, brief("a.py, b.py"))])
    free(stub, 5)
    plan(proj, stub, "--record")
    assert [(r["brief"], r["holder"], r["file"]) for r in rows(proj)] == [
        (5, 20, "a.py"), (5, 30, "b.py"),
    ]  # fmt: skip


def test_ac13_a_taken_brief_and_an_earlier_ready_brief_are_holders(proj, stub):
    """REQ-057 AC13: item 7, every kind of hold the plan's waves make."""
    stub.serve(PULLS, [])
    listing(
        stub,
        [
            issue(4, brief("t.py")),
            issue(5, brief("t.py")),
            issue(6, brief("u.py")),
            issue(7, brief("u.py")),
        ],
    )
    stub.serve(f"{ISSUES}/4/comments", [comment(1, "other", f"taken: other {TODAY}")])
    free(stub, 5, 6, 7)
    plan(proj, stub, "--record")
    assert [(r["brief"], r["holder"], r["file"]) for r in rows(proj)] == [
        (5, 4, "t.py"), (7, 6, "u.py"),
    ]  # fmt: skip


def test_ac13_recording_posts_nothing(proj, stub):
    """REQ-057 AC13: `plan` stays read-only on GitHub."""
    held_by_pull(stub)
    plan(proj, stub, "--record")
    assert posts(stub) == []


def test_ac13_the_record_is_kept_out_of_git(proj, stub):
    """REQ-057 AC13: `Q-772-1` as read, principle 5: no tracked ignore line, in any project."""
    held_by_pull(stub)
    plan(proj, stub, "--record")
    plan(proj, stub, "--record")
    assert (proj.root / HOLDS).exists()
    assert HOLDS not in proj.git("status", "--porcelain", "--untracked-files=all")
    exclude = proj.root / ".git" / "info" / "exclude"
    assert exclude.read_text(encoding="utf-8").splitlines().count(HOLDS) == 1


# --- marking a hold ----------------------------------------------------------------------------


class Commits:
    """A file `f.txt` of ten lines, changed by commits this fixture names."""

    def __init__(self, repo) -> None:
        self.repo = repo
        self.lines = TEN.splitlines(keepends=True)
        repo.write("f.txt", TEN)
        repo.git("add", "-A")
        repo.git("commit", "-qm", "base")

    def change(self, *at: int, text: str = "x") -> str:
        """Rewrite the lines at these 1-based numbers; the sha of the commit."""
        for n in at:
            self.lines[n - 1] = f"{text} {n}\n"
        return self.save()

    def insert(self, count: int) -> str:
        self.lines[:0] = [f"new {n}\n" for n in range(count)]
        return self.save()

    def save(self) -> str:
        self.repo.write("f.txt", "".join(self.lines))
        self.repo.git("add", "-A")
        self.repo.git("commit", "-qm", "c")
        return self.repo.git("rev-parse", "HEAD").strip()


@pytest.fixture
def commits(repo):
    return Commits(repo)


def mark(repo, first: str, second: str, path: str = "f.txt") -> str | None:
    return session_plan.hold_mark(repo.root, path, first, second)


def test_ac13_no_common_line_is_a_false_hold(repo, commits):
    """REQ-057 AC13: item 7."""
    assert mark(repo, commits.change(2), commits.change(8)) == "false"


def test_ac13_a_common_line_is_a_true_hold(repo, commits):
    """REQ-057 AC13: item 7."""
    assert mark(repo, commits.change(2), commits.change(2, text="y")) == "true"


def test_ac13_lines_are_mapped_back_over_the_commits_between(repo, commits):
    """REQ-057 AC13: item 7, mapped back: line 7 of the later diff was line 2."""
    first = commits.change(2)
    commits.insert(5)
    assert mark(repo, first, commits.change(7, text="y")) == "true"


def test_ac13_a_line_moved_by_the_commits_between_stays_apart(repo, commits):
    """REQ-057 AC13: item 7, the same number after the shift is another line."""
    first = commits.change(7)
    commits.insert(5)
    assert mark(repo, first, commits.change(7, text="y")) == "false"


def test_ac13_a_line_inside_a_change_between_maps_to_the_whole_of_it(repo, commits):
    """REQ-057 AC13: item 7, the safe side: a later line that a commit between rewrote may be any
    of the lines it replaced, so a hold on one of them is true."""
    first = commits.change(4)
    commits.lines[1:4] = ["merged\n"]
    commits.save()
    assert mark(repo, first, commits.change(2, text="y")) == "true"


def test_ac13_a_file_only_one_changed_is_a_false_hold(repo, commits):
    """REQ-057 AC13: item 7, "a file only one of them changed included"."""
    first = commits.change(2)
    repo.write("g.txt", "other\n")
    repo.git("add", "-A")
    repo.git("commit", "-qm", "other")
    assert mark(repo, first, repo.git("rev-parse", "HEAD").strip()) == "false"


def test_ac13_a_rename_is_unknown(repo, commits):
    """REQ-057 AC13: item 7, "as for a rename"."""
    first = commits.change(2)
    repo.git("mv", "f.txt", "renamed.txt")
    repo.git("commit", "-qm", "move")
    assert mark(repo, first, repo.git("rev-parse", "HEAD").strip()) == "unknown"


def test_ac13_a_binary_file_changed_by_both_is_unknown(repo, commits):
    """REQ-057 AC13: item 7, a file with no lines cannot be mapped."""
    shas = []
    for content in (b"\0one", b"\0two"):
        (repo.root / "b.bin").write_bytes(content)
        repo.git("add", "-A")
        repo.git("commit", "-qm", "bin")
        shas.append(repo.git("rev-parse", "HEAD").strip())
    assert mark(repo, shas[0], shas[1], "b.bin") == "unknown"


def test_ac13_a_folder_entry_is_unknown(repo, commits):
    """REQ-057 AC13: item 7, two folders clash on a folder, which has no lines to map."""
    repo.write("d/one.txt", "1\n")
    repo.git("add", "-A")
    repo.git("commit", "-qm", "d")
    first = repo.git("rev-parse", "HEAD").strip()
    repo.write("d/two.txt", "2\n")
    repo.git("add", "-A")
    repo.git("commit", "-qm", "e")
    assert mark(repo, first, repo.git("rev-parse", "HEAD").strip(), "d") == "unknown"


def test_ac13_commits_on_two_lines_of_history_are_unknown(repo, commits):
    """REQ-057 AC13: item 7, the mapping needs the later one to follow the earlier one."""
    first = commits.change(2)
    repo.git("checkout", "-q", "-b", "side", f"{first}^")
    repo.write("f.txt", TEN.replace("line 8\n", "side\n"))
    repo.git("add", "-A")
    repo.git("commit", "-qm", "side")
    assert mark(repo, first, repo.git("rev-parse", "HEAD").strip()) == "unknown"


def merged_pull(number: int, brief_no: int, at: timedelta, sha: str) -> dict:
    return {**pr(number, brief_no, state="closed"), "merged_at": iso(-at), "merge_commit_sha": sha}


def pair(**extra) -> dict:
    return {"at": iso(-DAY), "brief": 5, "holder": 20, "file": "f.txt", "minutes": 0} | extra


def marked(proj, stub, pulls: list[dict]) -> list[dict]:
    stub.serve(PULLS, pulls)
    listing(stub, [])
    assert plan(proj, stub, "--record").returncode == 0
    return [r for r in rows(proj) if "mark" in r]


def test_ac13_after_both_merge_one_more_line_marks_the_hold(proj, stub, commits):
    """REQ-057 AC13: item 7; the holder is the pull request, the brief merged by its own."""
    first, second = commits.change(2), commits.change(8)
    seed(proj, pair())
    merged_holder = {**merged_pull(20, 90, DAY, first)}
    found = marked(proj, stub, [merged_holder, merged_pull(21, 5, DAY / 2, second)])
    assert [(r["brief"], r["holder"], r["file"], r["mark"]) for r in found] == [
        (5, 20, "f.txt", "false")
    ]


def test_ac13_a_hold_is_marked_once(proj, stub, commits):
    """REQ-057 AC13: item 7, "one more line"."""
    first, second = commits.change(2), commits.change(2, text="y")
    seed(proj, pair())
    pulls = [merged_pull(20, 90, DAY, first), merged_pull(21, 5, DAY / 2, second)]
    assert [r["mark"] for r in marked(proj, stub, pulls)] == ["true"]
    assert [r["mark"] for r in marked(proj, stub, pulls)] == ["true"]


def test_ac13_a_holder_brief_is_followed_to_its_pull_request(proj, stub, commits):
    """REQ-057 AC13: item 7, a taken brief that held another is read through its `Brief:` line."""
    first, second = commits.change(2), commits.change(8)
    seed(proj, pair(holder=4))
    found = marked(
        proj, stub, [merged_pull(30, 4, DAY, first), merged_pull(31, 5, DAY / 2, second)]
    )
    assert [r["mark"] for r in found] == ["false"]


def test_ac13_nothing_is_marked_until_both_merged(proj, stub, commits):
    """REQ-057 AC13: item 7, "after both merge"."""
    seed(proj, pair())
    assert marked(proj, stub, [merged_pull(21, 5, DAY, commits.change(2))]) == []


def test_ac13_a_brief_of_two_merged_builds_is_unknown(proj, stub, commits):
    """REQ-057 AC13: item 7, no single merged diff to map."""
    a, b, c = commits.change(2), commits.change(4), commits.change(8)
    seed(proj, pair())
    pulls = [
        merged_pull(20, 90, DAY, a),
        merged_pull(21, 5, DAY / 2, b),
        merged_pull(22, 5, DAY / 4, c),
    ]
    assert [r["mark"] for r in marked(proj, stub, pulls)] == ["unknown"]


def test_ac13_a_commit_not_fetched_waits_for_a_later_pass(proj, stub, commits):
    """REQ-057 AC13: a stale clone is no measurement, so it marks nothing rather than `unknown`."""
    first = commits.change(2)
    seed(proj, pair())
    pulls = [merged_pull(20, 90, DAY, first), merged_pull(21, 5, DAY / 2, "0" * 40)]
    assert marked(proj, stub, pulls) == []


def test_ac13_a_line_that_cannot_be_read_is_passed_over(proj, stub):
    """REQ-057 AC13: one bad line of an append-only file does not end the record."""
    proj.write(HOLDS, "not json\n[1]\n")
    held_by_pull(stub)
    assert plan(proj, stub, "--record").returncode == 0
    assert (proj.root / HOLDS).read_text(encoding="utf-8").startswith("not json\n[1]\n")


# --- the weekly report -------------------------------------------------------------------------

MONDAY = date(2026, 10, 5)
NEXT = date(2026, 10, 12)


def stamped(day: int, hour: int = 12, **fields) -> dict:
    return {
        "at": f"2026-10-{day:02d}T{hour:02d}:00:00Z",
        "brief": 5,
        "holder": 20,
        "file": "a.py",
    } | fields


def line(proj, *records: dict) -> str:
    seed(proj, *records)
    return metrics_module.holds_line(proj.root, MONDAY, NEXT)


def test_ac13_an_absent_file_reports_unknown(repo):
    """REQ-057 AC13: item 7, never 0."""
    assert metrics_module.holds_line(repo.root, MONDAY, NEXT) == "holds: unknown"


def test_ac13_an_empty_file_reports_unknown(proj):
    """REQ-057 AC13: item 7, never 0."""
    proj.write(HOLDS, "")
    assert metrics_module.holds_line(proj.root, MONDAY, NEXT) == "holds: unknown"


def test_ac13_a_week_with_no_record_reports_unknown(proj):
    """REQ-057 AC13: a measure of another week says nothing about this one."""
    assert line(proj, stamped(1, minutes=70)) == "holds: unknown"


def test_ac13_the_line_gives_minutes_rate_and_worst_entry(proj):
    """REQ-057 AC13: item 7, SPEC-0007 by item 10; 70 minutes over a 7-day window."""
    found = line(
        proj,
        stamped(6, 9, minutes=0),
        stamped(6, 10, minutes=70),
        stamped(7, mark="false"),
        stamped(7, file="b.py", brief=6, mark="false"),
        stamped(7, file="a.py", brief=7, mark="false"),
        stamped(8, file="c.py", brief=8, mark="true"),
    )
    assert found == (
        "holds: held builder-minutes per day 10.0; false-hold rate 3/4 (75%); "
        "most false holds: a.py (2)"
    )


def test_ac13_unknown_marks_are_left_out_of_the_rate(proj):
    """REQ-057 AC13: item 7."""
    found = line(proj, stamped(6, mark="false"), stamped(6, brief=6, mark="unknown"))
    assert "false-hold rate 1/1 (100%)" in found


def test_ac13_with_no_mark_the_rate_is_unknown(proj):
    """REQ-057 AC13: item 7, a rate of nothing is unknown, never 0."""
    assert line(proj, stamped(6, minutes=7)) == (
        "holds: held builder-minutes per day 1.0; false-hold rate unknown; most false holds: none"
    )


def test_ac13_a_brief_with_two_holders_is_one_builder_waiting(proj):
    """REQ-057 AC13: item 7, builder-minutes: the longest of the two, never the sum."""
    found = line(
        proj,
        stamped(6, 9, minutes=0),
        stamped(6, 10, minutes=70),
        stamped(6, 9, holder=30, file="b.py", minutes=0),
        stamped(6, 10, holder=30, file="b.py", minutes=70),
    )
    assert found.startswith("holds: held builder-minutes per day 10.0;")


def test_ac13_minutes_are_counted_on_the_day_they_passed(proj):
    """REQ-057 AC13: item 7, `minutes` is cumulative: an earlier week's share is not this week's."""
    found = line(proj, stamped(4, minutes=700), stamped(6, minutes=770))
    assert found.startswith("holds: held builder-minutes per day 10.0;")


def test_ac13_unreadable_lines_are_passed_over(proj):
    """REQ-057 AC13: `unknown`, never a crash and never 0."""
    proj.write(HOLDS, 'nonsense\n[]\n{"at": 3}\n')
    assert metrics_module.holds_line(proj.root, MONDAY, NEXT) == "holds: unknown"


def test_ac13_the_weekly_report_carries_the_line(repo):
    """REQ-057 AC13: SPEC-0007 by item 10; in a workflow the file is absent."""
    proc = metrics(repo, "empty-week")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "holds: unknown" in proc.stdout.splitlines()
