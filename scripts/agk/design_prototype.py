"""The prototype writer of `/agk:design prototype` (SPEC-0037 rules 4 to 6 and 12; brief #457).

Kit-only (never installed); `design.py prototype` calls `write(root)`. From the kit's design
standard, `docs/design/theme.md` and the agreed `docs/design/inventory.md`, and from nothing else,
it writes the next free version folder `docs/design/prototype/v<n>/` (`Q-S0037-4`): `index.html`
(the flows and the start of each demo path), one `<screen>--<state>.html` for each screen and each
state marked `yes` in the inventory, `standard.css` (the kit's standard unchanged), `theme.css` (the
theme block), `agk-prototype.js` (the kit's runtime unchanged), `demo.md` (one sentence for the
presenter per step of each flow) and `README.md`. A page is the pattern's block of
`kit/templates/design-patterns.md` for its state (a state the standard does not name uses the
`default` block), its fixture slots filled from `kit/templates/design-prototype/fixtures.json`
alone, inside `page.html`, with a state bar of plain relative links, plain relative links to the
screens of its `- Links to:` line and, on a demo step, plain links to the previous and next step.

It refuses, naming the rule and never a value: an inventory that does not exist or does not pass its
check; an inventory whose digest has no `inventory` row in `docs/design/signoffs.md` (rule 3); a
theme on the standard that does not pass the standard's theme check, or an old-format theme with a
token the standard has no role for (rule 2). With no theme it writes one from
`kit/templates/design-theme.md` with the evidence line set to the version; an old-format theme
(SPEC-0029) is moved to the standard by its `Standard:` line, its five tokens mapped by
`design_standard.OLD_TOKENS` to their roles unchanged in value in light and dark, and its brand
record, source lines and evidence line carried over unchanged (rule 12). Nothing is written before
every refusal has been checked, and a folder is never overwritten. Files only: no network, no model,
no process.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_inventory
import design_signoff
import design_standard
from common import CheckError

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
PROTOTYPE_KIT = TEMPLATES / "design-prototype"
PROTOTYPE = "docs/design/prototype"
THEME = "docs/design/theme.md"
INVENTORY = design_inventory.INVENTORY
VERSION = re.compile(r"^v([1-9]\d*)$")
SLOT = re.compile(r"\{\{([a-z][a-z0-9_.-]*)\}\}")
FIELD = re.compile(r"^- ([A-Za-z][\w -]*?):(.*)$")
FENCE = re.compile(r"```css\n(.*?)```", re.S)
DECLARATION = re.compile(r"^\s*(--[\w-]+)\s*:\s*([^;]*?)\s*$")
TO_INDEX = ("link.home", "link.back")
COPIED = {
    "standard.css": TEMPLATES / "design-standard.css",
    "agk-prototype.js": PROTOTYPE_KIT / "agk-prototype.js",
}
REFUSAL = "rule 3: the inventory has no inventory row in docs/design/signoffs.md for its digest"


# --- reading -------------------------------------------------------------------------------------


def patterns() -> dict[str, dict[str, str]]:
    """{pattern: {state: html block}} of the kit's pattern library."""
    found: dict[str, dict[str, str]] = {}
    text = (TEMPLATES / "design-patterns.md").read_text(encoding="utf-8")
    pattern = state = None
    for part in re.split(r"(?m)^(##+ .*)$", text):
        if part.startswith("### ") and pattern is not None:
            state = part[4:].strip()
        elif part.startswith("## "):
            pattern, state = part[3:].strip(), None
            found[pattern] = {}
        elif pattern is not None and state is not None:
            blocks = re.findall(r"```html\n(.*?)```", part, re.S)
            if blocks:
                found[pattern][state] = blocks[0].rstrip("\n")
    return found


def screens(root: Path) -> list[dict]:
    """The screens of the inventory, in file order, with their pages (the states marked `yes`)."""
    parts = design_inventory._parts((root / INVENTORY).read_text(encoding="utf-8"))
    found = []
    for heading, lines in parts.get("Screens", []):
        fields: dict[str, str] = {}
        states: list[str] = []
        for line in lines:
            match = FIELD.match(line)
            if not match:
                continue
            name, value = match.group(1).strip(), match.group(2).strip()
            if name.startswith("State "):
                if value == "yes":
                    states.append(name[len("State ") :].strip())
            else:
                fields.setdefault(name, value)
        links = fields.get("Links to", "none")
        found.append(
            {
                "id": heading,
                "title": heading.replace("-", " ").capitalize(),
                "flow": fields.get("Flow", ""),
                "pattern": fields.get("Pattern", ""),
                "links": []
                if links == "none"
                else [n.strip() for n in links.split(",") if n.strip()],
                "states": states,
            }
        )
    return found


def fixtures() -> dict[str, str]:
    """{`<group>.<key>`: value} of the kit's fixture set."""
    data = json.loads((PROTOTYPE_KIT / "fixtures.json").read_text(encoding="utf-8"))
    return {
        f"{group}.{key}": str(value)
        for group, values in data.items()
        if isinstance(values, dict)
        for key, value in values.items()
    }


def sections(text: str) -> list[tuple[str, list[str]]]:
    """[(heading, lines)] of a markdown text by its `## ` headings; the first heading is ''."""
    found: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        if line.startswith("## "):
            found.append((line[3:].strip(), []))
        else:
            found[-1][1].append(line)
    return found


def joined(parts: list[tuple[str, list[str]]]) -> str:
    out: list[str] = []
    for heading, lines in parts:
        if heading:
            out.append(f"## {heading}")
        out.extend(lines)
    return "\n".join(out).rstrip("\n") + "\n"


def layout(text: str) -> tuple[str, str]:
    """(density, alignment) of the theme's layout block."""
    values = {"density": "comfortable", "alignment": "start"}
    for heading, lines in sections(text):
        if heading != "Layout":
            continue
        for line in lines:
            match = re.match(r"^-\s*(density|alignment)\s*:\s*(\S+)\s*$", line.strip())
            if match:
                values[match.group(1)] = match.group(2)
    return values["density"], values["alignment"]


# --- the theme (rules 2 and 12) ------------------------------------------------------------------


def old_tokens(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """(light, dark) of an old-format theme's one token block; a token with no role is refused."""
    body = "\n".join(
        lines for heading, part in sections(text) if heading == "Tokens" for lines in part
    )
    fences = FENCE.findall(body)
    if len(fences) != 1:
        raise CheckError(f"rule 2: {THEME}: the old theme does not hold one token block")
    rules, outside = design_standard.css_rules(fences[0])
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    unknown = bool(outside.strip())
    for prelude, rule in rules:
        if prelude == ":root":
            target, bodies = light, [rule]
        elif design_standard.DARK_QUERY.match(prelude):
            inner, rest = design_standard.css_rules(rule)
            unknown = unknown or bool(rest.strip()) or any(p != ":root" for p, _ in inner)
            target, bodies = dark, [b for p, b in inner if p == ":root"]
        else:
            unknown = True
            continue
        for part in (p for b in bodies for p in b.split(";") if p.strip()):
            match = DECLARATION.match(part)
            if not match or match.group(1) not in design_standard.OLD_TOKENS:
                unknown = True
            else:
                target[match.group(1)] = match.group(2)
    if unknown:
        raise CheckError(
            f"rule 2: {THEME}: the old theme sets a token or rule the standard has no role for; "
            "move it by hand"
        )
    return light, dark


REPLACED = {"Tokens", "Contrast", "Rules"}  # the old sections the standard's text replaces


def with_logo(brand: list[str], logo: str) -> list[str]:
    """The Brand section with the template's placeholder logo line when it has none."""
    if any(design_standard.LOGO_LINE.match(line) for line in brand):
        return brand
    items = [i for i, ln in enumerate(brand) if ln.startswith("- ")]
    if items:
        return [*brand[: items[-1] + 1], logo, *brand[items[-1] + 1 :]]
    filled = [i for i, ln in enumerate(brand) if ln.strip()]
    if not filled:
        return ["", logo, ""]
    last = filled[-1] + 1
    return [*brand[:last], "", logo, *brand[last:]]


def moved_theme(text: str, version: str) -> str:
    """The old-format theme moved onto the standard (SPEC-0037 rules 2 and 12).

    The owner's title, the text before the first section and every section but Tokens, Contrast
    and Rules stay unchanged and in place; Tokens becomes the theme and layout blocks, Rules the
    standard's rules, Contrast goes (the standard computes it).
    """
    light, dark = old_tokens(text)
    old = sections(text)
    names = [heading for heading, _ in old[1:]]
    if {"Theme", "Layout"} & set(names) or len(names) != len(set(names)):
        raise CheckError(
            f"rule 2: {THEME}: the old theme has a section the standard's would replace; "
            "move it by hand"
        )
    template = dict(sections(template_theme().replace("{{evidence}}", f"{PROTOTYPE}/{version}/")))

    def block(values: dict[str, str], indent: str) -> list[str]:
        return [
            f"{indent}  {design_standard.token(design_standard.OLD_TOKENS[name])}: {values[name]};"
            for name in design_standard.OLD_TOKENS
            if name in values
        ]

    css = [":root {", *block(light, ""), "}"]
    if dark:
        css += [
            "@media (prefers-color-scheme: dark) {",
            "  :root {",
            *block(dark, "  "),
            "  }",
            "}",
        ]
    standard = f"Standard: agk design standard {design_standard.STANDARD}"
    lead = list(old[0][1])
    at = 1 if lead and lead[0].startswith("# ") else 0
    lead[at:at] = ["", standard] if at else [standard, ""]
    logo = next(ln for ln in template["Brand"] if design_standard.LOGO_LINE.match(ln))
    out: list[tuple[str, list[str]]] = [("", lead)]
    for heading, lines in old[1:]:
        if heading == "Brand":
            out.append((heading, with_logo(list(lines), logo)))
        elif heading == "Tokens":
            out.append(("Theme", ["", "```css", *css, "```", ""]))
            out.append(("Layout", list(template["Layout"])))
        elif heading == "Rules":
            out.append((heading, list(template["Rules"])))
        elif heading not in REPLACED:
            out.append((heading, list(lines)))
    # a standard section the old theme lacks goes after the standard section before it
    order = [h for h, _ in sections(template_theme())[1:]]
    for i, heading in enumerate(order):
        present = [h for h, _ in out]
        if heading in present:
            continue
        before = [present.index(h) for h in order[:i] if h in present]
        at = max(before, default=0) + 1
        lines = list(template[heading])
        if lines and lines[-1].strip():
            lines.append("")
        out.insert(at, (heading, lines))
    return joined(out)


def template_theme() -> str:
    return (TEMPLATES / "design-theme.md").read_text(encoding="utf-8")


def theme_for(root: Path, version: str) -> tuple[str, str | None, str]:
    """(the theme text the version uses, the text to write or None, what to print)."""
    path = root / THEME
    if not path.is_file():
        text = template_theme().replace("{{evidence}}", f"{PROTOTYPE}/{version}/")
        return text, text, f"wrote {THEME}"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise CheckError(f"rule 2: {THEME} cannot be read") from None
    if design_standard.theme_format(text) == "old":
        moved = moved_theme(text, version)
        return moved, moved, f"moved {THEME} to agk design standard {design_standard.STANDARD}"
    if design_standard.standard_theme_problems(text):
        raise CheckError(f"rule 2: {THEME}: the theme does not pass the standard's theme check")
    return text, None, ""


# --- the pages (rules 4 to 6) --------------------------------------------------------------------


def page_name(screen: str, state: str) -> str:
    return f"{screen}--{state}.html"


def entry(screen: dict) -> str:
    """The page a link to SCREEN opens: its `default` page, else its first page."""
    if "default" in screen["states"]:
        return page_name(screen["id"], "default")
    return page_name(screen["id"], screen["states"][0]) if screen["states"] else "index.html"


def fill(block: str, screen: dict, by_id: dict[str, dict], data: dict[str, str]) -> str:
    """BLOCK with its slots filled: links to pages of the folder, data from the fixtures only."""
    targets = [entry(by_id[n]) for n in screen["links"] if n in by_id] or [entry(screen)]
    links: dict[str, str] = {}

    def value(match: re.Match) -> str:
        key = match.group(1)
        if key in TO_INDEX:
            return "index.html"
        if key.startswith("link."):
            if key not in links:
                links[key] = targets[len(links) % len(targets)]
            return links[key]
        if key == "page.title":
            return html.escape(screen["title"])
        if key not in data:
            raise CheckError("rule 6: a pattern slot has no value in the fixture set")
        return html.escape(data[key])

    return SLOT.sub(value, block)


def sentence(screen: dict, by_id: dict[str, dict]) -> str:
    """The presenter's one sentence for SCREEN's step of its flow."""
    text = (
        f"Open the {screen['title'].lower()} screen ({screen['pattern']}) of the "
        f"{screen['flow']} flow"
    )
    named = [by_id[n]["title"].lower() for n in screen["links"] if n in by_id]
    if named:
        listed = named[0] if len(named) == 1 else ", ".join(named[:-1]) + " and " + named[-1]
        text += ", and show that it leads on to " + listed
    return text.replace(".", "") + "."


def flows(all_screens: list[dict]) -> dict[str, list[dict]]:
    """{flow: [its screens with a page]} in the inventory's order."""
    found: dict[str, list[dict]] = {}
    for screen in all_screens:
        if screen["states"]:
            found.setdefault(screen["flow"], []).append(screen)
    return found


def nav_list(label: str, items: list[str], extra: str = "") -> str:
    """A `nav` of plain links in a row that wraps (`.cluster`), at every breakpoint."""
    lines = [f'<nav class="cluster" aria-label="{html.escape(label)}"{extra}>', *items, "</nav>"]
    return "\n".join(lines)


def link(href: str, text: str, attrs: str = "") -> str:
    return f'<a class="nav-link" href="{href}"{attrs}>{html.escape(text)}</a>'


def page(
    screen: dict,
    state: str,
    by_id: dict[str, dict],
    library: dict[str, dict[str, str]],
    data: dict[str, str],
    demo: dict[str, tuple[str, str, str, str]],
    shell: str,
) -> str:
    blocks = library[screen["pattern"]]
    block = fill(blocks.get(state, blocks["default"]), screen, by_id, data)
    bar = [
        link(
            page_name(screen["id"], s),
            s,
            ' aria-current="page"' if s == state else "",
        )
        for s in screen["states"]
    ]
    parts = [nav_list(f"States of {screen['title'].lower()}", bar, ' id="states"')]
    heading = "" if "<h1" in block else f"<h1>{html.escape(screen['title'])}</h1>\n"
    if "<main" in block:
        parts.append(heading + block)
    else:
        parts.append(f'<main id="main" class="stack">\n{heading}{block}\n</main>')
    linked = [by_id[n] for n in screen["links"] if n in by_id]
    if linked:
        parts.append(
            nav_list("Links to other screens", [link(entry(s), s["title"]) for s in linked])
        )
    name = page_name(screen["id"], state)
    if name in demo:
        text, previous, following, where = demo[name]
        parts.append(
            nav_list(
                f"Demo: {where}",
                [
                    link(previous, "Previous step", ' rel="prev"'),
                    link(following, "Next step", ' rel="next"'),
                ],
                f' data-demo="{html.escape(text)}"',
            )
        )
    parts.append('<p><a href="index.html">All flows</a></p>')
    title = f"{screen['title']}, {state}"
    return shell.replace("{{title}}", html.escape(title)).replace("{{content}}", "\n".join(parts))


def demo_steps(
    paths: dict[str, list[dict]], by_id: dict[str, dict]
) -> tuple[dict[str, tuple[str, str, str, str]], str]:
    """({step page: (sentence, previous, next, where)}, the text of `demo.md`)."""
    steps: dict[str, tuple[str, str, str, str]] = {}
    lines: list[str] = []
    for flow, members in paths.items():
        lines += ["", f"## {flow}", ""]
        names = [entry(s) for s in members]
        for number, screen in enumerate(members, 1):
            text = sentence(screen, by_id)
            previous = names[number - 2] if number > 1 else "index.html"
            following = names[number] if number < len(names) else "index.html"
            where = f"step {number} of {len(names)} of the {flow} flow"
            steps[names[number - 1]] = (text, previous, following, where)
            lines.append(f"{number}. `{names[number - 1]}`: {text}")
    return steps, "\n".join(lines)


def index(paths: dict[str, list[dict]], shell: str, version: str) -> str:
    parts = []
    for number, (flow, members) in enumerate(paths.items(), 1):
        start = entry(members[0])
        items = []
        for screen in members:
            states = ", ".join(
                f'<a href="{page_name(screen["id"], s)}">{html.escape(s)}</a>'
                for s in screen["states"]
            )
            items.append(f'<li class="list-item">{html.escape(screen["title"])}: {states}</li>')
        parts.append(
            "\n".join(
                [
                    f'<section class="stack" aria-labelledby="flow-{number}">',
                    f'<h2 id="flow-{number}">{html.escape(flow)}</h2>',
                    f'<p><a class="button button-primary" href="{start}#demo">'
                    f"Start the demo of {html.escape(flow)}</a></p>",
                    '<ul class="list">',
                    *items,
                    "</ul>",
                    "</section>",
                ]
            )
        )
    return shell.replace("{{title}}", f"Prototype {version}").replace("{{flows}}", "\n".join(parts))


# --- writing -------------------------------------------------------------------------------------


def next_version(root: Path) -> str:
    folder = root / PROTOTYPE
    numbers = [
        int(m.group(1))
        for p in (folder.iterdir() if folder.is_dir() else [])
        if (m := VERSION.match(p.name))  # a file named `v<n>` is counted too: never reused
    ]
    return f"v{max(numbers, default=0) + 1}"


def agreed(root: Path) -> None:
    """Refuse an inventory that is missing, fails its check, or has no `inventory` row."""
    if not (root / INVENTORY).is_file():
        raise CheckError(f"rule 3: {INVENTORY} does not exist")
    if design_inventory.inventory_problems(root):
        raise CheckError("rule 3: the inventory does not pass its check; run check_design.py")
    digest = design_signoff.inventory_digest(root)
    rows = design_signoff.rows(root)
    if not any(r["kind"] == "inventory" and r["digest"] == digest for r in rows):
        raise CheckError(REFUSAL)


def build(root: Path, version: str) -> tuple[dict[str, str], str | None, str]:
    """({file name: text} of the version folder, the theme to write or None, what to print)."""
    theme, theme_out, note = theme_for(root, version)
    density, alignment = layout(theme)
    all_screens = screens(root)
    by_id = {s["id"]: s for s in all_screens}
    library = patterns()
    data = fixtures()
    for screen in all_screens:
        if screen["pattern"] not in library:
            raise CheckError(f"rule 3: {screen['id']}: the pattern is not one of the standard's")

    def shell(name: str) -> str:
        text = (PROTOTYPE_KIT / name).read_text(encoding="utf-8")
        return text.replace("{{density}}", density).replace("{{alignment}}", alignment)

    paths = flows(all_screens)
    steps, demo_text = demo_steps(paths, by_id)
    out: dict[str, str] = {}
    page_shell = shell("page.html")
    for screen in all_screens:
        for state in screen["states"]:
            out[page_name(screen["id"], state)] = page(
                screen, state, by_id, library, data, steps, page_shell
            )
    out["index.html"] = index(paths, shell("index.html"), version)
    block = FENCE.findall(joined([s for s in sections(theme) if s[0] == "Theme"]))[0]
    out["theme.css"] = (
        f"/* theme.css of {PROTOTYPE}/{version}/: the theme block of {THEME} "
        "(SPEC-0037 rule 2), loaded after standard.css. */\n" + block
    )
    out["demo.md"] = (
        f"# Demo paths of {version}\n\nOne sentence for the presenter per step of each flow "
        "(SPEC-0037 rule 4). Start each path from `index.html`; in a page, d shows the sentence, "
        "n opens the next step and p the previous one.\n" + demo_text + "\n"
    )
    out["README.md"] = (
        (PROTOTYPE_KIT / "README.md").read_text(encoding="utf-8").replace("{{version}}", version)
    )
    return out, theme_out, note


def write(root: Path) -> int:
    agreed(root)
    version = next_version(root)
    out, theme_out, note = build(root, version)
    folder = root / PROTOTYPE / version
    try:
        folder.mkdir(parents=True, exist_ok=False)  # never overwritten
    except (FileExistsError, NotADirectoryError):
        raise CheckError(
            f"rule 4: {PROTOTYPE}/{version}/ cannot be made; nothing is overwritten"
        ) from None
    for name, text in out.items():
        (folder / name).write_text(text, encoding="utf-8")
    for name, source in COPIED.items():
        (folder / name).write_bytes(source.read_bytes())  # byte-equal to the kit's file
    print(f"wrote {PROTOTYPE}/{version}/")
    if theme_out is not None:
        (root / THEME).write_text(theme_out, encoding="utf-8")
        print(note)
    return 0
