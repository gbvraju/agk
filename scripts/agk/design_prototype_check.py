"""The checks of a prototype version folder (SPEC-0037 rules 5, 7 and 8; brief #458).

Installed: `kit/manifest.json` lists it in `verbatim`, and `check_design.py` calls
`version_problems(root, version)` for each `docs/design/prototype/v<n>/`. It reads the folder and
`docs/design/inventory.md` and returns one
`rule <n>: docs/design/prototype/<version>/<screen>--<state>: <what>` for each problem (a folder
file such as `theme.css` stands where the screen is):

- rule 7: a screen and state marked `yes` in the inventory with no page, or a page for none (an
  `n/a:` state needs no page);
- rule 7: a link or a loaded file (`href`, `src`, `srcset`, `poster`, `data`, `action`) that does
  not resolve to a file of the same folder;
- rule 5: an inline script, an event handler attribute, a `javascript:` link, a script element
  other than one `<script src="agk-prototype.js"></script>` at the end of the page, another script
  file, or a runtime file whose SHA-256 is not in `RUNTIME_HASHES` (`Q-S0037-5`);
- rule 5: a `link` element other than the folder's `standard.css` and `theme.css`, `@import`, a
  `url()` of anything outside the folder, or a frame, object, embed or base element;
- rule 7: a colour outside the tokens; a contrast below 4.5:1 for text or 3:1 for large text and UI
  parts, in light or dark, computed from `standard.css` and `theme.css`; a placeholder; an email
  address, link host or phone number not in the fixture set (`FIXTURE_EMAILS`, `FIXTURE_HOSTS`,
  `FIXTURE_PHONES`, the values of the kit's `fixtures.json`: the installed check never reads the
  kit); a form control without a label, an image without `alt`, not exactly one `h1`, a skipped
  heading level, no `lang`, a positive `tabindex`, no `:focus-visible` style, no viewport line, or
  a fixed width over 360 px outside a media query;
- rule 8: a `sideways` entry of `screenshots/reflow.json`, naming the breakpoint, and a record that
  cannot be read. `reflow_not_run(root, version)` is true when the record is absent, lacks an entry
  or has a `not run` one: information, never `ok` for reflow.

It never names the value it found. Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_inventory
import design_standard

PROTOTYPE = "docs/design/prototype"
VERSION = re.compile(r"^v[1-9]\d*$")
RUNTIME = "agk-prototype.js"
STYLESHEETS = ("standard.css", "theme.css")
REFLOW = "screenshots/reflow.json"
MODES = ("light", "dark")
REFLOW_RESULTS = ("ok", "sideways", "not run")
# The SHA-256 of each released runtime of the kit (`agk-prototype.js`), oldest first.
RUNTIME_HASHES = ("00f6853d42f9f12c0deb6cbebcd881cba79a00479ab96c12b7cec0a72d20318b",)
# The values of the kit's fixture set, `fixtures.json` (a kit test keeps them equal).
FIXTURE_EMAILS = ("ada.fenwick@example.com", "tomas.okafor@example.org")
FIXTURE_HOSTS = ("www.example.org",)
FIXTURE_PHONES = ("+1 202 555 0143", "+44 20 7946 0958")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
HOST = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://([^/\s\"'<>:?#]+)")
PHONE = re.compile(r"\+\d[\d ()-]{6,}\d|\(\d{2,5}\)\s?\d[\d -]{4,}\d|\b\d{3}[ .-]\d{3}[ .-]\d{4}\b")
PLACEHOLDER = re.compile(r"\[[^\]\n]*\]|\{\{[^}\n]*\}\}|(?i:lorem ipsum)|\bTODO\b|\bTBD\b")
FOCUS_VISIBLE = re.compile(r":focus-visible[^{}]*\{")
URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
WIDE_PROPERTIES = ("width", "min-width", "inline-size", "min-inline-size")
LENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(px|rem|em)\b", re.I)
MAX_FIXED = 360
LOADING = ("src", "srcset", "poster", "data", "action")
EXTERNAL_ELEMENTS = ("iframe", "frame", "object", "embed", "base", "portal")
CONTROLS = ("input", "select", "textarea")
UNLABELLED_INPUTS = ("hidden", "submit", "button", "reset", "image")
END_SCRIPT = re.compile(r'<script src="agk-prototype\.js"></script>\s*</body>\s*</html>\s*$', re.I)


def versions(root: Path) -> list[str]:
    """The version folders `v<n>` of `docs/design/prototype/` that hold a file, in number order.

    An empty folder is not a version: the writer never leaves one, and it has nothing to show.
    """
    folder = root / PROTOTYPE
    if not folder.is_dir():
        return []
    found = [
        p.name
        for p in folder.iterdir()
        if p.is_dir()
        and VERSION.match(p.name)
        and any(p.iterdir())  # an empty folder is no version
    ]
    return sorted(found, key=lambda name: int(name[1:]))


def expected_pages(root: Path) -> set[str] | None:
    """{`<screen>--<state>`} of every state marked `yes`, or None without an inventory."""
    path = root / design_inventory.INVENTORY
    if not path.is_file():
        return None
    parts = design_inventory._parts(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for screen, lines in parts.get("Screens", []):
        for line in lines:
            match = design_inventory.FIELD.match(line)
            if match and match.group(1).strip().startswith("State "):
                if match.group(2).strip() == "yes":
                    found.add(f"{screen}--{match.group(1).strip()[len('State ') :].strip()}")
    return found


# --- reading a page ------------------------------------------------------------------------------


class Page(HTMLParser):
    """What the checks read of one page: its elements, attributes, text and style."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.scripts: list[tuple[dict[str, str | None], str]] = []
        self.styles: list[str] = []
        self.headings: list[int] = []
        self.label_for: set[str] = set()
        self.controls: list[tuple[dict[str, str | None], bool]] = []
        self.text: list[str] = []
        self._labels = 0
        self._in: str | None = None
        self._body: list[str] = []
        self._attrs: dict[str, str | None] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        self.tags.append((tag, found))
        if tag in ("script", "style"):
            self._in, self._body, self._attrs = tag, [], found
        elif tag == "label":
            self._labels += 1
            if found.get("for"):
                self.label_for.add(str(found["for"]))
        elif tag in CONTROLS:
            kind = str(found.get("type") or "").lower()
            if tag != "input" or kind not in UNLABELLED_INPUTS:
                self.controls.append((found, self._labels > 0))
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))

    def handle_endtag(self, tag: str) -> None:
        if tag == self._in:
            body = "".join(self._body)
            if tag == "script":
                self.scripts.append((self._attrs, body))
            else:
                self.styles.append(body)
            self._in = None
        elif tag == "label" and self._labels:
            self._labels -= 1

    def handle_data(self, data: str) -> None:
        if self._in:
            self._body.append(data)
        else:
            self.text.append(data)


def parse(text: str) -> Page:
    page = Page()
    page.feed(text)
    page.close()
    if page._in == "script":  # an unclosed script element is still a script
        page.scripts.append((page._attrs, "".join(page._body)))
    return page


def in_folder(folder: Path, target: str) -> bool:
    """Whether TARGET (a link or a loaded file) is a file of FOLDER itself."""
    path = target.split("#", 1)[0]
    if not path:
        return True  # a fragment of the same page
    if ":" in path or "/" in path or "\\" in path or path in (".", ".."):
        return False
    return (folder / path).is_file()


# --- css -----------------------------------------------------------------------------------------


def css_without_tokens(css: str) -> str:
    """CSS with its `:root` token rules (light and the dark media) taken out."""
    rules, outside = design_standard.css_rules(css)
    kept: list[str] = [outside]
    for prelude, body in rules:
        if prelude == ":root":
            continue
        if design_standard.DARK_QUERY.match(prelude):
            inner, rest = design_standard.css_rules(body)
            body = rest + "".join(f"{p} {{{b}}}" for p, b in inner if p != ":root")
        kept.append(f"{prelude} {{{body}}}")
    return "\n".join(kept)


def declarations(body: str) -> list[tuple[str, str]]:
    out = []
    for part in body.split(";"):
        name, colon, value = part.partition(":")
        if colon:
            out.append((name.strip().lower(), value.strip()))
    return out


def is_wide(name: str, value: str) -> bool:
    if name not in WIDE_PROPERTIES:
        return False
    for number, unit in LENGTH.findall(value):
        size = float(number) * (1 if unit.lower() == "px" else 16)
        if size > MAX_FIXED:
            return True
    return False


def wide_css(css: str) -> bool:
    """Whether CSS sets a fixed width over 360 px outside a media query."""
    rules, _ = design_standard.css_rules(css)
    for prelude, body in rules:
        if prelude.lower().startswith("@media"):
            continue
        if prelude.startswith("@"):
            if wide_css(body):
                return True
            continue
        if any(is_wide(n, v) for n, v in declarations(body)):
            return True
    return False


def css_problems(folder: Path, where: str, css: str) -> list[str]:
    """`@import` and `url()` of anything outside the folder (rule 5)."""
    out: list[str] = []
    clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if re.search(r"@import\b", clean, re.I):
        out.append(f"rule 5: {where}: the stylesheet uses @import")
    if any(not in_folder(folder, target.strip()) for _, target in URL.findall(clean)):
        out.append(f"rule 5: {where}: url() names a file outside the folder")
    return out


def role_colours(css: str) -> tuple[dict[str, str], dict[str, str]]:
    """(light, dark) of the `--color-<role>` tokens of CSS."""
    rules, _ = design_standard.css_rules(css)
    light: dict[str, str] = {}
    dark: dict[str, str] = {}

    def take(body: str, into: dict[str, str]) -> None:
        for name, value in declarations(body):
            if name.startswith("--color-"):
                into[name[len("--color-") :]] = value

    for prelude, body in rules:
        if prelude == ":root":
            take(body, light)
        elif design_standard.DARK_QUERY.match(prelude):
            for inner, inner_body in design_standard.css_rules(body)[0]:
                if inner == ":root":
                    take(inner_body, dark)
    return light, dark


def contrast_problems(where: str, standard: str, theme: str) -> list[str]:
    """The contrast of rule 7, after the theme's overrides (the cascade), in light and dark."""
    import check_design

    std_light, std_dark = role_colours(standard)
    th_light, th_dark = role_colours(theme)
    modes = (
        ("light", {**std_light, **th_light}),
        ("dark", {**std_light, **std_dark, **th_light, **th_dark}),
    )
    out: list[str] = []
    for mode, values in modes:
        for first, second, minimum in design_standard.CONTRAST_PAIRS:
            a, b = values.get(first, ""), values.get(second, "")
            if not (check_design.HEX.match(a) and check_design.HEX.match(b)):
                out.append(f"rule 7: {where}: a colour role of a contrast pair is not a hex colour")
                return out
            if check_design.contrast(a, b) < minimum:
                ratio = f"{minimum:g}:1 in {mode}"
                out.append(f"rule 7: {where}: contrast below {ratio} for {first} on {second}")
    return out


# --- one page ------------------------------------------------------------------------------------


def script_problems(where: str, text: str, page: Page) -> list[str]:
    out: list[str] = []
    if any("src" not in attrs or body.strip() for attrs, body in page.scripts):
        out.append(f"rule 5: {where}: the page holds an inline script")
    if any(name.startswith("on") for _, attrs in page.tags for name in attrs):
        out.append(f"rule 5: {where}: the page holds an event handler attribute")
    values = [str(v) for _, attrs in page.tags for v in attrs.values() if v]
    if any(re.search(r"javascript\s*:", re.sub(r"\s", "", v), re.I) for v in values):
        out.append(f"rule 5: {where}: the page holds a javascript: link")
    external = [attrs for attrs, _ in page.scripts if "src" in attrs]
    if any(attrs != {"src": RUNTIME} for attrs in external):
        out.append(f"rule 5: {where}: the page loads a script other than the kit's runtime")
    elif page.scripts and (len(page.scripts) != 1 or not END_SCRIPT.search(text)):
        out.append(f"rule 5: {where}: the runtime is not one script element at the end of the page")
    return out


def link_problems(folder: Path, where: str, page: Page) -> list[str]:
    out: list[str] = []
    sheets = [attrs for tag, attrs in page.tags if tag == "link"]
    allowed: list[dict[str, str | None]] = [
        {"rel": "stylesheet", "href": name} for name in STYLESHEETS
    ]
    if any(attrs not in allowed for attrs in sheets) or any(sheets.count(a) > 1 for a in allowed):
        out.append(f"rule 5: {where}: a link element other than the folder's two stylesheets")
    if any(tag in EXTERNAL_ELEMENTS for tag, _ in page.tags):
        out.append(f"rule 5: {where}: the page makes an external request or loads a resource")
    broken = False
    for tag, attrs in page.tags:
        targets = []
        if tag in ("a", "area", "link") and attrs.get("href") is not None:
            targets.append(str(attrs["href"]).strip())
        if tag != "script":
            for name in LOADING:
                value = attrs.get(name)
                if value is None:
                    continue
                if name == "srcset":
                    targets += [part.split()[0] for part in str(value).split(",") if part.split()]
                else:
                    targets.append(str(value).strip())
        if any(not in_folder(folder, t) for t in targets):
            broken = True
    if broken:
        out.append(f"rule 7: {where}: a link does not resolve to a file of the folder")
    return out


def data_problems(where: str, text: str) -> list[str]:
    """Email addresses, link hosts and phone numbers outside the fixture set (rule 6)."""
    emails = {e.lower() for e in FIXTURE_EMAILS}
    hosts = {h.lower() for h in FIXTURE_HOSTS}
    phones = {re.sub(r"\D", "", p) for p in FIXTURE_PHONES}
    if (
        any(e.lower() not in emails for e in EMAIL.findall(text))
        or any(h.lower() not in hosts for h in HOST.findall(text))
        or any(re.sub(r"\D", "", p) not in phones for p in PHONE.findall(text))
    ):
        return [f"rule 7: {where}: the page holds data that is not in the fixture set"]
    return []


def access_problems(where: str, page: Page, sheets: str) -> list[str]:
    out: list[str] = []
    labelled = [
        inside
        or bool(str(attrs.get("aria-label") or "").strip())
        or bool(str(attrs.get("aria-labelledby") or "").strip())
        or (attrs.get("id") is not None and str(attrs.get("id")) in page.label_for)
        for attrs, inside in page.controls
    ]
    if not all(labelled):
        out.append(f"rule 7: {where}: a form control has no label")
    if any(tag == "img" and "alt" not in attrs for tag, attrs in page.tags):
        out.append(f"rule 7: {where}: an image has no alt text")
    if page.headings.count(1) != 1:
        out.append(f"rule 7: {where}: the page does not have exactly one h1")
    if any(b > a + 1 for a, b in zip(page.headings, page.headings[1:], strict=False)):
        out.append(f"rule 7: {where}: a heading level is skipped")
    html_tags = [attrs for tag, attrs in page.tags if tag == "html"]
    if not html_tags or not str(html_tags[0].get("lang") or "").strip():
        out.append(f"rule 7: {where}: the page has no lang")

    def positive(value: str | None) -> bool:
        try:
            return int(str(value).strip()) > 0
        except ValueError:
            return False

    if any(positive(attrs.get("tabindex")) for _, attrs in page.tags if "tabindex" in attrs):
        out.append(f"rule 7: {where}: an element has a positive tabindex")
    if not FOCUS_VISIBLE.search(re.sub(r"/\*.*?\*/", "", sheets, flags=re.S)):
        out.append(f"rule 7: {where}: the page has no :focus-visible style")
    viewport = [
        attrs
        for tag, attrs in page.tags
        if tag == "meta" and str(attrs.get("name") or "").lower() == "viewport"
    ]
    if not any(
        "width=device-width" in str(a.get("content") or "").replace(" ", "") for a in viewport
    ):
        out.append(f"rule 7: {where}: the page has no viewport line")
    return out


def page_problems(folder: Path, where: str, text: str, sheets: dict[str, str]) -> list[str]:
    import check_design

    page = parse(text)
    out = script_problems(where, text, page)
    out += link_problems(folder, where, page)
    style = "\n".join(page.styles)
    inline = [str(a["style"]) for _, a in page.tags if a.get("style")]
    out += css_problems(folder, where, style + "\n" + "\n".join(inline))
    out += check_design.colour_problems(where, style, inline)
    readable = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    readable = re.sub(r"<(script|style)\b.*?</\1\s*>", "", readable, flags=re.S | re.I)
    if PLACEHOLDER.search(readable):
        out.append(f"rule 7: {where}: the page holds a placeholder")
    out += data_problems(where, readable)
    linked = [
        str(attrs.get("href"))
        for tag, attrs in page.tags
        if tag == "link" and attrs.get("href") in sheets
    ]
    out += access_problems(where, page, style + "\n" + "\n".join(sheets[n] for n in linked))
    if wide_css(style) or any(is_wide(n, v) for body in inline for n, v in declarations(body)):
        out.append(f"rule 7: {where}: a fixed width over 360 px outside a media query")
    return out


# --- the folder ----------------------------------------------------------------------------------


def folder_problems(folder: Path, rel: str, sheets: dict[str, str]) -> list[str]:
    """The runtime, the other script files and the two stylesheets of the folder."""
    import check_design

    out: list[str] = []
    runtime = folder / RUNTIME
    if runtime.is_file():
        if hashlib.sha256(runtime.read_bytes()).hexdigest() not in RUNTIME_HASHES:
            out.append(
                f"rule 5: {rel}/{RUNTIME}: the runtime's hash is not a released runtime hash"
            )
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in (".js", ".mjs") and path.name != RUNTIME:
            out.append(f"rule 5: {rel}/{path.name}: a script file other than the kit's runtime")
    for name, css in sheets.items():
        where = f"{rel}/{name}"
        out += css_problems(folder, where, css)
        out += check_design.colour_problems(where, css_without_tokens(css), [])
        if wide_css(css):
            out.append(f"rule 7: {where}: a fixed width over 360 px outside a media query")
    out += contrast_problems(
        f"{rel}/theme.css", sheets.get("standard.css", ""), sheets.get("theme.css", "")
    )
    return out


def reflow_entries(folder: Path) -> list[tuple[str, int, str, str]] | None:
    """[(page, breakpoint, mode, result)] of `screenshots/reflow.json`, None when absent.

    Raises ValueError when the record cannot be read as the list of entries.
    """
    path = folder / REFLOW
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("not a list of entries")
    out = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("an entry is not an object")
        page, width, mode = item.get("page"), item.get("breakpoint"), item.get("mode")
        result = item.get("result")
        if (
            not isinstance(page, str)
            or isinstance(width, bool)
            or not isinstance(width, int)
            or mode not in MODES
            or result not in REFLOW_RESULTS
        ):
            raise ValueError("an entry is not page, breakpoint, mode and result")
        out.append((page.removesuffix(".html"), width, mode, result))
    return out


def reflow_problems(root: Path, version: str) -> list[str]:
    folder = root / PROTOTYPE / version
    try:
        entries = reflow_entries(folder)
    except (OSError, UnicodeDecodeError, ValueError):
        return [f"rule 8: {version}/{REFLOW}: the reflow record cannot be read"]
    out: list[str] = []
    for page, width, _mode, result in entries or []:
        line = f"rule 8: {version}/{page}: the page scrolls sideways at {width} px"
        if result == "sideways" and line not in out:
            out.append(line)
    return out


def reflow_not_run(root: Path, version: str) -> bool:
    """True when the reflow test of VERSION has not run for every page, breakpoint and mode."""
    folder = root / PROTOTYPE / version
    try:
        entries = reflow_entries(folder)
    except (OSError, UnicodeDecodeError, ValueError):
        return True
    if entries is None or any(result == "not run" for *_, result in entries):
        return True
    pages = expected_pages(root) or set()
    pages &= {p.stem for p in folder.glob("*.html")}
    seen = {(page, width, mode) for page, width, mode, _ in entries}
    return any(
        (page, width, mode) not in seen
        for page in pages
        for width in design_standard.BREAKPOINTS
        for mode in MODES
    )


def version_problems(root: Path, version: str) -> list[str]:
    """The problems of `docs/design/prototype/<version>/`; an empty list when it passes."""
    folder = root / PROTOTYPE / version
    rel = f"{PROTOTYPE}/{version}"
    out: list[str] = []
    expected = expected_pages(root)
    pages = {p.stem: p for p in sorted(folder.glob("*.html")) if p.is_file()}
    if expected is None:
        out.append(f"rule 7: {rel}: there is no inventory to check the pages against")
    else:
        for name in sorted(expected - set(pages)):
            out.append(f"rule 7: {rel}/{name}: the state has no page")
        for name in sorted(set(pages) - expected - {"index"}):
            out.append(
                f"rule 7: {rel}/{name}: the page is for no screen and state of the inventory"
            )
    sheets: dict[str, str] = {}
    for name in STYLESHEETS:
        path = folder / name
        if path.is_file():
            sheets[name] = path.read_text(encoding="utf-8", errors="replace")
    out += folder_problems(folder, rel, sheets)
    for name, path in pages.items():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out.append(f"rule 7: {rel}/{name}: the page cannot be read as UTF-8 text")
            continue
        out += page_problems(folder, f"{rel}/{name}", text, sheets)
    out += reflow_problems(root, version)
    return out
