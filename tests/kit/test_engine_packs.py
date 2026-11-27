"""Tests of engines and playbook skills from a pinned pack (SPEC-0077 rules 12 and 14 build (e);
SPEC-0029 rules 1 and 2 by amendment 261; REQ-084 AC5; brief #2035, ADR-0842).

An `[engines]` value `<pack id>:<skill>` of a pack that `[packs] use` lists and `config/packs.lock`
holds reads `present` only from the pack's locked folder when `packs.verify` passes for it, and
`missing` (reason class `packs`) when the skill is not in the lock or the pack fails; a prefix that
names no pack in use stays `cannot-check plugin-unreadable`. A playbook's unprefixed skill counts
as present from such a pack too. Fixtures in `tmp_path` only: invented data (`example.com`), no
network, no model.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_packs  # noqa: E402
import doctor  # noqa: E402
import packs  # noqa: E402
import playbook_format  # noqa: E402

PID = "zz-shop"
SKILL = "# An invented skill\n\nDraft the shop's terms (https://example.com/terms).\n"
MANIFEST = """format = 1
id = "{pid}"
version = "1.2.0"
publisher = "Example Org"
tier = "curated"
licence = "MIT"
source = "https://example.com/packs/{pid}.git"
kit = ">=0.65"
as_of = "2026-11-20"
reviewed = "2026-11-21 by maintainers"
kinds = ["skills"]

[permissions]

[files]
"skills/shop/SKILL.md" = "{sha}"
"""
AMENDMENT = KIT_ROOT / "docs" / "runs" / "proposed-spec-amendments-261.md"
SPEC_0029 = (
    KIT_ROOT / "docs" / "specs" / "0029-a-product-owner-starts-from-a-brief-idea-the-vision-the-stac.md"
)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """HOME is a directory of the test, so the user's own skills never reach a result."""
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


def project(tmp_path: Path, pid: str = PID, use: bool = True, lock: bool = True) -> Path:
    """A project with one stub pack (one skill `shop`) in `config/packs/<pid>/`, in `[packs] use`
    and in the lock, as `packs.py add` leaves it; USE or LOCK False leaves that part out."""
    root = tmp_path / "project"
    folder = root / check_packs.FOLDER / pid
    (folder / "skills" / "shop").mkdir(parents=True)
    (folder / "skills" / "shop" / "SKILL.md").write_text(SKILL, encoding="utf-8")
    sha = hashlib.sha256(SKILL.encode()).hexdigest()
    (folder / check_packs.MANIFEST).write_text(MANIFEST.format(pid=pid, sha=sha), encoding="utf-8")
    if lock:
        (root / packs.LOCK).write_text(packs.lock_text([packs.lock_entry(folder)]))
    digest = check_packs.digest(folder / check_packs.MANIFEST)
    entry = f'{{ id = "{pid}", version = "1.2.0", sha256 = "{digest}" }}'
    table = f"[packs]\nuse = [{entry}]\n" if use else ""
    (root / "agk.toml").write_text(f'review_mode = "solo"\n{table}', encoding="utf-8")
    return root


def kit(tmp_path: Path, *skills: str) -> Path:
    base = tmp_path / "kit"
    (base / "skills").mkdir(parents=True)
    for name in skills:
        (base / "skills" / name).mkdir()
        (base / "skills" / name / "SKILL.md").write_text("# an invented skill\n", encoding="utf-8")
    return base


def engine(root: Path, kit_root: Path | None, value, key: str = "vision") -> doctor.Result:
    return doctor.engine_results(root, kit_root, {"engines": {key: value}})[f"engine-{key}"]


def is_missing_packs(result: doctor.Result) -> bool:
    return result.status == "fail" and result.message == " (missing: packs)"


def test_ac5_a_skill_of_a_locked_pack_in_use_is_present(tmp_path):
    """REQ-084 AC5: rule 12 and amendment 261 item 2 (present from the verified locked folder)."""
    root = project(tmp_path)
    found = engine(root, kit(tmp_path), f"{PID}:shop")
    assert (found.status, found.message) == ("ok", " (present)")


def test_ac5_a_skill_the_lock_does_not_hold_is_missing_naming_packs(tmp_path):
    """REQ-084 AC5: amendment 261 item 2 (in use, the skill not in the lock: missing, `packs`)."""
    root = project(tmp_path)
    found = engine(root, kit(tmp_path, "other"), f"{PID}:other")
    assert is_missing_packs(found)
    assert PID not in found.message and "other" not in found.message  # principle 8


def test_ac5_a_prefix_naming_no_pack_in_use_stays_plugin_unreadable(tmp_path):
    """REQ-084 AC5: amendment 261 item 2 (not in use: cannot-check plugin-unreadable)."""
    root = project(tmp_path, use=False)
    found = engine(root, kit(tmp_path), f"{PID}:shop")
    assert (found.status, found.reason) == ("cannot-check", "plugin-unreadable")


def test_ac5_a_pack_in_use_that_the_lock_does_not_hold_is_missing(tmp_path):
    """REQ-084 AC5: answer 1 (in use, its verify fails: missing, never present)."""
    root = project(tmp_path, lock=False)
    assert is_missing_packs(engine(root, kit(tmp_path), f"{PID}:shop"))


@pytest.mark.parametrize("how", ["changed", "unlocked-copy", "folder-gone"])
def test_ac5_a_pack_failing_verify_reads_missing(tmp_path, how):
    """REQ-084 AC5: Q-PE-1 (a failing verify is missing, reason `packs`, so a changed or
    unlocked skill is never used silently; the class stays closed, answer 7)."""
    root = project(tmp_path)
    folder = root / check_packs.FOLDER / PID / "skills"
    if how == "changed":
        (folder / "shop" / "SKILL.md").write_text(SKILL + "A changed line.\n", encoding="utf-8")
        name = "shop"
    elif how == "unlocked-copy":
        (folder / "extra").mkdir()
        (folder / "extra" / "SKILL.md").write_text("# an unlocked copy\n", encoding="utf-8")
        name = "extra"
    else:
        (folder / "shop" / "SKILL.md").unlink()
        name = "shop"
    assert packs.verify(root, None)  # the stand-in really fails verify
    assert is_missing_packs(engine(root, kit(tmp_path), f"{PID}:{name}"))


def test_ac5_a_pack_its_own_check_refuses_reads_missing(tmp_path, monkeypatch):
    """REQ-084 AC5: answer 4 (`[packs] trust` or build (d)'s scan refusing the pack: missing,
    reason `packs`); `check_packs.problems` is where those refusals land, stubbed here."""
    root = project(tmp_path)
    monkeypatch.setattr(check_packs, "problems", lambda folder: ["rule 6: refused (key: files)"])
    assert is_missing_packs(engine(root, kit(tmp_path), f"{PID}:shop"))


def test_ac5_without_packs_every_engine_line_equals_todays(tmp_path):
    """REQ-084 AC5: answer 4 (`[packs] use = []` or no table: today's lines; `agk:` and
    unprefixed names unchanged; an unknown key fails `engines-keys`; an invalid name fails)."""
    base = kit(tmp_path, "shop")
    for table in ("", "[packs]\nuse = []\n"):
        root = tmp_path / f"p{len(table)}"
        root.mkdir()
        (root / "agk.toml").write_text(f'review_mode = "solo"\n{table}', encoding="utf-8")
        assert engine(root, base, f"{PID}:shop").reason == "plugin-unreadable"
        assert engine(root, base, "agk:shop").message == " (present)"
        assert engine(root, base, "shop").message == " (present)"
        assert engine(root, base, "nowhere").message == " (missing)"
        assert engine(root, base, f"{PID}:Bad_Name").message == " (invalid)"
        found = doctor.engine_results(root, base, {"engines": {"colour": "shop"}})
        assert found["engines-keys"].status == "fail"
        assert found["engine-vision"].message.startswith(" (absent")


def test_ac5_a_pack_named_like_a_plugin_wins_only_when_locked(tmp_path):
    """REQ-084 AC5: answer 5 (a pack id that is also a plugin name: the pack only from the lock)."""
    root = project(tmp_path, pid="agk")
    base = kit(tmp_path, "other")
    assert engine(root, base, "agk:shop").message == " (present)"
    assert is_missing_packs(engine(root, base, "agk:other"))
    (root / packs.LOCK).unlink()
    assert engine(root, base, "agk:other").message == " (present)"  # today's reading


def test_ac5_a_playbook_skill_is_present_from_a_locked_pack_only(tmp_path, monkeypatch):
    """REQ-084 AC5: answer 2 (an unprefixed playbook skill from a locked pack in use) and answer
    7 (an unlocked copy never reads present)."""
    root = project(tmp_path)
    playbook = root / "config" / "playbooks" / "web-app.toml"
    playbook.parent.mkdir(parents=True)
    playbook.write_text("", encoding="utf-8")
    monkeypatch.setattr(playbook_format, "selected", lambda r: playbook)
    monkeypatch.setattr(playbook_format, "skills", lambda p, r: ["shop", "extra"])
    assert doctor.skill_lines(root, kit(tmp_path)) == ["skill: shop present", "skill: extra absent"]
    extra = root / check_packs.FOLDER / PID / "skills" / "extra"
    extra.mkdir()
    (extra / "SKILL.md").write_text("# an unlocked copy\n", encoding="utf-8")
    assert doctor.skill_lines(root, None) == ["skill: shop absent", "skill: extra absent"]


def _inserts() -> list[str]:
    text = AMENDMENT.read_text(encoding="utf-8")
    found = re.findall(r'insert "(.*?)"\.\n\s+Class:', text, flags=re.S)
    return [re.sub(r"\s*\n\s*", " ", f) for f in found]


def test_ac5_spec_0029_carries_amendment_261_word_for_word(tmp_path):
    """REQ-084 AC5: answer 3 (principle 6: the two items applied to rules 1 and 2, word for word,
    and the amendment file marked applied)."""
    spec = SPEC_0029.read_text(encoding="utf-8")
    one, two = _inserts()
    assert "A value is the name of a skill the session can see;" + one in spec
    assert "or `missing` (named but not found)." + two in spec
    rules = [line for line in spec.splitlines() if re.match(r"\d+\. \*\*", line)]
    assert one in rules[0] and two in rules[1]
    assert not any(one in r or two in r for r in rules[2:])
    assert "brief #2035: items 1 and 2 (to rules 1 and 2) applied" in AMENDMENT.read_text("utf-8")
