"""The nine-point operations checklist (brief #799, REQ-054, ADR-0374; brief #981, ADR-0420).

`checklist.py` is read-only and judges saved facts: tests use invented saved documents (example.com
names only) and a temporary root; no network, no `gh`.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import checklist
import metrics
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SAVED_AT = "2026-03-10T12:00:00Z"
LINE = re.compile(r"^([1-9])\. ([a-z -]+): (yes|partly|no|unknown) (\S.*)$")
NAMES = [
    "machine capacity",
    "conductor runs builders",
    "test optimization",
    "parallel runs",
    "auto-merge",
    "model selection",
    "conflict planning",
    "smart assignment",
    "cost per pull request",
]


CONDUCTOR = "conductor-example"
CONDUCTOR_ISSUE = 5


def comment(issue: int, body: str, at: str, author: str = "builder-example") -> dict:
    return {
        "issue_url": f"https://api.example.com/repos/o/r/issues/{issue}",
        "body": body,
        "created_at": at,
        "user": {"login": author},
        "author": author,
    }


def assign(brief: int, at: str = "2026-03-10T07:00:00Z", **kw) -> dict:
    """An `Assign: s<brief> #<brief>` line on the conductor issue by the listed conductor."""
    slot = kw.get("slot", f"s{brief}")
    tail = kw.get("tail", "")
    issue = kw.get("issue", CONDUCTOR_ISSUE)
    return comment(issue, f"Assign: {slot} #{brief}{tail}", at, kw.get("author", CONDUCTOR))


def day(hour: int, minute: int = 0) -> str:
    return f"2026-03-10T{hour:02d}:{minute:02d}:00Z"


def report(started: int, refused: int = 0, at: str = day(9)) -> dict:
    text = f"Conductor report {at}\nBuilders started ({started}): a, b. Refused ({refused}): c."
    return comment(7, text, at)


def pull(number: int = 50, brief: int = 20, **extra) -> dict:
    record = {
        "number": number,
        "brief": brief,
        "state": "merged",
        "merged_at": day(11),
        "head": "a" * 40,
        "head_cleared": "yes",
        "usage": 1000,
        "verdicts": [{"kind": "cleared", "sha": "a" * 40, "at": day(10)}],
    }
    return record | extra


def saved(**extra) -> dict:
    document = {
        "saved_at": SAVED_AT,
        "facts": {"pull_requests": [pull()], "flow": {"stall_hours": 4}},
        "comments": [],
        "runs": [],
        "briefs": [],
        "pr_tests": None,
        "local_mode": False,
        "verdict_authors": [CONDUCTOR],
        "conductor_issues": [CONDUCTOR_ISSUE],
    }
    return document | extra


def takes(*briefs: int, at: str = day(8), hours: int = 0) -> list[dict]:
    return [comment(b, f"taken: s{b} 2026-03-10", at) for b in briefs]


def project(tmp_path, document=None, toml: str = "", holds: str | None = None) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    text = "[flow]\nmax_builders = 4\nauto_merge = true\nplan_issue = 7\n"
    text += '[testing]\nworkers = "auto"\n'
    (root / "agk.toml").write_text(text + toml, encoding="utf-8")
    if holds is not None:
        (root / "docs" / "runs").mkdir(parents=True)
        (root / "docs" / "runs" / "holds.jsonl").write_text(holds, encoding="utf-8")
    if document is not None:
        (tmp_path / "saved.json").write_text(json.dumps(document), encoding="utf-8")
    return root


def lines_of(capsys, root: Path, tmp_path, *more: str) -> dict[int, tuple[str, str]]:
    code = checklist.main(["--root", str(root), "--saved", str(tmp_path / "saved.json"), *more])
    assert code == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 9, out
    found = {}
    for number, line in enumerate(out, 1):
        match = LINE.fullmatch(line)
        assert match, line
        assert int(match[1]) == number
        assert match[2] == NAMES[number - 1]
        found[number] = (match[3], match[4])
    return found


def test_nine_lines_in_order_exit_zero(tmp_path, capsys):
    """REQ-054: brief #799 answer 1."""
    lines_of(capsys, project(tmp_path, saved()), tmp_path)


def test_no_saved_facts_is_unknown_with_a_reason_and_never_zero(tmp_path, capsys):
    """REQ-054: brief #799 answers 1 and 4."""
    root = project(tmp_path)
    found = lines_of(capsys, root, tmp_path)
    assert {status for status, _ in found.values()} == {"unknown"}
    for _, measure in found.values():
        assert not re.search(r"(?<![\w.-])0(?![\w.])", measure), measure
        assert measure.strip()


def test_capacity_yes_at_the_threshold_with_no_refused_start(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (1)."""
    document = saved(comments=[*takes(20, 21), report(2)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[1][0] == "yes"
    assert "peak 2" in found[1][1] and "max_builders 4" in found[1][1]
    assert "refused 0" in found[1][1]


def test_capacity_partly_below_the_threshold_or_with_a_refused_start(tmp_path, capsys):
    document = saved(comments=[*takes(20, 21), report(2, refused=1)])
    assert lines_of(capsys, project(tmp_path, document), tmp_path)[1][0] == "partly"


def test_capacity_partly_when_refused_starts_cannot_be_read(tmp_path, capsys):
    """A refused count that is not recorded is unknown, never 0, so it cannot say yes."""
    found = lines_of(capsys, project(tmp_path, saved(comments=takes(20, 21))), tmp_path)
    assert found[1][0] == "partly"
    assert "refused unknown" in found[1][1]


def test_capacity_no_when_no_builder_was_alive_in_the_window(tmp_path, capsys):
    found = lines_of(capsys, project(tmp_path, saved(comments=[report(0)])), tmp_path)
    assert found[1][0] == "no"
    assert found[4][0] == "no"


def test_a_take_ends_at_its_report_so_peak_counts_only_overlap(tmp_path, capsys):
    """Two takes in turn are one builder at once, not two."""
    first = takes(20, at=day(6))
    done = comment(50, "Report: abc ready for review\nUsage: 10 tokens", day(7))
    later = takes(21, at=day(8))
    document = saved(
        comments=[*first, done, *later, report(2)],
        facts={"pull_requests": [pull(50, 20)], "flow": {"stall_hours": 4}},
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "peak 1" in found[1][1]


def test_a_take_with_no_later_record_ends_at_the_stall_limit(tmp_path, capsys):
    first = takes(20, at=day(1))
    later = takes(21, at=day(9))
    document = saved(comments=[*first, *later, report(2)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "peak 1" in found[1][1]


def test_conductor_share_is_assigned_starts_over_takes(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (2); brief #981 answer 1."""
    document = saved(comments=[assign(20), *takes(20, 21, 22, 23), report(4)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "partly"
    assert "conductor 1 of 4 (25%); by hand 3" in found[2][1]


def test_hand_starts_are_not_counted_as_the_conductors(tmp_path, capsys):
    """REQ-054: brief #981 answer 3 (a): a report's own start count, an Assign by someone else,
    on another issue, for another brief or after the take are all starts by hand."""
    document = saved(
        comments=[
            assign(20, author="person-example"),
            assign(21, issue=99),
            assign(23, slot="s22"),
            *takes(20, 21, 22),
            assign(23, at=day(9)),
            *takes(23),
            report(4),
        ]
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "no"
    assert "conductor 0 of 4 (0%); by hand 4" in found[2][1]


def test_an_assign_followed_by_the_slots_take_is_counted_once(tmp_path, capsys):
    """REQ-054: brief #981 answer 3 (b): any Assign form counts; one Assign starts one take."""
    document = saved(
        comments=[
            assign(20),
            assign(21, tail=" build (b)"),
            *takes(20, 21),
            comment(20, "taken: s20 2026-03-10", day(9)),
        ]
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "partly"
    assert "conductor 2 of 3 (67%); by hand 1" in found[2][1]


def test_conductor_share_yes_and_stalls_replaced_counted(tmp_path, capsys):
    retake = comment(21, "taken: s9 2026-03-10 retakes", day(8))
    document = saved(comments=[assign(20), assign(21, slot="s9"), *takes(20), retake])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "yes"
    assert "stalls replaced 1" in found[2][1]


def test_a_takeover_counts_as_a_stall_replaced(tmp_path, capsys):
    over = comment(21, "taken over: s9 2026-03-10", day(8))
    document = saved(comments=[assign(20), *takes(20), over])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "stalls replaced 1" in found[2][1]


def test_conductor_share_no_when_it_assigned_none(tmp_path, capsys):
    document = saved(comments=[*takes(20), report(1)])
    assert lines_of(capsys, project(tmp_path, document), tmp_path)[2][0] == "no"


@pytest.mark.parametrize("missing", ["verdict_authors", "conductor_issues"])
def test_conductor_share_unknown_without_the_authors_or_the_issue(tmp_path, capsys, missing):
    document = saved(comments=[assign(20), *takes(20)])
    document[missing] = None
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "unknown"
    assert "not saved" in found[2][1]


def test_a_report_on_another_issue_is_not_read(tmp_path, capsys):
    stray = comment(99, "Conductor report x\nBuilders started (9): a. Refused (0): b.", day(9))
    found = lines_of(capsys, project(tmp_path, saved(comments=[*takes(20), stray])), tmp_path)
    assert "refused unknown" in found[1][1]


LINE_75 = (
    "pr tests: 12 runs; selected 9 of 12 (75%); test step 31.5 minutes; "
    "full: always_full 3; unknown: 0"
)
MEDIAN_FAST = "pr tests median: selected 2.5 minutes (9 runs); full 8.0 minutes (3 runs)"
MEDIAN_SLOW = "pr tests median: selected 8.0 minutes (9 runs); full 9.0 minutes (3 runs)"
FULL_SUITE = "full suite: median 300s; budget_seconds 600; 4 runs; slowest: x; workers: 2"
WEEKLY = {"pr_tests": LINE_75, "pr_tests_median": MEDIAN_FAST, "full_suite": FULL_SUITE}


def test_tests_share_and_minutes_from_the_weekly_line(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (3); brief #981 answer 2."""
    found = lines_of(capsys, project(tmp_path, saved(**WEEKLY)), tmp_path)
    assert found[3][0] == "yes"
    assert "9 of 12" in found[3][1] and "31.5 minutes" in found[3][1]
    assert "selected median 2.5 minutes; full suite median on main 5.0 minutes" in found[3][1]
    assert "(weekly line)" in found[3][1]


def test_tests_with_no_weekly_line_read_the_windows_figures(tmp_path, capsys):
    """REQ-054: brief #981 answer 3 (c)."""
    window = {"pr_tests": LINE_75, "pr_tests_median": MEDIAN_FAST, "full_suite": FULL_SUITE}
    found = lines_of(capsys, project(tmp_path, saved(window_tests=window)), tmp_path)
    assert found[3][0] == "yes"
    assert "9 of 12" in found[3][1] and "(window)" in found[3][1]


def test_a_weekly_line_with_no_runs_falls_back_to_the_window(tmp_path, capsys):
    empty = "pr tests: 0 runs; selected 0 of 0 (none); test step 0.0 minutes; full: x"
    window = {"pr_tests": LINE_75, "pr_tests_median": MEDIAN_FAST, "full_suite": FULL_SUITE}
    document = saved(pr_tests=empty, window_tests=window)
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[3][0] == "yes" and "(window)" in found[3][1]


def test_a_selected_median_slower_than_mains_full_median_reads_partly(tmp_path, capsys):
    """REQ-054: brief #981 answer 3 (d): both medians are printed."""
    found = lines_of(
        capsys, project(tmp_path, saved(**WEEKLY | {"pr_tests_median": MEDIAN_SLOW})), tmp_path
    )
    assert found[3][0] == "partly"
    assert "selected median 8.0 minutes; full suite median on main 5.0 minutes" in found[3][1]


@pytest.mark.parametrize("missing", ["pr_tests_median", "full_suite"])
def test_an_unknown_median_cannot_read_yes(tmp_path, capsys, missing):
    found = lines_of(capsys, project(tmp_path, saved(**WEEKLY | {missing: None})), tmp_path)
    assert found[3][0] == "partly"
    assert "median" in found[3][1] and "unknown" in found[3][1]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("pr tests: 4 runs; selected 1 of 4 (25%); test step 5.0 minutes; full: x", "partly"),
        ("pr tests: 4 runs; selected 0 of 4 (0%); test step 5.0 minutes; full: x", "no"),
        ("pr tests: 0 runs; selected 0 of 0 (none); test step 0.0 minutes; full: x", "unknown"),
        (None, "unknown"),
        ("not the line", "unknown"),
    ],
)
def test_tests_statuses(tmp_path, capsys, line, expected):
    document = saved(**WEEKLY | {"pr_tests": line})
    assert lines_of(capsys, project(tmp_path, document), tmp_path)[3][0] == expected


def test_parallel_yes_needs_the_peak_and_workers(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (4)."""
    document = saved(comments=[*takes(20, 21), report(2)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[4][0] == "yes"
    assert "workers auto" in found[4][1]


def test_parallel_partly_when_the_full_suite_has_one_worker(tmp_path, capsys):
    document = saved(comments=[*takes(20, 21), report(2)])
    root = tmp_path / "one"
    root.mkdir()
    (root / "agk.toml").write_text("[flow]\nmax_builders = 4\nplan_issue = 7\n", encoding="utf-8")
    (tmp_path / "saved.json").write_text(json.dumps(document), encoding="utf-8")
    found = lines_of(capsys, root, tmp_path)
    assert found[4][0] == "partly"
    assert "workers 1" in found[4][1]


def merger_run(conclusion: str, at: str = day(9)) -> dict:
    return {"name": "merger", "conclusion": conclusion, "created_at": at}


def test_auto_merge_yes_setting_on_clean_runs_no_late_cleared(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (5)."""
    document = saved(runs=[merger_run("success")])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[5][0] == "yes"
    assert "failed merger runs 0" in found[5][1]
    assert "cleared unmerged over 20 min 0" in found[5][1]


def test_auto_merge_partly_on_a_failed_run_or_a_late_cleared(tmp_path, capsys):
    late = pull(60, 30, state="open", merged_at=None)
    late["verdicts"] = [{"kind": "cleared", "sha": "a" * 40, "at": day(11, 30)}]
    document = saved(
        runs=[merger_run("failure"), merger_run("failure", "2026-02-01T00:00:00Z")],
        facts={"pull_requests": [late], "flow": {"stall_hours": 4}},
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[5][0] == "partly"
    assert "failed merger runs 1" in found[5][1]
    assert "cleared unmerged over 20 min 1" in found[5][1]


def test_auto_merge_a_cleared_head_inside_20_minutes_is_not_late(tmp_path, capsys):
    fresh = pull(61, 31, state="open", merged_at=None)
    fresh["verdicts"] = [{"kind": "cleared", "sha": "a" * 40, "at": day(11, 45)}]
    document = saved(facts={"pull_requests": [fresh], "flow": {"stall_hours": 4}})
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "cleared unmerged over 20 min 0" in found[5][1]


def test_auto_merge_a_head_cleared_by_a_fix_list_with_a_final_line_counts_as_late(tmp_path, capsys):
    """REQ-054: `head_cleared` is `yes` for a fix list with no items and a `Final:` line too."""
    waiting = pull(62, 32, state="open", merged_at=None)
    waiting["verdicts"] = [{"kind": "fix", "sha": "a" * 40, "at": day(11, 30)}]
    document = saved(facts={"pull_requests": [waiting], "flow": {"stall_hours": 4}})
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[5][0] == "partly"
    assert "cleared unmerged over 20 min 1" in found[5][1]


def test_auto_merge_a_verdict_on_another_head_does_not_date_a_cleared_head(tmp_path, capsys):
    waiting = pull(63, 33, state="open", merged_at=None)
    waiting["verdicts"] = [{"kind": "fix", "sha": "b" * 40, "at": day(11, 30)}]
    document = saved(facts={"pull_requests": [waiting], "flow": {"stall_hours": 4}})
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "cleared unmerged over 20 min 0" in found[5][1]


def test_auto_merge_no_when_the_setting_is_off(tmp_path, capsys):
    root = tmp_path / "off"
    root.mkdir()
    (root / "agk.toml").write_text("[flow]\nmax_builders = 4\nplan_issue = 7\n", encoding="utf-8")
    (tmp_path / "saved.json").write_text(json.dumps(saved()), encoding="utf-8")
    found = lines_of(capsys, root, tmp_path)
    assert found[5][0] == "no"
    assert "setting off" in found[5][1]


def test_models_are_unknown_with_the_reason(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (6), Q-799-2: no start records its runtime model."""
    found = lines_of(capsys, project(tmp_path, saved()), tmp_path)
    assert found[6][0] == "unknown"
    assert "runtime model" in found[6][1]


def hold(mark: str | None, at: str = day(9)) -> str:
    row = {"at": at, "brief": 20, "holder": 21, "file": "src/a.py", "minutes": 5}
    return json.dumps(row | ({"mark": mark} if mark else {})) + "\n"


def test_conflicts_rate_from_the_marks(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (7)."""
    holds = hold("true") * 9 + hold("false")
    found = lines_of(capsys, project(tmp_path, saved(), holds=holds), tmp_path)
    assert found[7][0] == "yes"
    assert "holds 10" in found[7][1] and "1/10" in found[7][1]


@pytest.mark.parametrize(
    "holds, expected",
    [
        (hold("true") * 7 + hold("false") * 3, "partly"),
        (hold("false") * 3 + hold("true"), "no"),
        (hold(None), "unknown"),
        ("not json\n", "unknown"),
        (hold("true", "2026-01-01T00:00:00Z"), "unknown"),
        (None, "unknown"),
    ],
)
def test_conflicts_statuses(tmp_path, capsys, holds, expected):
    assert lines_of(capsys, project(tmp_path, saved(), holds=holds), tmp_path)[7][0] == expected


def brief(number: int, created: str, closed: str | None = None, depends: str = "") -> dict:
    return {"number": number, "created_at": created, "closed_at": closed, "body": depends}


def test_idle_minutes_count_free_slots_while_a_brief_is_ready(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (8): one ready brief, slots free, for the last two hours."""
    document = saved(briefs=[brief(30, day(10))], comments=[report(0)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[8][0] == "partly"
    assert "idle builder-minutes 120" in found[8][1]


def test_idle_is_zero_and_yes_with_no_ready_brief(tmp_path, capsys):
    document = saved(
        briefs=[brief(30, "2026-02-01T00:00:00Z", "2026-02-02T00:00:00Z")], comments=[report(0)]
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[8][0] == "yes"
    assert "idle builder-minutes 0" in found[8][1]


def test_a_brief_waiting_on_an_open_dependency_is_not_ready(tmp_path, capsys):
    blocked = brief(30, day(10), depends="Depends-on: #31")
    other = brief(31, day(10))
    document = saved(briefs=[blocked, other], comments=[*takes(31, at=day(10))])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "idle builder-minutes 0" in found[8][1]


def test_a_taken_brief_is_not_ready_and_the_old_ones_count_as_idle_no(tmp_path, capsys):
    document = saved(briefs=[brief(30, "2026-03-05T12:00:00Z")], comments=[report(0)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[8][0] == "no"


def test_idle_unknown_without_the_brief_list(tmp_path, capsys):
    found = lines_of(capsys, project(tmp_path, saved(briefs=None)), tmp_path)
    assert found[8][0] == "unknown"


def test_cost_share_and_tokens_per_merged_pull_request(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (9)."""
    bodies = ["Report: a done\nUsage: 100 tokens", "Report: b done\nUsage: 300 tokens"]
    document = saved(
        comments=[comment(50, b, day(9)) for b in bodies],
        facts={
            "pull_requests": [pull(50, 20, usage=1000), pull(51, 21, usage=3000)],
            "flow": {"stall_hours": 4},
        },
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[9][0] == "yes"
    assert "2 of 2" in found[9][1] and "2000 tokens per merged" in found[9][1]


@pytest.mark.parametrize(
    "bodies, expected",
    [
        (["Report: a\nUsage: 5 tokens", "Report: b\nUsage: not shown"], "partly"),
        (["Report: a\nUsage: not shown"], "no"),
        ([], "unknown"),
    ],
)
def test_cost_statuses(tmp_path, capsys, bodies, expected):
    document = saved(comments=[comment(50, b, day(9)) for b in bodies])
    assert lines_of(capsys, project(tmp_path, document), tmp_path)[9][0] == expected


def test_cost_a_usage_not_shown_is_not_a_zero(tmp_path, capsys):
    document = saved(
        comments=[comment(50, "Report: a\nUsage: not shown", day(9))],
        facts={"pull_requests": [pull(usage="unknown")], "flow": {"stall_hours": 4}},
    )
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "tokens per merged unknown" in found[9][1]


def test_the_window_leaves_out_older_records(tmp_path, capsys):
    """REQ-054: brief #799 answer 1 (`--days`)."""
    old = "2026-03-01T08:00:00Z"
    document = saved(comments=[assign(20, at=old), *takes(20, at=old)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path, "--days", "2")
    assert found[2][0] == "unknown"  # nothing was taken in the window
    found = lines_of(capsys, project_again(tmp_path), tmp_path, "--days", "30")
    assert found[2][0] == "yes"


def project_again(tmp_path: Path) -> Path:
    return tmp_path / "project"


@pytest.mark.parametrize("days", ["0", "-1", "x"])
def test_bad_days_is_a_usage_error(tmp_path, days):
    assert checklist.main(["--root", str(project(tmp_path)), "--days", days]) == 2


def test_a_threshold_is_read_from_the_table(tmp_path, capsys):
    """REQ-054: brief #799 answer 3."""
    document = saved(comments=[*takes(20, 21), report(2)])
    toml = "[checklist]\ncapacity_use = 0.75\n"
    assert lines_of(capsys, project(tmp_path, document, toml), tmp_path)[1][0] == "partly"


@pytest.mark.parametrize(
    "toml, setting",
    [
        ("[checklist]\nnope = 1\n", "checklist.nope"),
        ('[checklist]\ncapacity_use = "lots"\n', "checklist.capacity_use"),
        ("[checklist]\ncapacity_use = 1.5\n", "checklist.capacity_use"),
        ("[checklist]\nidle_minutes = -1\n", "checklist.idle_minutes"),
        ("[checklist]\nparallel_peak = true\n", "checklist.parallel_peak"),
    ],
)
def test_a_bad_table_is_refused_naming_the_setting_never_the_value(tmp_path, capsys, toml, setting):
    """REQ-054: brief #799 answer 3."""
    code = checklist.main(["--root", str(project(tmp_path, saved(), toml))])
    assert code == 1
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert setting in text
    assert "lots" not in text and "1.5" not in text


def test_a_table_that_is_not_a_table_is_refused(tmp_path, capsys):
    root = project(tmp_path, saved())
    (root / "agk.toml").write_text('checklist = "x"\n', encoding="utf-8")
    assert checklist.main(["--root", str(root)]) == 1
    assert "checklist" in capsys.readouterr().out


def test_personal_mode_says_why_each_point_is_unknown(tmp_path, capsys):
    """REQ-054: brief #799 answer 4."""
    root = project(tmp_path, saved(comments=[*takes(20), report(1)]))
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    found = lines_of(capsys, root, tmp_path)
    assert {status for status, _ in found.values()} == {"unknown"}
    assert all("personal mode" in measure for _, measure in found.values())


def test_local_mode_cannot_read_ci_runs(tmp_path, capsys):
    """REQ-054: brief #799 answer 4: no Actions runs, the rest still measured."""
    document = saved(local_mode=True, pr_tests=LINE_75, comments=[*takes(20, 21), report(2)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[3][0] == "unknown" and "local mode" in found[3][1]
    assert found[5][0] == "unknown" and "local mode" in found[5][1]
    assert found[1][0] == "yes"


def test_a_saved_file_that_is_not_json_is_unknown_not_a_crash(tmp_path, capsys):
    root = project(tmp_path)
    (tmp_path / "saved.json").write_text("{", encoding="utf-8")
    found = lines_of(capsys, root, tmp_path)
    assert {status for status, _ in found.values()} == {"unknown"}


def test_it_reads_only_the_standard_library_and_common():
    """REQ-054: brief #799 answer 1: no network call, nothing but common.py."""
    source = (KIT_ROOT / "scripts" / "agk" / "checklist.py").read_text(encoding="utf-8")
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    assert names <= {"__future__", "argparse", "json", "re", "sys", "tomllib", "common"} | {
        "datetime",
        "pathlib",
        "typing",
    }
    assert '"gh"' not in source


def test_it_writes_nothing(tmp_path, capsys):
    """REQ-054: brief #799 answer 1."""
    root = project(tmp_path, saved(comments=takes(20)))
    before = sorted(p for p in tmp_path.rglob("*"))
    lines_of(capsys, root, tmp_path)
    assert sorted(p for p in tmp_path.rglob("*")) == before


# --- the saving step in metrics.py ------------------------------------------------------------


WEEKLY_BODY = "\n".join(["x", FULL_SUITE, LINE_75, MEDIAN_FAST, "y", ""])


def api_dir(tmp_path: Path, weekly: str = WEEKLY_BODY, more: dict | None = None) -> Path:
    folder = tmp_path / "api"
    folder.mkdir()
    responses = {
        "comments-checklist": [comment(7, "Report: a\nUsage: 5 tokens", day(9))],
        "runs-checklist": {
            "workflow_runs": [
                {
                    "name": "merger",
                    "status": "completed",
                    "conclusion": "failure",
                    "created_at": day(9),
                    "id": 1,
                }
            ]
        },
        "checklist-briefs": [
            {"number": 3, "created_at": day(1), "closed_at": None, "body": "Depends-on: #2"},
            {"number": 4, "created_at": day(1), "closed_at": None, "pull_request": {}},
        ],
        "issues-checklist-metrics": [{"body": weekly}],
        "checklist-open": [
            {"number": 2, "title": "Local mode since 2026-03-01", "labels": []},
            {
                "number": CONDUCTOR_ISSUE,
                "title": "Conductor",
                "labels": [{"name": "agk-conductor"}],
            },
        ],
    }
    for name, body in {**responses, **(more or {})}.items():
        (folder / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")
    return folder


def test_the_save_step_writes_the_document_checklist_reads(tmp_path, monkeypatch):
    """REQ-054: brief #799 answer 1: GET only, one file, never a commit."""
    import facts

    monkeypatch.setattr(facts, "build", lambda *a, **k: {"pull_requests": [], "flow": {}})
    target = tmp_path / "saved.json"
    src = metrics.ApiDir(api_dir(tmp_path))
    metrics.save_checklist(src, tmp_path, "o/r", 7, target, SAVED_AT)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["saved_at"] == SAVED_AT
    assert document["facts"] == {"pull_requests": [], "flow": {}}
    assert document["comments"][0]["body"].startswith("Report:")
    assert document["runs"] == [{"name": "merger", "conclusion": "failure", "created_at": day(9)}]
    assert [b["number"] for b in document["briefs"]] == [3]  # a pull request is not a brief
    assert document["pr_tests"] == LINE_75
    assert document["local_mode"] is True


def test_the_save_step_keeps_authors_the_conductor_issue_and_the_weekly_medians(
    tmp_path, monkeypatch
):
    """REQ-054: brief #981 answers 1 and 2: what points 2 and 3 read, from the same GETs."""
    import facts

    monkeypatch.setattr(facts, "build", lambda *a, **k: {"pull_requests": [], "flow": {}})
    monkeypatch.setattr(metrics, "verdict_authors", lambda root: [CONDUCTOR])
    target = tmp_path / "saved.json"
    metrics.save_checklist(metrics.ApiDir(api_dir(tmp_path)), tmp_path, "o/r", 7, target, SAVED_AT)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["comments"][0]["author"] == "builder-example"
    assert document["verdict_authors"] == [CONDUCTOR]
    assert document["conductor_issues"] == [CONDUCTOR_ISSUE]
    assert document["pr_tests_median"] == MEDIAN_FAST
    assert document["full_suite"] == FULL_SUITE
    assert document["window_tests"] is None  # a weekly line with runs needs no window figures


def test_with_no_weekly_line_the_save_step_keeps_the_windows_figures(tmp_path, monkeypatch):
    """REQ-054: brief #981 answer 2: the figures metrics.py writes, for the pull requests closed
    in the window, read with its own GETs (no new reader)."""
    import facts

    monkeypatch.setattr(facts, "build", lambda *a, **k: {"pull_requests": [], "flow": {}})
    seen = []

    def lines(ctx, details):
        seen.append([d["number"] for d in details])
        return (LINE_75, "most", MEDIAN_FAST, "reasons")

    monkeypatch.setattr(metrics, "pr_tests_lines", lines)
    monkeypatch.setattr(metrics, "full_suite_line", lambda ctx, details: FULL_SUITE)
    listing = [
        {"number": 50, "closed_at": day(9), "updated_at": day(9)},
        {"number": 49, "closed_at": "2026-02-01T00:00:00Z", "updated_at": "2026-02-01T00:00:00Z"},
    ]
    more = {"pulls": listing, "pull-50": {"number": 50, "merged_at": day(9)}}
    target = tmp_path / "saved.json"
    folder = api_dir(tmp_path, weekly="no lines here", more=more)
    metrics.save_checklist(metrics.ApiDir(folder), tmp_path, "o/r", 7, target, SAVED_AT)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["pr_tests"] is None
    assert seen == [[50]]  # only the pull request closed in the window
    assert document["window_tests"] == {
        "pr_tests": LINE_75,
        "pr_tests_median": MEDIAN_FAST,
        "full_suite": FULL_SUITE,
    }


def test_save_leaves_unread_parts_unknown_not_empty(tmp_path, monkeypatch):
    import facts

    monkeypatch.setattr(facts, "build", lambda *a, **k: {"pull_requests": "unknown"})
    empty = tmp_path / "none"
    empty.mkdir()
    target = tmp_path / "saved.json"
    metrics.save_checklist(metrics.ApiDir(empty), tmp_path, "o/r", 7, target, SAVED_AT)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["comments"] is None and document["runs"] is None
    assert document["briefs"] is None and document["pr_tests"] is None
    assert document["conductor_issues"] is None and document["window_tests"] is None


def test_save_args_are_read(tmp_path):
    parsed = metrics.parse_args(["--save-checklist", "--to", "f", "--days", "3"])
    assert parsed["save"] is True and parsed["to"] == "f" and parsed["days"] == 3


def test_save_refuses_a_bad_days():
    assert metrics.parse_args(["--save-checklist", "--days", "0"]) is None


# --- wiring: the report and the kit ------------------------------------------------------------


def test_the_conductor_report_ends_with_the_nine_lines():
    """REQ-054: brief #799 answer 5."""
    role = (KIT_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    found = [
        s
        for line in role.splitlines()
        for s in re.split(r"(?<=\.)\s+", line)
        if "scripts/agk/checklist.py" in s
    ]
    assert len(found) == 1
    assert "every hourly report ends with" in found[0]
    assert "AGK-NINE-CHECKLIST" in found[0]
    assert "metrics.py --save-checklist" in found[0]


def test_the_kit_installs_the_command_and_its_test():
    """REQ-054: brief #799 answer 4."""
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/checklist.py" in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
    guide = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "checklist.py" in guide and "[checklist]" in guide
