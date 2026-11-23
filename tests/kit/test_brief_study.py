"""brief_study.py prints the earlier record a brief's writer reads (brief #1800; REQ-037)."""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
BRIEF = (
    'Sentence: "A team can run a thing."\nAnswers:\n1. one\nSize: S\nAdvances: new\n'
    "Touches: scripts/agk/tool.py, agk.toml, docs/x.md\nPriority: 1\n"
    "Wiring: scripts/agk/tool.py:main called by skills/brief/SKILL.md\n"
)


def study(tmp_path: Path, root: Path, body: str = BRIEF):
    (tmp_path / "brief.md").write_text(body, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "brief_study.py"),
            str(tmp_path / "brief.md"),
            "--root",
            str(root),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for folder in ("scripts/agk", "docs/adr", "docs/specs", "docs/runs"):
        (root / folder).mkdir(parents=True)
    (root / "scripts" / "agk" / "tool.py").write_text("def main():\n    return 0\n", "utf-8")
    return root


def record(root: Path) -> None:
    (root / "docs" / "adr" / "0007-tool.md").write_text(
        "# ADR-0007: tool\n\n- Status: Proposed\n\nThe rule for `scripts/agk/tool.py`.\n",
        "utf-8",
    )
    (root / "docs" / "adr" / "0008-other.md").write_text(
        "# ADR-0008: other\n\n- Status: Accepted\n\nOnly `agk.toml` and `scripts/agk/other.py`.\n",
        "utf-8",
    )
    (root / "docs" / "specs" / "0005-tools.md").write_text(
        "# SPEC-0005: tools\n\n- Status: Approved\n\nSee https://example.com. Amendment 3.\n",
        "utf-8",
    )
    runs = root / "docs" / "runs"
    (runs / "proposed-spec-amendments-4.md").write_text(
        "# Proposed spec amendments 4 (SPEC-0005; REQ-001)\n\n`tool.main` changes.\n", "utf-8"
    )
    (runs / "proposed-spec-amendments-3.md").write_text(
        "# Proposed spec amendments 3 (SPEC-0005; REQ-001)\n\n`scripts/agk/tool.py` too.\n", "utf-8"
    )


def test_ac4_the_study_prints_the_adr_the_unapplied_amendment_and_no_shared_file_match(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    record(root)
    out = study(tmp_path, root)
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.splitlines()
    assert any(x.startswith("ADR-0007 (Proposed)") for x in lines)
    assert any(x.startswith("amendment 4 (SPEC-0005, not in the spec)") for x in lines)
    assert not any("amendment 3 " in x for x in lines)  # already named in its spec
    assert not any(x.startswith("ADR-0008") for x in lines)  # agk.toml is shared by every change
    assert any(x.startswith("briefs: not read") for x in lines)


def test_ac4_the_study_prints_nothing_for_a_tree_with_no_record(tmp_path):
    """REQ-037 AC4"""
    out = study(tmp_path, tree(tmp_path))
    assert out.returncode == 0
    assert [x for x in out.stdout.splitlines() if not x.startswith("briefs: ")] == []


def test_ac4_the_study_prints_an_overlapping_open_brief_from_a_saved_list(tmp_path):
    """REQ-037 AC4"""
    root = tree(tmp_path)
    saved = tmp_path / "open.json"
    saved.write_text(
        '[{"number": 41, "body": "Touches: scripts/agk/tool.py"},'
        ' {"number": 42, "body": "Touches: docs/other.md"},'
        ' {"number": 43, "body": "Touches: **"}]',
        encoding="utf-8",
    )
    (tmp_path / "brief.md").write_text(BRIEF, encoding="utf-8")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "brief_study.py"),
            str(tmp_path / "brief.md"),
            "--root",
            str(root),
            "--open-briefs",
            str(saved),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    lines = out.stdout.splitlines()
    assert any(x.startswith("brief #41 (open)") for x in lines), out.stdout + out.stderr
    assert not any(x.startswith(("brief #42", "brief #43")) for x in lines)


def test_ac4_a_usage_error_exits_2(tmp_path):
    """REQ-037 AC4"""
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "brief_study.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 2 and out.stdout.startswith("usage:")


def adr(root: Path, number: int, header: str = "", context: str = "", decision: str = "") -> None:
    text = f"# ADR-{number:04d}: x\n\n- Status: Accepted\n{header}\n## Context\n\n{context}\n"
    text += f"\n## Decision\n\n{decision}\n\n## Consequences\n\nNone.\n"
    (root / "docs" / "adr" / f"{number:04d}-x.md").write_text(text, "utf-8")


def marks(out) -> dict[str, str]:
    return {
        x.split(" ", 1)[0]: x.rsplit("; ", 1)[-1]
        for x in out.stdout.splitlines()
        if x.startswith("ADR-")
    }


def test_ac4_a_hit_is_strong_in_the_header_or_decision_and_weak_elsewhere_or_by_name(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 1)"""
    root = tree(tmp_path)
    adr(root, 20, header="- Related: `scripts/agk/tool.py`\n")
    adr(root, 21, decision="1. `scripts/agk/tool.py` decides it.")
    adr(root, 22, decision="1. `tool.main` decides it.")
    adr(root, 23, context="It once named `scripts/agk/tool.py`.")
    adr(root, 24, decision="1. Only `tool.py` by its name.")
    adr(root, 25, context="x", decision="y\n\n## Residual\n\n`scripts/agk/tool.py` later.")
    got = marks(study(tmp_path, root))
    assert got == {
        "ADR-0020": "strong",
        "ADR-0021": "strong",
        "ADR-0022": "strong",
        "ADR-0023": "weak",
        "ADR-0024": "weak",
        "ADR-0025": "weak",
    }, got


def test_ac4_an_adr_without_a_decision_heading_is_searched_whole_as_strong(tmp_path):
    """REQ-037 AC4 (brief #1819 answer 7)"""
    root = tree(tmp_path)
    (root / "docs" / "adr" / "0030-old.md").write_text(
        "# ADR-0030: old\n\n- Status: Accepted\n\n## Background\n\n`scripts/agk/tool.py`.\n",
        "utf-8",
    )
    assert marks(study(tmp_path, root)) == {"ADR-0030": "strong"}


def test_ac4_strong_hits_come_first_ranked_by_terms_then_the_newer_number(tmp_path):
    """REQ-037 AC4 (brief #1819 answers 2 and 3)"""
    root = tree(tmp_path)
    adr(root, 40, context="`scripts/agk/tool.py` in passing.")
    adr(root, 41, decision="`scripts/agk/tool.py`")
    adr(root, 42, decision="`scripts/agk/tool.py` and `tool.main`")
    adr(root, 43, decision="`scripts/agk/tool.py`")
    out = study(tmp_path, root)
    order = [x.split(" ", 1)[0] for x in out.stdout.splitlines() if x.startswith("ADR-")]
    assert order == ["ADR-0042", "ADR-0043", "ADR-0041", "ADR-0040"], out.stdout
