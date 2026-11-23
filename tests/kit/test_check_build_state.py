"""Tests of scripts/agk/check_build_state.py."""

from __future__ import annotations

import pytest

ROW1 = "| 2026-11-01 | invented row | REQ-001 |\n"
ROW2 = "| 2026-11-02 | second invented row | REQ-002 |\n"
HEAD = "# Build state\n\n## Done log\n\n| Date | Change | REQs |\n"
TAIL = "\n## Decisions\n\n- invented decision (example.com)\n"
BS = HEAD + ROW1 + ROW2 + TAIL
NEW = "| 2026-11-03 | appended row | REQ-003 |\n"
FAIL = (
    "FAIL build-state: docs/build-state.md is only appended; an existing row was changed or "
    "removed (path class: docs/build-state.md)"
)


@pytest.fixture
def base(repo):
    repo.commit({"docs/build-state.md": BS, "src/a.py": "1\n", "docs/x.md": "x\n"}, "base")
    repo.branch()
    return repo


def check(repo):
    return repo.run("check_build_state.py", "--base", "main")


def test_unrelated_pr_passes(base):
    """REQ-006 AC1"""
    base.commit({"src/a.py": "2\n"})
    assert check(base).returncode == 0


def test_ac1_feature_pr_editing_build_state_fails(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": BS + "row\n", "src/a.py": "2\n"})
    proc = check(base)
    assert proc.returncode == 1
    assert "docs/build-state.md" in proc.stdout


def test_docs_only_pr_may_edit_build_state(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": BS + "row\n", "docs/x.md": "y\n"})
    assert check(base).returncode == 0


def test_readme_is_not_docs(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": BS + "row\n", "README.md": "y\n"})
    assert check(base).returncode == 1


def test_creating_build_state_is_allowed_for_bootstrap(repo):
    """REQ-006 AC1"""
    repo.commit({"src/a.py": "1\n"}, "base")
    repo.branch()
    repo.commit({"docs/build-state.md": BS, "src/a.py": "2\n"})
    assert check(repo).returncode == 0


def test_deleting_build_state_fails(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": None, "docs/x.md": "y\n"})
    assert check(base).returncode == 1


def test_creation_exemption_only_when_absent_at_base(repo):
    """REQ-006 AC1: with the file present at base, an edit alongside code fails."""
    repo.commit({"docs/build-state.md": BS, "src/a.py": "1\n"}, "base")
    repo.branch()
    repo.commit({"docs/build-state.md": BS + "edited\n", "src/a.py": "2\n"})
    proc = check(repo)
    assert proc.returncode == 1
    assert "docs/build-state.md" in proc.stdout


def test_editing_existing_file_uncommitted_fails(base):
    """REQ-006 AC1: uncommitted edits to an existing file are judged against the base too."""
    base.write("docs/build-state.md", BS + "edited\n")
    base.write("src/a.py", "3\n")
    assert check(base).returncode == 1


# --- brief #1836, ADR-0765: principle 4's "only appended" half ----------------------------------


def assert_rejected(proc):
    assert proc.returncode == 1, proc.stdout
    assert FAIL in proc.stdout
    for word in ("invented", "second", "2026-11-0", "REQ-00"):
        assert word not in proc.stdout


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(
            HEAD + ROW1.replace("invented row", "rewritten row") + ROW2 + TAIL, id="rewrite"
        ),
        pytest.param(HEAD + ROW1.replace("|\n", "| \n") + ROW2 + TAIL, id="trailing-space"),
        pytest.param(HEAD + ROW1.replace("\n", "\r\n") + ROW2 + TAIL, id="crlf-line"),
        pytest.param(HEAD + ROW2 + TAIL, id="removed"),
        pytest.param(HEAD + ROW2 + ROW1 + TAIL, id="swapped"),
        pytest.param(HEAD + ROW1 + ROW2 + TAIL.lstrip("\n"), id="blank-line-removed"),
        pytest.param("\ufeff" + BS, id="byte-order-mark"),
        pytest.param(
            HEAD + ROW1 + ROW2 + "\n- invented decision (example.com)\n## Decisions\n",
            id="heading-moved",
        ),
    ],
)
def test_docs_only_change_that_rewrites_a_row_fails(base, text):
    """REQ-006 AC1: brief #1836 answers 1, 2 and 6."""
    base.commit({"docs/build-state.md": text, "docs/x.md": "y\n"})
    assert_rejected(check(base))


def test_a_branch_that_changes_only_the_file_and_removes_a_row_fails(base):
    """REQ-006 AC1: brief #1836, the removed row of CM-14.4."""
    base.commit({"docs/build-state.md": HEAD + ROW1 + TAIL})
    assert_rejected(check(base))


def test_every_line_turned_to_crlf_fails(base):
    """REQ-006 AC1: brief #1836 answer 2, committed CRLF is a changed row."""
    base.commit({"docs/build-state.md": BS.replace("\n", "\r\n")})
    assert_rejected(check(base))


def test_an_uncommitted_rewrite_fails(base):
    """REQ-006 AC1: brief #1836 answer 6, the working tree is read."""
    base.write("docs/build-state.md", HEAD + ROW2 + TAIL)
    assert_rejected(check(base))


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(BS + NEW, id="at-the-end"),
        pytest.param(HEAD + ROW1 + ROW2 + NEW + TAIL, id="before-decisions"),
        pytest.param(HEAD + ROW1 + NEW + ROW2 + TAIL, id="between-rows"),
    ],
)
def test_appended_rows_pass(base, text):
    """REQ-006 AC1: brief #1836 answers 1 and 6."""
    base.commit({"docs/build-state.md": text})
    proc = check(base)
    assert proc.returncode == 0, proc.stdout
    assert "ok build-state (rows appended)" in proc.stdout


def test_an_append_to_a_file_with_no_final_newline_passes(repo):
    """REQ-006 AC1: brief #1836 answer 2, the one exception."""
    repo.commit({"docs/build-state.md": BS.rstrip("\n")}, "base")
    repo.branch()
    repo.commit({"docs/build-state.md": BS + NEW})
    proc = check(repo)
    assert proc.returncode == 0, proc.stdout
    assert "(rows appended)" in proc.stdout


def test_an_autocrlf_only_working_tree_passes(base):
    """REQ-006 AC1: brief #1836 answer 2, committed bytes decide (ADR-0550)."""
    base.commit({"docs/build-state.md": BS + NEW})
    base.git("config", "core.autocrlf", "true")
    (base.root / "docs/build-state.md").write_bytes((BS + NEW).replace("\n", "\r\n").encode())
    proc = check(base)
    assert proc.returncode == 0, proc.stdout
    assert "(rows appended)" in proc.stdout


def test_a_mode_only_change_keeps_the_docs_only_line(base):
    """REQ-006 AC1: brief #1836 answer 1."""
    (base.root / "docs/build-state.md").chmod(0o755)
    base.git("add", "-A")
    base.git("commit", "-q", "-m", "mode")
    proc = check(base)
    assert proc.returncode == 0, proc.stdout
    assert "ok build-state (docs-only change)" in proc.stdout


def test_a_row_changed_and_changed_back_passes(base):
    """REQ-006 AC1: brief #1836 answer 6, the net change is judged."""
    base.commit({"docs/build-state.md": HEAD + ROW2 + TAIL})
    base.commit({"docs/build-state.md": BS + NEW})
    assert check(base).returncode == 0


def test_a_file_that_is_not_utf8_is_compared_as_bytes(repo):
    """REQ-006 AC1: brief #1836 answer 6, no decode error and no byte named."""
    path = repo.root / "docs/build-state.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"# State\n| \xff row |\n")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "base")
    repo.branch()
    path.write_bytes(b"# State\n| \xfe row |\n")
    repo.git("commit", "-qam", "rewrite")
    proc = check(repo)
    assert proc.returncode == 1 and FAIL in proc.stdout, proc.stdout + proc.stderr
    path.write_bytes(b"# State\n| \xff row |\n| \xfe new |\n")
    repo.git("commit", "-qam", "append")
    proc = check(repo)
    assert proc.returncode == 0 and "(rows appended)" in proc.stdout, proc.stdout + proc.stderr


@pytest.mark.parametrize("how", ["cli", "AGK_BASE", "GITHUB_BASE_REF", "default_branch"])
def test_each_way_to_name_the_base_compares_with_its_merge_base(base, how):
    """REQ-006 AC1: brief #1836 answer 5, the settings that resolve the base."""
    base.commit({"docs/build-state.md": HEAD + ROW2 + TAIL})
    if how == "cli":
        proc = check(base)
    elif how == "AGK_BASE":
        proc = base.run("check_build_state.py", AGK_BASE="main")
    elif how == "GITHUB_BASE_REF":
        base.git("update-ref", "refs/remotes/origin/main", "main")
        proc = base.run("check_build_state.py", GITHUB_BASE_REF="main", CI="true")
    else:
        proc = base.run("check_build_state.py")
    assert_rejected(proc)


def test_a_base_that_does_not_resolve_names_no_ref(base):
    """REQ-006 AC1: brief #1836 answer 5, today's line."""
    proc = base.run("check_build_state.py", "--base", "no-such-branch-example")
    assert proc.returncode == 1
    assert "no-such-branch-example" not in proc.stdout
