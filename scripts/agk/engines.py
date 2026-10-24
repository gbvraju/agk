"""agk engines: the idea in the vision and the discovery questions (SPEC-0029 rule 4).

Usage:
    python3 engines.py questions
    python3 engines.py vision-write --idea-file F [--draft-file D] [--root DIR]
    python3 engines.py vision-check [--root DIR]

Kit-only (never installed). An engine (a skill named in `[engines]` of `agk.toml`) only drafts
text; this script writes it through the kit's templates and checks it, and it decides nothing.
`vision-write` puts the idea, unchanged, as the first section of `constitution/vision.md`, between
two markers with the SHA-256 of the idea, so `vision-check` can tell an altered idea; the four
sections of `/agk:start` follow, from the draft or from the template with `TODO(owner)` marks.
Messages name the rule and never quote the idea. No network and no model.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from common import CheckError

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
USAGE = (
    "usage: engines.py questions | vision-write --idea-file F [--draft-file D] | vision-check | "
    "[--root DIR]"
)
FLAGS = ("--root", "--idea-file", "--draft-file")
VISION = "constitution/vision.md"
MAX_IDEA = 1500
OPEN = "<!-- agk-idea sha256:"
CLOSE = "<!-- /agk-idea -->"
IDEA_HEADING = "## The idea"
HEADINGS = (
    "## What this is for",
    "## Who it serves",
    "## How success is measured",
    "## Out of scope",
)
QUESTIONS = (
    ("users", "Who are the users, and who pays for it?"),
    (
        "existing",
        "What already exists: repositories, hosting, identity, data, and which of it is private?",
    ),
    ("runs", "Where does it run, and must it be portable between places?"),
    ("data", "What data does it store, and for how long?"),
    ("scale", "What scale is expected, in users, volume and growth?"),
    ("compliance", "Which rules, laws or contracts must it meet?"),
    (
        "devices",
        "Which devices and screen widths must it work on, from the narrowest to the widest?",
    ),
    ("accessibility", "Which accessibility needs must it meet, and to which standard?"),
    ("languages", "Which languages must it speak, and in which order of priority?"),
    (
        "brand",
        "What brand does it carry: name, colours, type, logo, and where each is written down?",
    ),
)
TOPICS = tuple(topic for topic, _ in QUESTIONS)
INSTALLED_PLACEHOLDER = "TODO(maintainers)"
PLACEHOLDER = re.compile(r"TODO\(owner\)")


def idea_of(text: str) -> tuple[str, str] | None:
    """(recorded digest, idea text) between the markers of the first section, else None."""
    start = text.find(OPEN)
    end = text.find(CLOSE)
    if start < 0 or end < start:
        return None
    head, _, rest = text[start + len(OPEN) :].partition(" -->\n\n")
    return head.strip(), rest[: end - start - len(OPEN) - len(head) - len(" -->\n\n")].rstrip("\n")


def has_idea(text: str) -> bool:
    return OPEN in text


def vision_problems(text: str) -> list[str]:
    """SPEC-0029 rule 4: the idea is the first section, and is what the owner gave."""
    if not has_idea(text):
        return []
    out: list[str] = []
    lines = text.splitlines()
    headings = [ln for ln in lines if ln.startswith("## ")]
    found = idea_of(text)
    if not headings or headings[0] != IDEA_HEADING or found is None:
        out.append("rule 4: the first section of the vision is not the idea between its markers")
    else:
        before = text[: text.find(IDEA_HEADING)].strip()
        if before != "# Vision":
            out.append("rule 4: something stands before the idea section of the vision")
        digest, idea = found
        if hashlib.sha256(idea.encode("utf-8")).hexdigest() != digest:
            out.append("rule 4: the idea section was changed after it was written")
    rest = text.split(CLOSE, 1)[-1]
    if PLACEHOLDER.search(rest):
        out.append("rule 4: the sections after the idea are not drafted yet")
    if OPEN in rest:
        out.append("rule 4: the idea marker appears twice")
    return out


def cmd_questions() -> int:
    for topic, question in QUESTIONS:
        print(f"{topic}\t{question}")
    return 0


def read(path: Path, what: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise CheckError(f"rule 4: {what} cannot be read") from None


def cmd_vision_write(root: Path, opts: dict[str, str]) -> int:
    if "idea-file" not in opts:
        raise CheckError("rule 4: --idea-file is required")
    idea = read(Path(opts["idea-file"]), "the idea file").strip("\n")
    if not idea.strip():
        raise CheckError("rule 4: the idea is empty")
    if len(idea) > MAX_IDEA:
        raise CheckError(f"rule 4: the idea is over {MAX_IDEA} characters")
    if CLOSE in idea or OPEN in idea:
        raise CheckError("rule 4: the idea holds a marker of the idea section")
    target = root / VISION
    current = target.read_text(encoding="utf-8") if target.is_file() else ""
    if has_idea(current):
        raise CheckError("rule 4: the vision already holds an idea; it is never overwritten")
    if current and INSTALLED_PLACEHOLDER not in current:
        raise CheckError(
            "rule 4: the vision is not the installed placeholder; a vision that holds "
            "content is never overwritten"
        )
    if "draft-file" in opts:
        draft = read(Path(opts["draft-file"]), "the draft file").strip("\n") + "\n"
        lines = draft.splitlines()
        positions = [lines.index(h) if h in lines else -1 for h in HEADINGS]
        if -1 in positions or positions != sorted(positions):
            raise CheckError(
                "rule 4: the draft lacks one of the four headings, or they are out of order"
            )
        if has_idea(draft) or IDEA_HEADING in lines or PLACEHOLDER.search(draft):
            raise CheckError("rule 4: the draft holds the idea section or a placeholder")
        body = draft
    else:
        body = (TEMPLATES / "vision-sections.md").read_text(encoding="utf-8")
    digest = hashlib.sha256(idea.encode("utf-8")).hexdigest()
    text = f"# Vision\n\n{IDEA_HEADING}\n\n{OPEN}{digest} -->\n\n{idea}\n\n{CLOSE}\n\n{body}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {VISION}")
    return 0


def cmd_vision_check(root: Path) -> int:
    path = root / VISION
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not has_idea(text):
        print("ok engines-vision (no idea section)")
        return 0
    problems = vision_problems(text)
    for problem in problems:
        print(f"FAIL engines: {problem}")
    if not problems:
        print("ok engines-vision")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = ("questions", "vision-write", "vision-check")
    if not args or args[0] not in commands:
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
        if args[0] == "questions":
            return cmd_questions()
        if args[0] == "vision-write":
            return cmd_vision_write(root, opts)
        if args[0] == "vision-check":
            return cmd_vision_check(root)
        print(USAGE, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL engines: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
