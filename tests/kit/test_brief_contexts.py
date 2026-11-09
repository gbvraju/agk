"""The `Contexts:` line of a brief and the `Contexts` section of a spec (amendment 142; REQ-037).

Every brief and every new or re-statused spec says how it works in each context: kit, github,
local, personal and stacks. `check_brief.py` refuses a brief without the line or with a context
missing and `check_specs.py` the same for a spec's section, naming the rule. Invented data only;
no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
import session

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
LINE = (
    "Contexts: kit (the check runs here); github, local and personal (the same check runs in each "
    "mode; read from files); stacks (not applicable: no test step changes).\n"
)
BODY = 'Sentence: "A thing."\nAnswers:\n1. one\nSize: M\nAdvances: new\nTouches: src/a.py\n'
SPEC = "docs/specs/0001-thing.md"
SECTION = (
    "\n## Contexts\n\n- kit: the check runs here\n- github, local and personal: the same check\n"
    "- stacks: not applicable: no test step changes\n"
)


def spec(status: str = "Draft", extra: str = "") -> str:
    return (
        f"# SPEC-0001: Thing\n\n- Status: {status}\n- Owner: maintainers\n"
        f"- Requirements: REQ-001\n\n## Rules\n\n1. A rule.\n{extra}"
    )


def check(tmp_path: Path, body: str):
    (tmp_path / "brief.md").write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), str(tmp_path / "brief.md")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def base(repo):
    repo.commit({"src/a.py": "1\n", SPEC: spec()}, "base")
    repo.branch()
    return repo


def specs(repo):
    return repo.run("check_specs.py", "--base", "main")


def test_ac4_a_brief_with_every_context_passes(tmp_path):
    """REQ-037 AC4: grouped names and a `not applicable: <reason>` are one good line."""
    out = check(tmp_path, BODY + LINE)
    assert out.returncode == 0 and out.stdout.strip() == "ok brief"


def test_ac4_the_line_of_a_real_shape_with_semicolons_in_the_brackets_passes():
    """REQ-037 AC4: a semicolon inside an entry's brackets does not end the entry."""
    line = "Contexts: kit (a; b); github (c); local (d); personal (e); stacks (f)."
    assert session.contexts_problems(line[len("Contexts:") :]) == []


def test_ac4_a_brief_without_the_line_fails_naming_the_rule(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, BODY)
    assert out.returncode == 1
    assert "rule 4" in out.stdout and "Contexts" in out.stdout


def test_ac4_two_lines_fail(tmp_path):
    """REQ-037 AC4"""
    out = check(tmp_path, BODY + LINE + LINE)
    assert out.returncode == 1 and "rule 4" in out.stdout


@pytest.mark.parametrize("missing", ["kit", "github", "local", "personal", "stacks"])
def test_ac4_a_context_missing_fails_naming_the_rule_and_the_context(tmp_path, missing):
    """REQ-037 AC4: every context is stated, and the refusal names which."""
    entries = [f"{c} (works)" for c in session.CONTEXTS if c != missing]
    out = check(tmp_path, BODY + "Contexts: " + "; ".join(entries) + "\n")
    assert out.returncode == 1
    assert "rule 4" in out.stdout and missing in out.stdout


def test_ac4_a_context_named_only_in_prose_does_not_count(tmp_path):
    """REQ-037 AC4: `local` inside another entry's text is not an entry for `local`."""
    line = "Contexts: kit (not local); github (x); personal (y); stacks (z)\n"
    out = check(tmp_path, BODY + line)
    assert out.returncode == 1 and "local" in out.stdout


@pytest.mark.parametrize(
    "line",
    [
        "Contexts: kit; github (x); local (x); personal (x); stacks (x)\n",
        "Contexts: kit (); github (x); local (x); personal (x); stacks (x)\n",
        "Contexts: kit (not applicable:); github (x); local (x); personal (x); stacks (x)\n",
        "Contexts: kit (not applicable); github (x); local (x); personal (x); stacks (x)\n",
    ],
)
def test_ac4_an_entry_that_says_nothing_fails(tmp_path, line):
    """REQ-037 AC4: each context says how, or `not applicable: <reason>`."""
    out = check(tmp_path, BODY + line)
    assert out.returncode == 1 and "rule 4" in out.stdout


def test_ac4_an_unknown_context_and_a_repeated_one_fail(tmp_path):
    """REQ-037 AC4"""
    good = "kit (x); github (x); local (x); personal (x); stacks (x)"
    assert check(tmp_path, f"{BODY}Contexts: {good}; mobile (x)\n").returncode == 1
    assert check(tmp_path, f"{BODY}Contexts: {good}; kit (y)\n").returncode == 1


def test_ac4_the_refusal_never_repeats_the_text_of_the_line(tmp_path):
    """REQ-037 AC4: principle 8."""
    out = check(tmp_path, BODY + "Contexts: kit (invented-words-here)\n")
    assert out.returncode == 1 and "invented-words-here" not in out.stdout


def test_ac4_a_new_spec_without_the_section_fails(base):
    """REQ-037 AC4"""
    base.commit({"docs/specs/0002-new.md": spec().replace("0001", "0002")})
    out = specs(base)
    assert out.returncode == 1
    assert "Contexts" in out.stdout and "0002-new" in out.stdout


def test_ac4_a_new_spec_with_every_context_passes(base):
    """REQ-037 AC4"""
    base.commit({"docs/specs/0002-new.md": spec(extra=SECTION).replace("0001", "0002")})
    assert specs(base).returncode == 0


def test_ac4_a_new_spec_with_a_context_missing_fails_naming_it(base):
    """REQ-037 AC4"""
    text = spec(extra=SECTION.replace("- stacks: not applicable: no test step changes\n", ""))
    base.commit({"docs/specs/0002-new.md": text.replace("0001", "0002")})
    out = specs(base)
    assert out.returncode == 1 and "stacks" in out.stdout


def test_ac4_a_spec_whose_status_changes_needs_the_section(base):
    """REQ-037 AC4"""
    base.commit({SPEC: spec("Approved")})
    out = specs(base)
    assert out.returncode == 1 and "Contexts" in out.stdout


def test_ac4_a_draft_edited_without_a_status_change_is_not_refused(base):
    """REQ-037 AC4: only new specs, status changes and amended Approved specs."""
    base.commit({SPEC: spec("Draft", "2. Another rule.\n")})
    assert specs(base).returncode == 0


def test_ac4_an_approved_spec_is_not_refused_until_it_is_next_amended(repo):
    """REQ-037 AC4: untouched, it passes; amended, it needs the section."""
    repo.commit({"src/a.py": "1\n", SPEC: spec("Approved")}, "base")
    repo.branch()
    repo.commit({"src/b.py": "2\n"})
    assert specs(repo).returncode == 0
    repo.commit(
        {
            SPEC: spec("Approved", "2. Another rule.\n"),
            "docs/runs/proposed-spec-amendments-1.md": f"# Amendment\n\n{SPEC}\n",
        }
    )
    out = specs(repo)
    assert out.returncode == 1 and "Contexts" in out.stdout


def test_ac4_the_routers_red_branch_brief_needs_no_line(tmp_path):
    """REQ-037 AC4: SPEC-0032 rule 7's brief is a fixed repair, not a design."""
    body = (
        'Sentence: "The default branch is red."\nAnswers:\n1. the failing check\nSize: S\n'
        "Advances: none\nPriority: 0\nTouches: x\n"
    )
    assert session.contexts_line_problems(body) == []


def test_ac4_the_spec_template_lists_every_context_and_is_refused_unfilled():
    """REQ-037 AC4: the template names the five contexts, and left empty it does not pass."""
    root = Path(__file__).resolve().parents[2]
    text = (root / "docs/specs/TEMPLATE.md").read_text(encoding="utf-8")
    lines = [
        x.strip().removeprefix("- ")
        for x in text.split("## Contexts")[1].split("##")[0].split("\n")
    ]
    entries = [x for x in lines if x]
    assert entries == [f"{c}:" for c in session.CONTEXTS]
    assert session.contexts_problems("; ".join(entries)) != []
