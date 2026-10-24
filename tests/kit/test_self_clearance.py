"""Tests of the author rule (SPEC-0025 rule 4, REQ-032 AC4). No network, no model, no `gh`.

With two or more listed verdict authors, a verdict by the pull request's own author clears nothing,
covers nothing and is not a review round, for the metrics, the facts and `check_final_clearance.py`.
With one listed author nothing changes.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from facts import pull_record
from metrics import counted_authors

FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
TODAY = "2026-10-14"
ADR = "docs/adr/0001-x.md"


def adr(status: str) -> str:
    return f"# ADR-0001: x\n\n- Status: {status}\n- Date: 2026-10-22\n"


@pytest.mark.parametrize(
    ("authors", "own", "expected"),
    [
        (["a", "b"], "a", ["b"]),
        (["@A", "b"], "a", ["b"]),
        (["a", "b"], "c", ["a", "b"]),
        (["a"], "a", ["a"]),
        (["a", "A"], "a", ["a", "A"]),
        (["a", "b"], "", ["a", "b"]),
        (["a", "b"], None, ["a", "b"]),
        ([], "a", []),
        (None, "a", None),
    ],
)
def test_ac4_counted_authors_drops_the_own_author_only_with_two_or_more_listed(
    authors, own, expected
):
    """REQ-032 AC4: rule 4 (logins compare without case; one listed author changes nothing)."""
    assert counted_authors(authors, own) == expected


# --- the metrics ----------------------------------------------------------------------------------


def metrics_row(repo, tmp_path: Path, listed: str, author: str | None) -> dict[str, str]:
    api = tmp_path / "api"
    shutil.copytree(FIXTURES / "fix-lists-cleared", api)
    if author:
        pull = json.loads((api / "pull-102.json").read_text())
        pull["user"] = {"login": author}
        (api / "pull-102.json").write_text(json.dumps(pull))
    repo.write("config/reviewers.yaml", f"version: 1\nverdict_authors: [{listed}]\n")
    proc = repo.run("metrics.py", "--api-dir", str(api), "--today", TODAY)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    row = next(ln for ln in lines[2:] if ln.strip("| ").startswith("102"))
    return dict(zip(header, [c.strip() for c in row.strip("|").split("|")], strict=True))


def test_ac4_the_metrics_ignore_the_own_authors_verdicts_with_two_listed(repo, tmp_path):
    """REQ-032 AC4: rule 4 (no round, no clearance: the other author wrote no verdict)."""
    row = metrics_row(repo, tmp_path, "reviewer, other", "reviewer")
    assert (row["review_rounds"], row["merged_head_cleared"]) == ("unknown", "unknown")


def test_ac4_the_metrics_count_the_other_authors_verdicts(repo, tmp_path):
    """REQ-032 AC4: rule 4 (a pull request by someone else keeps both rounds and its clearance)."""
    row = metrics_row(repo, tmp_path, "reviewer, other", "someone")
    assert (row["review_rounds"], row["merged_head_cleared"]) == ("2", "yes")


def test_ac4_with_one_listed_author_the_metrics_do_not_change(repo, tmp_path):
    """REQ-032 AC4: rule 4 (a single listed author may clear their own pull request)."""
    row = metrics_row(repo, tmp_path, "reviewer", "reviewer")
    assert (row["review_rounds"], row["merged_head_cleared"]) == ("2", "yes")


def test_ac4_a_pull_request_without_a_user_changes_nothing(repo, tmp_path):
    """REQ-032 AC4: rule 4 (no author login in the record: nothing is dropped)."""
    row = metrics_row(repo, tmp_path, "reviewer, other", None)
    assert (row["review_rounds"], row["merged_head_cleared"]) == ("2", "yes")


# --- the facts ------------------------------------------------------------------------------------


class Src:
    """A record source that holds only the comments of one pull request."""

    def __init__(self, comments: list[dict]) -> None:
        self.comments = comments

    def get(self, name: str, endpoint: str):
        return self.comments if name == "comments-7" else None


def verdict_comment(login: str, at: int) -> dict:
    return {
        "body": "Verdict: fix list abc1234\n",
        "created_at": f"2026-10-06T10:{at:02d}:00Z",
        "user": {"login": login},
    }


def facts_verdicts(login: str | None, listed: list[str]) -> object:
    item = {"number": 7, "state": "open", "head": {"sha": ""}}
    if login:
        item["user"] = {"login": login}
    comments = [verdict_comment("reviewer", 0), verdict_comment("other", 1)]
    return pull_record(Src(comments), item, listed)["verdicts"]


def test_ac4_the_facts_drop_the_own_authors_verdict_with_two_listed():
    """REQ-032 AC4: rule 4."""
    found = facts_verdicts("reviewer", ["reviewer", "other"])
    assert [v["at"] for v in found] == ["2026-10-06T10:01:00Z"]


def test_ac4_the_facts_keep_every_verdict_with_one_listed_or_another_author():
    """REQ-032 AC4: rule 4."""
    assert len(facts_verdicts("reviewer", ["reviewer"])) == 1
    assert len(facts_verdicts("someone", ["reviewer", "other"])) == 2
    assert len(facts_verdicts(None, ["reviewer", "other"])) == 2


# --- check_final_clearance ------------------------------------------------------------------------


def final_scenario(repo, tmp_path: Path, listed: str) -> Path:
    """A reviewed head, a fix list by `reviewer` naming the ADR, a final commit that is not it."""
    repo.commit(
        {
            "config/reviewers.yaml": f"version: 1\nverdict_authors: [{listed}]\n",
            ADR: adr("Proposed"),
        },
        "reviewed",
    )
    reviewed = repo.git("rev-parse", "HEAD").strip()
    repo.commit({ADR: adr("Proposed") + "extra line\n"}, "not the final commit")
    body = f"Verdict: fix list {reviewed[:7]}\n\nreviewed.\n\nFinal: {ADR} Proposed -> Accepted\n"
    path = tmp_path / "comments.json"
    found = [{"body": body, "created_at": "2026-10-22T10:00:00Z", "user": {"login": "reviewer"}}]
    path.write_text(json.dumps(found), encoding="utf-8")
    return path


def clearance(repo, comments: Path, *extra: str):
    return repo.run("check_final_clearance.py", "--comments", str(comments), *extra)


def test_ac4_the_check_fails_on_a_bad_final_commit_without_an_author(repo, tmp_path):
    """REQ-032 AC4: rule 4 (no `--author`: the fix list covers, so the commit is checked)."""
    comments = final_scenario(repo, tmp_path, "reviewer, other")
    proc = clearance(repo, comments)
    assert proc.returncode == 1 and "rule 3" in proc.stdout, proc.stdout


def test_ac4_the_own_authors_fix_list_covers_nothing_with_two_listed(repo, tmp_path):
    """REQ-032 AC4: rule 4 (the pull request's author is `reviewer`; nothing is covered)."""
    comments = final_scenario(repo, tmp_path, "reviewer, other")
    proc = clearance(repo, comments, "--author", "Reviewer")
    assert (proc.returncode, proc.stdout) == (0, "ok final-clearance\n"), proc.stdout


def test_ac4_with_one_listed_author_the_own_fix_list_still_covers(repo, tmp_path):
    """REQ-032 AC4: rule 4 (nothing changes with one listed author)."""
    comments = final_scenario(repo, tmp_path, "reviewer")
    proc = clearance(repo, comments, "--author", "reviewer")
    assert proc.returncode == 1 and "rule 3" in proc.stdout, proc.stdout


def test_ac4_another_authors_pull_request_keeps_the_fix_list_covering(repo, tmp_path):
    """REQ-032 AC4: rule 4."""
    comments = final_scenario(repo, tmp_path, "reviewer, other")
    proc = clearance(repo, comments, "--author", "someone")
    assert proc.returncode == 1 and "rule 3" in proc.stdout, proc.stdout


def test_ac4_the_workflow_passes_the_pull_request_author_to_the_check():
    """REQ-032 AC4: rule 4 (the author login is read from the event; permissions stay read)."""
    text = (Path(__file__).resolve().parents[2] / ".github/workflows/governance.yml").read_text()
    assert "PR_AUTHOR: ${{ github.event.pull_request.user.login }}" in text
    assert '--author "$PR_AUTHOR"' in text
