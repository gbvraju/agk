"""agk design: the writer of `/agk:design`, its screenshots and the inventory skeleton.

Usage:
    python3 design.py write --name NAME [--date D] [--theme-file F] [--root DIR]
    python3 design.py screenshots --folder FOLDER [--root DIR]
    python3 design.py inventory [--root DIR]

Kit-only (never installed). `write` makes `docs/design/theme.md` (only when it is absent, from the
engine's draft or from the kit's template) and the mockup folder
`docs/design/mockups/<date>-<name>/` with `index.html` and `README.md`, from
`kit/templates/design-*`. The approval line is the owner's: the README holds `Approved: not yet`
and the script never writes `Approved by`. `screenshots` takes four pictures (360 and 1280 px
wide, light and dark) with a headless browser found on PATH and runs nothing else; with none it
says so and succeeds (SPEC-0029 rule 6). `inventory` writes the skeleton of
`docs/design/inventory.md` from `kit/templates/design-inventory.md` (SPEC-0037 rule 3): one section
for each requirement of `docs/requirements.md`, its `- Specs:` filled from the `Requirements:` lines
of `docs/specs/*.md` (`none` when no spec names it), every other slot empty, and an empty
`## Screens` part; it refuses when the file exists and never fills a slot. Messages name the rule,
never a value. No network and no model; `check_design.py` checks what `write` and `inventory` made.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, parse_requirements

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
USAGE = (
    "usage: design.py write --name NAME [--date D] [--theme-file F] | "
    "screenshots --folder FOLDER | inventory  [--root DIR]"
)
COMMANDS = ("write", "screenshots", "inventory")
FLAGS = ("--root", "--name", "--date", "--theme-file", "--folder")
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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


def template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def valid_date(text: str) -> bool:
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return False
    return bool(DATE.match(text))


def cmd_write(root: Path, opts: dict[str, str]) -> int:
    name = opts.get("name", "")
    if not NAME.match(name):
        raise CheckError("rule 6: the name is not a lower-case slug of at most 50 characters")
    date = opts["date"] if "date" in opts else datetime.now(UTC).date().isoformat()
    if not valid_date(date):
        raise CheckError("rule 6: the date is not a real YYYY-MM-DD")
    folder = root / MOCKUPS / f"{date}-{name}"
    if folder.exists():
        raise CheckError("rule 6: the mockup folder already exists; it is never overwritten")
    rel = f"{MOCKUPS}/{date}-{name}/"
    theme = root / THEME
    text = None
    if not theme.exists():
        if "theme-file" in opts:
            try:
                text = Path(opts["theme-file"]).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                raise CheckError("rule 6: the theme file cannot be read") from None
        else:
            text = template("design-theme.md").replace("{{evidence}}", f"{rel}")
    folder.mkdir(parents=True)
    (folder / "index.html").write_text(template("design-index.html"), encoding="utf-8")
    (folder / "README.md").write_text(
        template("design-readme.md").replace("{{folder}}", f"{date}-{name}"), encoding="utf-8"
    )
    print(f"wrote {rel}")
    if text is not None:
        theme.parent.mkdir(parents=True, exist_ok=True)
        theme.write_text(text, encoding="utf-8")
        print(f"wrote {THEME}")
    return 0


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
        raise ValueError("inventory takes only --root")
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
        if args[0] == "inventory":
            return cmd_inventory(root, opts)
        return cmd_screenshots(root, opts)
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL design: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
