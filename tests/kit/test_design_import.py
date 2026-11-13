"""Tests of the imported version (SPEC-0037 rule 15 as amendment 161 items 1 to 3 propose; REQ-044,
REQ-036; brief #1061, build (a) of item 8).

`design.py import <folder>` copies a customer's prototype byte for byte into
`docs/design/imported/i<n>/files/` with `manifest.json` (path, size, SHA-256, `digest`, `pages`) and
`external.txt`; `scripts/agk/design_import.py` (installed, imported by `check_design.py`) checks
each imported version: the files against the manifest, `external.txt` against the files, the map
`map.md` against the manifest and `docs/design/inventory.md`, and the coverage of every `yes` state
by an imported row or a kit page. Messages name the rule and the file (or the screen and state),
never a value. Rules 5 to 7 do not apply to an imported page, and no test opens one: pages are read
as text only. Invented pages only, `example.com` links, in `tmp_path`; the PDF is made in the test;
files only, no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

try:
    import design_import as di  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    di = None

DESIGN = KIT_ROOT / "scripts" / "agk" / "design.py"
CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
I1 = "docs/design/imported/i1"
WHERE = f"rule 15: {I1}"

REQUIREMENTS = """# Requirements

### REQ-001 — A reader keeps a list of books

- Acceptance: AC1 a reader adds a book
- Status: planned
"""

INVENTORY = """# Design inventory

The screens and states of the product, from the requirements and specs only.

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: books

## Screens

### books

- Flow: keep a list
- Pattern: list with filter and sort
- Links to: none
- State default: yes
- State empty: yes
- State loading: n/a: the list is read at once
- State error: n/a: nothing can fail
- State no-permission: n/a: every reader may see their own list
- State long-content: n/a: the list is short
- State success: n/a: nothing is saved
"""

INDEX = """<!doctype html>
<html><head><title>Books</title>
<link rel="stylesheet" href="css/site.css">
<link rel="stylesheet" href="https://cdn.example.com/kit.css">
<style>.hero { color: #ff00aa; background: url('img/hero.png') }</style>
<script>document.title = "Books";</script>
</head><body onload="go()">
<img src="img/logo.png" alt="logo"><a href="empty.html">none yet</a>
<script src="js/app.js"></script>
</body></html>
"""
EMPTY = "<!doctype html><title>No books</title><p>No books yet.</p>\n"
CSS = "body { color: tomato } .x { background: url(//images.example.com/bg.png) }\n"


def pdf(pages: int) -> bytes:
    """A small PDF of PAGES pages, written here and never committed."""
    kids = " ".join(f"{3 + i} 0 R" for i in range(pages))
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>",
        *["<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>" for _ in range(pages)],
    ]
    body = "%PDF-1.4\n" + "".join(f"{n} 0 obj\n{o}\nendobj\n" for n, o in enumerate(objects, 1))
    return (body + "trailer\n<< /Root 1 0 R >>\n%%EOF\n").encode("ascii")


def prototype(folder: Path) -> Path:
    """An invented click-through prototype of two pages, assets, a picture and a two-page PDF."""
    (folder / "css").mkdir(parents=True)
    (folder / "img").mkdir()
    (folder / "js").mkdir()
    (folder / "index.html").write_text(INDEX, encoding="utf-8")
    (folder / "empty.html").write_text(EMPTY, encoding="utf-8")
    (folder / "css" / "site.css").write_text(CSS, encoding="utf-8")
    (folder / "js" / "app.js").write_text("function go() { return 1; }\n", encoding="utf-8")
    (folder / "img" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n logo")
    (folder / "img" / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n hero")
    (folder / "img" / "sketch.png").write_bytes(b"\x89PNG\r\n\x1a\n sketch")
    (folder / "flows.pdf").write_bytes(pdf(2))
    return folder


def project(root: Path) -> Path:
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    (root / "docs" / "design" / "inventory.md").write_text(INVENTORY, encoding="utf-8")
    return root


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, *args], capture_output=True, text=True, check=False
    )


def imported(tmp_path: Path) -> Path:
    """A project with the fixture prototype imported as i1."""
    root = project(tmp_path / "proj")
    source = prototype(tmp_path / "customer")
    proc = run(str(DESIGN), "import", str(source), "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root


COMPLETE = """# Screen map of i1

- index.html -> books/default
- empty.html -> books/empty
- img/sketch.png -> out: an early sketch the customer replaced
- flows.pdf#page=1 -> out: the flow overview, no screen of its own
- flows.pdf#page=2 -> out: the release notes
"""


def mapped(root: Path, text: str = COMPLETE) -> Path:
    (root / I1 / "map.md").write_text(text, encoding="utf-8")
    return root


def problems(root: Path) -> list[str]:
    assert di is not None, "scripts/agk/design_import.py is missing"
    return di.imported_problems(root)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


# --- item 1: the import ---------------------------------------------------------------------------


def test_import_copies_every_file_byte_for_byte_into_files(tmp_path):
    """REQ-044: amendment 161 item 1 (every file, its relative path kept, Q-S0037-17, 18)."""
    root = imported(tmp_path)
    assert tree(root / I1 / "files") == tree(tmp_path / "customer")
    assert (root / I1 / "manifest.json").is_file()
    assert (root / I1 / "external.txt").is_file()


def test_import_numbers_i1_then_i2_and_never_overwrites(tmp_path):
    """REQ-044: amendment 161 item 1 (the next free number, Q-S0037-12)."""
    root = imported(tmp_path)
    before = tree(root / I1)
    (tmp_path / "customer" / "index.html").write_text(EMPTY, encoding="utf-8")
    proc = run(str(DESIGN), "import", str(tmp_path / "customer"), "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert tree(root / I1) == before
    assert (root / "docs/design/imported/i2/files/index.html").read_text(encoding="utf-8") == EMPTY


def test_the_manifest_lists_path_size_and_sha256_sorted_by_path(tmp_path):
    """REQ-044: amendment 161 item 1 (one entry per file, sorted by path)."""
    root = imported(tmp_path)
    manifest = json.loads((root / I1 / "manifest.json").read_text(encoding="utf-8"))
    files = tree(tmp_path / "customer")
    assert [e["path"] for e in manifest["files"]] == sorted(files)
    for entry in manifest["files"]:
        data = files[entry["path"]]
        assert entry["size"] == len(data)
        assert entry["sha256"] == sha(data)


def test_the_digest_follows_rule_9s_formula_is_stable_and_changes_with_one_byte(tmp_path):
    """REQ-044: amendment 161 item 1 (the SHA-256 of the sorted `<path> <SHA-256>` lines)."""
    root = imported(tmp_path)
    manifest = json.loads((root / I1 / "manifest.json").read_text(encoding="utf-8"))
    lines = sorted(f"{p} {sha(d)}\n" for p, d in tree(tmp_path / "customer").items())
    assert manifest["digest"] == sha("".join(lines).encode("utf-8"))
    assert di.manifest(root / I1 / "files")["digest"] == manifest["digest"]
    (root / I1 / "files" / "js" / "app.js").write_bytes(b"function go() { return 2; }\n")
    assert di.manifest(root / I1 / "files")["digest"] != manifest["digest"]


def refused(tmp_path: Path, source: Path, root: Path, words: str) -> None:
    before = tree(root)
    proc = run(str(DESIGN), "import", str(source), "--root", str(root))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout.startswith("FAIL design: rule 15: "), proc.stdout
    assert words in proc.stdout, proc.stdout
    assert tree(root) == before
    assert not (root / "docs/design/imported").exists()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symbolic links on this system")
def test_a_symbolic_link_is_refused_naming_the_rule_and_the_file_copying_nothing(tmp_path):
    """REQ-044: amendment 161 item 1 (a symbolic link is refused; nothing is copied)."""
    root = project(tmp_path / "proj")
    source = prototype(tmp_path / "customer")
    os.symlink(source / "index.html", source / "img" / "again.html")
    refused(tmp_path, source, root, "img/again.html")


def test_a_source_inside_docs_design_is_refused_copying_nothing(tmp_path):
    """REQ-044: amendment 161 item 1 (a source folder inside docs/design/ is refused)."""
    root = project(tmp_path / "proj")
    source = prototype(root / "docs" / "design" / "drop")
    refused(tmp_path, source, root, "docs/design/")


def test_an_empty_folder_is_refused_copying_nothing(tmp_path):
    """REQ-044: amendment 161 item 1 (an empty folder is refused)."""
    root = project(tmp_path / "proj")
    (tmp_path / "customer" / "css").mkdir(parents=True)
    refused(tmp_path, tmp_path / "customer", root, "no file")


# --- item 1: pages, picture pages and assets ------------------------------------------------------


def test_pages_picture_pages_and_assets_are_classified_from_the_files(tmp_path):
    """REQ-044: amendment 161 item 1 (an HTML file is a page; an image no page references and
    each PDF page are picture pages; a referenced image, a stylesheet and a script are assets,
    Q-S0037-13)."""
    root = imported(tmp_path)
    manifest = json.loads((root / I1 / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["pages"] == [
        "empty.html",
        "flows.pdf#page=1",
        "flows.pdf#page=2",
        "img/sketch.png",
        "index.html",
    ]


def test_an_image_referenced_only_by_a_css_url_in_a_page_is_an_asset(tmp_path):
    """REQ-044: amendment 161 item 1 (a page's CSS `url()` makes the image an asset)."""
    root = imported(tmp_path)
    pages = json.loads((root / I1 / "manifest.json").read_text(encoding="utf-8"))["pages"]
    assert "img/hero.png" not in pages
    assert "img/logo.png" not in pages


# --- items 2 and 3: the checks --------------------------------------------------------------------


def test_a_complete_map_passes(tmp_path):
    """REQ-044: amendment 161 item 2 (every page and picture page has a row)."""
    root = mapped(imported(tmp_path))
    assert problems(root) == []


def test_check_design_reads_the_imported_version_and_passes_a_complete_map(tmp_path):
    """REQ-044: amendment 161 item 3 (`check_design.py` imports `design_import.py`)."""
    root = mapped(imported(tmp_path))
    proc = run(str(CHECK), "--root", str(root))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.strip().splitlines()[-1] == "ok design"


def test_check_design_fails_an_imported_version_with_no_map(tmp_path):
    """REQ-044: amendment 161 item 2 (a page with no row fails `check_design.py`)."""
    root = imported(tmp_path)
    proc = run(str(CHECK), "--root", str(root))
    assert proc.returncode == 1
    assert f"FAIL design: {WHERE}/map.md: index.html: the page has no row" in proc.stdout


def test_a_missing_listed_file_fails_naming_the_file(tmp_path):
    """REQ-044: amendment 161 item 3 (a listed file that is missing)."""
    root = mapped(imported(tmp_path))
    (root / I1 / "files" / "js" / "app.js").unlink()
    assert f"{WHERE}/files/js/app.js: a listed file is missing" in problems(root)


def test_an_added_file_fails_naming_the_file(tmp_path):
    """REQ-044: amendment 161 item 3 (a file of files/ that the manifest does not list)."""
    root = mapped(imported(tmp_path))
    (root / I1 / "files" / "extra.txt").write_text("added\n", encoding="utf-8")
    assert f"{WHERE}/files/extra.txt: the file is not in the manifest" in problems(root)


def test_a_changed_file_fails_naming_the_file_and_the_digest(tmp_path):
    """REQ-044: amendment 161 item 3 (a size or SHA-256 that does not match, and the digest)."""
    root = mapped(imported(tmp_path))
    (root / I1 / "files" / "css" / "site.css").write_text("body {}\n", encoding="utf-8")
    found = problems(root)
    assert f"{WHERE}/files/css/site.css: the size or SHA-256 does not match the manifest" in found
    assert f"{WHERE}/manifest.json: the digest does not follow from the files" in found
    assert not any(sha(b"body {}\n") in p for p in found)  # never a value


def test_a_pages_list_that_does_not_follow_from_the_files_fails(tmp_path):
    """REQ-044: amendment 161 item 3 (the `pages` list is recomputed from the files)."""
    root = mapped(imported(tmp_path))
    path = root / I1 / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["pages"].remove("img/sketch.png")
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert f"{WHERE}/manifest.json: the pages list does not follow from the files" in problems(root)


def test_an_edited_external_list_fails(tmp_path):
    """REQ-044: amendment 161 item 3 (the check recomputes `external.txt` and compares)."""
    root = mapped(imported(tmp_path))
    (root / I1 / "external.txt").write_text("", encoding="utf-8")
    assert f"{WHERE}/external.txt: the list does not follow from the files" in problems(root)


MAP_FAILURES = [
    (
        "- index.html -> books/default\n",
        "",
        "map.md: index.html: the page has no row",
    ),
    (
        "",
        "- nowhere.html -> out: gone\n",
        "map.md: nowhere.html: the row names no page of the manifest",
    ),
    (
        "",
        "- index.html -> out: a second row\n",
        "map.md: index.html: the file has more than one row",
    ),
    (
        "- empty.html -> books/empty\n",
        "- empty.html -> shelves/default\n",
        "map.md: shelves/default: the row names a screen or state not in the inventory",
    ),
    (
        "- empty.html -> books/empty\n",
        "- empty.html -> books/archived\n",
        "map.md: books/archived: the row names a screen or state not in the inventory",
    ),
    (
        "- empty.html -> books/empty\n",
        "- empty.html -> books/loading\n",
        "map.md: books/loading: the state is marked n/a: in the inventory",
    ),
    (
        "- empty.html -> books/empty\n",
        "- empty.html -> books/default\n",
        "map.md: books/default: two rows name the same screen and state",
    ),
    (
        "- img/sketch.png -> out: an early sketch the customer replaced\n",
        "- img/sketch.png -> out:\n",
        "map.md: img/sketch.png: the out: row has no reason",
    ),
]


@pytest.mark.parametrize(("old", "new", "message"), MAP_FAILURES)
def test_each_map_rule_fails_naming_the_rule(tmp_path, old, new, message):
    """REQ-044: amendment 161 item 2 (no row, a row for no file, a file twice, an unknown screen or
    state, an `n/a:` state, a screen and state twice, an `out:` row with no reason)."""
    text = COMPLETE.replace(old, new) if old else COMPLETE + new
    root = mapped(imported(tmp_path), text)
    assert f"{WHERE}/{message}" in problems(root)


def test_a_yes_state_that_no_version_covers_fails_naming_the_screen_and_state(tmp_path):
    """REQ-044: amendment 161 item 2 (a `yes` state that neither a row nor a kit page covers)."""
    text = COMPLETE.replace("- empty.html -> books/empty\n", "- empty.html -> out: a draft\n")
    root = mapped(imported(tmp_path), text)
    expected = "rule 15: docs/design/inventory.md: books/empty: no version covers the state"
    assert problems(root) == [expected]


def test_a_yes_state_covered_only_by_a_kit_page_passes(tmp_path):
    """REQ-044: amendment 161 item 2 (the coverage reads `v<n>` and `i<n>` folders alike)."""
    text = COMPLETE.replace("- empty.html -> books/empty\n", "- empty.html -> out: a draft\n")
    root = mapped(imported(tmp_path), text)
    kit = root / "docs" / "design" / "prototype" / "v1"
    kit.mkdir(parents=True)
    (kit / "books--empty.html").write_text("<h1>No books</h1>\n", encoding="utf-8")
    assert problems(root) == []


# --- item 3: rules 5 to 7 do not apply; external references are listed ----------------------------


def test_an_imported_page_is_not_held_to_rules_5_to_7(tmp_path):
    """REQ-044: amendment 161 item 3 (an inline script, an event handler, an external stylesheet
    and a colour outside the tokens pass, because rules 5 to 7 do not apply)."""
    root = mapped(imported(tmp_path))
    proc = run(str(CHECK), "--root", str(root))
    assert proc.returncode == 0, proc.stdout
    assert "rule 5" not in proc.stdout and "rule 6" not in proc.stdout
    assert "rule 7" not in proc.stdout


def test_every_external_reference_is_listed_with_its_file(tmp_path):
    """REQ-044: amendment 161 item 3 (URLs that start `http:`, `https:` or `//`, Q-S0037-14)."""
    root = imported(tmp_path)
    lines = (root / I1 / "external.txt").read_text(encoding="utf-8").splitlines()
    assert lines == [
        "css/site.css //images.example.com/bg.png",
        "index.html https://cdn.example.com/kit.css",
    ]


def test_no_check_or_import_opens_a_page(tmp_path):
    """REQ-044: amendment 161 item 3 (pages are read as text only: no browser, no subprocess)."""
    assert di is not None, "scripts/agk/design_import.py is missing"
    text = (KIT_ROOT / "scripts" / "agk" / "design_import.py").read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:subprocess|webbrowser|socket|urllib|http|requests|ssl)\b",
        text,
        re.M,
    )


def test_without_an_imported_version_check_design_is_unchanged(tmp_path):
    """REQ-044: amendment 161 item 2 (a project with only an inventory reads as before)."""
    root = project(tmp_path)
    proc = run(str(CHECK), "--root", str(root))
    assert proc.returncode == 0, proc.stdout
    assert "rule 15" not in proc.stdout


# --- brief #1204: a one-page prototype drawn by script --------------------------------------------

NOTICE = "has one page drawn by script; capture each screen and state as its own page"
GUIDE = KIT_ROOT / "docs" / "guides" / "planning.md"
SKILL = KIT_ROOT / "skills" / "plan-intake" / "SKILL.md"
SCRIPTED = """<!doctype html><html><head><title>App</title></head>
<body><div id="app"></div>
<script>document.getElementById("app").textContent = "Books";</script>
</body></html>
"""


def import_of(tmp_path: Path, pages: dict[str, str]) -> subprocess.CompletedProcess:
    root = project(tmp_path / "proj")
    source = tmp_path / "customer"
    source.mkdir()
    for name, text in pages.items():
        (source / name).write_text(text, encoding="utf-8")
    return run(str(DESIGN), "import", str(source), "--root", str(root))


def test_a_one_page_import_drawn_by_script_prints_the_notice_once_and_exits_0(tmp_path):
    """REQ-050: brief #1204 answer 1 (a one-page prototype drawn by script is flagged)."""
    proc = import_of(tmp_path, {"index.html": SCRIPTED, "app.css": "body { color: tomato }\n"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [line for line in proc.stdout.splitlines() if line.startswith("notice: ")]
    assert lines == [
        f"notice: i1 {NOTICE} and import that folder instead"
        ' (docs/guides/planning.md "From a prototype")'
    ]
    assert (tmp_path / "proj" / I1 / "files" / "index.html").is_file()


@pytest.mark.parametrize(
    "pages",
    [
        {"index.html": EMPTY},
        {"index.html": SCRIPTED, "empty.html": EMPTY},
    ],
    ids=["one-page-no-script", "two-pages"],
)
def test_a_one_page_import_without_script_or_a_two_page_import_prints_no_notice(tmp_path, pages):
    """REQ-050: brief #1204 answer 1 (only one page that holds a script is flagged)."""
    proc = import_of(tmp_path, pages)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "notice:" not in proc.stdout


def test_the_fixture_prototype_of_two_pages_prints_no_notice(tmp_path):
    """REQ-050: brief #1204 answer 4 (c) (the existing import is unchanged)."""
    root = project(tmp_path / "proj")
    proc = run(str(DESIGN), "import", str(prototype(tmp_path / "customer")), "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "notice:" not in proc.stdout


def test_the_guide_captures_a_scripted_prototype_first_and_traces_before_approval():
    """REQ-050: brief #1204 answer 2 (step 0, and `unmatched screen:` read before approval)."""
    text = GUIDE.read_text(encoding="utf-8")
    section = text.split("## From a prototype and an OpenSpec file", 1)[1].split("\n## ", 1)[0]
    step0 = section.index("0. **Capture")
    assert step0 < section.index("1. **Import the prototype")
    assert "<screen>--<state>.html" in section[step0:]
    flat = " ".join(section[step0 : section.index("1. **Import the prototype")].split())
    assert "approved only after `check_plan.py --trace`" in flat
    assert "`unmatched screen:` lines are read before the approval" in flat
    assert section.index("`unmatched screen:`", step0) < section.index("7. **Approve and publish")


def test_the_plan_intake_skill_points_at_step_0_for_a_one_page_import():
    """REQ-050: brief #1204 answer 3 (say so before drafting, point at step 0)."""
    text = SKILL.read_text(encoding="utf-8")
    assert "no version with more than one page" in text
    assert "step 0" in text
