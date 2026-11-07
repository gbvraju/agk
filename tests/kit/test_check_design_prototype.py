"""Tests of the prototype checks of `check_design.py` (SPEC-0037 rules 5, 7 and 8; REQ-044 AC4).

`design_prototype_check.version_problems(root, version)` checks one version folder
`docs/design/prototype/v<n>/` against `docs/design/inventory.md`: a page per screen and state marked
`yes` (an `n/a:` state needs none), links inside the folder, the kit's hashed runtime as the one
script, the folder's two stylesheets as the only `link` elements, colours from the tokens, the
standard's contrast in light and dark, no placeholder, data from the fixture set alone, the
accessibility basics and the layout basics; and it reads `screenshots/reflow.json`. Each failure
names the rule and the screen, never the value. One invented version folder under `tmp_path`
passes; each variant breaks one thing. Files only: no network, no model.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import design_standard  # noqa: E402

try:  # the module is new: before it exists every test fails rather than the collection
    import design_prototype_check  # noqa: E402
except ImportError:  # pragma: no cover - only before the build
    design_prototype_check = None  # type: ignore[assignment]

CHECK = SCRIPTS / "check_design.py"
DESIGN = SCRIPTS / "design.py"
KIT = KIT_ROOT / "kit" / "templates" / "design-prototype"
RUNTIME = KIT / "agk-prototype.js"
FIXTURES = KIT / "fixtures.json"
STANDARD = KIT_ROOT / "kit" / "templates" / "design-standard.css"
SIGNOFFS_TEMPLATE = KIT_ROOT / "kit" / "templates" / "design-signoffs.md"
VERSION = "v1"
REL = f"docs/design/prototype/{VERSION}"
HEAD = "0123456789abcdef0123456789abcdef01234567"

REQUIREMENTS = """# Requirements

### REQ-001 — A reader keeps a list of books

- Acceptance: AC1 a reader opens a book
- Status: planned
"""

NA = "n/a: the invented product has no such state"


def screen_section(name: str, links: str, yes: tuple[str, ...]) -> str:
    states = "".join(f"- State {s}: {'yes' if s in yes else NA}\n" for s in design_standard.STATES)
    return f"### {name}\n\n- Flow: Reading\n- Pattern: detail\n- Links to: {links}\n{states}"


INVENTORY = f"""# Design inventory

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: book-list, book-detail

## Screens

{screen_section("book-list", "book-detail", ("default", "empty"))}
{screen_section("book-detail", "book-list", ("default",))}"""

THEME_CSS = """/* theme.css of the invented version */
:root {
  --color-accent: #1a56db;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-accent: #8ab4ff;
  }
}
"""

PAGE = """<!doctype html>
<html lang="en" data-density="comfortable" data-align="start">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="standard.css">
<link rel="stylesheet" href="theme.css">
</head>
<body>
<div class="page stack">
<nav class="cluster" aria-label="States" id="states">
{bar}
</nav>
<main id="main" class="stack">
<h1>{title}</h1>
<h2>Find a book</h2>
<div class="field"><label for="q">Search for</label>
<input class="input" id="q" name="q" type="search"></div>
<p>Ask ada.fenwick@example.com or call +1 202 555 0143.</p>
<p><a href="{other}#demo">The Quiet Orchard</a></p>
</main>
<p><a href="index.html">All flows</a></p>
</div>
<script src="agk-prototype.js"></script>
</body>
</html>
"""

INDEX = PAGE.format(
    title="Prototype v1",
    bar='<a class="nav-link" href="book-list--default.html">Book list</a>',
    other="book-detail--default.html",
)


def page(screen: str, state: str, states: tuple[str, ...], other: str) -> str:
    bar = "\n".join(f'<a class="nav-link" href="{screen}--{s}.html">{s}</a>' for s in states)
    return PAGE.format(title=f"{screen}, {state}", bar=bar, other=other)


PAGES = {
    "book-list--default": page(
        "book-list", "default", ("default", "empty"), "book-detail--default.html"
    ),
    "book-list--empty": page(
        "book-list", "empty", ("default", "empty"), "book-detail--default.html"
    ),
    "book-detail--default": page("book-detail", "default", ("default",), "book-list--default.html"),
}


def put(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def version(root: Path) -> Path:
    """An invented project with one version folder that passes every check."""
    put(root, "docs/requirements.md", REQUIREMENTS)
    put(root, "docs/design/inventory.md", INVENTORY)
    folder = root / REL
    for name, text in PAGES.items():
        put(root, f"{REL}/{name}.html", text)
    put(root, f"{REL}/index.html", INDEX)
    put(root, f"{REL}/theme.css", THEME_CSS)
    (folder / "standard.css").write_bytes(STANDARD.read_bytes())
    (folder / "agk-prototype.js").write_bytes(RUNTIME.read_bytes())
    put(root, f"{REL}/README.md", "# Prototype v1\n")
    put(root, f"{REL}/demo.md", "# Demo paths of v1\n")
    return folder


def edit(folder: Path, name: str, old: str, new: str) -> None:
    path = folder / name
    text = path.read_text(encoding="utf-8")
    assert old in text, (name, old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def problems(root: Path) -> list[str]:
    return design_prototype_check.version_problems(root, VERSION)


def check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def fails(root: Path, rule: int, screen: str, *, value: str | None = None) -> str:
    """The one failure of ROOT: it names the rule and the screen, and never VALUE."""
    found = problems(root)
    prefix = f"rule {rule}: {REL}/{screen}: "
    assert any(p.startswith(prefix) for p in found), found
    proc = check(root)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"FAIL design: {prefix}" in proc.stdout, proc.stdout
    if value is not None:
        assert value not in proc.stdout + proc.stderr, proc.stdout
    return proc.stdout


# --- the folder that passes --------------------------------------------------------------------


def test_ac4_the_invented_version_passes(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (one fixture version that passes)."""
    version(tmp_path)
    assert problems(tmp_path) == []
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok design" in proc.stdout


def test_ac4_a_version_the_kit_writes_passes(tmp_path):
    """REQ-044 AC4: the folder that `design.py prototype` writes (#457) passes the check."""
    put(tmp_path, "docs/requirements.md", REQUIREMENTS)
    put(tmp_path, "docs/design/inventory.md", INVENTORY)
    sys.path.insert(0, str(SCRIPTS))
    import design_signoff

    put(tmp_path, "docs/design/signoffs.md", SIGNOFFS_TEMPLATE.read_text(encoding="utf-8"))
    row = (
        f"| inventory | - | {design_signoff.inventory_digest(tmp_path)} | {HEAD} | 2026-11-02 "
        "| https://example.com/review/1 |\n"
    )
    path = tmp_path / "docs/design/signoffs.md"
    path.write_text(path.read_text(encoding="utf-8") + row, encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(DESIGN), "prototype", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert problems(tmp_path) == []
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ac4_an_empty_version_folder_is_not_checked(tmp_path):
    """REQ-044 AC4: Q-458-3 (an empty `v<n>/`, as a theme's evidence target, holds no version)."""
    (tmp_path / REL).mkdir(parents=True)
    assert design_prototype_check.versions(tmp_path) == []
    version(tmp_path / "other")
    assert design_prototype_check.versions(tmp_path / "other") == [VERSION]


# --- rule 7: states and pages ------------------------------------------------------------------


def test_ac4_a_state_with_no_page_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a screen or state with no page)."""
    folder = version(tmp_path)
    (folder / "book-list--empty.html").unlink()
    edit(folder, "book-list--default.html", "book-list--empty.html", "book-list--default.html")
    out = fails(tmp_path, 7, "book-list--empty")
    assert "has no page" in out


def test_ac4_a_page_for_no_state_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a page for none); an `n/a:` state needs no page."""
    folder = version(tmp_path)
    put(tmp_path, f"{REL}/book-detail--loading.html", PAGES["book-detail--default"])
    fails(tmp_path, 7, "book-detail--loading")
    (folder / "book-detail--loading.html").unlink()
    assert problems(tmp_path) == []


def test_ac4_an_na_state_needs_no_page(tmp_path):
    """REQ-044 AC4: ADR-0252 decision 3, Q-457-5: an `n/a:` state has no page and passes."""
    version(tmp_path)
    assert not any("loading" in p for p in problems(tmp_path))


# --- rule 7: links -----------------------------------------------------------------------------


def test_ac4_a_broken_link_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a link that does not resolve to a file of the folder)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "book-detail--default.html#demo", "gone.html")
    out = fails(tmp_path, 7, "book-list--default", value="gone.html")
    assert "link" in out


def test_ac4_a_link_out_of_the_folder_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a link into another folder does not resolve)."""
    folder = version(tmp_path)
    put(tmp_path, "docs/design/prototype/other.html", INDEX)
    edit(folder, "book-list--default.html", "book-detail--default.html#demo", "../other.html")
    fails(tmp_path, 7, "book-list--default", value="other.html")


# --- rule 5: the runtime and the stylesheets ---------------------------------------------------


def test_ac4_an_inline_script_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (an inline script)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "</main>", "<script>let shelf = 1;</script></main>")
    fails(tmp_path, 5, "book-list--default", value="shelf")


def test_ac4_an_event_handler_attribute_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (an event handler attribute)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", '<main id="main"', '<main onclick="shelf()" id="main"')
    fails(tmp_path, 5, "book-list--default", value="shelf")


def test_ac4_a_javascript_link_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (a `javascript:` link)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", 'href="index.html"', 'href="javascript:shelf()"')
    fails(tmp_path, 5, "book-list--default", value="shelf")


def test_ac4_another_script_file_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (a script element other than the runtime's)."""
    folder = version(tmp_path)
    put(tmp_path, f"{REL}/shelf.js", "// invented\n")
    edit(folder, "book-list--default.html", 'src="agk-prototype.js"', 'src="shelf.js"')
    out = fails(tmp_path, 5, "book-list--default")
    assert "the page loads a script other than the kit's runtime" in out
    assert f"rule 5: {REL}/shelf.js: a script file other than the kit's runtime" in out


def test_ac4_the_runtime_not_at_the_end_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (one script element, at the end of the page)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "</body>", "<p>After the runtime.</p>\n</body>")
    fails(tmp_path, 5, "book-list--default")


def test_ac4_an_edited_runtime_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (a runtime file edited by one byte)."""
    folder = version(tmp_path)
    runtime = folder / "agk-prototype.js"
    runtime.write_bytes(runtime.read_bytes() + b" ")
    digest = hashlib.sha256(runtime.read_bytes()).hexdigest()
    out = fails(tmp_path, 5, "agk-prototype.js", value=digest)
    assert "hash" in out


def test_ac4_an_unknown_runtime_hash_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (a runtime whose hash is not a released one)."""
    folder = version(tmp_path)
    (folder / "agk-prototype.js").write_text("// agk-prototype 99\n", encoding="utf-8")
    fails(tmp_path, 5, "agk-prototype.js", value="agk-prototype 99")


def test_ac4_a_third_stylesheet_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (a `link` element other than the two stylesheets)."""
    folder = version(tmp_path)
    put(tmp_path, f"{REL}/shelf.css", "p { margin: 0; }\n")
    edit(
        folder,
        "book-list--default.html",
        "</head>",
        '<link rel="stylesheet" href="shelf.css">\n</head>',
    )
    fails(tmp_path, 5, "book-list--default", value="shelf.css")


def test_ac4_the_two_stylesheets_of_the_folder_pass(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (`standard.css` and `theme.css` of the folder pass)."""
    version(tmp_path)
    assert not any("stylesheet" in p or "link element" in p for p in problems(tmp_path))


def test_ac4_an_import_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (`@import`)."""
    folder = version(tmp_path)
    with (folder / "theme.css").open("a", encoding="utf-8") as handle:
        handle.write('@import "shelf.css";\n')
    fails(tmp_path, 5, "theme.css", value="shelf.css")


def test_ac4_a_url_outside_the_folder_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (`url()` of a file outside the folder)."""
    folder = version(tmp_path)
    with (folder / "theme.css").open("a", encoding="utf-8") as handle:
        handle.write(".shelf { background-image: url(../shelf.png); }\n")
    fails(tmp_path, 5, "theme.css", value="shelf.png")


# --- rule 7: colours and contrast --------------------------------------------------------------


def test_ac4_a_colour_outside_the_tokens_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a colour outside the tokens)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "<h2>", '<h2 style="color: #a1b2c3">')
    out = fails(tmp_path, 7, "book-list--default", value="#a1b2c3")
    assert "colour" in out


def test_ac4_a_colour_outside_the_tokens_of_the_theme_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a colour in `theme.css` outside its token rules)."""
    folder = version(tmp_path)
    with (folder / "theme.css").open("a", encoding="utf-8") as handle:
        handle.write(".shelf { color: #a1b2c3; }\n")
    fails(tmp_path, 7, "theme.css", value="#a1b2c3")


def test_ac4_a_low_contrast_in_dark_only_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a contrast below 4.5:1, in dark only)."""
    folder = version(tmp_path)
    edit(folder, "theme.css", "    --color-accent: #8ab4ff;", "    --color-text: #2a2f36;")
    out = fails(tmp_path, 7, "theme.css", value="#2a2f36")
    assert "contrast" in out
    assert "dark" in out
    assert "in light" not in out


def test_ac4_a_low_contrast_for_a_ui_part_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (3:1 for UI parts: the border on the background)."""
    folder = version(tmp_path)
    edit(folder, "theme.css", "  --color-accent: #1a56db;", "  --color-border: #eeeeee;")
    out = fails(tmp_path, 7, "theme.css", value="#eeeeee")
    assert "3:1" in out


# --- rule 7: placeholders and data -------------------------------------------------------------


@pytest.mark.parametrize("text", ["[Book title]", "Lorem ipsum dolor", "TODO later", "TBD"])
def test_ac4_a_placeholder_fails(tmp_path, text):
    """REQ-044 AC4: SPEC-0037 rule 7 (a placeholder)."""
    folder = version(tmp_path)
    edit(folder, "book-list--empty.html", "The Quiet Orchard", text)
    out = fails(tmp_path, 7, "book-list--empty", value=text)
    assert "placeholder" in out


def test_ac4_an_email_outside_the_fixtures_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rules 6 and 7 (an email address outside the fixture set)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "ada.fenwick@example.com", "shelf@example.net")
    out = fails(tmp_path, 7, "book-list--default", value="shelf@example.net")
    assert "fixture" in out


def test_ac4_a_phone_outside_the_fixtures_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rules 6 and 7 (a phone number outside the fixture set)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "+1 202 555 0143", "+1 202 555 0199")
    fails(tmp_path, 7, "book-list--default", value="0199")


def test_ac4_a_link_host_outside_the_fixtures_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rules 6 and 7 (a link host outside the fixture set)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "Ask ", "See https://shelf.example.net/a or ask ")
    fails(tmp_path, 7, "book-list--default", value="shelf.example.net")


# --- rule 7: accessibility and layout ----------------------------------------------------------


def test_ac4_a_control_without_a_label_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a form control without a label)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", '<label for="q">Search for</label>', "")
    out = fails(tmp_path, 7, "book-list--default")
    assert "label" in out


def test_ac4_a_control_inside_its_label_passes(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a control wrapped in its label has a label)."""
    folder = version(tmp_path)
    edit(
        folder,
        "book-list--default.html",
        '<label for="q">Search for</label>\n<input class="input" id="q" name="q" type="search">',
        '<label>Search for <input class="input" name="q" type="search"></label>',
    )
    assert problems(tmp_path) == []


def test_ac4_an_image_without_alt_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (an image without alt text)."""
    folder = version(tmp_path)
    put(tmp_path, f"{REL}/cover.png", "invented")
    edit(folder, "book-list--default.html", "<h2>", '<img src="cover.png">\n<h2>')
    fails(tmp_path, 7, "book-list--default")


def test_ac4_a_skipped_heading_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a skipped heading level)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "<h2>Find a book</h2>", "<h3>Find a book</h3>")
    out = fails(tmp_path, 7, "book-list--default")
    assert "heading" in out


def test_ac4_two_h1_fail(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (not exactly one `h1`)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "<h2>Find a book</h2>", "<h1>Find a book</h1>")
    fails(tmp_path, 7, "book-list--default")


def test_ac4_no_lang_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a page without `lang`)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", ' lang="en"', "")
    fails(tmp_path, 7, "book-list--default")


def test_ac4_a_positive_tabindex_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a positive `tabindex`)."""
    folder = version(tmp_path)
    edit(folder, "book-list--default.html", "<h2>", '<h2 tabindex="3">')
    fails(tmp_path, 7, "book-list--default")


def test_ac4_no_focus_visible_style_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (no `:focus-visible` style)."""
    folder = version(tmp_path)
    css = (folder / "standard.css").read_text(encoding="utf-8")
    (folder / "standard.css").write_text(css.replace(":focus-visible", ":focus"), encoding="utf-8")
    fails(tmp_path, 7, "book-list--default")


def test_ac4_no_viewport_line_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a page without the viewport line)."""
    folder = version(tmp_path)
    edit(
        folder,
        "book-list--default.html",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        "",
    )
    fails(tmp_path, 7, "book-list--default")


def test_ac4_a_fixed_width_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a fixed width over 360 px outside a media query)."""
    folder = version(tmp_path)
    edit(
        folder,
        "book-list--default.html",
        "</head>",
        "<style>.shelf { width: 812px; }</style>\n</head>",
    )
    out = fails(tmp_path, 7, "book-list--default", value="812")
    assert "360 px" in out


def test_ac4_a_fixed_width_inside_a_media_query_passes(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 7 (a wide width inside a media query is not a fixed width)."""
    folder = version(tmp_path)
    edit(
        folder,
        "book-list--default.html",
        "</head>",
        "<style>@media (min-width: 900px) { .shelf { width: 812px; } }</style>\n</head>",
    )
    assert problems(tmp_path) == []


# --- rule 8: reflow ----------------------------------------------------------------------------


def reflow(folder: Path, result_of) -> None:
    entries = [
        {
            "page": f"{name}.html",
            "breakpoint": width,
            "mode": mode,
            "result": result_of(name, width),
        }
        for name in PAGES
        for width in design_standard.BREAKPOINTS
        for mode in ("light", "dark")
    ]
    put(folder, "screenshots/reflow.json", json.dumps({"entries": entries}))


def test_ac4_a_sideways_entry_fails_naming_the_breakpoint(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 8 (a page that scrolls sideways at a breakpoint)."""
    folder = version(tmp_path)
    reflow(
        folder,
        lambda name, width: "sideways" if (name, width) == ("book-list--empty", 360) else "ok",
    )
    found = problems(tmp_path)
    line = f"rule 8: {VERSION}/book-list--empty: the page scrolls sideways at 360 px"
    assert line in found, found
    assert len([p for p in found if p.startswith("rule 8")]) == 1
    proc = check(tmp_path)
    assert proc.returncode == 1
    assert f"FAIL design: {line}" in proc.stdout


def test_ac4_all_ok_reflow_prints_no_not_run(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 8 (every entry ok: no `not run` line)."""
    folder = version(tmp_path)
    reflow(folder, lambda name, width: "ok")
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert "reflow not run" not in proc.stdout


def test_ac4_no_reflow_file_reads_not_run(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 8 (no `reflow.json` reads not run, never ok, fails nothing)."""
    version(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert f"design: reflow not run ({VERSION})" in proc.stdout


def test_ac4_a_not_run_entry_reads_not_run(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 8 (any `not run` entry reads not run)."""
    folder = version(tmp_path)
    reflow(folder, lambda name, width: "not run" if width == 1440 else "ok")
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert f"design: reflow not run ({VERSION})" in proc.stdout


def test_ac4_an_unreadable_reflow_file_fails(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 8 (a `reflow.json` that is not the record fails, never ok)."""
    folder = version(tmp_path)
    put(folder, "screenshots/reflow.json", "{not json")
    found = problems(tmp_path)
    assert any(p.startswith(f"rule 8: {VERSION}/screenshots/reflow.json: ") for p in found), found


# --- the mockup folders stay as they were -------------------------------------------------------

MOCKUP = "docs/design/mockups/2026-10-24-home"
MOCKUP_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Home</title>
<style>
:root { --bg: #ffffff; --fg: #111111; --muted: #555555; --accent: #1a56db; --accent-fg: #ffffff; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #101418; --fg: #f2f2f2; --muted: #b0b0b0; --accent: #8ab4ff; --accent-fg: #101418; }
}
body { background: var(--bg); color: var(--fg); }
</style>
</head>
<body>
<h1>Home</h1>
</body>
</html>
"""


def mockup(root: Path, extra: str = "") -> None:
    put(root, f"{MOCKUP}/index.html", MOCKUP_PAGE.replace("</body>", extra + "</body>"))
    put(root, f"{MOCKUP}/README.md", "# Home\n")


def test_ac4_a_mockup_folder_without_script_or_link_passes(tmp_path):
    """REQ-044 AC4: SPEC-0037 rule 5 (a mockup folder is checked as before)."""
    mockup(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize(
    "extra",
    ['<script src="agk-prototype.js"></script>\n', '<link rel="stylesheet" href="standard.css">\n'],
)
def test_ac4_a_mockup_folder_with_a_script_or_a_link_still_fails(tmp_path, extra):
    """REQ-044 AC4: SPEC-0037 rule 5 (a mockup folder allows no script and no `link`)."""
    mockup(tmp_path, extra)
    proc = check(tmp_path)
    assert proc.returncode == 1, proc.stdout
    assert f"FAIL design: rule 7: {MOCKUP}/index.html: " in proc.stdout


# --- the constants equal the kit's files -------------------------------------------------------


def test_ac4_the_kit_runtime_hashes_to_the_newest_released_hash():
    """REQ-044 AC4: SPEC-0037 rule 5 and Q-S0037-5 (the kit's runtime is the newest entry)."""
    digest = hashlib.sha256(RUNTIME.read_bytes()).hexdigest()
    assert design_prototype_check.RUNTIME_HASHES[-1] == digest
    assert len(set(design_prototype_check.RUNTIME_HASHES)) == len(
        design_prototype_check.RUNTIME_HASHES
    )


def strings(value) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    return [str(value)]


def test_ac4_the_fixture_constants_equal_the_kits_fixture_set():
    """REQ-044 AC4: SPEC-0037 rule 6 and Q-457-3 (the installed check embeds `fixtures.json`)."""
    known = strings(json.loads(FIXTURES.read_text(encoding="utf-8")))
    emails = {e.lower() for v in known for e in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", v)}
    hosts = {
        h.lower()
        for v in known
        for h in re.findall(r"(?i)\b[a-z][a-z0-9+.-]*://([^/\s\"'<>:]+)", v)
    }
    phones = {p for v in known for p in re.findall(r"\+\d[\d ()-]{6,}\d", v)}
    assert emails and hosts and phones
    assert set(design_prototype_check.FIXTURE_EMAILS) == emails
    assert set(design_prototype_check.FIXTURE_HOSTS) == hosts
    assert set(design_prototype_check.FIXTURE_PHONES) == phones


def test_ac4_the_check_module_reads_no_network_and_no_kit_file():
    """REQ-044 AC4: SPEC-0037 rule 13 (files only; the installed check never reads the kit)."""
    text = (SCRIPTS / "design_prototype_check.py").read_text(encoding="utf-8")
    for name in ("socket", "urllib", "http.client", "requests", "subprocess", "kit/templates"):
        assert name not in text, name


def test_ac4_the_module_is_installed_verbatim():
    """REQ-044 AC4: SPEC-0037 rule 14 (a module the installed check imports is in `verbatim`)."""
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/design_prototype_check.py" in manifest["verbatim"]
