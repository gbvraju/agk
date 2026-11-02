"""The inventory check (SPEC-0037 rule 3). Installed: `kit/manifest.json` lists it in `verbatim`,
and `check_design.py` imports it.

`inventory_problems(root)` reads `docs/design/inventory.md` and `docs/requirements.md` and returns
one `rule 3: docs/design/inventory.md: <screen or REQ id>: <what>` for each problem: an empty slot
(a `- <field>:` line with nothing after the colon), a requirement without a section or with neither
screens nor a `no screen:` reason, a section for no requirement, a screen named by a requirement
with no section, a screen id that is not a lower-case slug, a screen listed twice, a pattern that is
not one of the standard's, a link to an unknown screen (a screen that links nowhere reads `none`),
a screen without `default` or a required state, a state that is neither `yes` nor `n/a: <reason>`,
a missing part and a line that is not a field of the inventory. It names the rule and the screen,
never a value. Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_standard
from common import parse_requirements

INVENTORY = "docs/design/inventory.md"
REQUIREMENTS = "docs/requirements.md"
PARTS = ("Requirements", "Screens")
REQ_HEADING = re.compile(r"^(REQ-\d{3})(?:\s+—.*)?$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FIELD = re.compile(r"^- ([A-Za-z][\w -]*?):(.*)$")
NO_SCREEN = re.compile(r"^no screen:(.*)$")
NOT_APPLICABLE = re.compile(r"^n/a:(.*)$")
REQ_FIELDS = ("Specs", "Screens")
SCREEN_FIELDS = ("Flow", "Pattern", "Links to")


def _parts(text: str) -> dict[str, list[tuple[str, list[str]]]]:
    """{part: [(heading, its `- ` lines)]} of the `## ` parts; prose and the intro are skipped."""
    parts: dict[str, list[tuple[str, list[str]]]] = {}
    sections: list[tuple[str, list[str]]] | None = None
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            sections = parts.setdefault(line[3:].strip(), [])
            current = None
        elif line.startswith("### ") and sections is not None:
            current = []
            sections.append((line[4:].strip(), current))
        elif line.startswith("- ") and current is not None:
            current.append(line.rstrip())
    return parts


def _fields(where: str, lines: list[str], out: list[str]) -> dict[str, str]:
    """{field: text} of a section's lines; an empty slot or a line of no field is a problem."""
    found: dict[str, str] = {}
    for line in lines:
        match = FIELD.match(line)
        if not match:
            out.append(f"{where}: a line is not a field of the inventory")
            continue
        name, value = match.group(1).strip(), match.group(2).strip()
        if not value:
            out.append(f"{where}: the slot {name} is empty")
        found.setdefault(name, value)
    return found


def _names(text: str) -> list[str]:
    return [n.strip() for n in text.split(",") if n.strip()]


def _requirement_problems(
    sections: list[tuple[str, list[str]]], known: list[str], screens: set[str], out: list[str]
) -> None:
    seen: set[str] = set()
    for heading, lines in sections:
        match = REQ_HEADING.match(heading)
        if not match:
            out.append("a requirement section is not headed by its id")
            continue
        req = match.group(1)
        if req in seen:
            out.append(f"{req}: the requirement has more than one section")
            continue
        seen.add(req)
        if req not in known:
            out.append(f"{req}: the section names no requirement")
            continue
        found = _fields(req, lines, out)
        for name in found:
            if name not in REQ_FIELDS:
                out.append(f"{req}: a line is not a field of the inventory")
        if "Specs" not in found:
            out.append(f"{req}: the field Specs is missing")
        text = found.get("Screens", "")
        reason = NO_SCREEN.match(text)
        if reason:
            if not reason.group(1).strip():
                out.append(f"{req}: the requirement has neither a screen nor a no-screen reason")
        elif "Screens" not in found:
            out.append(f"{req}: the requirement has neither a screen nor a no-screen reason")
        elif any(name not in screens for name in _names(text)):
            out.append(f"{req}: a screen it names has no section")
    for req in known:
        if req not in seen:
            out.append(f"{req}: the requirement has no section")


def _state_problems(screen: str, found: dict[str, str], out: list[str]) -> None:
    states = {name[len("State ") :].strip(): text for name, text in found.items()}
    standard = set(design_standard.STATES)
    for state in design_standard.STATES:
        if state not in states:
            out.append(f"{screen}: the state {state} is missing")
    for state, text in states.items():
        if not text:
            continue  # an empty slot, already named
        reason = NOT_APPLICABLE.match(text)
        if text == "yes" or (reason and reason.group(1).strip()):
            continue
        if state in standard:
            out.append(f"{screen}: the state {state} is not yes or n/a: <reason>")
        else:
            out.append(f"{screen}: a state is not yes or n/a: <reason>")


def _screen_problems(sections: list[tuple[str, list[str]]], out: list[str]) -> None:
    names = {heading for heading, _ in sections}
    seen: set[str] = set()
    for heading, lines in sections:
        if not SLUG.match(heading):
            out.append("a screen id is not a lower-case slug")
            continue
        if heading in seen:
            out.append(f"{heading}: the screen has more than one section")
            continue
        seen.add(heading)
        found = _fields(heading, lines, out)
        for name in found:
            if name not in SCREEN_FIELDS and not name.startswith("State "):
                out.append(f"{heading}: a line is not a field of the inventory")
        for name in SCREEN_FIELDS:
            if name not in found:
                out.append(f"{heading}: the field {name} is missing")
        pattern = found.get("Pattern", "")
        if pattern and pattern not in design_standard.PATTERNS:
            out.append(f"{heading}: the pattern is not one of the standard's")
        links = found.get("Links to", "")
        if links != "none" and any(link not in names for link in _names(links)):
            out.append(f"{heading}: a link names no screen of the inventory")
        _state_problems(heading, {n: v for n, v in found.items() if n.startswith("State ")}, out)


def inventory_problems(root: Path) -> list[str]:
    """The rule 3 problems of `docs/design/inventory.md`; an empty list when it passes."""
    text = (root / INVENTORY).read_text(encoding="utf-8")
    req_path = root / REQUIREMENTS
    reqs = req_path.read_text(encoding="utf-8") if req_path.is_file() else ""
    known = [r["id"] for r in parse_requirements(reqs)]
    parts = _parts(text)
    out: list[str] = []
    for part in PARTS:
        if part not in parts:
            out.append(f"the inventory has no {part} part")
    screens = parts.get("Screens", [])
    _requirement_problems(parts.get("Requirements", []), known, {h for h, _ in screens}, out)
    _screen_problems(screens, out)
    return [f"rule 3: {INVENTORY}: {problem}" for problem in out]
