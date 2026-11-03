"""agk design: the writer of `/agk:design`, its screenshots and the inventory skeleton.

Usage:
    python3 design.py prototype [--root DIR]
    python3 design.py screenshots --folder FOLDER [--root DIR]
    python3 design.py inventory [--root DIR]
    python3 design.py write ...   (refused: SPEC-0037 rule 12)

Kit-only (never installed). `prototype` writes the next version folder
`docs/design/prototype/v<n>/` from the standard, the theme and the agreed inventory
(`design_prototype.py`, SPEC-0037 rules 4 to 6 and 12); it refuses an inventory whose digest has no
`inventory` row in `docs/design/signoffs.md`. `write` no longer writes a mockup folder: it refuses,
`rule 12: a new mockup folder is not written; use /agk:design prototype`, and writes nothing; the
existing folders of `docs/design/mockups/` are only read and checked. `screenshots` takes four
pictures (360 and 1280 px wide, light and dark) of an existing mockup folder with a headless
browser found on PATH and runs nothing else; with none it says so and succeeds (SPEC-0029 rule 6).
`inventory` writes the skeleton of `docs/design/inventory.md` from
`kit/templates/design-inventory.md` (SPEC-0037 rule 3): one section for each requirement of
`docs/requirements.md`, its `- Specs:` filled from the `Requirements:` lines of `docs/specs/*.md`
(`none` when no spec names it), every other slot empty, and an empty `## Screens` part; it refuses
when the file exists and never fills a slot. Messages name the rule, never a value. No network and
no model; `check_design.py` checks what `prototype` and `inventory` made. A version's
`screenshots/` folder is written only by `design.py screenshots`, never by hand.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_prototype
from common import CheckError, parse_requirements

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
USAGE = "usage: design.py prototype | screenshots --folder FOLDER | inventory  [--root DIR]"
COMMANDS = ("prototype", "write", "screenshots", "inventory")
WRITE_REFUSAL = "rule 12: a new mockup folder is not written; use /agk:design prototype"
FLAGS = ("--root", "--name", "--date", "--theme-file", "--folder")
FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$")
MOCKUPS = "docs/design/mockups"
THEME = "docs/design/theme.md"
INVENTORY = "docs/design/inventory.md"
REQUIREMENTS = "docs/requirements.md"
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


def cmd_inventory(root: Path, opts: dict[str, str]) -> int:
    if set(opts) - {"root"}:
        raise UsageError("inventory takes only --root")
    target = root / INVENTORY
    if target.exists():
        raise CheckError(f"rule 3: {INVENTORY} already exists; it is never overwritten")
    try:
        reqs = parse_requirements((root / REQUIREMENTS).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        raise CheckError(f"rule 3: {REQUIREMENTS} cannot be read") from None
    specs = spec_index(root)
    sections = []
    for req in reqs:
        heading = f"### {req['id']} \u2014 {req['title']}" if req["title"] else f"### {req['id']}"
        named = ", ".join(specs.get(req["id"], [])) or "none"
        sections.append(f"{heading}\n\n- Specs: {named}\n- Screens:\n\n")
    text = template("design-inventory.md").replace("{{requirements}}\n", "".join(sections))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {INVENTORY}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in COMMANDS:
        print(USAGE, file=sys.stderr)
        return 2
    opts: dict[str, str] = {}
    it = iter(args[1:])
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
        return cmd_screenshots(root, opts)
    except UsageError:
        print(USAGE, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL design: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
