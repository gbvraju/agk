"""The nine-point operations checklist (brief #799, REQ-054, ADR-0374).

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


def comment(issue: int, body: str, at: str) -> dict:
    return {
        "issue_url": f"https://api.example.com/repos/o/r/issues/{issue}",
        "body": body,
        "created_at": at,
        "user": {"login": "builder@example.com"},
    }


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


def test_conductor_share_is_starts_over_takes(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (2)."""
    document = saved(comments=[*takes(20, 21, 22, 23), report(1)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "partly"
    assert "1 of 4" in found[2][1] and "25%" in found[2][1]


def test_conductor_share_yes_and_stalls_replaced_counted(tmp_path, capsys):
    retake = comment(21, "taken: s9 2026-03-10 retakes", day(8))
    document = saved(comments=[*takes(20), retake, report(2)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert found[2][0] == "yes"
    assert "stalls replaced 1" in found[2][1]


def test_a_takeover_counts_as_a_stall_replaced(tmp_path, capsys):
    over = comment(21, "taken over: s9 2026-03-10", day(8))
    document = saved(comments=[*takes(20), over, report(2)])
    found = lines_of(capsys, project(tmp_path, document), tmp_path)
    assert "stalls replaced 1" in found[2][1]


def test_conductor_share_no_when_it_started_none(tmp_path, capsys):
    document = saved(comments=[*takes(20), report(0)])
    assert lines_of(capsys, project(tmp_path, document), tmp_path)[2][0] == "no"


def test_conductor_share_unknown_without_a_report(tmp_path, capsys):
    found = lines_of(capsys, project(tmp_path, saved(comments=takes(20))), tmp_path)
    assert found[2][0] == "unknown"


def test_a_report_on_another_issue_is_not_read(tmp_path, capsys):
    stray = comment(99, "Conductor report x\nBuilders started (9): a.", day(9))
    found = lines_of(capsys, project(tmp_path, saved(comments=[*takes(20), stray])), tmp_path)
    assert found[2][0] == "unknown"


LINE_75 = (
    "pr tests: 12 runs; selected 9 of 12 (75%); test step 31.5 minutes; "
    "full: always_full 3; unknown: 0"
)


def test_tests_share_and_minutes_from_the_weekly_line(tmp_path, capsys):
    """REQ-054: brief #799 answer 2 (3)."""
    found = lines_of(capsys, project(tmp_path, saved(pr_tests=LINE_75)), tmp_path)
    assert found[3][0] == "yes"
    assert "9 of 12" in found[3][1] and "31.5 minutes" in found[3][1]


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
    assert lines_of(capsys, project(tmp_path, saved(pr_tests=line)), tmp_path)[3][0] == expected


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
    document = saved(comments=[*takes(20, at="2026-03-01T08:00:00Z"), report(1)])
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


def api_dir(tmp_path: Path) -> Path:
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
        "issues-checklist-metrics": [{"body": "x\n" + LINE_75 + "\ny\n"}],
        "checklist-open": [{"title": "Local mode since 2026-03-01"}],
    }
    for name, body in responses.items():
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
