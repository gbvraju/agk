"""The planning sources of a project that starts from an idea (SPEC-0043 rule 2b as amendment 174
item 2 proposes; REQ-050; brief #1216, ADR-0515). Installed: `kit/manifest.json` lists it in
`verbatim`.

    python3 plan_sources.py vision [--root DIR]
    python3 plan_sources.py architecture [--root DIR]

`vision` writes once, as a new file only, `docs/sources/vision.md`: rule 1's header
(`Source: vision and project charter ADR-<n>`, `Kind: charter`, `Version: ADR-<n> <digest>`, the
digest of `constitution/vision.md` and the charter ADR by `design_signoff.digest`, `Date:` from the
clock in UTC) and one blank line, then the text of `constitution/vision.md` and then the text of the
charter ADR `docs/adr/<n>-project-charter.md`, both unchanged, so every heading is kept.
`architecture` writes once `docs/sources/architecture.md` (`Source: stack ADR-<n>`, `Kind: other`,
`Version: ADR-<n> <digest>`, `Date:`) with the text of the stack ADR `docs/adr/<n>-stack-options.md`
unchanged. The ADR read is the highest-numbered file of that name. Each refuses with exit 1, naming
the rule and the file and writing nothing, an ADR whose first `- Status:` line is not `Accepted`, a
missing ADR or vision, and an existing target file; a malformed command exits 2 with the usage.
`vision_text(root)` and `architecture_text(root)` return the text and write nothing. Files only: no
network, no model.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_signoff
from common import STATUS_LINE, CheckError

SOURCES = "docs/sources"
ADR = "docs/adr"
VISION = "constitution/vision.md"
VISION_SOURCE = f"{SOURCES}/vision.md"
ARCH_SOURCE = f"{SOURCES}/architecture.md"
CHARTER = re.compile(r"^(\d{4})-project-charter\.md$")
STACK = re.compile(r"^(\d{4})-stack-options\.md$")
USAGE = "usage: plan_sources.py vision|architecture [--root DIR]"


def _read(path: Path, rel: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise CheckError(
            f"rule 2b: {rel}: the file cannot be read as text; nothing is written"
        ) from None


def accepted_adr(root: Path, name: re.Pattern[str], what: str) -> tuple[str, str, str]:
    """(`ADR-<n>`, path, text) of the highest-numbered ADR named NAME; refuses one not Accepted."""
    folder = root / ADR
    found = sorted(
        (p for p in folder.iterdir() if p.is_file() and name.match(p.name))
        if folder.is_dir()
        else [],
        key=lambda p: p.name,
    )
    if not found:
        raise CheckError(f"rule 2b: no {what} ADR under {ADR}/; nothing is written")
    path = found[-1]
    rel = path.relative_to(root).as_posix()
    text = _read(path, rel)
    status = next((m.group(1) for m in map(STATUS_LINE.match, text.splitlines()) if m), None)
    if status != "Accepted":
        raise CheckError(f"rule 2b: {rel}: the {what} ADR is not Accepted; nothing is written")
    number = name.match(path.name).group(1)  # type: ignore[union-attr]
    return f"ADR-{number}", rel, text


def _header(source: str, kind: str, version: str, today: str | None) -> list[str]:
    date = today or datetime.now(UTC).date().isoformat()
    return [f"Source: {source}", f"Kind: {kind}", f"Version: {version}", f"Date: {date}", ""]


def _body(*texts: str) -> str:
    return "\n".join(text.rstrip("\n") + "\n" for text in texts)


def vision_text(root: Path, today: str | None = None) -> str:
    """The vision source: the vision and the Accepted charter ADR, every heading kept."""
    if not (root / VISION).is_file():
        raise CheckError(f"rule 2b: {VISION}: the vision does not exist; nothing is written")
    vision = _read(root / VISION, VISION)
    adr, rel, charter = accepted_adr(root, CHARTER, "charter")
    digest = design_signoff.digest(root, [VISION, rel])
    head = _header(f"vision and project charter {adr}", "charter", f"{adr} {digest}", today)
    return "\n".join(head) + "\n" + _body(vision, charter)


def architecture_text(root: Path, today: str | None = None) -> str:
    """The architecture source: the Accepted stack ADR, every heading kept."""
    adr, rel, stack = accepted_adr(root, STACK, "stack")
    digest = design_signoff.digest(root, [rel])
    head = _header(f"stack {adr}", "other", f"{adr} {digest}", today)
    return "\n".join(head) + "\n" + _body(stack)


def write_once(root: Path, rel: str, text_of) -> Path:
    """Write REL once from TEXT_OF(root), never over an existing file."""
    path = root / rel
    if path.exists():
        raise CheckError(f"rule 2b: {rel}: the file exists; nothing is written")
    text = text_of(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:  # never over an existing file
        handle.write(text)
    print(f"wrote {rel} ({text.count(chr(10) + '#')} headings)")
    return path


COMMANDS = {
    "vision": (VISION_SOURCE, vision_text),
    "architecture": (ARCH_SOURCE, architecture_text),
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args.pop(0) if args else ""
    root_arg: str | None = None
    if args[:1] == ["--root"] and len(args) == 2:
        root_arg = args[1]
    elif args:
        command = ""
    if command not in COMMANDS:
        print(USAGE, file=sys.stderr)
        return 2
    from common import repo_root, run

    root = Path(root_arg) if root_arg else repo_root()
    rel, text_of = COMMANDS[command]

    def write() -> int:
        write_once(root, rel, text_of)
        return 0

    return run("plan-sources", write)


if __name__ == "__main__":
    sys.exit(main())
