"""Tests of the amendment numbers in scripts/agk/check_numbers.py (brief #480, ADR-0275; REQ-032).

A pull request that adds `docs/runs/proposed-spec-amendments-<n>.md` fails when the default branch
already has that number, and, with a saved open-pull-requests file and the pull request's own
number, when another open pull request adds the same number. The message names the number and the
other pull request. Fixture repositories and saved files only; no network.
"""

from __future__ import annotations

import json

import pytest

AMEND = "docs/runs/proposed-spec-amendments-{}.md"
REQS = "# Requirements\n\n### REQ-001 — One\n\n- Status: planned\n"


def base(repo):
    repo.commit({"docs/requirements.md": REQS, AMEND.format(107): "# Amendments 107\n"}, "base")


def open_file(tmp_path, records):
    path = tmp_path / "open-prs.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return str(path)


def test_ac1_a_new_amendment_number_passes(repo):
    """REQ-032 AC1: a pull request adding a free amendment number passes."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Amendments 108\n"})
    proc = repo.run("check_numbers.py")
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac1_an_amendment_number_the_default_branch_already_has_fails(repo):
    """REQ-032 AC1: main took 108 after the branch started; the branch adds 108 too."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Ours\n"})
    repo.git("checkout", "-q", "main")
    repo.commit({AMEND.format(108): "# Theirs\n"}, "main takes 108")
    repo.git("checkout", "-q", "feature")
    proc = repo.run("check_numbers.py")
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL numbers: rule 1")
    assert "amendment 108" in proc.stdout and "default branch" in proc.stdout
    assert "Ours" not in proc.stdout and "Theirs" not in proc.stdout


def test_ac1_an_amendment_number_another_open_pull_request_adds_fails_naming_it(repo, tmp_path):
    """REQ-032 AC1: another open pull request adds the same number; it is named."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Ours\n"})
    records = [
        {"number": 463, "files": [AMEND.format(108), "docs/adr/0001-x.md"]},
        {"number": 470, "files": [AMEND.format(109)]},
        {"number": 480, "files": [AMEND.format(108)]},
    ]
    proc = repo.run("check_numbers.py", "--open", open_file(tmp_path, records), "--number", "480")
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL numbers: rule 1")
    assert "amendment 108" in proc.stdout and "#463" in proc.stdout
    assert "#470" not in proc.stdout and "#480" not in proc.stdout


def test_ac1_open_pull_requests_with_other_numbers_pass(repo, tmp_path):
    """REQ-032 AC1: no other open pull request adds the number; its own record is ignored."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Ours\n"})
    records = [
        {"number": 470, "files": [AMEND.format(109)]},
        {"number": 480, "files": [AMEND.format(108)]},
    ]
    proc = repo.run("check_numbers.py", "--open", open_file(tmp_path, records), "--number", "480")
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac1_a_record_without_a_file_list_is_never_guessed(repo, tmp_path):
    """REQ-032 AC1: a record that lists no files is not compared (no guess from a title)."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Ours\n"})
    records = [{"number": 463, "title": "amendments 108"}, {"number": 464, "files": "x"}]
    proc = repo.run("check_numbers.py", "--open", open_file(tmp_path, records), "--number", "480")
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac1_an_amendment_already_on_the_branch_base_is_not_the_pull_requests_own(repo, tmp_path):
    """REQ-032 AC1: 107 was on main before the branch; another pull request editing it is fine."""
    base(repo)
    repo.branch()
    repo.commit({"a.txt": "x\n"})
    records = [{"number": 463, "files": [AMEND.format(107)]}]
    proc = repo.run("check_numbers.py", "--open", open_file(tmp_path, records), "--number", "480")
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac1_both_clashes_are_named_together(repo, tmp_path):
    """REQ-032 AC1: one run names every clash."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Ours\n", AMEND.format(109): "# Ours too\n"})
    repo.git("checkout", "-q", "main")
    repo.commit({AMEND.format(108): "# Theirs\n"}, "main takes 108")
    repo.git("checkout", "-q", "feature")
    records = [{"number": 466, "files": [AMEND.format(109)]}]
    proc = repo.run("check_numbers.py", "--open", open_file(tmp_path, records), "--number", "480")
    assert proc.returncode == 1
    assert "amendment 108" in proc.stdout and "amendment 109" in proc.stdout
    assert "#466" in proc.stdout


def test_ac1_the_open_file_needs_the_own_number(repo, tmp_path):
    """REQ-032 AC1: without --number its own record would match itself, so it is a usage error."""
    base(repo)
    proc = repo.run("check_numbers.py", "--open", open_file(tmp_path, []))
    assert proc.returncode == 2 and proc.stdout.startswith("usage:")


def test_ac1_an_unknown_option_is_a_usage_error(repo):
    """REQ-032 AC1: an option it does not know is refused."""
    base(repo)
    proc = repo.run("check_numbers.py", "--states", "x")
    assert proc.returncode == 2 and proc.stdout.startswith("usage:")


def test_ac1_an_unreadable_open_file_fails_naming_the_file_kind(repo, tmp_path):
    """REQ-032 AC1: a broken file fails naming what it is, never its content."""
    base(repo)
    repo.branch()
    repo.commit({AMEND.format(108): "# Ours\n"})
    bad = tmp_path / "open-prs.json"
    bad.write_text("{not json", encoding="utf-8")
    proc = repo.run("check_numbers.py", "--open", str(bad), "--number", "480")
    assert proc.returncode == 1
    assert "open pull requests file" in proc.stdout and "not json" not in proc.stdout


def test_ac1_without_a_base_ref_the_tree_part_still_runs(repo):
    """REQ-032 AC1: on a branch with no default branch to compare, the tree check alone runs."""
    repo.git("checkout", "-q", "-b", "trunk")
    repo.commit({"docs/requirements.md": REQS, AMEND.format(108): "# x\n"}, "base")
    proc = repo.run("check_numbers.py")
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac1_a_reserved_amendment_number_is_named_in_the_conductor_and_the_brief_template():
    """REQ-032 AC1: the conductor reserves amendment numbers in the field note, as ADR numbers."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for rel in (".claude/agents/conductor.md", "docs/briefs/TEMPLATE.md"):
        text = " ".join((root / rel).read_text(encoding="utf-8").split())
        assert "amendment number" in text and "field note" in text, rel


# --- reservations of open briefs (amendment 141 item 5; REQ-057 AC11) ---------------------------


def briefs_file(repo, *pairs) -> str:
    path = repo.root.parent / "briefs.json"
    path.write_text(
        json.dumps([{"number": n, "body": f"Reserved: {r}\n"} for n, r in pairs]), encoding="utf-8"
    )
    return str(path)


def on_branch(repo, **files):
    repo.commit({"docs/requirements.md": "# R\n\n### REQ-001 — a\n"}, "base")
    repo.git("branch", "-M", "main")
    repo.branch()
    repo.commit(files, "work")


def run_numbers(repo, *args):
    return repo.run("check_numbers.py", *args, AGK_BASE="main")


def test_ac11_a_number_added_here_and_reserved_by_another_open_brief_fails(repo):
    """REQ-057 AC11: naming both."""
    on_branch(repo, **{"docs/adr/0900-a.md": "# ADR-0900: a\n"})
    proc = run_numbers(repo, "--briefs", briefs_file(repo, (7, "ADR-0900")), "--brief", "5")
    assert proc.returncode == 1
    assert "ADR-0900" in proc.stdout and "#7" in proc.stdout and "#5" in proc.stdout


def test_ac11_the_pull_request_s_own_brief_is_excepted(repo):
    """REQ-057 AC11: reserved by its own brief passes."""
    on_branch(repo, **{"docs/adr/0900-a.md": "# ADR-0900: a\n"})
    proc = run_numbers(repo, "--briefs", briefs_file(repo, (5, "ADR-0900")), "--brief", "5")
    assert (proc.returncode, proc.stdout) == (0, "ok numbers\n")


def test_ac11_a_requirement_and_an_amendment_added_here_are_read(repo):
    """REQ-057 AC11: `REQ-nnn` and `amendment n` count."""
    on_branch(
        repo,
        **{
            "docs/requirements.md": "# R\n\n### REQ-001 — a\n\n### REQ-900 — b\n",
            "docs/runs/proposed-spec-amendments-139.md": "x\n",
        },
    )
    proc = run_numbers(repo, "--briefs", briefs_file(repo, (7, "REQ-900, amendment 139")), "--brief", "5")
    assert proc.returncode == 1
    assert "REQ-900" in proc.stdout and "amendment 139" in proc.stdout


def test_ac11_without_briefs_the_check_is_unchanged(repo):
    """REQ-057 AC11: the governance step passes no list, so no unrelated pull request turns red."""
    on_branch(repo, **{"docs/adr/0900-a.md": "# ADR-0900: a\n"})
    assert run_numbers(repo).returncode == 0


@pytest.mark.parametrize("args", [("--briefs", "x"), ("--brief", "5"), ("--briefs", "x", "--brief", "y")])
def test_ac11_the_two_flags_come_together(repo, args):
    """REQ-057 AC11: a usage error, exit 2."""
    assert repo.run("check_numbers.py", *args).returncode == 2
