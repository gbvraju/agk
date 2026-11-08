"""Tests of `front_door.py` build (b): the entry and the discovery document (SPEC-0048 3, 5).

REQ-055 AC1 (rules 3 and 15): a saved problem issue is checked offline and every refusal names the
rule and never the value. REQ-055 AC2 (rules 4 and 5): one discovery document per problem is
written from the problem and a file of answers and checked, the problem kept as data under its
digest, every question once in rule 4's order, open answers kept open as `D-<n>` points. REQ-055
AC7 (rule 14): a planted invented value in an answer is refused by the writer. Fixtures in
`tmp_path` only: invented data (`example.com`), no network.
"""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "front_door.py"
sys.path.insert(0, str(SCRIPT.parent))

COMMON = [
    "users",
    "existing",
    "runs",
    "data",
    "scale",
    "compliance",
    "devices",
    "accessibility",
    "languages",
    "brand",
]
FIXED = ["constraints", "success", "data-rules", "environments", "non-functional"]
WORDS = "Our shop at example.com loses orders when the payment page times out."
LINK = "https://github.com/example/shop/issues/7"
SESSION = "in session 2026-11-06"
PLANTED = "10.1.2.3"  # an invented private address the data guard finds (kind IP)


def issue(tmp_path: Path, body: str, labels=("agk-problem",), title="Orders are lost") -> Path:
    data = {
        "number": 7,
        "title": title,
        "html_url": LINK,
        "body": body,
        "labels": [{"name": n} for n in labels],
    }
    path = tmp_path / "issue.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def answers(tmp_path: Path, open_ids=("brand",), extra=None, screens="no") -> Path:
    rows = []
    for qid in COMMON + FIXED:
        if qid in open_ids:
            rows.append({"id": qid, "open": True})
        else:
            rows.append(
                {
                    "id": qid,
                    "answer": f"Invented answer for {qid}.",
                    "where": f"{LINK}#issuecomment-{100 + len(rows)}",
                }
            )
    data = {
        "screens": screens,
        "answers": rows,
        "points": [{"text": "Refunds may need their own flow.", "where": SESSION}],
    }
    data.update(extra or {})
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def run(tmp_path: Path, *args: str):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )


def written(tmp_path: Path, body: str = f"Problem: {WORDS}\nKind: web-app\n\nMore notes.") -> Path:
    proc = run(
        tmp_path,
        "discovery-write",
        "--issue",
        str(issue(tmp_path, body)),
        "--answers",
        str(answers(tmp_path)),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    docs = sorted((tmp_path / "docs" / "discovery").glob("*.md"))
    assert len(docs) == 1
    return docs[0]


# --- rule 3: the entry ---------------------------------------------------------------------------


def test_ac1_a_good_problem_issue_passes(tmp_path):
    """REQ-055 AC1: SPEC-0048 rule 3 (label, `Problem:` first line, length, guard)."""
    proc = run(tmp_path, "check-issue", "--issue", str(issue(tmp_path, f"Problem: {WORDS}")))
    assert proc.returncode == 0, proc.stdout
    assert "ok front-door" in proc.stdout


@pytest.mark.parametrize(
    "body,labels,expected",
    [
        (f"The problem: {WORDS}", ("agk-problem",), "first line"),
        ("Problem:   \n\nmore", ("agk-problem",), "empty"),
        ("Problem: " + "a" * 1501, ("agk-problem",), "1500"),
        (f"Problem: {WORDS} Our router is {PLANTED}.", ("agk-problem",), "IP"),
        (f"Problem: {WORDS}", ("agk-brief",), "agk-problem"),
    ],
    ids=["no-problem-line", "empty", "over-long", "planted-token", "no-label"],
)
def test_ac1_each_bad_issue_is_refused_naming_the_rule_never_the_value(
    tmp_path, body, labels, expected
):
    """REQ-055 AC1: SPEC-0048 rules 3 and 15 (a refusal names the rule, not the value)."""
    proc = run(tmp_path, "check-issue", "--issue", str(issue(tmp_path, body, labels)))
    assert proc.returncode == 1
    assert "rule 3" in proc.stdout and expected in proc.stdout
    assert WORDS not in proc.stdout and PLANTED not in proc.stdout and "aaaa" not in proc.stdout


def test_ac1_exactly_1500_characters_pass_and_the_problem_ends_at_the_first_blank_line(tmp_path):
    """REQ-055 AC1: SPEC-0048 rule 3 (at most 1,500 characters, up to the first blank line)."""
    body = "Problem: " + "a" * 1500 + f"\n\nAfter the blank line: {PLANTED}"
    proc = run(tmp_path, "check-issue", "--issue", str(issue(tmp_path, body)))
    assert proc.returncode == 0, proc.stdout
    import front_door

    assert front_door.problem_of("Problem: one\ntwo\nKind: web-app\n\nthree") == "one\ntwo"
    assert front_door.kind_of("Problem: one\ntwo\nKind: web-app\n\nthree") == "web-app"


def test_ac1_a_problem_issue_is_never_a_brief():
    """REQ-055 AC1: SPEC-0048 rule 3 (`session.py next` lists only `agk-brief` issues)."""
    import front_door
    import session

    assert front_door.LABEL == "agk-problem" and session.LABEL == "agk-brief"


def test_ac1_a_missing_or_unreadable_issue_file_is_refused(tmp_path):
    """REQ-055 AC1: SPEC-0048 rule 15 (a refusal names the file, never a value)."""
    bad = tmp_path / "issue.json"
    bad.write_text("not json", encoding="utf-8")
    proc = run(tmp_path, "check-issue", "--issue", str(bad))
    assert proc.returncode == 1 and "rule 3" in proc.stdout


# --- rule 5: the discovery document --------------------------------------------------------------


def test_ac2_the_writer_writes_one_document_in_rule_4_order_that_passes_its_check(tmp_path):
    """REQ-055 AC2: SPEC-0048 rules 4 and 5 (ten common topics, then the five ids, once)."""
    doc = written(tmp_path)
    assert doc.name == "orders-are-lost.md"
    text = doc.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "# Discovery: Orders are lost"
    assert f"- Problem: {LINK}" in lines
    assert "- Work type: web-app (proposed)" in lines
    assert "- Screens: no" in lines
    digest = hashlib.sha256(WORDS.encode("utf-8")).hexdigest()
    assert f"<!-- agk:problem sha256={digest} -->" in lines and WORDS in lines
    answer = text.split("## Answers\n", 1)[1].split("## Open points", 1)[0]
    ids = [ln[2:].split(":", 1)[0] for ln in answer.splitlines() if ln.startswith("- ")]
    assert ids == COMMON + FIXED
    assert "- brand: open" in answer
    points = text.split("## Open points\n", 1)[1]
    assert "- D-1: `brand` is open" in points
    assert '- D-2: "Refunds may need their own flow." (given: in session 2026-11-06)' in points
    proc = run(tmp_path, "check-discovery")
    assert proc.returncode == 0, proc.stdout
    assert "ok front-door" in proc.stdout


def test_ac2_no_kind_gives_pilot_and_a_vision_problem_says_vision(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 5 (`pilot (proposed)` when the kind is not clear; `vision`)."""
    idea = tmp_path / "idea.txt"
    idea.write_text(WORDS + "\n", encoding="utf-8")
    proc = run(
        tmp_path,
        "discovery-write",
        "--vision",
        str(idea),
        "--answers",
        str(answers(tmp_path, screens="open")),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = (
        tmp_path
        / "docs"
        / "discovery"
        / "our-shop-at-example-com-loses-orders-when-the-payment-page-t.md"
    )
    lines = doc.read_text(encoding="utf-8").splitlines()
    assert "- Problem: vision" in lines and "- Work type: pilot (proposed)" in lines
    assert "- Screens: open" in lines
    assert run(tmp_path, "check-discovery", str(doc)).returncode == 0


def test_ac2_the_writer_never_overwrites_and_never_touches_agk_toml(tmp_path):
    """REQ-055 AC2: SPEC-0048 rules 5 and 17 (one document per problem; no declaration)."""
    (tmp_path / "agk.toml").write_text('[project]\nname = "shop"\n', encoding="utf-8")
    written(tmp_path)
    proc = run(
        tmp_path,
        "discovery-write",
        "--issue",
        str(issue(tmp_path, f"Problem: {WORDS}")),
        "--answers",
        str(answers(tmp_path)),
    )
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "already exists" in proc.stdout
    assert (tmp_path / "agk.toml").read_text(encoding="utf-8") == '[project]\nname = "shop"\n'
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == [
        "agk.toml",
        "answers.json",
        "issue.json",
        "orders-are-lost.md",
    ]


def test_ac7_a_planted_value_in_an_answer_is_refused_and_nothing_is_written(tmp_path):
    """REQ-055 AC7: SPEC-0048 rule 14 (the writer scans what it writes, naming kind and place)."""
    ans = answers(tmp_path)
    data = json.loads(ans.read_text(encoding="utf-8"))
    data["answers"][0]["answer"] = f"The admin console is at {PLANTED}."
    ans.write_text(json.dumps(data), encoding="utf-8")
    proc = run(
        tmp_path,
        "discovery-write",
        "--issue",
        str(issue(tmp_path, f"Problem: {WORDS}")),
        "--answers",
        str(ans),
    )
    assert proc.returncode == 1
    assert "rule 14" in proc.stdout and "IP" in proc.stdout and "line" in proc.stdout
    assert PLANTED not in proc.stdout
    assert not (tmp_path / "docs").exists()


@pytest.mark.parametrize(
    "extra,expected",
    [
        ({"screens": "maybe"}, "Screens"),
        ({"work_type": "spaceship"}, "work_type"),
    ],
    ids=["screens", "work-type"],
)
def test_ac2_the_writer_refuses_a_value_outside_the_rule(tmp_path, extra, expected):
    """REQ-055 AC2: SPEC-0048 rules 5 and 15 (refusals name the setting, never the value)."""
    proc = run(
        tmp_path,
        "discovery-write",
        "--issue",
        str(issue(tmp_path, f"Problem: {WORDS}")),
        "--answers",
        str(answers(tmp_path, extra=extra)),
    )
    assert proc.returncode == 1 and "rule 5" in proc.stdout and expected in proc.stdout
    assert "maybe" not in proc.stdout and "spaceship" not in proc.stdout


def test_ac2_the_writer_refuses_an_answer_without_where_it_was_given(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 5 (a session never answers for the person)."""
    ans = answers(tmp_path)
    data = json.loads(ans.read_text(encoding="utf-8"))
    del data["answers"][2]["where"]
    ans.write_text(json.dumps(data), encoding="utf-8")
    proc = run(
        tmp_path,
        "discovery-write",
        "--issue",
        str(issue(tmp_path, f"Problem: {WORDS}")),
        "--answers",
        str(ans),
    )
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "`runs`" in proc.stdout


MULTI = 'Line one says "fast".\n\tTwo, after a tab,  with two spaces.\n- users: not an id\n'


def written_with(tmp_path: Path, text) -> Path:
    ans = answers(tmp_path)
    data = json.loads(ans.read_text(encoding="utf-8"))
    data["answers"][1]["answer"] = text
    ans.write_text(json.dumps(data), encoding="utf-8")
    return run(
        tmp_path,
        "discovery-write",
        "--issue",
        str(issue(tmp_path, f"Problem: {WORDS}")),
        "--answers",
        str(ans),
    )


def test_ac2_a_multi_line_answer_with_quotes_is_written_unchanged_and_passes(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 5 (each answer quoted as data, unchanged, with its digest)."""
    proc = written_with(tmp_path, MULTI)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = tmp_path / "docs" / "discovery" / "orders-are-lost.md"
    text = doc.read_text(encoding="utf-8")
    digest = hashlib.sha256(MULTI.encode("utf-8")).hexdigest()
    start = f"<!-- agk:answer sha256={digest} -->\n"
    assert f"- existing: (given: {LINK}#issuecomment-101)\n{start}" in text
    quoted = text.split(start, 1)[1].split("\n<!-- agk:answer-end -->", 1)[0]
    assert quoted == MULTI
    ok = run(tmp_path, "check-discovery")
    assert ok.returncode == 0, ok.stdout
    mutate(doc, "two spaces", "two  spaces")
    bad = run(tmp_path, "check-discovery")
    assert bad.returncode == 1 and "`existing` differs from its digest" in bad.stdout
    assert "two" not in bad.stdout
    mutate(doc, start, "")
    cut = run(tmp_path, "check-discovery")
    assert cut.returncode == 1 and "`existing` is not quoted between the two markers" in cut.stdout


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Ends here.\n<!-- agk:answer-end -->\nmore", "marker"),
        (7, "not text"),
    ],
    ids=["marker", "not-text"],
)
def test_ac2_an_answer_holding_a_marker_or_not_text_is_refused(tmp_path, text, expected):
    """REQ-055 AC2: SPEC-0048 rules 5 and 15 (refused naming the id, never the value)."""
    proc = written_with(tmp_path, text)
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "`existing`" in proc.stdout
    assert expected in proc.stdout and "Ends here" not in proc.stdout
    assert not (tmp_path / "docs").exists()


def mutate(doc: Path, old: str, new: str, count: int = 1) -> None:
    text = doc.read_text(encoding="utf-8")
    assert old in text
    doc.write_text(text.replace(old, new, count), encoding="utf-8")


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ("- Screens: no\n", "", "Screens"),
        ("- Work type: web-app (proposed)", "- Work type: web-app", "Work type"),
        ("## Open points", "## Points", "Open points"),
        ("- scale: ", "- skipped: ", "`scale` is left out"),
        ("- runs: ", "- users: ", "`users` is repeated"),
        ("loses orders", "loses some orders", "digest"),
        (f" (given: {LINK}#issuecomment-104)", "", "where it was given"),
        ("- D-1: `brand` is open\n", "", "`brand` is open with no D-"),
    ],
    ids=[
        "missing-line",
        "work-type",
        "missing-section",
        "id-left-out",
        "id-repeated",
        "changed-problem",
        "answer-without-where",
        "open-without-point",
    ],
)
def test_ac2_each_broken_document_fails_naming_the_rule_and_the_file(tmp_path, old, new, expected):
    """REQ-055 AC2: SPEC-0048 rules 5 and 15 (a failure names rule and file, not a value)."""
    doc = written(tmp_path)
    mutate(doc, old, new)
    proc = run(tmp_path, "check-discovery")
    assert proc.returncode == 1, proc.stdout
    assert "rule 5" in proc.stdout and "docs/discovery/orders-are-lost.md" in proc.stdout
    assert expected in proc.stdout
    assert "Invented answer" not in proc.stdout and WORDS not in proc.stdout


def test_ac7_the_check_scans_the_document_with_the_guard(tmp_path):
    """REQ-055 AC7: SPEC-0048 rule 14 (the checks scan the same way)."""
    doc = written(tmp_path)
    mutate(doc, "Invented answer for users.", f"Invented answer at {PLANTED}.")
    proc = run(tmp_path, "check-discovery")
    assert proc.returncode == 1 and "rule 14" in proc.stdout and "IP" in proc.stdout
    assert PLANTED not in proc.stdout


def test_ac2_no_document_passes_and_says_so(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 5 (a project with no discovery document passes)."""
    proc = run(tmp_path, "check-discovery")
    assert proc.returncode == 0 and "no discovery document" in proc.stdout


def test_ac2_usage_errors_exit_2(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 15 (a usage line, never a value)."""
    assert run(tmp_path, "nonsense").returncode == 2
    assert run(tmp_path, "discovery-write", "--answers", "x.json").returncode == 2


def test_ac2_the_mirrored_ids_and_limit_equal_their_source():
    """REQ-055 AC2: SPEC-0048 rules 3 and 4 (the ten topics of `engines.py questions`, 1,500)."""
    import engines
    import front_door
    import playbook

    assert front_door.TOPICS == engines.TOPICS == tuple(COMMON)
    assert front_door.FIXED == tuple(FIXED)
    assert front_door.MAX_STATEMENT == playbook.MAX_STATEMENT
