"""agk design compare: match or drift of each built screen against its signed-off version.

Usage:
    python3 design_compare.py --version v<n> --screens "<screen>/<state>, ..." [--root DIR]

Kit-only (never installed), run by the builder of a UI build before it marks its pull request
ready (SPEC-0037 rule 11, brief #461); `proof.py`, the CI proof job and `check_pr_body.py` do not
run or read it (`Q-S0037-11`). `--screens` takes the brief's `Screens:` pairs: `<screen>/*` is
every state of the screen, and a bare `*` every page of the version. For each pair it runs the
`render` command of `[design]` (read through `common.config_source`; split into words, no shell,
run in the root) with `AGK_DESIGN_SCREEN`, `AGK_DESIGN_STATE` and `AGK_DESIGN_OUT` set, reads
`<out>/<screen>--<state>.html` and compares it with the frozen page of
`docs/design/prototype/<version>/`: the structure (the landmarks, the heading outline, the controls
with their labels and the text of the links in order; the prototype's own state bar, demo bar,
link to `index.html` and runtime are left out), the tokens used (the standard's custom properties
referenced by `var()` in the page and in the stylesheets it links in its folder, except the
version's copy of the standard, `standard.css`, whose own references are not the page's) and, with a
headless browser (`design_render.py`), the share of differing pixels at each breakpoint and mode
against `pixel_tolerance` (default 0.01).

It prints one line per screen and state, `<screen>/<state> match` or
`<screen>/<state> drift: structure, tokens, pixels` (the kinds found), ending `; pixels: not run`
without a browser, and exits 0 on drift: it fails nothing. It exits 1 only on a usage error, an
unset or failing `render`, a bad `pixel_tolerance`, a version without a `design` row in
`docs/design/signoffs.md` or a pair the version has no page for, naming the setting or the rule
and never a value. It writes nothing into the project; no network (the browser runs offline).
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_brief
import design_render
import design_signoff
from common import CheckError, config_source

KIT = Path(__file__).resolve().parents[2]
STANDARD = KIT / "kit" / "templates" / "design-standard.css"
STANDARD_COPY = "standard.css"  # the kit's standard as `design.py prototype` copies it
USAGE = 'usage: design_compare.py --version v<n> --screens "<screen>/<state>, ..." [--root DIR]'
FLAGS = ("--version", "--screens", "--root")
DEFAULT_TOLERANCE = 0.01
DECLARED = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
USED = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
LANDMARKS = {"header", "nav", "main", "aside", "footer", "form", "search"}
CONTROLS = {"input", "select", "textarea", "button"}
HEADINGS = {f"h{n}": n for n in range(1, 7)}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
NOT_SIGNED = f"rule 11: the version has no design row in {design_signoff.SIGNOFFS}"
NO_RENDER = "rule 11: render in [design] of agk.toml is not set"
RENDER_FAILED = "rule 11: the render command of [design] (setting: render) wrote no page"
BAD_TOLERANCE = "rule 11: pixel_tolerance in [design] of agk.toml is not a share from 0 to 1"
UNREADABLE = "rule 11: agk.toml cannot be read (setting: [design])"


class UsageError(Exception):
    """Options the command does not take."""


def _words(text: str) -> str:
    return " ".join(text.split())


class Outline(HTMLParser):
    """The structure of a page, with the prototype's own parts left out."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[tuple] = []
        self.stylesheets: list[str] = []
        self.css: list[str] = []
        self.skip = 0  # depth inside a prototype-only element
        self.stack: list[str] = []
        self.text: list[list[str]] = []  # open text collectors (headings, links, buttons, labels)
        self.labels: dict[str, str] = {}
        self.pending: list[tuple] = []  # controls waiting for their `label for`
        self.in_style = False

    def _prototype_only(self, tag: str, attrs: dict[str, str | None]) -> bool:
        return (
            attrs.get("id") == "states"
            or "data-demo" in attrs
            or tag == "script"
            or (tag == "a" and attrs.get("href") == "index.html")
        )

    def handle_starttag(self, tag: str, attr_list: list) -> None:
        attrs = {k: v for k, v in attr_list}
        if tag == "style":
            self.in_style = True
        if tag == "link" and "stylesheet" in (attrs.get("rel") or "").split():
            self.stylesheets.append(attrs.get("href") or "")
        if attrs.get("style"):
            self.css.append(attrs["style"] or "")
        if self.skip or self._prototype_only(tag, attrs):
            if tag not in VOID:
                self.skip += 1
            return
        if tag in VOID:
            self._element(tag, attrs, closed=True)
            return
        self.stack.append(tag)
        self._element(tag, attrs, closed=False)

    def _element(self, tag: str, attrs: dict[str, str | None], closed: bool) -> None:
        role = attrs.get("role")
        if tag in LANDMARKS or role:
            self.items.append(("landmark", role or tag, attrs.get("aria-label") or ""))
        if tag in HEADINGS or tag == "a" or tag == "button" or tag == "label":
            self.text.append([])
        if tag == "label":
            self._label_for = attrs.get("for") or ""
        if tag in CONTROLS and tag != "button":
            self.pending.append(
                (tag, attrs.get("type") or "", attrs.get("aria-label") or "", attrs.get("id") or "")
            )
            self.items.append(("control", len(self.pending) - 1))

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False
        if self.skip:
            if tag not in VOID:
                self.skip -= 1
            return
        if tag not in self.stack:
            return
        while self.stack and self.stack.pop() != tag:
            pass
        if tag in HEADINGS or tag in ("a", "button", "label"):
            text = _words(" ".join(self.text.pop())) if self.text else ""
            if tag in HEADINGS:
                self.items.append(("heading", HEADINGS[tag], text))
            elif tag == "a":
                self.items.append(("link", text))
            elif tag == "button":
                self.items.append(("button", text))
            elif getattr(self, "_label_for", ""):
                self.labels[self._label_for] = text

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.css.append(data)
            return
        if self.skip:
            return
        for collector in self.text:
            collector.append(data)

    def structure(self) -> list[tuple]:
        out = []
        for item in self.items:
            if item[0] == "control":
                tag, kind, aria, ident = self.pending[item[1]]
                out.append(("control", tag, kind, aria or self.labels.get(ident, "")))
            else:
                out.append(item)
        return out


def standard_tokens() -> set[str]:
    return set(DECLARED.findall(STANDARD.read_text(encoding="utf-8")))


def read_page(path: Path) -> tuple[list[tuple], set[str]]:
    """(the structure, the standard's tokens used) of a page and its own linked stylesheets."""
    parser = Outline()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    css = list(parser.css)
    folder = path.parent.resolve()
    for href in parser.stylesheets:
        sheet = (folder / href).resolve()
        if sheet.is_file() and sheet.parent == folder and sheet.name != STANDARD_COPY:
            css.append(sheet.read_text(encoding="utf-8"))
    used = set(USED.findall("\n".join(css))) & standard_tokens()
    return parser.structure(), used


def settings(root: Path) -> tuple[list[str], float]:
    """(the `render` command as words, `pixel_tolerance`) of `[design]`, refused naming each."""
    try:
        design = config_source(root).get("design", {})
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError(UNREADABLE) from None
    if not isinstance(design, dict):
        raise CheckError(UNREADABLE)
    render = design.get("render", "")
    if not isinstance(render, str) or not render.strip():
        raise CheckError(NO_RENDER)
    tolerance = design.get("pixel_tolerance", DEFAULT_TOLERANCE)
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise CheckError(BAD_TOLERANCE)
    if not 0 <= tolerance <= 1:
        raise CheckError(BAD_TOLERANCE)
    try:
        words = shlex.split(render)
    except ValueError:
        raise CheckError(NO_RENDER) from None
    return words, float(tolerance)


def pairs(root: Path, version: str, screens: str) -> list[tuple[str, str]]:
    """The (screen, state) pairs named, `*` expanded as `check_brief.py` reads a Screens line."""
    signed = {r["version"] for r in design_signoff.rows(root) if r["kind"] == "design"}
    if version not in signed:
        raise CheckError(NOT_SIGNED)
    if screens.strip() == "*":
        folder = root / design_signoff.PROTOTYPE / version
        found = []
        for page in design_render.pages(folder):
            screen, _, state = page[:-5].rpartition("--")
            found.append((screen, state))
        return found
    try:
        return check_brief.screens_named(f"Screens: {version} {screens.strip()}", root)
    except CheckError as exc:
        if str(exc) == check_brief.SHAPE:
            raise UsageError from None
        raise CheckError(str(exc).replace("rule 10:", "rule 11:", 1)) from None


def render(root: Path, command: list[str], screen: str, state: str, out: Path) -> Path:
    env = dict(os.environ)
    env.update(AGK_DESIGN_SCREEN=screen, AGK_DESIGN_STATE=state, AGK_DESIGN_OUT=str(out))
    try:
        proc = subprocess.run(  # nosec B603 - the project's own command, no shell
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise CheckError(RENDER_FAILED) from None
    page = out / f"{screen}--{state}.html"
    if proc.returncode != 0 or not page.is_file():
        raise CheckError(RENDER_FAILED)
    return page


def pixels_drift(browser: str, frozen: Path, built: Path, tolerance: float, scratch: Path) -> bool:
    for width in design_render.BREAKPOINTS:
        for mode in design_render.MODES:
            first = scratch / f"frozen-{width}-{mode}.png"
            second = scratch / f"built-{width}-{mode}.png"
            design_render.shoot(browser, frozen, width, mode, first)
            design_render.shoot(browser, built, width, mode, second)
            if design_render.pixel_share(first, second) > tolerance:
                return True
    return False


def compare(root: Path, version: str, screens: str) -> int:
    if not design_signoff.VERSION.match(version):
        raise UsageError
    command, tolerance = settings(root)
    named = pairs(root, version, screens)
    folder = root / design_signoff.PROTOTYPE / version
    browser = design_render.find_browser()
    for screen, state in named:
        with tempfile.TemporaryDirectory(prefix="agk-compare-") as scratch:
            out = Path(scratch) / "out"
            out.mkdir()
            built = render(root, command, screen, state, out)
            frozen = folder / f"{screen}--{state}.html"
            frozen_structure, frozen_tokens = read_page(frozen)
            built_structure, built_tokens = read_page(built)
            kinds = []
            if frozen_structure != built_structure:
                kinds.append("structure")
            if frozen_tokens != built_tokens:
                kinds.append("tokens")
            if browser is not None and pixels_drift(
                browser, frozen, built, tolerance, Path(scratch)
            ):
                kinds.append("pixels")
        line = f"{screen}/{state} " + (f"drift: {', '.join(kinds)}" if kinds else "match")
        print(line + ("" if browser is not None else "; pixels: not run"))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    opts: dict[str, str] = {}
    it = iter(args)
    try:
        for arg in it:
            value = next(it, None)
            if arg not in FLAGS or value is None or arg[2:] in opts:
                raise UsageError
            opts[arg[2:]] = value
        if not {"version", "screens"} <= set(opts):
            raise UsageError
        return compare(Path(opts.get("root", ".")), opts["version"], opts["screens"])
    except UsageError:
        print(USAGE)
        return 1
    except CheckError as exc:
        print(f"FAIL design-compare: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
