"""A fix brief names its root cause and fix type, a redesign is the owner's choice by stage, and a
recurrence is counted on its parked root-cause brief (brief #2095, ADR-0870; REQ-037, REQ-066).

Saved briefs, a saved open-brief list and stub `gh` doubles stand in for GitHub; no network, no
model, invented data only (example.com).
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))

import brief_study  # noqa: E402
import steward_daily  # noqa: E402
import steward_evidence as ev  # noqa: E402

KEY = "time-from-a-guess"
CAUSE = (
    f"Root cause: {KEY}: the time was guessed; before: none: grep of open briefs;"
    " removed by: a clock"
)
HEAD = 'Sentence: "A clock."\n'
PATCH = f"{HEAD}Fix type: patch\n{CAUSE}\nRoot-cause: #40\nPriority: 1\nExpected: 1 hour\n"
REDESIGN = f"{HEAD}Fix type: redesign\n{CAUSE}\nPriority: 2\nExpected: 2 days\n"
ROOT = f"{HEAD}Fix type: root\n{CAUSE}\nPriority: 1\n"
TODAY = date(2026, 11, 28)


def tree(tmp_path: Path, fails_from: str | None = None) -> Path:
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "0007-clock.md").write_text("# ADR-0007\n", "utf-8")
    flow = f'[flow]\nbrief_study_fails_from = "{fails_from}"\n' if fails_from else ""
    (tmp_path / "agk.toml").write_text(flow, "utf-8")
    return tmp_path


def lines(body: str, root: Path) -> list[str]:
    return brief_study.root_cause_problems(body.splitlines(), root)


def held_brief(number: int, body: str) -> dict:
    return {"number": number, "body": body, "title": f"brief {number}"}


# --- answers 1 and 7: the lines ------------------------------------------------------------------


@pytest.mark.parametrize("body", [PATCH, REDESIGN, ROOT])
def test_req037_each_fix_type_with_its_lines_passes(tmp_path, body):
    """REQ-037: answer 1, one `Fix type:` and one `Root cause:`, `Root-cause:` only on a patch."""
    assert lines(body, tree(tmp_path)) == []


def test_req037_a_brief_that_fixes_nothing_is_not_held(tmp_path):
    """REQ-037: answer 1 (Q-RC-1), no fix line and no Priority 0: not a fix brief; the router's
    red-branch pair (`Advances: none`, `Priority: 0`) is never held (answer 7)."""
    root = tree(tmp_path)
    assert lines('Sentence: "A page."\nPriority: 1\n', root) == []
    assert lines("Advances: none\nPriority: 0\n", root) == []
    assert lines("Advances: REQ-001\nPriority: 0\n", root)  # a cause-naming Priority 0


@pytest.mark.parametrize(
    ("body", "setting"),
    [
        (PATCH.replace("Fix type: patch\n", "Fix type: patch\nFix type: root\n"), "Fix type:"),
        (PATCH.replace(CAUSE, CAUSE + "\n" + CAUSE), "Root cause:"),
        (PATCH.replace("Fix type: patch", "Fix type: hotfix"), "Fix type:"),
        (PATCH.replace(KEY, "Time From A Guess"), "Root cause:"),
        (PATCH.replace(KEY, "a" * 61), "Root cause:"),
        (PATCH.replace("; removed by: a clock", ""), "Root cause:"),
        (PATCH.replace("Root-cause: #40\n", ""), "Root-cause:"),
        (REDESIGN + "Root-cause: #40\n", "Root-cause:"),
        (ROOT + "Root-cause: #40\n", "Root-cause:"),
        (REDESIGN.replace("Priority: 2\n", ""), "Priority:"),
        (PATCH.replace("before: none: grep of open briefs", "before: ADR-0999"), "Root cause:"),
        (PATCH.replace("Fix type: patch\n", ""), "Fix type:"),
    ],
)
def test_req037_a_broken_line_fails_naming_the_line_never_its_text(tmp_path, body, setting):
    """REQ-037: answer 7, each edge case names its line as the setting, never the value."""
    found = lines(body, tree(tmp_path))
    assert found and all(x.startswith("study: ") for x in found)
    assert f"(setting: {setting})" in found[0]
    assert "Time From A Guess" not in found[0] and "hotfix" not in found[0]


def test_req037_an_existing_adr_in_before_passes(tmp_path):
    """REQ-037: answer 1, an `ADR-` id in `before:` must exist, as in `Prior:`."""
    body = PATCH.replace("before: none: grep of open briefs", "before: ADR-0007, #12")
    assert lines(body, tree(tmp_path)) == []


def result(tmp_path: Path, body: str, briefs, fails_from: str | None, number: int | None = None):
    root = tree(tmp_path, fails_from)
    return brief_study.study_result(body, root, number, today="2026-11-28", briefs=briefs)


def test_req037_the_lines_warn_before_the_day_and_fail_from_it(tmp_path):
    """REQ-037: answer 6, `[flow] brief_study_fails_from` holds them as the other study lines."""
    broken = PATCH.replace("Fix type: patch", "Fix type: hotfix")
    holder = [held_brief(40, REDESIGN)]
    fails, warns = result(tmp_path / "a", broken, holder, None)
    assert not any("Fix type:" in x for x in fails) and any("Fix type:" in x for x in warns)
    fails, warns = result(tmp_path / "b", broken, holder, "2026-12-14")
    assert not any("Fix type:" in x for x in fails)
    fails, _ = result(tmp_path / "c", broken, holder, "2026-11-01")
    assert any("(setting: Fix type:)" in x for x in fails)


# --- answer 2: one root-cause brief per cause ----------------------------------------------------


def test_req037_a_second_redesign_or_a_root_of_a_held_cause_fails_naming_the_holder(tmp_path):
    """REQ-037: answer 2 and Q-RC-6, the cause of open #40 takes `patch` with `Root-cause: #40`."""
    holder = [held_brief(40, REDESIGN)]
    for body in (REDESIGN, ROOT):
        found = brief_study.root_cause_open_problems(body, holder, 41)
        assert found == [
            "study: the cause has the open root-cause brief #40: write Fix type: patch and"
            " Root-cause: #40 (setting: Root cause:)"
        ]
    assert brief_study.root_cause_open_problems(REDESIGN, holder, 40) == []  # its own number


def test_req037_a_patch_naming_no_open_redesign_of_its_cause_fails(tmp_path):
    """REQ-037: answer 2 and 7, a closed or other-cause brief is no `Root-cause:` holder."""
    other = REDESIGN.replace(KEY, "stale-state")
    for briefs in ([], [held_brief(40, other)], [held_brief(40, PATCH)]):
        found = brief_study.root_cause_open_problems(PATCH, briefs, 41)
        assert found == [
            "study: the Root-cause: line names no open redesign brief of this cause"
            " (setting: Root-cause:)"
        ]
    assert brief_study.root_cause_open_problems(PATCH, [held_brief(40, REDESIGN)], 41) == []


def test_req037_with_no_cache_one_warning_and_never_a_failure(tmp_path):
    """REQ-037: answer 2, no plan cache gives one warning."""
    fails, warns = result(tmp_path, PATCH, None, "2026-11-01")
    assert not any("Root-cause:" in x for x in fails)
    assert warns.count("study: root causes not read (no plan cache)") == 1


def test_req037_the_command_lists_the_open_causes(tmp_path):
    """REQ-037: answer 2, `cause <key> #n` lines from `--open-briefs FILE`."""
    root = tree(tmp_path)
    (tmp_path / "brief.md").write_text(PATCH, "utf-8")
    (tmp_path / "open.json").write_text(json.dumps([held_brief(40, REDESIGN)]), "utf-8")
    run = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "brief_study.py"), str(tmp_path / "brief.md"), "--root",
         str(root), "--open-briefs", str(tmp_path / "open.json")],
        capture_output=True, text=True, cwd=tmp_path,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    assert f"cause {KEY} #40" in run.stdout.splitlines()


# --- answers 3 and 4: the decision packet --------------------------------------------------------


class Milestones:
    """A stub `gh`: the conductor issue and the open milestones, each call kept."""

    def __init__(self, conductor: bool, milestones: list | None) -> None:
        self.conductor, self.milestones, self.calls = conductor, milestones, []

    def __call__(self, method: str, endpoint: str, *rest):
        self.calls.append((method, endpoint))
        if "agk-conductor" in endpoint:
            return [{"number": 1}] if self.conductor else []
        if "milestones" in endpoint:
            return self.milestones
        raise AssertionError(endpoint)


DATED = [
    {"title": "v1 acceptance run", "due_on": "2026-12-04T08:00:00Z"},
    {"title": "v2", "due_on": "2027-02-01T08:00:00Z"},
    {"title": "old", "due_on": "2026-10-01T08:00:00Z"},
    {"title": "someday", "due_on": None},
]


def packet(tmp_path: Path, body: str, gh, briefs=(), redesign: str | None = None, triage=None):
    root = tree(tmp_path)
    return ev.root_cause(root, body, redesign, gh, TODAY, list(briefs), triage)


def value(found: list[str], key: str) -> str:
    return next(x for x in found if x.startswith(f"{key}: "))[len(key) + 2 :]


def test_req066_a_redesign_in_build_with_a_dated_release_recommends_the_patch(tmp_path):
    """REQ-066: answers 3 and 4, the earliest open milestone dated today or later."""
    gh = Milestones(True, DATED)
    code, found = packet(tmp_path, REDESIGN, gh, redesign=None)
    assert code == 3
    assert value(found, "cause") == KEY
    assert value(found, "open root-cause brief") == "none"
    assert value(found, "stage") == "build"
    assert value(found, "release") == "v1 acceptance run 2026-12-04"
    assert value(found, "recommend") == (
        "patch now; root-cause brief parked until after v1 acceptance run"
    )
    assert value(found, "cost") == "patch not stated; redesign 2 days"
    assert value(found, "reversible").startswith("a parked brief is unparked")
    assert value(found, "impact").startswith("this project ")
    assert len(gh.calls) == 2


def test_req066_the_kit_names_its_impact_on_the_kit_and_on_projects(tmp_path):
    """REQ-066: answer 3, in the kit the packet names both."""
    (tmp_path / "kit").mkdir()
    (tmp_path / "kit" / "agk-kit.mk").write_text("# kit\n", "utf-8")
    code, found = packet(tmp_path, PATCH.replace("Root-cause: #40\n", ""), Milestones(True, []),
                         redesign=REDESIGN)  # fmt: skip
    assert code == 3 and re.fullmatch(r"kit .+; projects .+", value(found, "impact"))
    assert value(found, "cost") == "patch 1 hour; redesign 2 days"


@pytest.mark.parametrize(
    ("conductor", "milestones", "recommend", "release"),
    [
        (False, DATED, "redesign now", "v1 acceptance run 2026-12-04"),
        (True, [DATED[2], DATED[3]], "redesign now", "none dated"),
        (True, None, "the owner decides", "unknown"),
    ],
)
def test_req066_the_recommendation_follows_the_stage_and_release(
    tmp_path, conductor, milestones, recommend, release
):
    """REQ-066: answer 4 and Q-RC-2, before build or with none dated: redesign; unread: owner."""
    code, found = packet(tmp_path, REDESIGN, Milestones(conductor, milestones))
    assert code == 3
    assert value(found, "recommend") == recommend and value(found, "release") == release


def test_req066_active_milestones_narrow_the_release(tmp_path):
    """REQ-066: answer 6, `[plan] active_milestones` set: the earliest dated active one."""
    root = tree(tmp_path)
    (root / "agk.toml").write_text('[plan]\nactive_milestones = ["v2"]\n', "utf-8")
    _, found = ev.root_cause(root, REDESIGN, None, Milestones(True, DATED), TODAY, [], None)
    assert value(found, "release") == "v2 2027-02-01"


def test_req066_root_recurrence_and_kit_defect_give_no_packet(tmp_path):
    """REQ-066: answers 3 and 6, each exit 0 with no packet."""
    gh = Milestones(True, DATED)
    assert packet(tmp_path / "a", ROOT, gh) == (
        0, ["no packet: the root-cause fix fits one brief"]
    )  # fmt: skip
    assert packet(tmp_path / "b", PATCH, gh, [held_brief(40, REDESIGN)]) == (
        0, ["recurrence: #40: file the patch with Root-cause: #40"]
    )  # fmt: skip
    assert packet(tmp_path / "c", REDESIGN, gh, triage="kit brief") == (
        0, ["kit defect: the cause is the kit's (steward_owner.py defect)"]
    )  # fmt: skip
    assert gh.calls == []


def test_req066_personal_mode_reads_no_github_and_the_plan_targets(tmp_path):
    """REQ-066: answer 6, `[personal]`: no GET; the release from `Target:` lines."""
    root = tree(tmp_path)
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', "utf-8")
    (root / "docs" / "plan").mkdir(parents=True)
    (root / "docs" / "plan" / "milestones.md").write_text(
        "# Milestones\n\n### M1 First release\nTarget: 2026-12-20\n", "utf-8"
    )
    gh = Milestones(True, DATED)
    code, found = ev.root_cause(root, REDESIGN, None, gh, TODAY, [], None)
    assert gh.calls == [] and code == 3
    assert value(found, "release") == "First release 2026-12-20"
    assert value(found, "stage") == "plan" and value(found, "recommend") == "redesign now"


# --- answer 5: the count and the owner's list ----------------------------------------------------


def test_req066_the_daily_list_raises_each_recurrence():
    """REQ-066: answer 5, one line per `Recurred:` comment of the day, or none, or unknown."""
    body = "Recurred: 3 times; newest #52 (2026-11-27)\n\nWho: AGK steward\n"
    comments = [{"id": 9, "body": body, "created_at": "2026-11-27T10:00:00Z",
                 "issue_url": "https://api.example.com/repos/acme/widgets/issues/40"}]  # fmt: skip
    days = [date(2026, 11, 26), date(2026, 11, 27)]
    text = steward_daily.daily_text(TODAY, days, comments, [], [])
    assert "Root cause recurred (2026-11-26): none" in text.splitlines()
    assert "Root cause recurred (2026-11-27): #40 3 times, newest #52" in text.splitlines()
    unread = steward_daily.daily_text(TODAY, days[1:], None, [], [])
    assert "Root cause recurred (2026-11-27): unknown" in unread.splitlines()


def test_req066_recurred_is_written_only_by_file_brief():
    """REQ-066: answer 9, the class stays closed: one writer of the `Recurred:` comment."""
    writers = [
        p.name for p in SCRIPTS.glob("*.py") if 'f"Recurred: {' in p.read_text(encoding="utf-8")
    ]
    assert writers == ["steward_owner.py"]
    text = (SCRIPTS / "steward_owner.py").read_text(encoding="utf-8")
    body = text[text.index("def file_brief(") :]
    body = body[: body.index("\ndef ", 1)]
    assert body.count("recurrence(") == 2  # filed, and printed in personal mode
    assert text.count("recurrence(") == 3  # its def and those two calls


class Posted:
    """`session.pages` and `post_file` recorded: #40's comments and each post."""

    def __init__(self, comments: list | None) -> None:
        self.comments, self.posts = comments, []

    def pages(self, endpoint: str):
        assert endpoint == "repos/acme/widgets/issues/40/comments"
        return self.comments

    def post(self, root, number, body, *rest):
        self.posts.append((number, body))
        return {"id": 1}


@pytest.mark.parametrize("personal", [False, True])
def test_req066_a_filed_patch_counts_one_recurrence_on_its_root_cause_brief(
    tmp_path, monkeypatch, personal
):
    """REQ-066: answer 5, k `Recurred:` comments give one `Recurred: k+1`; personal: printed."""
    import steward_owner

    root = tree(tmp_path)
    if personal:
        (root / "agk.toml").write_text('[personal]\nforge = "files"\n', "utf-8")
    seen = [{"body": "Recurred: 1 times; newest #45 (2026-11-20)\n\nWho: AGK steward\n"},
            {"body": "a note\n"}]  # fmt: skip
    stub = Posted(seen)
    monkeypatch.setattr(steward_owner.session, "repo_name", lambda root: "acme/widgets")
    monkeypatch.setattr(steward_owner.session, "pages", stub.pages)
    monkeypatch.setattr(steward_owner, "post_file", stub.post)
    now = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
    found = steward_owner.recurrence(root, PATCH, 52, now)
    if personal:
        assert stub.posts == [] and found[0].startswith("personal mode: the developer posts on #40")
    else:
        assert stub.posts == [
            (40, "Recurred: 2 times; newest #52 (2026-11-28)\n\nWho: AGK steward\n")
        ]
        assert found == ["recurred: #40 Recurred: 2 times; newest #52 (2026-11-28)"]
    assert steward_owner.recurrence(root, REDESIGN, 52, now) == []
    stub.comments = None
    if not personal:
        assert steward_owner.recurrence(root, PATCH, 52, now) == [
            "recurred: #40 comments cannot be read; nothing posted (count: unknown)"
        ]


# --- answer 6: triage ----------------------------------------------------------------------------


def test_req066_a_triaged_cause_without_its_lines_is_refused(tmp_path):
    """REQ-066: answer 6, a finding with `cause` and a brief text with no root-cause lines."""
    root = tree(tmp_path)
    modes = "Modes: github a; local b; personal c\n"
    finding = {"id": "F-1", "triage": "project brief", "why": "a bug", "cause": "the clock",
               "reproduced": "on main", "text": modes}  # fmt: skip
    found = ev.triage(finding, root)
    assert found["action"] == "refused"
    assert found["lines"] == [
        "refused: a fix brief names its root cause (rule 7; setting: Root cause:)"
    ]


def test_req066_the_utc_day_of_a_recurrence_is_the_filing_day():
    """REQ-066: answer 5, the `Recurred:` line's form."""
    import steward_owner

    now = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
    assert steward_owner.recurred_line(3, 52, now) == ("Recurred: 3 times; newest #52 (2026-11-28)")
