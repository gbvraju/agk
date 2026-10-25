"""shadow_rate.py: the conductor's catch rate from the marks (SPEC-0035 rules 3, 4 and 8; REQ-042).

Recorded GitHub responses in a directory (`pulls.json`, `comments-<n>.json`), named as in SPEC-0007
rule 20. No network, no model.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "shadow_rate.py"
SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
SHA7 = SHA[:7]
OTHER = "0123456789abcdef0123456789abcdef01234567"
ISSUE = 40
AUTHORS = "boss,second"
WEEK1 = "2026-10-19T10:00:00Z"  # 2026-W43
WEEK2 = "2026-10-26T10:00:00Z"  # 2026-W44


def comment(cid: int, login: str, body: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": "2026-10-20T10:00:00Z"}


class Dir:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.pulls: list[dict] = []

    def pull(self, n: int, merged: str | None = WEEK1, author: str = "builder") -> None:
        self.pulls = [p for p in self.pulls if p["number"] != n]
        self.pulls.append({"number": n, "merged_at": merged, "user": {"login": author}})
        (self.path / "pulls.json").write_text(json.dumps(self.pulls), encoding="utf-8")

    def comments(self, n: int, items: list[dict]) -> None:
        (self.path / f"comments-{n}.json").write_text(json.dumps(items), encoding="utf-8")

    def run(self, *extra: str, authors: str = AUTHORS):
        args = ["--api-dir", str(self.path), "--shadow-issue", str(ISSUE), "--authors", authors]
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPT), *args, *extra],
            capture_output=True,
            text=True,
            timeout=60,
        )


@pytest.fixture
def api(tmp_path: Path) -> Dir:
    return Dir(tmp_path)


def verdict(cid: int, kind: str = "fix list", sha: str = SHA, items: int = 3, who="boss") -> dict:
    body = f"Verdict: {kind} {sha}\n\nReviewed.\n\n" + "".join(
        f"{i}. **finding {i}** in `a.py`\n   - detail\n" for i in range(1, items + 1)
    )
    return comment(cid, who, body)


def shadow(cid: int, pr: int = 7, sha: str = SHA, items: int = 2, who="second") -> dict:
    body = f"Shadow: #{pr} {sha} fix list\n\n" + "".join(
        f"S{i}. `a.py` line {i}: finding\n" for i in range(1, items + 1)
    )
    return comment(cid, who, body)


def marks(cid: int, *lines: str, who: str = "builder") -> dict:
    return comment(cid, who, "Marks:\n" + "\n".join(lines) + "\n")


def lines_of(out: str, section: str = "total") -> dict[str, str]:
    """The `key: value` lines of one section (`week 2026-W43` or `total`)."""
    found, inside = {}, False
    for line in out.splitlines():
        if not line.startswith(" "):
            inside = line.strip() == section
        elif inside and ":" in line:
            key, _, value = line.strip().partition(":")
            found[key] = value.strip()
    return found


def basic(api: Dir, mark_lines: list[str] | None = None, who: str = "builder") -> None:
    api.pull(7)
    api.comments(7, [verdict(1), *([marks(3, *mark_lines, who=who)] if mark_lines else [])])
    api.comments(ISSUE, [shadow(2)])


MARKED = [
    f"C{SHA7}-1 right",
    f"C{SHA7}-2 both",
    f"C{SHA7}-3 wrong",
    f"S{SHA7}-1 both",
    f"S{SHA7}-2 right",
]


def test_ac1_a_shadow_comment_and_a_verdict_of_the_same_head_are_a_pair(api):
    """REQ-042 AC1"""
    basic(api)
    out = api.run()
    assert out.returncode == 0, out.stdout + out.stderr
    assert lines_of(out.stdout)["heads reviewed by both"] == "1"


def test_ac1_a_shadow_comment_that_matches_no_verdict_is_unpaired_never_a_pair(api):
    """REQ-042 AC1"""
    basic(api)
    api.comments(ISSUE, [shadow(2), shadow(5, sha=OTHER), shadow(6, pr=99)])
    total = lines_of(api.run().stdout)
    assert total["heads reviewed by both"] == "1" and total["unpaired shadow comments"] == "2"


def test_ac3_right_wrong_and_both_marks_count_each_finding_once(api):
    """REQ-042 AC3"""
    basic(api, MARKED)
    total = lines_of(api.run().stdout)
    assert total["right, conductor only"] == "1"
    assert total["right, shadow only"] == "1"
    assert total["right, both"] == "1"
    assert total["wrong, conductor"] == "1" and total["wrong, shadow"] == "0"
    assert total["unmarked heads"] == "0" and total["unmarked findings"] == "0"


def test_ac3_a_later_marks_comment_changes_a_mark_and_the_last_one_counts(api):
    """REQ-042 AC3: a person may change a mark."""
    basic(api, MARKED)
    items = json.loads((api.path / "comments-7.json").read_text())
    items.append(marks(9, f"C{SHA7}-3 right", who="second"))
    api.comments(7, items)
    total = lines_of(api.run().stdout)
    assert total["right, conductor only"] == "2" and total["wrong, conductor"] == "0"


def test_ac3_a_mark_that_names_no_finding_of_its_pull_request_is_refused_naming_the_rule(api):
    """REQ-042 AC3"""
    line = f"C{SHA7}-9 right"
    basic(api, [line])
    out = api.run()
    assert out.returncode == 1 and "rule 3" in out.stdout and line not in out.stdout
    other = f"C{OTHER[:7]}-1 right"
    basic(api, [other])
    assert api.run().returncode == 1


def test_ac3_marks_of_a_stranger_and_shadow_comments_of_a_stranger_are_ignored(api):
    """REQ-042 AC3: only listed authors and the pull request's author count."""
    basic(api, MARKED, who="stranger")
    assert lines_of(api.run().stdout)["unmarked heads"] == "1"
    basic(api, [f"C{SHA7}-1 right"])
    api.comments(ISSUE, [shadow(2, who="stranger")])
    assert lines_of(api.run().stdout)["heads reviewed by both"] == "0"


def test_ac4_a_mark_by_the_author_of_the_finding_is_refused_where_the_accounts_differ(api):
    """REQ-042 AC4"""
    basic(api, [f"C{SHA7}-1 right"], who="boss")
    out = api.run()
    assert out.returncode == 1 and "rule 3" in out.stdout
    basic(api, [f"S{SHA7}-1 right"], who="second")
    assert api.run().returncode == 1
    basic(api, [f"C{SHA7}-1 right"], who="builder")
    assert api.run().returncode == 0


def test_ac4_with_one_account_for_both_reviewers_no_mark_is_refused(api):
    """REQ-042 AC4: the residual of SPEC-0035, one account cannot be told apart."""
    api.pull(7)
    api.comments(7, [verdict(1), marks(3, f"C{SHA7}-1 right", who="boss")])
    api.comments(ISSUE, [shadow(2, who="boss")])
    assert api.run(authors="boss").returncode == 0


def test_ac4_a_pull_request_without_a_marks_comment_is_unmarked_never_zero(api):
    """REQ-042 AC4"""
    basic(api)
    total = lines_of(api.run().stdout)
    assert total["unmarked heads"] == "1"
    assert total["right, conductor only"] == "0" and total["catch rate"] == "none"


def test_ac4_a_finding_without_a_mark_in_a_marked_pull_request_is_an_unmarked_finding(api):
    """REQ-042 AC4"""
    basic(api, [f"C{SHA7}-1 right"])
    total = lines_of(api.run().stdout)
    assert total["unmarked heads"] == "0" and total["unmarked findings"] == "4"


def test_ac5_the_catch_rate_is_right_conductor_findings_over_those_plus_right_shadow_only(api):
    """REQ-042 AC5"""
    basic(api, MARKED)
    assert lines_of(api.run().stdout)["catch rate"] == "2/3 (66.7%)"


def test_ac5_with_no_right_finding_the_rate_is_none_and_never_zero(api):
    """REQ-042 AC5"""
    basic(api, [f"C{SHA7}-1 wrong", f"C{SHA7}-2 wrong", f"S{SHA7}-1 wrong"])
    assert lines_of(api.run().stdout)["catch rate"] == "none"


def test_ac5_a_rate_of_zero_is_printed_when_only_the_shadow_found_right_findings(api):
    """REQ-042 AC5"""
    basic(api, [f"S{SHA7}-1 right", f"S{SHA7}-2 right", f"C{SHA7}-1 wrong"])
    assert lines_of(api.run().stdout)["catch rate"] == "0/2 (0.0%)"


def test_ac5_each_iso_week_of_the_merge_has_a_section_and_the_total_sums_them(api):
    """REQ-042 AC5"""
    basic(api, MARKED)
    api.pull(8, merged=WEEK2)
    api.comments(8, [verdict(11, sha=OTHER), marks(13, f"C{OTHER[:7]}-1 right")])
    api.comments(ISSUE, [shadow(2), shadow(12, pr=8, sha=OTHER)])
    out = api.run().stdout
    assert [m for m in re.findall(r"(?m)^week (\S+)$", out)] == ["2026-W43", "2026-W44"]
    assert lines_of(out, "week 2026-W43")["right, conductor only"] == "1"
    assert lines_of(out, "week 2026-W44")["right, conductor only"] == "1"
    assert lines_of(out)["right, conductor only"] == "2"
    assert lines_of(out)["heads reviewed by both"] == "2"


def test_ac5_a_pull_request_that_did_not_merge_is_left_out(api):
    """REQ-042 AC5"""
    basic(api, MARKED)
    api.pull(7, merged=None)
    assert lines_of(api.run().stdout)["heads reviewed by both"] == "0"


def test_ac5_findings_of_a_head_the_shadow_did_not_review_are_not_counted(api):
    """REQ-042 AC5: only heads reviewed by both."""
    basic(api, MARKED)
    items = json.loads((api.path / "comments-7.json").read_text())
    api.comments(7, [*items, verdict(21, sha=OTHER, items=2)])
    assert lines_of(api.run().stdout)["right, conductor only"] == "1"


def test_ac5_a_missing_input_or_a_bad_call_is_exit_2_and_the_script_uses_no_network(api):
    """REQ-042 AC5 and rule 8"""
    bare = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT)], capture_output=True
    )
    assert bare.returncode == 2
    out = api.run()  # no pulls.json
    assert out.returncode == 2 and "pulls.json" in out.stdout
    text = SCRIPT.read_text(encoding="utf-8")
    assert "subprocess" not in text and "urllib" not in text and '"gh"' not in text
