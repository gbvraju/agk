"""Two standing owner rulings (brief #1385, ADR-0583; REQ-037).

Ruling 1: a pull request whose changed lines (tests excluded) are at most three times its brief's
size guide (300 when the brief gives none), and whose latest verdict names no finding, is accepted
with the line `Size: <n> of <guide>, accepted by standing ruling (ADR-0583)`; otherwise the owner
is asked. Ruling 2: an instruction file's word count may rise by at most ten percent over its
`config/rule-budget.txt` baseline when its rule lines do not rise, with the body line
`Rule budget: <file> <old> to <new> words, standing ruling (ADR-0583)`; otherwise asked. No network.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_req037_size_at_two_and_a_half_times_with_no_finding_is_accepted():
    """REQ-037: 250 of 100 with no finding carries the size line, so no `Owner needed:`."""
    from rules import size_ruling

    line = size_ruling(250, 100, 0)
    assert line == "Size: 250 of 100, accepted by standing ruling (ADR-0583)"
    assert "Owner needed:" not in line


def test_req037_size_over_three_times_or_with_a_finding_is_asked():
    """REQ-037: 350 of 100, or one finding, leaves the owner's question as today."""
    from rules import size_ruling

    assert size_ruling(350, 100, 0) is None
    assert size_ruling(250, 100, 1) is None
    assert size_ruling(300, 100, 0) is not None


def test_req037_a_brief_with_no_size_guide_uses_300():
    """REQ-037: no guide is 300, so 900 passes and 901 is asked."""
    from rules import size_ruling

    assert size_ruling(900, None, 0) == "Size: 900 of 300, accepted by standing ruling (ADR-0583)"
    assert size_ruling(901, None, 0) is None


def test_req037_a_rule_budget_raise_of_eight_percent_with_no_new_rule_passes():
    """REQ-037: 1000 to 1080 words, rule lines unchanged, gives the body line."""
    from rules import budget_ruling

    assert budget_ruling(".claude/agents/x.md", 1000, 1080, 12, 12) == (
        "Rule budget: .claude/agents/x.md 1000 to 1080 words, standing ruling (ADR-0583)"
    )
    assert budget_ruling(".claude/agents/x.md", 1000, 1100, 12, 11) is not None


def test_req037_twelve_percent_or_one_new_rule_line_is_asked():
    """REQ-037: 1000 to 1120 words, or one rule line more, is asked as today."""
    from rules import budget_ruling

    assert budget_ruling(".claude/agents/x.md", 1000, 1120, 12, 12) is None
    assert budget_ruling(".claude/agents/x.md", 1000, 1010, 12, 13) is None


def test_req037_the_conductor_file_and_the_adr_carry_both_rulings():
    """REQ-037: the conductor's verdict steps name both lines; the ADR quotes the owner."""
    conductor = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "accepted by standing ruling (ADR-0583)" in conductor
    assert "standing ruling (ADR-0583)`" in conductor and "Rule budget: <file>" in conductor
    adr = next((ROOT / "docs" / "adr").glob("0583-*.md")).read_text(encoding="utf-8")
    assert "- Status: " in adr and '"Go ahead"' in adr


# --- brief #1788 (ADR-0749): one count, one guide, one line ------------------------------------

# The recorded file list of #1762 at head 56db4b4b (filename, status, additions, deletions).
FILES_1762 = [
    ("changelog.d/brief-1757.md", "added", 1, 0),
    ("docs/adr/0735-the-kind-of-product-named-in-discovery-req-045-brief-1757.md", "added", 57, 0),
    ("docs/runs/proposed-spec-amendments-218.md", "added", 34, 0),
    ("scripts/agk/doctor.py", "modified", 24, 0),
    ("scripts/agk/engines.py", "modified", 19, 1),
    ("scripts/agk/playbook_format.py", "modified", 19, 0),
    ("scripts/agk/steward_owner.py", "modified", 214, 0),
    ("tests/kit/test_steward_work_type.py", "added", 277, 0),
]
PLAN_1757 = (
    "Sentence: invented.\n"
    "Plan: #661, milestone Wave 4. One pull request; tests first, marker `REQ-045`; about 100 "
    "changed lines outside tests or fewer; invented data only (example.com).\n"
)
HEAD = "56db4b4b45b0b1e4f62182d91909f4a95e61f287"


def files_of(rows) -> list[dict]:
    return [{"filename": f, "status": s, "additions": a, "deletions": d} for f, s, a, d in rows]


def api_dir(tmp_path, verdict: str | None = None, rows=FILES_1762) -> str:
    """Recorded responses of #1762 in the `--api-dir` form; no network."""
    import json

    pull = {
        "number": 1762,
        "head": {"sha": HEAD},
        "body": "Brief: #1757\n",
        "changed_files": len(rows),
    }
    comments = []
    if verdict is not None:
        comments.append({"id": 7, "user": {"login": "gbvraju"}, "body": verdict})
    for name, data in (
        ("pull-1762", pull),
        ("files-1762", files_of(rows)),
        ("brief-1757", {"number": 1757, "body": PLAN_1757}),
        ("comments-1762", comments),
    ):
        (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return str(tmp_path)


def test_req037_size_count_leaves_out_the_records_of_1762():
    """REQ-037: code and guides count (277); tests, ADR, amendment and fragment do not."""
    from rules import size_count

    assert size_count(files_of(FILES_1762)) == (277, 369)
    assert size_count(files_of(FILES_1762[:7])) == (277, 92)
    assert size_count([{"filename": "docs/img.png", "status": "added"}]) == (0, 0)
    assert size_count(files_of([("docs/guides/x.md", "added", 5, 0)])) == (5, 0)
    assert size_count(files_of([("docs/other/0749-x.md", "added", 9, 0)])) == (9, 0)


def test_req037_size_guide_reads_the_plan_line():
    """REQ-037: brief #1757's `Plan:` line gives 100; another line's phrase never wins."""
    from rules import size_guide

    assert size_guide(PLAN_1757) == 100
    assert size_guide("Size: about 40 changed lines\n" + PLAN_1757) == 100
    assert size_guide("Plan: one pull request.\n") is None
    assert size_guide(None) is None


def test_req037_size_findings_leave_out_merge_reprove_and_record_items():
    """REQ-037 (Q-F4-1): a merge of main, a re-prove or an evidence record is not a finding."""
    from rules import size_findings

    fix = (
        f"Verdict: fix list {HEAD}\n"
        "1. Merge origin/main into the branch (rule: config/session-rules.md 31)\n"
        "2. Post the local evidence line (rule: config/session-rules.md 30)\n"
        "3. Re-prove the head after the merge (rule: none)\n"
    )
    assert size_findings(fix) == 0
    assert (
        size_findings(fix + "4. The refusal names a value (rule: constitution/principles.md 8)\n")
        == 1
    )
    assert size_findings(f"Verdict: cleared {HEAD}\n") == 0
    assert size_findings(f"Verdict: rejected {HEAD}\nWrong item.\n") == 1


def run_size(*args: str) -> tuple[int, str]:
    import contextlib
    import io

    from rules import main

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["size", *args])
    return code, out.getvalue()


def test_req037_rules_size_on_1762_is_accepted_by_the_standing_ruling(tmp_path):
    """REQ-037: `rules.py size --pr 1762` prints 277 of 100, accepted, and the records."""
    code, out = run_size("--pr", "1762", "--root", str(ROOT), "--api-dir", api_dir(tmp_path))
    assert code == 0
    assert out.splitlines() == [
        "Size: 277 of 100, accepted by standing ruling (ADR-0583)",
        "records: 369 lines not counted",
    ]


def test_req037_rules_size_over_three_times_or_with_a_finding_asks(tmp_path):
    """REQ-037: 301 of 100, or one finding in the newest verdict, prints the ask line."""
    rows = [*FILES_1762, ("scripts/agk/session.py", "modified", 24, 0)]
    code, out = run_size(
        "--pr", "1762", "--root", str(ROOT), "--api-dir", api_dir(tmp_path, rows=rows)
    )
    assert code == 0
    assert (
        out.splitlines()[0]
        == "Size: 301 of 100, over the standing ruling (ADR-0583): ask the owner"
    )
    verdict = f"Verdict: fix list {HEAD}\n1. The refusal names a value (rule: none)\n"
    (tmp_path / "b").mkdir()
    code, out = run_size(
        "--pr", "1762", "--root", str(ROOT), "--api-dir", api_dir(tmp_path / "b", verdict)
    )
    assert (
        out.splitlines()[0]
        == "Size: 277 of 100, over the standing ruling (ADR-0583): ask the owner"
    )


def test_req037_rules_size_with_3000_files_is_unknown_and_asks(tmp_path):
    """REQ-037: GitHub's 3000-file limit gives `unknown`, never an acceptance."""
    rows = [(f"scripts/x{i}.py", "added", 0, 0) for i in range(3000)]
    code, out = run_size(
        "--pr", "1762", "--root", str(ROOT), "--api-dir", api_dir(tmp_path, rows=rows)
    )
    assert out.splitlines()[0] == "Size: unknown of 100 (3000 files or more): ask the owner"


def test_req037_rules_size_in_personal_mode_and_without_the_ruling(tmp_path):
    """REQ-037: personal mode is not run; an ADR withdrawing ADR-0583 leaves no ruling."""
    (tmp_path / "agk.toml").write_text("[personal]\n", encoding="utf-8")
    assert run_size("--pr", "1762", "--root", str(tmp_path)) == (0, "not run: personal mode\n")
    proj = tmp_path / "proj"
    (proj / "docs" / "adr").mkdir(parents=True)
    (proj / "agk.toml").write_text("", encoding="utf-8")
    (proj / "docs" / "adr" / "0002-x.md").write_text(
        "# ADR-0002: x\n\n- Status: Accepted\n- Withdraws: ADR-0583\n", encoding="utf-8"
    )
    (tmp_path / "api").mkdir()
    code, out = run_size(
        "--pr", "1762", "--root", str(proj), "--api-dir", api_dir(tmp_path / "api")
    )
    assert out.splitlines()[0] == "Size: 277 of 100, no standing ruling: ask the owner"
