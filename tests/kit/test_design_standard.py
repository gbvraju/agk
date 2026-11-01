"""Tests of the kit's design standard and the theme check on it (SPEC-0037 rules 1, 2; REQ-044 AC1).

The kit ships one standard: `kit/templates/design-standard.css` (the tokens) and
`kit/templates/design-patterns.md` (the patterns, each with its seven states). The installed module
`scripts/agk/design_standard.py` holds the same names and values as constants, because an
installed check never reads the kit; these tests prove the constants equal the two templates. A
theme with the line `Standard: agk design standard 1` overrides only its theme block (the brand
colour roles and the fonts) and its layout block (density and alignment); `check_design.py` fails
anything else naming the rule and never the value, and computes the contrast after the overrides
in light and dark. An old-format theme is checked exactly as before. Invented data only, in
`tmp_path`; no network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_design  # noqa: E402
import test_check_design as old  # noqa: E402

try:
    import design_standard as ds  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    ds = None

SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_design.py"
MODULE = KIT_ROOT / "scripts" / "agk" / "design_standard.py"
CSS = KIT_ROOT / "kit" / "templates" / "design-standard.css"
PATTERNS = KIT_ROOT / "kit" / "templates" / "design-patterns.md"

THEME = """# Theme

Standard: agk design standard 1

The brand record of this product and its overrides of the kit's design standard.

## Brand

- name: Reading List — source: the owner's brief of 2026-10-20
- primary: #1a56db — source: the brand guide, page 2
- font: Georgia, serif — source: the brand guide, page 3
- logo: docs/design/logo.svg — source: the brand guide, page 1

## Theme

```css
:root {
  --color-accent: #1d4ed8;
  --color-on-accent: #ffffff;
  --color-surface: #f7f7f2;
  --font-body: Georgia, serif;
  --font-heading: Georgia, serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-accent: #93b4fd;
    --color-on-accent: #0f1115;
    --color-surface: #1c1f24;
  }
}
```

## Layout

- density: compact
- alignment: centre

## Evidence

Evidence: docs/design/prototype/v1/
"""
DARK_BLOCK = """@media (prefers-color-scheme: dark) {
  :root {
    --color-accent: #93b4fd;
    --color-on-accent: #0f1115;
    --color-surface: #1c1f24;
  }
}
"""


def clean_env():
    return {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}


def put(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(root, theme=THEME):
    put(root, "docs/design/theme.md", theme)
    (root / "docs/design/prototype/v1").mkdir(parents=True, exist_ok=True)
    return root


def check(root):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def failed(root, needle, rule="rule 2"):
    proc = check(root)
    assert proc.returncode == 1, proc.stdout
    assert needle in proc.stdout, proc.stdout
    assert f"FAIL design: {rule}: docs/design/theme.md: " in proc.stdout, proc.stdout
    return proc.stdout


def css_text():
    return CSS.read_text(encoding="utf-8")


def declarations(body):
    return {n: v.strip() for n, v in re.findall(r"(--[\w-]+)\s*:\s*([^;{}]+);", body)}


def top_rules():
    found, rest = ds.css_rules(css_text())
    assert not rest.strip(), rest
    return found


def block(prelude):
    bodies = [body for pre, body in top_rules() if pre == prelude]
    assert len(bodies) == 1, prelude
    return bodies[0]


def media_root(query):
    inner, rest = ds.css_rules(block(f"@media ({query})"))
    assert not rest.strip()
    assert [pre for pre, _ in inner] == [":root"], query
    return declarations(inner[0][1])


# --- the standard's tokens (rule 1) ------------------------------------------------------------


def test_ac1_the_standard_is_headed_with_its_number():
    """REQ-044 AC1: SPEC-0037 rule 1 (one standard, numbered)."""
    assert css_text().splitlines()[0] == "/* agk design standard 1 */" == ds.HEADER
    assert ds.STANDARD == 1


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_ac1_every_colour_role_is_set_in_light_and_dark_and_equals_the_module(mode):
    """REQ-044 AC1: SPEC-0037 rule 1 (every colour role, light and dark; constants = template)."""
    tokens = (
        declarations(block(":root"))
        if mode == "light"
        else media_root("prefers-color-scheme: dark")
    )
    colours = {n[len("--color-") :]: v for n, v in tokens.items() if n.startswith("--color-")}
    assert colours == (ds.LIGHT if mode == "light" else ds.DARK)
    assert set(colours) == set(ds.ROLES)
    for role in ("success", "warning", "danger", "info", "accent"):
        assert role in ds.ROLES and f"on-{role}" in ds.ROLES
    for role in ("background", "surface", "text", "muted", "border", "focus"):
        assert role in ds.ROLES
    assert all(check_design.HEX.match(v) for v in colours.values())


def test_ac1_the_theme_roles_are_the_brand_roles_only():
    """REQ-044 AC1: SPEC-0037 rule 2 (status and focus roles are fixed by the standard)."""
    assert ds.THEME_ROLES == (
        "background",
        "surface",
        "text",
        "muted",
        "border",
        "accent",
        "on-accent",
    )
    assert set(ds.THEME_ROLES) < set(ds.ROLES)
    assert ds.FONT_TOKENS == ("--font-body", "--font-heading")


def test_ac1_the_scales_are_set():
    """REQ-044 AC1: SPEC-0037 rule 1 (type, spacing, radii, elevations, motion)."""
    tokens = declarations(block(":root"))
    names = (
        [f"--font-size-{n}" for n in range(1, 7)]
        + list(ds.FONT_TOKENS)
        + [f"--space-{n}" for n in range(1, 9)]
        + [f"--radius-{n}" for n in range(1, 4)]
        + [f"--elevation-{n}" for n in range(1, 4)]
        + ["--motion-fast", "--motion-normal", "--motion-slow"]
    )
    for name in names:
        assert name in tokens, name
    assert "--font-size-7" not in tokens and "--space-9" not in tokens
    for font in ds.FONT_TOKENS:
        assert "url(" not in tokens[font] and "system-ui" in tokens[font]


def test_ac1_every_motion_is_off_under_reduced_motion():
    """REQ-044 AC1: SPEC-0037 rule 1 (`prefers-reduced-motion: reduce`)."""
    tokens = media_root("prefers-reduced-motion: reduce")
    assert tokens == {"--motion-fast": "0ms", "--motion-normal": "0ms", "--motion-slow": "0ms"}


def test_ac1_focus_is_visible_and_targets_are_44_px():
    """REQ-044 AC1: SPEC-0037 rule 1 (WCAG 2.2 AA: `:focus-visible`, targets of 44 by 44 px)."""
    rules = dict(top_rules())
    focus = [body for pre, body in rules.items() if pre == ":focus-visible"]
    assert focus and "outline" in focus[0] and "var(--color-focus)" in focus[0]
    targets = [body for pre, body in rules.items() if "button" in pre.split(",")[0]]
    assert targets
    assert "min-height: 44px" in targets[0] and "min-width: 44px" in targets[0]


def test_ac1_density_and_alignment_rules_exist_for_each_value():
    """REQ-044 AC1: SPEC-0037 rule 2 (the layout block's settings have rules in the standard)."""
    preludes = [pre for pre, _ in top_rules()]
    assert ds.DENSITY == ("compact", "comfortable", "spacious")
    assert ds.ALIGNMENT == ("start", "centre")
    for value in ds.DENSITY:
        assert any(f'[data-density="{value}"]' in pre for pre in preludes), value
    for value in ds.ALIGNMENT:
        assert any(f'[data-align="{value}"]' in pre for pre in preludes), value


def test_ac1_the_media_queries_are_the_five_breakpoints():
    """REQ-044 AC1: SPEC-0037 rule 1 and Q-S0037-1 (360, 600, 900, 1200 and 1440 px)."""
    assert ds.BREAKPOINTS == (360, 600, 900, 1200, 1440)
    widths = {int(n) for n in re.findall(r"@media[^{]*?(?:min|max)-width:\s*(\d+)px", css_text())}
    assert widths == set(ds.BREAKPOINTS)
    for width in ds.BREAKPOINTS:
        assert f"@media (min-width: {width}px)" in css_text()


def test_ac1_no_colour_is_written_outside_the_token_blocks():
    """REQ-044 AC1: SPEC-0037 rule 1 (every colour of the standard is a token)."""
    text = css_text()
    rest = text
    for prelude, body in top_rules():
        if prelude == ":root":
            rest = rest.replace(body, "")
    rest = rest.replace(block("@media (prefers-color-scheme: dark)"), "")
    assert check_design.colour_problems("standard", rest, []) == []
    assert "url(" not in text and "@import" not in text and "://" not in text


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_ac1_the_standards_own_pairs_meet_4_5_and_3_to_1(mode):
    """REQ-044 AC1: SPEC-0037 rule 1 (4.5:1 for text, 3:1 for UI parts, in both modes)."""
    values = ds.LIGHT if mode == "light" else ds.DARK
    assert {m for _, _, m in ds.CONTRAST_PAIRS} == {4.5, 3.0}
    pairs = {(a, b) for a, b, _ in ds.CONTRAST_PAIRS}
    for need in [
        ("text", "background"),
        ("muted", "background"),
        ("on-accent", "accent"),
        ("border", "background"),
        ("focus", "background"),
    ]:
        assert need in pairs
    for role in ("success", "warning", "danger", "info"):
        assert (f"on-{role}", role) in pairs
    for first, second, minimum in ds.CONTRAST_PAIRS:
        assert check_design.contrast(values[first], values[second]) >= minimum, (first, second)


def test_ac1_the_old_tokens_map_to_the_five_roles():
    """REQ-044 AC1: SPEC-0037 rule 2 (`--bg`, `--fg`, `--muted`, `--accent`, `--accent-fg`)."""
    assert ds.OLD_TOKENS == {
        "--bg": "background",
        "--fg": "text",
        "--muted": "muted",
        "--accent": "accent",
        "--accent-fg": "on-accent",
    }
    assert set(ds.OLD_TOKENS.values()) <= set(ds.THEME_ROLES)


# --- the pattern library (rule 1) --------------------------------------------------------------


def pattern_sections():
    sections: dict[str, dict[str, list[str]]] = {}
    pattern = state = None
    for line in PATTERNS.read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("## "):
            pattern, state = line[3:].strip(), None
            sections[pattern] = {}
        elif line.startswith("### ") and pattern is not None:
            state = line[4:].strip()
            sections[pattern][state] = []
        elif pattern is not None and state is not None:
            sections[pattern][state].append(line)
    return sections


def test_ac1_every_pattern_has_its_seven_states_in_order():
    """REQ-044 AC1: SPEC-0037 rule 1 (eleven patterns, `default` and the six required states)."""
    sections = pattern_sections()
    assert tuple(sections) == ds.PATTERNS
    assert len(ds.PATTERNS) == 11
    assert ds.REQUIRED_STATES == (
        "empty",
        "loading",
        "error",
        "no-permission",
        "long-content",
        "success",
    )
    assert ds.STATES == ("default", *ds.REQUIRED_STATES)
    for pattern, states in sections.items():
        assert tuple(states) == ds.STATES, pattern


def test_ac1_each_state_is_one_html_block_of_the_standards_classes_only():
    """REQ-044 AC1: SPEC-0037 rule 1 (markup and classes only, no colour, size or font)."""
    defined = set(
        re.findall(r"\.([a-z][a-z0-9-]*)", re.sub(r"/\*.*?\*/", "", css_text(), flags=re.S))
    )
    for pattern, states in pattern_sections().items():
        for state, lines in states.items():
            text = "".join(lines)
            blocks = re.findall(r"```html\n(.*?)```", text, re.S)
            assert len(blocks) == 1 and text.count("```") == 2, (pattern, state)
            html = blocks[0]
            where = (pattern, state)
            assert html.strip(), where
            assert not re.search(r"\sstyle\s*=|<\s*style|<\s*script|\son[a-z]+\s*=", html, re.I), (
                where
            )
            assert not re.search(
                r"<\s*font\b|\s(?:color|bgcolor|width|height|size|face)\s*=", html, re.I
            ), where
            assert not check_design.COLOUR_LITERAL.search(html), where
            assert not re.search(r"\[[^\]]*\]", html), where
            assert not re.search(r"lorem ipsum|\bTODO\b|\bTBD\b|://", html, re.I), where
            used = {c for attr in re.findall(r'class="([^"]*)"', html) for c in attr.split()}
            assert used <= defined, (where, used - defined)


def test_ac1_fixture_slots_are_written_in_double_braces():
    """REQ-044 AC1: SPEC-0037 rule 6 (slots `{{<key>}}`, filled by the prototype writer)."""
    text = PATTERNS.read_text(encoding="utf-8")
    slots = re.findall(r"\{\{([^{}]*)\}\}", text)
    assert slots and all(re.fullmatch(r"[a-z][a-z0-9_.-]*", s) for s in slots)


# --- the module ---------------------------------------------------------------------------------


def test_ac1_the_installed_module_is_listed_and_reads_no_kit_and_no_network():
    """REQ-044 AC1: SPEC-0037 rule 14 (a) (installed: `verbatim`, sorted; files only)."""
    manifest = json.loads((KIT_ROOT / "kit/manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/design_standard.py" in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
    source = MODULE.read_text(encoding="utf-8")
    assert "kit/" not in source and "templates" not in source
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:socket|urllib|http|requests|ssl|subprocess)\b", source, re.M
    )
    design = SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"^import design_standard\b|^from design_standard import", design, re.M)
    assert "never installed" not in design.split('"""')[1]


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (THEME, "standard"),
        (
            THEME.replace("Standard: agk design standard 1", "Standard: agk design standard 2"),
            "standard",
        ),
        (old.THEME, "old"),
        ("# Theme\n\nThe Standard: line is described in prose.\n", "old"),
    ],
)
def test_ac1_the_theme_format_is_read_from_the_standard_line(text, kind):
    """REQ-044 AC1: SPEC-0037 rule 2 (no `Standard:` line is the old format)."""
    assert ds.theme_format(text) == kind


# --- a theme on the standard (rule 2) -----------------------------------------------------------


def test_ac1_a_theme_overriding_brand_colours_fonts_density_and_alignment_passes(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (the theme block and the layout block only)."""
    assert ds.standard_theme_problems(THEME) == []
    proc = check(project(tmp_path))
    assert (proc.returncode, proc.stdout) == (
        0,
        "design: the theme is not approved yet\nok design\n",
    )


def test_ac1_a_theme_with_only_the_standard_line_passes_on_the_standards_values(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (an empty override keeps the standard)."""
    bare = re.sub(r"```css\n.*?```", "```css\n:root {\n}\n```", THEME, flags=re.S)
    proc = check(project(tmp_path, bare))
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize(
    ("change", "needle", "secret"),
    [
        (
            lambda t: t.replace("--font-body: Georgia", "--space-2: 3px;\n  --font-body: Georgia"),
            "outside its theme block",
            "3px",
        ),
        (
            lambda t: t.replace("  --color-surface: #1c1f24;", "  --color-focus: #abcdef;"),
            "outside its theme block",
            "abcdef",
        ),
        (
            lambda t: t.replace(
                "@media (prefers-color", "body { margin: 7px; }\n@media (prefers-color"
            ),
            "outside its theme block",
            "7px",
        ),
        (
            lambda t: t.replace(
                "  --font-body: Georgia", "  color: #123456;\n  --font-body: Georgia"
            ),
            "outside its theme block",
            "123456",
        ),
        (
            lambda t: t.replace(
                "@media (prefers-color",
                "@media (min-width: 777px) { :root { --color-text: #000000; } }\n"
                "@media (prefers-color",
            ),
            "outside its theme block",
            "777",
        ),
        (
            lambda t: t.replace("```css\n", "```css\n@import 'q.css';\n"),
            "outside its theme block",
            "q.css",
        ),
        (
            lambda t: t.replace(
                "## Layout", "## Extra\n\n```css\n.card { padding: 9px; }\n```\n\n## Layout"
            ),
            "outside its theme block",
            "9px",
        ),
        (lambda t: t.replace("- density: compact", "- density: huge"), "density", "huge"),
        (
            lambda t: t.replace("- alignment: centre", "- alignment: justify"),
            "alignment",
            "justify",
        ),
        (lambda t: t.replace("- alignment: centre\n", ""), "alignment", "centre"),
        (
            lambda t: t.replace("- alignment: centre", "- alignment: centre\n- width: 1234px"),
            "layout",
            "1234",
        ),
        (lambda t: t.replace("## Theme\n", "## Colours\n"), "one theme block", "#1d4ed8"),
        (
            lambda t: t.replace("```\n\n## Layout", "```\n\n```css\n:root {\n}\n```\n\n## Layout"),
            "one theme block",
            "#1d4ed8",
        ),
        (lambda t: t.replace("design standard 1", "design standard 9"), "design standard", "9"),
        (
            lambda t: t.replace(
                "- logo: docs/design/logo.svg — source: the brand guide, page 1\n", ""
            ),
            "logo",
            "logo.svg",
        ),
    ],
)
def test_ac1_a_theme_that_sets_more_than_its_blocks_fails_naming_the_rule_not_the_value(
    tmp_path, change, needle, secret
):
    """REQ-044 AC1: SPEC-0037 rule 2 (anything outside the theme and layout blocks fails)."""
    text = change(THEME)
    assert text != THEME
    out = failed(project(tmp_path, text), needle)
    assert secret not in out


@pytest.mark.parametrize(
    ("change", "mode", "pair", "minimum"),
    [
        (
            lambda t: t.replace("--color-accent: #93b4fd", "--color-accent: #2a2f38"),
            "dark",
            "accent on background",
            "4.5",
        ),
        (
            lambda t: t.replace(
                "--color-surface: #f7f7f2;",
                "--color-surface: #f7f7f2;\n  --color-background: #fafafa;",
            ),
            "dark",
            "text on background",
            "4.5",
        ),
        (
            lambda t: t.replace(
                "--color-surface: #f7f7f2;", "--color-surface: #f7f7f2;\n  --color-border: #dddddd;"
            ),
            "light",
            "border on background",
            "3",
        ),
        (
            lambda t: t.replace("--color-on-accent: #ffffff", "--color-on-accent: #2a4ad0"),
            "light",
            "on-accent on accent",
            "4.5",
        ),
    ],
)
def test_ac1_the_contrast_is_computed_after_the_overrides_in_each_mode(
    tmp_path, change, mode, pair, minimum
):
    """REQ-044 AC1: SPEC-0037 rules 2 and 7 (after the overrides; light applies in dark too)."""
    out = failed(project(tmp_path, change(THEME)), "contrast", rule="rule 7")
    assert f"contrast below {minimum}:1 in {mode} for {pair}" in out
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", out)


def test_ac1_a_colour_role_that_is_not_hex_fails(tmp_path):
    """REQ-044 AC1: SPEC-0037 rules 2 and 7 (contrast is computed, so a role is a hex colour)."""
    out = failed(
        project(tmp_path, THEME.replace("--color-surface: #f7f7f2", "--color-surface: ivory")),
        "hex",
        rule="rule 7",
    )
    assert "ivory" not in out


def test_ac1_the_theme_colours_are_the_standards_after_the_cascade():
    """REQ-044 AC1: SPEC-0037 rule 2 (light overrides apply in dark unless dark sets the role)."""
    light, dark = ds.theme_colours(THEME.replace(DARK_BLOCK, ""))
    assert light["accent"] == "#1d4ed8" == dark["accent"]
    assert light["text"] == ds.LIGHT["text"] and dark["text"] == ds.DARK["text"]
    light, dark = ds.theme_colours(THEME)
    assert dark["accent"] == "#93b4fd" and dark["focus"] == ds.DARK["focus"]


def test_ac1_a_standard_theme_keeps_the_brand_record_and_evidence_checks(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (the brand record of SPEC-0029 rule 6 is kept)."""
    proc = check(project(tmp_path, THEME.replace(" — source: the brand guide, page 2", "")))
    assert proc.returncode == 1 and "source" in proc.stdout
    proc = check(project(tmp_path, THEME.replace("prototype/v1/", "prototype/v7/")))
    assert proc.returncode == 1 and "evidence" in proc.stdout


def test_ac1_a_standard_theme_pointing_to_an_approved_mockup_reads_approved(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 12 (existing mockup folders are read and checked as before)."""
    old.project(tmp_path)
    theme = THEME.replace("docs/design/prototype/v1/", f"docs/design/mockups/{old.FOLDER}/")
    put(tmp_path, "docs/design/theme.md", theme)
    proc = check(tmp_path)
    assert (proc.returncode, proc.stdout) == (0, "ok design\n")


# --- the old format and the evidence line (rules 2 and 12) --------------------------------------


def test_ac1_an_old_format_theme_and_its_mockup_pass_as_before(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 2 (an existing theme is not broken; rule 2 does not apply)."""
    proc = check(old.project(tmp_path))
    assert (proc.returncode, proc.stdout) == (0, "ok design\n")
    assert ds.theme_format(old.THEME) == "old"


def test_ac1_an_evidence_line_may_point_to_a_prototype_version_that_reads_not_approved_yet(
    tmp_path,
):
    """REQ-044 AC1: SPEC-0037 rule 12 (a prototype version is `not approved yet`)."""
    old.project(tmp_path)
    theme = old.THEME.replace(f"docs/design/mockups/{old.FOLDER}/", "docs/design/prototype/v2/")
    put(tmp_path, "docs/design/theme.md", theme)
    (tmp_path / "docs/design/prototype/v2").mkdir(parents=True)
    proc = check(tmp_path)
    assert (proc.returncode, proc.stdout) == (
        0,
        "design: the theme is not approved yet\nok design\n",
    )
    put(tmp_path, "docs/design/theme.md", theme.replace("prototype/v2/", "prototype/latest/"))
    assert check(tmp_path).returncode == 1


def test_ac1_the_check_writes_nothing(tmp_path):
    """REQ-044 AC1: SPEC-0037 rule 13 (files only, nothing written)."""
    project(tmp_path, THEME.replace("- density: compact", "- density: huge"))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    check(tmp_path)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
