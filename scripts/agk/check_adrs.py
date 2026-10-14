"""ADR format; Accepted ADRs change only their Status line relative to the base."""

from __future__ import annotations

import re
import sys

from common import (
    STATUS_LINE,
    base_arg,
    changed_files,
    changed_lines,
    merge_base,
    repo_root,
    resolve_base,
    run,
    show,
)

NAME = "adrs"
STATUSES = ("Proposed", "Accepted", "Superseded", "Rejected")
FIELDS = ("Status", "Date", "Deciders", "Related", "Requirements")
SECTIONS = ("Context", "Decision", "Consequences", "Residual")
FILE_RE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
TITLE_RE = re.compile(r"^# ADR-(\d{4}): \S")
FIELD_RE = re.compile(r"^- ([A-Za-z]+):\s*(.*?)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AMENDS_RE = re.compile(r"^ADR-(\d{4})$")


def status_of(text: str) -> str | None:
    for line in text.splitlines():
        m = STATUS_LINE.match(line)
        if m:
            return m.group(1)
    return None


def validate(name: str, text: str, known: set[str]) -> list[str]:
    problems: list[str] = []
    fm = FILE_RE.match(name)
    if not fm:
        return [f"{name}: file name must be NNNN-slug.md"]
    lines = text.splitlines()
    tm = TITLE_RE.match(lines[0]) if lines else None
    if not tm:
        problems.append(f"{name}: first line must be '# ADR-NNNN: Title'")
    elif tm.group(1) != fm.group(1):
        problems.append(f"{name}: title number differs from file number")
    fields = {}
    for line in lines[1:]:
        m = FIELD_RE.match(line)
        if m:
            fields.setdefault(m.group(1), m.group(2))
    for field in FIELDS:
        if not fields.get(field):
            problems.append(f"{name}: missing field '{field}'")
    if fields.get("Status") and fields["Status"] not in STATUSES:
        problems.append(f"{name}: Status is not one of {', '.join(STATUSES)}")
    if fields.get("Date") and not DATE_RE.match(fields["Date"]):
        problems.append(f"{name}: Date must be YYYY-MM-DD")
    if "Amends" in fields:
        am = AMENDS_RE.match(fields["Amends"])
        if not am or am.group(1) not in known:
            problems.append(f"{name}: Amends must name an existing ADR as ADR-NNNN")
    for section in SECTIONS:
        if f"## {section}" not in lines:
            problems.append(f"{name}: missing section '## {section}'")
    return problems


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    adr_dir = root / "docs" / "adr"
    files = (
        sorted(p for p in adr_dir.glob("*.md") if p.name != "TEMPLATE.md")
        if adr_dir.is_dir()
        else []
    )
    known = {m.group(1) for p in files if (m := FILE_RE.match(p.name))}
    problems: list[str] = []

    numbers: dict[str, str] = {}
    for p in files:
        m = FILE_RE.match(p.name)
        if m and m.group(1) in numbers:
            problems.append(f"{p.name}: number also used by {numbers[m.group(1)]}")
        elif m:
            numbers[m.group(1)] = p.name
        problems += validate(p.name, p.read_text(encoding="utf-8"), known)

    base = resolve_base(root, base_arg(argv))
    if base is None:
        print(f"{NAME}: no base ref available outside CI; immutability check skipped")
    else:
        mb = merge_base(root, base)
        for path, status in sorted(changed_files(root, mb).items()):
            if not path.startswith("docs/adr/") or path.endswith("/TEMPLATE.md"):
                continue
            old = show(root, mb, path)
            if old is None or status_of(old) != "Accepted":
                continue
            if status == "D":
                problems.append(f"{path}: an Accepted ADR cannot be deleted")
            elif status == "M" and not all(
                ln[1:].startswith("- Status:") for ln in changed_lines(root, mb, path)
            ):
                problems.append(f"{path}: an Accepted ADR may change only its Status line")
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME} ({len(files)} ADRs)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
