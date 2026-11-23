"""brief_study.py prints the earlier record a brief's writer must read (brief #1800, ADR-0752; REQ-037)."""

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
        [sys.executable, str(SCRIPTS / "brief_study.py"), str(tmp_path / "brief.md"),
         "--root", str(root)],
        cwd=tmp_path, capture_output=True, text=True,
    )


def tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for folder in ("scripts/agk", "docs/adr", "docs/specs", "docs/runs"):
        (root / folder).mkdir(parents=True)
    (root / "scripts" / "agk" / "tool.py").write_text("def main():\n    return 0\n", "utf-8")
    return root


def record(root: Path) -> None:
    (root / "docs" / "adr" / "0007-tool.md").write_text(
        "# ADR-0007: tool\n\n- Status: Proposed\n\nThe whole-tests rule for `scripts/agk/tool.py`.\n",
        "utf-8",
    )
    (root / "docs" / "adr" / "0008-other.md").write_text(
        "# ADR-0008: other\n\n- Status: Accepted\n\nOnly `agk.toml` and `scripts/agk/other.py`.\n",
        "utf-8",
    )
    (root / "docs" / "specs" / "0005-tools.md").write_text(
        "# SPEC-0005: tools\n\n- Status: Approved\n\nRule 1: see https://example.com. Amendment 3.\n",
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
        [sys.executable, str(SCRIPTS / "brief_study.py"), str(tmp_path / "brief.md"),
         "--root", str(root), "--open-briefs", str(saved)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    lines = out.stdout.splitlines()
    assert any(x.startswith("brief #41 (open)") for x in lines), out.stdout + out.stderr
    assert not any(x.startswith(("brief #42", "brief #43")) for x in lines)


def test_ac4_a_usage_error_exits_2(tmp_path):
    """REQ-037 AC4"""
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "brief_study.py")], cwd=tmp_path, capture_output=True,
        text=True,
    )
    assert out.returncode == 2 and out.stdout.startswith("usage:")
