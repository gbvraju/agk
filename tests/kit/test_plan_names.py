"""One owner per new path, and free names from the feature (brief #1425, ADR-0598; REQ-050).

`plan_names.py` compares a brief's `Adds:` with the tree, every other open brief and every open
pull request, as the forge and the file systems compare paths, and names a free path from a base.
Recorded issue lists only, invented names, no network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import plan_names as pn  # noqa: E402
from common import CheckError  # noqa: E402


def brief(number: int, adds: str = "", touches: str = "src/other.py", taken: bool = False) -> dict:
    body = f'Sentence: "x"\nTouches: {touches}\n' + (f"Adds: {adds}\n" if adds else "")
    labels = [{"name": "agk-brief"}] + ([{"name": "agk:taken"}] if taken else [])
    return {"number": number, "body": body, "labels": labels}


def test_two_waiting_briefs_adding_the_same_folder_clash():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(1, "src/gaps2/"), brief(2, "src/gaps2/")])
    assert pn.clashes(2, ["src/gaps2/"], h) == [
        {"path": "src/gaps2/", "holder": "#1", "theirs": "src/gaps2/"}
    ]


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("src/gaps2/", "src/gaps2/api.py"),
        ("src/gaps2/api.py", "src/gaps2/"),
        ("src/gaps*", "src/gaps2/api.py"),
        ("Gaps2/", "gaps2/"),
        ("./x/", "x"),
        ("a\\\\b//c", "a/b/c"),
        ("src/gaps2/**", "src/gaps2/x.py"),
    ],
)
def test_covering_matches_in_both_directions(a, b):
    """REQ-050"""
    assert pn.covers(a, b) and pn.covers(b, a)


def test_unrelated_names_do_not_cover():
    """REQ-050"""
    assert not pn.covers("src/gaps2/", "src/gaps20/")
    assert not pn.covers("src/gaps2", "src/gaps")


def test_a_match_with_touches_alone_is_ordered_not_a_clash():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(1, touches="src/gaps2/api.py")])
    assert pn.clashes(2, ["src/gaps2/"], h) == []
    assert pn.orders(2, ["src/gaps2/"], h) == [{"path": "src/gaps2/", "brief": 1}]


def test_an_open_pull_request_and_the_tree_hold_a_path():
    """REQ-050"""
    h = pn.Holders(tree=["src/Gaps1/a.py"], pulls=[{"number": 9, "brief": 5, "added": ["src/g3.py"]}])
    assert pn.clashes(2, ["src/gaps1/"], h)[0]["holder"] == "main"
    assert pn.clashes(2, ["src/g3.py"], h)[0]["holder"] == "#9"
    assert pn.clashes(5, ["src/g3.py"], h) == []  # its own pull request


def test_files_added_by_rule_are_left_out():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(1, "changelog.d/brief-1.md, docs/adr/0001-x.md")])
    assert pn.clashes(2, ["changelog.d/brief-1.md", "docs/adr/0001-x.md"], h) == []


def test_windows_reserved_names_and_long_paths_are_refused():
    """REQ-050"""
    assert pn.name_problems("src/con/x.py") and pn.name_problems("src/nul.txt")
    assert pn.name_problems("a/" + "b" * 200)
    assert pn.name_problems("src/console/x.py") == []


def test_a_parked_brief_keeps_its_name_and_a_closed_one_releases_it():
    """REQ-050"""
    parked = brief(1, "src/gaps2/")
    parked["labels"].append({"name": "agk-parked"})
    assert pn.clashes(2, ["src/gaps2/"], pn.Holders(briefs=[parked]))
    assert pn.clashes(2, ["src/gaps2/"], pn.Holders(briefs=[])) == []  # closed: not listed


def test_the_m1_and_m7_rerun_gets_free_names():
    """REQ-050"""
    m1 = [brief(60, "src/access/gaps1/"), brief(66, "src/access/gaps2/", taken=True)]
    h = pn.Holders(briefs=m1)
    assert pn.free("src/access/gaps2/", h) == "src/access/gaps2-2/"
    assert pn.free("src/access/access-control-m7-api/", h) == "src/access/access-control-m7-api/"


def test_a_batch_is_named_in_one_pass():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(1, "src/ac-m1-api/")])
    assert pn.batch(["src/ac-m1-api", "src/ac-m1-api", "src/ac-m1-ui"], h) == [
        "src/ac-m1-api-2",
        "src/ac-m1-api-3",
        "src/ac-m1-ui",
    ]


def test_a_fix_suggestion_never_repeats_a_name_in_use():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(66, "src/gaps2/", taken=True), brief(565, "src/gaps1/")])
    assert pn.free("src/gaps2", h) not in ("src/gaps2", "src/gaps1")


def test_a_folder_touched_above_does_not_hold_a_new_name():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(1, touches="src/**")])
    assert pn.free("src/ac-m7-api/", h) == "src/ac-m7-api/"


def test_a_base_that_is_not_lower_case_is_refused():
    """REQ-050"""
    with pytest.raises(CheckError):
        pn.free("src/Gaps_2", pn.Holders())


def test_impact_says_who_renames():
    """REQ-050"""
    h = pn.Holders(
        briefs=[brief(565, "src/gaps1/"), brief(66, "src/gaps1/x.py", taken=True)],
        pulls=[{"number": 70, "brief": 66, "added": ["src/gaps1/x.py"], "body": ""}],
    )
    assert pn.impact("src/gaps1", h) == [
        "#565 brief: steward edits (not taken)",
        "#66 brief: fix list (taken)",
        "#70 pull request: fix list",
    ]


def test_an_older_clash_names_the_one_not_taken():
    """REQ-050"""
    found = pn.plan_clashes([brief(66, "src/gaps2/", taken=True), brief(565, "src/gaps2/")], {66})
    assert pn.clash_line(found[0]) == (
        "CLASH: #66 and #565 both add src/gaps2/; rename in the one not taken "
        "(#565, free: src/gaps2-2/)"
    )


def test_650_open_briefs_are_read_from_one_listing(tmp_path, monkeypatch):
    """REQ-050"""
    issues = [brief(n, f"src/f{n}/") for n in range(1, 651)]
    calls: list[str] = []

    def pages(endpoint):
        calls.append(endpoint)
        return issues if "/issues?" in endpoint else []

    monkeypatch.setattr(pn.session, "pages", pages)
    monkeypatch.setattr(pn.session, "repo_name", lambda root: "example/repo")
    import session_plan

    monkeypatch.setattr(session_plan, "tree_files", lambda root, ref=None: [])
    monkeypatch.setattr(session_plan, "_default_branch", lambda root: "main")
    h = pn.read_holders(tmp_path, None, None)
    assert len(h.briefs) == 650 and sum("/issues?" in c for c in calls) == 1
    assert pn.free("src/f7/", h) == "src/f7-2/"


def test_the_command_reads_saved_lists(tmp_path):
    """REQ-050"""
    (tmp_path / "i.json").write_text(json.dumps([brief(1, "src/gaps2/")]), encoding="utf-8")
    (tmp_path / "p.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.txt").write_text("src/gaps2\nsrc/gaps2\n", encoding="utf-8")
    common = ["--root", str(tmp_path), "--issues", str(tmp_path / "i.json")]
    common += ["--pulls", str(tmp_path / "p.json")]
    script = str(ROOT / "scripts" / "agk" / "plan_names.py")

    def cli(*args):
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, script, *args, *common], capture_output=True, text=True
        )

    assert cli("next", "--base", "src/gaps2/").stdout.strip() == "src/gaps2-2/"
    assert cli("batch", str(tmp_path / "b.txt")).stdout.split() == ["src/gaps2-2", "src/gaps2-3"]
    assert "#1 brief" in cli("impact", "src/gaps2").stdout
    assert cli("bogus").returncode == 2
