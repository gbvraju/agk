"""agk engines: the idea in the vision, the discovery questions and the stack ADR (SPEC-0029).

Usage:
    python3 engines.py questions
    python3 engines.py vision-write --idea-file F [--draft-file D] [--root DIR]
    python3 engines.py vision-check [--root DIR]
    python3 engines.py stack-ids [--ref REF] [--root DIR]
    python3 engines.py stack-write [--ref REF] [--date D] [--root DIR]
    python3 engines.py stack-check [--root DIR]

Kit-only (never installed). An engine (a skill named in `[engines]` of `agk.toml`) only drafts
text; this script writes it through the kit's templates and checks it, and it decides nothing.
`vision-write` puts the idea, unchanged, as the first section of `constitution/vision.md`, between
two markers with the SHA-256 of the idea, so `vision-check` can tell an altered idea; the four
sections of `/agk:start` follow, from the draft or from the template with `TODO(owner)` marks.
`stack-write` writes the skeleton of the stack ADR; `stack-check` checks its shape (two or three
options, trade-offs, practices told apart as check or judgement, the lock). Messages name the rule
and never quote the idea or a name. No network and no model.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from check_adrs import validate as validate_adr
from common import CheckError, load_config, next_free_ids
from intake import section

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
USAGE = (
    "usage: engines.py questions | vision-write --idea-file F [--draft-file D] | vision-check | "
    "stack-ids [--ref REF] | stack-write [--ref REF] [--date D] | stack-check  [--root DIR]"
)
FLAGS = ("--root", "--idea-file", "--draft-file", "--ref", "--date")
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
STACK_NAME = re.compile(r"^docs/adr/(\d{4})-stack-options\.md$")
OPTION = re.compile(r"^\s*-\s+Option ([A-Z]) — (.+)$")
PRACTICE = re.compile(r"^\s*-\s+(.+?):\s+(check|judgement)(?:\s+\((.*)\))?\s*$")
STACK_PLACEHOLDER = re.compile(r"TODO\(architect\)")


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


def cmd_stack_ids(root: Path, opts: dict[str, str]) -> int:
    branch = load_config(root)["default_branch"]
    ids = next_free_ids(root, opts.get("ref") or f"origin/{branch}")
    print(json.dumps({"adr": ids["adr"], "slug": "stack-options", "branch": "stack/options"}))
    return 0


def cmd_stack_write(root: Path, opts: dict[str, str]) -> int:
    if any(STACK_NAME.match(p.relative_to(root).as_posix()) for p in root.glob("docs/adr/*.md")):
        raise CheckError("rule 5: a stack ADR already exists; it is never overwritten")
    branch = load_config(root)["default_branch"]
    adr = next_free_ids(root, opts.get("ref") or f"origin/{branch}")["adr"]
    today = opts.get("date") or datetime.now(UTC).date().isoformat()
    text = (TEMPLATES / "stack-adr.md").read_text(encoding="utf-8")
    text = text.replace("{{adr}}", adr).replace("{{date}}", today)
    path = root / "docs" / "adr" / f"{adr}-stack-options.md"
    path.write_text(text, encoding="utf-8")
    print(f"wrote docs/adr/{path.name}")
    return 0


def practice_names(option_text: str) -> list[str]:
    _, _, tail = option_text.partition("Practices:")
    return [p.strip().rstrip(".") for p in tail.split(",") if p.strip().rstrip(".")]


def stack_problems(name: str, text: str) -> list[str]:
    """SPEC-0029 rule 5: two or three options, each with trade-offs and practices, then the lock."""
    if STACK_PLACEHOLDER.search(text):
        return ["rule 5: the stack ADR is not drafted yet"]
    out = [
        f"rule 5: the stack ADR fails the ADR format check ({p.split(': ', 1)[-1]})"
        for p in validate_adr(name, text, {name[:4]})
    ]
    lines = section(text, "Decision") or []
    items: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        head = re.match(r"^\d+\.\s+\*\*([^*:]+)\*\*:?\s*(.*)$", line)
        if head:
            current = items.setdefault(head.group(1).strip(), [])
            if head.group(2):
                current.append(head.group(2))
        elif current is not None:
            current.append(line)
    for item in ("Options", "Practices", "Chosen"):
        if item not in items:
            out.append(f"rule 5: the Decision lacks the numbered item {item}")
    if out:
        return out
    options = [m for ln in items["Options"] if (m := OPTION.match(ln))]
    if len(options) not in (2, 3) or [m.group(1) for m in options] != list("ABC"[: len(options)]):
        out.append("rule 5: the Options item does not hold two or three options, A to C")
    named: set[str] = set()
    for m in options:
        body = m.group(2)
        if "Trade-offs:" not in body or not body.split("Trade-offs:", 1)[1].split("Practices:")[
            0
        ].strip(" ."):
            out.append(f"rule 5: option {m.group(1)} has no Trade-offs")
        names = practice_names(body)
        if "Practices:" not in body or not names:
            out.append(f"rule 5: option {m.group(1)} names no Practices")
        named |= set(names)
    recorded: set[str] = set()
    for line in items["Practices"]:
        if not line.strip():
            continue
        m = PRACTICE.match(line)
        if not m:
            out.append("rule 5: a practice is neither check nor judgement")
            continue
        if m.group(2) == "check" and not (m.group(3) or "").startswith("step:"):
            out.append("rule 5: a practice marked check names no step of the adopting build")
        recorded.add(m.group(1))
    if named - recorded:
        out.append("rule 5: a practice named by an option is not in the Practices item")
    status = re.search(r"(?m)^- Status: (\w+)$", text)
    chosen = " ".join(ln.strip() for ln in items["Chosen"]).strip()
    letters = {m.group(1) for m in options}
    if status and status.group(1) == "Proposed":
        if chosen != "none yet":
            out.append("rule 5: the ADR is Proposed and Chosen is not `none yet`")
    elif status and status.group(1) == "Accepted":
        picked = re.fullmatch(r"Option ([A-C])", chosen)
        if not picked or picked.group(1) not in letters:
            out.append("rule 5: the ADR is Accepted and Chosen names no single option")
    return out


def cmd_stack_check(root: Path) -> int:
    files = sorted(
        p for p in root.glob("docs/adr/*.md") if STACK_NAME.match(p.relative_to(root).as_posix())
    )
    if not files:
        print("ok engines-stack (no stack ADR)")
        return 0
    problems: list[str] = []
    for path in files:
        problems += stack_problems(path.name, path.read_text(encoding="utf-8"))
    for problem in problems:
        print(f"FAIL engines: {problem}")
    if not problems:
        print("ok engines-stack")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = (
        "questions",
        "vision-write",
        "vision-check",
        "stack-ids",
        "stack-write",
        "stack-check",
    )
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
        if args[0] == "stack-ids":
            return cmd_stack_ids(root, opts)
        if args[0] == "stack-write":
            return cmd_stack_write(root, opts)
        if args[0] == "stack-check":
            return cmd_stack_check(root)
        print(USAGE, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL engines: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
