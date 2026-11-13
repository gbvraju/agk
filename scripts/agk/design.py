"""agk design: the writer of `/agk:design`, its screenshots and the inventory skeleton.

Usage:
    python3 design.py prototype [--root DIR]
    python3 design.py screenshots --folder FOLDER [--root DIR]
    python3 design.py screenshots --version v<n> [--root DIR]
    python3 design.py inventory [--root DIR]
    python3 design.py import <folder> [--root DIR]
    python3 design.py write ...   (refused: SPEC-0037 rule 12)

Kit-only (never installed). `prototype` writes the next version folder
`docs/design/prototype/v<n>/` from the standard, the theme and the agreed inventory
(`design_prototype.py`, SPEC-0037 rules 4 to 6 and 12); it refuses an inventory whose digest has no
`inventory` row in `docs/design/signoffs.md`. `write` no longer writes a mockup folder: it refuses,
`rule 12: a new mockup folder is not written; use /agk:design prototype`, and writes nothing; the
existing folders of `docs/design/mockups/` are only read and checked. `screenshots` takes four
pictures (360 and 1280 px wide, light and dark) of an existing mockup folder with a headless
browser found on PATH and runs nothing else; with none it says so and succeeds (SPEC-0029 rule 6).
`screenshots --version v<n>` (SPEC-0037 rule 8, `design_render.py`) opens each page of a prototype
version, offline, at each breakpoint of the standard in light and dark, and writes one screenshot
of each and `screenshots/reflow.json` (`ok` or `sideways`); with no browser it says
`design: no headless browser found; reflow not run`, writes every entry as `not run` and succeeds.
`import <folder>` (SPEC-0037 rule 15 as amendment 161 item 1 proposes, `design_import.py`) copies a
customer's prototype byte for byte into the next imported version `docs/design/imported/i<n>/files/`
with its `manifest.json` and `external.txt`, and refuses a symbolic link, a source inside
`docs/design/` and an empty folder, copying nothing; it reads files only and opens no page. When the
new version has exactly one HTML page and that page holds a `<script` element, it prints one line
`notice: i<n> has one page drawn by script; ...` pointing at the planning guide's step 0, and still
succeeds (brief #1204, ADR-0511).
`inventory` writes the skeleton of `docs/design/inventory.md` from
`kit/templates/design-inventory.md` (SPEC-0037 rule 3): one section for each requirement of
`docs/requirements.md`, its `- Specs:` filled from the `Requirements:` lines of `docs/specs/*.md`
(`none` when no spec names it), every other slot empty, and an empty `## Screens` part; a kit
requirement (REQ-001 to REQ-099) reads `- Screens: no screen: a rule of the kit` instead of an empty
slot. On an existing inventory it keeps every line and only appends, at the end of the Requirements
part and in number order, a section for each requirement that has none, printing `added REQ-<n>`
for each; it never removes or rewrites a section, refuses a file with no Requirements part and
never fills a project requirement's slot (brief #1185, ADR-0504). Messages name the rule, never a
value. No network and no model; `check_design.py` checks what `prototype` and `inventory` made. A
version's `screenshots/` folder is written only by `design.py screenshots`, never by hand.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_import
import design_inventory
import design_prototype
from common import PROJECT_FIRST_REQ, CheckError, parse_requirements

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
USAGE = (
    "usage: design.py prototype | screenshots --folder FOLDER | screenshots --version v<n>"
    " | inventory | import <folder>  [--root DIR]"
)
COMMANDS = ("prototype", "write", "screenshots", "inventory", "import")
WRITE_REFUSAL = "rule 12: a new mockup folder is not written; use /agk:design prototype"
FLAGS = ("--root", "--name", "--date", "--theme-file", "--folder", "--version")
FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$")
MOCKUPS = "docs/design/mockups"
THEME = "docs/design/theme.md"
INVENTORY = "docs/design/inventory.md"
REQUIREMENTS = "docs/requirements.md"
KIT_NO_SCREEN = "no screen: a rule of the kit"
SPEC_FILE = re.compile(r"^(\d{4})-[^/]*\.md$")
SPEC_REQS = re.compile(r"(?m)^- Requirements:\s*(.*?)\s*$")
REQ = re.compile(r"\bREQ-\d{3}\b")
BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")
SHOTS = (("360", 800), ("1280", 800))
# In Blink 0 is dark and 1 is light (measured on Chromium); both are passed so a shot never
# depends on the machine's own setting.
SCHEME = {
    "dark": "--blink-settings=preferredColorScheme=0",
    "light": "--blink-settings=preferredColorScheme=1",
}


class UsageError(Exception):
    """A command given an option it does not take: the usage text, exit 2 (never a ValueError,
    so a decode or JSON error is not shown as usage)."""


def template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def cmd_write(root: Path, opts: dict[str, str]) -> int:
    """SPEC-0037 rule 12 (`Q-S0037-10`): a new mockup folder is never written; nothing is."""
    raise CheckError(WRITE_REFUSAL)


def cmd_prototype(root: Path, opts: dict[str, str]) -> int:
    if set(opts) - {"root"}:
        raise UsageError("prototype takes only --root")
    return design_prototype.write(root)


def find_browser() -> str | None:
    for candidate in BROWSERS:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def cmd_screenshots(root: Path, opts: dict[str, str]) -> int:
    if "version" in opts:
        if "folder" in opts:
            raise UsageError("screenshots takes --folder or --version, not both")
        import design_render  # it imports this module: imported here, when it is needed

        return design_render.reflow(root, opts["version"])
    name = opts.get("folder", "")
    folder = root / MOCKUPS / name
    if not FOLDER.match(name) or not (folder / "index.html").is_file():
        raise CheckError("rule 6: the folder is not a mockup folder with an index.html")
    browser = find_browser()
    if browser is None:
        print("design: no headless browser found; screenshots skipped")
        return 0
    out = folder / "screenshots"
    out.mkdir(exist_ok=True)
    for width, height in SHOTS:
        for mode in ("light", "dark"):
            target = out / f"{width}-{mode}.png"
            command = [
                browser,
                "--headless",
                "--disable-gpu",
                f"--screenshot={target}",
                f"--window-size={width},{height}",
                SCHEME[mode],
                f"file://{folder / 'index.html'}",
            ]
            proc = subprocess.run(  # nosec B603 - a fixed argument list, no shell
                command, capture_output=True, text=True, encoding="utf-8"
            )
            if proc.returncode != 0 or not target.is_file():
                raise CheckError("rule 6: the headless browser did not make a screenshot")
    print(f"wrote 4 screenshots in {MOCKUPS}/{name}/screenshots/")
    return 0


def spec_index(root: Path) -> dict[str, list[str]]:
    """{REQ id: [SPEC ids]} from the `Requirements:` line of each numbered `docs/specs/*.md`."""
    index: dict[str, list[str]] = {}
    for path in sorted((root / "docs" / "specs").glob("*.md")):
        match = SPEC_FILE.match(path.name)
        if not match:
            continue  # the template and any other unnumbered file name no spec
        line = SPEC_REQS.search(path.read_text(encoding="utf-8"))
        for req in REQ.findall(line.group(1) if line else ""):
            spec = f"SPEC-{match.group(1)}"
            if spec not in index.setdefault(req, []):
                index[req].append(spec)
    return index


def requirement_section(req: dict, specs: dict[str, list[str]]) -> str:
    """One `### REQ-<n> \u2014 <title>` section: its specs, and an empty Screens slot or, for a kit
    requirement (REQ-001 to REQ-099), the kit's no-screen reason (brief #1185, ADR-0504)."""
    heading = f"### {req['id']} \u2014 {req['title']}" if req["title"] else f"### {req['id']}"
    named = ", ".join(specs.get(req["id"], [])) or "none"
    screens = f" {KIT_NO_SCREEN}" if int(req["id"][4:]) < PROJECT_FIRST_REQ else ""
    return f"{heading}\n\n- Specs: {named}\n- Screens:{screens}\n\n"


def update_inventory(target: Path, reqs: list[dict], specs: dict[str, list[str]]) -> int:
    """Append a section for each requirement that has none, before the part after Requirements;
    every other byte of the file is kept, and nothing is removed or rewritten."""
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise CheckError(f"rule 3: {INVENTORY} cannot be read") from None
    have = design_inventory.sectioned_requirements(text)
    if have is None:
        raise CheckError(f"rule 3: {INVENTORY} has no Requirements part; it is never rewritten")
    missing = sorted((r for r in reqs if r["id"] not in have), key=lambda r: int(r["id"][4:]))
    if not missing:
        return 0
    lines = text.splitlines(keepends=True)
    start = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("## ") and line[3:].strip() == "Requirements"
    )
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    before = "".join(lines[:end])
    if before and not before.endswith("\n"):
        before += "\n"
    if before and not before.endswith("\n\n"):
        before += "\n"
    added = "".join(requirement_section(r, specs) for r in missing)
    if end == len(lines):
        added = added.rstrip("\n") + "\n"
    target.write_text(before + added + "".join(lines[end:]), encoding="utf-8")
    for req in missing:
        print(f"added {req['id']}")
    return 0


def cmd_inventory(root: Path, opts: dict[str, str]) -> int:
    if set(opts) - {"root"}:
        raise UsageError("inventory takes only --root")
    target = root / INVENTORY
    try:
        reqs = parse_requirements((root / REQUIREMENTS).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        raise CheckError(f"rule 3: {REQUIREMENTS} cannot be read") from None
    specs = spec_index(root)
    if target.exists():
        return update_inventory(target, reqs, specs)
    sections = [requirement_section(req, specs) for req in reqs]
    text = template("design-inventory.md").replace("{{requirements}}\n", "".join(sections))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {INVENTORY}")
    return 0


def cmd_import(root: Path, source: str, opts: dict[str, str]) -> int:
    if set(opts) - {"root"}:
        raise UsageError("import takes a folder and only --root")
    version = design_import.import_folder(root, Path(source))
    notice = scripted_one_page(root, version)
    if notice:
        print(notice)
    return 0


def scripted_one_page(root: Path, version: str) -> str | None:
    """Brief #1204: the notice for a version of exactly one HTML page that holds a `<script`
    element, read as bytes only (nothing is run, no network), else None."""
    files = root / design_import.IMPORTED / version / design_import.FILES
    html = sorted(
        p for p in files.rglob("*") if p.is_file() and p.name.lower().endswith(design_import.PAGES)
    )
    if len(html) != 1 or b"<script" not in html[0].read_bytes().lower():
        return None
    return (
        f"notice: {version} has one page drawn by script; capture each screen and state as its"
        " own page and import that folder instead"
        ' (docs/guides/planning.md "From a prototype")'
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in COMMANDS:
        print(USAGE, file=sys.stderr)
        return 2
    source = None
    rest = args[1:]
    if args[0] == "import":
        if not rest or rest[0].startswith("--"):
            print(USAGE, file=sys.stderr)
            return 2
        source, rest = rest[0], rest[1:]
    opts: dict[str, str] = {}
    it = iter(rest)
    for arg in it:
        value = next(it, None)
        if arg not in FLAGS or value is None:
            print(USAGE, file=sys.stderr)
            return 2
        opts[arg[2:]] = value
    root = Path(opts.get("root", "."))
    try:
        if args[0] == "write":
            return cmd_write(root, opts)
        if args[0] == "prototype":
            return cmd_prototype(root, opts)
        if args[0] == "inventory":
            return cmd_inventory(root, opts)
        if source is not None:
            return cmd_import(root, source, opts)
        return cmd_screenshots(root, opts)
    except UsageError:
        print(USAGE, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL design: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
