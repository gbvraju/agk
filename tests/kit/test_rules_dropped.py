"""`rules.py dropped --since DATE`: the rules agents drop, counted (brief #647 answer 2, ADR-0310;
REQ-037 AC5).

It reads, GET only, the fix-list comments of the merged and open pull requests and prints the count
per rule, newest first, and the items with no tag, as references only (no comment text). The tests
read recorded responses (`--api-dir`); no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "rules.py"
CONFIG = "version: 1\nverdict_authors: [reviewer]\n"


def pr(number: int, state: str, merged: str | None, updated: str) -> dict:
    return {"number": number, "state": state, "merged_at": merged, "updated_at": updated}


def note(cid: int, body: str, at: str, login: str = "reviewer") -> dict:
    return {"id": cid, "body": body, "created_at": at, "user": {"login": login}}


def fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    (root / "config" / "reviewers.yaml").write_text(CONFIG, encoding="utf-8")
    api = tmp_path / "api"
    api.mkdir()
    pulls = [
        pr(3, "open", None, "2026-11-05T09:00:00Z"),
        pr(2, "closed", "2026-11-04T09:00:00Z", "2026-11-04T09:00:00Z"),
        pr(4, "closed", None, "2026-11-04T08:00:00Z"),  # closed unmerged: not read
        pr(1, "closed", "2026-10-01T09:00:00Z", "2026-10-01T09:00:00Z"),  # before --since
    ]
    (api / "pulls.json").write_text(json.dumps(pulls), encoding="utf-8")
    three = [
        note(
            31,
            "Verdict: fix list 0066abc\n\n1. a (rule: config/session-rules.md 27)\n"
            "2. b (rule: CLAUDE.md 7)\n3. c secret-ish text\n",
            "2026-11-05T10:00:00Z",
        ),
        note(
            32,
            "Verdict: fix list 0066abd\n\n1. a (rule: config/session-rules.md 27)\n",
            "2026-11-05T09:00:00Z",
            login="stranger",
        ),  # not a listed verdict author
        note(33, "Verdict: cleared 0066abe\n\n1. a note (rule: none)\n", "2026-11-05T11:00:00Z"),
    ]
    two = [
        note(
            21,
            "Verdict: fix list 0077abc\n\n1. a (rule: config/session-rules.md 27)\n"
            "2. b (rule: none)\n",
            "2026-11-04T10:00:00Z",
        ),
        note(
            22, "Verdict: fix list 0077abd\n\n1. old (rule: CLAUDE.md 7)\n", "2026-10-30T10:00:00Z"
        ),
    ]
    (api / "comments-3.json").write_text(json.dumps(three), encoding="utf-8")
    (api / "comments-2.json").write_text(json.dumps(two), encoding="utf-8")
    (api / "comments-4.json").write_text(json.dumps(three), encoding="utf-8")
    return root, api


def dropped(root: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "dropped", "--root", str(root), "--repo", "o/r", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603


def test_req037_counts_per_rule_newest_first_and_lists_the_untagged(tmp_path):
    """REQ-037 AC5"""
    root, api = fixture(tmp_path)
    out = dropped(root, "--since", "2026-11-01", "--api-dir", str(api))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.splitlines() == [
        "dropped since 2026-11-01: 5 fix-list items in 2 verdicts on 2 pull requests",
        "2 config/session-rules.md 27 (newest 2026-11-05)",
        "1 CLAUDE.md 7 (newest 2026-11-05)",
        "1 none (newest 2026-11-04)",
        "untagged: 1",
        "untagged #3 comment 31 item 3",
    ]
    assert "secret-ish" not in out.stdout


def test_req037_the_since_date_moves_the_window(tmp_path):
    """REQ-037 AC5: comments before DATE are not counted."""
    root, api = fixture(tmp_path)
    out = dropped(root, "--since", "2026-11-05", "--api-dir", str(api))
    assert out.returncode == 0
    assert out.stdout.splitlines()[0] == (
        "dropped since 2026-11-05: 3 fix-list items in 1 verdicts on 1 pull requests"
    )


def test_req037_unreadable_pulls_are_unknown_never_zero(tmp_path):
    """REQ-037 AC5"""
    root, api = fixture(tmp_path)
    (api / "pulls.json").unlink()
    out = dropped(root, "--since", "2026-11-01", "--api-dir", str(api))
    assert out.returncode == 1
    assert out.stdout.strip() == "dropped: unknown (the pull requests cannot be read)"


def test_req037_an_unreadable_comment_list_is_named(tmp_path):
    """REQ-037 AC5: the count says which pull request it could not read."""
    root, api = fixture(tmp_path)
    (api / "comments-2.json").unlink()
    out = dropped(root, "--since", "2026-11-01", "--api-dir", str(api))
    assert out.returncode == 0
    assert "unread: #2" in out.stdout.splitlines()


def test_req037_a_bad_call_exits_2(tmp_path):
    """REQ-037 AC5"""
    root, api = fixture(tmp_path)
    for args in (["--since", "soon"], [], ["--since", "2026-11-01", "--write"]):
        out = dropped(root, *args, "--api-dir", str(api))
        assert out.returncode == 2 and out.stdout.startswith("usage: rules.py"), args


def test_req037_dropped_uses_get_only():
    """REQ-037 AC5: the command posts nothing."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--method" not in text.replace('"--method", "GET"', "")
    assert "POST" not in text and "PATCH" not in text and "DELETE" not in text
