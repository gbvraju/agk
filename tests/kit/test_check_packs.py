"""Tests of the pack format check (SPEC-0077 rules 2 and 3; REQ-084 AC1; brief #2031, ADR-0838).

A pack is `config/packs/<id>/` holding one `agk-pack.toml`. `check_packs.findings` refuses each
malformed manifest naming the rule, the pack id and the key, never a value; a well-formed stub pack
passes; `check_playbooks.findings` carries the line, so the `playbooks` step prints it as
`FAIL playbooks:`. `agk-core`, the built-in pack, has no manifest. Fixtures in `tmp_path` only:
invented data (`example.com`), no network, no model.
"""

from __future__ import annotations

import hashlib
import subprocess  # nosec B404 - runs the check itself with a fixed argument list
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_packs  # noqa: E402
import check_playbooks  # noqa: E402

PID = "zz-shop"
REL = f"config/packs/{PID}"
KNOWLEDGE = """[[terms]]
term = "basket"
source = "https://example.com/shop (accessed 2026-11-20)"

[[terms]]
term = "till"
basis = "expected"
"""
SKILL = "# An invented skill\n\nDraft the shop's terms.\n"
MANIFEST = """format = 1
id = "zz-shop"
version = "1.2.0"
publisher = "Example Org"
tier = "curated"
licence = "MIT"
source = "https://example.com/packs/zz-shop"
kit = ">=0.65"
as_of = "2026-11-20"
reviewed = "2026-11-21 by maintainers"
kinds = ["domains", "skills"]

[permissions]

[files]
"""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_pack(
    root: Path, manifest: str | None = None, files: dict[str, str] | None = None, folder: str = PID
) -> Path:
    """A stub pack: FILES written and listed in `[files]` with their hashes unless MANIFEST is
    given whole."""
    files = (
        {"domains/shop.toml": KNOWLEDGE, "skills/shop/SKILL.md": SKILL} if files is None else files
    )
    base = root / "config" / "packs" / folder
    for rel, text in files.items():
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_text(text, encoding="utf-8")
    if manifest is None:
        manifest = MANIFEST + "".join(f'"{rel}" = "{sha(text)}"\n' for rel, text in files.items())
    base.mkdir(parents=True, exist_ok=True)
    (base / check_packs.MANIFEST).write_text(manifest, encoding="utf-8")
    return base


def good() -> str:
    files = {"domains/shop.toml": KNOWLEDGE, "skills/shop/SKILL.md": SKILL}
    return MANIFEST + "".join(f'"{rel}" = "{sha(text)}"\n' for rel, text in files.items())


def test_ac1_no_pack_folder_gives_no_finding(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 2 (with no pack only `agk-core`, and nothing to say)."""
    assert check_packs.findings(tmp_path) == []
    (tmp_path / "config" / "packs").mkdir(parents=True)
    assert check_packs.findings(tmp_path) == []
    assert check_packs.in_use(tmp_path) == [check_packs.CORE] == ["agk-core"]


def test_ac1_a_well_formed_stub_pack_passes(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (a pack listed in `[packs] use` with its manifest hash)."""
    base = write_pack(tmp_path)
    digest = hashlib.sha256((base / check_packs.MANIFEST).read_bytes()).hexdigest()
    (tmp_path / "agk.toml").write_text(
        f'[packs]\nuse = [{{ id = "{PID}", version = "1.2.0", sha256 = "{digest}" }}]\n',
        encoding="utf-8",
    )
    assert check_packs.findings(tmp_path) == []
    assert check_packs.in_use(tmp_path) == ["agk-core", PID]


@pytest.mark.parametrize(
    ("old", "new", "what", "key"),
    [
        ("format = 1\n", "", "a required key is missing", "format"),
        ("format = 1\n", "format = 2\n", "the key has the wrong value", "format"),
        ("format = 1\n", "format = true\n", "the key has the wrong type", "format"),
        ('publisher = "Example Org"\n', "", "a required key is missing", "publisher"),
        (
            'licence = "MIT"\n',
            'licence = "MIT"\nzz_extra = "zz-x"\n',
            "the key is not of the format",
            "zz_extra",
        ),
        ('id = "zz-shop"\n', 'id = "Zz_Shop"\n', "the key has the wrong value", "id"),
        ('id = "zz-shop"\n', 'id = "agk-core"\n', "the key has the wrong value", "id"),
        ('id = "zz-shop"\n', 'id = "zz-other"\n', "the id is not the folder's name", "id"),
        ('version = "1.2.0"\n', 'version = ">=1.2"\n', "the key has the wrong value", "version"),
        ('version = "1.2.0"\n', 'version = "1.x"\n', "the key has the wrong value", "version"),
        ('tier = "curated"\n', 'tier = "zz-gold"\n', "the key has the wrong value", "tier"),
        (
            'as_of = "2026-11-20"\n',
            'as_of = "20 Nov 2026"\n',
            "the key has the wrong value",
            "as_of",
        ),
        (
            'reviewed = "2026-11-21 by maintainers"\n',
            'reviewed = "2026-11-21"\n',
            "the key has the wrong value",
            "reviewed",
        ),
        (
            'reviewed = "2026-11-21 by maintainers"\n',
            'reviewed = "2026-11-21 by zz@example.com"\n',
            "the key has the wrong value",
            "reviewed",
        ),
        (
            'kinds = ["domains", "skills"]',
            'kinds = ["domains", "skills", "zz-recipes"]',
            "a kind is not one of rule 2's nine",
            "kinds",
        ),
        (
            'kinds = ["domains", "skills"]',
            'kinds = "domains"',
            "the key has the wrong type",
            "kinds",
        ),
        (
            "[permissions]\n",
            '[permissions]\nnetwork = "open"\n',
            "the key has the wrong value",
            "permissions.network",
        ),
        (
            "[permissions]\n",
            "[permissions]\nmcp = [1]\n",
            "the key has the wrong type",
            "permissions.mcp",
        ),
        (
            "[permissions]\n",
            "[permissions]\nhooks = true\n",
            "the key is not of the format",
            "permissions.hooks",
        ),
        ('kit = ">=0.65"\n', "kit = 65\n", "the key has the wrong type", "kit"),
        ('kit = ">=0.65"\n', 'kit = ">=0.65"\nevals = 1\n', "the key has the wrong type", "evals"),
    ],
)
def test_ac1_a_malformed_manifest_is_refused_naming_rule_pack_and_key(
    tmp_path, old, new, what, key
):
    """REQ-084 AC1: SPEC-0077 rule 3 (each refusal names the rule, the pack id and the key)."""
    text = good()
    assert old in text
    write_pack(tmp_path, text.replace(old, new, 1))
    lines = check_packs.findings(tmp_path)
    assert f"rule 3: {REL}: {what} (key: {key})" in lines
    for value in (
        "Zz_Shop",
        "zz-other",
        ">=1.2",
        "zz-gold",
        "20 Nov",
        "zz@example.com",
        "zz-recipes",
        "open",
        "zz-x",
    ):
        assert all(value not in line for line in lines)


def test_ac1_a_file_not_listed_missing_or_changed_is_refused(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (a file not listed, or whose hash differs)."""
    base = write_pack(tmp_path)
    (base / "domains" / "zz-stray.toml").write_text(KNOWLEDGE, encoding="utf-8")
    (base / "skills" / "shop" / "SKILL.md").write_text(SKILL + "more\n", encoding="utf-8")
    (base / "domains" / "shop.toml").unlink()
    lines = check_packs.findings(tmp_path)
    assert f"rule 3: {REL}: a file is not listed (key: files)" in lines
    assert f"rule 3: {REL}: a listed file is missing (key: files)" in lines
    assert f"rule 3: {REL}: a listed file's SHA-256 differs (key: files)" in lines


def test_ac1_a_file_under_no_listed_kind_is_refused(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (a file under no kind's folder, or outside the pack)."""
    files = {
        "recipes/shop.toml": KNOWLEDGE,
        "skills/shop/SKILL.md": SKILL,
        "playbooks/web.toml": KNOWLEDGE,
    }
    write_pack(tmp_path, files=files)
    lines = check_packs.findings(tmp_path)
    assert lines.count(f"rule 3: {REL}: a file is under no listed kind's folder (key: kinds)") == 2
    text = good() + '"../zz.toml" = "' + "0" * 64 + '"\n'
    write_pack(tmp_path, text)
    assert f"rule 3: {REL}: a listed file is outside the pack (key: files)" in (
        check_packs.findings(tmp_path)
    )


def test_ac1_a_bad_hash_value_is_refused(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (`files` maps each path to a SHA-256)."""
    write_pack(
        tmp_path, good().replace('"skills/shop/SKILL.md" = "', '"skills/shop/SKILL.md" = "zz')
    )
    assert f"rule 3: {REL}: the key has the wrong value (key: files)" in check_packs.findings(
        tmp_path
    )


def test_ac1_an_entry_with_no_source_and_no_basis_is_refused(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (every knowledge item carries a dated source or basis)."""
    bad = KNOWLEDGE + '\n[[terms]]\nterm = "aisle"\n\n[[terms]]\nterm = "shelf"\n'
    bad += 'source = "https://example.com/zz"\n\n[[terms]]\nterm = "bay"\nbasis = "zz-guess"\n'
    write_pack(tmp_path, files={"domains/shop.toml": bad, "skills/shop/SKILL.md": SKILL})
    lines = check_packs.findings(tmp_path)
    assert (
        lines.count(
            f'rule 3: {REL}: an entry has neither a dated `source` nor `basis = "expected"` '
            "(key: source)"
        )
        == 3
    )
    write_pack(tmp_path, files={"domains/shop.toml": "[[terms]\n", "skills/shop/SKILL.md": SKILL})
    assert f"rule 3: {REL}: a knowledge file is not readable TOML (key: files)" in (
        check_packs.findings(tmp_path)
    )


def test_ac1_a_line_the_data_guard_flags_is_refused_without_its_text(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (a line that `guard.scan_text` flags)."""
    flagged = SKILL + "Write to zz.person@shop-zz.test for the shop.\n"
    write_pack(tmp_path, files={"domains/shop.toml": KNOWLEDGE, "skills/shop/SKILL.md": flagged})
    lines = check_packs.findings(tmp_path)
    hit = [line for line in lines if "the data guard flags" in line]
    assert hit and all(line.startswith(f"rule 3: {REL}: ") for line in hit)
    assert all("zz.person" not in line for line in lines)


def test_ac1_a_folder_with_no_manifest_or_a_manifest_not_toml(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (named by the pack's path class, never its text)."""
    (tmp_path / "config" / "packs" / PID).mkdir(parents=True)
    assert check_packs.findings(tmp_path) == [
        f"rule 3: {REL}: the pack has no agk-pack.toml (key: format)"
    ]
    write_pack(tmp_path, 'format = 1\nid = "zz-shop\n')
    assert check_packs.findings(tmp_path) == [
        f"rule 3: {REL}: the manifest is not readable TOML (key: format)"
    ]


def test_ac1_a_folder_name_the_guard_or_the_form_refuses_is_named_by_class(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (a name the guard would flag is named by its class only)."""
    write_pack(tmp_path, folder="Zz Bad")
    lines = check_packs.findings(tmp_path)
    assert "rule 3: config/packs/: the id is not the folder's name (key: id)" in lines
    assert all("Zz Bad" not in line for line in lines)


def test_ac1_a_pack_no_use_entry_lists_is_a_finding(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 12 (a pack folder that `[packs] use` does not list)."""
    write_pack(tmp_path)
    assert check_packs.findings(tmp_path) == [
        f"rule 12: {REL}: the pack is not listed in use (setting: packs.use)"
    ]
    assert check_packs.in_use(tmp_path) == ["agk-core"]


def test_ac1_a_refused_packs_table_is_a_finding(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 12 (the table's refusal is one more line of the step)."""
    (tmp_path / "agk.toml").write_text('[packs]\ntrust = "zz-any"\n', encoding="utf-8")
    assert check_packs.findings(tmp_path) == [
        "rule 12: the [packs] table is refused (setting: packs.trust)"
    ]


def test_ac1_the_playbooks_step_carries_a_pack_problem(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 3 (`check_playbooks.findings` runs the pack check)."""
    base = write_pack(tmp_path)
    (base / "skills" / "shop" / "SKILL.md").write_text("changed\n", encoding="utf-8")
    line = f"rule 3: {REL}: a listed file's SHA-256 differs (key: files)"
    assert line in check_playbooks.findings(tmp_path)
    assert check_playbooks.findings(tmp_path, []) == []  # a named playbook alone reads no pack
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_playbooks.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1 and f"FAIL playbooks: {line}" in proc.stdout


def test_ac1_run_alone_the_check_prints_nothing_with_no_pack(tmp_path):
    """REQ-084 AC1: SPEC-0077 rule 2 (with no pack the check prints nothing and exits 0)."""
    script = str(KIT_ROOT / "scripts/agk/check_packs.py")
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, script, "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and proc.stdout == ""
    write_pack(tmp_path)
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, script, "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL packs: rule 12: ")


def test_ac1_the_kit_itself_has_only_agk_core():
    """REQ-084 AC1: SPEC-0077 rule 2 (the kit's own repository: no `[packs]`, `agk-core` only)."""
    assert check_packs.findings(KIT_ROOT) == []
    assert check_packs.in_use(KIT_ROOT) == ["agk-core"]
    assert check_packs.core_file(KIT_ROOT, "agk.toml") == KIT_ROOT / "agk.toml"
