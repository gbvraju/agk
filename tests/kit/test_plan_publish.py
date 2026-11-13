"""Tests of `plan_intake.py publish` (SPEC-0043 rules 8 and 25; REQ-050).

REQ-050 AC2.

After the person's `Approve: plan <full head ID>` (an account of `spec_approvers`, never through an
agent app), `publish` prints one `gh api` command per milestone and per brief, milestones first,
briefs in `depends_on` order, each brief withheld until `--numbers` names its milestone and every
brief it depends on, so a `Depends-on:` line always names `#<n>`. It refuses, printing no command,
a brief that `check_brief.py --root .` fails, and runs none of the commands. In personal mode it
writes the briefs through `forge.FilesForge`. Invented data only (example.com), no network.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import socket
import subprocess  # nosec B404 - the guard below replaces it; nothing is run
from pathlib import Path

import personal_state as ps
import plan_intake
import pytest
from forge import FilesForge
from test_plan_intake import TITLE, write
from test_plan_render import proposals, render
from test_plan_render import repo as repo  # noqa: F401 - the fixture, reused

HEAD = "c0ffee" + "0" * 34
OTHER = "d" * 40
OWNER = "demo-owner"
STRANGER = "demo-stranger"
REVIEWERS = f"verdict_authors: [{OWNER}]\nspec_approvers: [{OWNER}]\n"


@pytest.fixture(autouse=True)
def no_network(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("publish opens no socket")

    monkeypatch.setattr(socket, "socket", refuse)


def comment(body: str, login: str = OWNER, app: str | None = None) -> dict:
    via = {"slug": app} if app else None
    return {"body": body, "user": {"login": login}, "performed_via_github_app": via}


def approved(head: str = HEAD, login: str = OWNER, app: str | None = None) -> list[dict]:
    return [comment(f"Approve: plan {head}", login, app)]


def numbered(root: Path, req: str = "REQ-101") -> None:
    """The person's step of rule 7: each rendered `Advances:` key replaced by its REQ number."""
    for path in (root / "docs/plan/briefs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r"(?m)^Advances: .*$", f"Advances: {req}", text), "utf-8")


@pytest.fixture
def plan(repo: Path, capsys) -> Path:  # noqa: F811 - the reused fixture
    write(repo, "config/reviewers.yaml", REVIEWERS)
    data = proposals()
    data["briefs"].append(data["briefs"][0] | {"key": "B0", "depends_on": []})
    assert render(repo, data, capsys)[0] == 0
    numbered(repo)
    return repo


def publish(
    root: Path, capsys, comments: object, numbers: object = None, head: str = HEAD
) -> tuple[int, str]:
    path = root.parent / "comments.json"
    path.write_text(json.dumps(comments), encoding="utf-8")
    args = ["publish", "--comments", str(path), "--head", head, "--root", str(root)]
    if numbers is not None:
        saved = root.parent / "numbers.json"
        saved.write_text(json.dumps(numbers), encoding="utf-8")
        args += ["--numbers", str(saved)]
    code = plan_intake.main(args)
    out = capsys.readouterr()
    return code, out.out + out.err


def commands(out: str) -> list[list[str]]:
    """Each printed command, its quoted body spanning lines as the shell reads it."""
    found: list[list[str]] = []
    pending: list[str] = []
    for line in out.splitlines():
        if not pending and not line.startswith("gh api "):
            continue
        pending.append(line)
        try:
            found.append(shlex.split("\n".join(pending)))
        except ValueError:
            continue
        pending = []
    assert not pending, "a command is cut off"
    return found


def hidden(body: str) -> str:
    """Amendment 169: the rendered brief between the line `<!-- agk` and the line `-->`."""
    lines = body.splitlines(keepends=True)
    start = lines.index("<!-- agk\n")
    assert lines[-1] == "-->\n", "the hidden block ends the body"
    return "".join(lines[start + 1 : -1])


def field(command: list[str], name: str) -> str:
    """The value of `-f name=...` or `-F name=...` in a printed command."""
    for flag, value in zip(command, command[1:], strict=False):
        if flag in ("-f", "-F") and value.startswith(f"{name}="):
            return value.split("=", 1)[1]
    raise AssertionError(f"no field {name}")


@pytest.mark.parametrize(
    ("comments", "why"),
    [
        ([], "none"),
        (approved(login=STRANGER), "another account"),
        (approved(head=OTHER), "another head"),
        (approved(app="claude"), "an agent app"),
        ([comment(f"Thanks.\nApprove: plan {HEAD}")], "not the first line"),
    ],
)
def test_ac2_rule_8_publish_refuses_without_the_person_s_confirmation(
    plan: Path, capsys, comments: list[dict], why: str
) -> None:
    """REQ-050 AC2: rule 8, nothing is printed for creation until the person confirms (`why`)."""
    code, out = publish(plan, capsys, comments, {"M1": 7})
    assert code == 2, why
    assert "Approve: plan" in out and "spec_approvers" in out
    assert HEAD not in out and "gh api" not in out


def test_ac2_rule_25_milestones_first_and_every_brief_withheld_without_its_milestone(
    plan: Path, capsys
) -> None:
    """REQ-050 AC2: rule 25, a brief needs its milestone's number, so the first run prints only
    the milestones, with their title and due date."""
    code, out = publish(plan, capsys, approved())
    assert code == 0, out
    [milestone] = commands(out)
    assert milestone[:3] == ["gh", "api", "repos/{owner}/{repo}/milestones"]
    assert field(milestone, "title") == f"M1 {TITLE}"
    assert field(milestone, "due_on") == "2026-12-18T00:00:00Z"
    assert re.findall(r"(?m)^withheld (\S+): waits for (.+)$", out) == [
        ("B0", "M1"),
        ("B1", "M1"),
        ("B2", "M1, B1"),
    ]
    assert "nothing was run" in out


def test_ac2_rule_25_a_dependent_brief_waits_until_numbers_names_its_dependency(
    plan: Path, capsys
) -> None:
    """REQ-050 AC2: rule 25, `Depends-on:` always names `#<n>`, never a key."""
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 0, out
    printed = commands(out)
    assert [field(c, "title") for c in printed] == [TITLE, TITLE]  # B0 then B1, by key
    for command in printed:
        assert command[:3] == ["gh", "api", "repos/{owner}/{repo}/issues"]
        assert field(command, "labels[]") == "agk-brief"
        assert field(command, "milestone") == "7"
        assert "-F" in command and command[command.index("-F") + 1] == "milestone=7"
    assert re.findall(r"(?m)^withheld (\S+): waits for (.+)$", out) == [("B2", "B1")]
    code, out = publish(plan, capsys, approved(), {"M1": 7, "B0": 11, "B1": 12})
    assert code == 0, out
    [brief] = commands(out)
    body = field(brief, "body")
    assert re.findall(r"(?m)^Depends-on: .*$", body) == ["Depends-on: #12"]
    assert re.findall(r"(?m)^published (\S+) (#\d+)$", out) == [("B0", "#11"), ("B1", "#12")]
    rendered = (plan / "docs/plan/briefs/M1/B2.md").read_text(encoding="utf-8")
    assert hidden(body) == rendered.replace("Depends-on: B1", "Depends-on: #12")


def test_ac2_rule_25_the_last_round_names_the_board_command(plan: Path, capsys) -> None:
    """REQ-050 AC2: brief #1190 answer 6 (ADR-0506), once nothing is withheld the final line names
    `/agk:board --yes`; a round that withholds a brief does not."""
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 0, out
    assert "/agk:board" not in out
    code, out = publish(plan, capsys, approved(), {"M1": 7, "B0": 11, "B1": 12})
    assert code == 0, out
    last = out.strip().splitlines()[-1]
    assert last.startswith("ok publish: ") and "0 withheld" in last
    assert last.endswith("; next: /agk:board --yes (ADR-0506)")


def test_ac2_rule_25_a_brief_that_check_brief_fails_is_refused(plan: Path, capsys) -> None:
    """REQ-050 AC2: rule 25 and rule 7, a brief whose `Advances:` is still a key, or a REQ that is
    not in `docs/requirements.md`, is refused with no command printed at all."""
    path = plan / "docs/plan/briefs/M1/B1.md"
    path.write_text(re.sub(r"(?m)^Advances: .*$", "Advances: R1", path.read_text("utf-8")), "utf-8")
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 1
    assert "rule 25: briefs B1: check_brief.py fails" in out
    assert "gh api" not in out
    numbered(plan, "REQ-999")
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 1 and "briefs B0" in out and "gh api" not in out


def test_ac2_rule_25_a_plan_that_names_nothing_is_refused(plan: Path, capsys) -> None:
    """REQ-050 AC2: rule 25, an unknown dependency, a cycle or a wrong milestone line is refused."""
    b0 = plan / "docs/plan/briefs/M1/B0.md"
    text = b0.read_text(encoding="utf-8")
    b1 = plan / "docs/plan/briefs/M1/B1.md"
    b1.write_text(b1.read_text("utf-8").replace("Milestone: M1", "Milestone: M1\nDepends-on: B2"))
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 1 and "rule 25: briefs B1: depends_on makes a cycle" in out
    b0.write_text(text.replace("Milestone: M1", "Milestone: M9"), "utf-8")
    b1.write_text(b1.read_text("utf-8").replace("Depends-on: B2", "Depends-on: B7"), "utf-8")
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 1 and "gh api" not in out
    assert "rule 25: briefs B0: Milestone: is not its folder" in out
    assert "rule 25: briefs B1: depends_on names nothing" in out


def test_ac2_rule_25_publish_runs_no_command(plan: Path, capsys, monkeypatch) -> None:
    """REQ-050 AC2: rule 25, the commands are printed and none is run."""

    def refuse(*args, **kwargs):
        raise AssertionError("publish runs no command")

    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, refuse)
    monkeypatch.setattr(os, "system", refuse)
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 0 and len(commands(out)) == 2


@pytest.mark.parametrize(
    ("numbers", "head"),
    [({"M1": "seven"}, HEAD), (["M1"], HEAD), ({"M1": 0}, HEAD), ({"M1": 7}, "c0ffee")],
)
def test_ac2_rule_25_a_bad_numbers_file_or_head_is_usage(
    plan: Path, capsys, numbers: object, head: str
) -> None:
    """REQ-050 AC2: rule 25, refusals name the option, never the value."""
    code, out = publish(plan, capsys, approved(), numbers, head=head)
    assert code == 2 and "gh api" not in out
    assert "--numbers" in out or "usage" in out


def test_ac2_rule_3_publish_needs_the_data_guard(plan: Path, capsys) -> None:
    """REQ-050 AC2: rule 3, every command of `plan_intake.py`, `publish` too."""
    (plan / "scripts/agk/guard.py").unlink()
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 2 and "data guard not installed: scripts/agk/guard.py" in out


def test_ac2_rule_25_publish_without_a_plan_is_refused(tmp_path: Path, capsys) -> None:
    """REQ-050 AC2: rule 25, no `docs/plan/milestones.md`, nothing to publish."""
    root = tmp_path / "bare"
    write(root, "scripts/agk/guard.py", "# placeholder\n")
    write(root, ".claude/hooks/data_guard.py", "# placeholder\n")
    write(root, "config/reviewers.yaml", REVIEWERS)
    code, out = publish(root, capsys, approved())
    assert code == 1 and "rule 25: docs/plan/milestones.md" in out


def test_ac2_rule_25_personal_mode_writes_the_briefs_through_the_files_forge(
    plan: Path, tmp_path: Path, capsys
) -> None:
    """REQ-050 AC2: rule 25, in personal mode the same briefs become issues of the files forge,
    in order, with `Depends-on: #<n>` and the label `agk-brief`; nothing is sent to GitHub."""
    sidecar = tmp_path / "sidecar"
    ps.make_sidecar(sidecar, OWNER)
    for rel in ("scripts/agk/guard.py", ".claude/hooks/data_guard.py"):
        write(sidecar, rel, "# placeholder\n")
    shutil.copytree(plan / "docs/plan", sidecar / "docs/plan")
    requirements = sidecar / "docs/requirements.md"
    extra = (plan / "docs/requirements.md").read_text(encoding="utf-8").split("\n", 2)[2]
    requirements.write_text(requirements.read_text("utf-8") + "\n" + extra, "utf-8")
    code, out = publish(sidecar, capsys, approved())
    assert code == 0, out
    assert "gh api" not in out
    created = re.findall(r"(?m)^created (\S+) #(\d+)$", out)
    assert [key for key, _ in created] == ["B0", "B1", "B2"]
    numbers = {key: int(n) for key, n in created}
    forge = FilesForge(sidecar, env={})
    b2 = forge.load(f"issues/{numbers['B2']}.json")
    assert b2["title"] == TITLE and b2["labels"] == [{"name": "agk-brief"}]
    assert f"Depends-on: #{numbers['B1']}" in b2["body"] and "Milestone: M1" in b2["body"]
    assert b2["body"].startswith("## What\n") and "\n<!-- agk\n" in b2["body"]  # amendment 169
    code, out = publish(sidecar, capsys, approved(), numbers)
    assert code == 0 and "created" not in out
    assert sorted(forge.numbers("issues")) == sorted(numbers.values())


@pytest.mark.parametrize("solo", [False, True])
def test_ac2_rule_8_the_approval_inside_the_person_s_confirmation(
    plan: Path, capsys, solo: bool
) -> None:
    """REQ-050 AC2: rule 8, in solo mode the line counts inside the one person's whole
    `Confirmed:` comment, and only for the head it confirms (session rule 29); in team mode a
    `Confirmed:` comment confirms nothing. A short head ID never counts."""
    if solo:
        write(plan, "agk.toml", 'review_mode = "solo"\n')
    lines = [f"Confirmed: {HEAD}", f"Verdict: cleared {HEAD}", f"Approve: plan {OTHER}"]
    lines += [f"Approve: plan {HEAD}", "Shown:", "one", "two", "three"]
    lines.append(f"confirmed by {OWNER} in a session at 2026-11-12T13:00:00Z")
    code, out = publish(plan, capsys, [comment("\n".join(lines))], {"M1": 7})
    assert code == (0 if solo else 2), out
    code, out = publish(plan, capsys, [comment("\n".join(lines))], {"M1": 7}, head=OTHER)
    assert code == 2 and "gh api" not in out
    code, out = publish(plan, capsys, [comment(f"Approve: plan {HEAD[:12]}")], {"M1": 7})
    assert code == 2 and "gh api" not in out


# --- amendment 169 (brief #1124, ADR-0481): engineer-first issues, AGK's fields hidden ------------


def test_ac2_amendment_169_the_issue_reads_as_an_engineering_issue(plan: Path, capsys) -> None:
    """REQ-050 AC2: amendment 169 item 1, `## What` with the sentence, `## Acceptance` with the
    `Answers` items as checkboxes, the milestone and the dependence in words, then the rendered
    brief, unchanged but for its numbered `Depends-on:`, in a block GitHub does not show."""
    code, out = publish(plan, capsys, approved(), {"M1": 7, "B0": 11, "B1": 12})
    assert code == 0, out
    [brief] = commands(out)
    body = field(brief, "body")
    rendered = (plan / "docs/plan/briefs/M1/B2.md").read_text(encoding="utf-8")
    shown = body[: body.index("<!-- agk\n")]
    answers = [x for x in rendered.splitlines() if re.match(r"\d+\. ", x)]
    assert answers, rendered
    assert shown == "\n".join(
        ["## What", "", TITLE, "", "## Acceptance", ""]
        + ["- [ ] " + re.sub(r"^\d+\. ", "", x) for x in answers]
        + ["", "Part of milestone M1. Depends on #12.", "", ""]
    )
    assert hidden(body) == rendered.replace("Depends-on: B1", "Depends-on: #12")
    assert field(brief, "title") == TITLE
    for line in shown.splitlines():
        assert not re.match(r"(Sentence|Answers|Advances|Touches|Size|Depends-on|Milestone):", line)


def test_ac2_amendment_169_without_a_dependence_only_the_milestone(plan: Path, capsys) -> None:
    """REQ-050 AC2: amendment 169 item 1, `Depends on` only when the brief depends on another."""
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 0, out
    for command in commands(out):
        body = field(command, "body")
        assert "\nPart of milestone M1.\n" in body and "Depends on" not in body


def test_ac2_amendment_169_every_reader_reads_the_same_lines(plan: Path, capsys) -> None:
    """REQ-050 AC2: amendment 169 item 1, `session.brief_problems` (and `check_brief.py`'s check)
    give the same result for the whole issue body and for the rendered body alone, both for a
    good brief and for one that breaks a rule."""
    import check_brief  # noqa: PLC0415 - its `brief_problems` is `session.brief_problems`

    code, out = publish(plan, capsys, approved(), {"M1": 7, "B0": 11, "B1": 12})
    assert code == 0, out
    body = field(commands(out)[0], "body")
    inner = hidden(body)
    assert check_brief.brief_problems(body) == check_brief.brief_problems(inner) == []
    assert check_brief.body_problems(body, None, None) == check_brief.body_problems(
        inner, None, None
    )
    broken = plan_intake.issue_body(
        {"body": inner.replace("Size: M", "Size: XL"), "milestone": "M1"}, {}
    )
    assert check_brief.brief_problems(broken) == check_brief.brief_problems(hidden(broken)) != []


def test_ac2_amendment_169_a_brief_holding_the_end_of_a_comment_is_refused(
    plan: Path, capsys
) -> None:
    """REQ-050 AC2: amendment 169 item 1, `-->` would end the hidden block early: refused by key,
    nothing printed to run."""
    path = plan / "docs/plan/briefs/M1/B1.md"
    path.write_text(path.read_text("utf-8").replace("Size: M", "Size: M\nNote: a --> b"), "utf-8")
    code, out = publish(plan, capsys, approved(), {"M1": 7})
    assert code == 1
    assert "rule 25: briefs B1: the body holds `-->`" in out
    assert "gh api" not in out
