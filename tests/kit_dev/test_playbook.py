"""Kit-only tests of the playbook: templates, brief, the architect role and its skill (SPEC-0013).

Rules 6 to 17 and 27. The guard's table of commands and paths is in
`tests/kit/test_architect_guard.py` (the hook is installed, so its test is). No model, no network.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo, set_handle

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
    "shadow-record.md",
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


def test_ac1_the_eight_templates_exist_and_only_those(tmp_path):
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
    # CLAUDE.md points at the core-rules page, which holds its former list (ADR-0247).
    rels = ("CLAUDE.md", "config/core-rules.md")
    body = "".join((KIT_ROOT / rel).read_text(encoding="utf-8") for rel in rels)
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


# --- /agk:start (rules 2 to 5) ----------------------------------------------------------------

PRINCIPLES = "# Principles\n\nOne.\n"
VISION_TEMPLATE = "# Vision\n\nTODO(maintainers): replace this paragraph.\n"
ADR1 = "# ADR-0001: adopts agk\n\n- Status: Accepted\n- Date: 2026-01-01\n- Requirements: REQ-001\n"
GOOD_VISION = """# Vision

## What this is for

A tool that keeps a reading list.

## Who it serves

Readers who forget what they meant to read.

## How success is measured

A reader finds a saved item in under 10 seconds.

## Out of scope

Syncing between devices.

## Project rules

- Prefer plain files over a database. <!-- project-specific -->
"""
GOOD_CHARTER = """# ADR-0002: the project charter

- Status: Proposed
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

Protected classes: `constitution/`

## Context

The statement, restated as data.

## Decision

1. **Milestones**
   - M1: a saved list exists. exit: 3 items can be saved and read back.
   - M2: export. exit: every saved item is in the exported file.
2. **Non-goals**
   - Syncing between devices.
3. **Done means**
   - The milestones' exit statements hold and a person merged the work.
4. **Discovery**
   - users: readers, who pay nothing
   - existing: one public repository
   - runs: a laptop, not portable
   - data: saved items, kept for a year
   - scale: one reader
   - compliance: none

## Consequences

The ruleset recorded in ADR-0001 stays as it is.

## Residual

None.
"""


@pytest.fixture
def started(tmp_path):
    root = make_repo(tmp_path / "proj")
    files = {
        "agk.toml": 'default_branch = "main"\n',
        "constitution/principles.md": PRINCIPLES,
        "constitution/vision.md": VISION_TEMPLATE,
        "docs/adr/0001-adopt-agk.md": ADR1,
        "docs/requirements.md": "### REQ-001 — T\n\n- Status: planned\n",
    }
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "start/a-reading-list")
    return root


def good_start(root, vision=GOOD_VISION, charter=GOOD_CHARTER):
    (root / "constitution" / "vision.md").write_text(vision, encoding="utf-8")
    (root / "docs" / "adr" / "0002-project-charter.md").write_text(charter, encoding="utf-8")


def check_start(root):
    return run("check-start", "--base", "main", "--root", str(root))


def test_ac1_start_ids_reads_the_next_adr_and_names_the_branch(started):
    """REQ-020 AC1: rules 2 and 4 (the number is read from the ref, never guessed)."""
    proc = run(
        "start-ids",
        "--statement",
        "A reading list for me.",
        "--ref",
        "main",
        "--root",
        str(started),
    )
    assert proc.returncode == 0, proc.stdout
    assert json.loads(proc.stdout) == {
        "adr": "0002",
        "slug": "a-reading-list-for-me",
        "branch": "start/a-reading-list-for-me",
    }


def test_ac1_start_refuses_without_agk_toml_and_installs_nothing(started):
    """REQ-020 AC1: rule 2 (it does not call init or adopt)."""
    (started / "agk.toml").unlink()
    before = sorted(p.name for p in started.rglob("*") if ".git" not in p.parts)
    proc = run("start-ids", "--statement", "x", "--ref", "main", "--root", str(started))
    assert proc.returncode == 1 and "/agk:init or /agk:adopt first" in proc.stdout
    assert sorted(p.name for p in started.rglob("*") if ".git" not in p.parts) == before


@pytest.mark.parametrize("statement", ["", "   ", "!!!", "x" * 1501])
def test_ac1_start_refuses_an_empty_or_long_statement(started, statement):
    """REQ-020 AC1: rule 3 (at most 1,500 characters)."""
    proc = run("start-ids", "--statement", statement, "--ref", "main", "--root", str(started))
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL playbook:")


def test_ac1_a_statement_of_1500_characters_in_two_paragraphs_is_accepted(started):
    """REQ-020 AC1: rule 3 (one or more paragraphs)."""
    text = ("a" * 700) + "\n\n" + ("b" * 798)
    assert len(text) == 1500
    assert (
        run("start-ids", "--statement", text, "--ref", "main", "--root", str(started)).returncode
        == 0
    )


def test_ac1_a_good_start_passes_check_start(started):
    """REQ-020 AC1: rule 5."""
    good_start(started)
    proc = check_start(started)
    assert (proc.returncode, proc.stdout) == (0, "ok playbook-start\n")


def failed(root, needle):
    proc = check_start(root)
    assert proc.returncode == 1, proc.stdout
    assert needle in proc.stdout, proc.stdout
    return proc.stdout


def test_ac1_a_third_file_or_a_missing_charter_fails(started):
    """REQ-020 AC1: rule 5 (the two files are the whole difference)."""
    good_start(started)
    (started / "docs" / "extra.md").write_text("x\n", encoding="utf-8")
    failed(started, "rule 4: the difference")
    (started / "docs" / "extra.md").unlink()
    (started / "docs" / "adr" / "0002-project-charter.md").unlink()
    failed(started, "rule 4: the difference")


def test_ac1_the_principles_file_must_be_untouched(started):
    """REQ-020 AC1: rule 5 (byte-identical to the base)."""
    good_start(started)
    (started / "constitution" / "principles.md").write_text(PRINCIPLES + "Two.\n", encoding="utf-8")
    failed(started, "principles")


@pytest.mark.parametrize(
    ("vision", "needle"),
    [
        (GOOD_VISION + "\nTODO(maintainers) later\n", "placeholder"),
        (GOOD_VISION.replace("## Who it serves", "## Audience"), "four headings"),
        (
            GOOD_VISION.replace("## Out of scope\n\nSyncing between devices.\n\n", ""),
            "four headings",
        ),
        (
            GOOD_VISION.replace("## Who it serves", "@@")
            .replace("## What this is for", "## Who it serves")
            .replace("@@", "## What this is for"),
            "out of order",
        ),
        (GOOD_VISION.replace(" <!-- project-specific -->", ""), "project marker"),
    ],
)
def test_ac1_vision_failures_name_the_rule(started, vision, needle):
    """REQ-020 AC1: rule 5 (placeholder; headings; order; the marker on every project rule)."""
    good_start(started, vision=vision)
    failed(started, needle if needle != "out of order" else "four headings")


def test_ac1_a_vision_without_project_rules_is_fine(started):
    """REQ-020 AC1: rule 5 (`## Project rules` is optional)."""
    good_start(started, vision=GOOD_VISION.split("## Project rules")[0].rstrip() + "\n")
    assert check_start(started).stdout == "ok playbook-start\n"


@pytest.mark.parametrize(
    ("change", "needle"),
    [
        (lambda t: t.replace("- Status: Proposed", "- Status: Accepted"), "not Proposed"),
        (lambda t: t.replace("`constitution/`", "`docs/`"), "constitution"),
        (
            lambda t: t.replace("2. **Non-goals**\n   - Syncing between devices.\n", ""),
            "numbered items",
        ),
        (lambda t: t.replace("3. **Done means**", "3. **Finished**"), "numbered items"),
        (lambda t: t.replace("exit: every saved item", "every saved item"), "`exit:`"),
        (
            lambda t: t.replace(
                "exit: 3 items can be saved and read back.", "exit: it works well."
            ),
            "measurable",
        ),
        (lambda t: t.replace("## Residual\n\nNone.\n", ""), "ADR format"),
    ],
)
def test_ac1_charter_failures_name_the_rule(started, change, needle):
    """REQ-020 AC1: rule 5 (status; class; the three items; exit with a measurable statement)."""
    good_start(started, charter=change(GOOD_CHARTER))
    failed(started, needle)


def test_ac1_the_charter_number_must_be_the_next_free_one(started):
    """REQ-020 AC1: rules 4 and 5 (read from the base, not guessed)."""
    good_start(started, charter=GOOD_CHARTER.replace("ADR-0002", "ADR-0005"))
    (started / "docs" / "adr" / "0002-project-charter.md").rename(
        started / "docs" / "adr" / "0005-project-charter.md"
    )
    failed(started, "next free ADR number")


def test_ac1_messages_name_the_rule_and_never_the_text(started):
    """REQ-020 AC1: rule 5."""
    good_start(
        started, vision=GOOD_VISION.replace("reading list", "SECRET-WORD") + "TODO(maintainers)\n"
    )
    assert "SECRET-WORD" not in failed(started, "placeholder")


def test_ac1_next_steps_print_the_commands_and_a_body_that_passes_check_pr_body(started):
    """REQ-020 AC1: rule 3 (the script prints; the skill does not commit)."""
    good_start(started)
    proc = run(
        "next-steps",
        "--base",
        "main",
        "--date",
        "2026-10-19",
        "--brief",
        "none",
        "--root",
        str(started),
    )
    assert proc.returncode == 0, proc.stdout
    assert "git push -u origin HEAD" in proc.stdout
    body = proc.stdout.split("Pull request body:\n\n", 1)[1]
    ok = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "check_pr_body.py"), "-"],
        input=body,
        capture_output=True,
        text=True,
    )
    assert ok.stdout == "ok pr-body\n"


def test_ac1_next_steps_refuse_on_the_default_branch_a_detached_head_or_a_failing_start(started):
    """REQ-020 AC1: rule 3 (no push of the default branch; nothing printed for a failing start)."""
    proc = run("next-steps", "--base", "main", "--root", str(started))
    assert (
        proc.returncode == 1 and "git push" not in proc.stdout
    )  # the vision is still the placeholder
    good_start(started)
    git(started, "add", "-A")
    git(started, "commit", "-q", "-m", "start")
    git(started, "switch", "-q", "main")
    assert run("next-steps", "--base", "main~1", "--root", str(started)).returncode == 1
    git(started, "switch", "-q", "--detach", "start/a-reading-list")
    detached = run("next-steps", "--base", "main", "--root", str(started))
    assert detached.returncode == 1 and "git push" not in detached.stdout


def test_ac1_the_start_skill_is_user_invoked_names_two_files_and_no_forbidden_verb():
    """REQ-020 AC1: rules 3 and 4 (SPEC-0005 rule 10)."""
    body = (KIT_ROOT / "skills" / "start" / "SKILL.md").read_text(encoding="utf-8")
    assert "disable-model-invocation: true" in body
    for verb in ("git push", "git commit", "gh pr", "gh issue", "gh api"):
        assert verb not in body, verb
    assert "Write exactly two files" in body and "constitution/principles.md" in body
    assert re.findall(r'playbook\.py" (\S+)', body) == ["start-ids", "check-start", "next-steps"]
    assert "existing codebase" in body and "/agk:adopt" in body


@pytest.mark.parametrize("how", ["init", "adopt"])
def test_ac1_start_works_in_a_new_repository_and_in_an_existing_codebase(tmp_path, how):
    """REQ-020 AC1: rules 1, 2 and 5 (the installed template is replaced; governance passes)."""
    root = make_repo(tmp_path / "proj")
    if how == "init":
        proc = subprocess.run(
            [
                sys.executable,
                str(KIT_ROOT / "scripts" / "agk" / "init.py"),
                str(root),
                "--unreleased",
            ],
            capture_output=True,
            text=True,
            env=clean_env(),
        )
    else:
        (root / "app.py").write_text("print('app')\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "app")
        proc = subprocess.run(
            [
                sys.executable,
                str(KIT_ROOT / "scripts" / "agk" / "adopt.py"),
                str(root),
                "--unreleased",
            ],
            capture_output=True,
            text=True,
            env=clean_env(),
        )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    set_handle(root)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "install the kit")
    ids = json.loads(
        run(
            "start-ids", "--statement", "A reading list.", "--ref", "main", "--root", str(root)
        ).stdout
    )
    git(root, "switch", "-q", "-c", ids["branch"])
    (root / "constitution" / "vision.md").write_text(GOOD_VISION, encoding="utf-8")
    charter = GOOD_CHARTER.replace("ADR-0002", f"ADR-{ids['adr']}")
    (root / "docs" / "adr" / f"{ids['adr']}-project-charter.md").write_text(
        charter, encoding="utf-8"
    )
    assert check_start(root).stdout == "ok playbook-start\n"
    gov = subprocess.run(
        ["make", "-f", "agk.mk", "agk-governance"],
        cwd=root,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert gov.returncode == 0, gov.stdout + gov.stderr
