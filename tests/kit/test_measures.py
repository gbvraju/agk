"""Tests of scripts/agk/measures.py: the measures of each delivered feature for a date range.

Brief #1557, ADR-0659, amendment 191 (SPEC-0007). REQ-012 AC2: the record of a pull request also
carries what it took. Saved API responses, a saved git tree and a stub sidecar in `tmp_path` only;
invented data (example.com, `member-example-1`); no network, no model and no `gh`.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import personal_state as ps  # noqa: E402
from common import MERGED_BY  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
BUILDER = "member-example-1"
OWNER = "member-example-2"
REVIEWER = "reviewer"
APP = {"slug": "claude"}
NAMES = ("example.com", BUILDER, OWNER, "Widget", "frobnicate", "feature-branch", "secret-word")


def at(day: int, hour: int = 9, minute: int = 0) -> str:
    return f"2026-10-{day:02d}T{hour:02d}:{minute:02d}:00Z"


def comment(cid: int, who: str, when: str, body: str, app: bool = True) -> dict:
    return {
        "id": cid,
        "user": {"login": who},
        "created_at": when,
        "updated_at": when,
        "body": body,
        "performed_via_github_app": APP if app else None,
    }


class Api:
    """A saved GitHub: briefs, pull requests, their comments and events, written as JSON."""

    def __init__(self, root: Path) -> None:
        self.path = root / "api"
        self.path.mkdir(parents=True)
        self.pulls: list[dict] = []
        self.issues: list[dict] = []

    def put(self, name: str, data: object) -> None:
        (self.path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
        (self.path / "pulls.json").write_text(json.dumps(self.pulls), encoding="utf-8")

    def brief(self, n: int, created: str, comments: list[dict], state: str = "closed") -> None:
        body = "Widget frobnicate secret-word at https://example.com\nSize: M\n"
        self.put(f"issue-{n}", {"number": n, "title": "Widget", "body": body, "state": state,
                                "created_at": created, "user": {"login": OWNER}})  # fmt: skip
        self.put(f"comments-{n}", comments)

    def pull(self, n: int, brief: int | None, opened: str, closed: str, merge: str | None,
             comments: list[dict], finishes: bool = False) -> None:  # fmt: skip
        lines = [f"Brief: #{brief}" if brief else "Brief: none (design)", "Summary: a Widget"]
        if finishes:
            lines.append(f"Finishes: #{brief}")
        detail = {
            "number": n, "title": "Widget frobnicate", "body": "\n".join(lines),
            "user": {"login": BUILDER}, "created_at": opened, "closed_at": closed,
            "merged_at": closed if merge else None, "merge_commit_sha": merge,
            "head": {"sha": f"{n:04d}" + "a" * 36, "ref": "feature-branch"},
            "base": {"sha": "b" * 40, "ref": "main"},
        }  # fmt: skip
        self.pulls.append({k: detail[k] for k in ("number", "closed_at", "merged_at")}
                          | {"updated_at": closed})  # fmt: skip
        self.put(f"pull-{n}", detail)
        self.put(f"comments-{n}", comments)


def taken(cid: int, when: str) -> dict:
    return comment(cid, BUILDER, when, "taken: cb1 2026-10-02")


def report(cid: int, when: str, tokens: int, what: str = "ready for review") -> dict:
    return comment(cid, BUILDER, when, f"Report: abc1234 {what}\n\nUsage: {tokens} tokens")


def report_line(cid: int, when: str, tokens: int, what: str = "ready for review") -> dict:
    return comment(cid, BUILDER, when, f"Report: abc1234 {what}; Usage: {tokens} tokens")


def verdict(cid: int, when: str, text: str) -> dict:
    return comment(cid, REVIEWER, when, f"Verdict: {text}")


@pytest.fixture
def setup(repo, tmp_path):
    repo.write("config/reviewers.yaml", f"version: 1\nverdict_authors: [{REVIEWER}]\n")
    repo.write("agk.toml", 'agent_apps = ["claude"]\n')
    repo.commit({"README.md": "x\n"}, "start")
    return repo, Api(tmp_path)


def feature(repo, api: Api) -> None:
    """Brief 50: two pull requests (one fix list, one reopen), finished by #61; a follow-up #62;
    #61 is a guarded merge and #60 a hand merge; the owner approves, asks and is answered."""
    hand = repo.git("rev-parse", "HEAD").strip()
    repo.commit({"b.txt": "b\n"}, f"guarded\n\n{MERGED_BY}")
    guarded = repo.git("rev-parse", "HEAD").strip()
    api.brief(50, at(1, 9), [
        taken(1, at(1, 11)),
        comment(2, OWNER, at(2, 9), "Approve: design 1 abc", app=False),
        comment(3, REVIEWER, at(1, 13), "Correction: read rule 2 again"),
        taken(4, at(2, 13)),
    ])  # fmt: skip
    api.pull(60, 50, at(1, 12), at(2, 12), hand, [
        report_line(10, at(1, 14), 1000),
        verdict(11, at(1, 15), "fix list"),
        report_line(12, at(1, 16), 500, "fix list applied"),
        verdict(13, at(1, 17), "cleared 0060aaa"),
    ])  # fmt: skip
    api.pull(61, 50, at(2, 13), at(3, 13), guarded, [
        comment(20, BUILDER, at(2, 14), "Question: Q-50-1 for the maintainers: which?"),
        comment(21, REVIEWER, at(2, 14, 30), "Maintainer answer: Q-50-1 this one\n\n"
                "Owner said (2026-10-02 14:20 UTC): \"this one\""),
        report_line(22, at(2, 15), 2000),
        verdict(23, at(2, 17), "cleared 0061aaa"),
    ], finishes=True)  # fmt: skip
    api.put("events-50", [])
    api.put("events-60", [{"event": "labeled", "created_at": at(1, 13)}])
    api.put("events-61", [{"event": "reopened", "created_at": at(2, 14)}])
    api.pull(62, 50, at(4, 9), at(4, 12), guarded, [report_line(30, at(4, 10), 300)])


def measures(repo, api: Api, *args: str, start: str = "2026-10-01", end: str = "2026-10-31"):
    return repo.run("measures.py", "--from", start, "--to", end, "--api-dir", str(api.path), *args)


def row(text: str, prefix: str) -> dict[str, str]:
    found = [x for x in text.splitlines() if x.startswith(prefix)]
    assert len(found) == 1, text
    cells = [c.split(" ", 1) for c in found[0][len(prefix) :].split("; ")]
    return {c[0]: c[1] if len(c) > 1 else "" for c in cells}


def test_req_012_ac2_a_feature_of_two_pull_requests(setup):
    """REQ-012 AC2: brief #1557 answers 2 to 4, 6 and 8 (one row per feature, rework and spend)."""
    repo, api = setup
    feature(repo, api)
    proc = measures(repo, api)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = row(proc.stdout, "feature #50: ")
    assert got["pulls"] == "#60 #61"
    assert (got["lead_hours"], got["queue_hours"], got["build_hours"]) == ("52.0", "2.0", "50.0")
    assert got["builder_hours"] == "5.5"  # 4.0 on #60, 1.5 on #61 (the wait on the question not)
    assert (got["fix_rounds"], got["rejected"], got["corrections"]) == ("1", "0", "1")
    assert (got["reopened"], got["follow_ups"], got["first_review_pass"]) == ("1", "1", "no")
    assert got["tokens"] == "3500"
    assert got["cost"] == "not priced"
    assert got["hand_merges"].split(" ")[0] == "1"
    assert (got["owner_questions"], got["owner_wait_minutes"]) == ("1", "30")
    assert got["owner_lines"] == "2"  # the Approve: and the relayed Owner said ( line
    assert row(proc.stdout, "totals: ")["features"] == "1"


def test_req_012_ac2_the_json_form_has_the_same_rows(setup):
    """REQ-012 AC2: brief #1557 answer 9 (`--json` gives the same rows, the same field names)."""
    repo, api = setup
    feature(repo, api)
    text = measures(repo, api).stdout
    data = json.loads(measures(repo, api, "--json").stdout)
    assert data["range"] == {"from": "2026-10-01", "to": "2026-10-31"}
    (one,) = data["features"]
    assert {k: v for k, v in one.items() if k != "brief"} == row(text, "feature #50: ")
    assert data["totals"] == row(text, "totals: ")


def test_req_012_ac2_no_name_or_text_reaches_the_output(setup):
    """REQ-012 AC2: brief #1557 answer 9 (numbers only: no title, body, login, branch or host)."""
    repo, api = setup
    feature(repo, api)
    for args in ((), ("--json",)):
        proc = measures(repo, api, *args)
        assert proc.returncode == 0, proc.stderr
        for word in NAMES:
            assert word.lower() not in proc.stdout.lower(), word


def test_req_012_ac2_two_runs_are_byte_identical(setup):
    """REQ-012 AC2: brief #1557 answer 1 (the same input gives the same bytes)."""
    repo, api = setup
    feature(repo, api)
    assert measures(repo, api).stdout == measures(repo, api).stdout


def test_req_012_ac2_a_range_with_nothing_merged(setup):
    """REQ-012 AC2: brief #1557 answer 12 (rows empty, 0 features, an input-less figure unknown)."""
    repo, api = setup
    feature(repo, api)
    proc = measures(repo, api, start="2026-11-01", end="2026-11-30")
    assert proc.returncode == 0, proc.stderr
    assert "feature #" not in proc.stdout
    totals = row(proc.stdout, "totals: ")
    assert totals["features"] == "0"
    assert totals["lead_hours_median"] == "unknown"
    assert totals["billed_minutes"] == "unknown"  # no run list was saved


@pytest.mark.parametrize(
    ("start", "end", "option"),
    [
        ("2026-10-31", "2026-10-01", "--to"),
        ("2026-13-01", "2026-10-01", "--from"),
        ("2026-10-01", "2027-01-02", "--to"),  # 94 days, over the 92 of Q-1557-2
    ],
)
def test_req_012_ac2_a_refused_range_names_the_option(setup, start, end, option):
    """REQ-012 AC2: brief #1557 answer 1 (a bad range is refused naming the option)."""
    repo, api = setup
    proc = measures(repo, api, start=start, end=end)
    assert proc.returncode != 0
    assert f"option: {option}" in proc.stderr
    assert proc.stdout == ""


def test_req_012_ac2_untied_pull_requests_have_their_own_row(setup):
    """REQ-012 AC2: brief #1557 answer 2 (a pull request with `Brief: none (...)`)."""
    repo, api = setup
    feature(repo, api)
    api.pull(70, None, at(5, 9), at(5, 10), "c" * 40, [])
    assert row(measures(repo, api).stdout, "not tied to a brief: ")["pulls"] == "#70"


def test_req_012_ac2_an_unclosed_brief_is_no_feature_without_finishes(setup):
    """REQ-012 AC2: brief #1557 answer 2 (the last merged pull request finishes a closed brief)."""
    repo, api = setup
    api.brief(51, at(1), [taken(1, at(1, 10))], state="open")
    api.pull(63, 51, at(1, 11), at(1, 12), "d" * 40, [report_line(5, at(1, 11, 30), 10)])
    proc = measures(repo, api)
    assert "feature #51" not in proc.stdout
    api.brief(51, at(1), [taken(1, at(1, 10))], state="closed")
    assert row(measures(repo, api).stdout, "feature #51: ")["pulls"] == "#63"


def test_req_012_ac2_local_mode_minutes_read_none(setup):
    """REQ-012 AC2: brief #1557 answer 7 (`execution = "local"`: none, never 0)."""
    repo, api = setup
    repo.write("agk.toml", 'agent_apps = ["claude"]\nexecution = "local"\n')
    feature(repo, api)
    proc = measures(repo, api)
    got = row(proc.stdout, "feature #50: ")
    assert got["minutes"] == got["pool_minutes"] == "none (local mode)"
    assert row(proc.stdout, "totals: ")["billed_minutes"] == "none (local mode)"


def test_req_012_ac2_one_account_without_an_app_mark_is_unknown(setup):
    """REQ-012 AC2: brief #1557 Q-1557-6 (owner lines cannot be told apart: unknown)."""
    repo, api = setup
    feature(repo, api)
    comments = json.loads((api.path / "comments-60.json").read_text())
    for c in comments:
        c["performed_via_github_app"] = None
    api.put("comments-60", comments)
    assert row(measures(repo, api).stdout, "feature #50: ")["owner_lines"].startswith("unknown")


def step(name: str, conclusion: str = "success") -> dict:
    return {"name": name, "status": "completed", "conclusion": conclusion,
            "started_at": at(3, 9), "completed_at": at(3, 9, 5)}  # fmt: skip


def run_(rid: int, name: str, event: str, conclusion: str, branch: str) -> dict:
    return {"id": rid, "name": name, "event": event, "head_branch": branch, "run_attempt": 1,
            "created_at": at(3, 9), "status": "completed", "conclusion": conclusion}  # fmt: skip


def test_req_012_ac2_an_escape_is_counted_on_its_feature(setup):
    """REQ-012 AC2: brief #1557 answer 5 (`escape_of` over the feature's merged pull requests)."""
    repo, api = setup
    feature(repo, api)
    detail = json.loads((api.path / "pull-61.json").read_text())
    head, merge = detail["head"]["sha"], detail["merge_commit_sha"]
    runs = [run_(1, "governance", "pull_request", "success", "feature-branch"),
            run_(2, "proof", "pull_request", "success", "feature-branch")]  # fmt: skip
    api.put(f"runs-{head}", {"total_count": 2, "workflow_runs": runs})
    proof = {"name": "proof", "started_at": at(3, 9), "completed_at": at(3, 9, 5),
             "conclusion": "success", "labels": ["ubuntu-latest"],
             "steps": [step("Run proof"), step("outcome: proven"),
                       step("outcome: not-proven (red-on-head)", "skipped"),
                       step("outcome: skipped", "skipped")]}  # fmt: skip
    api.put("run-jobs-2", {"total_count": 1, "jobs": [proof]})
    push = [run_(3, "governance", "push", "failure", "main")]
    api.put(f"runs-{merge}", {"total_count": 1, "workflow_runs": push})
    got = row(measures(repo, api).stdout, "feature #50: ")
    assert got["escapes"] == "1"
    assert got["red_pushes"] == "0"


def test_req_012_ac2_a_personal_sidecar_is_read_through_the_files_forge(setup, tmp_path):
    """REQ-012 AC2: brief #1557 answer 10 (personal mode: minutes, escapes, owner lines none)."""
    repo, api = setup
    feature(repo, api)
    sidecar = tmp_path / "sidecar"
    ps.make_sidecar(sidecar, REVIEWER)
    forge = sidecar / "forge"
    for kind, numbers in (("issues", (50,)), ("pulls", (60, 61, 62))):
        (forge / kind).mkdir(parents=True, exist_ok=True)
        for n in numbers:
            src = "issue" if kind == "issues" else "pull"
            data = json.loads((api.path / f"{src}-{n}.json").read_text())
            data.setdefault("state", "closed")
            (forge / kind / f"{n}.json").write_text(json.dumps(data))
    for n in (50, 60, 61, 62):
        shutil.copy(api.path / f"comments-{n}.json", forge / f"comments-{n}.json")
    proc = repo.run("measures.py", "--from", "2026-10-01", "--to", "2026-10-31",
                    "--sidecar", str(sidecar))  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = row(proc.stdout, "feature #50: ")
    assert got["pulls"] == "#60 #61"
    for field in ("minutes", "escapes", "owner_lines"):
        assert got[field] == "none (personal mode)"


def test_req_012_ac2_the_weekly_report_is_byte_identical(repo):
    """REQ-012 AC2: brief #1557 answer 11 (SPEC-0007's weekly report does not change)."""
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer, r]\n")
    case = FIXTURES / "fix-lists-cleared"
    proc = repo.run("metrics.py", "--api-dir", str(case), "--today", "2026-10-14")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("agk metrics 2026-W41 (window 2026-10-05 to 2026-10-12)\n")
    assert "measures" not in proc.stdout


def test_req_012_ac2_a_close_a_second_after_the_merge_keeps_the_finish(setup):
    """REQ-012 AC2: brief #1557 answer 2 (GitHub may close a second after the merge; the finishing
    pull request is still the feature's, not a follow-up)."""
    repo, api = setup
    api.brief(52, at(1), [taken(1, at(1, 10))])
    api.pull(64, 52, at(1, 11), at(1, 12), "e" * 40, [report_line(5, at(1, 11, 30), 10)], True)
    detail = json.loads((api.path / "pull-64.json").read_text())
    detail["closed_at"] = "2026-10-01T12:00:01Z"
    api.put("pull-64", detail)
    got = row(measures(repo, api).stdout, "feature #52: ")
    assert (got["pulls"], got["follow_ups"]) == ("#64", "0")
