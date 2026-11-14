"""An upgrade arrives as one ready pull request with a full ADR (brief #1222, ADR-0521, REQ-014).

Answer 1: `upgrade.py TARGET --write-adr` writes `docs/adr/<next>-upgrade-agk-to-<version>.md` with
every field and section `check_adrs.py` requires, naming each protected class the upgrade changed,
Status Proposed, titled so that `--next-steps` finds it. Answer 2: the upgrade skill branches
`upgrade/agk-<version>` from the default branch before writing, writes the ADR by default, runs the
local gate, prints the checked body and says the upgrade is held for the owner's merge. Answer 3:
the written ADR passes `check_adrs.py`; an upgrade with no change writes no ADR.
"""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import check_adrs
import pytest
import upgrade

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "upgrade" / "SKILL.md"
OLD = b"old makefile\n"
NEW = b"new makefile\n"
DATE = "2026-11-14"
ADR_NAME = "0008-upgrade-agk-to-2-0-0.md"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    """A kit at 2.0.0 that ships a new Makefile; its table knows the 1.0.0 copy."""
    root = tmp_path / "kit_root"
    (root / "kit").mkdir(parents=True)
    (root / "Makefile").write_bytes(NEW)
    manifest = {
        "kit_version": "2.0.0",
        "verbatim": ["Makefile"],
        "templates": {},
        "rendered": [],
        "adopt": {"skip": ["Makefile"], "blocks": {}, "templates": {}},
    }
    (root / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    row = {"commits": [], "verbatim": {}, "blocks": {}, "templates": {}}
    table = {
        "table": 1,
        "releases": {
            "1.0.0": {**row, "verbatim": {"Makefile": [digest(OLD)]}},
            "2.0.0": {**row, "verbatim": {"Makefile": [digest(NEW)]}},
        },
    }
    (root / "kit" / "hashes.json").write_text(json.dumps(table), encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n", encoding="utf-8")
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def target(tmp_path: Path, version: str = "1.0.0", makefile: bytes = OLD) -> Path:
    root = tmp_path / "target"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    (root / "agk.toml").write_text(f'mode = "init"\nversion = "{version}"\n', encoding="utf-8")
    (root / "Makefile").write_bytes(makefile)
    (root / "config").mkdir()
    (root / "config" / "protected-paths.txt").write_text("Makefile\nagk.toml\n", encoding="utf-8")
    adr = root / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "0001-adopt-agk.md").write_text("# ADR-0001: demo adopts agk\n", encoding="utf-8")
    (adr / "0007-an-older-decision.md").write_text("# ADR-0007: older\n", encoding="utf-8")
    (adr / "TEMPLATE.md").write_text("# ADR-NNNN: Title\n", encoding="utf-8")
    return root


def run(capsys, root: Path, *args: str) -> tuple[int, str]:
    code = upgrade.main([str(root), *args])
    return code, capsys.readouterr().out


def adrs(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "docs" / "adr").glob("*.md"))


# --- answers 1 and 3: the written ADR ------------------------------------------------------------


def test_write_adr_writes_the_next_numbered_adr_that_check_adrs_accepts(tmp_path, kit, capsys):
    root = target(tmp_path)
    code, out = run(capsys, root, "--write-adr", "--date", DATE)
    assert code == 0, out
    assert (root / "Makefile").read_bytes() == NEW
    assert f"adr: wrote docs/adr/{ADR_NAME} (ADR-0008, Proposed)" in out.splitlines()
    path = root / "docs" / "adr" / ADR_NAME
    text = path.read_text(encoding="utf-8")
    assert check_adrs.validate(path.name, text, {"0001", "0007"}) == []
    lines = text.splitlines()
    assert lines[0] == "# ADR-0008: Upgrade agk from 1.0.0 to 2.0.0"
    assert "- Status: Proposed" in lines and f"- Date: {DATE}" in lines
    assert "- Requirements: REQ-001" in lines


def test_the_written_adr_names_each_protected_class_the_upgrade_changed(tmp_path, kit, capsys):
    root = target(tmp_path)
    assert run(capsys, root, "--write-adr", "--date", DATE)[0] == 0
    text = (root / "docs" / "adr" / ADR_NAME).read_text(encoding="utf-8")
    assert "Protected classes: `Makefile`, `agk.toml`" in text.splitlines()


def test_next_steps_finds_the_written_adr(tmp_path, kit, capsys):
    root = target(tmp_path)
    assert run(capsys, root, "--write-adr", "--date", DATE)[0] == 0
    assert upgrade.upgrade_adr(root, "2.0.0") == ("ADR-0008", "1.0.0", "REQ-001")


def test_an_upgrade_with_no_change_writes_no_adr(tmp_path, kit, capsys):
    root = target(tmp_path, version="2.0.0", makefile=NEW)
    before = adrs(root)
    code, out = run(capsys, root, "--write-adr", "--date", DATE)
    assert (code, out.splitlines()[-1]) == (0, "nothing to do")
    assert "adr:" not in out
    assert adrs(root) == before


def test_without_write_adr_no_adr_is_written(tmp_path, kit, capsys):
    root = target(tmp_path)
    before = adrs(root)
    code, out = run(capsys, root)
    assert code == 0, out
    assert adrs(root) == before
    assert "--write-adr" in out


def test_a_dry_run_with_write_adr_names_the_file_and_writes_nothing(tmp_path, kit, capsys):
    root = target(tmp_path)
    before = adrs(root)
    code, out = run(capsys, root, "--dry-run", "--write-adr", "--date", DATE)
    assert code == 0, out
    assert f"adr: would write docs/adr/{ADR_NAME} (ADR-0008, Proposed)" in out.splitlines()
    assert adrs(root) == before and (root / "Makefile").read_bytes() == OLD


def test_a_bad_date_is_refused_before_anything_is_written(tmp_path, kit, capsys):
    root = target(tmp_path)
    before = adrs(root)
    code, out = run(capsys, root, "--write-adr", "--date", "14 Nov")
    assert code == 1
    assert out.splitlines()[-1] == "refused: the date is not YYYY-MM-DD (option --date)"
    assert (root / "Makefile").read_bytes() == OLD and adrs(root) == before


def test_an_upgrade_adr_already_written_for_the_version_is_kept(tmp_path, kit, capsys):
    root = target(tmp_path)
    mine = root / "docs" / "adr" / "0007-an-older-decision.md"
    mine.write_text("# ADR-0007: Upgrade agk from 1.0.0 to 2.0.0\n", encoding="utf-8")
    before = adrs(root)
    code, out = run(capsys, root, "--write-adr", "--date", DATE)
    assert code == 0, out
    assert "adr: kept docs/adr/0007-an-older-decision.md (ADR-0007)" in out.splitlines()
    assert adrs(root) == before


@pytest.mark.parametrize(
    "args", [["--date", DATE], ["--write-adr", "--date"], ["--write-adr", "--brief", "1"]]
)
def test_write_adr_options_outside_their_form_are_a_usage_error(tmp_path, kit, capsys, args):
    root = target(tmp_path)
    assert upgrade.main([str(root), *args]) == 2
    assert (root / "Makefile").read_bytes() == OLD


# --- answer 2: the skill -------------------------------------------------------------------------


def test_the_skill_branches_first_writes_the_adr_gates_and_holds_for_the_owner():
    text = SKILL.read_text(encoding="utf-8")
    branch = text.index("git switch -c upgrade/agk-<version> origin/<default branch>")
    write = text.index('upgrade.py" . --write-adr')
    assert branch < write
    assert write < text.index("make governance") < text.index('upgrade.py" . --next-steps')
    assert "check_pr_body.py" in text
    assert "held for the owner's merge" in text and "merge_cleared.py" in text
    assert "Write no ADR" not in text
