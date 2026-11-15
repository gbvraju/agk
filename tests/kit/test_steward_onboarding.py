"""Tests of scripts/agk/steward_onboard.py, onboarding at any stage with an evidence harvest
(SPEC-0059 rule 20 and rule 18's budget; brief #1325, ADR-0562; REQ-066 AC1).

A recorded `gh` double counts each call and answers from an invented issue store; no network, no
model, invented data only (example.com).
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import steward  # noqa: E402
import steward_onboard  # noqa: E402

NOW = datetime(2026, 11, 15, 10, 30, tzinfo=UTC)
PATH = re.compile(r"repos/\{owner\}/\{repo\}/(issues(?:/comments)?)(?:/(\d+))?(/comments)?(?:\?(.*))?$")


class GitHub:
    """The recorded double: issues by label, the memory issue's comments and the repository's."""

    def __init__(self, labels=(), repo_comments=(), conductor=False, unreadable=()) -> None:
        self.calls: list[tuple[str, str]] = []
        self.memory: list[dict] = []
        self.has_memory = False
        self.labels = {name: list(items) for name, items in labels}
        if conductor:
            self.labels["agk-conductor"] = [{"number": 9, "state": "open"}]
        self.repo = list(repo_comments)
        self.unreadable = set(unreadable)
        self.next_id = 5000

    def posted(self) -> list[str]:
        return [c["body"] for c in self.memory]

    def __call__(self, method: str, endpoint: str, fields: dict | None = None):
        self.calls.append((method, endpoint))
        found = PATH.match(endpoint)
        assert found, endpoint
        kind, number, comments, query = found.groups()
        query = query or ""
        if any(word in endpoint for word in self.unreadable):
            return None
        if kind == "issues/comments":
            page = int(re.search(r"page=(\d+)", query)[1])
            return self.repo[(page - 1) * 100 : page * 100]
        if method == "GET" and number is None:
            label = re.search(r"labels=([^&]+)", query)[1]
            if label == "agk-steward":
                return [{"number": 1, "comments": len(self.memory)}] if self.has_memory else []
            items = self.labels.get(label, [])
            return [i for i in items if "state=all" in query or i.get("state") == "open"]
        if method == "GET":
            return self.memory
        if method == "POST" and number is None:
            self.has_memory = True
            return {"number": 1, "comments": 0}
        if method == "POST" and comments:
            self.next_id += 1
            item = {"id": self.next_id, "body": fields["body"], "created_at": "2026-11-15T10:30:00Z"}
            item["updated_at"] = item["created_at"]
            self.memory.append(item)
            return item
        raise AssertionError((method, endpoint))


def comment(n: int, body: str, issue: int = 40) -> dict:
    return {
        "id": 900 + n,
        "body": body,
        "issue_url": f"https://api.example.com/repos/o/r/issues/{issue}",
        "created_at": f"2026-11-{1 + n % 9:02d}T08:00:00Z",
    }


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    return tmp_path


def executing(root: Path) -> None:
    """An approved plan, an Accepted ADR, a ruled question, an Approved spec and requirements."""
    (root / "docs" / "plan").mkdir(parents=True)
    (root / "docs" / "plan" / "scope-lock.md").write_text("Locked.\n", encoding="utf-8")
    (root / "docs" / "adr").mkdir()
    (root / "docs" / "adr" / "0007-totals-are-weekly.md").write_text(
        "# ADR-0007: Totals are weekly\n\n- Status: Accepted\n", encoding="utf-8"
    )
    (root / "docs" / "adr" / "0008-a-draft.md").write_text(
        "# ADR-0008: A draft\n\n- Status: Proposed\n", encoding="utf-8"
    )
    (root / "docs" / "specs").mkdir()
    (root / "docs" / "specs" / "0003-the-report.md").write_text(
        "# SPEC-0003: The report\n\n- Status: Approved\n", encoding="utf-8"
    )
    (root / "docs" / "runs" / "decisions").mkdir(parents=True)
    (root / "docs" / "runs" / "decisions" / "2026-11-02-q-12-1.md").write_text(
        "| 2026-11-02 | Q-12-1 ruled: the report goes out on Fridays. | comment 1 | x | maintainers |\n",
        encoding="utf-8",
    )
    (root / "docs" / "requirements.md").write_text(
        "# Requirements\n\n### REQ-001 The weekly report\n- Status: in-progress\n", encoding="utf-8"
    )


def merged_work() -> list:
    return [("agk-brief", [{"number": 12, "state": "closed", "title": "The weekly report"}])]


def test_req066_an_empty_repository_starts_at_start(root):
    """REQ-066 AC1: rule 20 (a), day 0: no Approved spec and no brief; the stage is `start`."""
    gh = GitHub()
    code, lines = steward_onboard.onboard(root, gh, NOW)
    assert code == 0
    assert lines[0] == "entry: day 0"
    assert "stage: start" in lines
    assert gh.posted()[-1].startswith("Onboarded: start 2026-11-15, 0 decisions, 0 gaps, 0 open")
    assert not any(e.endswith("issues/comments?per_page=100&page=1") for _, e in gh.calls)


def test_req066_sources_and_a_draft_plan_name_the_planning_stage(root):
    """REQ-066 AC1: rule 20 (b), a repository with sources and a scope names its planning stage."""
    (root / "docs" / "discovery").mkdir(parents=True)
    (root / "docs" / "discovery" / "vision.md").write_text("Vision.\n", encoding="utf-8")
    (root / "docs" / "plan").mkdir(parents=True)
    (root / "docs" / "plan" / "milestones.md").write_text("### M1\n", encoding="utf-8")
    gh = GitHub(labels=[("agk-brief", [{"number": 3, "state": "open", "title": "a draft"}])])
    code, lines = steward_onboard.onboard(root, gh, NOW)
    assert code == 0
    assert lines[:2] == ["entry: planning", "stage: plan"]
    assert gh.posted()[-1].startswith("Onboarded: plan 2026-11-15,")


def test_req066_execution_harvests_decisions_with_sources_before_any_answer(root):
    """REQ-066 AC1: rule 20 (c), `Maintainer answer:` lines and ADRs become `Decision:` notes with
    their sources, marked `harvested`, and `Onboarded:` is the last post, with no `Answer:`."""
    executing(root)
    owner = 'Maintainer answer: Q-12-2 weekly\nOwner said (2026-11-03T08:00Z): "weekly"'
    gh = GitHub(labels=merged_work(), repo_comments=[comment(1, owner), comment(2, "Thanks.")])
    code, lines = steward_onboard.onboard(root, gh, NOW)
    assert code == 0 and lines[0] == "entry: execution"
    posts = gh.posted()
    decisions = "\n".join(p for p in posts if p.startswith("Decision: harvested"))
    assert "Q-12-2 weekly (source: #40 comment 901)" in decisions
    assert "ADR-0007 Totals are weekly (source: docs/adr/0007-totals-are-weekly.md)" in decisions
    assert "ADR-0008" not in decisions
    assert "SPEC-0003 The report (source: docs/specs/0003-the-report.md)" in decisions
    assert "Q-12-1 ruled: the report goes out on Fridays." in decisions
    assert "REQ-001 in-progress (source: docs/requirements.md)" in decisions
    assert all(p.rstrip().endswith(steward.WHO) for p in posts)
    assert posts[-1].startswith("Onboarded: build 2026-11-15, 6 decisions, 0 gaps, 0 open questions")
    assert not any(p.startswith("Answer:") for p in posts)
    assert any(line.startswith("rely on: ") for line in lines)


def test_req066_a_contradiction_goes_to_the_owner_and_an_unreadable_source_is_a_gap(root):
    """REQ-066 AC1: rule 20 (d), two answers to one question disagree: an owner question, not a
    decision; the parked list cannot be read: a `Gap:` naming it, never assumed empty."""
    executing(root)
    first = 'Maintainer answer: Q-12-3 Friday\nOwner said (2026-11-03T08:00Z): "Friday"'
    gh = GitHub(
        labels=merged_work(),
        repo_comments=[comment(1, first), comment(2, "Answer: Q-12-3 Monday (evidence: x)")],
        unreadable=("agk:parked",),
    )
    steward_onboard.onboard(root, gh, NOW)
    posts = gh.posted()
    assert not any("Q-12-3" in p for p in posts if p.startswith("Decision:"))
    owner = [p for p in posts if p.startswith("Owner question:")]
    assert owner and "Q-12-3" in owner[0] and "#40 comment 901" in owner[0]
    gaps = [p for p in posts if p.startswith("Gap:")]
    assert gaps and "parked work cannot be read" in gaps[0]
    assert ", 1 gaps, 1 open questions" in posts[-1]


def test_req066_open_questions_and_parked_work_are_harvested(root):
    """REQ-066 AC1: rule 20, an unanswered `Question:` and an `Owner needed:` are open questions,
    an answered one is not, and parked work is a `Risk:`."""
    executing(root)
    labels = [*merged_work(), ("agk:parked", [{"number": 51, "state": "open", "title": "Totals"}])]
    repo = [
        comment(1, "Question: Q-51-1 for the maintainers: which week?", issue=51),
        comment(2, "Question: Q-52-1 a lint?", issue=52),
        comment(3, "Answer: Q-52-1 run make lint (evidence: Makefile)", issue=52),
        comment(4, "Owner needed: the start of #53 was refused", issue=53),
    ]
    gh = GitHub(labels=labels, repo_comments=repo)
    steward_onboard.onboard(root, gh, NOW)
    posts = gh.posted()
    questions = "\n".join(p for p in posts if p.startswith("Owner question:"))
    assert "Q-51-1" in questions and "Owner needed:" in questions and "Q-52-1" not in questions
    assert any(p.startswith("Risk:") and "#51 Totals" in p for p in posts)
    assert ", 2 open questions" in posts[-1]


def test_req066_the_harvest_reads_by_list_pages_within_its_budget(root):
    """REQ-066 AC1: rule 20 (e) and Q-S0059-15, 150 repository comments are read in 2 pages and
    never one read per item; the whole first onboarding makes a fixed count of calls."""
    executing(root)
    repo = [
        comment(n, f'Maintainer answer: Q-60-{n} yes\nOwner said (2026-11-03T08:00Z): "yes"')
        for n in range(150)
    ]
    gh = GitHub(labels=merged_work(), repo_comments=repo)
    steward_onboard.onboard(root, gh, NOW)
    pages = [e for _, e in gh.calls if "issues/comments?" in e]
    assert len(pages) == 2
    gets = [e for m, e in gh.calls if m == "GET"]
    # the memory listing, the conductor, the briefs, two pages and the parked list
    assert len(gets) == 6
    posts = [e for m, e in gh.calls if m == "POST"]
    # the memory issue, 155 decisions in 4 notes of at most 50 lines, and the `Onboarded:` entry
    assert len(posts) == 6


def test_req066_a_second_start_is_already_onboarded_and_writes_nothing(root):
    """REQ-066 AC1: rule 20, a memory with an `Onboarded:` entry is not a first start."""
    executing(root)
    gh = GitHub(labels=merged_work())
    steward_onboard.onboard(root, gh, NOW)
    before = len(gh.posted())
    code, lines = steward_onboard.onboard(root, gh, NOW)
    assert code == 0 and lines[0].startswith("onboarded: Onboarded: build")
    assert len(gh.posted()) == before


def test_req066_again_adds_only_new_notes(root):
    """REQ-066 AC1: rule 20 (f) and Q-S0059-14, `--again` keeps the notes and writes no fact twice."""
    executing(root)
    gh = GitHub(labels=merged_work())
    steward_onboard.onboard(root, gh, NOW)
    first = len(gh.posted())
    (root / "docs" / "adr" / "0009-a-new-one.md").write_text(
        "# ADR-0009: A new one\n\n- Status: Accepted\n", encoding="utf-8"
    )
    code, _ = steward_onboard.onboard(root, gh, NOW, again=True)
    assert code == 0
    new = gh.posted()[first:]
    assert len(new) == 2
    assert "ADR-0009 A new one" in new[0] and "ADR-0007" not in new[0]
    assert new[-1].startswith("Onboarded: build 2026-11-15, 1 decisions,")
    code, _ = steward_onboard.onboard(root, gh, NOW, again=True)
    assert len(gh.posted()) == first + 3  # only the `Onboarded:` entry


def test_req066_a_withheld_line_and_personal_mode(root):
    """REQ-066 AC1: rule 20 with rule 14, a line the data guard matches is withheld naming its
    class, never its value; in personal mode the harvest writes the sidecar file and posts nothing."""
    executing(root)
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    (root / "docs" / "adr" / "0010-mail.md").write_text(
        "# ADR-0010: Mail ops@example.com weekly\n\n- Status: Accepted\n", encoding="utf-8"
    )
    calls: list = []
    code, lines = steward_onboard.onboard(root, lambda *a: calls.append(a), NOW)
    assert code == 0 and calls == []
    memory = (root / steward.PERSONAL_FILE).read_text(encoding="utf-8")
    assert "ADR-0007 Totals are weekly" in memory and "Onboarded: plan" in memory
    assert "ops@example.com" not in memory and "withheld by the data guard" in memory


def test_req066_the_command_is_a_subcommand_of_steward(root, monkeypatch, capsys):
    """REQ-066 AC1: Q-S0059-14, `steward.py onboard --again` runs the onboarding."""
    seen = {}
    monkeypatch.setattr(steward, "repo_root", lambda: root)
    monkeypatch.setattr(
        steward_onboard, "onboard", lambda r, gh, now, again=False: seen.update(again=again) or (0, ["ok"])
    )
    assert steward.main(["onboard", "--again"]) == 0
    assert seen == {"again": True} and capsys.readouterr().out == "ok\n"
