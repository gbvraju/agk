"""Open questions and conflicts become business question issues (brief #1196, REQ-050, ADR-0508).

REQ-050 AC2.

`render` writes every open question and every unsettled conflict into the `Questions for business`
section of `docs/plan/scope.md`, each with its key, its plain question, its sources and the keys of
the requirements and briefs that cite one of them (`Blocks:`). `publish` reads that section, never
the proposals file, and prints, before the briefs, the label command and one `gh api` command per
question: an issue titled with the question's plain text, with `## Question`, the source,
`Blocks:` and an empty `## Answer`, labelled `agk-business-question` and never `agk-brief`. A
brief that a question blocks waits for the question's number and then carries `Blocked-by: #<n>`;
`session.py plan` prints it as `waits for question #<n>` until that issue is closed. Invented
sources only (example.com), no network.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import check_brief
import personal_state as ps
import pytest
from forge import FilesForge
from test_plan_intake import PRD, SOW, write
from test_plan_publish import (
    OWNER,
    REVIEWERS,
    approved,
    commands,
    field,
    numbered,
    publish,
)
from test_plan_publish import no_network as no_network  # noqa: F401 - the guard, reused
from test_plan_render import proposals, render
from test_plan_render import repo as repo  # noqa: F401 - the fixture, reused
from test_session import Stub, issue, listing, state
from test_session_flow import brief
from test_session_plan import free, plan
from test_session_plan import proj as proj  # noqa: F401 - the fixture, reused

LABEL = "agk-business-question"
QUESTION = "Who signs the list off?"
UNSETTLED = {"locations": [f"{SOW}#Estimates", f"{PRD}:10"], "description": "the hours of M1"}


def raw(command: list[str]) -> list[str]:
    """The label of each question command, read the way the person's shell reads it."""
    return [v.split("=", 1)[1] for f, v in zip(command, command[1:], strict=False) if f == "-f"]


def questions_only(out: str) -> list[list[str]]:
    return [c for c in commands(out) if f"labels[]={LABEL}" in c]


def briefs_only(out: str) -> list[list[str]]:
    return [c for c in commands(out) if "labels[]=agk-brief" in c]


@pytest.fixture
def asked(repo: Path, capsys) -> Path:  # noqa: F811 - the reused fixture
    """A rendered plan with one open question, one settled and one unsettled conflict; the open
    question cites the briefs' own source, so it blocks both briefs."""
    write(repo, "config/reviewers.yaml", REVIEWERS)
    data = proposals()
    data["scope"]["open_questions"][0]["sources"].append(f"{SOW}#Estimates")
    data["conflicts"].append(UNSETTLED)
    code, out = render(repo, data, capsys)
    assert code == 0, out
    numbered(repo)
    return repo


def test_1196_render_writes_each_question_into_scope_with_its_blocks(asked: Path) -> None:
    """REQ-050: brief #1196 answer 1, the render's file is what publish reads."""
    scope = (asked / "docs/plan/scope.md").read_text(encoding="utf-8")
    section = scope.split("\n## Questions for business\n", 1)[1]
    assert "\n### Q1\n" in section and "\n### conflict-2\n" in section
    assert "\n### conflict-1\n" not in section  # settled: nothing left to ask
    assert f"Question: {QUESTION} (verify)" in section
    assert f"Source: `{SOW}#Scope`, `{SOW}#Estimates`" in section
    assert section.count("Blocks: B1, B2") == 2  # each cites the briefs' source
    assert "Question: The sources disagree: the hours of M1. Which one holds?" in section


def test_1196_a_publish_prints_one_question_issue_per_open_question_and_conflict(
    asked: Path, capsys
) -> None:
    """REQ-050: brief #1196 answer 5 (a), the label first, the questions before every brief."""
    code, out = publish(asked, capsys, approved(), {"M1": 7})
    assert code == 0, out
    label = [x for x in out.splitlines() if x.startswith("gh label create ")]
    assert label == [f"gh label create {LABEL} --description" + label[0].split("--description")[1]]
    assert "--force" in label[0]
    found = questions_only(out)
    assert [field(c, "title") for c in found] == [
        QUESTION,
        "The sources disagree: the hours of M1. Which one holds?",
    ]
    for command in found:
        assert command[:3] == ["gh", "api", "repos/{owner}/{repo}/issues"]
        assert "labels[]=agk-brief" not in command and "milestone" not in " ".join(raw(command))
    body = field(found[0], "body")
    assert body.startswith(f"## Question\n\n{QUESTION}\n\n")
    assert f"\nSource: `{SOW}#Scope`, `{SOW}#Estimates`\n" in body
    assert "\nBlocks: B1, B2\n" in body and body.endswith("\n## Answer\n")
    assert "proposals" not in body
    assert briefs_only(out) == []  # each brief waits for its question's number
    assert re.findall(r"(?m)^withheld (\S+): waits for (.+)$", out) == [
        ("B0", "Q1, conflict-2"),
        ("B1", "Q1, conflict-2"),
        ("B2", "B1, Q1, conflict-2"),
    ]
    assert out.index("gh label create") < out.index(f"labels[]={LABEL}") < out.index("withheld")


def test_1196_b_a_second_publish_with_the_numbers_prints_no_question_again(
    asked: Path, capsys
) -> None:
    """REQ-050: brief #1196 answer 5 (b), saved under the question's key, never printed twice;
    the brief it blocks then names the question's issue."""
    numbers = {"M1": 7, "Q1": 31, "conflict-2": 32}
    code, out = publish(asked, capsys, approved(), numbers)
    assert code == 0, out
    assert questions_only(out) == [] and "gh label create" not in out
    assert re.findall(r"(?m)^published (\S+) (#\d+)$", out) == [("Q1", "#31"), ("conflict-2", "#32")]
    printed = briefs_only(out)
    assert len(printed) == 2
    body = field(printed[0], "body")
    assert re.findall(r"(?m)^Blocked-by: .*$", body) == ["Blocked-by: #31", "Blocked-by: #32"]
    assert check_brief.body_problems(body, None, None) == []


def test_1196_a_question_that_blocks_nothing_lets_the_briefs_go(repo: Path, capsys) -> None:  # noqa: F811
    """REQ-050: brief #1196 answer 1, `Blocks: none`; the question is still an issue."""
    write(repo, "config/reviewers.yaml", REVIEWERS)
    assert render(repo, proposals(), capsys)[0] == 0
    numbered(repo)
    assert "\nBlocks: none\n" in (repo / "docs/plan/scope.md").read_text(encoding="utf-8")
    code, out = publish(repo, capsys, approved(), {"M1": 7})
    assert code == 0, out
    assert len(questions_only(out)) == 1 and len(briefs_only(out)) == 2
    assert all("Blocked-by" not in field(c, "body") for c in briefs_only(out))


def test_1196_a_question_key_that_is_also_a_brief_key_is_refused(asked: Path, capsys) -> None:
    """REQ-050: brief #1196 answer 1, the numbers file holds one number per key."""
    scope = asked / "docs/plan/scope.md"
    scope.write_text(scope.read_text("utf-8").replace("### Q1\n", "### B1\n"), "utf-8")
    code, out = publish(asked, capsys, approved(), {"M1": 7})
    assert code == 1 and "rule 25: questions B1: the key is also a brief's or a milestone's" in out
    assert "gh " not in out


def test_1196_personal_mode_writes_the_questions_through_the_files_forge(
    asked: Path, tmp_path: Path, capsys
) -> None:
    """REQ-050: brief #1196 contexts (personal), the questions go through the files forge first."""
    sidecar = tmp_path / "sidecar"
    ps.make_sidecar(sidecar, OWNER)
    for rel in ("scripts/agk/guard.py", ".claude/hooks/data_guard.py"):
        write(sidecar, rel, "# placeholder\n")
    shutil.copytree(asked / "docs/plan", sidecar / "docs/plan")
    requirements = sidecar / "docs/requirements.md"
    extra = (asked / "docs/requirements.md").read_text(encoding="utf-8").split("\n", 2)[2]
    requirements.write_text(requirements.read_text("utf-8") + "\n" + extra, "utf-8")
    code, out = publish(sidecar, capsys, approved())
    assert code == 0, out
    asked_ = dict(re.findall(r"(?m)^created question (\S+) #(\d+)$", out))
    assert list(asked_) == ["Q1", "conflict-2"]
    forge = FilesForge(sidecar, env={})
    q1 = forge.load(f"issues/{asked_['Q1']}.json")
    assert q1["title"] == QUESTION and q1["labels"] == [{"name": LABEL}]
    briefs = dict(re.findall(r"(?m)^created (B\d) #(\d+)$", out))
    b1 = forge.load(f"issues/{briefs['B1']}.json")
    assert f"Blocked-by: #{asked_['Q1']}" in b1["body"]
    numbers = {k: int(v) for k, v in (asked_ | briefs).items()}
    code, out = publish(sidecar, capsys, approved(), numbers)
    assert code == 0 and "created" not in out


# --- (d) the plan: a brief blocked by an open question waits ----------------------------------


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


def test_1196_d_a_brief_blocked_by_an_open_question_is_not_offered(proj, stub) -> None:  # noqa: F811
    """REQ-050: brief #1196 answer 3 and answer 5 (d)."""
    listing(stub, [issue(5, brief("a/") + "Blocked-by: #31\n"), issue(6, brief("b/"))])
    free(stub, 5, 6)
    state(stub, 31, "open")
    lines = plan(proj, stub).stdout.splitlines()
    assert lines[0] == "Start 1: builder-a takes #6."
    assert "#5 waits for question #31." in lines
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert {"brief": 5, "question": 31, "why": "it is open"} in data["waits"]


def test_1196_d_once_the_question_closes_the_brief_is_offered(proj, stub) -> None:  # noqa: F811
    """REQ-050: brief #1196 answer 3 and answer 5 (d)."""
    listing(stub, [issue(5, brief("a/") + "Blocked-by: #31\n"), issue(6, brief("b/"))])
    free(stub, 5, 6)
    state(stub, 31, "closed")
    out = plan(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.splitlines()[0] == "Start 2: builder-a takes #5, builder-b takes #6."
    assert "question" not in out.stdout


def test_1196_d_a_question_that_cannot_be_read_holds_the_brief(proj, stub) -> None:  # noqa: F811
    """REQ-050: brief #1196 answer 3, a failed read is never taken as closed."""
    listing(stub, [issue(5, brief("a/") + "Blocked-by: #31\n")])
    free(stub, 5)
    lines = plan(proj, stub).stdout.splitlines()
    assert "#5 waits for question #31 (it cannot be read)." in lines


def test_1196_d_next_does_not_offer_it_either(proj, stub) -> None:  # noqa: F811
    """REQ-050: brief #1196 answer 3, `next` judges by the same rule as `plan`."""
    from test_session import session

    listing(stub, [issue(5, brief("a/") + "Blocked-by: #31\n")])
    free(stub, 5)
    state(stub, 31, "open")
    out = session(proj, stub, "next", "--session", "s1")
    assert "skip #5: waits for question #31" in out.stdout, out.stdout + out.stderr
    assert "brief #5" not in out.stdout

