"""Kit-only tests of the playbook: templates, brief, the architect role and its skill (SPEC-0013).

Rules 6 to 17 and 27. The guard's table of commands and paths is in
`tests/kit/test_architect_guard.py` (the hook is installed, so its test is). No model, no network.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import metrics  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "playbook.py"
TEMPLATES = KIT_ROOT / "kit" / "templates" / "playbook"
AGENT = KIT_ROOT / ".claude" / "agents" / "architect.md"
PLACEHOLDERS = {
    "repo",
    "default_branch",
    "next_req",
    "next_adr",
    "next_spec",
    "branch_prefix",
    "date",
    "sha",
    "n",
}
NAMES = [
    "brief-overnight.md",
    "brief-day.md",
    "rulings-table.md",
    "verdict.md",
    "live-proof-plan.md",
    "held-out-findings.md",
    "pilot-week-record.md",
]
HEADINGS = {
    "brief-overnight.md": ["## Rules block", "## Items", "## Report format"],
    "brief-day.md": ["## Rules block", "## Items", "## Report format"],
    "live-proof-plan.md": ["## Preconditions", "## Steps", "## Restore", "## Result"],
    "pilot-week-record.md": ["## Week", "## Answers from the report alone", "## Marks", "## Score"],
}
TABLES = {
    "rulings-table.md": ["Q", "Ruling", "Where"],
    "live-proof-plan.md": ["Step", "Command", "Expected", "Recorded in"],
    "held-out-findings.md": [
        "#",
        "PR",
        "Commit",
        "Finding",
        "Recorded on",
        "Seen by a reviewer agent",
    ],
}


def text(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_ac1_the_seven_templates_exist_and_only_those(tmp_path):
    """REQ-020 AC1: rule 14."""
    assert sorted(p.name for p in TEMPLATES.iterdir()) == sorted(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_ac1_each_template_is_utf8_markdown_with_closed_placeholders_and_no_typed_numbers(name):
    """REQ-020 AC1: rule 15 (placeholders from the closed set; no literal PR, ADR or REQ number)."""
    body = text(name)
    assert {m for m in re.findall(r"\{\{(\w+)\}\}", body)} <= PLACEHOLDERS, name
    for pattern in (r"PR #\d+", r"ADR-\d+", r"REQ-\d+", r"SPEC-\d+", "gh pr view"):
        assert not re.search(pattern, body), (name, pattern)
    assert "{{" not in re.sub(r"\{\{\w+\}\}", "", body)


@pytest.mark.parametrize("name", list(HEADINGS))
def test_ac1_required_headings_are_present_and_in_order(name):
    """REQ-020 AC1: rule 15."""
    lines = text(name).splitlines()
    positions = [lines.index(h) for h in HEADINGS[name]]
    assert positions == sorted(positions)


@pytest.mark.parametrize("name", list(TABLES))
def test_ac1_required_table_columns(name):
    """REQ-020 AC1: rule 15."""
    header = next(ln for ln in text(name).splitlines() if ln.startswith("|"))
    assert [c.strip() for c in header.strip("|").split("|")] == TABLES[name]


@pytest.mark.parametrize("name", ["brief-overnight.md", "brief-day.md"])
def test_ac1_the_rules_block_has_the_three_sentences_and_the_state_command(name):
    """REQ-020 AC1: rule 15 (a GET for the state of a pull request)."""
    block = text(name).split("## Rules block")[1].split("## Items")[0]
    for sentence in (
        "Never merge.",
        "Never poll CI.",
        "Check the state of your pull request before every push",
    ):
        assert sentence in block
    assert "gh api repos/{{repo}}/pulls/{{n}}" in block


def test_ac1_the_verdict_template_first_line_matches_the_verdict_rule():
    """REQ-020 AC1: rule 11 (the template is the convention, exactly)."""
    first = text("verdict.md").splitlines()[0].replace("{{sha}}", "abc1234")
    assert metrics.VERDICT.fullmatch(first)
    body = text("verdict.md")
    for form in ("Verdict: cleared", "Verdict: fix list", "Verdict: rejected"):
        assert form in body
    assert not metrics.VERDICT.fullmatch(first + " ")  # nothing follows on that line


def test_ac1_no_instruction_file_names_the_graphql_command():
    """REQ-020 AC1: rule 17 (CLAUDE.md, templates, skills, agents, workflows)."""
    paths = [KIT_ROOT / "CLAUDE.md", *TEMPLATES.iterdir(), *(KIT_ROOT / "skills").rglob("SKILL.md")]
    paths += list((KIT_ROOT / ".claude" / "agents").glob("*.md"))
    paths += list((KIT_ROOT / ".github" / "workflows").glob("*.yml"))
    for path in paths:
        assert "gh pr view" not in path.read_text(encoding="utf-8"), path.name


def test_ac1_claude_md_carries_the_state_of_a_pull_request_line():
    """REQ-020 AC1: rule 17 (one line, a GET)."""
    body = (KIT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "gh api repos/{owner}/{repo}/pulls/{n}" in body and "(a GET)" in body
    assert body.count("pulls/{n}") == 1


# --- brief (rule 16) --------------------------------------------------------------------------


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=clean_env(),
    )


@pytest.fixture
def repo(tmp_path):
    root = make_repo(tmp_path / "proj")
    for rel, body in (
        ("docs/requirements.md", "### REQ-007 — T\n\n- Status: planned\n"),
        ("docs/specs/0003-a.md", "x\n"),
        ("docs/adr/0011-b.md", "x\n"),
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


@pytest.mark.parametrize("kind", ["overnight", "day"])
def test_ac1_brief_fills_the_numbers_the_repository_and_the_branch_names(repo, kind):
    """REQ-020 AC1: rule 16 (next free numbers from the ref; branch names `<p>/<slug>`)."""
    proc = run(
        "brief",
        "--kind",
        kind,
        "--branch-prefix",
        "day-15",
        "--repo",
        "o/r",
        "--ref",
        "main",
        "--date",
        "2026-10-19",
        "--root",
        str(repo),
    )
    assert proc.returncode == 0, proc.stdout
    out = proc.stdout
    assert "requirement REQ-008, ADR ADR-0012, spec SPEC-0004" in out
    assert "Repository: o/r (default branch `main`)" in out
    assert "`day-15/<slug>`" in out and "2026-10-19" in out
    assert (
        "gh api repos/o/r/pulls/{{n}}" in out
    )  # the pull request number is never written in advance
    assert not re.search(r"PR #\d+", out)
    assert "{{repo}}" not in out and "{{next_adr}}" not in out and "{{branch_prefix}}" not in out


def test_ac1_brief_reads_the_ref_not_the_work_tree(repo):
    """REQ-020 AC1: rule 16."""
    (repo / "docs" / "adr" / "0040-draft.md").write_text("x\n", encoding="utf-8")
    out = run(
        "brief",
        "--kind",
        "day",
        "--branch-prefix",
        "p",
        "--repo",
        "o/r",
        "--ref",
        "main",
        "--root",
        str(repo),
    ).stdout
    assert "ADR-0012" in out


@pytest.mark.parametrize(
    "args",
    [
        ["--kind", "week", "--branch-prefix", "p"],
        ["--kind", "day", "--branch-prefix", "Bad Prefix"],
        ["--kind", "day", "--branch-prefix", ""],
        ["--kind", "day"],
    ],
)
def test_ac1_brief_refuses_a_bad_kind_or_prefix(repo, args):
    """REQ-020 AC1: rule 16."""
    proc = run("brief", *args, "--repo", "o/r", "--ref", "main", "--root", str(repo))
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL playbook:")


def test_ac1_brief_without_a_resolvable_ref_fails_and_a_bad_command_is_usage(repo):
    """REQ-020 AC1: rule 16 (ids are read, never guessed)."""
    proc = run(
        "brief", "--kind", "day", "--branch-prefix", "p", "--repo", "o/r", "--root", str(repo)
    )
    assert proc.returncode == 1  # no origin/main
    assert run("bogus").returncode == 2 and run("brief", "--oops", "x").returncode == 2


def test_ac1_brief_writes_nothing(repo, tmp_path):
    """REQ-020 AC1: rule 16 (prints only)."""
    before = sorted(
        p.relative_to(repo).as_posix() for p in repo.rglob("*") if ".git" not in p.parts
    )
    run(
        "brief",
        "--kind",
        "day",
        "--branch-prefix",
        "p",
        "--repo",
        "o/r",
        "--ref",
        "main",
        "--root",
        str(repo),
    )
    after = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if ".git" not in p.parts)
    assert before == after


# --- the role (rules 6 to 9, 11, 13) ---------------------------------------------------------


def frontmatter(body: str) -> str:
    return body.split("---\n", 2)[1]


def test_ac1_the_role_file_has_the_tool_list_and_the_guard_hook():
    """REQ-020 AC1: rules 6 and 9 (the tool list, and the guard hook is declared)."""
    head = frontmatter(AGENT.read_text(encoding="utf-8"))
    assert re.search(r"(?m)^name: architect$", head)
    assert re.search(r"(?m)^tools: Read, Grep, Glob, Edit, Write, Bash$", head)
    assert "PreToolUse:" in head and "architect_guard.py" in head and "hooks:" in head
    assert "Edit|Write" in head and "Bash" in head


def test_ac1_the_role_file_states_the_role_rules():
    """REQ-020 AC1: rules 8, 10, 11 and 12 (each sentence the role is held to)."""
    body = AGENT.read_text(encoding="utf-8")
    for needle in (
        "claude --agent architect",
        "Verdict: cleared <sha>",
        "Verdict: fix list",
        "Verdict: rejected",
        "at least 7 hex characters",
        "Never execute the pull request's code",
        "Merge, enable auto-merge, or post `Verdict: cleared` on a pull request you authored",
        "Set a spec `Approved` or an ADR `Accepted`, except in a final commit that a person orders",
        "`## Rulings`",
        "Claim to catch defects",
        "(verify",
    ):
        assert needle in body, needle


def test_ac1_the_role_file_and_guard_name_no_plugin_variable():
    """REQ-020 AC1: SPEC-0005 rule 2 (the law files do not depend on the plugin)."""
    for path in (AGENT, KIT_ROOT / ".claude" / "hooks" / "architect_guard.py"):
        body = path.read_text(encoding="utf-8")
        assert "CLAUDE_PLUGIN" not in body and "/agk:" not in body


def test_ac1_the_skill_prints_the_start_command_and_checks_read_only(repo):
    """REQ-020 AC1: rule 7 (prerequisites; no file written)."""
    proc = run("architect", "--root", str(repo))
    assert proc.returncode == 1 and "claude --agent architect" in proc.stdout
    assert "agk.toml: missing" in proc.stdout
    (repo / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    ok = run("architect", "--root", str(repo))
    assert (
        ok.returncode == 0
        and "agk.toml: present" in ok.stdout
        and "default branch: main" in ok.stdout
    )
    assert "gh:" in ok.stdout


def test_ac1_the_architect_skill_is_a_reader_and_says_the_guard_is_not_enforced_elsewhere():
    """REQ-020 AC1: rule 7 (Q-K4-85: plain about what a loaded role cannot enforce)."""
    body = (KIT_ROOT / "skills" / "architect" / "SKILL.md").read_text(encoding="utf-8")
    assert "claude --agent architect" in body and "are **not** enforced" in body
    assert "disable-model-invocation" not in body
