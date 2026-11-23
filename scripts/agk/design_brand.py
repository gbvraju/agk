# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""A new theme filled from the discovery brand answer (SPEC-0037 rules 2, 7 and 12; brief #1840).

Kit-only (never installed); `design_prototype.theme_for` and `design.py theme` call
`theme_text(root, evidence)`. It reads the given `brand` answers of `docs/discovery/*.md` (the words
between `<!-- agk:answer sha256=... -->` and `<!-- agk:answer-end -->`) and fills `name`, `primary`
and `font` of `kit/templates/design-theme.md` only where it reads them without guessing: labelled
parts (`name: ...`, `primary: #rrggbb` or `#rgb`, `font: ...`, split at `;` or a line break), or,
with no label, the one hex colour of the answer and its first part as the name. A value it cannot
read keeps its bracketed placeholder; the logo line is always the template's; documents with
different brand answers fill nothing and print a note. A brand colour that fails a contrast pair of
the standard's roles in a mode is written as the first one-per-cent shade toward black (light) or
white (dark) that passes, with a proposal comment and an `ask the person:` line naming no value
(ADR-0770). The theme is read by the data guard before it is returned. Nothing of
`docs/design/imported/` is read (rule 13). Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_standard
import guard
from check_design import contrast
from common import CheckError

KIT = Path(__file__).resolve().parents[2]
TEMPLATE = KIT / "kit" / "templates" / "design-theme.md"
THEME = design_standard.THEME
DISCOVERY = "docs/discovery"
GIVEN = re.compile(r"^- brand: \(given: (.+)\)$")
START = re.compile(r"^<!-- agk:answer sha256=[0-9a-f]{64} -->$")
END = "<!-- agk:answer-end -->"
HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9A-Za-z])")
FONT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 -]{0,59}$")
LABELS = ("name", "primary", "font")
PROPOSAL = (
    "/* a shade of the brand primary for 4.5:1 (proposed; the person's sign-off confirms it) */"
)
DIFFERING = (
    "note: discovery documents give different brand answers; the brand record keeps its "
    "placeholders"
)
ASK = (
    "ask the person: The brand colour is {word} to read as text on the page; the theme uses a "
    "shade of it that reads at 4.5:1. Keep that shade? Yes or not yet; I recommend yes."
)
NO_SHADE = (
    "ask the person: The brand colour reads below 4.5:1 on the page in {modes} and no shade of it "
    "passes (rule 7); which colour should the theme use?"
)


def answers(root: Path) -> list[tuple[str, str, str]]:
    """(document, where it was given, words) of each given brand answer, in file order."""
    found = []
    for path in sorted((root / DISCOVERY).glob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines[:-1]):
            given = GIVEN.match(line)
            if given and START.match(lines[i + 1]) and END in lines[i + 2 :]:
                end = lines.index(END, i + 2)
                rel = f"{DISCOVERY}/{path.name}"
                found.append((rel, given.group(1), "\n".join(lines[i + 2 : end]).strip()))
                break
    return found


def name_ok(value: str) -> bool:
    return 0 < len(value) <= 60 and not re.search(r"[—\[\]]", value)


def expand(colour: str) -> str:
    digits = colour[1:]
    return "#" + ("".join(c * 2 for c in digits) if len(digits) == 3 else digits)


def parse(words: str) -> dict[str, str]:
    """The brand values an answer gives without guessing (brief #1840 answers 1 and 8)."""
    parts = [p.strip() for p in re.split(r"[;\n]", words) if p.strip()]
    labelled = {}
    for part in parts:
        label, colon, value = part.partition(":")
        if colon and label.strip().lower() in LABELS:
            labelled.setdefault(label.strip().lower(), value.strip())
    out: dict[str, str] = {}
    if labelled:
        if name_ok(labelled.get("name", "")):
            out["name"] = labelled["name"]
        if HEX.fullmatch(labelled.get("primary", "")):
            out["primary"] = expand(labelled["primary"])
        if FONT.match(labelled.get("font", "")):
            out["font"] = labelled["font"]
        return out
    colours = HEX.findall(words)
    if len(colours) == 1:
        out["primary"] = expand(colours[0])
    first = parts[0] if parts else ""
    if not HEX.search(first) and ":" not in first and name_ok(first):
        out["name"] = first
    return out


def brand(root: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """({value name: (value, source)}, notes) from the given brand answers of discovery."""
    given = answers(root)
    if not given:
        return {}, []
    if len({words for _, _, words in given}) > 1:
        return {}, [DIFFERING]
    rel, where, words = given[0]
    source = f"{rel} (brand, given: {where})"
    return {k: (v, source) for k, v in parse(words).items()}, []


def on_accent(colour: str, mode: str) -> str:
    roles = design_standard.LIGHT if mode == "light" else design_standard.DARK
    candidates = ("#ffffff", roles["text"], roles["on-accent"])
    return max(candidates, key=lambda c: contrast(colour, c))


def passes(colour: str, mode: str) -> bool:
    """Every `CONTRAST_PAIRS` row the accent meets, on the standard's roles of MODE."""
    roles = {**(design_standard.LIGHT if mode == "light" else design_standard.DARK)}
    roles.update({"accent": colour, "on-accent": on_accent(colour, mode)})
    return all(
        contrast(roles[a], roles[b]) >= minimum
        for a, b, minimum in design_standard.CONTRAST_PAIRS
        if "accent" in (a, b)
    )


def mix(colour: str, mode: str, percent: int) -> str:
    """COLOUR mixed PERCENT per cent toward black (light) or white (dark)."""
    target = 0 if mode == "light" else 255
    channels = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [int(c + (target - c) * percent / 100 + 0.5) for c in channels]
    return "#" + "".join(f"{c:02x}" for c in mixed)


def shade(colour: str, mode: str) -> str | None:
    """COLOUR when it passes in MODE, else the first shade that does, else None."""
    for percent in range(0, 101):
        candidate = colour if percent == 0 else mix(colour, mode, percent)
        if passes(candidate, mode):
            return candidate
    return None


def theme_block(template: str, primary: str | None, font: str | None) -> tuple[str, list[str]]:
    """The template's theme block with the brand's accent and font, and the lines to print."""
    found = design_standard._theme_block(template)
    light, dark = (dict(found[0]), dict(found[1])) if found else ({}, {})
    proposed, failed = [], []
    if primary:
        for mode, values in (("light", light), ("dark", dark)):
            chosen = shade(primary, mode)
            if chosen is None:
                failed.append(mode)
                chosen = primary
            elif chosen != primary:
                proposed.append(mode)
            values["--color-accent"] = chosen
            values["--color-on-accent"] = on_accent(chosen, mode)
    if font:
        name = f'"{font}"' if " " in font else font
        stack = f"{name}, system-ui, sans-serif"
        light.update({"--font-body": stack, "--font-heading": stack})

    def rule(values: dict[str, str], mode: str, indent: str) -> list[str]:
        note = [f"{indent}{PROPOSAL}"] if mode in proposed else []
        return note + [f"{indent}{k}: {v};" for k, v in values.items()]

    lines = [":root {", *rule(light, "light", "  "), "}", "@media (prefers-color-scheme: dark) {"]
    lines += ["  :root {", *rule(dark, "dark", "    "), "  }", "}"]
    notes = []
    if proposed:
        word = {
            ("light",): "too light",
            ("dark",): "too dark",
        }.get(tuple(proposed), "too light in light mode and too dark in dark mode")
        notes.append(ASK.format(word=word))
    if failed:
        notes.append(NO_SHADE.format(modes=" and ".join(failed)))
    return "\n".join(lines) + "\n", notes


def theme_text(root: Path, evidence: str) -> tuple[str, list[str]]:
    """(the new theme for EVIDENCE, the lines to print); refuses a theme the data guard flags."""
    text = TEMPLATE.read_text(encoding="utf-8").replace("{{evidence}}", evidence)
    values, notes = brand(root)
    if values:
        for key, (value, source) in values.items():
            line = f"- {key}: {value} — source: {source}"
            text = re.sub(rf"(?m)^- {key}: .*$", lambda _m, line=line: line, text)
    primary, font = values.get("primary", ("",))[0], values.get("font", ("",))[0]
    if primary or font:
        block, more = theme_block(text, primary, font)
        fence = r"(?s)(## Theme\n\n```css\n).*?(```)"
        text = re.sub(fence, lambda m: m.group(1) + block + m.group(2), text)
        notes += more
    if guard.scan_text(text):
        raise CheckError(
            f"rule 14: {THEME}: the theme holds text the data guard flags; nothing is written"
        )
    return text, notes
