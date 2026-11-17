"""A suggested rename is always a free name (brief #1441, ADR-0602; REQ-050).

`conductor.py check-verdict` reads every numbered fix item and every `MALFORMED` line of a verdict
for `rename <old> to <new>` and refuses a `<new>` that `plan_names.py` holds, naming the item, the
holder and a free name. `plan_names.py impact` matches a path only at a whole segment. Recorded
lists only, invented names, no network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import conductor  # noqa: E402
import plan_names as pn  # noqa: E402

SHA = "a" * 40
SCRIPT = ROOT / "scripts" / "agk" / "conductor.py"


def brief(number: int, adds: str = "", touches: str = "src/other.py") -> dict:
    body = f'Sentence: "x"\nTouches: {touches}\n' + (f"Adds: {adds}\n" if adds else "")
    return {"number": number, "body": body, "labels": [{"name": "agk-brief"}]}


def fix(*items: str) -> str:
    lines = [f"{n}. {text} (rule: none)" for n, text in enumerate(items, 1)]
    return f"Verdict: fix list {SHA}\n\n" + "\n".join(lines) + "\n"


def problems(body: str, h: pn.Holders, own: int | None = None) -> list[str]:
    return conductor.rename_problems(body, h, own)


def test_a_free_new_name_passes():
    """REQ-050"""
    h = pn.Holders(tree=["src/gaps1/a.py"], briefs=[brief(7, "src/gaps2/")])
    assert problems(fix("rename src/gaps1 to src/access-control-m7-api"), h) == []


def test_a_name_an_open_brief_adds_is_refused_with_a_free_name():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(7, "src/gaps2/")])
    assert problems(fix("Keep the tests.", "rename `src/gaps1/` to `src/gaps2/`."), h) == [
        "brief #1441 answer 1: item 2 renames to src/gaps2/, held by #7 (src/gaps2/); "
        "free: src/gaps2-2/"
    ]


def test_a_name_under_another_briefs_added_folder_is_refused_at_that_folders_level():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(7, "src/gaps2/")])
    assert problems(fix("rename src/old/api.py to src/gaps2/api.py"), h) == [
        "brief #1441 answer 1: item 1 renames to src/gaps2/api.py, held by #7 (src/gaps2/); "
        "free: src/gaps2-2/"
    ]


def test_a_name_another_brief_only_touches_above_passes():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(7, touches="src/")])
    assert problems(fix("rename src/gaps1 to src/gaps9"), h) == []
    below = pn.Holders(briefs=[brief(7, touches="src/gaps9/x.py")])
    assert problems(fix("rename src/gaps1 to src/gaps9"), below)[0].startswith(
        "brief #1441 answer 1: item 1 renames to src/gaps9, held by #7 (src/gaps9/x.py)"
    )


def test_a_case_only_difference_is_refused():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(7, "src/Gaps2/")], pulls=[])
    assert problems(fix("rename src/gaps1 to src/gaps2"), h)[0].endswith("free: src/gaps2-2")


def test_the_pull_requests_own_brief_is_left_out():
    """REQ-050: answer 2."""
    h = pn.Holders(
        briefs=[brief(5, "src/gaps2/")],
        pulls=[{"number": 9, "brief": 5, "added": ["src/gaps2/a.py"]}],
    )
    body = fix("rename src/gaps1 to src/gaps2")
    assert problems(body, h, own=5) == []
    assert problems(body, h)[0].startswith("brief #1441 answer 1: item 1")


def test_a_malformed_line_is_read_too():
    """REQ-050"""
    h = pn.Holders(pulls=[{"number": 9, "brief": 4, "added": ["src/gaps2/a.py"]}])
    body = f"Verdict: fix list {SHA}\n\nMALFORMED: #12 rule 4: rename src/gaps1 to src/gaps2\n"
    assert problems(body, h) == [
        "brief #1441 answer 1: a MALFORMED line renames to src/gaps2, held by #9 "
        "(src/gaps2/a.py); free: src/gaps2-2"
    ]


def test_the_plans_clash_name_passes_the_check():
    """REQ-050: answer 4, the plan names a free name only from `plan_names.free`."""
    briefs = [brief(66, "src/gaps2/"), brief(565, "src/gaps2/")]
    found = pn.plan_clashes(briefs, {66})[0]
    rest = pn.Holders(briefs=[b for b in briefs if b["number"] != found["rename"]])
    body = fix(f"rename src/gaps2/ to {found['free']}")
    assert problems(body, rest) == []


def test_a_cleared_verdict_and_prose_without_the_form_are_not_read():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(7, "src/gaps2/")])
    assert problems(f"Verdict: cleared {SHA}\n\nrename src/a to src/gaps2\n", h) == []
    assert problems(fix("Rename the folder; src/gaps2 is taken."), h) == []


def test_impact_matches_a_whole_segment_only():
    """REQ-050: answer 5."""
    h = pn.Holders(
        briefs=[brief(1, "src/gaps10/"), brief(2, "src/gaps1/x.py"), brief(3, "src/gaps1.")]
    )
    assert pn.impact("src/gaps1", h) == [
        "#2 brief: steward edits (not taken)",
        "#3 brief: steward edits (not taken)",
    ]


def cli(tmp_path: Path, body: str, *extra: str):
    path = tmp_path / "v.md"
    path.write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "check-verdict", str(path), "--root", str(tmp_path), *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_with_no_cache_and_no_file_the_tree_alone_is_compared(tmp_path):
    """REQ-050"""
    (tmp_path / "src" / "gaps3").mkdir(parents=True)
    (tmp_path / "src" / "gaps3" / "a.py").write_text("x\n", encoding="utf-8")
    held = cli(tmp_path, fix("rename src/gaps1 to src/gaps3"))
    assert held.returncode == 1, held.stderr
    assert held.stdout.strip() == (
        "brief #1441 answer 1: item 1 renames to src/gaps3, held by main (src/gaps3/a.py); "
        "free: src/gaps3-2"
    )
    free = cli(tmp_path, fix("rename src/gaps1 to src/gaps4"))
    assert free.returncode == 0 and free.stdout.strip() == "ok", free.stderr


def test_the_open_briefs_file_is_read(tmp_path):
    """REQ-050"""
    saved = tmp_path / "open.json"
    saved.write_text(json.dumps({"briefs": [brief(7, "src/gaps2/")], "pulls": []}))
    out = cli(tmp_path, fix("rename src/gaps1 to src/gaps2"), "--open-briefs", str(saved))
    assert out.returncode == 1 and "held by #7" in out.stdout, out.stderr
    assert cli(tmp_path, fix("x"), "--open-briefs").returncode == 2
