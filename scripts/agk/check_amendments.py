# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The class of each amendment item, and the steward's settled line (brief #1957, ADR-0813).

    python3 scripts/agk/check_amendments.py settle --amendment N --evidence E --agreed yes|no
        --comments FILE [--intake]

Each item of an amendment file from `FIRST_CLASSED` on carries one line `Class: correction`,
`Class: implementation` or `Class: behaviour` (answer 1). An item with no such line, one that
`BEHAVIOUR` marks (a new setting, gate, label, step, message or authority, or an intake), and a
`correction` that names no rule of an Approved spec are `behaviour` whatever the line says;
`file_problems` fails a mismatch naming the file, the item and ADR-0813, never the item's text,
and `check_numbers.py` runs it on each amendment file a pull request adds (answer 9).

`settle` prints the settled line (answer 2), with a `Text:` digest of the amendment as it reads
(answer 7: a changed text needs a new line), only when `[steward] settle_amendments` is on
(`settle_on`), the kit is not paused, the fresh reviewer agreed, every item is `correction` or
`implementation`, the amendment changes no principle, constitution or `spec_approvers` rule, it
is not an intake's and two owner overrides of a class in seven days, read from `--comments` (a
saved JSON list), have not stopped it (answer 4); otherwise it prints `owner: amendment <n> ...`
and exits 1. It posts nothing: the steward posts the line with `steward_evidence.py answer`, and
in personal mode the developer does. `settled_key`, `settled_keys`, `asked_keys`, `plain_ask` and
`digests` are the readings `route.py`, `merge_cleared.py` and the steward guard share (answer 3):
a settled line counts only for an amendment that is `settleable` at the head and whose text there
has the line's `Text:` digest. Files only: no network, no model.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (  # noqa: E402
    AMENDMENT,
    CheckError,
    option_pairs,
    paused,
    repo_root,
    run,
    utf8_output,
)

NAME = "amendments"
FIRST_CLASSED = 251  # the first amendment file written with `Class:` lines (ADR-0813)
CLASSES = ("correction", "implementation", "behaviour")
SETTLED_CLASSES = ("correction", "implementation")
# Answer 1 and 9: the one tuple of what makes an item `behaviour`, shared by the check and the step.
BEHAVIOUR = ("setting", "gate", "label", "step", "message", "authority")
MARKED = re.compile(
    r"\b(?:adds?|new|another|gives?)\b[^.\n]{0,40}?\b("
    + "|".join(BEHAVIOUR)
    + r")s?\b|\b(intake)\b",
    re.IGNORECASE,
)
OWNER_ONLY = re.compile(r"\bprinciple \d+\b|constitution/|\bspec_approvers\b", re.IGNORECASE)
CLASS_LINE = re.compile(r"^\s*Class:\s*(\S+)\s*$", re.MULTILINE)
ITEM = re.compile(r"^(\d+)\. ", re.MULTILINE)
RULE = re.compile(r"\bSPEC-(\d{4}) rules? (\d+)")
WHO = "Who: AGK steward"
SETTLED_FORM = "Answer: amendment {} settled (evidence: {}; class: {}; rule: {})"
SETTLED = re.compile(
    r"Answer: amendment (\d+) settled \(evidence: [^;()\n]+; class: (correction|implementation);"
    r" rule: SPEC-\d{4} rules? \d+\)"
)
TEXT_LINE = re.compile(r"^Text: ([0-9a-f]{16})$", re.MULTILINE)  # fix list item 4: the text settled
NUMBER = re.compile(r"[0-9]+")  # ASCII digits only (fix list item 6)
ASKED = re.compile(r"Maintainer answer: amendment (\d+) approved|Approve: (?:\S+ )?SPEC-(\d{4})")
OVERRIDE = ("Maintainer answer:", "Correction:")
OVERRIDE_DAYS, OVERRIDE_LIMIT = 7, 2  # SPEC-0059 rule 13's share, per class
PRINCIPLE_CLAUSE = (
    "the steward may settle an amendment of class correction or implementation that a fresh "
    "reviewer agrees with, where the owner turns it on"
)
USAGE = (
    "usage: check_amendments.py settle --amendment N --evidence E --agreed yes|no"
    " --comments FILE [--intake]"
)


def items(text: str) -> list[tuple[int, str]]:
    """The numbered items under `## Items` (the whole text when there is no such heading)."""
    part = text.split("\n## Items", 1)[-1].split("\n## ", 1)[0]
    starts = list(ITEM.finditer(part))
    ends = [m.start() for m in starts[1:]] + [len(part)]
    return [(int(m.group(1)), part[m.start() : end]) for m, end in zip(starts, ends, strict=True)]


def approved_rule(root: Path, text: str) -> str | None:
    """The first `SPEC-<nnnn> rule <n>` TEXT names whose spec is Approved at ROOT, else None."""
    for found in RULE.finditer(text):
        for path in sorted((root / "docs" / "specs").glob(f"{found.group(1)}-*.md")):
            try:
                if "\n- Status: Approved" in path.read_text(encoding="utf-8"):
                    return f"SPEC-{found.group(1)} rule {found.group(2)}"
            except (OSError, UnicodeDecodeError):
                continue
    return None


def item_class(text: str, root: Path, intake: bool = False) -> tuple[str, str | None]:
    """(the class an item TEXT has, the reason it is `behaviour` against its line or its rule)."""
    lines = CLASS_LINE.findall(text)
    declared = lines[0] if len(lines) == 1 and lines[0] in CLASSES else None
    rule = approved_rule(root, text)
    if declared is None:
        return "behaviour", "no Class line"
    if declared == "behaviour":
        return "behaviour", None
    found = MARKED.search(CLASS_LINE.sub("", text))
    if found is not None and not found.group(2):
        return "behaviour", f"Class: {declared} but it adds a {found.group(1).lower()}"
    if intake or found is not None:
        return "behaviour", f"Class: {declared} but it adds an intake"
    if rule is None and declared == "correction":
        return "behaviour", "Class: correction but it names no rule of an Approved spec"
    return declared, None


def file_problems(name: str, text: str, root: Path) -> list[str]:
    """Each item of the amendment file NAME whose class line is missing or wrong (answer 1)."""
    found = []
    for number, body in items(text):
        _, why = item_class(body, root)
        if why is not None:
            found.append(f"{name} item {number}: {why} (ADR-0813 answer 1)")
    return found


def added_problems(root: Path, added: list[tuple[int, str]]) -> list[str]:
    """`file_problems` of each ADDED amendment (number, path) from `FIRST_CLASSED` on."""
    found = []
    for number, path in added:
        if number >= FIRST_CLASSED and (root / path).is_file():
            try:
                text = (root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                found.append(f"{path}: not readable UTF-8 text (ADR-0813 answer 1)")
                continue
            found += file_problems(path, text, root)
    return found


def digest(text: str) -> str:
    """The short digest of an amendment's text that a settled line records (answer 7)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def settleable(text: str, root: Path) -> bool:
    """Whether every item of TEXT is `correction` or `implementation` and none names a principle,
    `constitution/` or `spec_approvers` (answer 2); the header, which names principle 6 in
    every amendment, is not read."""
    listed = items(text)
    if not listed or any(OWNER_ONLY.search(body) for _, body in listed):
        return False
    return all(item_class(body, root)[0] in SETTLED_CLASSES for _, body in listed)


def digests(texts: dict[str, str | None], root: Path) -> dict[str, str]:
    """{`amendment <n>`: digest} of each of TEXTS (the amendment files at the head) that is
    `settleable`; a text that could not be read settles nothing (fix list item 2)."""
    return {k: digest(t) for k, t in texts.items() if t is not None and settleable(t, root)}


def amendment_key(path: str) -> str | None:
    found = AMENDMENT.fullmatch(path)
    return f"amendment {int(found.group(1))}" if found else None


def amendment_path(key: str) -> str:
    return f"docs/runs/proposed-spec-amendments-{key.split()[1]}.md"


def settle_on(root: Path | None) -> bool:
    """Whether `[steward] settle_amendments` is on at ROOT, with a spec approver listed (answer 6);
    a refused or unreadable setting is off."""
    if root is None:
        return False
    try:
        from reviewers import spec_approvers

        from config import settle_refusal, steward_settings

        if settle_refusal(root) is not None:
            return False
        return steward_settings(root)["settle_amendments"] is True and bool(spec_approvers(root))
    except (CheckError, OSError, ValueError):
        return False


def stopped(cls: str, records: list[tuple[str, datetime]], now: datetime) -> bool:
    """Whether two owner overrides of CLS in seven days stop the steward settling it (answer 4)."""
    since = now - timedelta(days=OVERRIDE_DAYS)
    return sum(1 for c, when in records if c == cls and when >= since) >= OVERRIDE_LIMIT


def settle(
    number: int,
    text: str,
    root: Path,
    evidence: str,
    agreed: bool,
    intake: bool = False,
    overrides: list[tuple[str, datetime]] | None = None,
    now: datetime | None = None,
) -> str | None:
    """The settled comment for amendment NUMBER of TEXT, or None when it is the owner's."""
    listed = items(text)
    if not (agreed and settle_on(root)) or paused(root) or not settleable(text, root):
        return None
    kinds = {item_class(body, root, intake)[0] for _, body in listed}
    if not kinds <= set(SETTLED_CLASSES):
        return None
    if any(stopped(k, overrides or [], now or datetime.now(UTC)) for k in kinds):
        return None
    rule = next((r for _, b in listed if (r := approved_rule(root, b))), approved_rule(root, text))
    if rule is None or not re.fullmatch(r"[^;()\n]+", evidence or ""):
        return None
    cls = "correction" if "correction" in kinds else "implementation"
    first_line = SETTLED_FORM.format(number, evidence, cls, rule)
    return f"{first_line}\nText: {digest(text)}\n\n{WHO}\n"


def first(comment: dict) -> tuple[str, str, str]:
    body = str(comment.get("body") or "")
    login = str((comment.get("user") or {}).get("login") or "").lstrip("@").lower()
    return (body.splitlines() or [""])[0].strip(), body, login


def settled_key(line: str, body: str, settles: dict[str, str]) -> str | None:
    """`amendment <n>` of a settled first LINE whose BODY carries the steward's marker and the
    `Text:` digest SETTLES holds for that amendment at the head (fix list items 2 and 4)."""
    found = SETTLED.fullmatch(line)
    if not found or WHO not in body:
        return None
    key = f"amendment {int(found.group(1))}"
    text = TEXT_LINE.search(body)
    return key if text is not None and settles.get(key) == text.group(1) else None


def plain_ask(comments: list[dict]) -> bool:
    """Whether an `Owner needed:` asks more than approvals: none offered, or a Q id named."""
    return any(
        first(c)[0].startswith("Owner needed:")
        and (not asked_keys([c]) or re.search(r"\bQ-[\w-]+-\d+\b", first(c)[1]))
        for c in comments
    )


def asked_keys(comments: list[dict]) -> set[str]:
    """The approvals each `Owner needed:` offers alone on a line (`amendment <n>`, `SPEC-<n>`)."""
    keys = set()
    for c in comments:
        line, body, _ = first(c)
        if not line.startswith("Owner needed:"):
            continue
        for raw in body.splitlines():
            found = ASKED.fullmatch(raw.strip().strip("`").strip())
            if found:
                keys.add(
                    f"amendment {int(found.group(1))}"
                    if found.group(1)
                    else f"SPEC-{found.group(2)}"
                )
    return keys


def settled_keys(comments: list[dict], approvers: list[str], settles: dict[str, str]) -> set[str]:
    """The amendments a settled line by an account in APPROVERS settles after its newest ask,
    for the text SETTLES holds at the head."""
    allowed = {str(a).lstrip("@").lower() for a in approvers}
    done: set[str] = set()
    for c in comments:
        line, body, login = first(c)
        if line.startswith("Owner needed:"):
            done -= asked_keys([c])
        elif login in allowed and (key := settled_key(line, body, settles)):
            done.add(key)
    return done


def overrides(comments: list[dict]) -> list[tuple[str, datetime]]:
    """(class, when) of each owner `Maintainer answer:` or `Correction:` naming an amendment a
    settled line settled before it (SPEC-0059 rule 13, answer 4)."""
    classes: dict[str, str] = {}
    found = []
    for c in comments:
        if not isinstance(c, dict):
            raise CheckError("a comment record is not an object (ADR-0813 answer 4)")
        line, body, _ = first(c)
        try:
            when = datetime.fromisoformat(str(c["created_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            raise CheckError(
                "a comment record has no readable created_at (ADR-0813 answer 4)"
            ) from None
        if when.tzinfo is None:
            raise CheckError("a comment record has no readable created_at (ADR-0813 answer 4)")
        if (m := SETTLED.fullmatch(line)) and WHO in body:
            classes.setdefault(m.group(1), m.group(2))
        elif line.startswith(OVERRIDE):
            named = re.search(r"\bamendment (\d+)\b", line)
            if named and named.group(1) in classes:
                found.append((classes[named.group(1)], when))
    return found


def comment_records(path: Path) -> list[dict]:
    """The saved comments (a JSON list) the override share reads; unreadable is a refusal."""
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError("the comments file cannot be read (setting: --comments)") from None
    if not isinstance(records, list):
        raise CheckError("the comments file is not a list (setting: --comments)")
    return records


def command(args: list[str]) -> int:
    intake = "--intake" in args
    rest = [a for a in args if a != "--intake"]
    opts = dict(option_pairs(rest[1:], strict=False)) if rest[:1] == ["settle"] else {}
    keys = {"--amendment", "--evidence", "--agreed", "--comments"}
    if set(opts) != keys or len(rest) != 9:
        print(USAGE)
        return 2
    if not NUMBER.fullmatch(opts["--amendment"]) or opts["--agreed"] not in ("yes", "no"):
        print(USAGE)
        return 2
    number, root = int(opts["--amendment"]), repo_root()
    from config import settle_refusal

    if (refused := settle_refusal(root)) is not None:
        raise CheckError(refused)
    records = overrides(comment_records(Path(opts["--comments"])))
    path = root / "docs" / "runs" / f"proposed-spec-amendments-{number}.md"
    if not path.is_file():
        raise CheckError(f"amendment {number} is not in docs/runs/ (ADR-0813 answer 2)")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise CheckError(
            f"amendment {number} is not readable UTF-8 text (path class docs/runs/)"
        ) from None
    agreed = opts["--agreed"] == "yes"
    line = settle(number, text, root, opts["--evidence"], agreed, intake, records)
    if line is None:
        print(f"owner: amendment {number} (ADR-0813 answer 2; setting: steward.settle_amendments)")
        return 1
    print(line, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = sys.argv[1:] if argv is None else argv
    return run(NAME, lambda: command(args))


if __name__ == "__main__":
    sys.exit(main())
