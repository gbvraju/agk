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
    "Existing: none: `grep -rn login app/` gives 0 matches\n"  # brief #2065: a project's line
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
        self.filed: list = []
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
        if method == "POST" and endpoint == f"repos/{REPO}/issues/12/comments":
            self.filed.append(fields["body"][0])  # brief #2002: the approval on the filed brief
            return {"id": 2}
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
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "state" / "memory.json"))
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
    [
        ("", "[boss]"),
        ("[steward]\nfix_briefs = false\n", "[boss]"),
        (FIX_ON, "[boss, ann]"),
        (FIX_ON, "[]"),
    ],  # fmt: skip
)
def test_req066_fix_briefs_off_or_no_one_person_prints_the_proposed_body(root, setting, people):
    """REQ-066 AC5: answer 3, `fix_briefs` false by default (Q-1715-1), and solo mode with none or
    two people listed, print `Proposed body:` only."""
    base, _, gh, _ = root
    toml(base, SOLO + setting)
    one(base, people)
    code, lines = fix(base)
    assert code == 1 and lines[0] == "Proposed body: brief #5" and FIXED.strip() in "\n".join(lines)
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
    assert code == 0 and "nothing is posted" in lines[0] and FIXED.strip() in "\n".join(lines)
    code, lines = file(base, BODY, said="Yes, go ahead.")
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


def test_req066_the_real_brief_check_refuses_a_shapeless_draft(root, monkeypatch):
    base, _, gh, _ = root
    import importlib

    monkeypatch.setattr(check_brief, "body_problems", importlib.reload(check_brief).body_problems)
    code, lines = file(base, "Priority: 0\n")
    assert code == 2 and "brief check" in lines[0] and gh.created == []


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
    code, lines = file(base, BODY, said="Yes, go ahead.")
    assert code == 0, lines
    body = gh.created[0]["body"].rstrip().splitlines()
    assert body[-2:] == [f'Owner said ({AT}): "Yes, go ahead."', "Who: AGK steward"]
    code, lines = file(base, BODY, said="Not now, later.")
    assert code == 1 and len(gh.created) == 1


def test_req066_a_yes_older_than_four_owner_waits_is_refused(root):
    base, _, gh, _ = root
    toml(base, SOLO + "[flow]\nowner_wait_minutes = 10\n")
    old = (NOW - timedelta(minutes=41)).strftime("%Y-%m-%dT%H:%MZ")
    code, lines = file(base, BODY, said="Yes, go ahead.", at=old)
    assert code == 2 and "owner_wait_minutes" in lines[0] and gh.created == []
    toml(base, SOLO)  # unset: 24 hours
    assert file(base, BODY, said="Yes, go ahead.", at=old)[0] == 0
    toml(base, SOLO + "[flow]\nowner_wait_minutes = -1\n")
    with pytest.raises(CheckError) as caught:
        file(base, BODY, said="Yes, go ahead.")
    assert "owner_wait_minutes" in str(caught.value)


def test_req066_in_team_mode_only_a_spec_approvers_yes_counts(root):
    base, _, gh, _ = root
    toml(base, 'review_mode = "team"\n')
    code, lines = file(base, BODY, said="Yes, go ahead.", by="someone")
    assert code == 2 and "spec_approvers" in lines[0] and gh.created == []
    assert file(base, BODY, said="Yes, go ahead.", by="boss")[0] == 0


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
    toml(base, SOLO + f'execution = "{execution}"\n' + FIX_ON)
    assert fix(base)[0] == 0 and seen == [FIXED] and gh.patched == [FIXED]


# --- brief #1753 (ADR-0733): the owner's named yes, and never the same draft twice ---------------

NAME = "gate-runner test map"


def named(base: Path, said: str | None, name: str | None, text: str = BODY, title: str = ""):
    words = write(base, "said.txt", said + "\n") if said is not None else None
    return steward_owner.file_brief(
        base, write(base, "draft.md", text), title or "A person signs in", words, AT, None, NOW,
        name=name,
    )  # fmt: skip


@pytest.mark.parametrize(
    "said",
    [
        "Yes, file the gate-runner test map brief.",
        "yes file gate-runner test map",
        "YES, FILE THE  Gate-Runner Test Map  BRIEF",
        "Yes, brief the gate-runner test map",
        "yes brief gate-runner test map.",
    ],
)
def test_req066_a_named_yes_with_its_name_files_once_with_the_owner_said_line(root, said):
    """REQ-066: brief #1753 answer 1, the named yes the steward's list offered counts."""
    base, records, gh, _ = root
    code, lines = named(base, said, NAME)
    assert code == 0, lines
    assert len(gh.created) == 1 and lines[0] == "brief filed: #12 (agk-brief)"
    body = gh.created[0]["body"].rstrip().splitlines()
    assert body[-2:] == [f'Owner said ({AT}): "{said}"', "Who: AGK steward"]
    assert [kind for kind, _ in records] == ["Decision"]


@pytest.mark.parametrize(
    "said",
    [
        "Yes, file the checkout brief",  # another draft's name
        "Yes, file the gate-runner test map brief but later",  # a condition
        "Comprehensively think all scenarios then Yes, file the gate-runner test map brief",
        "file the gate-runner test map brief",  # Q-1753-1: no `yes`, no yes
        "Yes, file the gate-runner test map brief!!",
    ],
)
def test_req066_a_named_yes_for_another_name_or_with_a_condition_is_not_a_yes(root, said):
    """REQ-066: brief #1753 answers 1 and 2, a yes given for one draft never files another."""
    base, records, gh, _ = root
    code, lines = named(base, said, NAME)
    assert code == 1 and lines[-1] == "not a yes: nothing filed; ask again in other words"
    assert gh.created == [] and records == []


def test_req066_without_name_only_a_plain_yes_counts(root):
    """REQ-066: brief #1753 answer 1, with no `--name` the named form is not a yes, as before."""
    base, _, gh, _ = root
    code, lines = named(base, f"Yes, file the {NAME} brief", None)
    assert code == 1 and gh.created == []
    assert named(base, "Yes, go ahead.", None)[0] == 0


@pytest.mark.parametrize("name", ["", "a`b", "x" * 81, "two\nlines"])
def test_req066_a_malformed_name_is_refused_naming_the_setting_never_the_value(root, name):
    """REQ-066: brief #1753 answer 2."""
    base, _, gh, _ = root
    code, lines = named(base, f"Yes, file the {name} brief", name)
    assert code == 2 and lines[0].endswith("(setting: --name)") and gh.created == []
    if name:
        assert name not in lines[0]


def test_req066_name_without_said_is_refused_naming_the_setting(root):
    """REQ-066: brief #1753 answer 2, `--name` only ever qualifies the person's words."""
    base, _, gh, _ = root
    code, lines = named(base, None, NAME, BODY.replace("Priority: 1", "Priority: 0"))
    assert code == 2 and lines == ["refused: --name goes with --said (setting: --name)"]
    assert gh.created == []


def test_req066_approve_still_needs_a_plain_yes():
    """REQ-066: brief #1753 answer 1, `is_yes` (approve, relay) is unchanged by the named form."""
    import steward_voice

    assert not steward_voice.is_yes("Yes, file the checkout brief")
    assert steward_voice.is_yes("Yes, go ahead.")


def open_brief(number: int, title: str, body: str) -> dict:
    return {"number": number, "title": title, "body": body, "state": "open",
            "labels": [{"name": "agk-brief"}]}  # fmt: skip


@pytest.mark.parametrize("same", ["title", "body"])
def test_req066_a_second_filing_of_an_open_briefs_title_or_body_is_refused(root, same, monkeypatch):
    """REQ-066: brief #1753 answer 3, one GET listing of the open briefs, and nothing recorded."""
    base, records, gh, _ = root
    asked: list = []
    title = "  a PERSON   signs in " if same == "title" else "Another title"
    body = (
        BODY.replace("\nWho:", '\nOwner said (2026-11-22T07:00Z): "Yes, go ahead."\nWho:')
        if same == "body"
        else "Sentence: other.\n"
    )
    listed = [open_brief(4, title, body), {"number": 9, "pull_request": {}, "title": title}]
    monkeypatch.setattr(
        steward_owner.session, "pages", lambda endpoint: asked.append(endpoint) or listed
    )
    code, lines = named(base, "Yes, go ahead.", None)
    assert code == 2 and gh.created == [] and records == []
    assert lines == [
        "refused: #4 is an open brief with this title or body; nothing filed (setting: --title)"
    ]
    assert asked == [f"repos/{REPO}/issues?labels=agk-brief&state=open"]
    toml(base, SOLO + "[steward]\nauto_file = 1\n")
    code, lines = named(base, None, None)
    assert code == 2 and gh.created == [], "the auto_file path is held the same way"


def test_req066_another_open_brief_does_not_block_and_an_unreadable_list_fails_closed(
    root, monkeypatch
):
    """REQ-066: brief #1753 answers 3 and 7; a closed brief is not listed (state=open)."""
    base, _, gh, _ = root
    listed = [open_brief(4, "Something else", "Sentence: other.\n")]
    monkeypatch.setattr(steward_owner.session, "pages", lambda endpoint: listed)
    assert named(base, "Yes, go ahead.", None)[0] == 0 and len(gh.created) == 1
    monkeypatch.setattr(steward_owner.session, "pages", lambda endpoint: None)
    with pytest.raises(steward_owner.steward.Unreadable):
        named(base, "Yes, go ahead.", None)
    assert len(gh.created) == 1


def test_req066_personal_mode_reads_no_open_briefs(root, monkeypatch):
    """REQ-066: brief #1753 answer 5, personal mode prints the brief and makes no forge call."""
    base, _, gh, _ = root
    monkeypatch.setattr(steward_owner, "personal_table", lambda root: {"forge": "files"})
    monkeypatch.setattr(
        steward_owner.session, "pages", lambda endpoint: pytest.fail("a forge read")
    )
    code, lines = named(base, f"Yes, file the {NAME} brief.", NAME)
    assert code == 0 and lines[0].startswith("personal mode:") and gh.created == []


def test_req066_the_cli_passes_name_through(root, monkeypatch):
    """REQ-066: brief #1753 answer 1, `file-brief --name` reaches the command."""
    base, _, _, _ = root
    seen: dict = {}
    monkeypatch.setattr(steward_owner, "repo_root", lambda: base)
    monkeypatch.setattr(
        steward_owner, "file_brief", lambda *a, name=None, **k: seen.update(name=name) or (0, [])
    )
    draft = write(base, "draft.md", BODY)
    assert (
        steward_owner.main(["file-brief", "--file", str(draft), "--title", "T", "--name", NAME])
        == 0
    )
    assert seen == {"name": NAME}


# --- brief #1813 (ADR-0756): the steward runs the whole brief check, its study included ----------

STUDY = (
    "Impact:\nSpeed: none: one fix\nQuality: the login is checked\nGitHub: none: no change\n"
    "Cost: none: no Actions\nTests: one test file\nWiring: none: a new file\n"
    "Prior: none: searched docs/adr for login.py\nClass: a missing sign-in; seen 0 (searched)\n"
)
NO_CLASS = BODY.replace("\nWho:", STUDY.split("Class:")[0] + "\nWho:")


@pytest.mark.parametrize(
    "settings", [SOLO + FIX_ON, FIX_ON, SOLO + FIX_ON + '[personal]\nforge = "files"\n'],
    ids=["solo", "team", "personal"],
)  # fmt: skip
def test_req037_brief_refusal_reads_the_study_in_every_mode(root, monkeypatch, settings):
    """REQ-037 AC4: brief #1813 answers 1, 5 and 8 (team, solo and personal mode alike)."""
    import brief_study

    base, _, _, _ = root
    toml(base, settings)
    whole = BODY.replace("\nWho:", STUDY + "\nWho:")
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: None)
    warned: list[str] = []
    assert steward_owner.brief_refusal(base, NO_CLASS, 5, warned) is None
    assert any(x.startswith("warning: study: exactly one line Class:") for x in warned), warned
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: "2000-01-01")
    refusal = steward_owner.brief_refusal(base, NO_CLASS, 5)
    assert refusal is not None and "brief check" in refusal and "Class:" in refusal
    assert steward_owner.brief_refusal(base, whole, 5) is None


def test_req037_the_steward_prints_the_study_warnings_with_its_lines(root, monkeypatch):
    """REQ-037 AC4: brief #1813 answer 1 (the warnings follow the steward's own lines)."""
    import brief_study

    base, _, gh, _ = root
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: None)
    toml(base, SOLO + FIX_ON + '[personal]\nforge = "files"\n')
    code, lines = file(base, NO_CLASS, said="Yes, go ahead.")
    assert code == 0 and lines[0].startswith("personal mode:")
    assert lines[-1].startswith("warning: study:") and gh.calls == []
    monkeypatch.setattr(brief_study, "brief_study_fails_from", lambda _root: "2000-01-01")
    code, lines = file(base, NO_CLASS, said="Yes, go ahead.")
    assert code == 2 and "Class:" in lines[0]


# --- brief #2002 (ADR-0828): the owner's filing yes approves the amendment it names ---------------

import check_amendments  # noqa: E402

ITEMS = '> 1. **SPEC-0901 rule 2.** Append "x" (amendment 254).\n> Class: behaviour\n'
CHANGE = BODY.replace("Reserved: an ADR at take", "Reserved: amendment 254").replace(
    "\nWho:", "Spec fit: SPEC-0901 rule 2 change by amendment 254\n" + ITEMS + "\nWho:"
)
DIGEST = check_amendments.items_digest(ITEMS.replace("> ", ""))
NOT_AT_FILING = "amendment 254: not approved at filing (setting: Spec fit:)"


@pytest.fixture
def fits(root, monkeypatch):
    monkeypatch.setattr(check_brief, "spec_fit_problems", lambda *a, **k: ([], []))
    return root


def filing(
    base: Path, said: str | None, name: str | None = NAME, by: str | None = None, text: str = CHANGE
):
    words = write(base, "said.txt", said + "\n") if said is not None else None
    return steward_owner.file_brief(
        base, write(base, "draft.md", text), "A person signs in", words, AT, by, NOW, name=name
    )


def record_ask(
    base: Path, question: str, session: str = "steward-a", at: str = "2026-11-22T07:40Z"
):
    """The session's open ask, as `steward_owner.py ask` records it (the asks file)."""
    steward_owner.save_asks(base, [{"id": "Q-12-1", "question": question, "at": at,
                                    "open": True, "session": session}])  # fmt: skip


def test_req066_2002_a_spec_change_is_never_filed_under_auto_file(fits):
    """REQ-066: answers 5 and 9: whatever its priority, a change needs the person's yes."""
    base, _, gh, _ = fits
    code, lines = filing(base, None, name=None, text=CHANGE.replace("Priority: 1", "Priority: 0"))
    assert code == 1 and gh.created == []
    assert (
        lines[-1] == "not filed: a spec change needs the person's yes (setting: steward.auto_file)"
    )


def test_req066_2002_a_yes_naming_the_amendment_files_and_posts_the_approval_in_solo(fits):
    """REQ-066: answer 5: the named yes approves the amendment it names; in solo mode one
    comment on the filed brief in rule 5's form with the digest of the quoted items."""
    base, _, gh, _ = fits
    said = f"Yes, file the {NAME} brief with amendment 254"
    code, lines = filing(base, said)
    assert code == 0, lines
    assert len(gh.created) == 1 and len(gh.filed) == 1
    posted = gh.filed[0].rstrip().splitlines()
    assert (
        posted
        == [  # fix list 7202066567 item 5: `Owner said` second, as the steward guard reads
            "Maintainer answer: amendment 254 approved",
            f'Owner said ({AT}): "{said}"',
            'Asked: "file the A person signs in brief"',
            f"Text: {DIGEST}",
            "Who: ProductOwner",
        ]
    )
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "hooks"))
    import steward_guard  # noqa: PLC0415

    assert steward_guard.OWNER_SAID.match(posted[1])
    assert "approved at filing on #12: amendment 254" in lines


def test_req066_2002_a_yes_that_names_no_amendment_files_and_approves_nothing(fits):
    """REQ-066: answer 5: the brief is filed as today and the amendment is asked at merge."""
    base, _, gh, _ = fits
    code, lines = filing(base, f"Yes, file the {NAME} brief")
    assert code == 0 and len(gh.created) == 1 and gh.filed == []
    assert NOT_AT_FILING in lines
    code, lines = filing(base, f"Yes, file the {NAME} brief with amendment 999")
    assert code == 0 and gh.filed == [] and NOT_AT_FILING in lines


def test_req066_2002_a_plain_yes_counts_only_for_the_recorded_ask_naming_the_amendment(
    fits, monkeypatch
):
    """REQ-066: answer 5 and fix list 7202066567 item 1: a plain yes approves an amendment only
    when the session's recorded open ask named it; another session's ask, an ask newer than the
    yes and an ask naming none approve nothing, and the brief is still filed."""
    base, _, gh, _ = fits
    monkeypatch.setenv("AGK_SESSION", "steward-a")
    ask = "May I file the sign-in work with its rule change, amendment 254? I recommend yes."
    record_ask(base, ask)
    code, lines = filing(base, "Yes, go ahead.", name=None)
    assert code == 0 and len(gh.filed) == 1
    assert gh.filed[0].splitlines()[2] == f'Asked (2026-11-22T07:40Z): "{ask}"'
    for other in (
        dict(question=ask, session="steward-b"),
        dict(question=ask, at="2026-11-22T07:55Z"),
        dict(question="May I file the sign-in work? I recommend yes."),
    ):
        record_ask(base, **other)
        code, lines = filing(base, "Yes, go ahead.", name=None)
        assert code == 0 and len(gh.filed) == 1 and NOT_AT_FILING in lines
    steward_owner.save_asks(base, [])
    assert NOT_AT_FILING in filing(base, "Yes, go ahead.", name=None)[1]


def test_req066_2002_team_mode_prints_the_approval_for_a_spec_approver(fits):
    """REQ-066: answer 9: in team mode the steward posts no approval; it prints the two lines."""
    base, _, gh, _ = fits
    toml(base, 'review_mode = "team"\n')
    code, lines = filing(base, f"Yes, file the {NAME} brief with amendment 254", by="boss")
    assert code == 0 and len(gh.created) == 1 and gh.filed == []
    at = lines.index("post on #12 as a spec approver:")
    assert lines[at + 1 : at + 3] == [
        "Maintainer answer: amendment 254 approved",
        f"Text: {DIGEST}",
    ]


def test_req066_2002_no_spec_approver_approves_nothing_at_filing(fits):
    """REQ-066: answer 9: with no `spec_approvers` nothing can approve; the brief is filed."""
    base, _, gh, _ = fits
    (base / "config" / "reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [boss]\nspec_approvers: []\n", encoding="utf-8"
    )
    code, lines = filing(base, f"Yes, file the {NAME} brief with amendment 254")
    assert code == 0 and len(gh.created) == 1 and gh.filed == []
    assert "amendment 254: not approved at filing (setting: spec_approvers)" in lines


def test_req066_2002_personal_mode_prints_the_brief_and_the_approval(fits):
    """REQ-066: answer 9: `[personal]` prints the brief and the approval lines, posts nothing."""
    base, _, gh, _ = fits
    toml(base, SOLO + '[personal]\nforge = "files"\n')
    code, lines = filing(base, f"Yes, file the {NAME} brief with amendment 254")
    assert code == 0 and gh.created == [] and gh.filed == []
    assert "Maintainer answer: amendment 254 approved" in lines and f"Text: {DIGEST}" in lines
