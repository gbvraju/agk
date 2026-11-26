"""The conductor reads the Tells sent to it (brief #1970, ADR-0823; REQ-037).

`conductor.tell_lines` gives `watch` and `sweep` their Tells: `watch` wakes on a new
`Tell: <conductor id>` by a listed author on the open `agk-conductor` issue, from the delta read or
one `since` GET; `sweep` prints each unread one once as `TELL <id> reply-to <steward|none>: <line>`
and moves the inbox mark only after it printed them. The GitHub responses are recorded copies with
invented logins and names; the settings are real `agk.toml` and `config/reviewers.yaml` files in a
temporary project; no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import conductor  # noqa: E402
from common import CheckError  # noqa: E402

REPO = "example/kit"
ISSUE = 204
STEWARD_ISSUE = 300
NOW = datetime(2026, 11, 26, 4, 30, tzinfo=UTC)
ME = "conductor-long"
STEWARD_SIGN = "\n\nWho: AGK steward\n"


def stamp(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def said(
    cid: int, text: str, minutes: float, who: str = "owner", issue: int = ISSUE, sign: str = ""
) -> dict:
    return {
        "id": cid,
        "user": {"login": who},
        "body": f"{text}{sign}",
        "created_at": stamp(minutes),
        "updated_at": stamp(minutes),
        "issue_url": f"https://api.github.example.com/repos/{REPO}/issues/{issue}",
    }


def reviewers(handle: str) -> str:
    return f'version: 1\nteams:\n  maintainers: {{github_team: "{handle}"}}\n'


@pytest.fixture
def gh(monkeypatch, tmp_path):
    """Recorded GitHub: `comments` of the agk-conductor issue, `steward` notes, the GETs made; a
    project folder with `agk.toml` and `config/reviewers.yaml` listing `@owner`."""
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "agk.toml").write_text('[flow]\ngithub_reads = "full"\n', encoding="utf-8")
    (root / "config" / "reviewers.yaml").write_text(reviewers("@owner"), encoding="utf-8")

    class Gh:
        comments: list[dict] = []
        steward: list[dict] = []
        gets: list[str] = []
        broken: set[str] = set()
        no_issue = False
        name: str | None = ME
        folder = root

    def pages(endpoint):
        Gh.gets.append(endpoint)
        if endpoint.startswith(f"repos/{REPO}/issues?state=open&labels=agk-conductor"):
            if "issues" in Gh.broken:
                return None
            return [] if Gh.no_issue else [{"number": ISSUE, "labels": [{"name": "agk-conductor"}]}]
        if endpoint.startswith(f"repos/{REPO}/issues/{ISSUE}/comments"):
            return None if "comments" in Gh.broken else list(Gh.comments)
        if endpoint.startswith(f"repos/{REPO}/issues?labels=agk-steward"):
            return [{"number": STEWARD_ISSUE}]
        if endpoint.startswith(f"repos/{REPO}/issues/{STEWARD_ISSUE}/comments"):
            return list(Gh.steward)
        return []

    monkeypatch.setattr(conductor.session, "pages", pages)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "inbox_mark", lambda root, me: tmp_path / f"in-{me}")
    monkeypatch.setattr(conductor, "own_name", lambda root: Gh.name)
    monkeypatch.setattr(conductor, "tell_now", lambda: NOW)
    monkeypatch.setattr(conductor, "TELL_ROOT", [root])
    monkeypatch.delenv("AGK_ROLE", raising=False)
    monkeypatch.delenv("AGK_SESSION", raising=False)
    conductor.TELL_ISSUE.clear()
    conductor.TELL_MARK.clear()
    return Gh


def sweep_tells(gh) -> list[str]:
    """The `sweep` reader; the mark moves as the sweep moves it, after the lines."""
    lines = conductor.tell_lines(gh.folder, REPO)
    conductor.tell_mark(gh.folder)
    return lines


def watch_tells(gh, since_minutes: float, delta: list | None = None) -> list[str]:
    since = NOW - timedelta(minutes=since_minutes)
    return conductor.tell_lines(gh.folder, REPO, since, delta)


def quiet_sweep(monkeypatch, fail_at_start: bool = False) -> None:
    """Every other reader of `sweep` answers nothing, so only its Tell lines print."""
    for name in (
        "proof_lines",
        "slot_lines",
        "stall_report",
        "unacted_lines",
        "owner_lines",
        "steward_lines",
        "held_builder_lines",
        "extra_conductor_lines",
        "main_folder_lines",
    ):
        monkeypatch.setattr(conductor, name, lambda *a, **k: [])
    monkeypatch.setattr(conductor, "branch_line", lambda *a: "main: green")
    monkeypatch.setattr(conductor.caps, "over_lines", lambda *a: [])
    monkeypatch.setattr(conductor.session, "gh", lambda *a, **k: {"default_branch": "main"})
    monkeypatch.setattr(conductor.session, "owner_wait_settings", lambda root: {})
    monkeypatch.setattr(conductor.session.STORE, "begin", lambda *a: None)

    def start_lines(*args):
        if fail_at_start:
            raise CheckError("the plan cannot be read")
        return []

    monkeypatch.setattr(conductor, "start_lines", start_lines)


def test_1970_watch_wakes_on_a_new_tell_in_full_with_one_since_get(gh):
    """REQ-037: brief #1970 answer 2; `full` reads only the comments since `since`."""
    gh.comments = [
        said(1, "Tell: conductor-long merge #21 on restart", 2),
        said(2, "Tell: cb22 merge the default branch", 2),
        said(3, "Tell: conductor-long an old one", 30),
        said(4, "Tell: conductor-long by a stranger", 1, who="stranger"),
    ]
    assert watch_tells(gh, 10) == [f"{ISSUE} Tell: conductor-long merge #21 on restart"]
    reads = [g for g in gh.gets if g.startswith(f"repos/{REPO}/issues/{ISSUE}/comments")]
    assert reads == [f"repos/{REPO}/issues/{ISSUE}/comments?since={stamp(10)}"]


def test_1970_watch_wakes_from_the_delta_read_without_another_get(gh):
    """REQ-037: brief #1970 answer 2; `delta` takes the Tells from the read already made."""
    delta = [
        said(5, "Tell: conductor-long asks for a builder", 1),
        said(6, "Tell: conductor-long on another issue", 1, issue=999),
    ]
    assert watch_tells(gh, 10, delta) == [f"{ISSUE} Tell: conductor-long asks for a builder"]
    assert not [g for g in gh.gets if f"issues/{ISSUE}/comments" in g]


def stub_watch(monkeypatch) -> None:
    for name in ("green_lines", "start_lines"):
        monkeypatch.setattr(conductor, name, lambda *a, **k: [])
    monkeypatch.setattr(conductor, "held_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "sweep_late", lambda *a: [])
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: [])


def test_1970_watch_once_ends_on_a_tell(gh, monkeypatch, capsys):
    """REQ-037: brief #1970 test: `watch --once` wakes on a new Tell to the lease name."""
    gh.comments = [said(7, "Tell: conductor-long re-review #30", 1)]
    stub_watch(monkeypatch)
    assert conductor.watch(gh.folder, NOW - timedelta(minutes=5), once=True) == 0
    assert capsys.readouterr().out.splitlines() == [f"{ISSUE} Tell: conductor-long re-review #30"]
    assert conductor.TELL_ROOT == [None] and conductor.TELL_ISSUE == {}


def test_1970_a_tell_wakes_the_watch_on_its_next_poll(gh, monkeypatch, capsys):
    """REQ-037: brief #1970 answer 5, `conductor_poll_seconds`: the same interval; the Tell
    posted during the first sleep ends the second poll."""
    (gh.folder / "agk.toml").write_text(
        '[flow]\ngithub_reads = "full"\nconductor_poll_seconds = 7\n', encoding="utf-8"
    )
    stub_watch(monkeypatch)
    slept: list[float] = []

    def sleep(seconds):
        slept.append(seconds)
        gh.comments = [said(8, "Tell: conductor-long restart cb22", 0.5)]

    monkeypatch.setattr(conductor.time, "sleep", sleep)
    assert conductor.watch(gh.folder, NOW - timedelta(minutes=5), once=False) == 0
    assert slept == [7]
    assert capsys.readouterr().out.splitlines() == [f"{ISSUE} Tell: conductor-long restart cb22"]


def test_1970_a_refused_github_reads_is_refused_naming_the_setting(gh):
    """REQ-037: brief #1970 answer 5: another value is refused as today, never the value."""
    (gh.folder / "agk.toml").write_text('[flow]\ngithub_reads = "sometimes"\n', encoding="utf-8")
    with pytest.raises(CheckError) as refused:
        conductor.watch(gh.folder, NOW, once=True)
    assert "github_reads" in str(refused.value) and "sometimes" not in str(refused.value)


def test_1970_sweep_prints_each_unread_tell_once_with_the_live_steward(gh):
    """REQ-037: brief #1970 answer 3; the mark moves as `inbox` moves it."""
    gh.steward = [said(50, "Started: steward st-agk-day 2026-11-26T04:00Z", 30, issue=300)]
    gh.comments = [
        said(10, "Tell: conductor-long merge #21 on restart", 40, sign=STEWARD_SIGN),
        said(11, "Tell: someone-else stop", 30, sign=STEWARD_SIGN),
        said(12, "Tell: conductor-long information only", 20, sign=STEWARD_SIGN),
    ]
    assert sweep_tells(gh) == [
        "TELL 10 reply-to st-agk-day: Tell: conductor-long merge #21 on restart",
        "TELL 12 reply-to st-agk-day: Tell: conductor-long information only",
    ]
    assert sweep_tells(gh) == []
    gh.comments.append(said(13, "Tell: conductor-long one more", 5, sign=STEWARD_SIGN))
    assert sweep_tells(gh) == ["TELL 13 reply-to st-agk-day: Tell: conductor-long one more"]


def test_1970_a_persons_tell_or_no_live_steward_says_reply_to_none(gh):
    """REQ-037: brief #1970 answer 3 and Q-CT-1 (fix list item 5, and item 1 on 66b79bc3): only a
    Tell signed `Who: AGK steward` names the steward; a person's, or one signed plain `Who: AGK`,
    names no session; a stale steward marker names none either."""
    gh.steward = [said(51, "Started: steward st-agk-day 2026-11-26T04:00Z", 30, issue=300)]
    gh.comments = [said(14, "Tell: conductor-long merge #21", 5)]
    assert sweep_tells(gh) == ["TELL 14 reply-to none: Tell: conductor-long merge #21"]
    plain = "\n\nWho: AGK\n"  # every comment `session.gh` posts: a terminal or a builder (item 1)
    gh.comments.append(said(23, "Tell: conductor-long merge #23", 4, sign=plain))
    assert sweep_tells(gh) == ["TELL 23 reply-to none: Tell: conductor-long merge #23"]
    gh.steward = [said(52, "Started: steward st-old 2026-11-26T01:00Z", 200, issue=300)]
    gh.comments.append(said(25, "Tell: conductor-long merge #22", 4, sign=STEWARD_SIGN))
    assert sweep_tells(gh) == ["TELL 25 reply-to none: Tell: conductor-long merge #22"]


def test_1970_the_conductor_id_is_the_lease_else_its_session(gh, monkeypatch):
    """REQ-037: brief #1970 answer 1; neither prints the one name line and reads no Tell."""
    gh.comments = [said(16, "Tell: conductor-x restart cb22", 5)]
    gh.name = None
    assert sweep_tells(gh) == ["TELL: no conductor name (lease)"]
    assert watch_tells(gh, 10) == []
    monkeypatch.setenv("AGK_SESSION", "conductor-x")
    assert sweep_tells(gh) == ["TELL: no conductor name (lease)"]
    monkeypatch.setenv("AGK_ROLE", "conductor")
    assert sweep_tells(gh) == ["TELL 16 reply-to none: Tell: conductor-x restart cb22"]


def test_1970_replace_me_lists_nobody_and_prints_the_author_line(gh):
    """REQ-037: brief #1970 answer 5: `@REPLACE-ME` in `config/reviewers.yaml` lists nobody."""
    reviewers_file = gh.folder / "config" / "reviewers.yaml"
    reviewers_file.write_text(reviewers("@REPLACE-ME"), encoding="utf-8")
    gh.comments = [said(17, "Tell: conductor-long merge #21", 5, who="replace-me")]
    assert sweep_tells(gh) == ["TELL: no listed author (verdict_authors)"]
    assert watch_tells(gh, 10) == []
    assert not any("replace-me" in line.lower() for line in sweep_tells(gh))


def test_1970_a_failed_read_prints_its_line_and_the_other_sweep_lines(gh, monkeypatch, capsys):
    """REQ-037: brief #1970 answer 3 (fix list items 2 and 6): `sweep` itself prints one line for
    a failed read of the issue list or of its comments, and every other line still prints."""
    quiet_sweep(monkeypatch)
    gh.broken = {"comments"}
    assert conductor.sweep(gh.folder) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "no open pull request",
        "main: green",
        f"TELL: the comments of #{ISSUE} cannot be read",
    ]
    gh.broken = {"issues"}
    conductor.TELL_ISSUE.clear()
    assert conductor.sweep(gh.folder) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "TELL: the open issues labelled agk-conductor cannot be read"
    assert watch_tells(gh, 10) == []
    gh.broken, gh.no_issue = set(), True  # no agk-conductor issue: no Tell, no line
    conductor.TELL_ISSUE.clear()
    assert conductor.sweep(gh.folder) == 0
    assert capsys.readouterr().out.splitlines() == ["no open pull request", "main: green"]


def test_1970_a_sweep_that_ends_early_leaves_its_tells_unread(gh, monkeypatch, capsys):
    """REQ-037: fix list item 1: the mark moves only after the sweep printed the Tells."""
    gh.comments = [said(18, "Tell: conductor-long merge #21", 5)]
    quiet_sweep(monkeypatch, fail_at_start=True)
    with pytest.raises(CheckError):
        conductor.sweep(gh.folder)
    assert capsys.readouterr().out == ""
    quiet_sweep(monkeypatch)
    assert conductor.sweep(gh.folder) == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        "TELL 18 reply-to none: Tell: conductor-long merge #21"
    )
    assert conductor.sweep(gh.folder) == 0
    assert "TELL" not in capsys.readouterr().out


SETTINGS = [
    '[flow]\nbuilder_start = "assign"\n',
    '[flow]\nbuilder_start = "start"\nmax_builders = 1\n',
    "[flow]\nauto_merge = false\n",
    "[flow]\nauto_merge = true\nmerge_queue = true\n",
    'pr_mode = "flow"\nreview_mode = "solo"\n',
    'pr_mode = "strict"\nreview_mode = "team"\n',
    'execution = "hosted"\n',
    'execution = "hybrid"\n',
    'execution = "pool"\n',
    'execution = "local"\n',
    "paused = true\n",
]


@pytest.mark.parametrize("settings", SETTINGS)
def test_1970_the_tell_lines_are_the_same_under_each_setting(gh, settings):
    """REQ-037: brief #1970 answer 5: no setting changes what is read; the conductor answers by
    its rules (the role file names the refusing setting in `not done:`)."""
    (gh.folder / "agk.toml").write_text(settings, encoding="utf-8")
    gh.comments = [said(19, "Tell: conductor-long merge #21", 5)]
    assert watch_tells(gh, 10) == [f"{ISSUE} Tell: conductor-long merge #21"]
    assert sweep_tells(gh) == ["TELL 19 reply-to none: Tell: conductor-long merge #21"]


def test_1970_paused_ends_the_conductor_before_any_read():
    """REQ-037: brief #1970 answer 5, `paused = true`: the role file's pause step comes first."""
    text = (KIT_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "agk paused" in text and text.index("agk paused") < text.index("Tells to you")


def test_1970_personal_mode_prints_no_tell_line(gh, monkeypatch):
    """REQ-037: brief #1970 answer 5: `forge = "files"` has no agk-conductor issue."""
    monkeypatch.setattr(conductor.common, "personal_table", lambda root: {"forge": "files"})
    gh.comments = [said(20, "Tell: conductor-long merge #21", 5)]
    assert sweep_tells(gh) == [] and watch_tells(gh, 10) == [] and gh.gets == []


def test_1970_the_reader_reads_the_first_words_it_pins(gh, monkeypatch):
    """REQ-037: brief #1970 answer 8 (fix list item 3): the reader takes its first word from
    `TELLS`, and the words the conductor wakes on are a closed list."""
    assert set(conductor.WAKES + conductor.TELLS) == {
        "Question:",
        "Report:",
        "Answer:",
        "Maintainer answer:",
        "Approve:",
        "Tell:",
    }
    gh.comments = [said(21, "Tell: conductor-long merge #21", 5)]
    monkeypatch.setattr(conductor, "TELLS", ("Note:",))
    assert watch_tells(gh, 10) == [] and sweep_tells(gh) == []


def test_1970_the_role_file_says_check_under_your_rules_or_answer():
    """REQ-037: brief #1970 answer 4 (fix list item 4): a Tell prompts a check, never a merge."""
    text = (KIT_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    paragraph = next((p for p in text.split("\n\n") if p.startswith("Tells to you")), "")
    for part in (
        "`TELL <comment id>",
        "reply-to",
        "not done:",
        "already done:",
        "acted|answered|noted",
        "Needs you",
        "never a verdict",
        "a reason to merge (session rule 38)",
        "only your own clearing verdict leads to a merge",
        "auto_merge off (principle 2)",
        "max_builders",
    ):
        assert part in paragraph, part
    assert "merge_cleared" not in paragraph
