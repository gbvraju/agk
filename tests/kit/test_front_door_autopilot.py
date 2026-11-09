"""Tests of `front_door.py` build (f): the auto-pilot drive (SPEC-0048 rules 1, 9 and 13).

REQ-055 AC7: `status --issue N --api-dir DIR` prints one line, the phase and what the problem waits
for, from saved responses and the files only. Auto-pilot is on only with `[flow] assign =
"conductor"` and the first line `Auto-pilot: on` by a listed approver, never through an agent app;
the conductor's `Discovery: round <n>` comments hold at most three questions; only a listed
approver's comment answers one. REQ-055 AC4: no mode reaches past `waits for the go` without the
line of rule 9, on the pull request that carries the artifact. Personal mode has no issue entry.
Fixtures in `tmp_path` only: invented data (`example.com`), saved responses, no network.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import front_door
import pytest
from test_front_door_design import (
    DEMO,
    DESIGN,
    LINK,
    SCRIPT,
    SLUG,
    TODAY,
    demo,
    discovery,
    prototype,
    record,
    write,
)
from test_front_door_design import design as architecture

KIT_ROOT = SCRIPT.parents[2]
OWNER = "owner-example"
STRANGER = "stranger-example"
CONDUCTOR = "conductor-example"
HEAD = "a" * 40
SPEC_GO = "Approve: SPEC-0099"
DESIGN_GO = f"Approve: design v1 {HEAD}"
PRIVATE_WORDS = "a private word from example.com"  # a value: never printed
NUMBER = 7
ISSUE = {
    "number": NUMBER,
    "title": "Orders are lost",
    "html_url": LINK,
    "body": "Problem: Orders at example.com are lost when payment times out.",
    "labels": [{"name": "agk-problem"}],
}
THREE = "\n- users: who?\n- existing: what exists?\n- runs: where does it run?"


def comment(login: str, body: str, app: str | None = None) -> dict:
    item = {"user": {"login": login}, "body": body, "created_at": "2026-11-08T10:00:00Z"}
    if app:
        item["performed_via_github_app"] = {"slug": app}
    return item


PILOT = comment(OWNER, "Auto-pilot: on")


def round_of(n: int, questions: str = THREE, login: str = CONDUCTOR) -> dict:
    return comment(login, f"Discovery: round {n}{questions}")


def configure(tmp_path: Path, assign: str = "conductor", top: str = "") -> None:
    write(tmp_path, "agk.toml", f'{top}\n[flow]\nassign = "{assign}"\n')
    write(
        tmp_path,
        "config/reviewers.yaml",
        f"spec_approvers: [{OWNER}]\nverdict_authors: [{CONDUCTOR}]\n",
    )


def save(tmp_path: Path, comments: list, issue: dict | None = None) -> Path:
    write(tmp_path, f"api/issue-{NUMBER}.json", json.dumps(issue or ISSUE))
    write(tmp_path, f"api/issue-{NUMBER}-comments.json", json.dumps(comments))
    return tmp_path / "api"


def status(tmp_path: Path, *extra: str, api: bool = True, capsys=None) -> tuple[int, str]:
    args = ["status", "--date", TODAY, "--root", str(tmp_path)]
    if api:
        args += ["--issue", str(NUMBER), "--api-dir", str(tmp_path / "api")]
    capsys.readouterr()  # a fixture's `discovery-write` printed its own line
    code = front_door.main([*args, *extra])
    out = capsys.readouterr()
    return code, out.out + out.err


def line_of(tmp_path, capsys, *extra: str) -> str:
    code, out = status(tmp_path, *extra, capsys=capsys)
    assert code == 0, out
    assert out.count("\n") == 1, out
    return out.strip()


PHASE_2 = f"#{NUMBER} {SLUG}: phase 2 discovery"


# --- the command ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        ["--issue", "7"],
        ["--api-dir", "api"],
        ["--issue", "seven", "--api-dir", "api"],
        ["--issue", "0", "--api-dir", "api"],
        ["--issue", "7", "--api-dir", "api", "--pr", "x"],
        ["--issue", "7", "--api-dir", "api", SLUG],
        ["--pr", "9"],
    ],
)
def test_ac7_status_issue_usage(tmp_path, capsys, extra):
    """REQ-055 AC7: SPEC-0048 rule 1 (`--issue N` goes with `--api-dir DIR`, and names no slug)."""
    configure(tmp_path)
    code, out = status(tmp_path, *extra, api=False, capsys=capsys)
    assert code == 2 and "usage:" in out


def test_ac7_status_issue_still_needs_the_date(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 6 (the date comes from `date -u`; a check reads no clock)."""
    args = ["status", "--issue", "7", "--api-dir", str(tmp_path), "--root", str(tmp_path)]
    assert front_door.main(args) == 2
    assert "usage:" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["missing", "not json", "wrong shape"])
def test_ac7_unreadable_saved_responses_are_refused_not_read_as_empty(tmp_path, capsys, bad):
    """REQ-055 AC7: SPEC-0048 rules 1 and 15 (unknown is never zero; names the file only)."""
    configure(tmp_path)
    api = save(tmp_path, [])
    target = api / f"issue-{NUMBER}-comments.json"
    if bad == "missing":
        target.unlink()
    else:
        target.write_text("{" if bad == "not json" else '{"a": 1}', encoding="utf-8")
    code, out = status(tmp_path, capsys=capsys)
    assert code == 1
    assert f"issue-{NUMBER}-comments.json" in out and "rule 1" in out


def test_ac1_an_issue_that_fails_the_entry_stays_at_phase_1(tmp_path, capsys):
    """REQ-055 AC1: SPEC-0048 rules 1, 3 and 15 (phase 1, and no words of the issue printed)."""
    configure(tmp_path)
    save(tmp_path, [PILOT], {**ISSUE, "labels": [], "title": PRIVATE_WORDS})
    line = line_of(tmp_path, capsys)
    assert (
        line == f"#{NUMBER}: phase 1 the entry; waits for a problem issue that passes check-issue"
    )
    assert "private" not in line


def test_ac7_status_reads_saved_responses_only_and_writes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-055 AC7: SPEC-0048 rules 1 and 16 (no network, nothing written)."""

    def no_network(*_args, **_kwargs):
        raise AssertionError("a socket was opened")

    configure(tmp_path)
    save(tmp_path, [PILOT, round_of(1)])
    monkeypatch.setattr(socket, "socket", no_network)
    before = sorted(p for p in tmp_path.rglob("*"))
    line_of(tmp_path, capsys)
    assert sorted(p for p in tmp_path.rglob("*")) == before


# --- auto-pilot: on only with the setting and the owner's line (rules 3 and 13) ------------------


def test_ac7_without_the_line_the_conductor_drives_nothing(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (no `Auto-pilot: on`: the plain phase, rounds not read)."""
    configure(tmp_path)
    save(tmp_path, [round_of(1), comment(OWNER, "the answers")])
    assert line_of(tmp_path, capsys) == f"{PHASE_2}; waits for docs/discovery/{SLUG}.md"


@pytest.mark.parametrize(
    "item",
    [
        comment(STRANGER, "Auto-pilot: on"),
        comment(CONDUCTOR, "Auto-pilot: on"),
        comment(OWNER, "Auto-pilot: on", app="claude"),
        comment(OWNER, "please turn it on\nAuto-pilot: on"),
        comment(OWNER, "Auto-pilot: off"),
    ],
)
def test_ac7_only_the_owners_first_line_turns_it_on(tmp_path, capsys, item):
    """REQ-055 AC7: SPEC-0048 Q-S0048-4 (a listed approver's first line, never an agent app)."""
    configure(tmp_path)
    save(tmp_path, [item, round_of(1)])
    assert "auto-pilot" not in line_of(tmp_path, capsys)


def test_ac7_the_setting_alone_or_the_line_alone_is_not_enough(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 3 (`[flow] assign = "conductor"` and the line, both)."""
    configure(tmp_path, assign="next")
    save(tmp_path, [PILOT, round_of(1)])
    assert "auto-pilot" not in line_of(tmp_path, capsys)
    configure(tmp_path)
    save(tmp_path, [])
    assert "auto-pilot" not in line_of(tmp_path, capsys)


def test_ac7_a_saved_line_with_a_carriage_return_still_counts(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (a body from the browser ends its lines `\\r\\n`)."""
    configure(tmp_path)
    save(tmp_path, [comment(OWNER, "Auto-pilot: on\r\n")])
    assert "auto-pilot on" in line_of(tmp_path, capsys)


# --- the rounds (rule 13) ------------------------------------------------------------------------


def test_ac7_the_rounds_go_question_answer_question(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (each round waits for the person's answer)."""
    configure(tmp_path)
    head = f"{PHASE_2}; auto-pilot on; waits for"
    save(tmp_path, [PILOT])
    assert line_of(tmp_path, capsys) == f"{head} the conductor's `Discovery: round 1`"
    save(tmp_path, [PILOT, round_of(1)])
    assert line_of(tmp_path, capsys) == f"{head} the person's answer to round 1"
    save(tmp_path, [PILOT, round_of(1), comment(OWNER, PRIVATE_WORDS)])
    line = line_of(tmp_path, capsys)
    assert line == f"{head} the conductor's round 2 or the brief of docs/discovery/{SLUG}.md"
    save(tmp_path, [PILOT, round_of(1), comment(OWNER, "words"), round_of(2)])
    assert line_of(tmp_path, capsys) == f"{head} the person's answer to round 2"


@pytest.mark.parametrize(
    "item",
    [
        comment(STRANGER, "the answers"),
        comment(CONDUCTOR, "the answers"),
        comment(OWNER, "the answers", app="claude"),
        comment(OWNER, ""),
        comment(OWNER, SPEC_GO),
        comment(OWNER, "Auto-pilot: on"),
    ],
)
def test_ac7_only_a_person_answer_counts(tmp_path, capsys, item):
    """REQ-055 AC7: SPEC-0048 rule 13 (only a listed approver's comment is the person's)."""
    configure(tmp_path)
    save(tmp_path, [PILOT, round_of(1), item])
    assert line_of(tmp_path, capsys).endswith("waits for the person's answer to round 1")


def test_ac7_an_answer_before_the_round_answers_nothing(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (the answer comes after the question)."""
    configure(tmp_path)
    save(tmp_path, [PILOT, comment(OWNER, "early words"), round_of(1)])
    assert line_of(tmp_path, capsys).endswith("waits for the person's answer to round 1")


FOUR = THREE + "\n- data: what data?"


@pytest.mark.parametrize(
    "items, again",
    [
        ([round_of(1, FOUR)], 1),
        ([round_of(1, "\nno question listed")], 1),
        ([round_of(2)], 1),
        ([round_of(1), comment(OWNER, "words"), round_of(1)], 2),
    ],
)
def test_ac7_a_round_out_of_form_is_posted_again(tmp_path, capsys, items, again):
    """REQ-055 AC7: SPEC-0048 rule 13 (one comment per round, numbered, at most three questions)."""
    configure(tmp_path)
    save(tmp_path, [PILOT, *items])
    expected = f"waits for the conductor to post round {again} with one to three questions"
    assert line_of(tmp_path, capsys).endswith(expected)


def test_ac7_a_repost_in_form_clears_the_round_out_of_form(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (the later comment in form is the round)."""
    configure(tmp_path)
    save(tmp_path, [PILOT, round_of(1, FOUR), round_of(1)])
    assert line_of(tmp_path, capsys).endswith("waits for the person's answer to round 1")


@pytest.mark.parametrize(
    "items",
    [
        [PILOT, round_of(1, login=STRANGER)],
        [PILOT, round_of(1, login=OWNER)],
        [round_of(1), PILOT],
    ],
)
def test_ac7_a_round_counts_only_from_the_conductor_after_the_line(tmp_path, capsys, items):
    """REQ-055 AC7: SPEC-0048 rule 13 (the conductor posts the rounds, once it is turned on)."""
    configure(tmp_path)
    save(tmp_path, items)
    assert line_of(tmp_path, capsys).endswith("the conductor's `Discovery: round 1`")


def test_ac7_once_the_document_is_there_the_files_say_the_phase(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rules 1 and 13 (the briefs write the records; the rounds are over)."""
    configure(tmp_path)
    save(tmp_path, [PILOT, round_of(1)])
    discovery(tmp_path)
    expected = (
        f"#{NUMBER} {SLUG}: phase 3 research; auto-pilot on; waits for docs/research/{SLUG}.md"
    )
    assert line_of(tmp_path, capsys) == expected


# --- the go (rule 9) -----------------------------------------------------------------------------


def at_the_go(tmp_path: Path, screens: str = "no", top: str = "") -> None:
    configure(tmp_path, top=top)
    save(tmp_path, [PILOT])
    discovery(tmp_path, screens)
    record(tmp_path)
    if screens == "no":
        architecture(tmp_path, f"Demo: {DEMO}")
        demo(tmp_path)
    else:
        architecture(tmp_path)
        prototype(tmp_path)


def pull(tmp_path: Path, comments: list, files: tuple[str, ...] = (DESIGN,)) -> tuple[str, str]:
    write(tmp_path, "api/pr-9-comments.json", json.dumps(comments))
    write(tmp_path, "api/pr-9-files.json", json.dumps([{"filename": f} for f in files]))
    return "--pr", "9"


AT_GO = f"#{NUMBER} {SLUG}: phase 5 the go; auto-pilot on; waits for the go"
PAST_GO = (
    f"#{NUMBER} {SLUG}: phase 6 milestones and the stack; auto-pilot on;"
    " waits for the plan (rule 10), then the existing path (rule 11)"
)
PROTO = "docs/design/prototype/v1/index.html"


def test_ac4_the_line_on_the_pull_request_is_the_go(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rule 9 (without screens, the first spec's approval)."""
    at_the_go(tmp_path)
    assert line_of(tmp_path, capsys) == AT_GO
    assert line_of(tmp_path, capsys, *pull(tmp_path, [])) == AT_GO
    assert line_of(tmp_path, capsys, *pull(tmp_path, [comment(OWNER, SPEC_GO)])) == PAST_GO
    long_form = comment(OWNER, f"Approve: {HEAD} SPEC-0099")
    assert line_of(tmp_path, capsys, *pull(tmp_path, [long_form])) == PAST_GO


@pytest.mark.parametrize(
    "item",
    [
        comment(STRANGER, SPEC_GO),
        comment(CONDUCTOR, SPEC_GO),
        comment(OWNER, SPEC_GO, app="claude"),
        comment(OWNER, f"yes\n{SPEC_GO}"),
    ],
)
def test_ac4_only_the_owners_line_is_the_go(tmp_path, capsys, item):
    """REQ-055 AC4: SPEC-0048 rule 9 (a listed account, its first line, never an agent app)."""
    at_the_go(tmp_path)
    assert line_of(tmp_path, capsys, *pull(tmp_path, [item])) == AT_GO


def test_ac4_a_go_on_the_problem_issue_is_not_the_go(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rule 9 (the line is on the pull request that carries the artifact)."""
    at_the_go(tmp_path)
    save(tmp_path, [PILOT, comment(OWNER, SPEC_GO)])
    assert line_of(tmp_path, capsys) == AT_GO


def test_ac4_a_go_on_a_pull_request_without_the_artifact_is_not_the_go(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rule 9 (the pull request's saved files name the artifact)."""
    at_the_go(tmp_path)
    args = pull(tmp_path, [comment(OWNER, SPEC_GO)], files=("README.md",))
    assert line_of(tmp_path, capsys, *args) == AT_GO


def test_ac4_with_screens_the_go_is_both_lines(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rule 9 (until #459, the design line and the first spec's)."""
    at_the_go(tmp_path, "yes")
    both = [comment(OWNER, DESIGN_GO), comment(OWNER, SPEC_GO)]
    assert line_of(tmp_path, capsys, *pull(tmp_path, both[:1], (PROTO,))) == AT_GO
    assert line_of(tmp_path, capsys, *pull(tmp_path, both[1:], (PROTO,))) == AT_GO
    assert line_of(tmp_path, capsys, *pull(tmp_path, both, (PROTO,))) == PAST_GO


def test_ac4_screens_open_is_read_as_yes_for_the_go(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rules 8 and 9 (`open` is treated as `yes`)."""
    at_the_go(tmp_path, "open")
    assert line_of(tmp_path, capsys, *pull(tmp_path, [comment(OWNER, SPEC_GO)], (PROTO,))) == AT_GO


@pytest.mark.parametrize("bad", ["comments", "files"])
def test_ac4_a_named_pull_request_that_was_not_saved_is_refused(tmp_path, capsys, bad):
    """REQ-055 AC4: SPEC-0048 rules 9 and 15 (unknown is never the go)."""
    at_the_go(tmp_path)
    args = pull(tmp_path, [comment(OWNER, SPEC_GO)])
    (tmp_path / f"api/pr-9-{bad}.json").unlink()
    code, out = status(tmp_path, *args, capsys=capsys)
    assert code == 1 and f"pr-9-{bad}.json" in out and "phase 6" not in out


SOLO = 'review_mode = "solo"'


def solo_config(tmp_path: Path) -> None:
    write(
        tmp_path,
        "config/reviewers.yaml",
        f"spec_approvers: [{OWNER}]\nverdict_authors: [{OWNER}]\n",
    )


def confirmed(*lines: str, login: str = OWNER) -> dict:
    body = [
        f"Confirmed: {HEAD}",
        f"Verdict: cleared {HEAD}",
        *lines,
        "Shown:",
        "one",
        "two",
        "three",
        f"confirmed by {login} in a session at 2026-11-08T10:00:00Z",
    ]
    return comment(login, "\n".join(body))


def test_ac4_in_solo_mode_the_line_counts_inside_the_confirmation(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rules 9 and 13 (the person's `Confirmed:` comment holds the go)."""
    at_the_go(tmp_path, "yes", top=SOLO)
    solo_config(tmp_path)
    both = confirmed(SPEC_GO, DESIGN_GO)
    assert line_of(tmp_path, capsys, *pull(tmp_path, [both], (PROTO,))).endswith("(rule 11)")
    one = confirmed(SPEC_GO)
    assert line_of(tmp_path, capsys, *pull(tmp_path, [one], (PROTO,))).endswith("waits for the go")


def test_ac4_in_solo_mode_a_line_outside_a_confirmation_is_not_the_go(tmp_path, capsys):
    """REQ-055 AC4: SPEC-0048 rule 9 (a bare line, and a verdict that only looks confirmed)."""
    at_the_go(tmp_path, "no", top=SOLO)
    solo_config(tmp_path)
    bare = comment(OWNER, SPEC_GO)
    shaped = comment(OWNER, f"Verdict: cleared {HEAD}\n{SPEC_GO}")
    for item in (
        bare,
        shaped,
        confirmed(SPEC_GO) | {"performed_via_github_app": {"slug": "claude"}},
    ):
        assert line_of(tmp_path, capsys, *pull(tmp_path, [item])).endswith("waits for the go")


@pytest.mark.parametrize("top", ["", SOLO, 'execution = "local"'])
@pytest.mark.parametrize("assign", ["conductor", "next"])
def test_ac7_no_mode_passes_the_go_without_the_line(tmp_path, capsys, top, assign):
    """REQ-055 AC7: SPEC-0048 rule 13 (solo, team, local and auto-pilot all stop at the go)."""
    at_the_go(tmp_path, "no", top=top)
    if top == SOLO:
        solo_config(tmp_path)
    configure_keep = (tmp_path / "config/reviewers.yaml").read_text(encoding="utf-8")
    configure(tmp_path, assign=assign, top=top)
    (tmp_path / "config/reviewers.yaml").write_text(configure_keep, encoding="utf-8")
    line = line_of(tmp_path, capsys, *pull(tmp_path, []))
    assert line.endswith("waits for the go") and "phase 5" in line


# --- personal mode (rule 13) ---------------------------------------------------------------------


PERSONAL = '[personal]\nforge = "files"\n'


def test_ac7_a_sidecar_refuses_the_issue_entry(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (personal mode enters by `/agk:vision` only)."""
    write(tmp_path, "agk.toml", PERSONAL)
    api = save(tmp_path, [PILOT])
    issue = str(api / f"issue-{NUMBER}.json")
    answers = str(write(tmp_path, "in/answers.json", json.dumps({"answers": []})))
    root = ["--root", str(tmp_path)]
    for args in (
        ["status", "--date", TODAY, "--issue", "7", "--api-dir", str(api), *root],
        ["check-issue", "--issue", issue, *root],
        ["discovery-write", "--issue", issue, "--answers", answers, *root],
    ):
        assert front_door.main(args) == 1
        out = capsys.readouterr().out
        assert "rule 13" in out and "forge" in out and "example.com" not in out
    assert not (tmp_path / "docs/discovery").exists()


def test_ac7_a_sidecar_keeps_the_vision_door(tmp_path, capsys):
    """REQ-055 AC7: SPEC-0048 rule 13 (the vision door is not stopped by rule 13)."""
    write(tmp_path, "agk.toml", PERSONAL)
    idea = write(tmp_path, "in/idea.txt", "Orders at example.com are lost.")
    answers = write(tmp_path, "in/answers.json", json.dumps({"answers": []}))
    args = ["discovery-write", "--vision", str(idea), "--answers", str(answers)]
    front_door.main([*args, "--root", str(tmp_path)])
    assert "rule 13" not in capsys.readouterr().out


# --- the conductor's steps and the budget (answer 2) ---------------------------------------------


def test_ac7_the_conductor_file_carries_the_drive():
    """REQ-055 AC7: SPEC-0048 rule 13 (the steps are in the conductor's file)."""
    text = (KIT_ROOT / ".claude/agents/conductor.md").read_text(encoding="utf-8")
    start = text.index("Auto-pilot (REQ-055).")
    step = text[start : text.index("\n", start)]
    for needle in (
        '`[flow] assign = "conductor"`',
        "`Auto-pilot: on`",
        "`spec_approvers`",
        "`Discovery: round <n>`",
        "at most three",
        "never `Approve:`",
        "front_door.py status --issue",
    ):
        assert needle in step, needle


def test_ac7_the_session_rules_place_the_two_lines():
    """REQ-055 AC7: SPEC-0048 rule 13 and Q-S0048-4 (a session never posts the owner's line)."""
    text = (KIT_ROOT / "config/session-rules.md").read_text(encoding="utf-8")
    rule = next(ln for ln in text.splitlines() if ln.startswith("17. "))
    assert "On problem issues: only an approver posts `Auto-pilot: on`" in rule
    assert "the conductor posts `Discovery: round <n>`" in rule
