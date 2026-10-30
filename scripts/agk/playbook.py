"""agk playbook: `/agk:start` checks, the architect start-up check and the brief skeleton.

Usage:
    python3 playbook.py start-ids --statement TEXT [--ref REF] [--root DIR]
    python3 playbook.py check-start [--base REF] [--root DIR]
    python3 playbook.py next-steps [--base REF] [--date D] [--brief N|none] [--issues FILE]
                                   [--root DIR]
    python3 playbook.py architect [--root DIR]
    python3 playbook.py brief --kind overnight|day --branch-prefix PREFIX [--repo O/R]
                              [--ref REF] [--date D] [--root DIR]

Kit-only (never installed). `start-ids`, `check-start` and `next-steps` serve `/agk:start`
(rules 2 to 5): the next free ADR number and the branch name, the deterministic checks of the two
files it writes, and the commands for the person, with a pull request body that passed
the repository's body check (`pr_body.py`, brief #273). `architect` prints how to start the role and
checks, read-only, that `agk.toml` is present, that `gh` is logged in and which branch is the
default. `brief` prints a brief skeleton from `kit/templates/playbook/` in which the next
requirement, ADR and spec numbers are read from `origin/<default branch>`
(`common.next_free_ids`), the repository and the default branch come from `origin` and
`agk.toml`, and no pull request number is written in advance.
Nothing is written.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from check_adrs import validate as validate_adr
from common import (
    CheckError,
    changed_files,
    git,
    load_config,
    merge_base,
    next_free_ids,
    resolve_base,
    show,
)
from doctor import origin_repo
from engines import TOPICS as ALL_TOPICS
from engines import has_idea, print_offer, vision_problems
from intake import section, slug
from pr_body import brief_option, prepare, print_body

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates" / "playbook"
USAGE = (
    "usage: playbook.py architect [--root DIR] | brief --kind overnight|day --branch-prefix P "
    "[--repo O/R] [--ref REF] [--date D] [--root DIR]"
)
PREFIX = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")
FLAGS = (
    "--root",
    "--kind",
    "--branch-prefix",
    "--repo",
    "--ref",
    "--date",
    "--statement",
    "--base",
    "--brief",
    "--issues",
)
MAX_STATEMENT = 1500
VISION = "constitution/vision.md"
PRINCIPLES = "constitution/principles.md"
VISION_HEADINGS = (
    "## What this is for",
    "## Who it serves",
    "## How success is measured",
    "## Out of scope",
)
MARKER = "<!-- project-specific -->"
CHARTER_NAME = re.compile(r"^docs/adr/(\d{4})-project-charter\.md$")
CHARTER_ITEMS = ("Milestones", "Non-goals", "Done means")
TOPICS = ("users", "existing", "runs", "data", "scale", "compliance")
NOT_KNOWN = "not known yet"
BULLET = re.compile(r"^[-*]\s+([A-Za-z]+):\s*(.*)$")
MEASURABLE = re.compile(r"\d|\b(?:all|every|none|zero)\b", re.IGNORECASE)


def cmd_architect(root: Path) -> int:
    print(
        "Start the architect role from the repository root with:\n\n    claude --agent architect\n"
    )
    config = root / "agk.toml"
    missing = "missing (run /agk:init or /agk:adopt first)"
    print(f"agk.toml: {'present' if config.is_file() else missing}")
    try:
        gh = subprocess.run(  # nosec B603 B607 - fixed argument list, read-only, no shell
            ["gh", "auth", "status"], capture_output=True, text=True, encoding="utf-8"
        ).returncode
        print(f"gh: {'logged in' if gh == 0 else 'not logged in or not working'}")
    except OSError:
        print("gh: not installed")
    if config.is_file():
        print(f"default branch: {load_config(root)['default_branch']}")
    print("The role file is .claude/agents/architect.md;")
    print("its guard is .claude/hooks/architect_guard.py.")
    return 0 if config.is_file() else 1


def cmd_brief(root: Path, opts: dict[str, str]) -> int:
    kind = opts.get("kind")
    prefix = opts.get("branch-prefix", "")
    if kind not in ("overnight", "day") or not PREFIX.match(prefix):
        raise CheckError("usage: --kind overnight|day and --branch-prefix like 'day-14' (rule 16)")
    branch = load_config(root)["default_branch"]
    ids = next_free_ids(root, opts.get("ref") or f"origin/{branch}")
    repo = opts.get("repo") or origin_repo(root)
    if not repo:
        raise CheckError("repository unknown; pass --repo OWNER/REPO (path class: git remote)")
    values = {
        "repo": repo,
        "default_branch": branch,
        "next_req": ids["req"],
        "next_adr": f"ADR-{ids['adr']}",
        "next_spec": f"SPEC-{ids['spec']}",
        "branch_prefix": prefix,
        "date": opts.get("date") or datetime.now(UTC).date().isoformat(),
    }
    text = (TEMPLATES / f"brief-{kind}.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    sys.stdout.write(text)
    return 0


def statement_ok(text: str) -> str:
    text = text.strip()
    if not text or len(text) > MAX_STATEMENT or not slug(text):
        raise CheckError(
            f"rule 3: the problem statement is empty or over {MAX_STATEMENT} characters"
        )
    return text


def cmd_start_ids(root: Path, opts: dict[str, str]) -> int:
    if not (root / "agk.toml").is_file():
        raise CheckError("rule 2: run /agk:init or /agk:adopt first (agk.toml is absent)")
    text = statement_ok(opts.get("statement", ""))
    branch = load_config(root)["default_branch"]
    ids = next_free_ids(root, opts.get("ref") or f"origin/{branch}")
    name = slug(text)
    print(json.dumps({"adr": ids["adr"], "slug": name, "branch": f"start/{name}"}))
    return 0


def charter_items(lines: list[str]) -> dict[str, list[str]]:
    """The numbered items of the Decision, by heading word, with their list lines."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        head = re.match(r"^\d+\.\s+\*\*([^*]+)\*\*", line)
        if head:
            current = found.setdefault(head.group(1).strip().rstrip(".:"), [])
            continue
        if current is not None and re.match(r"^\s*(?:[-*]|\d+[.)])\s+\S", line):
            current.append(line.strip())
    return found


def start_problems(root: Path, mb: str, ref_ids: dict[str, str]) -> list[str]:
    out: list[str] = []
    changed = changed_files(root, mb)
    charters = [p for p in changed if CHARTER_NAME.match(p)]
    if set(changed) != {VISION, *charters} or len(charters) != 1 or changed.get(VISION) != "M":
        out.append("rule 4: the difference is not the vision (modified) and one new charter ADR")
    if PRINCIPLES in changed or show(root, mb, PRINCIPLES) != _read(root, PRINCIPLES):
        out.append("rule 4: the principles file is not byte-identical to the base")
    vision = _read(root, VISION) or ""
    if "TODO(maintainers)" in vision:
        out.append("rule 5: the vision still holds the placeholder")
    lines = vision.splitlines()
    positions = [lines.index(h) if h in lines else -1 for h in VISION_HEADINGS]
    if -1 in positions or positions != sorted(positions):
        out.append("rule 5: the vision lacks one of the four headings, or they are out of order")
    rules = section(vision, "Project rules") or []
    if any(ln.strip() and MARKER not in ln for ln in rules):
        out.append("rule 5: a line under the project rules does not carry the project marker")
    out += vision_problems(vision)
    if len(charters) == 1:
        out += charter_problems(root, charters[0], ref_ids, has_idea(vision))
    return out


def _read(root: Path, rel: str) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def charter_problems(root: Path, rel: str, ref_ids: dict[str, str], ten: bool = False) -> list[str]:
    out: list[str] = []
    text = _read(root, rel) or ""
    name = Path(rel).name
    if validate_adr(name, text, {name[:4]}):
        out.append("rule 5: the charter does not pass the ADR format check")
    if not re.search(r"(?m)^- Status: Proposed$", text):
        out.append("rule 5: the charter is not Proposed")
    if name[:4] != ref_ids["adr"]:
        out.append("rule 5: the charter number is not the next free ADR number")
    line = next((ln for ln in text.splitlines() if ln.startswith("Protected classes:")), "")
    if "constitution/" not in line:
        out.append("rule 4: the Protected classes line does not name the constitution")
    items = charter_items(section(text, "Decision") or [])
    if any(not items.get(item) for item in CHARTER_ITEMS):
        out.append(
            "rule 5: the Decision lacks the numbered items Milestones, Non-goals, Done means"
        )
    for milestone in items.get("Milestones", []):
        _, _, after = milestone.partition("exit:")
        if "exit:" not in milestone or not MEASURABLE.search(after):
            out.append("rule 5: a milestone line has no `exit:` with a measurable statement")
            break
    return out + discovery_problems(items, ten)


def topic_bullets(lines: list[str]) -> list[tuple[str, str]]:
    """`- <topic>: <text>` bullets as (word, text) pairs, in order."""
    found = (BULLET.match(line) for line in lines)
    return [(m.group(1).lower(), m.group(2).strip()) for m in found if m]


def discovery_problems(items: dict[str, list[str]], ten: bool = False) -> list[str]:
    """SPEC-0023 rules 6 and 7: six topics in order, an answer each, a slice for the unknown.

    With `ten` (the vision has the idea section of `/agk:vision`, SPEC-0029 rule 4) the four
    topics of the vision step follow, and the charter records an answer for each.
    """
    if not items.get("Discovery"):
        return ["rule 7: the Decision lacks the numbered item Discovery"]
    out: list[str] = []
    answers = topic_bullets(items["Discovery"])
    words = [word for word, _ in answers]
    wanted = ALL_TOPICS if ten else TOPICS
    for topic in wanted:
        if topic not in words:
            out.append(f"rule 6: the Discovery item lacks the topic {topic}")
    if not out and words not in (list(wanted), list(ALL_TOPICS)):
        count = "ten" if ten else "six"
        out.append(f"rule 6: the Discovery topics are not the {count} topics in their order")
    slices = dict(topic_bullets(items.get("Slice", [])))
    for word, text in answers:
        if word in ALL_TOPICS and not text:
            out.append(f"rule 6: the Discovery topic {word} has no answer")
        elif text.lower() == NOT_KNOWN and not slices.get(word):
            out.append(f"rule 7: the topic {word} is not known yet and has no Slice bullet")
    for word, text in topic_bullets(items.get("Slice", [])):
        if word not in ALL_TOPICS or not text:
            out.append("rule 6: a Slice bullet names no topic or says nothing")
            break
    return out


def start_context(root: Path, base: str | None) -> tuple[str, dict[str, str]]:
    ref = resolve_base(root, base)
    if ref is None:
        raise CheckError("no base ref resolves (setting default_branch)")
    mb = merge_base(root, ref)
    return mb, next_free_ids(root, mb)


def cmd_check_start(root: Path, opts: dict[str, str]) -> int:
    mb, ref_ids = start_context(root, opts.get("base"))
    problems = start_problems(root, mb, ref_ids)
    for problem in problems:
        print(f"FAIL playbook: {problem}")
    if not problems:
        print("ok playbook-start")
    return 1 if problems else 0


def cmd_next_steps(root: Path, opts: dict[str, str]) -> int:
    branch = git(root, "branch", "--show-current").strip()
    if not branch or branch == load_config(root)["default_branch"]:
        raise CheckError(
            "rule 3: the work is not on a start branch (detached or the default branch)"
        )
    mb, ref_ids = start_context(root, opts.get("base"))
    problems = start_problems(root, mb, ref_ids)
    if problems:
        for problem in problems:
            print(f"FAIL playbook: {problem}")
        print("the start does not pass `check-start`; no next steps are printed")
        return 1
    today = opts.get("date") or datetime.now(UTC).date().isoformat()
    fields = [
        ("Advances", "REQ-001"),
        ("Build-state row", f"{today} REQ-001 vision and project charter proposed, start only"),
        (
            "Summary",
            "Sets out the project's vision and charter, to be reviewed before any work starts.",
        ),
        ("Decisions taken", "none; the problem statement became a vision and a Proposed charter"),
        ("Questions", "none"),
        ("Verified", "`python3 scripts/agk/playbook.py check-start` printed `ok playbook-start`"),
    ]
    brief = brief_option(opts.get("brief"))
    path, body = prepare(
        root, fields, brief=brief, issues=opts.get("issues"), changed=None, base=mb
    )
    print("Commit message:\n\nstart: the vision and the project charter\n")
    print(f"Push command:\n\ngit push -u origin {branch}\n")
    print("Open the pull request from that branch into the default branch with this body.\n")
    print_body(path, body)
    print(
        "The checks cannot tell that the milestones are the right ones or that the vision says\n"
        "what you meant. That is the review of the pull request; merging approves the charter\n"
        "as a proposal."
    )
    print_offer(root)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = ("architect", "brief", "start-ids", "check-start", "next-steps")
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
        if args[0] == "architect":
            return cmd_architect(root)
        if args[0] == "start-ids":
            return cmd_start_ids(root, opts)
        if args[0] == "check-start":
            return cmd_check_start(root, opts)
        if args[0] == "next-steps":
            return cmd_next_steps(root, opts)
        return cmd_brief(root, opts)
    except CheckError as exc:
        print(f"FAIL playbook: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
