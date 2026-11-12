"""Tests of the shared components of an imported prototype (SPEC-0037 rule 16 as amendment 164
item 3 proposes, with its Q-1089-5 reading; REQ-044, REQ-050; brief #1091, build (q), ADR-0463).

`design_import.py components --version i<n> --slug <slug>` writes once
`docs/sources/<slug>-components-i<n>.md`: rule 1's header (`Source: shared components of imported
prototype i<n>`, `Kind: design`, `Version: i<n> <digest>`, `Date:`), one blank line, then one
`## <name>` heading per element structure (tag, class names as written, child tags in order) that
two or more different mapped pages share, the element having a child element or a class and not
lying inside a listed structure on exactly the same pages, in the order of first appearance, with
one `structure:` line and one `- <screen>/<state>` line per mapped row it appears on. Pages are read
as text only: no page is opened, no network. Invented pages only (`example.com`), in `tmp_path`.
"""

from __future__ import annotations

import json
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
TARGET = "docs/sources/shop-components-i1.md"

NAV = (
    '<nav class="app-nav"><a href="orders.html">Zulu orders</a><a href="items.html">Zulu items</a>'
    '<a href="help.html">Zulu help</a><ul><li><a href="more.html">Zulu more</a></li></ul>'
    '<span class="badge">7</span></nav>'
)


def table(rows: int) -> str:
    body = "".join(f"<tr><td>Kilo row {n}</td></tr>" for n in range(rows))
    return f'<table class="results"><thead><tr><th>Kilo head</th></tr></thead><tbody>{body}</tbody></table>'


PAGES = {
    "orders.html": (
        "<!doctype html><html><head><title>Yankee orders</title>"
        '<link rel="stylesheet" href="app.css"></head><body>'
        f"{NAV}<main><h1>Yankee orders</h1>{table(1)}"
        '<div class="only-here"><p>Only here</p></div><span>loose</span></main></body></html>\n'
    ),
    "items.html": (
        "<!doctype html><html><head><title>Yankee items</title></head><body>"
        f"{NAV}<main><h1>Yankee items</h1>{table(2)}<span>loose</span></main></body></html>\n"
    ),
    "help.html": (
        "<!doctype html><html><head><title>Yankee help</title></head><body>"
        f'<main><h1>Yankee help</h1>{table(3)}<span class="badge">1</span>'
        '<div class="card"><p>Twice here</p></div><div class="card"><p>Twice here</p></div>'
        '<div class="legacy"><p>Old block</p></div></main></body></html>\n'
    ),
    "old.html": (
        f'<!doctype html><body>{NAV}<div class="legacy"><p>Old block</p></div></body>\n'
    ),
}
ROWS = [
    "orders.html -> orders/default",
    "items.html -> items/default",
    "help.html -> help/default",
    "img/sketch.png -> orders/empty",
    "old.html -> out: the customer replaced it",
]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, *args], capture_output=True, text=True, check=False
    )


def inventory(rows: list[str]) -> str:
    states: dict[str, list[str]] = {}
    for row in rows:
        target = row.split(" -> ", 1)[1]
        if not target.startswith("out:"):
            screen, state = target.split("/")
            states.setdefault(screen, []).append(state)
    out = ["# Design inventory", "", "## Screens", ""]
    for screen, names in states.items():
        out += [f"### {screen}", "", "- Flow: see it"] + [f"- State {s}: yes" for s in names] + [""]
    return "\n".join(out)


def imported(
    tmp_path: Path, pages: dict[str, str] | None = None, rows: list[str] | None = None
) -> Path:
    """A project with the fixture prototype imported as i1 and mapped."""
    pages = PAGES if pages is None else pages
    rows = ROWS if rows is None else rows
    root = tmp_path / "proj"
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "inventory.md").write_text(inventory(rows), encoding="utf-8")
    customer = tmp_path / "customer"
    (customer / "img").mkdir(parents=True)
    for name, text in pages.items():
        (customer / name).write_text(text, encoding="utf-8")
    if any(row.startswith("img/sketch.png") for row in rows):
        (customer / "img" / "sketch.png").write_bytes(b"\x89PNG\r\n\x1a\n sketch")
    (customer / "app.css").write_text(".app-nav { display: flex }\n", encoding="utf-8")
    proc = run(str(DESIGN), "import", str(customer), "--root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (root / I1 / "map.md").write_text(
        "# Screen map of i1\n\n" + "".join(f"- {row}\n" for row in rows), encoding="utf-8"
    )
    return root


def components(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return run(str(IMPORT), "components", "--root", str(root), *extra)


def written(root: Path) -> str:
    proc = components(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return (root / TARGET).read_text(encoding="utf-8")


def blocks(text: str) -> dict[str, list[str]]:
    """{heading: its non-empty lines}, in the file's order."""
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:]
            out[current] = []
        elif current is not None and line:
            out[current].append(line)
    return out


def tree(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    }


# --- the file -------------------------------------------------------------------------------------


def test_the_header_is_rule_1s_four_lines_then_one_blank_line(tmp_path):
    """REQ-050 AC1: rule 16, the header of SPEC-0043 rule 1 (`Kind: design`, the version's digest)."""
    root = imported(tmp_path)
    text = written(root)
    digest = json.loads((root / I1 / "manifest.json").read_text())["digest"]
    lines = text.splitlines()
    assert lines[0] == "Source: shared components of imported prototype i1"
    assert lines[1] == "Kind: design"
    assert lines[2] == f"Version: i1 {digest}"
    assert re.fullmatch(r"Date: \d{4}-\d{2}-\d{2}", lines[3])
    assert lines[4] == ""
    assert check_plan.header_problems(text) == []
    assert check_plan.source_problems(root) == []


def test_the_repeated_structures_with_their_screens_in_first_appearance_order(tmp_path):
    """REQ-044: rule 16, a nav on two pages and a table on three, each with its screens."""
    assert blocks(written(imported(tmp_path))) == {
        "app-nav": [
            "structure: nav.app-nav: a a a ul span",
            "- orders/default",
            "- items/default",
        ],
        "badge": [
            "structure: span.badge:",
            "- orders/default",
            "- items/default",
            "- help/default",
        ],
        "results": [
            "structure: table.results: thead tbody",
            "- orders/default",
            "- items/default",
            "- help/default",
        ],
    }


def test_one_page_structures_classless_leaves_and_nested_repeats_are_not_listed(tmp_path):
    """REQ-044: rule 16 with Q-1089-5, the `ul`, `li`, `thead` and `tr` inside a listed structure on
    the same pages, a class-less leaf, a structure on one page and one repeated on one page only."""
    text = written(imported(tmp_path))
    for name in ("only-here", "card", "legacy", "span", "ul", "li", "thead", "tr", "main", "body"):
        assert not any(h == name or h.endswith(">" + name) for h in check_plan.headings(text)), name


def test_a_structure_inside_a_listed_one_on_other_pages_is_listed(tmp_path):
    """REQ-044: rule 16 with Q-1089-5, the badge is inside the nav on two pages and alone on a third."""
    assert "badge" in check_plan.headings(written(imported(tmp_path)))


def test_no_out_row_and_no_picture_page_is_read(tmp_path):
    """REQ-044: rule 16, a mapped page is a page of a row that is not `out:`."""
    text = written(imported(tmp_path))
    assert "legacy" not in text  # on help.html and on old.html, which is out:
    assert "orders/empty" not in text and "sketch" not in text


def test_no_text_of_a_page_is_in_the_file(tmp_path):
    """REQ-044: rule 13 as item 3 extends it, tag, class, screen and state names only."""
    text = written(imported(tmp_path))
    for words in ("Zulu", "Kilo", "Yankee", "Only here", "Twice here", "loose", "example", "7"):
        assert words not in text.split("\n", 4)[4]


def test_names_are_the_tag_path_without_a_class_and_get_a_number_when_used(tmp_path):
    """REQ-044: rule 16, the first class name, else the tag path from `body` joined with `>`, never
    `/`; a name already used gets `-2`, `-3`."""
    page = (
        "<!doctype html><body><main><section><h2>A</h2><p>B</p></section>"
        '<div class="card"><p>C</p></div><div class="card"><h3>D</h3></div>'
        '<div class="w-1/2 box"><p>E</p></div></main></body>\n'
    )
    rows = ["one.html -> one/default", "two.html -> two/default"]
    other = page.replace("</main>", "<hr></main>")  # the two `main` elements differ
    text = written(imported(tmp_path, {"one.html": page, "two.html": other}, rows))
    found = check_plan.headings(text)
    assert found == ["main>section", "card", "card-2", "main>div"]
    assert not any("/" in heading for heading in found)
    assert blocks(text)["main>div"][0] == "structure: div.w-1/2.box: p"


def test_one_none_line_when_nothing_repeats(tmp_path):
    """REQ-044: rule 16, the header and one `none:` line."""
    rows = ["one.html -> one/default", "two.html -> two/default"]
    pages = {
        "one.html": '<body><div class="a"><p>x</p></div></body>\n',
        "two.html": '<body><div class="b"><p>x</p></div></body>\n',
    }
    lines = written(imported(tmp_path, pages, rows)).splitlines()
    assert lines[4:] == ["", "none: no element structure appears on two or more mapped pages"]


def test_the_text_is_the_same_on_every_run(tmp_path):
    """REQ-044: rule 16, the output is stable."""
    assert di is not None, "scripts/agk/design_import.py is missing"
    root = imported(tmp_path)
    first = di.components_text(root, "i1", today="2026-11-12")
    assert di.components_text(root, "i1", today="2026-11-12") == first


def test_the_command_prints_the_file_it_wrote(tmp_path):
    """REQ-044: rule 16, one line naming the file and the count of structures."""
    root = imported(tmp_path)
    proc = components(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == f"wrote {TARGET} (3 structures)\n"


# --- the refusals ---------------------------------------------------------------------------------


def test_a_second_run_refuses_the_existing_file_and_leaves_it_byte_for_byte(tmp_path):
    """REQ-044: rule 16, never over an existing file."""
    root = imported(tmp_path)
    written(root)
    before = (root / TARGET).read_bytes()
    proc = components(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 1
    assert "rule 16" in proc.stdout and TARGET in proc.stdout
    assert (root / TARGET).read_bytes() == before


def test_a_version_not_on_the_branch_is_refused_writing_nothing(tmp_path):
    """REQ-044: rule 16, the version must exist."""
    root = imported(tmp_path)
    proc = components(root, "--version", "i2", "--slug", "shop")
    assert proc.returncode == 1
    assert "rule 16" in proc.stdout and "i2" in proc.stdout
    assert not (root / "docs" / "sources").exists()


@pytest.mark.parametrize("change", ["missing-file", "unmapped-page"])
def test_a_version_whose_import_or_map_check_fails_is_refused_writing_nothing(tmp_path, change):
    """REQ-044: rule 16, a version with an import or map problem is refused."""
    if change == "unmapped-page":
        root = imported(tmp_path, rows=ROWS[:2] + ROWS[3:])
    else:
        root = imported(tmp_path)
        (root / I1 / "files" / "help.html").unlink()
    before = tree(root)
    proc = components(root, "--version", "i1", "--slug", "shop")
    assert proc.returncode == 1
    assert "rule 16" in proc.stdout and "i1" in proc.stdout
    assert tree(root) == before


@pytest.mark.parametrize("args", [[], ["--slug"], ["--slug", "Shop"], ["--slug", "shop/x"]])
def test_a_missing_or_malformed_slug_exits_2_naming_slug(tmp_path, args):
    """REQ-044: rule 16, `--slug` is required and a lower-case slug."""
    root = imported(tmp_path)
    proc = components(root, "--version", "i1", *args)
    assert proc.returncode == 2
    assert "--slug" in proc.stderr
    assert not (root / "docs" / "sources").exists()


def test_a_malformed_version_exits_2_and_an_unknown_command_prints_both(tmp_path):
    """REQ-044: rule 16, `--version` names `i<n>`; the usage names both commands."""
    root = imported(tmp_path)
    proc = components(root, "--slug", "shop", "--version", "v1")
    assert proc.returncode == 2 and "--version" in proc.stderr
    proc = run(str(IMPORT), "parts")
    assert proc.returncode == 2
    assert "components" in proc.stderr and "source" in proc.stderr


# --- nothing is opened ----------------------------------------------------------------------------


def test_no_page_is_opened_and_no_connection_made(tmp_path, monkeypatch):
    """REQ-044: amendment 161 item 3 and rule 16, pages are read as text (a socket guard)."""
    assert di is not None, "scripts/agk/design_import.py is missing"
    root = imported(tmp_path)

    def refuse(*args, **kwargs):
        raise AssertionError("the command opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    assert di.write_components(root, "i1", "shop") == root / TARGET
    text = IMPORT.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:subprocess|webbrowser|socket|urllib|http\b|requests|ssl)\b",
        text,
        re.M,
    )
