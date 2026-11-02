"""The kit's design standard as constants, and the reading of a theme on it (SPEC-0037 rules 1, 2).

Installed (listed in the kit's manifest, verbatim) and imported by `check_design.py`. It never
reads a file: the kit's tests prove these constants equal the standard's own token sheet and pattern
library, so an installed project needs neither. A theme with the line
`Standard: agk design standard 1` overrides only its theme block (the brand colour roles and the
font stacks, in light and dark) and its layout block (density and alignment); everything else is a
rule 2 problem, named without the value. Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import re

STANDARD = 1
HEADER = f"/* agk design standard {STANDARD} */"
THEME = "docs/design/theme.md"

STATUS_ROLES = ("success", "warning", "danger", "info")
ROLES = (
    "background",
    "surface",
    "text",
    "muted",
    "border",
    "accent",
    "on-accent",
    "focus",
    *(r for s in STATUS_ROLES for r in (s, f"on-{s}")),
)
# The brand roles a theme may set; focus and the status roles are fixed by the standard.
THEME_ROLES = ("background", "surface", "text", "muted", "border", "accent", "on-accent")
FONT_TOKENS = ("--font-body", "--font-heading")
DENSITY = ("compact", "comfortable", "spacious")
ALIGNMENT = ("start", "centre")
BREAKPOINTS = (360, 600, 900, 1200, 1440)
PATTERNS = (
    "app shell and navigation",
    "list with filter and sort",
    "detail",
    "form with validation",
    "table",
    "dashboard",
    "wizard",
    "search",
    "settings",
    "notifications",
    "confirmation dialog",
)
REQUIRED_STATES = ("empty", "loading", "error", "no-permission", "long-content", "success")
STATES = ("default", *REQUIRED_STATES)
# (foreground role, background role, minimum ratio): 4.5:1 for text, 3:1 for UI parts.
CONTRAST_PAIRS = (
    ("text", "background", 4.5),
    ("text", "surface", 4.5),
    ("muted", "background", 4.5),
    ("muted", "surface", 4.5),
    ("accent", "background", 4.5),
    ("accent", "surface", 4.5),
    ("on-accent", "accent", 4.5),
    *((f"on-{s}", s, 4.5) for s in STATUS_ROLES),
    ("border", "background", 3.0),
    ("border", "surface", 3.0),
    ("focus", "background", 3.0),
    ("focus", "surface", 3.0),
)
# The tokens of an old-format theme (SPEC-0029 rule 6) and the role each moves to, same value.
OLD_TOKENS = {
    "--bg": "background",
    "--fg": "text",
    "--muted": "muted",
    "--accent": "accent",
    "--accent-fg": "on-accent",
}
LIGHT = {
    "background": "#ffffff",
    "surface": "#f5f6f8",
    "text": "#15181d",
    "muted": "#4f5661",
    "border": "#7a828e",
    "accent": "#1a56db",
    "on-accent": "#ffffff",
    "focus": "#0b57d0",
    "success": "#1b6e3a",
    "on-success": "#ffffff",
    "warning": "#8a5a00",
    "on-warning": "#ffffff",
    "danger": "#b3261e",
    "on-danger": "#ffffff",
    "info": "#155e9c",
    "on-info": "#ffffff",
}
DARK = {
    "background": "#101418",
    "surface": "#1b2027",
    "text": "#f2f4f7",
    "muted": "#b4bcc8",
    "border": "#7d8794",
    "accent": "#8ab4ff",
    "on-accent": "#101418",
    "focus": "#a8c7fa",
    "success": "#6dd58c",
    "on-success": "#0b1f12",
    "warning": "#f2c14e",
    "on-warning": "#241a00",
    "danger": "#ffb4ab",
    "on-danger": "#3b0906",
    "info": "#8ccff7",
    "on-info": "#0a2233",
}

STANDARD_LINE = re.compile(r"(?m)^Standard:")
KNOWN_LINE = re.compile(rf"(?m)^Standard:\s*agk design standard {STANDARD}\s*$")
DARK_QUERY = re.compile(r"^@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)$")
DECLARATION = re.compile(r"^\s*([a-zA-Z-][\w-]*)\s*:\s*([^;]*?)\s*$")
LAYOUT_LINE = re.compile(r"^-\s*([^:]+?)\s*:\s*(.*?)\s*$")
LOGO_LINE = re.compile(r"^- logo:\s")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def token(role: str) -> str:
    return f"--color-{role}"


ALLOWED = frozenset([token(r) for r in THEME_ROLES] + list(FONT_TOKENS))


def theme_format(text: str) -> str:
    """`standard` when the theme has a `Standard:` line, else `old` (SPEC-0029 rule 6)."""
    return "standard" if STANDARD_LINE.search(text) else "old"


def css_rules(css: str) -> tuple[list[tuple[str, str]], str]:
    """The top-level rules of `css` as (prelude, body), and the text outside every rule."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[str, str]] = []
    outside: list[str] = []
    i = 0
    while i < len(css):
        start = css.find("{", i)
        if start < 0:
            outside.append(css[i:])
            break
        prelude_text = css[i:start]
        cut = prelude_text.rfind(";") + 1  # a statement such as `@import ...;` is outside
        outside.append(prelude_text[:cut])
        depth, j = 1, start + 1
        while j < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        rules.append((" ".join(prelude_text[cut:].split()), css[start + 1 : j - 1]))
        i = j
    return rules, "".join(outside)


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None:
            current.append(line)
    return sections


def _declared(body: str) -> tuple[dict[str, str], bool]:
    """(the declarations of a rule body, whether it holds anything else: a nested rule or junk)."""
    found: dict[str, str] = {}
    other = "{" in body or "}" in body
    for part in body.split(";"):
        if not part.strip():
            continue
        match = DECLARATION.match(part)
        if match:
            found[match.group(1)] = match.group(2)
        else:
            other = True
    return found, other


def _theme_block(text: str) -> tuple[dict[str, str], dict[str, str], list[str]] | None:
    """(light, dark, problems) of the one css block of `## Theme`, or None when it is not one."""
    sections = _sections(text)
    fences = re.findall(r"```css\n(.*?)```", "\n".join(sections.get("Theme", [])), re.S)
    if len(fences) != 1:
        return None
    rules, outside = css_rules(fences[0])
    roots = [body for pre, body in rules if pre == ":root"]
    darks = [body for pre, body in rules if DARK_QUERY.match(pre)]
    if len(roots) != 1 or len(darks) > 1:
        return None
    problems: list[str] = []
    outside_rule = bool(outside.strip()) or len(rules) != len(roots) + len(darks)
    light, other = _declared(roots[0])
    outside_rule = outside_rule or other
    dark: dict[str, str] = {}
    if darks:
        inner, rest = css_rules(darks[0])
        if rest.strip() or [pre for pre, _ in inner] != [":root"]:
            outside_rule = True
        for pre, body in inner:
            if pre == ":root":
                found, other = _declared(body)
                dark.update(found)
                outside_rule = outside_rule or other
    if outside_rule or set(light) - ALLOWED or set(dark) - ALLOWED:
        problems.append(f"rule 2: {THEME}: the theme sets a token or rule outside its theme block")
    return light, dark, problems


def standard_theme_problems(text: str) -> list[str]:
    """The rule 2 problems, and the colour-value problem, of a theme on the standard; no value."""
    out: list[str] = []
    if not KNOWN_LINE.search(text):
        out.append(f"rule 2: {THEME}: the theme names a design standard this check does not know")
    sections = _sections(text)
    if not any(LOGO_LINE.match(line) for line in sections.get("Brand", [])):
        out.append(f"rule 2: {THEME}: the brand record has no logo line")
    for name, lines in sections.items():
        if name != "Theme" and re.search(r"(?m)^```css\s*$", "\n".join(lines)):
            out.append(f"rule 2: {THEME}: the theme sets a token or rule outside its theme block")
            break
    block = _theme_block(text)
    if block is None:
        out.append(f"rule 2: {THEME}: the theme does not hold one theme block")
    else:
        light, dark, problems = block
        out += [p for p in problems if p not in out]
        colours = [v for k, v in [*light.items(), *dark.items()] if k.startswith("--color-")]
        if any(not HEX.match(v) for v in colours):
            out.append(f"rule 7: {THEME}: a token in a contrast pair is not a hex colour")
    settings: dict[str, list[str]] = {}
    other = False
    for line in sections.get("Layout", []):
        if not line.strip():
            continue
        match = LAYOUT_LINE.match(line.strip())
        if match and match.group(1) in ("density", "alignment"):
            settings.setdefault(match.group(1), []).append(match.group(2))
        else:
            other = True
    for name, allowed in (("density", DENSITY), ("alignment", ALIGNMENT)):
        values = settings.get(name, [])
        if len(values) != 1 or values[0] not in allowed:
            out.append(f"rule 2: {THEME}: the layout setting {name} is not one of the standard's")
    if other:
        out.append(
            f"rule 2: {THEME}: the layout block sets something other than density and alignment"
        )
    return out


def theme_colours(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """The colour roles a page shows, light and dark, after the theme's overrides.

    `theme.css` is loaded after the standard, so a light override applies in dark as well unless the
    theme's dark rule sets the same role (the cascade).
    """
    block = _theme_block(text)
    light_set, dark_set = (block[0], block[1]) if block else ({}, {})

    def roles(declared: dict[str, str]) -> dict[str, str]:
        return {
            k[len("--color-") :]: v
            for k, v in declared.items()
            if k in ALLOWED and k.startswith("--color-")
        }

    light = {**LIGHT, **roles(light_set)}
    dark = {**DARK, **roles(light_set), **roles(dark_set)}
    return light, dark
