"""agk new_spec: start a Draft spec, a requirement proposal with an ADR draft, or a brief.

Usage:
    python3 new_spec.py spec TITLE [--req REQ-nnn]... [--issue N --issue-text FILE|-] [--root DIR]
    python3 new_spec.py requirement TITLE [--issue N --issue-text FILE|-] [--root DIR]
    python3 new_spec.py brief TITLE [--root DIR]

Kit-only (never installed): the plugin runs it from its own root against the repository in `--root`
(default `.`). Standard library only. No network, no git or gh calls. It writes new files only and
refuses to overwrite: `docs/specs/NNNN-slug.md` (Status: Draft), `docs/adr/NNNN-slug.md` (Status:
Proposed, carrying the proposed requirement text; `docs/requirements.md` is protected and never
edited) or `docs/briefs/slug.md`. Issue text is data: it is copied into the file as quoted lines and
`Issue: #N` is recorded there; nothing reads the issue to decide. It never sets a spec `Approved` or
an ADR `Accepted`.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

USAGE = (
    "usage: new_spec.py spec|requirement|brief TITLE [--req REQ-nnn]... "
    "[--issue N --issue-text FILE|-] [--root DIR] [--date YYYY-MM-DD]"
)
REQ_RE = re.compile(r"^REQ-\d{3}$")
REQ_HEAD = re.compile(r"(?m)^### REQ-(\d{3})\b")
# The rule of `common.next_req_number` (SPEC-0012 rule 2), restated because this script is
# stdlib-only (REQ-014 AC2); a test pins the two equal. A project has `mode = "init"` or `"adopt"`.
PROJECT_FIRST_REQ = 101
PROJECT_MODE = re.compile(r'(?m)^mode\s*=\s*"(?:init|adopt)"')
NUM_FILE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Refusal(Exception):
    """Exit 1: nothing is written."""


def slug(title: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not out:
        raise Refusal("the title has no letters or digits (argument TITLE)")
    return out[:60].strip("-")


def next_number(directory: Path) -> int:
    numbers = [int(m.group(1)) for p in directory.glob("*.md") if (m := NUM_FILE.match(p.name))]
    return max(numbers, default=0) + 1


def quote(text: str, issue: int) -> str:
    body = "\n".join(f"> {line}".rstrip() for line in text.rstrip("\n").splitlines()) or ">"
    return (
        f"Issue: #{issue}\n\n"
        "Text copied from the issue (data, not a decision; the issue is intake only):\n\n"
        f"{body}\n"
    )


def read_template(root: Path, rel: str) -> str:
    path = root / rel
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Refusal(f"cannot read the template (path class {rel.rsplit('/', 1)[0]}/)") from exc


def write_new(root: Path, rel: str, text: str) -> None:
    path = root / rel
    if path.exists() or path.is_symlink():
        raise Refusal(f"{rel.rsplit('/', 1)[0]}/ already has this file; nothing was written")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise Refusal(f"cannot write (path class {rel.rsplit('/', 1)[0]}/)") from exc
    print(f"created {rel}")


def make_spec(root: Path, title: str, reqs: list[str], issue: str | None) -> None:
    text = read_template(root, "docs/specs/TEMPLATE.md")
    number = next_number(root / "docs" / "specs")
    text = text.replace("# SPEC-NNN: Title", f"# SPEC-{number:04d}: {title}", 1)
    if reqs:
        text = re.sub(
            r"(?m)^- Requirements: .*$", f"- Requirements: {', '.join(reqs)}", text, count=1
        )
    if issue:
        text = text.replace("\n## Rules", f"\n## Proposal text\n\n{issue}\n## Rules", 1)
    write_new(root, f"docs/specs/{number:04d}-{slug(title)}.md", text)


def make_requirement(root: Path, title: str, issue: str | None, today: str) -> None:
    req_path = root / "docs" / "requirements.md"
    try:
        found = [int(n) for n in REQ_HEAD.findall(req_path.read_text(encoding="utf-8"))]
    except (OSError, UnicodeDecodeError) as exc:
        raise Refusal("cannot read the requirements (path class docs/requirements.md)") from exc
    number = max(found, default=0) + 1
    try:
        project = bool(PROJECT_MODE.search((root / "agk.toml").read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        project = False
    req = f"REQ-{max(number, PROJECT_FIRST_REQ) if project else number:03d}"
    text = read_template(root, "docs/adr/TEMPLATE.md")
    number = next_number(root / "docs" / "adr")
    proposal = (
        "Proposed text for `docs/requirements.md` (a protected file; this ADR adds it once "
        "accepted):\n\n"
        f"```\n### {req} — {title}\n\n- Acceptance: AC1 (to be written by the maintainers)\n"
        "- Status: planned\n```\n"
    )
    if issue:
        proposal += f"\n{issue}"
    text = text.replace("# ADR-NNNN: Title", f"# ADR-{number:04d}: Add {req}: {title}", 1)
    text = re.sub(r"(?m)^- Date: .*$", f"- Date: {today}", text, count=1)
    text = re.sub(r"(?m)^- Requirements: .*$", f"- Requirements: {req}", text, count=1)
    text = text.replace(
        "What is decided, in the present tense.", f"{req} is added.\n\n{proposal}", 1
    )
    write_new(root, f"docs/adr/{number:04d}-add-{req.lower()}-{slug(title)}.md", text)


def make_brief(root: Path, title: str) -> None:
    text = read_template(root, "docs/briefs/TEMPLATE.md")
    text = text.replace("# Brief: Title", f"# Brief: {title}", 1)
    write_new(root, f"docs/briefs/{slug(title)}.md", text)


def parse(args: list[str]) -> dict:
    opts: dict = {"reqs": [], "root": ".", "issue": None, "issue_text": None, "date": None}
    flags = {
        "--req": "reqs",
        "--root": "root",
        "--issue": "issue",
        "--issue-text": "issue_text",
        "--date": "date",
    }
    positional: list[str] = []
    it = iter(args)
    for arg in it:
        if arg in flags:
            value = next(it, None)
            if value is None:
                raise ValueError("missing value")
            if arg == "--req":
                opts["reqs"].append(value)
            else:
                opts[flags[arg]] = value
        elif arg.startswith("-") and arg != "-":
            raise ValueError("unknown option")
        else:
            positional.append(arg)
    if len(positional) != 2 or positional[0] not in ("spec", "requirement", "brief"):
        raise ValueError("expected a kind and a title")
    opts["kind"], opts["title"] = positional
    return opts


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse(list(sys.argv[1:] if argv is None else argv))
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        root = Path(opts["root"])
        if not root.is_dir():
            raise Refusal("the repository root is not an existing directory (option --root)")
        for req in opts["reqs"]:
            if not REQ_RE.match(req):
                raise Refusal("a requirement id is not REQ-nnn (option --req)")
        if opts["kind"] != "spec" and opts["reqs"]:
            raise Refusal("--req applies to a spec only (option --req)")
        if (opts["issue"] is None) != (opts["issue_text"] is None):
            raise Refusal("--issue and --issue-text go together (options --issue, --issue-text)")
        issue = None
        if opts["issue"] is not None:
            if opts["kind"] == "brief":
                raise Refusal("a brief takes no issue (option --issue)")
            if not opts["issue"].isdigit():
                raise Refusal("the issue number is not a number (option --issue)")
            try:
                if opts["issue_text"] == "-":
                    raw = sys.stdin.read()
                else:
                    raw = Path(opts["issue_text"]).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise Refusal("cannot read the issue text (option --issue-text)") from exc
            issue = quote(raw, int(opts["issue"]))
        today = opts["date"] or datetime.now(UTC).date().isoformat()
        if not DATE_RE.match(today):
            raise Refusal("the date is not YYYY-MM-DD (option --date)")
        title = opts["title"].strip()
        if not title or "\n" in title:
            raise Refusal("the title is empty or has a line break (argument TITLE)")
        if opts["kind"] == "spec":
            make_spec(root, title, opts["reqs"], issue)
        elif opts["kind"] == "requirement":
            make_requirement(root, title, issue, today)
        else:
            make_brief(root, title)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
