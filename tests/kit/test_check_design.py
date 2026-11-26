"""Tests of `check_design.py` (SPEC-0029 rule 7; REQ-036 AC6 and AC7).

The check reads `docs/design/theme.md` and `docs/design/mockups/<date>-<name>/` and fails a mockup
with a script, an external request, a colour outside the token block or a contrast under 4.5:1. A
theme whose evidence folder has no approval line reads "not approved yet"; a placeholder brand is
reported as at risk. Both are information, not failures. No network, no model.
"""

from __future__ import annotations

import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]


def clean_env():
    return {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}


SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_design.py"
FOLDER = "2026-10-24-home"
LIGHT = """  --bg: #ffffff;
  --fg: #111111;
  --muted: #555555;
  --accent: #1a56db;
  --accent-fg: #ffffff;
"""
DARK = """    --bg: #101418;
    --fg: #f2f2f2;
    --muted: #b0b0b0;
    --accent: #8ab4ff;
    --accent-fg: #101418;
"""
TOKENS = f""":root {{
{LIGHT}}}
@media (prefers-color-scheme: dark) {{
  :root {{
{DARK}  }}
}}
"""
THEME = f"""# Theme

## Brand

- name: Reading List — source: the owner's brief of 2026-10-20
- primary: #1a56db — source: the brand guide, page 2
- font: system-ui — source: the owner's brief of 2026-10-20

## Tokens

```css
{TOKENS}```

## Contrast

- --fg on --bg
- --muted on --bg
- --accent-fg on --accent

## Rules

One token block, light and dark, contrast 4.5:1 by a computed test, status as word plus colour,
native controls, 44 px targets, 360 px to wide.

## Evidence

Evidence: docs/design/mockups/{FOLDER}/
"""
HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Home [page title]</title>
<style>
{TOKENS}body {{ font-family: system-ui; background: var(--bg); color: var(--fg); margin: 0; }}
a, button {{ min-height: 44px; color: var(--accent); border: 1px solid var(--muted); }}
.note {{ color: var(--muted); }}
</style>
</head>
<body>
<h1>[Product name]</h1>
<p class="note">[One sentence about what this is for.]</p>
<button type="button">[Primary action]</button>
<a href="#top">Top</a>
</body>
</html>
"""
APPROVED = "# Mockup\n\nApproved by Sam Owner on 2026-10-24\n"
NOT_YET = "# Mockup\n\nApproved: not yet\n"


def put(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(root, theme=THEME, html=HTML, readme=APPROVED, folder=FOLDER):
    put(root, "docs/design/theme.md", theme)
    put(root, f"docs/design/mockups/{folder}/index.html", html)
    put(root, f"docs/design/mockups/{folder}/README.md", readme)
    return root


def check(root):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def failed(root, needle):
    proc = check(root)
    assert proc.returncode == 1, proc.stdout
    assert needle in proc.stdout, proc.stdout
    assert "rule 7" in proc.stdout
    return proc.stdout


# --- the good record, and nothing to check -----------------------------------------------------


def test_ac6_no_design_record_is_nothing_to_check(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (a project that never ran /agk:design passes)."""
    proc = check(tmp_path)
    assert (proc.returncode, proc.stdout) == (0, "ok design (no design record)\n")


def test_ac6_an_approved_theme_with_a_clean_mockup_passes(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (the good record)."""
    proc = check(project(tmp_path))
    assert (proc.returncode, proc.stdout) == (0, "ok design\n")


# --- the mockup --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "needle"),
    [
        (lambda h: h.replace("</body>", "<script>alert(1)</script></body>"), "script"),
        (lambda h: h.replace("<button ", '<button onclick="x()" '), "script"),
        (lambda h: h.replace('href="#top"', 'href="javascript:void(0)"'), "script"),
        (
            lambda h: h.replace("</body>", '<img src="https://cdn.example.org/a.png"></body>'),
            "external",
        ),
        (lambda h: h.replace("</body>", '<img src="//cdn.example.org/a.png"></body>'), "external"),
        (lambda h: h.replace("<style>", "<style>\n@import 'other.css';"), "external"),
        (lambda h: h.replace("</head>", '<link rel="stylesheet" href="s.css"></head>'), "external"),
        (
            lambda h: h.replace("margin: 0;", "background-image: url(//x.example.org/a.png);"),
            "external",
        ),
        (lambda h: h.replace("</body>", '<iframe src="about:blank"></iframe></body>'), "external"),
    ],
)
def test_ac6_a_mockup_with_a_script_or_an_external_request_fails(tmp_path, change, needle):
    """REQ-036 AC6: SPEC-0029 rule 7 (no script, no external request) and no value printed."""
    project(tmp_path, html=change(HTML))
    out = failed(tmp_path, needle)
    assert "example.org" not in out and "alert" not in out and "javascript" not in out


@pytest.mark.parametrize(
    "outside",
    [
        "p { color: #ff0000; }",
        "p { color: #f00; }",
        "p { background: rgb(1, 2, 3); }",
        "p { border-color: hsl(10 20% 30%); }",
        "p { color: red; }",
        "p { box-shadow: 0 0 2px black; }",
    ],
)
def test_ac6_a_colour_outside_the_token_block_fails(tmp_path, outside):
    """REQ-036 AC6: SPEC-0029 rule 7 (every colour is a token)."""
    project(tmp_path, html=HTML.replace("</style>", f"{outside}\n</style>"))
    out = failed(tmp_path, "colour")
    assert "ff0000" not in out and "rgb(" not in out


def test_ac6_colour_words_that_are_not_colours_pass(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (`inherit`, `transparent`, `currentColor` and `var()` pass)."""
    css = "p { color: inherit; background: transparent; border-color: currentColor; }"
    project(tmp_path, html=HTML.replace("</style>", f"{css}\n</style>"))
    assert check(tmp_path).stdout == "ok design\n"


SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
    'width="24" height="24" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none"/></svg>'
)


def test_ac6_an_inline_svg_and_its_namespace_declarations_make_no_request(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (only `xmlns` values are ignored; an SVG asks for nothing)."""
    project(tmp_path, html=HTML.replace("<h1>", f"{SVG}<h1>"))
    assert check(tmp_path).stdout == "ok design\n"


def test_ac6_a_namespace_declaration_does_not_hide_a_real_request(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (the same page with a remote image still fails)."""
    remote = '<img src="https://cdn.example.org/a.png">'
    project(tmp_path, html=HTML.replace("<h1>", f"{SVG}{remote}<h1>"))
    out = failed(tmp_path, "external")
    assert "example.org" not in out
    project(tmp_path, html=HTML.replace("<h1>", '<svg data-x="http://a.example.org/"></svg><h1>'))
    failed(tmp_path, "external")


@pytest.mark.parametrize(
    "selector", ["#feed", "#add", "a:hover, #feed", "p#bad:hover", ".cafe > #dad"]
)
def test_ac6_an_id_selector_made_of_hex_letters_is_not_a_colour(tmp_path, selector):
    """REQ-036 AC6: SPEC-0029 rule 7 (the colour scan reads declaration values, not selectors)."""
    css = selector + " { color: var(--muted); }"
    project(tmp_path, html=HTML.replace("</style>", f"{css}\n</style>"))
    assert check(tmp_path).stdout == "ok design\n"


def test_ac6_a_colour_inside_a_media_block_still_fails(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (rules nested in an at-rule are scanned too)."""
    css = "@media (min-width: 40em) { #feed { color: #ff0000; } }"
    project(tmp_path, html=HTML.replace("</style>", f"{css}\n</style>"))
    failed(tmp_path, "colour")
    css = "#feed { color: var(--fg); }\n"
    project(
        tmp_path,
        html=HTML.replace("</style>", css + "</style>").replace(
            ">Top<", ' style="color: #123456">Top<'
        ),
    )
    failed(tmp_path, "colour")


def test_ac6_a_mockup_with_two_style_blocks_or_two_token_blocks_fails(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (the tokens are one CSS block)."""
    project(tmp_path, html=HTML.replace("</head>", "<style>p { margin: 0; }</style></head>"))
    failed(tmp_path, "one token block")
    again = HTML.replace("</style>", ":root { --extra: #000000; }\n</style>")
    project(tmp_path, html=again)
    failed(tmp_path, "one token block")


def test_ac6_a_mockup_without_light_and_dark_tokens_fails(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (light and dark)."""
    html = HTML.replace(f"@media (prefers-color-scheme: dark) {{\n  :root {{\n{DARK}  }}\n}}\n", "")
    project(tmp_path, html=html)
    failed(tmp_path, "light and dark")


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_ac6_a_contrast_under_4_5_to_1_fails_and_names_the_pair_not_the_values(tmp_path, mode):
    """REQ-036 AC6: SPEC-0029 rule 7 (contrast is computed, in both modes)."""
    html = HTML.replace(
        "--muted: #555555" if mode == "light" else "--muted: #b0b0b0",
        "--muted: #999999" if mode == "light" else "--muted: #333333",
    )
    project(tmp_path, html=html)
    out = failed(tmp_path, "contrast")
    assert "--muted on --bg" in out and mode in out
    assert "999999" not in out and "333333" not in out


def test_ac6_the_contrast_is_the_wcag_ratio(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (black on white is 21, #777 on white is just under 4.5)."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import check_design

    assert round(check_design.contrast("#000000", "#ffffff"), 2) == 21.0
    assert round(check_design.contrast("#ffffff", "#ffffff"), 2) == 1.0
    assert (
        check_design.contrast("#767676", "#ffffff")
        >= 4.5
        > check_design.contrast("#777777", "#ffffff")
    )
    assert check_design.contrast("#fff", "#000") == check_design.contrast("#ffffff", "#000000")


def test_ac6_a_mockup_folder_without_its_files_or_with_a_bad_name_fails(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (`<date>-<name>`, `index.html` and `README.md`)."""
    project(tmp_path)
    (tmp_path / "docs/design/mockups" / FOLDER / "README.md").unlink()
    failed(tmp_path, "README")
    project(tmp_path, folder="home")
    failed(tmp_path, "folder name")


# --- the theme ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "needle"),
    [
        (
            lambda t: t.replace("```css", "```css\n:root { --x: #000000; }\n```\n\n```css", 1),
            "one token block",
        ),
        (lambda t: t.replace("--bg: #ffffff", "--bg: white"), "hex"),
        (lambda t: t.replace("--muted: #555555", "--muted: #aaaaaa"), "contrast"),
        (lambda t: t.replace(" — source: the brand guide, page 2", ""), "source"),
        (lambda t: t.replace("## Brand", "## Colours"), "Brand"),
        (lambda t: t.replace("## Evidence", "## Proof"), "Evidence"),
        (lambda t: t.replace("- --fg on --bg", "- --nothing on --bg"), "token"),
    ],
)
def test_ac6_a_theme_that_breaks_its_shape_fails_naming_the_rule(tmp_path, change, needle):
    """REQ-036 AC6: SPEC-0029 rule 7 (one token block, hex tokens, contrast, a source each)."""
    project(tmp_path, theme=change(THEME))
    failed(tmp_path, needle)


def test_ac6_the_evidence_must_point_to_a_mockup_folder_that_exists(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (the evidence line is a path to a folder)."""
    project(tmp_path, theme=THEME.replace(FOLDER, "2026-01-01-missing"))
    failed(tmp_path, "evidence")
    project(tmp_path, theme=THEME.replace(f"docs/design/mockups/{FOLDER}/", "../../etc"))
    failed(tmp_path, "evidence")


# --- approval and the placeholder brand --------------------------------------------------------


@pytest.mark.parametrize(
    "readme",
    [
        NOT_YET,
        "# Mockup\n",
        "# Mockup\n\nApproved by Sam on someday\n",
        "# Mockup\n\nApproved by  on 2026-10-24\n",
    ],
)
def test_ac7_an_evidence_folder_without_an_approval_line_reads_not_approved_yet(tmp_path, readme):
    """REQ-036 AC7: SPEC-0029 rule 7 (information, not a failure)."""
    proc = check(project(tmp_path, readme=readme))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout == "design: the theme is not approved yet\nok design\n"


def test_ac7_a_placeholder_brand_is_reported_as_at_risk_and_is_not_a_failure(tmp_path):
    """REQ-036 AC7: SPEC-0029 rule 7 (a placeholder brand is in At risk by kind)."""
    theme = THEME.replace("- name: Reading List", "- name: [brand name]")
    proc = check(project(tmp_path, theme=theme))
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout == "at risk design: placeholder brand\nok design\n"
    assert "brand name" not in proc.stdout


def test_ac7_both_notes_can_stand_together_in_a_fixed_order(tmp_path):
    """REQ-036 AC7: SPEC-0029 rule 7 (not approved first, then the placeholder)."""
    theme = THEME.replace("- name: Reading List", "- name: [brand name]")
    proc = check(project(tmp_path, theme=theme, readme=NOT_YET))
    assert proc.stdout.splitlines() == [
        "design: the theme is not approved yet",
        "at risk design: placeholder brand",
        "ok design",
    ]


# --- what the check does not do ----------------------------------------------------------------


def test_ac6_the_check_reads_files_only_and_prints_no_value(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (no network, no model; nothing quoted)."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:socket|urllib|http|requests|ssl)\b", source, re.M
    )
    project(tmp_path, html=HTML.replace("</body>", '<img src="https://a.example.org/x"></body>'))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    check(tmp_path)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


# --- brief #1840 answer 4: the evidence line may name an imported version -----------------------

DESIGN = KIT_ROOT / "scripts" / "agk" / "design.py"
STANDARD_THEME = """# Theme

Standard: agk design standard 1

## Brand

- name: [brand name] — source: [where the owner wrote it down]
- primary: [primary colour as a hex value] — source: [where the owner wrote it down]
- font: system-ui — source: the kit's default, a system font with no download
- logo: [logo file] — source: [where the owner wrote it down]

## Theme

```css
:root {
  --color-accent: #1a56db;
  --color-on-accent: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-accent: #8ab4ff;
    --color-on-accent: #101418;
  }
}
```

## Layout

- density: comfortable
- alignment: start

## Evidence

Evidence: {{evidence}}
"""  # the shape of kit/templates/design-theme.md (not installed)
IMPORT_REQUIREMENTS = """# Requirements

### REQ-001 — A reader keeps a list of books

- Acceptance: AC1 a reader adds a book
- Status: planned
"""
IMPORT_INVENTORY = """# Design inventory

The screens and states of the product.

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
- State empty: n/a: the list is never empty
- State loading: n/a: the list is read at once
- State error: n/a: nothing can fail
- State no-permission: n/a: every reader may see their own list
- State long-content: n/a: the list is short
- State success: n/a: nothing is saved
"""
SIGNOFF_HEAD = "0123456789abcdef0123456789abcdef01234567"


def imported_theme(tmp_path, accent="#1a56db", evidence="docs/design/imported/i1/"):
    """A project on the import path: i1 with its map, and a theme on the standard naming it."""
    root = tmp_path / "proj"
    put(root, "docs/requirements.md", IMPORT_REQUIREMENTS)
    put(root, "docs/design/inventory.md", IMPORT_INVENTORY)
    put(tmp_path / "customer", "index.html", "<!doctype html><title>Books</title><p>Books</p>\n")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(DESIGN), "import", str(tmp_path / "customer"), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    put(
        root,
        "docs/design/imported/i1/map.md",
        "# Screen map of i1\n\n- index.html -> books/default\n",
    )
    theme = STANDARD_THEME.replace("{{evidence}}", evidence)
    put(
        root,
        "docs/design/theme.md",
        theme.replace("--color-accent: #1a56db;", f"--color-accent: {accent};"),
    )
    return root


def test_ac7_an_imported_evidence_line_passes_and_reads_not_approved_yet(tmp_path):
    """REQ-036 AC7: SPEC-0037 rules 12 and 15 (brief #1840 answer 4)."""
    proc = check(imported_theme(tmp_path))
    assert proc.returncode == 0, proc.stdout
    assert "design: the theme is not approved yet" in proc.stdout
    assert proc.stdout.endswith("ok design\n")


def test_ac7_an_imported_evidence_line_reads_approved_with_a_design_row_of_its_digest(tmp_path):
    """REQ-036 AC7: SPEC-0037 rules 9 and 12 (the `i<n>` row of `design_signoff.signed_off`)."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import design_signoff

    root = imported_theme(tmp_path)
    template = (KIT_ROOT / "kit" / "templates" / "design-signoffs.md").read_text(encoding="utf-8")
    row = (
        f"| design | i1 | {design_signoff.imported_digest(root, 'i1')} | {SIGNOFF_HEAD} "
        "| 2026-11-23 | https://example.com/review/2 |\n"
    )
    put(root, "docs/design/signoffs.md", template + row)
    proc = check(root)
    assert proc.returncode == 0, proc.stdout
    assert "not approved yet" not in proc.stdout


def test_ac6_an_imported_evidence_line_to_a_missing_version_fails_with_the_new_wording(tmp_path):
    """REQ-036 AC6: SPEC-0029 rule 7 (brief #1840 answer 4: the folder must exist)."""
    root = imported_theme(tmp_path, evidence="docs/design/imported/i2/")
    failed(
        root,
        "rule 7: docs/design/theme.md: the evidence line points to no mockup, prototype or "
        "imported folder",
    )


def test_ac6_pb05_colour_still_fails_contrast_alone_with_an_imported_evidence_line(tmp_path):
    """REQ-036 AC6: SPEC-0037 rule 7 (brief #1840 answer 2: the check is unchanged)."""
    proc = check(imported_theme(tmp_path, accent="#b5562b"))
    assert proc.returncode == 1
    fails = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL")]
    assert fails == [
        "FAIL design: rule 7: docs/design/theme.md: contrast below 4.5:1 in light for accent "
        "on surface"
    ], proc.stdout


# --- the hold at the design (SPEC-0073 rule 6; REQ-080 AC4; brief #1938, ADR-0803) -------------

HELD_DESIGN = "docs/design/architecture/shop.md"
CRITICAL = ("problem", "who-hurts", "non-goals", "riskiest", "success")
OPEN = "critical 4/5; risk accepted: none; questions 5/12; accepted recommendations 0"
RISKED = "critical 5/5; risk accepted: riskiest; questions 5/12; accepted recommendations 0"
SETTLED = "critical 5/5; risk accepted: none; questions 5/12; accepted recommendations 2"
HOLD_OFF = "[quality]\ngrill_hold = false\n"


def readiness_tree(root, line=OPEN, agk="", open_ids=("riskiest",), risk=None):
    """A tree with only a design, the default playbook and its discovery's `## Assumptions` and
    `## Readiness` (no theme, no mockup); `line=None` leaves the grill sections out."""
    put(root, HELD_DESIGN, "# Design: shop\n")
    default = KIT_ROOT / "config" / "playbooks" / "default.toml"
    put(root, "config/playbooks/default.toml", default.read_text(encoding="utf-8"))
    rows = []
    for n, item in enumerate(CRITICAL, 1):
        rows.append(
            f"- A-{n}: {item}: (open)" if item in open_ids else f'- A-{n}: {item}: "x" (stated)'
        )
        rows += [f"  Risk accepted: {item} (2026-11-25T11:00:00Z)"] if item == risk else []
    points = "".join(f"- D-{n}: `{i}` is open\n" for n, i in enumerate(open_ids, 1)) or "- none\n"
    grill = "\n".join(
        [
            "## Assumptions",
            "",
            *rows,
            "",
            "## Risks",
            "",
            "- none",
            "",
            "## Readiness",
            "",
            line or "",
        ]
    )
    text = (
        f"# Discovery: shop\n\n## Open points\n\n{points}\n{grill}\n"
        if line is not None
        else ("# Discovery: shop\n\n## Open points\n\n- none\n")
    )
    put(root, "docs/discovery/shop.md", text)
    if agk:
        put(root, "agk.toml", agk)
    return root


def held(proc, why="its discovery has an open critical item"):
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout == (
        f"FAIL design: SPEC-0073 rule 6: {HELD_DESIGN} is held: {why}"
        " (setting: quality.grill_hold)\n"
    )


def test_ac4_a_design_whose_discovery_has_an_open_critical_item_is_held(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 6 (held naming the rule, the file and the setting, never a
    value; it fires with no theme or mockups present)."""
    held(check(readiness_tree(tmp_path)))


def test_ac4_a_hand_edited_count_does_not_clear_the_hold(tmp_path):
    """REQ-080 AC4: fix list 7172312072 item 1 (`critical 5/5` over an `## Assumptions` item
    still open with no accepted risk holds; `check-discovery` fails the count too)."""
    readiness_tree(tmp_path, line=SETTLED)
    held(check(tmp_path))
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import front_door

    text = (tmp_path / "docs/discovery/shop.md").read_text(encoding="utf-8")
    found = front_door.quality_problems("docs/discovery/shop.md", text, tmp_path)
    assert any("settled count is not that of `## Assumptions`" in p for p in found), found


@pytest.mark.parametrize("line", ["nearly ready", "", OPEN + "\n" + OPEN])
def test_ac4_a_readiness_out_of_form_holds_the_design(tmp_path, line):
    """REQ-080 AC4: fix list 7172312072 item 2 (fail closed: a `## Readiness` section whose line
    is out of form, empty or doubled holds the design)."""
    held(
        check(readiness_tree(tmp_path, line=line)),
        "its discovery's `## Readiness` is not of rule 7's form",
    )


def test_ac4_grill_items_that_cannot_be_composed_hold_the_design(tmp_path):
    """REQ-080 AC4: fix list 7172312072 item 2 (fail closed: no playbook to read the items)."""
    readiness_tree(tmp_path, line=SETTLED, open_ids=())
    (tmp_path / "config/playbooks/default.toml").unlink()
    held(check(tmp_path), "its discovery's grill items cannot be composed")


@pytest.mark.parametrize(
    "line,agk,open_ids,risk,discovery",
    [
        (RISKED, "", ("riskiest",), "riskiest", True),
        (SETTLED, "", (), None, True),
        (OPEN, HOLD_OFF, ("riskiest",), None, True),
        ("nearly ready", HOLD_OFF, ("riskiest",), None, True),
        (None, "", (), None, True),
        (OPEN, "", ("riskiest",), None, False),
    ],
    ids=[
        "risk-accepted",
        "all-settled",
        "grill-hold-false",
        "malformed-hold-false",
        "no-readiness",
        "no-discovery",
    ],
)
def test_ac4_a_design_is_not_held_when_nothing_critical_is_open(
    tmp_path, line, agk, open_ids, risk, discovery
):
    """REQ-080 AC4: SPEC-0073 rules 6 and 14 (an accepted risk, `grill_hold = false`, no
    `## Readiness` and no discovery document of the slug hold nothing)."""
    readiness_tree(tmp_path, line, agk, open_ids, risk)
    if not discovery:
        (tmp_path / "docs/discovery/shop.md").rename(tmp_path / "docs/discovery/other.md")
    proc = check(tmp_path)
    assert (proc.returncode, proc.stdout) == (0, "ok design (no design record)\n")


def test_ac4_the_hold_joins_the_other_design_failures(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 6 (the hold is one failure among the design step's)."""
    project(tmp_path)
    readiness_tree(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 1
    assert "SPEC-0073 rule 6" in proc.stdout and "ok design" not in proc.stdout


def test_ac4_two_designs_are_each_held_or_cleared_alone(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 14 (two discovery documents: each read alone)."""
    readiness_tree(tmp_path)
    put(tmp_path, "docs/design/architecture/cafe.md", "# Design: cafe\n")
    settled = (tmp_path / "docs/discovery/shop.md").read_text(encoding="utf-8")
    settled = settled.replace("- A-4: riskiest: (open)", '- A-4: riskiest: "x" (stated)')
    put(tmp_path, "docs/discovery/cafe.md", settled.replace(OPEN, SETTLED))
    held(check(tmp_path))


def test_ac7_a_grill_hold_out_of_form_fails_naming_the_setting(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (never read as held or clear; the setting, not the value)."""
    proc = check(readiness_tree(tmp_path, agk='[quality]\ngrill_hold = "maybe"\n'))
    assert proc.returncode == 1, proc.stdout
    assert "quality.grill_hold" in proc.stdout and "maybe" not in proc.stdout
    assert "is held" not in proc.stdout and "ok design" not in proc.stdout


# --- the usability record (SPEC-0038 rule 10 by amendment 237; REQ-080 AC5; brief #1953) --------


def test_ac5_a_web_app_with_no_design_record_is_unchanged(tmp_path):
    """REQ-080 AC5: brief #1953 answer 8 (`ok design (no design record)` with no record at all)."""
    put(tmp_path, "agk.toml", '[delivery]\nwork_type = "web-app"\n')
    proc = check(tmp_path)
    assert (proc.returncode, proc.stdout) == (0, "ok design (no design record)\n")
