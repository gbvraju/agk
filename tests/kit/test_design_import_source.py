"""Tests of the prototype source (SPEC-0043 rule 2a as amendment 163 item 2 proposes, with the
owner's ruling on Q-1073-2; REQ-050, REQ-044; brief #1077, build (k)).

`design_import.py source --version i<n> --slug <slug>` writes once
`docs/sources/<slug>-prototype-i<n>.md`: rule 1's header (`Source:`, `Kind: design`,
`Version: i<n> <digest>`, `Date:`), one blank line, then one `## <screen>/<state>` heading per row
of the version's `map.md` that is not `out:`, in the map's order, with the page's visible text under
it (every text outside `script`, `style` and `template`, in document order, plus the names and
placeholders of fields), or `picture: <file>` for a picture page. It refuses a version that is not
there or whose import or map check fails, an existing target file, and a missing or malformed
`--slug`, writing nothing. Pages are read as text only: no page is opened, no network.
Invented pages only (`example.com`), in `tmp_path`.
"""

from __future__ import annotations

import re
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_plan  # noqa: E402

try:
    import design_import as di  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    di = None

DESIGN = KIT_ROOT / "scripts" / "agk" / "design.py"
IMPORT = KIT_ROOT / "scripts" / "agk" / "design_import.py"
I1 = "docs/design/imported/i1"
TARGET = "docs/sources/shop-prototype-i1.md"

INVENTORY = """# Design inventory

## Screens

### orders

- Flow: see the orders
- State default: yes
- State empty: yes
- State error: yes
- State loading: n/a: read at once

### signin

- Flow: sign in
- State default: yes
"""

ORDERS = """<!doctype html>
<html><head><title>Orders  of
 the shop</title>
<style>.x { color: red } body::after { content: "style text" }</style>
<script>var hidden = "script text";</script>
</head><body>
<!-- a comment is not text -->
<h1>Your   orders</h1>
<p>Orders placed at <b>shop.example.com</b> this year.</p>
<template><p>template text</p></template>
<form>
<label for="q">Search orders</label>
<input id="q" name="query" placeholder="Order number">
<select name="status"><option>Any status</option><option>Shipped</option></select>
<button type="submit">Find</button>
</form>
<a href="empty.html">No orders yet?</a>
<p class="hint">Last sync was an hour ago.</p>
<div role="alert">Two orders are late.</div>
<p>   </p>
<p># of orders: 3</p>
<script src="js/app.js"></script>
</body></html>
"""

EMPTY = "<!doctype html><title>No orders</title><p>You have no orders.</p>\n"
ERROR = "<!doctype html><title>Error</title><div role=\"status\">The list could not load.</div>\n"
SIGNIN = (
    "<!doctype html><title>Sign in</title>"
    '<form><input type="email" name="email" placeholder="you@example.com">'
    '<input type="submit" value="Sign in"></form>\n'
)

MAP = """# Screen map of i1

- signin.html -> signin/default
- orders.html -> orders/default
- img/empty-sketch.png -> orders/empty
- old.html -> out: an older page the customer replaced
- error.html -> orders/error
"""


def prototype(folder: Path) -> Path:
    (folder / "img").mkdir(parents=True)
    (folder / "js").mkdir()
    (folder / "orders.html").write_text(ORDERS, encoding="utf-8")
    (folder / "empty.html").write_text(EMPTY, encoding="utf-8")
    (folder / "error.html").write_text(ERROR, encoding="utf-8")
    (folder / "signin.html").write_text(SIGNIN, encoding="utf-8")
    (folder / "old.html").write_text("<title>Old</title><p>old text</p>\n", encoding="utf-8")
    (folder / "js" / "app.js").write_text("function go() { return 1; }\n", encoding="utf-8")
    (folder / "img" / "empty-sketch.png").write_bytes(b"\x89PNG\r\n\x1a\n sketch")
    return folder


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, *args], capture_output=True, text=True, check=False
    )


def imported(tmp_path: Path, mapping: str = MAP) -> Path:
    """A project with the fixture prototype imported as i1 and mapped."""
    root = tmp_path / "proj"
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "inventory.md").write_text(INVENTORY, encoding="utf-8")
    proc = run(str(DESIGN), "import", str(prototype(tmp_path / "customer")), "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (root / I1 / "map.md").write_text(mapping, encoding="utf-8")
    return root


def source(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return run(str(IMPORT), "source", "--root", str(root), *extra)


def written(root: Path) -> str:
    proc = source(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return (root / TARGET).read_text(encoding="utf-8")


def section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index(f"## {heading}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return [line for line in lines[start:end] if line]


def tree(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


# --- the file -------------------------------------------------------------------------------------


def test_the_header_is_rule_1s_four_lines_then_one_blank_line(tmp_path):
    """REQ-050 AC1: rule 2a, the header (`Version: i<n> <digest>`, the date from the UTC clock)."""
    root = imported(tmp_path)
    text = written(root)
    digest = __import__("json").loads((root / I1 / "manifest.json").read_text())["digest"]
    lines = text.splitlines()
    assert lines[0] == "Source: imported prototype i1"
    assert lines[1] == "Kind: design"
    assert lines[2] == f"Version: i1 {digest}"
    assert re.fullmatch(r"Date: \d{4}-\d{2}-\d{2}", lines[3])
    assert lines[4] == ""
    assert check_plan.header_problems(text) == []


def test_one_heading_per_mapped_row_in_the_maps_order_and_none_for_out(tmp_path):
    """REQ-050 AC1: rule 2a, one `## <screen>/<state>` per row that is not `out:`."""
    text = written(imported(tmp_path))
    assert check_plan.headings(text) == [
        "signin/default",
        "orders/default",
        "orders/empty",
        "orders/error",
    ]
    assert "old text" not in text and "Old" not in text


def test_every_visible_text_of_the_page_one_per_line_in_document_order(tmp_path):
    """REQ-050 AC1: rule 2a with the Q-1073-2 ruling, every text outside script, style, template."""
    text = written(imported(tmp_path))
    assert section(text, "orders/default") == [
        "Orders of the shop",
        "Your orders",
        "Orders placed at shop.example.com this year.",
        "Search orders",
        "query",
        "Order number",
        "status",
        "Any status",
        "Shipped",
        "Find",
        "No orders yet?",
        "Last sync was an hour ago.",
        "Two orders are late.",
        "\\# of orders: 3",
    ]


def test_no_script_style_template_or_comment_text_is_read(tmp_path):
    """REQ-050 AC1: rule 2a, the ruling's exclusions."""
    text = written(imported(tmp_path))
    for words in ("script text", "style text", "template text", "a comment", "color: red", "go()"):
        assert words not in text


def test_field_names_placeholders_messages_and_input_buttons_are_read(tmp_path):
    """REQ-050 AC1: rule 2a, the names and placeholders of fields, a role=status message."""
    text = written(imported(tmp_path))
    assert section(text, "signin/default") == ["Sign in", "email", "you@example.com", "Sign in"]
    assert section(text, "orders/error") == ["Error", "The list could not load."]


def test_a_picture_page_gets_one_picture_line(tmp_path):
    """REQ-050 AC1: rule 2a, `picture: <file>` for a picture page."""
    text = written(imported(tmp_path))
    assert section(text, "orders/empty") == ["picture: img/empty-sketch.png"]


def test_the_written_source_passes_check_plan_and_its_headings_resolve(tmp_path):
    """REQ-050 AC1: rules 1 and 2a, the file is a source of rule 1 with resolvable locations."""
    root = imported(tmp_path)
    written(root)
    assert check_plan.source_problems(root) == []
    assert check_plan.location_problem(root, f"{TARGET}#orders/default") is None


def test_the_command_prints_the_file_it_wrote(tmp_path):
    """REQ-050 AC1: rule 2a, one line naming the file and the count of headings."""
    root = imported(tmp_path)
    proc = source(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == f"wrote {TARGET} (4 headings)\n"


# --- the refusals ---------------------------------------------------------------------------------


def test_a_second_run_refuses_the_existing_file_and_leaves_it_byte_for_byte(tmp_path):
    """REQ-050 AC1: rule 2a, never over an existing file."""
    root = imported(tmp_path)
    written(root)
    before = (root / TARGET).read_bytes()
    proc = source(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 1
    assert "rule 2a" in proc.stdout and TARGET in proc.stdout
    assert (root / TARGET).read_bytes() == before


def test_a_version_not_on_the_branch_is_refused_writing_nothing(tmp_path):
    """REQ-050 AC1: rule 2a, the version must exist."""
    root = imported(tmp_path)
    proc = source(root, "--version", "i2", "--slug", "shop")
    assert proc.returncode == 1
    assert "rule 2a" in proc.stdout and "i2" in proc.stdout
    assert not (root / "docs" / "sources").exists()


@pytest.mark.parametrize(
    "change",
    [
        "missing-file",
        "unmapped-page",
        "unknown-state",
    ],
)
def test_a_version_whose_import_or_map_check_fails_is_refused_writing_nothing(tmp_path, change):
    """REQ-050 AC1: rule 2a, a version with an import or map problem is refused."""
    if change == "unmapped-page":
        root = imported(tmp_path, MAP.replace("- error.html -> orders/error\n", ""))
    elif change == "unknown-state":
        root = imported(tmp_path, MAP.replace("orders/error", "orders/sideways"))
    else:
        root = imported(tmp_path)
        (root / I1 / "files" / "error.html").unlink()
    before = tree(root)
    proc = source(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 1
    assert "rule 2a" in proc.stdout and "i1" in proc.stdout
    assert tree(root) == before


@pytest.mark.parametrize("args", [[], ["--slug"], ["--slug", "Shop"], ["--slug", "-shop"],
                                  ["--slug", "shop/x"]])
def test_a_missing_or_malformed_slug_exits_2_naming_slug(tmp_path, args):
    """REQ-050 AC1: rule 2a, `--slug` is required and a lower-case slug (Q-1073-1)."""
    root = imported(tmp_path)
    proc = source(root, "--version", "i1", *args)
    assert proc.returncode == 2
    assert "--slug" in proc.stderr
    assert not (root / "docs" / "sources").exists()


@pytest.mark.parametrize("args", [["--slug", "shop"], ["--slug", "shop", "--version", "v1"]])
def test_a_missing_or_malformed_version_exits_2_naming_version(tmp_path, args):
    """REQ-050 AC1: rule 2a, `--version` names an imported version `i<n>`."""
    root = imported(tmp_path)
    proc = source(root, *args)
    assert proc.returncode == 2
    assert "--version" in proc.stderr


# --- nothing is opened ----------------------------------------------------------------------------


def test_no_page_is_opened_and_no_connection_made(tmp_path, monkeypatch):
    """REQ-044: amendment 161 item 3 and rule 2a, pages are read as text (a socket guard)."""
    assert di is not None, "scripts/agk/design_import.py is missing"
    root = imported(tmp_path)

    def refuse(*args, **kwargs):
        raise AssertionError("the source opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    path = di.write_source(root, "i1", "shop")
    assert path == root / TARGET
    text = IMPORT.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:subprocess|webbrowser|socket|urllib|http\b|requests|ssl)\b",
        text,
        re.M,
    )


def test_source_text_returns_the_text_and_writes_nothing(tmp_path):
    """REQ-050 AC1: rule 2a, `source_text` only reads."""
    assert di is not None, "scripts/agk/design_import.py is missing"
    root = imported(tmp_path)
    before = tree(root)
    text = di.source_text(root, "i1", today="2026-11-12")
    assert text.splitlines()[3] == "Date: 2026-11-12"
    assert tree(root) == before
