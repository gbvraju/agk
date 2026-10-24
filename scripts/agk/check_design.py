"""The design check (SPEC-0029 rule 7). Kit-only: never installed.

Reads `docs/design/theme.md` and the folders of `docs/design/mockups/` and fails, naming the rule
and the path and never a value, on: a script or an event handler in a mockup, an external request
or a loaded resource, a colour that is not a token, a token block that is not one with a light and
a dark set, a contrast under 4.5:1 (computed from the tokens, in both modes), a brand value with no
source, an evidence line that points to no mockup folder. Two things are information and not
failures: a theme whose evidence folder has no approval line reads "not approved yet", and a
placeholder brand is reported as at risk. Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from common import repo_root, run

NAME = "design"
THEME = "docs/design/theme.md"
MOCKUPS = "docs/design/mockups"
MIN_CONTRAST = 4.5
FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$")
EVIDENCE = re.compile(r"^Evidence:\s*docs/design/mockups/([^/\s]+)/?\s*$", re.M)
APPROVAL = re.compile(r"(?m)^Approved by \S.* on \d{4}-\d{2}-\d{2}\s*$")
BRAND = re.compile(r"^- ([^:]+):\s+(.+?)\s+—\s+source:\s+(\S.*)$")
PAIR = re.compile(r"^-\s+(--[\w-]+)\s+on\s+(--[\w-]+)\s*$")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
DARK_MEDIA = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{")
ROOT_RULE = re.compile(r":root\s*\{([^}]*)\}")
DECLARATION = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+)")
COLOUR_LITERAL = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color)\(", re.I
)
COLOUR_PROPERTY = re.compile(r"color|^background|^border|^outline|shadow|^fill|^stroke", re.I)
NAMED = frozenset(
    "black white red green blue yellow orange purple pink gray grey silver gold navy teal maroon "
    "lime aqua fuchsia olive brown cyan magenta indigo violet beige ivory khaki coral salmon "
    "crimson tomato turquoise lavender tan plum orchid azure".split()
)
SCRIPT_MARKS = (r"<\s*script\b", r"\son[a-z]+\s*=", r"javascript\s*:")
EXTERNAL_MARKS = (
    r"://",
    r"(?:src|href|action|poster|srcset|data)\s*=\s*[\"']?\s*//",
    r"url\(\s*[\"']?\s*//",
    r"@import",
    r"<\s*(?:link|iframe|object|embed|base)\b",
)
DEFAULT_PAIRS = [("--fg", "--bg"), ("--muted", "--bg")]


def luminance(colour: str) -> float:
    digits = colour.lstrip("#")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    channels = []
    for i in (0, 2, 4):
        value = int(digits[i : i + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first: str, second: str) -> float:
    """The WCAG 2 contrast ratio of two hex colours."""
    a, b = sorted((luminance(first), luminance(second)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def split_tokens(css: str) -> tuple[dict[str, str], dict[str, str], str, tuple[int, int]]:
    """(light tokens, dark tokens, css without the token rules, (light, dark) :root rule counts)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    dark_text = ""
    match = DARK_MEDIA.search(css)
    if match:
        depth, i = 1, match.end()
        while i < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        dark_text = css[match.end() : i - 1]
        css = css[: match.start()] + css[i:]
    light_rules = ROOT_RULE.findall(css)
    dark_rules = ROOT_RULE.findall(dark_text)

    def declared(rules: list[str]) -> dict[str, str]:
        found: dict[str, str] = {}
        for body in rules:
            for name, value in DECLARATION.findall(body):
                if name.startswith("--"):
                    found[name] = value.strip()
        return found

    rest = ROOT_RULE.sub("", css) + ROOT_RULE.sub("", dark_text)
    return declared(light_rules), declared(dark_rules), rest, (len(light_rules), len(dark_rules))


def token_problems(where: str, css: str, pairs: list[tuple[str, str]]) -> tuple[list[str], str]:
    """Problems of one token block (rule 7) and the css left once the token rules are taken out."""
    light, dark, rest, (light_rules, dark_rules) = split_tokens(css)
    out: list[str] = []
    if not light or not dark:
        out.append(f"rule 7: {where}: the tokens lack a light and dark set")
    if light_rules != 1 or dark_rules > 1:
        out.append(f"rule 7: {where}: the tokens are not one token block")
    for mode, tokens in (("light", light), ("dark", dark)):
        if not tokens:
            continue
        for first, second in pairs:
            if first not in tokens or second not in tokens:
                out.append(f"rule 7: {where}: a contrast pair names a token the {mode} set lacks")
            elif not (HEX.match(tokens[first]) and HEX.match(tokens[second])):
                out.append(f"rule 7: {where}: a token in a contrast pair is not a hex colour")
            elif contrast(tokens[first], tokens[second]) < MIN_CONTRAST:
                out.append(
                    f"rule 7: {where}: contrast under 4.5:1 for {first} on {second} ({mode})"
                )
    return out, rest


def colour_problems(where: str, css: str) -> list[str]:
    for prop, value in DECLARATION.findall(css):
        if COLOUR_LITERAL.search(value):
            return [f"rule 7: {where}: a colour is written outside the token block"]
        if COLOUR_PROPERTY.search(prop) and NAMED & set(re.findall(r"[a-z]+", value.lower())):
            return [f"rule 7: {where}: a colour is written outside the token block"]
    return []


def mockup_problems(root: Path, folder: Path, pairs: list[tuple[str, str]]) -> list[str]:
    rel = folder.relative_to(root).as_posix()
    out: list[str] = []
    if not FOLDER.match(folder.name):
        out.append(f"rule 7: {rel}: the folder name is not <date>-<name>")
    for name in ("index.html", "README.md"):
        if not (folder / name).is_file():
            out.append(f"rule 7: {rel}: {name} is missing")
    page = folder / "index.html"
    if not page.is_file():
        return out
    html = page.read_text(encoding="utf-8")
    where = f"{rel}/index.html"
    if any(re.search(mark, html, re.I) for mark in SCRIPT_MARKS):
        out.append(f"rule 7: {where}: the page holds a script or an event handler")
    if any(re.search(mark, html, re.I) for mark in EXTERNAL_MARKS):
        out.append(f"rule 7: {where}: the page makes an external request or loads a resource")
    blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.S | re.I)
    if len(blocks) != 1:
        out.append(f"rule 7: {where}: the tokens are not one token block in one style element")
        return out
    problems, rest = token_problems(where, blocks[0], pairs)
    out += problems
    inline = " ".join(re.findall(r"\sstyle\s*=\s*[\"']([^\"']*)[\"']", html, re.I))
    out += colour_problems(where, rest + " " + inline)
    return out


def theme_parts(text: str) -> tuple[dict[str, list[str]], list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None:
            current.append(line)
    return sections, [ln for ln in sections.get("Contrast", []) if ln.strip()]


def theme_problems(root: Path, text: str) -> tuple[list[str], list[tuple[str, str]], bool, bool]:
    """(problems, contrast pairs, placeholder brand, approved) of the theme."""
    sections, pair_lines = theme_parts(text)
    out: list[str] = []
    pairs = [m.groups() for ln in pair_lines if (m := PAIR.match(ln.strip()))] or DEFAULT_PAIRS
    placeholder = False
    if "Brand" not in sections:
        out.append(f"rule 7: {THEME}: the theme has no Brand section")
    for line in sections.get("Brand", []):
        if not line.startswith("- "):
            continue
        match = BRAND.match(line)
        if not match:
            out.append(f"rule 7: {THEME}: a brand value has no source line")
        elif re.search(r"\[[^\]]*\]", match.group(2)):
            placeholder = True
    body = "\n".join(sections.get("Tokens", []))
    fences = re.findall(r"```css\n(.*?)```", body, re.S)
    if len(fences) != 1:
        out.append(f"rule 7: {THEME}: the theme does not hold one token block")
    else:
        out += token_problems(THEME, fences[0], pairs)[0]
    approved = False
    evidence = EVIDENCE.search("\n".join(sections.get("Evidence", [])))
    folder = root / MOCKUPS / evidence.group(1) if evidence else None
    if "Evidence" not in sections:
        out.append(f"rule 7: {THEME}: the theme has no Evidence section")
    elif folder is None or not folder.is_dir():
        out.append(f"rule 7: {THEME}: the evidence line points to no mockup folder")
    else:
        readme = folder / "README.md"
        approved = readme.is_file() and bool(APPROVAL.search(readme.read_text(encoding="utf-8")))
    return out, pairs, placeholder, approved


def cmd_check(root: Path) -> int:
    theme = root / THEME
    folders = sorted(p for p in (root / MOCKUPS).glob("*") if p.is_dir())
    if not theme.is_file() and not folders:
        print("ok design (no design record)")
        return 0
    problems: list[str] = []
    pairs = DEFAULT_PAIRS
    notes: list[str] = []
    if theme.is_file():
        found, pairs, placeholder, approved = theme_problems(
            root, theme.read_text(encoding="utf-8")
        )
        problems += found
        if not found and not approved:
            notes.append("design: the theme is not approved yet")
        if placeholder:
            notes.append("at risk design: placeholder brand")
    for folder in folders:
        problems += mockup_problems(root, folder, pairs)
    for line in notes if not problems else []:
        print(line)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print("ok design")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: check_design.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
