"""A cleared head in re-prove goes back to a builder (brief #1740, ADR-0725; SPEC-0050 rule 6).

The router's `agk:reprove` from the pull request's files and one compare of the head with the
default branch, its place in the order, the hand-over it becomes, the label lists that name it and
the plan that no longer counts it as ready. Saved GitHub answers only: no network, no model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import route  # noqa: E402
import session  # noqa: E402
import session_plan  # noqa: E402
import uninstall  # noqa: E402
from test_route import HEAD, REPO, facts, ok, proj, run_router, said, stub  # noqa: E402, F401

STEWARD = ".claude/agents/steward.md"
INDEXES = list(session_plan.SHARED_INDEXES)
CLEARED = said(1, "boss", f"Verdict: cleared {HEAD}")
READY = said(2, "builder", f"Report: {HEAD[:7]} ready for review")
HANDED = said(3, "builder", f"Report: {HEAD[:7]} handing over: blocked: owner-needed waits")
PUSHED = {"commit": {"committer": {"date": "2026-10-25T09:00:00Z"}}}


def changed(*paths: str, renamed_from: str | None = None) -> list[dict]:
    found = [{"filename": p, "status": "modified"} for p in paths]
    if renamed_from:
        found[-1].update(status="renamed", previous_filename=renamed_from)
    return found


def compare(*paths: str, ahead: int = 1, renamed_from: str | None = None) -> dict:
    return {"files": changed(*paths, renamed_from=renamed_from), "ahead_by": ahead}


def cleared(**kw) -> dict:
    """A cleared head with green checks and a ready Report (#1723 before #1719 merged)."""
    base = {
        "comments": [CLEARED, READY],
        "files": changed(STEWARD, "scripts/agk/steward.py"),
        "body": "Brief: #1715\n",
        "commit": PUSHED,
    }
    base.update(kw)
    return facts(**base)


# --- answer 1: the re-prove files from the compare ----------------------------------------------


def test_1740_1_a_file_both_change_is_a_full_reprove():
    """REQ-057: brief #1740 answer 1 (the files both change, shared-mechanical not exempt)."""
    mine = changed(STEWARD, "changelog.d/brief-1715.md")
    assert route.reprove_of(mine, compare(STEWARD), INDEXES, None) == ("full", [STEWARD])
    mech = compare("changelog.d/brief-1715.md")
    assert route.reprove_of(mine, mech, INDEXES, None) == ("full", ["changelog.d/brief-1715.md"])


def test_1740_7i_a_rename_on_the_default_branch_is_counted():
    """REQ-057: brief #1740 test 7 (i): renamed from or to."""
    moved = compare("docs/new.md", renamed_from=STEWARD)
    assert route.reprove_of(changed(STEWARD), moved, INDEXES, None) == ("full", [STEWARD])
    mine = changed("docs/x.md", renamed_from="docs/old.md")
    assert route.reprove_of(mine, compare("docs/old.md"), INDEXES, None) == (
        "full",
        ["docs/old.md"],
    )


def test_1740_7b_only_shared_indexes_is_light():
    """REQ-057: brief #1740 answer 1 and test 7 (b) (amendment 171)."""
    mine = changed("agk.toml", "scripts/agk/x.py")
    assert route.reprove_of(mine, compare("agk.toml"), INDEXES, None) == ("light", ["agk.toml"])
    # [flow] shared_indexes set without agk.toml: the same file is a full re-prove
    assert route.reprove_of(mine, compare("agk.toml"), ["docs/x.md"], None) == (
        "full",
        ["agk.toml"],
    )


def test_1740_7k_behind_counts_only_with_max_behind_merges_set():
    """REQ-057: brief #1740 answer 1 (Q-2) and test 7 (k)."""
    mine = changed(STEWARD)
    assert route.reprove_of(mine, compare("other.md", ahead=9), INDEXES, None) == ("none", [])
    assert route.reprove_of(mine, compare("other.md", ahead=9), INDEXES, 3) == ("behind", [])
    assert route.reprove_of(mine, compare("other.md", ahead=3), INDEXES, 3) == ("none", [])
    assert route.reprove_of(mine, compare("other.md", ahead=1), INDEXES, 0) == ("behind", [])


def test_1740_7j_a_compare_that_cannot_be_read_is_unknown():
    """REQ-057: brief #1740 answer 1 and test 7 (j): never a clean state."""
    assert route.reprove_of(changed(STEWARD), None, INDEXES, None) is None
    assert route.reprove_of(None, compare(STEWARD), INDEXES, None) is None
    assert route.reprove_of(changed(STEWARD), {"ahead_by": 1}, INDEXES, None) is None
    no_count = {"files": [], "ahead_by": None}
    assert route.reprove_of(changed(STEWARD), no_count, INDEXES, 2) is None


# --- answer 2: the order ------------------------------------------------------------------------


def test_1740_7a_1723s_facts_are_reprove_then_handover():
    """REQ-057: brief #1740 test 7 (a)."""
    assert route.decide(cleared()) == "agk:merge-ready"  # not read: today's state
    assert route.decide(cleared(reprove="full")) == "agk:reprove"
    assert route.pr_state(cleared(reprove="full"))[1] == "builder"
    handed = cleared(reprove="full", comments=[CLEARED, READY, HANDED])
    assert route.decide(handed) == "agk:handover"
    assert route.decide(cleared(reprove="behind")) == "agk:reprove"


def test_1740_7b_a_light_reprove_is_the_conductors_review():
    """REQ-057: brief #1740 test 7 (b) (Q-3)."""
    assert route.decide(cleared(reprove="light")) == "agk:review"


def test_1740_7c_to_7g_the_earlier_states_win():
    """REQ-057: brief #1740 answer 2 and tests 7 (c) to (g)."""
    assert route.decide(cleared(reprove="full", mergeable_state="dirty")) == "agk:conflict"
    assert route.decide(cleared(reprove="full", draft=True)) == "agk:build"
    fix = said(4, "boss", f"Verdict: fix list {HEAD}\n\n1. merge the default branch")
    assert route.decide(cleared(reprove="full", comments=[CLEARED, READY, fix])) == "agk:fix"
    parked = cleared(reprove="full", labels=["agk:parked"])
    assert route.decide(parked) == "agk:parked"
    ask = said(5, "boss", "Owner needed: Q-1715-3 which reading?")
    assert route.decide(cleared(reprove="full", comments=[CLEARED, READY, ask])) == "agk:question"
    red = {"name": "proof", "status": "completed", "conclusion": "failure"}
    assert route.decide(cleared(reprove="full", checks=[red])) == "agk:ci-red"


def test_1740_7h_an_owner_merge_ask_then_main_moves_is_reprove():
    """REQ-057: brief #1740 answer 4 and test 7 (h)."""
    command = route.OWNER_COMMAND.format(7)
    ask = said(6, "boss", f"Owner needed: cleared, held as outside author.\n\nRun: {command}\n")
    asked = cleared(number=7, comments=[CLEARED, READY, ask])
    assert route.decide(asked) == "agk:owner-merge"
    assert route.decide({**asked, "reprove": "full"}) == "agk:reprove"
    assert route.decide({**asked, "reprove": "light"}) == "agk:review"
    assert route.decide({**asked, "reprove": "full", "mergeable_state": "dirty"}) == "agk:conflict"
    owner = cleared(files=changed("constitution/principles.md"))
    assert route.decide(owner) == "agk:owner-merge"
    assert route.decide({**owner, "reprove": "full"}) == "agk:reprove"


def test_1740_7l_after_the_reprove_push_the_new_head_is_reviewed():
    """REQ-057: brief #1740 test 7 (l)."""
    new = "f" * 40
    ready = said(7, "builder", f"Report: {new[:7]} merge of main")
    after = cleared(head=new, comments=[CLEARED, READY, HANDED, ready], reprove="none")
    assert route.decide(after) == "agk:review"


# --- answer 5: the label lists ------------------------------------------------------------------


def test_1740_5_every_label_reader_lists_reprove():
    """REQ-057: brief #1740 answer 5."""
    assert route.ACTOR["agk:reprove"] == "builder"
    assert "agk:reprove" in route.BUILDER_STATES
    assert "agk:reprove" in route.LABELS
    assert route.COLORS["agk:reprove"]
    assert route.description_of("agk:reprove") == (
        "AGK: builder acts next: merge the default branch and re-prove"
    )
    assert "agk:reprove" in session.ROLES["builder"]
    assert "agk:reprove" in session.BUILDER_LABELS
    assert "agk:reprove" not in session.WAITING_LABELS
    assert "agk:reprove" in uninstall.LABELS
    labels = ROOT / "tests" / "kit" / "fixtures" / "doctor" / "ok" / "api" / "labels.json"
    named = {x["name"]: x["description"] for x in json.loads(labels.read_text(encoding="utf-8"))}
    assert named["agk:reprove"] == route.description_of("agk:reprove")
    for guide in ("security.md", "getting-started.md"):
        assert "`agk:reprove`" in (ROOT / "docs" / "guides" / guide).read_text(encoding="utf-8")


def test_1740_7n_the_plan_no_longer_counts_it_ready():
    """REQ-057: brief #1740 test 7 (n): the label the router gives is not a ready label."""
    label = route.decide(cleared(reprove="full"))
    assert label not in session_plan.READY_LABELS
    assert route.decide(cleared(reprove="none")) in session_plan.READY_LABELS


# --- the router reads the compare (answer 1; settings of answer 6) ------------------------------


def served(stub, files: list[dict], found) -> None:
    stub.pull(7)
    stub.fixtures[f"repos/{REPO}/pulls/7"]["body"] = "Brief: #1715\n"
    stub.serve("issues/7/comments", [CLEARED, READY])
    stub.serve("pulls/7/files", files)
    stub.serve(f"commits/{HEAD}", PUSHED)
    stub.serve(f"compare/{HEAD}...main", found)


def test_1740_the_router_reads_one_compare_and_labels_reprove(proj, stub, tmp_path):
    """REQ-057: brief #1740 answer 1 (the measured line: `#1723 agk:reprove`)."""
    served(stub, changed(STEWARD), compare(STEWARD))
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines()[0] == "#7 agk:reprove"
    reads = [c[1] for c in stub.calls() if "compare/" in c[1]]
    assert reads == [f"repos/{REPO}/compare/{HEAD}...main"]


def test_1740_7j_an_unreadable_compare_keeps_todays_state_and_says_so(proj, stub, tmp_path):
    """REQ-057: brief #1740 test 7 (j) in the job log."""
    served(stub, changed(STEWARD), "FAIL")
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines()[0] == "#7 agk:merge-ready"
    assert "re-prove: #7 unknown (cannot be read)" in out.stderr


def test_1740_no_compare_is_read_for_a_head_that_is_not_cleared(proj, stub, tmp_path):
    """REQ-057: brief #1740 answer 1 (only for a would-be cleared state)."""
    served(stub, changed(STEWARD), compare(STEWARD))
    stub.serve("issues/7/comments", [READY])
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.stdout.splitlines()[0] == "#7 agk:review"
    assert not [c for c in stub.calls() if "compare/" in c[1]]


@pytest.mark.parametrize(
    ("toml", "ahead", "label"),
    [
        ("", 9, "agk:merge-ready"),
        ("[flow]\nmax_behind_merges = 3\n", 9, "agk:reprove"),
        ("[flow]\nmax_behind_merges = 3\n", 3, "agk:merge-ready"),
        ("[flow]\nmax_behind_merges = 0\n", 1, "agk:reprove"),
    ],
)
def test_1740_6_max_behind_merges(proj, stub, tmp_path, toml, ahead, label):
    """REQ-057: brief #1740 answer 6 (`[flow] max_behind_merges` unset and set)."""
    (proj / "agk.toml").write_text(toml, encoding="utf-8")
    served(stub, changed(STEWARD), compare("docs/other.md", ahead=ahead))
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.stdout.splitlines()[0] == f"#7 {label}", out.stderr


@pytest.mark.parametrize(
    ("toml", "setting"),
    [
        ('[flow]\nmax_behind_merges = "two"\n', "max_behind_merges"),
        ("[flow]\nmax_behind_merges = -1\n", "max_behind_merges"),
        ('[flow]\nshared_indexes = ["docs/*.md"]\n', "shared_indexes"),
        ("[flow]\nshared_indexes = 3\n", "shared_indexes"),
    ],
)
def test_1740_6_a_bad_setting_is_refused_naming_it(proj, stub, tmp_path, toml, setting):
    """REQ-057: brief #1740 answer 6 (refused as today, naming the setting, never the value)."""
    (proj / "agk.toml").write_text(toml, encoding="utf-8")
    served(stub, changed(STEWARD), compare(STEWARD))
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.returncode != 0
    said_out = out.stdout + out.stderr
    assert setting in said_out
    assert "two" not in said_out and "docs/*.md" not in said_out


def test_1740_6_shared_indexes_set_decides_light(proj, stub, tmp_path):
    """REQ-057: brief #1740 answer 6 (`[flow] shared_indexes` set)."""
    (proj / "agk.toml").write_text('[flow]\nshared_indexes = ["docs/index.md"]\n', "utf-8")
    served(stub, changed("docs/index.md", STEWARD), compare("docs/index.md"))
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.stdout.splitlines()[0] == "#7 agk:review", out.stderr


def test_1740_6_auto_merge_off_still_labels(proj, stub, tmp_path):
    """REQ-057: brief #1740 answer 6 (`auto_merge = false`, `merge_queue`: the label informs)."""
    (proj / "agk.toml").write_text("[flow]\nauto_merge = false\nmerge_queue = true\n", "utf-8")
    served(stub, changed(STEWARD), compare(STEWARD))
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert out.stdout.splitlines()[0] == "#7 agk:reprove", out.stderr


def test_1740_the_router_creates_the_label_when_missing(proj, stub, tmp_path):
    """REQ-057: brief #1740 answer 5 (created when missing, as for the others)."""
    served(stub, changed(STEWARD), compare(STEWARD))
    out = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7")
    assert out.returncode == 0, out.stderr
    writes = stub.writes()
    assert writes[0][:2] == ["POST", f"repos/{REPO}/labels"]
    assert "name=agk:reprove" in writes[0][2]
    assert ["POST", f"repos/{REPO}/issues/7/labels"] == writes[1][:2]

