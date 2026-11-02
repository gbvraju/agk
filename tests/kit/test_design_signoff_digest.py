"""Tests of the sign-off digest and the reading of the sign-off record (SPEC-0037 rules 3 and 9).

REQ-044 AC2, brief #456: `scripts/agk/design_signoff.py` (installed) computes `digest(root, paths)`,
the SHA-256 of the sorted lines `<path> <SHA-256 of the file>`; `version_digest(root, version)` over
every file of `docs/design/prototype/<version>/` except `screenshots/`; `inventory_digest(root)`
over `docs/design/inventory.md`; and `rows(root)` reads the `inventory` and `design` rows of
`docs/design/signoffs.md`, refusing a row of another shape naming the rule and the row number and
never a value. It writes nothing. Invented data only, in `tmp_path`; files only, no network.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

from common import CheckError  # noqa: E402

try:
    import design_signoff as ds  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    ds = None

MODULE = KIT_ROOT / "scripts" / "agk" / "design_signoff.py"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "design-signoffs.md"
SIGNOFFS = "docs/design/signoffs.md"
V1 = "docs/design/prototype/v1"
DIGEST = "a" * 64
HEAD = "0123456789abcdef0123456789abcdef01234567"
LINK = "https://example.com/acme/books/pull/12#issuecomment-345"


def module():
    assert ds is not None, "scripts/agk/design_signoff.py is missing"
    return ds


def version(root: Path) -> Path:
    folder = root / V1
    (folder / "screenshots").mkdir(parents=True)
    (folder / "css").mkdir()
    (folder / "index.html").write_text("<!doctype html><title>Books</title>\n", encoding="utf-8")
    (folder / "books--default.html").write_text("<h1>Books</h1>\n", encoding="utf-8")
    (folder / "css" / "extra.css").write_text("body { margin: 0; }\n", encoding="utf-8")
    (folder / "screenshots" / "books--default-360-light.png").write_bytes(b"\x89PNG one")
    (folder / "screenshots" / "reflow.json").write_text("{}\n", encoding="utf-8")
    return folder


def expected(root: Path, rels: list[str]) -> str:
    """The digest by the definition of rule 9, computed here independently."""
    lines = sorted(f"{rel} {hashlib.sha256((root / rel).read_bytes()).hexdigest()}" for rel in rels)
    return hashlib.sha256("".join(f"{line}\n" for line in lines).encode("utf-8")).hexdigest()


def table(*rows: str) -> str:
    return (
        "# Design sign-offs\n\nOne row per agreement.\n\n"
        "| kind | version | digest | head | date | comment |\n"
        "|---|---|---|---|---|---|\n" + "".join(f"{r}\n" for r in rows)
    )


def write_signoffs(root: Path, text: str) -> None:
    path = root / SIGNOFFS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


INVENTORY_ROW = f"| inventory | - | {DIGEST} | {HEAD} | 2026-11-02 | {LINK} |"
DESIGN_ROW = f"| design | v1 | {'b' * 64} | {HEAD} | 2026-11-03 | {LINK} |"


def test_ac2_the_digest_is_stable_and_follows_the_definition(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (SHA-256 of the sorted `<path> <SHA-256>` lines)."""
    version(tmp_path)
    rels = [f"{V1}/index.html", f"{V1}/books--default.html"]
    first = module().digest(tmp_path, rels)
    assert first == module().digest(tmp_path, list(reversed(rels)))
    assert first == expected(tmp_path, rels)
    assert len(first) == 64 and first == first.lower()


def test_ac2_one_changed_byte_changes_the_digest(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (any change in a signed-off file shows in the digest)."""
    folder = version(tmp_path)
    before = module().version_digest(tmp_path, "v1")
    page = folder / "books--default.html"
    page.write_bytes(page.read_bytes().replace(b"Books", b"Booke"))
    assert module().version_digest(tmp_path, "v1") != before


def test_ac2_a_file_added_or_removed_changes_the_version_digest(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (an addition or a removal shows in the digest)."""
    folder = version(tmp_path)
    before = module().version_digest(tmp_path, "v1")
    (folder / "new.html").write_text("<h1>New</h1>\n", encoding="utf-8")
    added = module().version_digest(tmp_path, "v1")
    assert added != before
    (folder / "new.html").unlink()
    (folder / "css" / "extra.css").unlink()
    assert module().version_digest(tmp_path, "v1") not in (before, added)


def test_ac2_the_version_digest_leaves_screenshots_out(tmp_path):
    """REQ-044 AC2: SPEC-0037 rules 8 and 9 (`screenshots/` is outside the signed-off digest)."""
    folder = version(tmp_path)
    before = module().version_digest(tmp_path, "v1")
    rels = [f"{V1}/index.html", f"{V1}/books--default.html", f"{V1}/css/extra.css"]
    assert before == expected(tmp_path, rels)
    (folder / "screenshots" / "reflow.json").write_text('{"x": "ok"}\n', encoding="utf-8")
    (folder / "screenshots" / "more.png").write_bytes(b"\x89PNG two")
    assert module().version_digest(tmp_path, "v1") == before


@pytest.mark.parametrize("name", ["v0", "1", "v1/..", "../v1", "draft"])
def test_ac2_a_version_that_is_not_v_n_is_refused(tmp_path, name):
    """REQ-044 AC2: SPEC-0037 rule 4 (`v1`, `v2` and so on; Q-S0037-4)."""
    version(tmp_path)
    with pytest.raises(CheckError) as caught:
        module().version_digest(tmp_path, name)
    assert str(caught.value).startswith("rule 9:")
    assert name not in str(caught.value)


def test_ac2_a_missing_version_folder_is_refused(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (no digest of a version that does not exist)."""
    with pytest.raises(CheckError) as caught:
        module().version_digest(tmp_path, "v2")
    assert "rule 9: the version folder does not exist" in str(caught.value)


def test_ac2_the_inventory_digest_is_the_digest_of_the_inventory_file(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (the `inventory` row holds the digest of `inventory.md`)."""
    path = tmp_path / "docs" / "design" / "inventory.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Design inventory\n", encoding="utf-8")
    found = module().inventory_digest(tmp_path)
    assert found == expected(tmp_path, ["docs/design/inventory.md"])
    path.write_text("# Design inventory.\n", encoding="utf-8")
    assert module().inventory_digest(tmp_path) != found


def test_ac2_the_inventory_digest_refuses_without_an_inventory(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (no digest of an inventory that does not exist)."""
    with pytest.raises(CheckError) as caught:
        module().inventory_digest(tmp_path)
    assert "rule 3: docs/design/inventory.md does not exist" in str(caught.value)


def test_ac2_the_template_is_one_empty_table_that_rows_reads(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (the template holds the one table, with no row)."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "| kind | version | digest | head | date | comment |" in text
    write_signoffs(tmp_path, text)
    assert module().rows(tmp_path) == []


def test_ac2_rows_reads_the_inventory_and_design_rows(tmp_path):
    """REQ-044 AC2: SPEC-0037 rules 3 and 9 (the rows, in file order)."""
    write_signoffs(tmp_path, table(INVENTORY_ROW, DESIGN_ROW))
    found = module().rows(tmp_path)
    assert found == [
        {
            "row": 1,
            "kind": "inventory",
            "version": "-",
            "digest": DIGEST,
            "head": HEAD,
            "date": "2026-11-02",
            "comment": LINK,
        },
        {
            "row": 2,
            "kind": "design",
            "version": "v1",
            "digest": "b" * 64,
            "head": HEAD,
            "date": "2026-11-03",
            "comment": LINK,
        },
    ]


def test_ac2_no_signoffs_file_reads_no_row(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (nothing signed off yet)."""
    assert module().rows(tmp_path) == []


BAD = [
    ("kind", f"| zzkind | - | {DIGEST} | {HEAD} | 2026-11-02 | {LINK} |", "zzkind"),
    ("version", f"| inventory | v1 | {DIGEST} | {HEAD} | 2026-11-02 | {LINK} |", None),
    ("version", f"| design | zzv | {DIGEST} | {HEAD} | 2026-11-02 | {LINK} |", "zzv"),
    ("version", f"| design | - | {DIGEST} | {HEAD} | 2026-11-02 | {LINK} |", None),
    ("digest", f"| inventory | - | {'z' * 64} | {HEAD} | 2026-11-02 | {LINK} |", "z" * 64),
    ("digest", f"| inventory | - | {DIGEST[:40]} | {HEAD} | 2026-11-02 | {LINK} |", None),
    ("head", f"| inventory | - | {DIGEST} | {HEAD[:12]} | 2026-11-02 | {LINK} |", HEAD[:12]),
    ("date", f"| inventory | - | {DIGEST} | {HEAD} | 2026-02-30 | {LINK} |", "2026-02-30"),
    ("date", f"| inventory | - | {DIGEST} | {HEAD} | 2 Nov 2026 | {LINK} |", "2 Nov"),
    ("comment", f"| inventory | - | {DIGEST} | {HEAD} | 2026-11-02 | zz-not-a-link |", "zz-not"),
    ("cells", f"| inventory | - | {DIGEST} | {HEAD} | 2026-11-02 |", None),
]


@pytest.mark.parametrize("what,row,value", BAD, ids=[f"{b[0]}-{i}" for i, b in enumerate(BAD)])
def test_ac2_a_malformed_row_is_refused_naming_the_rule_and_the_row(tmp_path, what, row, value):
    """REQ-044 AC2: SPEC-0037 rule 9 (a row of another shape is refused, never its value)."""
    write_signoffs(tmp_path, table(INVENTORY_ROW, row))
    with pytest.raises(CheckError) as caught:
        module().rows(tmp_path)
    message = str(caught.value)
    assert message.startswith(f"rule 9: {SIGNOFFS}: row 2:"), message
    if what != "cells":
        assert f"the {what}" in message, message
    if value is not None:
        assert value not in message


def test_ac2_a_signoffs_file_without_the_table_is_refused(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (the file holds the one table of the template)."""
    write_signoffs(tmp_path, "# Design sign-offs\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    with pytest.raises(CheckError) as caught:
        module().rows(tmp_path)
    assert str(caught.value) == f"rule 9: {SIGNOFFS}: the file has no sign-off table"


def test_ac2_the_signoff_module_writes_nothing(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 9 (no check writes anything)."""
    version(tmp_path)
    write_signoffs(tmp_path, table(INVENTORY_ROW))
    (tmp_path / "docs" / "design" / "inventory.md").write_text("# Inventory\n", encoding="utf-8")
    before = sorted((p.as_posix(), p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file())
    module().version_digest(tmp_path, "v1")
    module().inventory_digest(tmp_path)
    module().rows(tmp_path)
    after = sorted((p.as_posix(), p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file())
    assert after == before
    source = MODULE.read_text(encoding="utf-8")
    for word in ("socket", "urllib", "http.client", "subprocess", "write_text", "write_bytes"):
        assert word not in source, word


def test_ac2_the_signoff_module_is_installed_in_sorted_order():
    """REQ-044 AC2: SPEC-0037 rule 14 (b) (the sign-off module is verbatim)."""
    verbatim = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text())["verbatim"]
    assert "scripts/agk/design_signoff.py" in verbatim
    assert verbatim == sorted(verbatim)
