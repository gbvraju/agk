"""The rule budget (brief #647 answer 1, ADR-0310; REQ-037 AC1).

`config/rule-budget.txt` records, for each instruction file an agent reads, its word count and
its count of numbered or bulleted rule lines. A file whose count rises above its line fails ("a
rule was added"), a line above its file fails ("lower the baseline"), and a listed file that is
gone or an agent file that is not listed fails. `rules.py budget` prints the counts. No network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "rules.py"

CORE = (
    "CLAUDE.md",
    "constitution/principles.md",
    "config/core-rules.md",
    "config/session-rules.md",
    "config/review-checklist.md",
)
AGENT = "---\nname: x\nhooks:\n  - matcher: y\n---\n\nRead first.\n\n1. One rule.\n- A bullet.\n"


def layout(tmp_path: Path, agent: str = AGENT) -> Path:
    for rel in CORE:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# T\n\n1. Do one thing.\n2. Do another.\n", encoding="utf-8")
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "a.md").write_text(agent, encoding="utf-8")
    return tmp_path


def baseline(root: Path) -> None:
    from rules import budget_lines

    (root / "config" / "rule-budget.txt").write_text(
        "# words and rule lines\n" + "".join(f"{ln}\n" for ln in budget_lines(root)),
        encoding="utf-8",
    )


def test_req037_counts_words_and_rule_lines_outside_front_matter_and_fences():
    """REQ-037 AC1: a rule line is numbered or bulleted; front matter and fences hold none."""
    from rules import counts

    text = (
        "---\nhooks:\n  - matcher: x\n---\n\n1. One.\n   - Two.\n* Three\n```\n- no\n```\nplain\n"
    )
    words, rules = counts(text)
    assert words == len(text.split())
    assert rules == 3


def test_req037_the_files_are_the_core_files_every_agent_file_and_the_checklist(tmp_path):
    """REQ-037 AC1: the list that `launch.py prompts` and SPEC-0045 rule 7 name, and the agents."""
    from rules import instruction_files

    root = layout(tmp_path)
    (root / ".claude" / "agents" / "b.md").write_text("x\n", encoding="utf-8")
    assert instruction_files(root) == [
        *CORE[:4],
        ".claude/agents/a.md",
        ".claude/agents/b.md",
        CORE[4],
    ]


def test_req037_a_matching_baseline_passes(tmp_path):
    """REQ-037 AC1"""
    from rules import budget_problems

    root = layout(tmp_path)
    baseline(root)
    assert budget_problems(root) == []


def test_req037_a_rule_added_fails_naming_the_way_out(tmp_path):
    """REQ-037 AC1: a count above its baseline line fails, naming retire-or-check."""
    from rules import budget_problems

    root = layout(tmp_path)
    baseline(root)
    with (root / "config" / "session-rules.md").open("a", encoding="utf-8") as f:
        f.write("3. A new rule.\n")
    problems = budget_problems(root)
    assert len(problems) == 1
    assert problems[0].startswith("config/session-rules.md: ")
    assert (
        "a rule was added: retire one, or make it a check, in the same pull request" in problems[0]
    )


def test_req037_words_added_fail_too(tmp_path):
    """REQ-037 AC1: the word count is a budget as well."""
    from rules import budget_problems

    root = layout(tmp_path)
    baseline(root)
    with (root / "CLAUDE.md").open("a", encoding="utf-8") as f:
        f.write("More words here.\n")
    problems = budget_problems(root)
    assert len(problems) == 1 and problems[0].startswith("CLAUDE.md: ")
    assert "words" in problems[0]


def test_req037_a_baseline_above_its_file_fails_lower_the_baseline(tmp_path):
    """REQ-037 AC1: a cut file lowers its baseline in the same pull request."""
    from rules import budget_problems

    root = layout(tmp_path)
    baseline(root)
    (root / ".claude" / "agents" / "a.md").write_text(
        "---\nname: x\n---\n\nRead.\n", encoding="utf-8"
    )
    problems = budget_problems(root)
    assert problems and all("lower the baseline" in p for p in problems)
    assert all(p.startswith(".claude/agents/a.md: ") for p in problems)


def test_req037_an_unlisted_agent_file_and_a_gone_file_fail(tmp_path):
    """REQ-037 AC1: a new agent file cannot escape the budget, and a stale line is removed."""
    from rules import budget_problems

    root = layout(tmp_path)
    baseline(root)
    (root / ".claude" / "agents" / "new.md").write_text("1. x\n", encoding="utf-8")
    (root / "config" / "review-checklist.md").unlink()
    problems = budget_problems(root)
    assert any(
        p.startswith(".claude/agents/new.md: ") and "not in the baseline" in p for p in problems
    )
    assert any(
        p.startswith("config/review-checklist.md: ") and "remove its line" in p for p in problems
    )


def test_req037_a_missing_or_malformed_baseline_fails_naming_the_file(tmp_path):
    """REQ-037 AC1: no baseline is a failure, never a pass."""
    from rules import budget_problems

    root = layout(tmp_path)
    assert budget_problems(root) == ["config/rule-budget.txt: cannot be read"]
    (root / "config" / "rule-budget.txt").write_text("CLAUDE.md many 2\n", encoding="utf-8")
    assert any("config/rule-budget.txt: line 1" in p for p in budget_problems(root))


def test_req037_this_repository_meets_its_budget():
    """REQ-037 AC1: the committed baseline equals the files on this head."""
    from rules import budget_problems

    assert budget_problems(ROOT) == []


def test_req037_budget_command_prints_counts_and_checks(tmp_path):
    """REQ-037 AC1: `budget` prints `<path> <words> <rules>`; `--check` exits 1 on a problem."""
    root = layout(tmp_path)
    run = [sys.executable, str(SCRIPT), "budget", "--root", str(root)]
    shown = subprocess.run(run, capture_output=True, text=True, check=False)  # nosec B603
    assert shown.returncode == 0
    assert shown.stdout.splitlines()[0] == "CLAUDE.md 9 2"
    checked = subprocess.run([*run, "--check"], capture_output=True, text=True, check=False)  # nosec B603
    assert checked.returncode == 1 and "config/rule-budget.txt: cannot be read" in checked.stdout
    baseline(root)
    checked = subprocess.run([*run, "--check"], capture_output=True, text=True, check=False)  # nosec B603
    assert checked.returncode == 0 and checked.stdout.strip() == "ok rule-budget"
