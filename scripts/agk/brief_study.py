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

In the kit (`kit/agk-kit.mk` under the root, brief #2052, ADR-0850) a brief also has one line
`Existing:` before its Answers line: items `- ...` naming `<path>:<line>` with `not enough: <text>`,
or `Existing: none: <text>` with a backquoted `grep`, `git grep`, `rg` or `brief_study.py` command
and a `<n> match(es)` count, held as the other study lines are. `code_matches` finds the scripts,
functions and settings the brief names under `scripts/` and `.claude/hooks/`, and the study warns on
the first `CODE_WARNINGS` that `Existing:` leaves out; the command prints them as `code ...` lines.
A project's tree (brief #2065, ADR-0857) is held to the same line, failing only from its own day;
an item there may name a kit command or kit path in backquotes without a line. `project_matches`
searches `project_source` (the project's own code), the kit's scripts and reference guide, the packs
in use and the build files' dependencies, warning as `defines`, `declares` or `documents`.
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import kit_root
import plan_names
from common import CheckError, run, utf8_output
from session import touches_of

from config import BRIEF_PRIOR_WARNINGS, TABLE_KEYS, brief_prior_warnings, brief_study_fails_from

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
# Brief #2052 (ADR-0850): only the kit repository has the marker (`check_kit_tests.KIT_MAKE`).
KIT_MAKE = "kit/agk-kit.mk"
CONFIG = "scripts/agk/config.py"  # answer 2: a setting's key, when agk.toml does not set it
CODE_WARNINGS = 10  # answer 2 (Q-P0A-2): the code matches warned at most, with one count line
EXISTING_REF = re.compile(r"(?<![\w./*-])([\w.-]*[/.][\w./-]*):(\d+)\b")
EXISTING_SEARCH = re.compile(r"`(?:grep|git grep|rg|brief_study\.py)\b[^`]*`")
EXISTING_COUNT = re.compile(r"\b\d+ match(?:es)?\b")
SPAN = re.compile(r"`([^`\n]+)`")
SCRIPT_TERM = re.compile(r"[\w./-]*\w\.py")
FUNCTION_TERM = re.compile(r"([A-Za-z_]\w*)\.([A-Za-z_]\w*)|([A-Za-z_]\w*)\(.*")
SETTING_TERM = re.compile(r"\[(\w+)\]\s+(\w+)|(\w+)\.(\w+)")
# Brief #2065 (ADR-0857): a project's source, read at most `SOURCE_FILES` files.
SOURCE_FILES = 2000
NOT_SOURCE = ("config/", "constitution/", ".github/")
REFERENCE = "docs/guides/reference.md"
PARTS = "docs/parts.md"
DECLARES = r"^\s*(?:export\s+)?(?:default\s+)?(?:pub\s+)?(?:async\s+)?"
DECLARE_WORDS = "function|class|const|let|var|func|fn|interface|type|export"


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
    return define_line(_read(path), name) is not None


def define_line(text: str, name: str) -> int | None:
    """The first line of TEXT that defines NAME (a `def`, a `class` or a top-level name)."""
    form = rf"^(\s*(async\s+)?def\s+{name}\s*\(|class\s+{name}\b|{name}\s*(:[^=\n]*)?=)"
    found = re.search(form, text, re.M)
    return (
        text.count("\n", 0, found.end()) + 1 if found else None
    )  # the leading space may span lines


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
        numbers = pattern.findall(text)
        found = [p.name for p in (root / folder).glob(glob.format("*"))] if numbers else []
        # one listing per folder (brief #1815: the plan reads this per open brief)
        known = {n.split("-", 1)[0] for n in found} if glob.startswith("{}-") else set(found)
        for number in numbers:
            if (number if glob.startswith("{}-") else glob.format(number)) not in known:
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


def is_kit(root: Path) -> bool:
    """Brief #2052 answer 3: the Existing line and the code search hold only in the kit."""
    return (root / KIT_MAKE).is_file()


def existing_section(lines: list[str]) -> tuple[list[int], list[str]]:
    """(the indexes of the `Existing:` lines, the first one's text with its items up to the first
    blank line)."""
    heads = [i for i, x in enumerate(lines) if x.startswith("Existing:")]
    if not heads:
        return heads, []
    section = [lines[heads[0]].rstrip()]
    for line in lines[heads[0] + 1 :]:
        if not line.strip():
            break
        section.append(line.rstrip())
    return heads, section


def _place(path: str) -> str:
    parent = Path(path).parent.as_posix()
    return "the root" if parent in (".", "") else f"{parent}/"


def existing_problems(lines: list[str], root: Path) -> list[str]:
    """Brief #2052 answers 1 and 5: what the `Existing:` line breaks, naming the line or a path's
    class, never the brief's text; nothing outside the kit."""
    heads, section = existing_section(lines)
    answers = next((i for i, x in enumerate(lines) if x.startswith("Answers")), None)
    if not heads:
        return ["study: the Existing line is missing: Existing: (items, or none: <search>)"]
    if len(heads) != 1:
        return ["study: exactly one line Existing: (items, or none: <search>) before Answers"]
    if answers is not None and heads[0] > answers:
        return ["study: the Existing line stands after the Answers line"]
    text = section[0][len("Existing:") :].strip()
    if text.startswith("none:"):
        if PLACEHOLDER in text:
            return []  # the render's placeholder: `placeholder_warnings` names it
        if EXISTING_SEARCH.search(text) and EXISTING_COUNT.search(text):
            return []
        return [
            "study: the Existing none: form needs a backquoted search command and a match count"
        ]
    items = [x for x in section[1:] if x.lstrip().startswith("- ")]
    if text or not items:
        return ["study: the Existing line is Existing: alone with items - ..., or Existing: none:"]
    problems = []
    for item in items:
        refs = EXISTING_REF.findall(item)
        feature = any(not re.search(r":\d+$", x) for x in SPAN.findall(item))
        if not refs and (is_kit(root) or not feature):  # Q-P0AP-2: a kit command, no line
            problems.append("study: an Existing item names no <path>:<line>")
        if "not enough:" not in item:
            problems.append("study: an Existing item holds no not enough: <reason>")
        for path, number in refs:
            target = root / path
            if not target.is_file():
                problems.append(f"study: an Existing item names no file of {_place(path)}")
            elif not 1 <= int(number) <= len(_read(target).splitlines()):
                problems.append(
                    f"study: an Existing item names a line past a file of {_place(path)}"
                )
    return problems


def _code_files(root: Path) -> list[Path]:
    return sorted({*root.glob("scripts/**/*.py"), *root.glob(".claude/hooks/*.py")})


def _setting_line(root: Path, table: str, key: str) -> tuple[str, int] | None:
    current = None
    for number, line in enumerate(_read(root / "agk.toml").splitlines(), start=1):
        header = re.fullmatch(r"\s*\[\[?\s*([\w.-]+)\s*\]\]?\s*(#.*)?", line)
        if header:
            current = header.group(1)
        elif current == table and re.match(rf"\s*{re.escape(key)}\s*=", line):
            return "agk.toml", number
    try:  # the kit's own file, by the resolver (ADR-0759): the root's copy in the kit
        config = kit_root.kit_file(root, CONFIG)
    except kit_root.Refused:
        return None
    for number, line in enumerate(_read(config).splitlines(), 1):
        if f'"{key}"' in line:
            return CONFIG, number
    return None


def code_terms_named(body: str) -> list[str]:
    """Answer 2's search terms: the backquoted spans of the `Sentence:` line and the Answers
    items, then the code paths of `Touches:`; `agk.toml` and `kit/hashes.json` are none."""
    lines = body.splitlines()
    text = [x for x in lines if x.startswith("Sentence:")]
    start = next((i for i, x in enumerate(lines) if x.startswith("Answers")), None)
    for line in lines[start + 1 :] if start is not None else []:
        if line.strip() and not (line[:1].isdigit() or line[:1].isspace()):
            break
        text.append(line)
    spans = [s.strip() for s in SPAN.findall("\n".join(text))]
    paths = [t.strip() for t in touches_of(body)]
    spans += [t for t in paths if _code(t) and not re.search(r"[*?[]", t)]
    return [t for t in dict.fromkeys(spans) if t and t not in SHARED]


def code_matches(body: str, root: Path) -> list[tuple[str, int, str]]:
    """Brief #2052 answer 2: (path, line, term) of each script, function and setting the brief
    names that a file under `scripts/` or `.claude/hooks/` defines; in a project, the matches of
    `project_matches` (brief #2065). A file that cannot be read is skipped. Files only."""
    if not is_kit(root):
        return [match[:3] for match in project_matches(body, root)[0]]
    files = _code_files(root)
    texts: dict[Path, str] = {}

    def text(path: Path) -> str:
        if path not in texts:
            texts[path] = _read(path)
        return texts[path]

    def rel(path: Path) -> str:
        return path.relative_to(root).as_posix()

    found: list[tuple[str, int, str]] = []
    for term in code_terms_named(body):
        hits: list[tuple[str, int]] = []
        setting = SETTING_TERM.fullmatch(term)
        table, key = (
            (setting.group(1) or setting.group(3), setting.group(2) or setting.group(4))
            if setting
            else ("", "")
        )
        function = FUNCTION_TERM.fullmatch(term)
        if SCRIPT_TERM.fullmatch(term):
            if "/" in term:
                hits = [(term, 1)] if (root / term) in files else []
            else:
                hits = [(rel(p), 1) for p in files if p.name == term]
        elif setting and table in TABLE_KEYS:
            place = _setting_line(root, table, key)
            hits = [place] if place else []
        elif function:
            module, name = function.group(1), function.group(2) or function.group(3)
            for path in files:
                if module is not None and path.stem != module:
                    continue
                line = define_line(text(path), name)
                if line is not None:
                    hits.append((rel(path), line))
        found += [(path, line, term) for path, line in hits]
    return found


def declare_line(text: str, name: str, ext: str) -> int | None:
    """Brief #2065 answer 3: the first line of TEXT that declares NAME, by `define_line` in a
    `.py` file, else a whole-word `function`, `class`, `const`, ... or `export` declaration."""
    if ext == ".py":
        return define_line(text, name)
    form = rf"{DECLARES}(?:{DECLARE_WORDS})\s+\*?{re.escape(name)}\b"
    found = re.search(form, text, re.M)
    return text.count("\n", 0, found.end()) + 1 if found else None


def declares(path: Path, name: str) -> bool:
    return declare_line(_read(path), name, path.suffix) is not None


def project_source(root: Path) -> tuple[list[str], int]:
    """Brief #2065 answer 2: (the project's source files read, sorted, the count left unread): the
    files `project_lint_paths` names, else the tracked source files less the docs, tests, vendored
    folders and the kit's folders; at most `SOURCE_FILES` under `survey.TOO_LARGE` bytes. Raises
    `CheckError` naming the setting when `project_lint_paths` is refused."""
    import tomllib  # noqa: PLC0415 - only a project's search needs these

    import survey
    from check_licence_notice import KIT_FOLDERS
    from common import test_dirs
    from gates import pins

    import config

    files = pins.tracked(root)
    globs = config.project_lint_paths(root)
    if globs is not None:
        found = [f for f in files if any(fnmatch.fnmatchcase(f, g) for g in globs)]
    else:
        try:
            with open(Path(survey.__file__).resolve().parents[2] / survey.SIGNALS, "rb") as handle:
                ignore = set(tomllib.load(handle).get("ignore", []))
        except (OSError, tomllib.TOMLDecodeError):
            ignore = set()
        try:
            tests = tuple(f"{str(d).strip('/')}/" for d in test_dirs(root))
        except (CheckError, OSError, ValueError):
            tests = ()
        out = (*NOT_CODE, *tests, *KIT_FOLDERS, *NOT_SOURCE)
        found = [
            f
            for f in files
            if Path(f).suffix in survey.LANGUAGES
            and not f.startswith(out)
            and not set(f.split("/")[:-1]) & ignore
        ]
        named = {row["path"] for row in survey.detect_test_files(found)}
        found = [f for f in found if f not in named]
    sized = []
    for rel in sorted(found):
        try:
            if (root / rel).stat().st_size <= survey.TOO_LARGE:
                sized.append(rel)
        except OSError:
            continue
    return sized[:SOURCE_FILES], max(0, len(sized) - SOURCE_FILES)


def _first_line(text: str, needle: str) -> int | None:
    return next((n for n, x in enumerate(text.splitlines(), 1) if needle in x), None)


def _parts(root: Path, notes: list[str]) -> list[tuple[str, str, str]]:
    """(name, file, needle) of each part: the `Part` column of `docs/parts.md` when it has one,
    else the direct dependencies of each `pins.STACKS` build file at the root; then each pack id
    of `packs.used`."""
    import packs
    from gates import pins  # noqa: PLC0415

    out: list[tuple[str, str, str]] = []
    rows = [x.strip().strip("|").split("|") for x in _read(root / PARTS).splitlines()]
    rows = [[c.strip() for c in r] for r in rows if len(r) > 1]
    if rows and "Part" in rows[0]:
        at = rows[0].index("Part")
        out = [(r[at].strip("`"), PARTS, r[at]) for r in rows[2:] if len(r) > at and r[at]]
    else:
        for _pack, build, _lock, reader in pins.STACKS.values():
            if (root / build).is_file():
                try:
                    out += [
                        (n, build, f'"{n}"') for n, _v, _f in pins.declared(root, reader, build)
                    ]
                except (OSError, ValueError, KeyError, TypeError, CheckError):
                    continue
    try:
        out += [(pid, "agk.toml", pid) for pid, _ in packs.used(root)]
    except (packs.Refused, CheckError):
        notes.append("not run pack search (setting: packs)")
    return out


def project_matches(body: str, root: Path) -> tuple[list[tuple[str, int, str, str]], list[str]]:
    """Brief #2065 answer 3: ((path, line, term, verb) of each match, the `not run` and count
    lines) in a project: its source, then the kit's scripts, the kit's reference guide and the
    parts. A layer that cannot be read is left out with one line naming the setting."""
    notes: list[str] = []
    try:
        source, unread = project_source(root)
    except CheckError as exc:
        return [], [f"not run code search: {exc}"]
    if unread:
        notes.append(f"code search: {unread} files not read")
    kit: Path | None = None
    reference: Path | None = None
    try:
        kit, reference = kit_root.kit_dir(root), kit_root.kit_file(root, REFERENCE)
    except kit_root.Refused:
        notes.append("not run kit search: no kit copy (setting: CLAUDE_PLUGIN_ROOT)")
    scripts = sorted(kit.glob("*.py")) if kit is not None and kit.is_dir() else []
    parts = _parts(root, notes)
    guide = _read(reference) if reference is not None else ""

    def rel(path: Path) -> str:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return f"scripts/agk/{path.name}"

    found: list[tuple[str, int, str, str]] = []
    for term in code_terms_named(body):
        function = FUNCTION_TERM.fullmatch(term)
        name = (function.group(2) or function.group(3)) if function else None
        module = function.group(1) if function else None
        hits = [(f, 1) for f in source if f == term or ("/" not in term and Path(f).name == term)]
        for rel_path in source if not hits else []:
            if name is not None and (module is None or Path(rel_path).stem == module):
                line = declare_line(_read(root / rel_path), name, Path(rel_path).suffix)
                hits += [(rel_path, line)] if line else []
        for path in scripts if not hits else []:
            if SCRIPT_TERM.fullmatch(term) and path.name == Path(term).name:
                hits.append((rel(path), 1))
            elif name and (module is None or path.stem == module):
                line = define_line(_read(path), name)
                hits += [(rel(path), line)] if line else []
        found += [(p, n, term, "defines") for p, n in hits]
        if not hits:
            for part, file, needle in parts:
                if term == part:
                    line = _first_line(_read(root / file), needle) or 1
                    found.append((file, line, term, "declares"))
        if not hits and guide:
            line = _first_line(guide, f"`{term}")
            if line:
                found.append((REFERENCE, line, term, "documents"))
    return list(dict.fromkeys(found)), notes


def code_warnings(body: str, root: Path, matches: list[tuple]) -> list[str]:
    """Answer 2: a warning for each match the `Existing:` section leaves out (all of them under
    `none:`), at most `CODE_WARNINGS`, with one line counting the rest."""
    _, section = existing_section(body.splitlines())
    named = "\n".join(section)
    if section and section[0][len("Existing:") :].strip().startswith("none:"):
        named = ""
    left = [
        f"study: Existing leaves out {m[0]}:{m[1]}, which {(*m, 'defines')[3]} {m[2]}"
        for m in matches
        if not _named(named, [m[0], Path(m[0]).name])
    ]
    left = list(dict.fromkeys(left))
    if len(left) > CODE_WARNINGS:
        more = len(left) - CODE_WARNINGS
        left = left[:CODE_WARNINGS] + [
            f"study: Existing: {more} more code matches not warned;"
            " brief_study.py <file> --root . lists them"
        ]
    return left


SIGNAL_NAMED = re.compile(r"\bsignal: (?:none \(.+?\)|[a-z0-9]+(?:-[a-z0-9]+)*\b)", re.I)
NO_SIGNAL = "study: the Measured line names no signal (signal: <id> or signal: none (<reason>))"


def signal_problems(lines: list[str]) -> list[str]:
    """Brief #2054 answer 5: a `Measured:` line whose after-part (all of it when it names no
    `after`) names no `signal: <id>` or `signal: none (<reason>)` is warned, never failed."""
    measured = next((x for x in lines if x.startswith("Measured:")), None)
    if measured is None:
        return []
    after = re.split(r"\bafter\b", measured, maxsplit=1)
    return [] if SIGNAL_NAMED.search(after[-1]) else [NO_SIGNAL]


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
    problems += existing_problems(lines, root) if full else []  # brief #2052
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
    filled = placeholder_warnings(lines) + signal_problems(lines)
    if True:  # brief #2052, extended to a project by brief #2065: the placeholder and the search
        filled += [
            "study: the Existing line is the render's placeholder"
            for x in lines
            if x.startswith("Existing:") and PLACEHOLDER in x
        ][:1]
        if held(body)[1]:
            kit = is_kit(root)
            found = code_matches(body, root) if kit else project_matches(body, root)[0]
            left += code_warnings(body, root, found)
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
        for path, line, term in code_matches(body, root):  # brief #2052 answer 2
            print(f"code {path}:{line}: {term}")
        for note in [] if is_kit(root) else project_matches(body, root)[1]:  # brief #2065
            print(note)
        return 0

    return run(NAME, act)


if __name__ == "__main__":
    sys.exit(main())
