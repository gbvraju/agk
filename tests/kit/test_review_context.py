"""Tests of scripts/agk/review_context.py (SPEC-0003 rules 4-7, 18-19)."""

from __future__ import annotations

import ast
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys

import pytest
from review_fixtures import BUILDERS, GOOD_BODY, ROOT, build, clean_env, snapshot

SCRIPT = ROOT / "scripts" / "agk" / "review_context.py"
CHECKS = ROOT / "scripts" / "agk"
SECTIONS = [
    "Context problems",
    "PR body",
    "Diff",
    "Changed files",
    "Requirements",
    "Protected classes touched",
    "Referenced specs and ADRs",
    "Principles",
    "Operating rules",
]


def context(fx, *extra: str, body: str | None = "file", stdin: str | None = None):
    args = [sys.executable, str(SCRIPT), "--base", "main", *extra]
    if body == "file":
        args += ["--body", str(fx.body)]
    elif body == "stdin":
        args += ["--body", "-"]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        args, cwd=fx.repo, capture_output=True, text=True, env=clean_env(), input=stdin
    )


def top_headings(text: str) -> list[str]:
    heads, fence = [], None
    for line in text.splitlines():
        if fence:
            if line.strip() == fence:
                fence = None
        elif line.startswith("~~~~"):
            fence = line.rstrip("abcdefghijklmnopqrstuvwxyz").strip()
        elif line.startswith("## "):
            heads.append(line[3:])
    return heads


def section(text: str, name: str) -> str:
    """The text of one top-level section, fences respected."""
    out, current, fence = {}, None, None
    for line in text.splitlines():
        if fence:
            if line.strip() == fence:
                fence = None
        elif line.startswith("~~~~"):
            fence = line.rstrip("abcdefghijklmnopqrstuvwxyz").strip()
        elif line.startswith("## "):
            current = line[3:]
            out[current] = []
            continue
        if current is not None:
            out[current].append(line)
    return "\n".join(out[name])


def problems_of(text: str) -> str:
    return section(text, "Context problems")


@pytest.fixture(params=sorted(BUILDERS))
def fixture_pr(request, tmp_path):
    return build(request.param, tmp_path)


def test_ac1_context_is_byte_identical_across_two_runs(fixture_pr):
    """REQ-013 AC1: rules 6 and 19."""
    first = context(fixture_pr)
    second = context(fixture_pr)
    assert first.returncode == 0, first.stdout + first.stderr
    assert first.stdout == second.stdout
    assert first.stdout.startswith("# Review context\n")


def test_ac1_sections_appear_in_the_order_of_rule_5(tmp_path):
    """REQ-013 AC1: rules 5 and 19."""
    out = context(build("F8", tmp_path)).stdout
    assert top_headings(out) == SECTIONS


def test_ac1_hunks_are_numbered_and_headed_with_old_and_new_lines(tmp_path):
    """REQ-013 AC1: rule 5(b)."""
    out = context(build("F7", tmp_path)).stdout
    heads = re.findall(r"^### (\S+):H(\d+) \(old (\d+),(\d+) new (\d+),(\d+)\)$", out, re.M)
    assert [(h[0], h[1]) for h in heads] == [("docs/notes.md", "1"), ("docs/other.md", "2")]
    assert heads[0][2:] == ("0", "0", "1", "1")


def test_ac1_untracked_files_are_part_of_the_diff(tmp_path):
    """REQ-013 AC1: rule 5(b), merge-base..worktree."""
    fx = build("F8", tmp_path)
    (fx.repo / "docs" / "late.md").write_text("late\n", encoding="utf-8")
    out = context(fx).stdout
    assert re.search(r"^### docs/late\.md:H\d+ \(old 0,0 new 1,1\)$", out, re.M)


def test_ac1_requirement_section_and_markers_are_included(tmp_path):
    """REQ-013 AC1: rule 5(c)."""
    out = context(build("F8", tmp_path)).stdout
    reqs = section(out, "Requirements")
    assert "### REQ-001" in reqs and "AC2 does another" in reqs and "Status: done" in reqs
    assert "tests/test_demo.py" in reqs


def test_ac1_protected_classes_touched_and_adr_coverage_are_listed(tmp_path):
    """REQ-013 AC1: rule 5(d); F1 is detectable from the context."""
    out = context(build("F1", tmp_path)).stdout
    classes = section(out, "Protected classes touched")
    assert "scripts/agk/" in classes
    assert "not named in any changed ADR" in classes
    clean = context(build("F8", tmp_path)).stdout
    assert "none" in section(clean, "Protected classes touched")


def test_ac1_specs_and_adrs_of_the_advanced_requirement_are_included(tmp_path):
    """REQ-013 AC1: rule 5(e)."""
    out = context(build("F8", tmp_path)).stdout
    refs = section(out, "Referenced specs and ADRs")
    assert "### docs/specs/0001-demo.md" in refs and "### docs/adr/0001-demo.md" in refs
    assert "Do the first thing." in refs


def test_ac1_ids_named_in_the_body_pull_in_their_files(tmp_path):
    """REQ-013 AC1: rule 5(e), named by id in the PR body."""
    fx = build("F8", tmp_path)
    fx.body.write_text(GOOD_BODY.replace("Advances: REQ-001", "Advances: REQ-002 SPEC-0001"))
    out = context(fx).stdout
    assert "### docs/specs/0001-demo.md" in out
    assert "SPEC-0001" not in problems_of(out)


def test_ac1_principles_are_included(tmp_path):
    """REQ-013 AC1: rule 5(f)."""
    out = context(build("F8", tmp_path)).stdout
    principles = section(out, "Principles")
    assert "2. Agents never merge." in principles


def test_ac1_f5_missing_advances_is_a_context_problem(tmp_path):
    """REQ-013 AC1: rule 7 and 19."""
    out = context(build("F5", tmp_path)).stdout
    assert "no `Advances:` line" in problems_of(out)
    assert "none" in problems_of(context(build("F8", tmp_path / "x")).stdout)


def test_ac1_unknown_req_missing_spec_and_empty_diff_are_context_problems(tmp_path):
    """REQ-013 AC1: rule 7."""
    fx = build("F8", tmp_path)
    fx.body.write_text(GOOD_BODY.replace("REQ-001", "REQ-777") + "\nSee SPEC-0099 and ADR-0042.\n")
    problems = problems_of(context(fx).stdout)
    assert "REQ-777" in problems and "SPEC-0099" in problems and "ADR-0042" in problems
    empty = build("F8", tmp_path / "e")
    subprocess.run(["git", "checkout", "-q", "main"], cwd=empty.repo, check=True)  # nosec B603 B607 - fixed argument list, no shell
    assert "the diff is empty" in problems_of(context(empty).stdout)


def test_ac1_f9_injected_body_cannot_forge_structure(tmp_path):
    """REQ-013 AC1: rules 3 and 18 (F9). The body is fenced; headings and hunks stay real."""
    out = context(build("F9", tmp_path)).stdout
    assert top_headings(out) == SECTIONS
    assert "fake.py:H99" in out  # present, inside the fence, as data
    heads = re.findall(r"^### (\S+):H(\d+) ", section(out, "Diff"), re.M)
    assert heads == [("docs/notes.md", "1")]
    ok = context(build("F8", tmp_path / "ok")).stdout
    assert top_headings(ok) == top_headings(out)


def test_ac1_f10_oversized_diff_is_truncated_and_marked(tmp_path):
    """REQ-013 AC1: rule 6 (caps from agk.toml) and F10."""
    out = context(build("F10", tmp_path)).stdout
    assert re.search(r"^\[truncated: \d+ lines omitted\]$", out, re.M)
    assert re.search(r"^Truncated: yes$", out, re.M)
    clean = context(build("F8", tmp_path / "c")).stdout
    assert re.search(r"^Truncated: no$", clean, re.M)
    assert "[truncated" not in clean


@pytest.mark.parametrize("bad", ["0", "-5", '"many"', "true", "1.5"])
def test_ac1_invalid_cap_is_refused_naming_the_setting(tmp_path, bad):
    """REQ-013 AC1: rule 6. The message names the setting and never the value."""
    fx = build("F8", tmp_path)
    (fx.repo / "agk.toml").write_text(
        f'default_branch = "main"\ntest_dirs = ["tests"]\nreview_other_cap = {bad}\n',
        encoding="utf-8",
    )
    proc = context(fx)
    assert proc.returncode == 1
    assert "review_other_cap" in proc.stdout
    assert bad.strip('"') not in proc.stdout.replace("review_other_cap", "")


def test_ac1_body_can_come_from_stdin(tmp_path):
    """REQ-013 AC1: rule 4."""
    fx = build("F8", tmp_path)
    via_stdin = context(fx, body="stdin", stdin=fx.body.read_text(encoding="utf-8"))
    assert via_stdin.returncode == 0
    assert via_stdin.stdout == context(fx).stdout


def test_ac1_usage_errors_exit_2(tmp_path):
    """REQ-013 AC1: rule 4."""
    fx = build("F8", tmp_path)
    assert context(fx, body=None).returncode == 2
    assert context(fx, "--nope").returncode == 2


def test_ac1_script_writes_nothing(tmp_path):
    """REQ-013 AC1: rule 19 (write guard)."""
    fx = build("F8", tmp_path)
    before = snapshot(fx.repo)
    assert context(fx).returncode == 0
    assert snapshot(fx.repo) == before


def test_ac1_script_has_no_network_or_write_calls():
    """REQ-013 AC1: rule 4 and 19 (import guard)."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names, writes = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute) and node.attr in {
            "write_text",
            "write_bytes",
            "unlink",
        }:
            writes.append(node.attr)
    forbidden = {"subprocess", "socket", "urllib", "http", "ftplib", "smtplib", "requests", "ssl"}
    assert not names & forbidden
    assert names <= set(sys.stdlib_module_names) | {"common"}
    assert not writes


# --- F1-F7: the mechanical defects are detectable from the context (rule 20) -------------------

CHECK_FOR = {
    "F1": ("check_protected_changes.py", "scripts/agk/"),
    "F2": ("check_requirements.py", "REQ-003"),
    "F3": ("check_specs.py", "docs/specs/0001-demo.md"),
    "F4": ("check_adrs.py", "0001"),
    "F5": ("check_pr_body.py", "Advances"),
    "F6": ("check_build_state.py", "docs/build-state.md"),
}


@pytest.mark.parametrize("name", sorted(CHECK_FOR))
def test_ac1_existing_check_fails_on_the_fixture(tmp_path, name):
    """REQ-013 AC1: rule 20. The expected finding comes from the existing check."""
    fx = build(name, tmp_path)
    script, needle = CHECK_FOR[name]
    args = [sys.executable, str(CHECKS / script), "--base", "main"]
    if name == "F5":
        args = [sys.executable, str(CHECKS / script), str(fx.body)]
    proc = subprocess.run(args, cwd=fx.repo, capture_output=True, text=True, env=clean_env())  # nosec B603 - fixed argument list, no shell
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert needle in proc.stdout


def test_ac1_f2_context_shows_done_without_a_marker(tmp_path):
    """REQ-013 AC1: rule 20 (F2)."""
    out = context(build("F2", tmp_path)).stdout
    reqs = section(out, "Requirements")
    assert "### REQ-003" in reqs and "Status: done" in reqs
    assert "markers: none" in reqs


def test_ac1_f3_f4_context_shows_edited_approved_spec_and_accepted_adr(tmp_path):
    """REQ-013 AC1: rule 20 (F3, F4)."""
    f3 = context(build("F3", tmp_path / "a")).stdout
    assert re.search(r"^### docs/specs/0001-demo\.md:H\d+ ", f3, re.M) and "Status: Approved" in f3
    assert "proposed-spec-amendments" not in section(f3, "Diff")
    f4 = context(build("F4", tmp_path / "b")).stdout
    assert re.search(r"^### docs/adr/0001-demo\.md:H\d+ ", f4, re.M) and "Status: Accepted" in f4


def test_ac1_f6_f7_context_shows_the_diff_against_the_body(tmp_path):
    """REQ-013 AC1: rule 20 (F6, F7)."""
    f6 = context(build("F6", tmp_path / "a")).stdout
    assert re.search(r"^### docs/build-state\.md:H\d+ ", f6, re.M)
    f7 = context(build("F7", tmp_path / "b")).stdout
    assert "docs/other.md" in f7 and "docs/other.md" not in f7.split("## Diff")[0]


def test_ac1_base_may_come_from_the_environment(tmp_path):
    """REQ-013 AC1: rule 4 (--base, AGK_BASE, then the default branch)."""
    fx = build("F8", tmp_path)
    env = {**clean_env(), "AGK_BASE": "main"}
    args = [sys.executable, str(SCRIPT), "--body", str(fx.body)]
    via_env = subprocess.run(args, cwd=fx.repo, capture_output=True, text=True, env=env)  # nosec B603 - fixed argument list, no shell
    assert via_env.returncode == 0, via_env.stdout
    assert via_env.stdout == context(fx).stdout
    default = subprocess.run(args, cwd=fx.repo, capture_output=True, text=True, env=clean_env())  # nosec B603 - fixed argument list, no shell
    assert default.returncode == 0, default.stdout  # the default branch of agk.toml is main
    assert default.stdout == via_env.stdout


def test_ac1_a_path_named_in_a_changed_file_pulls_in_that_document(tmp_path):
    """REQ-013 AC1: rule 5(e), named in the text of a changed file."""
    fx = build("F8", tmp_path)
    (fx.repo / "docs" / "notes.md").write_text("see docs/specs/0001-demo.md\n", encoding="utf-8")
    fx.body.write_text(
        GOOD_BODY.replace("Advances: REQ-001", "Advances: REQ-002"), encoding="utf-8"
    )
    refs = section(context(fx).stdout, "Referenced specs and ADRs")
    assert "### docs/specs/0001-demo.md" in refs


# --- amendments 9: operating rules, changed files in full (shadow review 2) ---------------------


def test_ac1_operating_rules_of_claude_md_are_always_included(tmp_path):
    """REQ-013 AC1: SPEC-0003 rule 5 as amended. CLAUDE.md is in the context even when untouched."""
    out = context(build("F8", tmp_path)).stdout
    rules = section(out, "Operating rules")
    assert "4. Tests first. Every check ships with tests of the check (`tests/kit/`)." in rules
    assert "8. Product-neutral: nothing names a company, product, person or environment." in rules
    assert "CLAUDE.md" not in section(out, "Diff")


def test_ac1_missing_claude_md_is_a_context_problem(tmp_path):
    """REQ-013 AC1: rule 7 as amended."""
    fx = build("F8", tmp_path)
    (fx.repo / "CLAUDE.md").unlink()
    out = context(fx).stdout
    assert "CLAUDE.md is missing" in problems_of(out)
    assert section(out, "Operating rules").strip() == "none"


def test_ac1_changed_files_are_included_with_their_full_current_text(tmp_path):
    """REQ-013 AC1: rule 5 as amended, in path order."""
    out = context(build("F7", tmp_path)).stdout
    changed = section(out, "Changed files")
    assert changed.index("### docs/notes.md") < changed.index("### docs/other.md")
    assert "notes\n" in changed and "other\n" in changed


def test_ac1_f11_a_rule_next_to_a_change_is_now_visible(tmp_path):
    """REQ-013 AC1: a case from shadow review 2. The unchanged rule 8 sits outside the hunk."""
    out = context(build("F11", tmp_path)).stdout
    rule_8 = "8. Product-neutral: nothing names a company, product, person or environment."
    assert rule_8 not in section(out, "Diff")
    changed = section(out, "Changed files")
    assert "### CLAUDE.md" in changed and rule_8 in changed
    assert rule_8 in section(out, "Operating rules")


def test_ac1_f12_installed_check_without_installed_tests_is_visible(tmp_path):
    """REQ-013 AC1: a case from shadow review 2. The context holds what a reviewer needs to see it.

    The check is listed by the manifest, its tests sit in an uninstalled directory, and CLAUDE.md
    (principle 4 in operating form) says every check ships with tests under tests/kit/.
    """
    out = context(build("F12", tmp_path)).stdout
    assert "Every check ships with tests of the check" in section(out, "Operating rules")
    changed = section(out, "Changed files")
    for path in (
        "kit/manifest.json",
        "scripts/agk/check_new.py",
        "tests/kit_dev/test_check_new.py",
    ):
        assert f"### {path}" in changed, path
    manifest = changed.split("### kit/manifest.json", 1)[1].split("\n### ", 1)[0]
    assert '"scripts/agk/check_new.py"' in manifest
    assert '"tests/kit/test_check_a.py"' in manifest  # a line outside the hunk
    assert "check_new" not in manifest.replace('"scripts/agk/check_new.py"', "")
    assert "tests/kit/test_check_new.py" not in out.split("## Operating rules", 1)[0].replace(
        "tests/kit_dev/test_check_new.py", ""
    )
    protected = section(out, "Protected classes touched")
    assert "scripts/agk/" in protected and "named in docs/adr/0002-new-check.md" in protected


def test_ac1_changed_files_deleted_binary_and_oversized(tmp_path):
    """REQ-013 AC1: rules 5 and 6 as amended. Deleted and binary files are named, not embedded."""
    fx = build("F8", tmp_path)
    (fx.repo / "tests" / "test_demo.py").unlink()
    (fx.repo / "docs" / "blob.bin").write_bytes(b"\x00\x01\x02")
    changed = section(context(fx).stdout, "Changed files")
    assert "### tests/test_demo.py (deleted)" in changed
    assert "### docs/blob.bin (not shown: binary or too large)" in changed


def test_ac1_changed_files_are_capped_by_review_other_cap(tmp_path):
    """REQ-013 AC1: rule 6 as amended. The cut is marked and the header says Truncated: yes."""
    fx = build("F8", tmp_path)
    (fx.repo / "agk.toml").write_text(
        'default_branch = "main"\ntest_dirs = ["tests"]\nreview_other_cap = 8\n', encoding="utf-8"
    )
    (fx.repo / "docs" / "long.md").write_text("".join(f"row {i}\n" for i in range(50)))
    out = context(fx).stdout
    assert re.search(r"^Truncated: yes$", out, re.M)
    assert re.search(r"^\[truncated: \d+ lines omitted\]$", section(out, "Changed files"), re.M)


def test_ac1_context_with_full_files_stays_deterministic(tmp_path):
    """REQ-013 AC1: rule 6."""
    fx = build("F12", tmp_path)
    assert context(fx).stdout == context(fx).stdout
