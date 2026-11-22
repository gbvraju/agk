"""The steward fixes a brief's mechanical lines and files a draft the person said yes to as a
buildable brief (SPEC-0059 rules 6, 11 and 12; brief #1715, ADR-0714; REQ-066).

A recorded `gh` double stands in for GitHub (each call kept); no network, no model, invented data
only (example.com).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import check_brief  # noqa: E402
import session_plan  # noqa: E402
import steward_owner  # noqa: E402
from common import CheckError  # noqa: E402

REPO = "acme/widgets"
SEEN = "2026-11-22T07:00:00Z"
NEWER = "2026-11-22T07:05:00Z"
NOW = datetime(2026, 11, 22, 8, 0, tzinfo=UTC)
AT = "2026-11-22T07:50Z"
SOLO = 'review_mode = "solo"\n'
FIX_ON = "[steward]\nfix_briefs = true\n"
BODY = (
    'Sentence: "A person signs in on the login page."\n'
    "Evidence: traced on main at abc1234.\n"
    "Advances: REQ-001\n"
    "Priority: 1\n"
    "Touches: app/login.py\n"
    "Adds: tests/test_login.py\n"
    "Reserved: an ADR at take\n"
    "\nWho: AGK steward\n"
)
FIXED = BODY.replace("Adds: tests/test_login.py", "Adds: none").replace(
    "Reserved: an ADR at take", "Reserved: ADR-0001"
)


class GitHub:
    """`session.gh` recorded: one brief issue #5 and the issue list."""

    def __init__(self, **issue) -> None:
        self.issue = {
            "number": 5, "title": "A person signs in", "state": "open", "body": BODY,
            "updated_at": SEEN, "labels": [{"name": "agk-brief"}], **issue,
        }  # fmt: skip
        self.calls, self.comments, self.patched, self.created = [], [], [], []
        self.fail_comment = False

    @staticmethod
    def text(extra: tuple) -> dict:
        out = {}
        for i in range(0, len(extra) - 1, 2):
            key, _, value = extra[i + 1].partition("=")
            out.setdefault(key, []).append(
                Path(value[1:]).read_text(encoding="utf-8") if value.startswith("@") else value
            )
        return out

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint))
        fields = self.text(extra)
        if method == "GET" and endpoint == f"repos/{REPO}/issues/5":
            return dict(self.issue)
        if method == "POST" and endpoint == f"repos/{REPO}/issues/5/comments":
            if self.fail_comment:
                return None
            self.comments.append(fields["body"][0])
            return {"id": 1}
        if method == "PATCH" and endpoint == f"repos/{REPO}/issues/5":
            self.patched.append(fields["body"][0])
            self.issue.update(body=fields["body"][0], updated_at=NEWER)
            return dict(self.issue)
        if method == "POST" and endpoint == f"repos/{REPO}/issues":
            made = {"number": 12, "title": fields["title"][0], "body": fields["body"][0],
                    "labels": [{"name": n} for n in fields.get("labels[]", [])]}  # fmt: skip
            self.created.append(made)
            return made
        raise AssertionError((method, endpoint))


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "agk.toml").write_text(SOLO + FIX_ON, encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "neutrality.txt").write_text("zebracorp\n", encoding="utf-8")
    one(tmp_path, "[boss]")
    monkeypatch.delenv("AGK_STEWARD_START", raising=False)
    monkeypatch.setattr(steward_owner.session, "repo_name", lambda root: REPO)
    records: list = []
    monkeypatch.setattr(
        steward_owner.steward,
        "record",
        lambda r, kind, text, gh: records.append((kind, text)) or (0, ["recorded"]),
    )
    monkeypatch.setattr(check_brief, "body_problems", lambda body, root, waves, opened=None: [])
    comments: list = []
    monkeypatch.setattr(steward_owner.session, "pages", lambda endpoint: list(comments))
    gh = GitHub()
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    return tmp_path, records, gh, comments


def one(base: Path, people: str) -> None:
    (base / "config" / "reviewers.yaml").write_text(
        f"version: 1\nverdict_authors: {people}\nspec_approvers: {people}\n", encoding="utf-8"
    )


def write(base: Path, name: str, text: str) -> Path:
    path = base / name
    path.write_bytes(text.encode("utf-8"))
    return path


def fix(base: Path, text: str = FIXED, seen: str = SEEN):
    return steward_owner.fix_brief(base, 5, write(base, "new.md", text), seen)


def file(base: Path, text: str, said: str | None = None, by: str | None = None, at: str = AT):
    words = write(base, "said.txt", said + "\n") if said is not None else None
    return steward_owner.file_brief(
        base, write(base, "draft.md", text), "A person signs in", words, at, by, NOW
    )


def toml(base: Path, text: str) -> None:
    (base / "agk.toml").write_text(text, encoding="utf-8")


# --- answer 1: the mechanical fix ----------------------------------------------------------------


def test_req066_a_mechanical_fix_posts_the_old_body_then_the_new_one_and_one_note(root):
    """REQ-066 AC5: answer 1, `Body fixed:` with the old body first, then the body, then a note;
    the new `updated_at` is printed for a second fix in the same pass."""
    base, records, gh, _ = root
    code, lines = fix(base)
    assert code == 0, lines
    assert [c[0] for c in gh.calls] == ["GET", "POST", "PATCH"]
    assert gh.comments[0].startswith("Body fixed: #5") and BODY.strip() in gh.comments[0]
    assert gh.comments[0].rstrip().endswith("Who: AGK steward")
    assert gh.patched == [FIXED]
    assert len(records) == 1 and records[0][0] == "Decision" and "#5" in records[0][1]
    assert any(line == f"seen: {NEWER}" for line in lines)
    code, lines = fix(base, FIXED.replace("Adds: none", "Adds: tests/test_signin.py"), NEWER)
    assert code == 0, lines
    assert len(gh.patched) == 2


@pytest.mark.parametrize(
    "old, new",
    [
        ('Sentence: "A person signs in on the login page."', 'Sentence: "A person signs out."'),
        ("Priority: 1", "Priority: 0"),
        ("Advances: REQ-001", "Advances: REQ-002"),
        ("\nWho: AGK steward", "\nAnswers:\n1. Sign in.\n\nWho: AGK steward"),
    ],
)
def test_req066_any_other_change_is_printed_as_a_proposed_body_and_nothing_is_written(
    root, old, new
):
    """REQ-066 AC5: answer 1, a change outside the mechanical lines goes to the owner."""
    base, records, gh, _ = root
    code, lines = fix(base, FIXED.replace(old, new))
    assert code == 1 and lines[0] == "Proposed body: brief #5"
    assert gh.comments == [] and gh.patched == [] and records == []


def test_req066_an_unchanged_body_writes_nothing(root):
    base, _, gh, _ = root
    code, lines = fix(base, BODY)
    assert code == 0 and lines == ["#5: nothing to change"] and gh.patched == []


# --- answer 3: the settings ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "setting, people",
    [("", "[boss]"), ("[steward]\nfix_briefs = false\n", "[boss]"),
     (FIX_ON, "[boss, ann]"), (FIX_ON, "[]")],  # fmt: skip
)
def test_req066_fix_briefs_off_or_no_one_person_prints_the_proposed_body(root, setting, people):
    """REQ-066 AC5: answer 3, `fix_briefs` false by default (Q-1715-1), and solo mode with none or
    two people listed, print `Proposed body:` only."""
    base, _, gh, _ = root
    toml(base, SOLO + setting)
    one(base, people)
    code, lines = fix(base)
    assert code == 1 and lines[0] == "Proposed body: brief #5" and FIXED.strip() in lines
    assert gh.patched == [] and gh.comments == []


def test_req066_team_mode_prints_the_proposed_body(root):
    base, _, gh, _ = root
    toml(base, 'review_mode = "team"\n' + FIX_ON)
    code, lines = fix(base)
    assert code == 1 and "setting: review_mode" in lines[-1] and gh.patched == []


@pytest.mark.parametrize("value", ["1", "'yes'", "0"])
def test_req066_a_malformed_fix_briefs_is_refused_naming_the_setting(root, value):
    base, _, gh, _ = root
    toml(base, SOLO + f"[steward]\nfix_briefs = {value}\n")
    with pytest.raises(CheckError) as caught:
        fix(base)
    assert "(setting: steward.fix_briefs)" in str(caught.value) and "'yes'" not in str(caught.value)
    assert gh.calls == []


def test_req066_a_steward_the_conductor_started_fixes_and_files_nothing(root, monkeypatch):
    base, _, gh, _ = root
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    for code, lines in (fix(base), file(base, BODY.replace("Priority: 1", "Priority: 0"))):
        assert code == 2 and "setting: AGK_STEWARD_START" in lines[0]
    assert gh.calls == []


def test_req066_personal_mode_prints_and_patches_nothing(root):
    base, _, gh, _ = root
    toml(base, SOLO + FIX_ON + '[personal]\nforge = "files"\n')
    code, lines = fix(base)
    assert code == 0 and "nothing is posted" in lines[0] and FIXED.strip() in lines
    code, lines = file(base, BODY, said="Yes, file it.")
    assert code == 0 and "nothing is posted" in lines[0]
    assert gh.calls == []


def test_req066_another_forge_is_refused_naming_the_setting(root):
    base, _, gh, _ = root
    toml(base, SOLO + FIX_ON + '[personal]\nforge = "gitlab"\n')
    with pytest.raises(CheckError) as caught:
        fix(base)
    assert "personal.forge" in str(caught.value) and gh.calls == []


@pytest.mark.parametrize("layout", ["installed", "plugin"])
def test_req066_both_kit_layouts_fix_the_same_way(root, layout):
    base, _, gh, _ = root
    toml(base, SOLO + FIX_ON + f'[kit]\nlayout = "{layout}"\n')
    assert fix(base)[0] == 0 and gh.patched == [FIXED]


def test_req066_another_kit_layout_is_refused_naming_it(root):
    base, _, gh, _ = root
    toml(base, SOLO + FIX_ON + '[kit]\nlayout = "flat"\n')
    with pytest.raises(CheckError) as caught:
        fix(base)
    assert "layout" in str(caught.value) and "flat" not in str(caught.value) and gh.calls == []


# --- answer 4: the edge cases --------------------------------------------------------------------


@pytest.mark.parametrize(
    "issue, setting",
    [
        ({"updated_at": NEWER}, "--seen"),
        ({"labels": [{"name": "agk-brief"}, {"name": "agk:taken"}]}, "agk:taken"),
        ({"title": "Intake: a new idea"}, "Intake:"),
        ({"state": "closed"}, "state"),
        ({"labels": [{"name": "agk-steward"}]}, "agk-brief"),
    ],
)
def test_req066_an_edited_taken_intake_closed_or_unlabelled_brief_is_refused(root, issue, setting):
    """REQ-066 AC5: answer 4, the brief as read is the brief fixed, and its builder owns a take."""
    base, _, gh, _ = root
    gh.issue.update(issue)
    code, lines = fix(base)
    assert code == 2 and setting in lines[0], lines
    assert gh.patched == [] and gh.comments == []


def test_req066_an_unreleased_take_is_refused(root):
    base, _, gh, comments = root
    comments.append({"body": "taken: cb1 2026-11-22T06:00Z"})
    assert fix(base)[0] == 2
    comments.append({"body": "released: cb1"})
    assert fix(base)[0] == 0 and gh.patched == [FIXED]


def test_req066_a_new_body_that_fails_the_brief_check_writes_nothing(root, monkeypatch):
    base, _, gh, _ = root
    monkeypatch.setattr(check_brief, "body_problems", lambda *a, **k: ["rule 2: no Sentence"])
    code, lines = fix(base)
    assert code == 2 and "brief check" in lines[0] and gh.calls[-1][0] == "GET"
    code, lines = file(base, BODY.replace("Priority: 1", "Priority: 0"))
    assert code == 2 and gh.created == []


def test_req066_the_real_brief_check_refuses_a_shapeless_body(root, monkeypatch):
    monkeypatch.undo()  # the real check, nothing patched but GitHub
    base, _, gh, _ = root
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    monkeypatch.setattr(steward_owner.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(steward_owner.session, "pages", lambda endpoint: [])
    code, lines = fix(base, "Adds: none\n")
    assert code == 2 and gh.patched == []


def test_req066_a_neutrality_token_refuses_naming_the_list_never_the_token(root):
    base, _, gh, _ = root
    code, lines = fix(base, FIXED.replace("Adds: none", "Adds: docs/zebracorp.md"))
    assert code == 2 and "config/neutrality.txt" in lines[0] and "zebracorp" not in lines[0]
    assert gh.patched == []


def test_req066_an_unreadable_issue_fails_closed(root):
    base, _, gh, _ = root
    gh.issue = None
    gh.__class__ = type("Down", (GitHub,), {"__call__": lambda self, *a, **k: None})
    with pytest.raises(steward_owner.steward.Unreadable):
        fix(base)


def test_req066_a_failed_body_fixed_post_writes_no_body(root):
    base, records, gh, _ = root
    gh.fail_comment = True
    with pytest.raises(CheckError):
        fix(base)
    assert gh.patched == [] and records == []


# --- answer 2: filing as a brief -----------------------------------------------------------------


def test_req066_a_draft_at_or_below_auto_file_is_filed_as_a_brief(root):
    """REQ-066 AC5: answer 2, `Priority: 0` at the default `auto_file` opens one `agk-brief`."""
    base, records, gh, _ = root
    code, lines = file(base, BODY.replace("Priority: 1", "Priority: 0"))
    assert code == 0, lines
    assert [x["labels"] for x in gh.created] == [[{"name": "agk-brief"}]]
    assert lines[0] == "brief filed: #12 (agk-brief)" and records[0][0] == "Decision"


def test_req066_a_draft_above_auto_file_with_no_yes_is_printed_and_not_filed(root):
    base, _, gh, _ = root
    code, lines = file(base, BODY)
    assert code == 1 and "setting: steward.auto_file" in lines[-1] and gh.created == []
    toml(base, SOLO + "[steward]\nauto_file = false\n")
    code, lines = file(base, BODY.replace("Priority: 1", "Priority: 0"))
    assert code == 1 and gh.created == []


def test_req066_the_persons_yes_files_it_with_the_owner_said_line(root):
    base, _, gh, _ = root
    code, lines = file(base, BODY, said="Yes, file it.")
    assert code == 0, lines
    body = gh.created[0]["body"].rstrip().splitlines()
    assert body[-2:] == [f'Owner said ({AT}): "Yes, file it."', "Who: AGK steward"]
    code, lines = file(base, BODY, said="Not now, later.")
    assert code == 1 and len(gh.created) == 1


def test_req066_a_yes_older_than_four_owner_waits_is_refused(root):
    base, _, gh, _ = root
    toml(base, SOLO + "[flow]\nowner_wait_minutes = 10\n")
    old = (NOW - timedelta(minutes=41)).strftime("%Y-%m-%dT%H:%MZ")
    code, lines = file(base, BODY, said="Yes, file it.", at=old)
    assert code == 2 and "owner_wait_minutes" in lines[0] and gh.created == []
    toml(base, SOLO)  # unset: 24 hours
    assert file(base, BODY, said="Yes, file it.", at=old)[0] == 0
    toml(base, SOLO + "[flow]\nowner_wait_minutes = -1\n")
    with pytest.raises(CheckError) as caught:
        file(base, BODY, said="Yes, file it.")
    assert "owner_wait_minutes" in str(caught.value)


def test_req066_in_team_mode_only_a_spec_approvers_yes_counts(root):
    base, _, gh, _ = root
    toml(base, 'review_mode = "team"\n')
    code, lines = file(base, BODY, said="Yes, file it.", by="someone")
    assert code == 2 and "spec_approvers" in lines[0] and gh.created == []
    assert file(base, BODY, said="Yes, file it.", by="boss")[0] == 0


@pytest.mark.parametrize("pr_mode", ["strict", "flow"])
@pytest.mark.parametrize("assign", ["next", "conductor"])
@pytest.mark.parametrize("start", ["start", "assign"])
def test_req066_a_filed_brief_is_offered_by_the_plan_in_each_flow(root, pr_mode, assign, start):
    """REQ-066 AC5: answer 3, `pr_mode`, `[flow] assign` and `builder_start` are not read: the
    filed issue carries the plan's own label and the plan's filter keeps it."""
    base, _, gh, _ = root
    flow = f'[flow]\nassign = "{assign}"\nbuilder_start = "{start}"\n'
    toml(base, SOLO + f'pr_mode = "{pr_mode}"\n' + flow)
    assert file(base, BODY.replace("Priority: 1", "Priority: 0"))[0] == 0
    made = gh.created[-1]
    assert steward_owner.session.LABEL in session_plan.label_names(made)
    assert session_plan.plan_briefs([made]) == [made]


@pytest.mark.parametrize("execution", ["hosted", "hybrid", "pool", "local"])
def test_req066_each_execution_fixes_the_same_way_with_the_brief_check_in_the_command(
    root, execution, monkeypatch
):
    """REQ-066 AC5: answer 3, where no GitHub job runs the in-command brief check is the check."""
    base, _, gh, _ = root
    seen: list = []
    monkeypatch.setattr(check_brief, "body_problems", lambda body, *a, **k: seen.append(body) or [])
    toml(base, SOLO + FIX_ON + f'execution = "{execution}"\n')
    assert fix(base)[0] == 0 and seen == [FIXED] and gh.patched == [FIXED]
