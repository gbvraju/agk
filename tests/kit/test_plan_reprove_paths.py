"""Prose that git merges by line never holds a brief; the later change re-proves (amendment 141).

Items 3 and 8 of amendment 141; REQ-057 AC1, AC3 and AC9. `[flow] reprove_paths` is one row of the
table of SPEC-0050 rule 3: `next`, `plan`, `claim` and the sweep read that table, the merge set and
the re-prove state do not. A `gh` stub serves saved JSON; invented briefs only; no network."""

from __future__ import annotations

import pytest
import session_plan
from common import CheckError
from test_session import ISSUES, REPO, Stub, comment, issue, listing, posts, session
from test_session_flow import DAY, PULLS, brief, flow, pr
from test_session_plan import changed, data, free, labelled, plan

GUIDE = "docs/guides/a.md"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def together(proj, stub, first: str, second: str) -> dict:
    """The plan of two free briefs, 5 and 6, with these `Touches:` entries."""
    listing(stub, [issue(5, brief(first)), issue(6, brief(second))])
    free(stub, 5, 6)
    return data(proj, stub)


def started(got: dict) -> list[int]:
    return [s["brief"] for s in got["start"]]


@pytest.mark.parametrize("path", [GUIDE, "README.md", ".claude/agents/conductor.md"])
def test_ac9_two_briefs_on_one_prose_file_start_together(proj, stub, path):
    """REQ-057 AC9: item 3, prose never holds, at any depth of the tree."""
    got = together(proj, stub, path, path)
    assert started(got) == [5, 6] and got["waits"] == []


@pytest.mark.parametrize("path", ["docs/specs/0001-x.md", "docs/adr/0001-x.md", "scripts/a.py"])
def test_ac9_specs_adrs_and_code_still_hold(proj, stub, path):
    """REQ-057 AC1: item 3, the last row of the table: everything else holds, as rule 2 says."""
    got = together(proj, stub, path, path)
    assert started(got) == [5] and got["waits"] == [
        {"brief": 6, "waits_for": 5, "why": f"both touch {path}"}
    ]


def test_ac9_prose_changed_by_an_open_pull_request_holds_nothing(proj, stub):
    """REQ-057 AC9: item 3, judged by `file_conflict` for a builder pull request too."""
    listing(stub, [issue(6, brief(GUIDE))])
    free(stub, 6)
    stub.serve(PULLS, [pr(20, 9)])
    changed(stub, 20, ("modified", GUIDE))
    got = data(proj, stub)
    assert started(got) == [6] and got["waits"] == []


def test_ac9_prose_of_a_taken_brief_holds_nothing(proj, stub):
    """REQ-057 AC9: item 3, judged by `clash` against a taken brief, and `claim` agrees."""
    listing(stub, [issue(5, brief(GUIDE)), issue(6, brief(GUIDE))])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: s-other {DAY}")])
    free(stub, 6)
    assert started(data(proj, stub)) == [6]
    out = session(proj, stub, "claim", "--session", "s-me", "--brief", "6")
    assert out.returncode == 0, out.stdout + out.stderr
    assert len([c for c in posts(stub) if c[1].endswith("/comments")]) == 1  # and the label


def test_ac9_a_set_list_replaces_the_default(proj, stub):
    """REQ-057 AC9: item 3, a project sets its own list; markdown then holds again."""
    flow(proj, 'reprove_paths = ["notes/*.txt"]')
    assert started(together(proj, stub, "notes/a.txt", "notes/a.txt")) == [5, 6]
    assert started(together(proj, stub, GUIDE, GUIDE)) == [5]


def test_ac9_a_bang_entry_takes_matches_away_in_order(proj, stub):
    """REQ-057 AC9: `Q-772-5`, the list is read in order, the last match decides."""
    flow(proj, 'reprove_paths = ["**/*.md", "!docs/keep/**", "docs/keep/open.md"]')
    assert started(together(proj, stub, "docs/keep/shut.md", "docs/keep/shut.md")) == [5]
    assert started(together(proj, stub, "docs/keep/open.md", "docs/keep/open.md")) == [5, 6]


@pytest.mark.parametrize("value", ['"zq-value"', "[7]", '["zq-value", ""]', '["!"]'])
def test_ac9_a_wrong_value_is_refused_naming_the_setting_never_the_value(proj, stub, value):
    """REQ-057 AC9: item 3, the plan stops by the setting's name."""
    flow(proj, f"reprove_paths = {value}")
    listing(stub, [issue(5, brief("a.py"))])
    free(stub, 5)
    out = plan(proj, stub)
    assert out.returncode != 0
    assert "flow.reprove_paths" in out.stdout + out.stderr
    assert "zq-value" not in out.stdout + out.stderr


def test_ac9_a_wildcard_all_of_whose_files_are_prose_holds_nothing(proj, stub):
    """REQ-057 AC9: item 3, a folder or wildcard is in a class when every file it matches is."""
    proj.commit({GUIDE: "a\n", "docs/guides/b.md": "b\n"})
    for entry in ("docs/guides/*.md", "docs/guides/"):
        assert started(together(proj, stub, entry, GUIDE)) == [5, 6]


def test_ac9_a_folder_with_one_held_file_still_holds(proj, stub):
    """REQ-057 AC1: item 3, one file outside the classes keeps the entry held."""
    proj.commit({GUIDE: "a\n", "docs/guides/b.py": "b\n"})
    assert started(together(proj, stub, "docs/guides/", "docs/guides/b.py")) == [5]


def test_ac9_a_wildcard_that_matches_no_file_is_held(proj, stub):
    """REQ-057 AC1: item 3, the safe side: nothing in the tree says it is prose."""
    proj.commit({"other.py": "o\n"})
    assert started(together(proj, stub, "notes/*.md", "notes/*.md")) == [5]


def test_ac9_shared_prose_is_still_merged_one_after_the_other(proj, stub):
    """REQ-057 AC9: item 3, `merge_set` counts it: the two do not merge together."""
    listing(stub, [])
    stub.serve(PULLS, [labelled(20, 7, "agk:ready"), labelled(21, 8, "agk:ready")])
    changed(stub, 20, ("modified", GUIDE))
    changed(stub, 21, ("modified", GUIDE))
    picked = data(proj, stub)["merge_set"]
    assert picked["together"] == [20] and picked["later"] == [
        {"pr": 21, "after": 20, "shares": GUIDE}
    ]


def test_ac9_the_re_prove_state_has_no_exemption_for_prose(repo):
    """REQ-057 AC9: item 3, rule 6 stands: a prose file both sides changed is named."""
    repo.commit({GUIDE: "a\n"})
    repo.git("branch", "work")
    repo.commit({GUIDE: "main\n"})
    main = repo.git("rev-parse", "HEAD").strip()
    repo.git("checkout", "-q", "work")
    repo.commit({GUIDE: "mine\n"})
    head = repo.git("rev-parse", "HEAD").strip()
    assert session_plan.reprove_files(repo.root, main, head) == [GUIDE]


def test_ac9_exempt_refuses_a_wrong_value(repo):
    """REQ-057 AC9: item 3, `next`, `plan` and `claim` read the list through `exempt`."""
    repo.write("agk.toml", '[flow]\nreprove_paths = "x"\n')
    with pytest.raises(CheckError, match="flow.reprove_paths"):
        session_plan.exempt(repo.root)


def test_ac5_the_rule_texts_say_a_re_prove_head_is_not_cleared_and_claim_refuses_overlap():
    """REQ-057 AC1 and AC5: build (e) of SPEC-0050, rules 4 and 7 in the instruction files."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    conductor = (root / ".claude/agents/conductor.md").read_text(encoding="utf-8")
    rules = (root / "config/session-rules.md").read_text(encoding="utf-8")
    item = "`merge the default branch and re-prove (rule 6 of SPEC-0050: <file> changed by #<m>)`"
    assert "re-prove state gets no clearing verdict" in conductor and item in conductor
    by_number = {ln.split(".", 1)[0]: ln for ln in rules.splitlines() if ln[:1].isdigit()}
    assert "`claim` refuses a brief that overlaps running work" in by_number["18"]
    assert "`skip #<n>: waits for ...`" in by_number["18"]
    assert "`Assign:` does not override it" in by_number["18"]
    ready = "re-prove state (SPEC-0050 rule 6) only after merging the default branch"
    assert ready in by_number["7"]
