# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The study a kit brief shows before it is filed (brief #1800, ADR-0752).

    python3 brief_study.py FILE --root DIR [--open-briefs FILE]

Prints the earlier record a brief's writer must read: each ADR and spec under `DIR/docs/` whose
text names a code path of `Touches:` (a `.py` file also by its file name), a `Wiring:` file or a
`Wiring:` function as `<module>.<function>`; each proposed amendment under `DIR/docs/runs/` that
names one and that its spec does not yet name (`amendment <n>`); and each open brief of the
plan's read cache, or of the saved list `--open-briefs FILE`, whose code paths in `Touches:` meet
this one's. Each line ends `strong` or `weak` (brief #1819): a hit is strong when a full code path
or a `Wiring:` `<module>.<function>` stands in the record's header (every line before the first
`## `) or its `## Decision` section (the whole record when it has none); strong records come first,
ranked by the distinct strong terms they name, then the newer number.
`agk.toml` and `kit/hashes.json`, which nearly every change touches, are no search term. Without
the cache the open-brief part prints `briefs: not read (no plan cache)`.

`study_result` is what `check_brief.py --root` applies: one `Impact:` line followed by the five
lines `Speed:`, `Quality:`, `GitHub:`, `Cost:` and `Tests:` in that order, each with a text or
`none: <reason>`; one `Wiring: <file>:<function> called by <callers>; ...` line whose files and
functions (a `def`, a `class` or a top-level name) exist under the root, or `Wiring: none:
<reason>`; one `Prior:` line whose ADR, spec and amendment ids exist, or `Prior: none: <what was
searched>`; and one `Class: <kind>; seen <n> ...` line, where `seen` above 0 needs an answer item
headed `**The class stays closed.**`. They are warnings, and failures for a brief filed on or after
`[flow] brief_study_fails_from` of the root's agk.toml (brief #1815, ADR-0757): judged by the
issue's `created_at`, else by the `today` its caller passes; unset, never. A `Priority: 0` brief,
the router's red-branch brief among them, is held only to `Class:` and `Prior:`. A study line
that holds the render's placeholder `(verify) for the person to state` is warned on any day and
never failed (brief #1813, ADR-0756).
An open brief the study finds and `Prior:` leaves out is always a warning, and so are the first
`[flow] brief_prior_warnings` (10 when unset) strong Accepted ADRs it leaves out, with one line
counting the rest. Reads files and the cache only: no network, no model.
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import plan_names
from common import CheckError, run, utf8_output
from session import touches_of

from config import BRIEF_PRIOR_WARNINGS, brief_prior_warnings, brief_study_fails_from

NAME = "brief-study"
USAGE = "usage: brief_study.py FILE --root DIR [--open-briefs FILE]"
IMPACT_NAMES = ("Speed", "Quality", "GitHub", "Cost", "Tests")
NOT_CODE = ("tests/", "docs/", "changelog.d/")
SHARED = ("agk.toml", "kit/hashes.json")  # nearly every change touches them: no search term
WIRING_ENTRY = re.compile(r"\s*(\S+):([A-Za-z_]\w*)\s+called by\s+\S.*")
CLASS_LINE = re.compile(r"Class: \S.*?; seen (\d+)\b.*")
# Brief #1813 answer 3: the text `plan_intake.py render` leaves for the person on each study line.
PLACEHOLDER = "(verify) for the person to state"
STUDY_NAMES = (*IMPACT_NAMES, "Wiring", "Prior", "Class")
CLOSED_ITEM = re.compile(r"\d+\.\s+\*\*The class stays closed\.\*\*")
REFS = (
    (re.compile(r"\bADR-(\d{4})\b"), "docs/adr", "{}-*.md", "ADR-{}"),
    (re.compile(r"\bSPEC-(\d{4})\b"), "docs/specs", "{}-*.md", "SPEC-{}"),
    (
        re.compile(r"\b[Aa]mendments? (\d+)\b"),
        "docs/runs",
        "proposed-spec-amendments-{}.md",
        "amendment {}",
    ),
)
STATUS = re.compile(r"^- Status:\s*(\w+)", re.M)
AMENDMENT = re.compile(r"proposed-spec-amendments-(\d+)\.md")
SPEC_OF = re.compile(r"\bSPEC-(\d{4})\b")
# Brief #1819 answer 2: the Accepted ADRs warned at most, strongest first; `[flow]
# brief_prior_warnings` sets it (Maintainer answer Q-F11-1), this is its default.
PRIOR_WARNINGS = BRIEF_PRIOR_WARNINGS
SECTION = re.compile(r"^## ", re.M)
DECISION = re.compile(r"^## Decision\b.*$", re.M)


FILED = re.compile(r"(\d{4}-\d{2}-\d{2})T")


def filed_day(created: object) -> str | None:
    """The UTC day of an issue's `created_at` (`YYYY-MM-DDT...Z`), None when it cannot be read."""
    match = FILED.match(created) if isinstance(created, str) else None
    return match.group(1) if match else None


def enforced(root: Path, today: str | None, filed: object = None) -> bool:
    """Brief #1815 answer 2: the study lines fail for a brief filed on or after the root's
    `[flow] brief_study_fails_from`, judged by its `created_at`, else by the caller's `today`;
    with no day set, or no day to judge by, they warn."""
    day = brief_study_fails_from(root)
    judged = filed_day(filed) or today
    return day is not None and judged is not None and judged >= str(day)


def _one(lines: list[str], key: str) -> str | None:
    found = [x.rstrip() for x in lines if x.startswith(key)]
    return found[0][len(key) :].strip() if len(found) == 1 else None


def impact_problems(lines: list[str]) -> list[str]:
    heads = [i for i, x in enumerate(lines) if x.rstrip() == "Impact:"]
    if len(heads) != 1:
        return ["study: exactly one line Impact: followed by " + ", ".join(IMPACT_NAMES)]
    after = [x.rstrip() for x in lines[heads[0] + 1 : heads[0] + 1 + len(IMPACT_NAMES)]]
    problems = []
    for at, name in enumerate(IMPACT_NAMES):
        line = after[at] if at < len(after) else ""
        if not line.startswith(f"{name}:"):
            problems.append(f"study: the Impact line {name}: is missing or out of order")
        elif not line[len(name) + 1 :].strip() or line[len(name) + 1 :].strip() in (
            "none",
            "none:",
        ):
            problems.append(f"study: the Impact line {name}: has no text (or none: <reason>)")
    return problems


def defines(path: Path, name: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    form = rf"^(\s*(async\s+)?def\s+{name}\s*\(|class\s+{name}\b|{name}\s*(:[^=\n]*)?=)"
    return re.search(form, text, re.M) is not None


def wiring_entries(text: str) -> list[tuple[str, str]] | None:
    """The (file, function) pairs of a `Wiring:` text, None when an entry has another shape."""
    found = []
    for entry in (e for e in text.split(";") if e.strip()):
        match = WIRING_ENTRY.fullmatch(entry)
        if match is None:
            return None
        found.append((match.group(1), match.group(2)))
    return found


def wiring_problems(lines: list[str], root: Path) -> list[str]:
    text = _one(lines, "Wiring:")
    if text is None:
        return ["study: exactly one line Wiring: <file>:<function> called by <callers>; ..."]
    if text.startswith("none:") and text[5:].strip():
        return []
    entries = wiring_entries(text)
    if not entries:
        return ["study: the Wiring line is not <file>:<function> called by <callers>; ..."]
    for file, name in entries:
        if not (root / file).is_file():
            return [f"study: the Wiring line names a file that is not in the tree ({file})"]
        if not defines(root / file, name):
            return [f"study: the Wiring line names a function {file} does not define ({name})"]
    return []


def prior_problems(lines: list[str], root: Path) -> list[str]:
    text = _one(lines, "Prior:")
    if not text:
        return ["study: exactly one line Prior: naming the earlier record, or Prior: none: <what>"]
    for pattern, folder, glob, label in REFS:
        for number in pattern.findall(text):
            if not any((root / folder).glob(glob.format(number))):
                return [f"study: the Prior line names {label.format(number)}, not in {folder}/"]
    return []


def class_problems(lines: list[str]) -> list[str]:
    text = _one(lines, "Class:")
    match = CLASS_LINE.fullmatch(f"Class: {text}") if text else None
    if match is None:
        return ["study: exactly one line Class: <the kind>; seen <n> times (<refs>)"]
    if int(match.group(1)) > 0 and not any(CLOSED_ITEM.match(x) for x in lines):
        return ["study: Class seen before needs an Answers item **The class stays closed.**"]
    return []


def code_terms(body: str) -> list[str]:
    """The search terms: code paths of `Touches:` and `Wiring:` (a `.py` file also by name), and
    `<module>.<function>` of each `Wiring:` pair."""
    lines = body.splitlines()
    paths = [
        t for t in (x.strip() for x in touches_of(body)) if _code(t) and not re.search(r"[*?[]", t)
    ]
    pairs = wiring_entries(_one(lines, "Wiring:") or "") or []
    paths += [f for f, _ in pairs if f not in paths]
    terms = list(paths) + [Path(p).name for p in paths if p.endswith(".py")]
    terms += [f"{Path(f).stem}.{n}" for f, n in pairs]
    return list(dict.fromkeys(terms))


def _named(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if re.search(rf"(?<![\w/.-]){re.escape(t)}(?![\w-])", text)]


def _names(text: str, terms: list[str]) -> str | None:
    found = _named(text, terms)
    return found[0] if found else None


def strong_terms(body: str) -> list[str]:
    """The terms whose hit is strong (brief #1819 answer 1): full code paths and the `Wiring:`
    `<module>.<function>` names; a bare file name is weak."""
    terms = code_terms(body)
    return [t for t in terms if "/" in t or not t.endswith(".py")]


def strong_text(text: str) -> str:
    """The places a strong hit is read: the header (every line before the first `## `) and the
    `## Decision` section; a record with no `## Decision` heading is read whole (answer 7)."""
    decision = DECISION.search(text)
    if decision is None:
        return text
    first = SECTION.search(text)
    end = SECTION.search(text, decision.end())
    return (
        text[: first.start() if first else 0]
        + text[decision.start() : end.start() if end else None]
    )


def _code(path: str) -> bool:
    return bool(path) and not path.startswith(NOT_CODE) and path not in SHARED


def _meet(a: str, b: str) -> bool:
    la, lb = (re.split(r"[*?[]", x, maxsplit=1)[0] for x in (a, b))
    if not la or not lb:
        return False
    return (
        fnmatch.fnmatchcase(a, b)
        or fnmatch.fnmatchcase(b, a)
        or la.startswith(lb)
        or lb.startswith(la)
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def candidates(body: str, root: Path, briefs: list[dict] | None, number: int | None = None):
    """(kind, ref, status, why, strength) of each record to read, strong records first ranked by
    the distinct strong terms they name, then the newer number, then the open briefs, then the
    weak records; briefs None means no cache was read."""
    terms, strong = code_terms(body), strong_terms(body)
    ranked: list[tuple[int, int, tuple[str, str, str, str, str]]] = []
    weak: list[tuple[str, str, str, str, str]] = []

    def add(kind: str, ref: str, status: str, text: str, hits: list[str], num: int) -> None:
        sure = _named(strong_text(text), [t for t in hits if t in strong])
        if sure:
            ranked.append((-len(sure), -num, (kind, ref, status, sure[0], "strong")))
        else:
            weak.append((kind, ref, status, hits[0], "weak"))

    for kind, folder, label in (("adr", "docs/adr", "ADR-{}"), ("spec", "docs/specs", "SPEC-{}")):
        for path in sorted((root / folder).glob("[0-9][0-9][0-9][0-9]-*.md")):
            text = _read(path)
            hits = _named(text, terms) if terms else []
            if hits:
                status = STATUS.search(text)
                ref = label.format(path.name[:4])
                add(
                    kind,
                    ref,
                    status.group(1) if status else "unknown",
                    text,
                    hits,
                    int(path.name[:4]),
                )
    specs = root / "docs" / "specs"
    for path in sorted((root / "docs" / "runs").glob("proposed-spec-amendments-*.md")):
        match = AMENDMENT.fullmatch(path.name)
        text = _read(path)
        hits = _named(text, terms) if match and terms else []
        spec = SPEC_OF.search(text.split("\n", 1)[0]) if hits else None
        if match is None or not hits or spec is None:
            continue
        spec_text = "".join(_read(p) for p in specs.glob(f"{spec.group(1)}-*.md"))
        if not re.search(rf"\b[Aa]mendments? {match.group(1)}\b", spec_text):
            ref = f"amendment {match.group(1)}"
            add("amendment", ref, f"SPEC-{spec.group(1)}", text, hits, int(match.group(1)))
    found = [entry for _, _, entry in sorted(ranked, key=lambda r: (r[0], r[1]))]
    mine = [t.strip() for t in touches_of(body) if _code(t.strip())]
    for issue in briefs or []:
        other = [t.strip() for t in touches_of(str(issue.get("body") or "")) if _code(t.strip())]
        hit = next((t for t in mine for o in other if _meet(t, o)), None)
        if hit and issue.get("number") != number:
            found.append(("brief", f"brief #{issue.get('number')}", "open", hit, "strong"))
    return found + weak


def placeholder_warnings(lines: list[str]) -> list[str]:
    """Answer 3 of brief #1813: a study line that still holds the render's placeholder is warned
    on any day, naming the line, and never failed: it is a line left to fill, not a study."""
    return [
        f"study: the {name} line is the render's placeholder"
        for name in STUDY_NAMES
        if any(x.startswith(f"{name}:") and PLACEHOLDER in x for x in lines)
    ]


def held(body: str) -> tuple[bool, bool]:
    """(held to the study at all, held to Impact and Wiring too): a `Priority: 0` brief, the
    router's red-branch brief among them, only to `Class:` and `Prior:` (brief #1815 answer 5)."""
    lines = [x.rstrip() for x in body.splitlines()]
    return True, "Priority: 0" not in lines


def study_problems(body: str, root: Path) -> list[str]:
    """What the study lines break, by the line and never a value: no ADR scan, no cache."""
    _, full = held(body)
    lines = body.splitlines()
    problems = (impact_problems(lines) + wiring_problems(lines, root)) if full else []
    return problems + prior_problems(lines, root) + class_problems(lines)


def study_failures(body: str, root: Path, filed: object, today: str | None) -> list[str]:
    """Brief #1815 answer 4: the failures alone, for the plan's brief shape; nothing before the
    day or with none set."""
    return study_problems(body, root) if enforced(root, today, filed) else []


def study_result(
    body: str,
    root: Path | None,
    number: int | None = None,
    today: str | None = None,
    briefs: list[dict] | None = None,
    filed: object = None,
) -> tuple[list[str], list[str]]:
    """(failures, warnings) of the study lines; nothing without a root (answer 5). FILED is the
    issue's `created_at`, TODAY the caller's day (brief #1815 answer 2)."""
    if root is None:
        return [], []
    lines = body.splitlines()
    problems = study_problems(body, root)
    prior = _one(lines, "Prior:") or ""
    if briefs is None:
        briefs = plan_names.cached_issues(root)
    found = candidates(body, root, briefs, number)
    out = [
        (kind, ref, status, why)
        for kind, ref, status, why, strength in found
        if (kind == "adr" and status == "Accepted" and strength == "strong") or kind == "brief"
        if not re.search(rf"{re.escape(ref)}(?!\d)", prior)
    ]
    adrs = [x for x in out if x[0] == "adr"]
    cap = brief_prior_warnings(root)
    kept = adrs[:cap] + [x for x in out if x[0] == "brief"]
    left = [
        f"study: Prior leaves out {ref} ({status}), which names {why}"
        for _, ref, status, why in kept
    ]
    if len(adrs) > cap:
        left.append(
            f"study: Prior: {len(adrs) - cap} more candidates not warned;"
            " brief_study.py <file> --root . lists them"
        )
    filled = placeholder_warnings(lines)
    if enforced(root, today, filed):
        return problems, filled + left
    return [], problems + filled + left


def open_briefs(path: str | None, root: Path) -> list[dict] | None:
    if path is None:
        return plan_names.cached_issues(root) or None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError("the open briefs file cannot be read (option: --open-briefs)") from exc
    items = (
        data if isinstance(data, list) else data.get("briefs") if isinstance(data, dict) else None
    )
    if not isinstance(items, list):
        raise CheckError("the open briefs file is not a list (option: --open-briefs)")
    return [x for x in items if isinstance(x, dict) and "pull_request" not in x]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if (
        len(args) not in (3, 5)
        or args[1] != "--root"
        or (len(args) == 5 and args[3] != "--open-briefs")
    ):
        print(USAGE)
        return 2
    file, root = Path(args[0]), Path(args[2])
    saved = args[4] if len(args) == 5 else None

    def act() -> int:
        try:
            body = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CheckError("the brief file cannot be read") from exc
        briefs = open_briefs(saved, root)
        for kind, ref, status, why, strength in candidates(body, root, briefs):
            detail = f"{status}, not in the spec" if kind == "amendment" else status
            print(f"{ref} ({detail}): names {why}; {strength}")
        if briefs is None:
            print("briefs: not read (no plan cache)")
        return 0

    return run(NAME, act)


if __name__ == "__main__":
    sys.exit(main())
