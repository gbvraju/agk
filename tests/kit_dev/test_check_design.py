"""Kit-only tests of `check_design.py` (SPEC-0029 rule 7; REQ-036 AC6 and AC7).

The check reads `docs/design/theme.md` and `docs/design/mockups/<date>-<name>/` and fails a mockup
with a script, an external request, a colour outside the token block or a contrast under 4.5:1. A
theme whose evidence folder has no approval line reads "not approved yet"; a placeholder brand is
reported as at risk. Both are information, not failures. No network, no model.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env

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
    return subprocess.run(
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
