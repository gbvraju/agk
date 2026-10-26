"""Assemble the review context of one pull request (SPEC-0003 rules 4-7).

Standard library only; no network, no `gh`, no writes. The document goes to stdout: the PR body,
the numbered hunks of the diff from the merge base to the work tree, the full current text of every
changed file, the advanced requirements, the protected classes touched, the referenced specs and
ADRs, the principles and the operating rules of CLAUDE.md. The same inputs give the same bytes.
"""

from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from common import (
    REQ_HEADER,
    REQ_ID,
    CheckError,
    changed_files,
    git,
    markers_for,
    matches,
    merge_base,
    read_list,
    repo_root,
    resolve_base,
    run,
    show,
)

NAME = "review-context"
USAGE = "usage: review_context.py [--base REF] --body FILE|-"
DEFAULT_CAPS = {"review_diff_cap": 4000, "review_other_cap": 1500}
PROTECTED = "config/protected-paths.txt"
REQUIREMENTS = "docs/requirements.md"
PRINCIPLES = "constitution/principles.md"
OPERATING_RULES = "CLAUDE.md"
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
DIFF_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
SPEC_ID = re.compile(r"SPEC-(\d{4})")
ADR_ID = re.compile(r"ADR-(\d{4})")
DOC_PATH = re.compile(r"docs/(?:specs|adr)/[\w.\-]+\.md")
MAX_TEXT_BYTES = 200_000


def settings(root: Path) -> dict:
    """The raw agk.toml (or [tool.agk] of pyproject.toml) table; empty when absent."""
    try:
        agk_toml = root / "agk.toml"
        pyproject = root / "pyproject.toml"
        if agk_toml.is_file():
            return tomllib.loads(agk_toml.read_text(encoding="utf-8"))
        if pyproject.is_file():
            return (
                tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}).get("agk", {})
            )
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CheckError("agk.toml cannot be read") from exc
    return {}


def caps(root: Path) -> dict[str, int]:
    source = settings(root)
    result = dict(DEFAULT_CAPS)
    for key in DEFAULT_CAPS:
        if key in source:
            value = source[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise CheckError(f"setting {key} must be a positive integer")
            result[key] = value
    return result


def fenced(lines: list[str], info: str = "") -> list[str]:
    """A tilde fence longer than any tilde run inside, so the text cannot close it."""
    longest = max((len(m.group()) for line in lines for m in re.finditer(r"~+", line)), default=0)
    fence = "~" * max(4, longest + 1)
    return [f"{fence}{info}", *lines, fence]


class Budget:
    """Line budget of one section; what does not fit is counted and marked, never dropped."""

    def __init__(self, limit: int) -> None:
        self.left = limit
        self.omitted = 0

    def take(self, lines: list[str]) -> list[str]:
        kept = lines[: max(self.left, 0)]
        self.left -= len(kept)
        self.omitted += len(lines) - len(kept)
        return kept

    def marker(self) -> list[str]:
        return [f"[truncated: {self.omitted} lines omitted]"] if self.omitted else []


def read_text(root: Path, rel: str) -> str | None:
    path = root / rel
    try:
        if path.is_file() and path.stat().st_size <= MAX_TEXT_BYTES * 5:
            return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return None


# --- the diff ---------------------------------------------------------------------------------


@dataclass
class Hunk:
    file: str
    old: tuple[int, int]
    new: tuple[int, int]
    lines: list[str] = field(default_factory=list)


def tracked_hunks(root: Path, mb: str) -> list[Hunk]:
    out = git(
        root, "-c", "core.quotepath=false", "-c", "diff.noprefix=false",
        "-c", "diff.mnemonicPrefix=false", "diff", "-U3", "--no-renames", "--no-color",
        "--no-ext-diff", mb,
    )  # fmt: skip
    hunks: list[Hunk] = []
    file: str | None = None
    current: Hunk | None = None
    for line in out.splitlines():
        header = DIFF_HEADER.match(line)
        if header:
            file, current = header.group(2), None
            continue
        if file is None:
            continue
        start = HUNK.match(line)
        if start:
            old_n = int(start.group(2)) if start.group(2) is not None else 1
            new_n = int(start.group(4)) if start.group(4) is not None else 1
            current = Hunk(file, (int(start.group(1)), old_n), (int(start.group(3)), new_n))
            hunks.append(current)
        elif current is not None and line[:1] in " +-\\":
            current.lines.append(line)
        elif current is None and (line.startswith("Binary files") or line.startswith("GIT binary")):
            hunks.append(Hunk(file, (0, 0), (0, 0), ["(binary file differs)"]))
    return hunks


def untracked_hunks(root: Path) -> list[Hunk]:
    hunks: list[Hunk] = []
    names = git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0")
    for rel in sorted(filter(None, names)):
        text = read_text(root, rel)
        if text is None or "\0" in text:
            hunks.append(Hunk(rel, (0, 0), (0, 0), ["(binary file differs)"]))
            continue
        body = text.splitlines()
        hunks.append(Hunk(rel, (0, 0), (1 if body else 0, len(body)), ["+" + x for x in body]))
    return hunks


def diff_section(hunks: list[Hunk], limit: int) -> tuple[list[str], bool]:
    budget = Budget(limit)
    lines: list[str] = []
    for number, hunk in enumerate(hunks, 1):
        shown = budget.take(hunk.lines)
        if not shown and hunk.lines:
            continue
        old, new = hunk.old, hunk.new
        lines.append(f"### {hunk.file}:H{number} (old {old[0]},{old[1]} new {new[0]},{new[1]})")
        lines += fenced(shown, "diff")
    lines += budget.marker()
    return lines or ["none"], bool(budget.omitted)


# --- the other sections -----------------------------------------------------------------------


def advanced(body: str) -> list[str]:
    for line in body.splitlines():
        if line.startswith("Advances:"):
            return sorted(set(REQ_ID.findall(line)))
    return []


def requirement_texts(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        header = REQ_HEADER.match(line)
        if header:
            current = header.group(1)
            sections[current] = [line]
        elif line.startswith("### "):
            current = None
        elif current:
            sections[current].append(line)
    for lines in sections.values():
        while lines and not lines[-1].strip():
            lines.pop()
    return sections


def requirements_section(
    root: Path, ids: list[str], texts: dict[str, list[str]], limit: int
) -> tuple[list[str], bool]:
    budget = Budget(limit)
    markers = markers_for(root)
    lines: list[str] = []
    for req in ids:
        if req not in texts:
            continue
        shown = budget.take(texts[req])
        if not shown:
            continue
        files = markers.get(req, [])
        lines += [
            f"### {req}",
            *fenced(shown),
            "Test markers: " + (", ".join(files) if files else "none"),
        ]
    lines += budget.marker()
    return lines or ["none"], bool(budget.omitted)


def protected_section(root: Path, mb: str, changed: dict[str, str]) -> list[str]:
    listing = show(root, mb, PROTECTED)
    if listing is None:
        listing = read_text(root, PROTECTED) or ""
    entries = read_list(listing)
    adrs = {
        p: read_text(root, p) or ""
        for p, status in sorted(changed.items())
        if status != "D" and re.fullmatch(r"docs/adr/\d{4}-[^/]*\.md", p)
    }
    lines = []
    for entry in sorted(entries):
        if any(matches(path, entry) for path in changed):
            naming = [p for p, text in adrs.items() if entry in text]
            lines.append(
                f"- {entry}: "
                + (f"named in {', '.join(naming)}" if naming else "not named in any changed ADR")
            )
    return lines or ["none"]


def find_doc(root: Path, kind: str, number: str) -> str | None:
    folder = "specs" if kind == "SPEC" else "adr"
    found = sorted((root / "docs" / folder).glob(f"{number}-*.md"))
    return found[0].relative_to(root).as_posix() if found else None


def referenced_docs(
    root: Path, body: str, ids: list[str], changed: dict[str, str]
) -> tuple[list[str], list[str]]:
    paths: set[str] = set()
    problems: list[str] = []
    for folder in ("specs", "adr"):
        for path in sorted((root / "docs" / folder).glob("[0-9][0-9][0-9][0-9]-*.md")):
            text = read_text(root, path.relative_to(root).as_posix()) or ""
            requirements = [x for x in text.splitlines() if x.startswith("- Requirements:")]
            if any(req in line for line in requirements for req in ids):
                paths.add(path.relative_to(root).as_posix())
    for pattern, kind in ((SPEC_ID, "SPEC"), (ADR_ID, "ADR")):
        for number in sorted(set(pattern.findall(body))):
            found = find_doc(root, kind, number)
            if found:
                paths.add(found)
            else:
                problems.append(f"{kind}-{number} is named in the PR body but does not exist")
    for named in sorted(set(DOC_PATH.findall(body))):
        if (root / named).is_file():
            paths.add(named)
        else:
            problems.append(f"{named} is named in the PR body but does not exist")
    for rel, status in sorted(changed.items()):
        changed_text = read_text(root, rel) if status != "D" else None
        if changed_text is None or len(changed_text.encode("utf-8")) > MAX_TEXT_BYTES:
            continue
        for pattern, kind in ((SPEC_ID, "SPEC"), (ADR_ID, "ADR")):
            for number in sorted(set(pattern.findall(changed_text))):
                found = find_doc(root, kind, number)
                if found:
                    paths.add(found)
        paths |= {named for named in DOC_PATH.findall(changed_text) if (root / named).is_file()}
    return sorted(paths), problems


def documents_section(root: Path, paths: list[str], limit: int) -> tuple[list[str], bool]:
    budget = Budget(limit)
    lines: list[str] = []
    for rel in paths:
        text = read_text(root, rel) or ""
        shown = budget.take(text.splitlines())
        if not shown:
            continue
        lines += [f"### {rel}", *fenced(shown)]
    lines += budget.marker()
    return lines or ["none"], bool(budget.omitted)


def changed_files_section(
    root: Path, changed: dict[str, str], limit: int
) -> tuple[list[str], bool]:
    """The full current text of every changed file, so a rule next to a change is visible."""
    budget = Budget(limit)
    lines: list[str] = []
    for rel, status in sorted(changed.items()):
        if status == "D":
            lines.append(f"### {rel} (deleted)")
            continue
        text = read_text(root, rel)
        if text is None or "\0" in text:
            lines.append(f"### {rel} (not shown: binary or too large)")
            continue
        shown = budget.take(text.splitlines())
        if not shown and text:
            continue
        lines += [f"### {rel}", *fenced(shown)]
    lines += budget.marker()
    return lines or ["none"], bool(budget.omitted)


def text_section(text: str | None, limit: int) -> tuple[list[str], bool]:
    if text is None:
        return ["none"], False
    budget = Budget(limit)
    shown = budget.take(text.splitlines())
    return [*fenced(shown), *budget.marker()], bool(budget.omitted)


# --- main -------------------------------------------------------------------------------------


def assemble(root: Path, cli_base: str | None, body: str) -> str:
    limits = caps(root)
    base = resolve_base(root, cli_base)
    if base is None:
        raise CheckError("no base ref resolves; pass --base")
    mb = merge_base(root, base)
    changed = changed_files(root, mb)
    ids = advanced(body)
    problems: list[str] = []
    if not ids:
        problems.append("the PR body has no `Advances:` line with a REQ id")

    hunks = tracked_hunks(root, mb) + untracked_hunks(root)
    hunks.sort(key=lambda h: h.file)
    if not hunks:
        problems.append("the diff is empty")
    diff, cut_diff = diff_section(hunks, limits["review_diff_cap"])

    other = limits["review_other_cap"]
    req_text = read_text(root, REQUIREMENTS)
    texts = requirement_texts(req_text) if req_text is not None else {}
    if req_text is None:
        problems.append(f"{REQUIREMENTS} is missing")
    problems += [
        f"{req} is not in {REQUIREMENTS}"
        for req in ids
        if req_text is not None and req not in texts
    ]
    reqs, cut_reqs = requirements_section(root, ids, texts, other)

    docs, doc_problems = referenced_docs(root, body, ids, changed)
    problems += doc_problems
    docs_lines, cut_docs = documents_section(root, docs, other)

    principles = read_text(root, PRINCIPLES)
    if principles is None:
        problems.append(f"{PRINCIPLES} is missing")
    principle_lines, cut_principles = text_section(principles, other)
    rules = read_text(root, OPERATING_RULES)
    if rules is None:
        problems.append(f"{OPERATING_RULES} is missing")
    rule_lines, cut_rules = text_section(rules, other)
    files_lines, cut_files = changed_files_section(root, changed, other)
    body_lines, cut_body = text_section(body, other)

    truncated = any((cut_diff, cut_files, cut_reqs, cut_docs, cut_principles, cut_rules, cut_body))
    out = ["# Review context", "", f"Truncated: {'yes' if truncated else 'no'}", ""]
    for title, lines in (
        ("Context problems", [f"- {p}" for p in problems] or ["- none"]),
        ("PR body", body_lines),
        ("Diff", diff),
        ("Changed files", files_lines),
        ("Requirements", reqs),
        ("Protected classes touched", protected_section(root, mb, changed)),
        ("Referenced specs and ADRs", docs_lines),
        ("Principles", principle_lines),
        ("Operating rules", rule_lines),
    ):
        out += [f"## {title}", "", *lines, ""]
    return "\n".join(out)


def parse_args(args: list[str]) -> tuple[str | None, str] | None:
    values: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i] in ("--base", "--body") and i + 1 < len(args):
            values[args[i]] = args[i + 1]
            i += 2
        else:
            return None
    if "--body" not in values:
        return None
    return values.get("--base"), values["--body"]


def main(argv: list[str] | None = None) -> int:
    parsed = parse_args(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return 2
    cli_base, body_arg = parsed
    try:
        if body_arg == "-":
            body = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(body_arg, encoding="utf-8") as fh:
                body = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("cannot read the PR body") from exc
    sys.stdout.write(assemble(repo_root(), cli_base, body))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
