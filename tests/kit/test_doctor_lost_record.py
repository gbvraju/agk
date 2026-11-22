"""The doctor names a decision a hand merge left Proposed (brief #1738 answer 1; REQ-035, ADR-0724).

`lost-record` prints one line per first-parent squash commit `(#n)` that the merger did not
make and that adds or changes an ADR the default branch reads `Proposed`, when the pull request's
latest verdict by a record author is a covered fix list whose `Final:` lines accept it and no record
does. Commits come from a temporary git repository; comments are `--api-dir` fixtures. No network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell

from test_doctor import checks_of, doctor, prepare

ADR = "docs/adr/0002-second.md"
HEAD = "a" * 40
LINE = "lost-record: #7 ADR-0002 merged without the merger (the release cannot accept it)"


def git(root, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout


def adr(status: str = "Proposed") -> str:
    return (
        f"# ADR-0002: Second\n\n- Status: {status}\n- Date: 2026-11-20\n- Deciders: maintainers\n"
        "- Related: none\n- Requirements: REQ-035\n\n## Context\n\nc\n\n## Decision\n\nd\n\n"
        "## Consequences\n\nq\n\n## Residual\n\nr\n"
    )


def verdict(cid: int = 42, body: str | None = None, at: str = "2026-11-20T10:00:00Z") -> dict:
    return {
        "id": cid,
        "issue_url": "https://api.example.com/repos/example-owner/example-repo/issues/7",
        "user": {"login": "reviewer"},
        "created_at": at,
        "body": body or f"Verdict: fix list {HEAD}\n\nok.\n\nFinal: {ADR} Proposed -> Accepted\n",
    }


def world(tmp_path, message: str = "Add the second decision (#7)", status: str = "Proposed"):
    dirs = prepare("ok", tmp_path)
    root = dirs["root"]
    reviewers = root / "config" / "reviewers.yaml"
    reviewers.write_text(reviewers.read_text(encoding="utf-8") + "verdict_authors: [reviewer]\n")
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "t")):
        git(root, "config", key, value)
    git(root, "checkout", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", "base")
    (root / ADR).parent.mkdir(parents=True, exist_ok=True)
    (root / ADR).write_text(adr(status), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", message)
    return dirs


def lost(dirs, comments: list[dict] | None) -> tuple[list[str], subprocess.CompletedProcess]:
    if comments is not None:
        (dirs["api"] / "comments-7.json").write_text(json.dumps(comments), encoding="utf-8")
    args = ("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), str(dirs["root"]))
    text = doctor(*args)
    data = doctor(*args[:4], "--json", args[4])
    assert json.loads(data.stdout).get("lost_record", []) == [
        ln for ln in text.stdout.splitlines() if ln.startswith("lost-record:")
    ]
    return [ln for ln in text.stdout.splitlines() if ln.startswith("lost-record:")], data


def test_1738_a_hand_merge_whose_final_accepts_a_proposed_adr_is_named(tmp_path):
    """REQ-035: brief #1738 answer 1 and edge case 5(a) (#1719's facts)."""
    lines, _ = lost(world(tmp_path), [verdict()])
    assert lines == [LINE]


def test_1738_a_verdict_on_an_older_head_is_still_named(tmp_path):
    """REQ-035: brief #1738 edge case 5(c): listed (the release does not accept it)."""
    body = f"Verdict: fix list {'b' * 40}\n\nok.\n\nFinal: {ADR} Proposed -> Accepted\n"
    lines, _ = lost(world(tmp_path), [verdict(body=body)])
    assert lines == [LINE]


def test_1738_the_line_is_a_warning_that_changes_no_exit_code(tmp_path):
    """REQ-035: brief #1738 answer 1 (a warning, never a failure)."""
    dirs = world(tmp_path)
    _, before = lost(dirs, [])
    _, after = lost(dirs, [verdict()])
    assert before.returncode == after.returncode
    assert checks_of(before.stdout) == checks_of(after.stdout)


def test_1738_a_merger_made_squash_is_never_named(tmp_path):
    """REQ-035: brief #1738 edge case 5(b)."""
    from common import MERGED_BY

    message = f"Add the second decision (#7)\n\nADR-0002 Accepted (Final 42)\n{MERGED_BY}\n"
    assert lost(world(tmp_path, message=message), [verdict()])[0] == []


def test_1738_a_numbered_fix_list_or_a_rejection_as_the_latest_verdict_is_not_named(tmp_path):
    """REQ-035: brief #1738 edge case 5(d)."""
    dirs = world(tmp_path)
    for body in (
        f"Verdict: fix list {HEAD}\n\n1. fix it (rule: none).\n",
        f"Verdict: rejected {HEAD}\n",
    ):
        later = verdict(43, body=body, at="2026-11-21T10:00:00Z")
        assert lost(dirs, [verdict(), later])[0] == [], body


def test_1738_an_adr_already_accepted_is_not_named(tmp_path):
    """REQ-035: brief #1738 edge case 5(e)."""
    assert lost(world(tmp_path, status="Accepted"), [verdict()])[0] == []


def test_1738_a_two_parent_merge_is_not_read(tmp_path):
    """REQ-035: brief #1738 edge case 5(f)."""
    dirs = prepare("ok", tmp_path)
    root = dirs["root"]
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "t")):
        git(root, "config", key, value)
    git(root, "checkout", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", "base")
    git(root, "checkout", "-q", "-b", "side")
    (root / ADR).parent.mkdir(parents=True, exist_ok=True)
    (root / ADR).write_text(adr(), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", "side work")
    git(root, "checkout", "-q", "main")
    git(root, "merge", "-q", "--no-ff", "--no-gpg-sign", "-m", "Merge the side (#7)", "side")
    assert lost(dirs, [verdict()])[0] == []


def test_1738_a_copied_record_line_is_still_named(tmp_path):
    """REQ-035: brief #1738 edge case 5(g): without the merger's line it is not a record."""
    message = "Add the second decision (#7)\n\nADR-0002 Accepted (Final 42)\n"
    assert lost(world(tmp_path, message=message), [verdict()])[0] == [LINE]


def test_1738_a_read_that_fails_is_unknown_never_clean(tmp_path):
    """REQ-035: brief #1738 edge case 5(i)."""
    dirs = world(tmp_path)
    assert lost(dirs, None)[0] == ["lost-record: #7 unknown (cannot be read)"]
    (dirs["api"] / "comments-7.json").write_text(json.dumps({"message": "x", "status": "403"}))
    assert lost(dirs, None)[0] == ["lost-record: #7 unknown (cannot be read)"]


def test_1738_the_line_is_printed_before_the_summary(tmp_path):
    """REQ-035: brief #1738 answer 1 (an information line, like `tidy:`)."""
    dirs = world(tmp_path)
    (dirs["api"] / "comments-7.json").write_text(json.dumps([verdict()]), encoding="utf-8")
    out = doctor("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), str(dirs["root"]))
    lines = out.stdout.splitlines()
    assert lines[-1].startswith("summary:") and LINE in lines
    assert lines.index(LINE) < len(lines) - 1
