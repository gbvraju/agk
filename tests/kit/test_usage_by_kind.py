"""The usage line of a builder's `Report:` and the sums by kind (SPEC-0045 rules 8 and 9).

REQ-052 AC7 and AC8, brief #710 (build (d) of SPEC-0045, ADR-0289). Session rule 17 says that a
builder's `Report:` line ends with `Usage: <n> tokens`, or `Usage: not shown`, which counts as not
reported and never as 0. `metrics.py --usage-by-kind FACTS` reads a saved facts document and each
merged pull request's brief (one GET each), and prints, per kind of rule 4, the merged pull
requests, the summed and per-pull-request tokens with the `not reported` count, the lead time and
the fix-list verdicts per merged pull request; `--before DAY` and `--after DAY` print the 7 days
before and after a day. It writes no file, posts nothing and exits 0. Saved facts and briefs
(`--api-dir`) or a `gh` stub on `PATH`, invented data, no network. The tests were written first.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = (
    "constitution/\nconfig/\n.claude/\n.github/\ndocs/requirements.md\nscripts/agk/\ntests/kit/\n"
)


def brief(size: str, touches: str) -> dict:
    body = f'Sentence: "A widget shows its price."\n\nSize: {size}\nTouches: {touches}\n'
    return {"number": 0, "body": body}


BRIEFS = {
    11: brief("S", "tests/kit/**"),  # small
    12: brief("M", "src/**"),  # build
    13: brief("S", "docs/specs/**"),  # design
}


def pull(number, brief_n, usage, created, merged, verdicts=(), state="merged"):
    body_brief = brief_n
    return {
        "number": number,
        "state": state,
        "created_at": created,
        "merged_at": merged if state == "merged" else None,
        "closed_at": merged,
        "usage": usage,
        "brief": body_brief,
        "verdicts": [{"kind": k, "sha": "a" * 40, "at": merged} for k in verdicts],
        "title": f"pull request {number}",
    }


PULLS = [
    pull(1, 11, 1200, "2026-10-20T08:00:00Z", "2026-10-20T10:00:00Z", ("fix", "cleared")),
    pull(2, 11, "not-reported", "2026-10-21T08:00:00Z", "2026-10-21T12:00:00Z", ("cleared",)),
    pull(3, 12, 3000, "2026-10-22T08:00:00Z", "2026-10-23T08:00:00Z", ("fix", "fix", "cleared")),
    pull(4, 13, "unknown", "2026-10-23T08:00:00Z", "2026-10-23T09:00:00Z", ("cleared",)),
    pull(5, None, 500, "2026-10-24T08:00:00Z", "2026-10-24T09:30:00Z", ("cleared",)),
    pull(6, 12, 9999, "2026-10-24T08:00:00Z", "2026-10-25T08:00:00Z", (), state="closed"),
    # after: the week from 2026-11-02
    pull(7, 11, 400, "2026-11-02T08:00:00Z", "2026-11-02T09:00:00Z", ("cleared",)),
    pull(8, 11, 200, "2026-11-03T08:00:00Z", "2026-11-03T11:00:00Z", ("cleared",)),
]


def facts_doc(pulls=None) -> dict:
    return {"schema": 1, "today": "2026-11-08", "pull_requests": PULLS if pulls is None else pulls}


@pytest.fixture
def setup(repo, tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    repo.write("config/protected-paths.txt", PROTECTED)
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer]\n")
    api = data / "api"
    api.mkdir()
    for n, item in BRIEFS.items():
        (api / f"issue-{n}.json").write_text(json.dumps(item | {"number": n}), encoding="utf-8")
    facts = data / "facts.json"
    facts.write_text(json.dumps(facts_doc()), encoding="utf-8")
    return repo, api, facts


def by_kind(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        found = re.match(r"(design|build|small|none): (.*)", line)
        if found:
            out[found.group(1)] = found.group(2)
    return out


def run(repo, *args, **env):
    return repo.run("metrics.py", "--usage-by-kind", *args, **env)


# --- rule 8: the line of the builder instructions -------------------------------------------------


def test_ac7_session_rule_17_ends_a_report_with_the_usage_or_not_shown():
    """REQ-052 AC7: rule 8, the `Report:` form of the builder instructions."""
    text = (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    rule = next(x for x in text.splitlines() if x.startswith("17. "))
    assert "`Usage: <n> tokens`" in rule and "`Usage: not shown`" in rule
    assert "not reported" in rule and "never 0" in rule


@pytest.mark.parametrize(
    "first, expected",
    [
        ("Report: abc1234 ready for review; CI pending. Usage: 1200 tokens", 1200),
        ("Report: abc1234 ready for review; CI pending. Usage: not shown", "not-reported"),
        ("Report: abc1234 ready for review; CI pending.", "not-reported"),
    ],
)
def test_ac7_a_report_with_not_shown_or_no_usage_is_not_reported_never_0(first, expected):
    """REQ-052 AC7: rule 8, the reader of SPEC-0033 rule 8."""
    import metrics

    comment = {"id": 1, "body": first, "user": {"login": "builder"}}
    assert metrics.usage_of([comment], "builder") == expected


# --- rule 8: the sums per kind --------------------------------------------------------------------


def test_ac7_the_sums_per_kind_count_not_reported_and_never_0(setup):
    """REQ-052 AC7: rule 8."""
    repo, api, facts = setup
    proc = run(repo, str(facts), "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    kinds = by_kind(proc.stdout)
    assert kinds["small"].startswith("4 merged; tokens 1800 (600 per reported pull request; 1 not")
    assert kinds["build"].startswith("1 merged; tokens 3000 (3000 per reported pull request; 0 not")
    assert kinds["design"].startswith("1 merged; tokens not reported (1 not reported)")
    assert kinds["none"].startswith("1 merged; tokens 500 (500 per reported pull request; 0 not")
    assert "9999" not in proc.stdout  # a closed pull request is not merged
    assert " 0 tokens" not in proc.stdout and "tokens 0" not in proc.stdout


def test_ac7_an_unreadable_brief_gives_design_never_a_lower_kind(setup):
    """REQ-052 AC7: rule 8 with rule 4's reading of an unreadable brief."""
    repo, api, facts = setup
    (api / "issue-12.json").unlink()
    kinds = by_kind(run(repo, str(facts), "--api-dir", str(api)).stdout)
    assert kinds["design"].startswith(
        "2 merged; tokens 3000 (3000 per reported pull request; 1 not"
    )
    assert kinds["build"] == "0 merged"


def test_ac7_the_facts_and_the_report_are_unchanged(setup):
    """REQ-052 AC7: rule 8, no field added to the facts, `report.json` keeps its schema."""
    import facts
    import product_report

    assert facts.SCHEMA == 1 and product_report.REPORT_SCHEMA == 9

    class Src:
        def get(self, name, endpoint, until=None):
            return [] if name.startswith(("comments-", "files-", "commits-")) else None

    item = {"number": 7, "head": {"sha": "d" * 40}, "created_at": "2026-10-06T09:00:00Z"}
    item |= {"state": "open", "title": "t", "body": "", "merged_at": None, "user": {"login": "b"}}
    record = facts.pull_record(Src(), item, ["reviewer"])
    assert "kind" not in record and "usage" in record  # the kind is read from the brief, not stored


def test_ac7_a_facts_file_that_is_not_json_is_refused_naming_the_path_class(setup, tmp_path):
    """REQ-052 AC7: rule 8, a refusal names the path class, never the value."""
    repo, api, _ = setup
    bad = tmp_path / "bad.json"
    bad.write_text("not json 4242", encoding="utf-8")
    proc = run(repo, str(bad), "--api-dir", str(api))
    assert proc.returncode == 1 and "path class: facts file" in proc.stdout
    assert "4242" not in proc.stdout


def test_ac7_unread_pull_requests_print_unknown_and_exit_0(setup, tmp_path):
    """REQ-052 AC7: rule 8, unknown, never 0."""
    repo, api, _ = setup
    doc = tmp_path / "unread.json"
    doc.write_text(json.dumps({"schema": 1, "pull_requests": "unknown"}), encoding="utf-8")
    proc = run(repo, str(doc), "--api-dir", str(api))
    assert proc.returncode == 0 and "unknown" in proc.stdout and "merged" not in proc.stdout


# --- rule 9: before and after ---------------------------------------------------------------------


def test_ac8_the_weeks_before_and_after_print_lead_time_and_rework_per_kind(setup):
    """REQ-052 AC8: rule 9."""
    repo, api, facts = setup
    proc = run(
        repo, str(facts), "--api-dir", str(api), "--before", "2026-10-26", "--after", "2026-11-02"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    before, after = proc.stdout.split("after:", 1)
    assert "before: 2026-10-19 to 2026-10-25" in before and "2026-11-02 to 2026-11-08" in after
    small_before = by_kind(before)["small"]
    assert small_before.startswith("2 merged; tokens 1200 (1200 per reported pull request; 1 not")
    assert "lead time 3.0 hours" in small_before  # (2 + 4) / 2
    assert "fix-list verdicts 0.50 per merged pull request" in small_before
    build_before = by_kind(before)["build"]
    assert "lead time 24.0 hours" in build_before and "fix-list verdicts 2.00 per" in build_before
    small_after = by_kind(after)["small"]
    assert small_after.startswith("2 merged; tokens 600 (300 per reported pull request; 0 not")
    assert "lead time 2.0 hours" in small_after and "fix-list verdicts 0.00 per" in small_after
    assert by_kind(after)["build"] == "0 merged"


def test_ac8_unread_verdicts_or_times_make_the_figure_unknown_never_0(setup, tmp_path):
    """REQ-052 AC8: rule 9."""
    repo, api, _ = setup
    one = pull(1, 11, 100, "2026-10-20T08:00:00Z", "2026-10-20T10:00:00Z")
    one["verdicts"] = "unknown"
    two = pull(2, 11, 100, "not a time", "2026-10-21T10:00:00Z")
    doc = tmp_path / "odd.json"
    doc.write_text(json.dumps(facts_doc([one, two])), encoding="utf-8")
    small = by_kind(run(repo, str(doc), "--api-dir", str(api)).stdout)["small"]
    assert "lead time unknown" in small and "fix-list verdicts unknown" in small


@pytest.mark.parametrize("bad", [["--before", "2026-13-01"], ["--after", "soon"], ["--before"]])
def test_ac8_a_malformed_day_prints_the_usage_and_exits_2(setup, bad):
    """REQ-052 AC8: rule 9."""
    repo, api, facts = setup
    proc = run(repo, str(facts), "--api-dir", str(api), *bad)
    assert proc.returncode == 2 and "usage: metrics.py" in proc.stderr


def test_ac8_the_command_writes_no_file_and_reads_with_get_only(setup, tmp_path_factory):
    """REQ-052 AC8: rule 9, it prints and blocks nothing; a `gh` stub serves the briefs."""
    repo, api, facts = setup
    outside = tmp_path_factory.mktemp("stub")
    bin_dir = outside / "bin"
    bin_dir.mkdir()
    calls = outside / "calls.txt"
    stub = bin_dir / "gh"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys\n"
        f"pathlib.Path({str(calls)!r}).open('a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        "n = sys.argv[-1].rsplit('/', 1)[-1]\n"
        f"f = pathlib.Path({str(api)!r}) / f'issue-{{n}}.json'\n"
        "sys.exit(1) if not f.is_file() else print(f.read_text())\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    before = sorted(p.relative_to(repo.root) for p in repo.root.rglob("*") if ".git" not in p.parts)
    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    proc = run(repo, str(facts), "--repo", "example/widgets", **env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert by_kind(proc.stdout)["build"].startswith("1 merged; tokens 3000")
    lines = calls.read_text(encoding="utf-8").splitlines()
    assert lines and all(
        x.startswith("api --method GET repos/example/widgets/issues/") for x in lines
    )
    assert len(lines) == len(set(lines)) == 3  # one read per brief
    after = sorted(p.relative_to(repo.root) for p in repo.root.rglob("*") if ".git" not in p.parts)
    assert before == after
