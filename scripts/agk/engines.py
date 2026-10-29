"""agk engines: the idea in the vision, the discovery questions and the stack ADR (SPEC-0029).

Usage:
    python3 engines.py questions
    python3 engines.py vision-write --idea-file F [--draft-file D] [--root DIR]
    python3 engines.py vision-check [--root DIR]
    python3 engines.py stack-ids [--ref REF] [--root DIR]
    python3 engines.py stack-write [--ref REF] [--date D] [--root DIR]
    python3 engines.py stack-check [--root DIR]
    python3 engines.py stack-next-steps [--base REF] [--date D] [--brief N|none] [--issues FILE]
                                        [--root DIR]
    python3 engines.py design-next-steps --req REQ-nnn [--base REF] [--date D] [--brief N|none]
                                         [--issues FILE] [--root DIR]

Kit-only (never installed). An engine (a skill named in `[engines]` of `agk.toml`) only drafts
text; this script writes it through the kit's templates and checks it, and it decides nothing.
`vision-write` puts the idea, unchanged, as the first section of `constitution/vision.md`, between
two markers with the SHA-256 of the idea, so `vision-check` can tell an altered idea; the four
sections of `/agk:start` follow, from the draft or from the template with `TODO(owner)` marks.
`stack-write` writes the skeleton of the stack ADR; `stack-check` checks its shape (two or three
options, trade-offs, practices told apart as check or judgement, the lock). Messages name the rule
and never quote the idea or a name. No network and no model. `stack-next-steps` and
`design-next-steps` print the commit, the push and a pull request body that passed the
repository's body check (`pr_body.py`, brief #273): the stack options, or the accepting change,
and the design theme with its mockup (`Brief: none (design)`). Once an option is accepted,
`stack-next-steps` also offers the default local-profile requirement (brief #267): a `/agk:spec`
sentence from `kit/templates/local-profile.md`, filled in with the option's `External services:`,
that writes nothing; `stack-check` prints `local profile: not decided` until a requirement names it
or the stack ADR's Residual declines it with a reason and a date.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from check_adrs import validate as validate_adr
from common import (
    REQ_ID,
    CheckError,
    changed_files,
    git,
    load_config,
    merge_base,
    next_free_ids,
    parse_requirements,
    resolve_base,
)
from intake import Refusal, check_sentence, section
from pr_body import brief_option, prepare, print_body

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates"
USAGE = (
    "usage: engines.py questions | vision-write --idea-file F [--draft-file D] | vision-check | "
    "stack-ids [--ref REF] | stack-write [--ref REF] [--date D] | stack-check | "
    "stack-next-steps | design-next-steps --req REQ-nnn  [--root DIR]"
)
FLAGS = (
    "--root",
    "--idea-file",
    "--draft-file",
    "--ref",
    "--date",
    "--base",
    "--brief",
    "--issues",
    "--req",
)
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
# The lock of an Accepted stack ADR: one option, then at most a one-line reason (brief 274).
CHOSEN = re.compile(r"Option ([A-C])(?: — \S.*)?")
# Brief 267: the default local-profile requirement, offered once a stack option is accepted.
LOCAL_PROFILE = TEMPLATES / "local-profile.md"
SERVICES_KEY = "External services:"
NO_SERVICES = "none named by the stack yet"
DECLINE_MARK = "local profile: declined"
DECLINED = re.compile(r"^(?:[-*]\s+)?local profile: declined, (.+) \((\d{4}-\d{2}-\d{2})\)$")
MIN_REASON = 20
DECLINE_FORM = "local profile: declined, <reason of at least 20 characters> (YYYY-MM-DD)"
NOT_DECIDED = "local profile: not decided"


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
        out += services_problems(m.group(1), body)
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
    out += decline_problems(text)
    status = re.search(r"(?m)^- Status: (\w+)$", text)
    chosen_lines = [ln.strip() for ln in items["Chosen"] if ln.strip()]
    chosen = " ".join(chosen_lines)
    letters = {m.group(1) for m in options}
    if status and status.group(1) == "Proposed":
        if chosen != "none yet":
            out.append(
                "rule 5: the ADR is Proposed and Chosen is not `none yet`; an option is chosen by "
                "one ordinary commit that sets Chosen and Status: Accepted in the same commit"
            )
    elif status and status.group(1) == "Accepted":
        picked = CHOSEN.fullmatch(chosen)
        if len(chosen_lines) != 1 or not picked or picked.group(1) not in letters:
            out.append(
                "rule 5: the ADR is Accepted and Chosen is not one option with at most a "
                "one-line reason (`Option <X>` or `Option <X> — <reason>`)"
            )
    return out


def services_problems(letter: str, body: str) -> list[str]:
    """Brief 267 answer 3: an option names its external services once, before its Practices."""
    if SERVICES_KEY not in body:
        return []
    services = option_services(body)
    if body.count(SERVICES_KEY) != 1 or services is None:
        return [
            f"rule 5: option {letter} names External services after its Practices or more than "
            "once; they are one list before Practices"
        ]
    if not services:
        return [f"rule 5: option {letter} has an External services segment that lists none"]
    if '"' in services:
        return [
            f"rule 5: option {letter} has a double quote in External services, which would break "
            "the quoted /agk:spec sentence of the local-profile offer"
        ]
    return []


def option_services(body: str) -> str | None:
    """The External services text of one option ('' when empty), None when misplaced or absent."""
    head, key, tail = body.partition(SERVICES_KEY)
    if not key or "Practices:" in head:
        return None
    if "Practices:" not in tail:
        return None
    return tail.split("Practices:", 1)[0].strip().rstrip(".").strip()


def residual_lines(text: str) -> list[str]:
    return [ln.strip() for ln in section(text, "Residual") or [] if ln.strip()]


def decline_problems(text: str) -> list[str]:
    """Brief 267 answer 2: a decline is one Residual line with a reason and a date."""
    out: list[str] = []
    for line in residual_lines(text):
        if DECLINE_MARK not in line:
            continue
        m = DECLINED.match(line)
        if not m or len(m.group(1).strip()) < MIN_REASON or not real_date(m.group(2)):
            out.append(f"rule 5: the local profile decline in the Residual is not `{DECLINE_FORM}`")
    return out


def real_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def declined(line: str) -> bool:
    m = DECLINED.match(line)
    return bool(m and len(m.group(1).strip()) >= MIN_REASON and real_date(m.group(2)))


def accepted_stack(root: Path) -> tuple[str, str, str] | None:
    """(file name, text, chosen letter) of the one Accepted stack ADR that passes, else None."""
    files = sorted(
        p for p in root.glob("docs/adr/*.md") if STACK_NAME.match(p.relative_to(root).as_posix())
    )
    if len(files) != 1:
        return None
    text = files[0].read_text(encoding="utf-8")
    status = STATUS.search(text)
    chosen = CHOSEN_LINE.search(text)
    if not status or status.group(1) != "Accepted" or not chosen:
        return None
    if stack_problems(files[0].name, text):
        return None
    return files[0].name, text, chosen.group(1)


def local_profile_decided(root: Path, text: str) -> bool:
    """Brief 267 answer 2: declined in the stack ADR's Residual, or a requirement names it."""
    if any(declined(line) for line in residual_lines(text)):
        return True
    path = root / "docs" / "requirements.md"
    try:
        reqs = parse_requirements(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return False
    return any(
        "local profile" in f"{r['title'] or ''} {r['acceptance'] or ''}".lower() for r in reqs
    )


def local_profile_sentence(text: str, letter: str) -> str:
    """The template sentence, filled in with the chosen option's external services."""
    body = next(
        (m.group(2) for m in map(OPTION.match, text.splitlines()) if m and m.group(1) == letter),
        "",
    )
    services = option_services(body) or NO_SERVICES
    template = LOCAL_PROFILE.read_text(encoding="utf-8").strip()
    return template.replace("{{services}}", services)


def local_profile_offer(root: Path) -> list[str]:
    """Brief 267 answer 1: the extra step once a stack is accepted; [] when not due."""
    stack = accepted_stack(root)
    if stack is None:
        return []
    name, text, letter = stack
    if local_profile_decided(root, text):
        return []
    sentence = local_profile_sentence(text, letter)
    lines = [
        "One more step, once the accepted stack is on the default branch: the default local",
        "profile requirement, in which the whole product runs on one machine with a stand-in for",
        f"every external service that option {letter} names. It is an offer: nothing is written",
        "until a person runs it, from a fresh default branch:",
        "",
        f'    /agk:spec "{sentence}"',
        "",
    ]
    try:
        check_sentence(sentence)
    except Refusal as exc:
        lines += [
            f"/agk:spec refuses this sentence ({exc}); shorten or reword the list of",
            "services in the brackets before running it.",
            "",
        ]
    lines += [
        "A spec approver (`spec_approvers` in `config/reviewers.yaml`) accepts it with the",
        "`Approve:` line of the intake, as any requirement. A maintainer declines it instead with",
        f"one line in the Residual of ADR-{name[:4]}:",
        "",
        f"    {DECLINE_FORM}",
        "",
        f"Until one of the two is done, `engines.py stack-check` prints `{NOT_DECIDED}`.",
    ]
    return lines


def print_offer(root: Path) -> None:
    lines = local_profile_offer(root)
    if lines:
        print()
        print("\n".join(lines))


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
        stack = accepted_stack(root)
        if stack is not None and not local_profile_decided(root, stack[1]):
            print(f"info engines: {NOT_DECIDED}")
    return 1 if problems else 0


CHOSEN_LINE = re.compile(r"(?m)^\s*3\.\s+\*\*Chosen\*\*:\s+Option ([A-Z])(?: — (.+))?$")
STATUS = re.compile(r"(?m)^- Status: (\w+)\s*$")
DESIGN_CHECK = KIT / "scripts" / "agk" / "check_design.py"


def work_branch(root: Path, what: str) -> str:
    branch = git(root, "branch", "--show-current").strip()
    if not branch or branch == load_config(root)["default_branch"]:
        raise CheckError(f"the work is not on a {what} branch (detached or the default branch)")
    return branch


def base_and_changes(root: Path, base: str | None) -> tuple[str | None, dict[str, str] | None]:
    ref = resolve_base(root, base)
    if ref is None:
        return None, None
    mb = merge_base(root, ref)
    return mb, changed_files(root, mb)


def steps(root: Path, opts: dict[str, str], commit: str, branch: str, fields) -> int:
    mb, changed = base_and_changes(root, opts.get("base"))
    brief = brief_option(opts.get("brief"))
    path, body = prepare(
        root, fields, brief=brief, issues=opts.get("issues"), changed=changed, base=mb
    )
    print(f"Commit message:\n\n{commit}\n")
    print(f"Push command:\n\ngit push -u origin {branch}\n")
    print("Open the pull request from that branch into the default branch with this body.\n")
    print_body(path, body)
    return 0


def cmd_stack_next_steps(root: Path, opts: dict[str, str]) -> int:
    """Brief #273 answer 2: the body of the options pull request, or of the accepting one."""
    branch = work_branch(root, "stack")
    files = sorted(
        p for p in root.glob("docs/adr/*.md") if STACK_NAME.match(p.relative_to(root).as_posix())
    )
    if len(files) != 1:
        raise CheckError("rule 5: there is not exactly one stack ADR (path class docs/adr/)")
    text = files[0].read_text(encoding="utf-8")
    problems = stack_problems(files[0].name, text)
    if problems:
        for problem in problems:
            print(f"FAIL engines: {problem}")
        print("the stack ADR does not pass `stack-check`; no next steps are printed")
        return 1
    line = next((ln for ln in text.splitlines() if ln.startswith("- Requirements:")), "")
    reqs = ", ".join(dict.fromkeys(REQ_ID.findall(line)))
    if not reqs:
        raise CheckError("rule 5: the stack ADR names no requirement on its Requirements line")
    adr = f"ADR-{files[0].name[:4]}"
    today = opts.get("date") or datetime.now(UTC).date().isoformat()
    verified = ("Verified", "`engines.py stack-check` printed `ok engines-stack`")
    status = STATUS.search(text)
    chosen = CHOSEN_LINE.search(text)
    if status and status.group(1) == "Accepted" and chosen:
        letter, reason = chosen.group(1), (chosen.group(2) or "").strip()
        option = next(
            (
                m.group(2)
                for m in map(OPTION.match, text.splitlines())
                if m and m.group(1) == letter
            ),
            "",
        )
        name = option.split(". Trade-offs:", 1)[0].strip().rstrip(".")
        why = f" ({reason})" if reason else ""
        fields = [
            ("Advances", reqs),
            (
                "Build-state row",
                f"{today} {reqs} unchanged, the stack ADR {adr} accepts option {letter}",
            ),
            ("Summary", f"The project's stack is chosen: option {letter}, {name}."),
            (
                "Decisions taken",
                f"{adr} Accepted, option {letter} chosen by the person who owns the stack{why}",
            ),
            ("Questions", "none"),
            verified,
        ]
        code = steps(root, opts, f"stack: accept option {letter} of {adr}", branch, fields)
        print_offer(root)
        return code
    fields = [
        ("Advances", reqs),
        ("Build-state row", f"{today} {reqs} unchanged, the stack options {adr} proposed"),
        ("Summary", "Sets out the stack options for the project, for the architect to choose one."),
        ("Decisions taken", f"none; {adr} is Proposed with the options and Chosen is none yet"),
        ("Questions", "none"),
        verified,
    ]
    return steps(root, opts, f"stack: the options of {adr}", branch, fields)


def cmd_design_next_steps(root: Path, opts: dict[str, str]) -> int:
    """Brief #273 answer 1: the body of a design pull request (`Brief: none (design)`)."""
    req = opts.get("req", "")
    if not REQ_ID.fullmatch(req):
        raise CheckError("the requirement the design serves is not given (option --req)")
    branch = work_branch(root, "design")
    proc = subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, "-I", str(DESIGN_CHECK), "--root", str(root.resolve())],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        print(proc.stdout, end="")
        print("the design does not pass `check_design.py`; no next steps are printed")
        return 1
    folders = sorted(p.name for p in (root / "docs" / "design" / "mockups").glob("*") if p.is_dir())
    mockup = folders[-1] if folders else "none"
    today = opts.get("date") or datetime.now(UTC).date().isoformat()
    fields = [
        ("Advances", req),
        (
            "Build-state row",
            f"{today} {req} unchanged, the design theme and the mockup {mockup} proposed",
        ),
        (
            "Summary",
            "Adds the design theme and a mockup of the first page, for the owner to approve.",
        ),
        ("Decisions taken", "none; the owner approves the mockup by its Approved line"),
        ("Questions", "none"),
        ("Verified", "`check_design.py` printed `ok design`"),
    ]
    return steps(root, opts, f"design: the theme and the mockup {mockup}", branch, fields)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = (
        "questions",
        "vision-write",
        "vision-check",
        "stack-ids",
        "stack-write",
        "stack-check",
        "stack-next-steps",
        "design-next-steps",
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
        if args[0] == "stack-next-steps":
            return cmd_stack_next_steps(root, opts)
        if args[0] == "design-next-steps":
            return cmd_design_next_steps(root, opts)
        print(USAGE, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL engines: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
