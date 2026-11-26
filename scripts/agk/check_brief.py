# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""A saved copy of a brief has the shape of SPEC-0030 rule 4.

    python3 check_brief.py FILE [--root DIR]

The body has one line `Sentence:` with the sentence in quotation marks (1 to 300 characters), one
line that starts `Answers` and ends with a colon followed by numbered items without a gap, zero or
more lines `Depends-on: #n`, one line `Size: S`, `Size: M` or `Size: L`, and (SPEC-0034 rule 2) one
line `Advances:` (REQ ids or `new`; brief #1929: `new` only beside a `Touches:` entry that is
exactly `docs/requirements.md`, an intake brief), one line `Touches:` (globs) and at most one
`Priority:` (0 to 3; SPEC-0032 rule 9: a `Priority: 0` brief needs one line `Measured:` with the
command and the output before and after a change that turns it green, except the red-branch
brief of the router). The
shape is the function `brief_problems` of `session.py`, which `session.py next` applies to the body
it reads. With `--root DIR` an `Advances:` that names a requirement that is not a `### REQ-n`
section of `DIR/docs/requirements.md` also fails, and (SPEC-0037 rule 10) a UI brief, one whose
`Touches:` glob meets a glob of `ui_paths` in the `[design]` table of `DIR/agk.toml`, needs exactly
one line `Screens: v<n> <screen>/<state>, ...` (`*` is every state of the screen) whose version has
a `design` row in `docs/design/signoffs.md` and a page `<screen>--<state>.html` for each pair in
its frozen folder. No `ui_paths` means no UI briefs. Amendment 161 item 5 (brief #1063): the line
may name an imported version `i<n>` instead, with a `design` row too, whose pairs are the
`<file> -> <screen>/<state>` rows of `docs/design/imported/i<n>/map.md` (`*` is every state of the
screen that the map covers; an `out:` row covers nothing).
With `--root DIR` and `plan_issue` in the `[flow]` table of `DIR/agk.toml` a brief also needs one
line `Wave: n` (amendment 140), a wave of `--waves` when that list is given. With `--root DIR` the
`Touches:` and `Adds:` lines are also judged against the tree (amendment 141 item 1); an optional
line `Adds:` lists the new files a brief creates and `Broad: <reason>` says that it is a sweep.
Brief #1660 (ADR-0691): `Adds: none` (any case) alone adds no file, and `Touches: none` touches
none; `none` beside a path or with punctuation (`None.`) is refused naming the line.
Amendment 142: one line `Contexts:` states every context of `session.CONTEXTS`, each with how the
change works there or `not applicable: <reason>`.
Amendment 168 (brief #1121): `Size: S` names at most 3 code paths in `Touches:` and `Size: M`
at most 6 (entries outside `tests/`, `docs/`, `changelog.d/` and `kit/hashes.json`; with
`--root DIR`, the limits of `brief_code_paths` in the `[flow]` table of `DIR/agk.toml`); `Broad:`
lifts the limit, and `Size: L` is refused beside a `Wave:` line.
Brief #982 (rule 4b): with `--root DIR`, a `Touches:` glob that meets a class of
`DIR/config/protected-paths.txt` in a brief that reserves no ADR and names no `Covered-by:` is
warned (`warning: ...` before `ok brief`, a `warnings` list in a passing event), never failed.

Brief #1425 (ADR-0598): with `--root DIR` each `Adds:` entry is also compared with the `Adds:` of
every other open brief and the files every open pull request adds (`plan_names.py`), read from
`--open-briefs FILE` (a saved list of issues, or `{"briefs": [...], "pulls": [...]}`) or else from
the plan's read cache, never by a request; a clash is refused naming the holder and a free name.
`--number N` (the issue number in `--event`) leaves the brief itself out. Two `Adds:`, `Touches:`,
`Reserved:` or `Expected:` lines are refused naming both and printing the one line to use.

Brief #1800 (ADR-0752): with `--root DIR` a brief that passes also shows its study, the `Impact:`,
`Wiring:`, `Prior:` and `Class:` lines of `brief_study.study_result`: warnings (`warning: study:
...`), failures for a brief filed on or after `[flow] brief_study_fails_from` (brief #1815,
ADR-0757): an event by the issue's `created_at`, a saved file by today's UTC date from
`common.utc_day`.
Brief #1813 (ADR-0756): `brief_result` is that whole reading, the one that `plan_intake.py
publish`, the steward's filing, fixing and triage and the conductor's guard call too.
Brief #1856 (ADR-0774, rule 4c): with a `[testing]` table, a brief whose `Touches:` does not name
`agk.toml` is warned for a new kit script no map entry or `always_full` covers and for a stated
whole test (failures from `[flow] brief_study_fails_from`), and for a closed-class test, a test
outside the map entry of a touched code path and a project's file-by-file mapped folder (warnings
only); a Reserved line whose path classes leave out a named `agk.toml` warns (rule 4b).
Brief #1972 (ADR-0824): a brief that names "standard library and `common.py` only" is warned
that the words read as the kit's offline set (`rules.py imports`), never failed.
Brief #2002 (ADR-0828): with `--root DIR`, each Approved spec of `DIR/docs/specs/` that the
Answers name, or whose `- Requirements:` names an `Advances:` id, needs one line `Spec fit:
SPEC-<nnnn> <part>[; <part>]` (`rule(s) <list> within` or `rule(s) <list> change by amendment
<m>`) naming every rule of it the brief names (`spec_fit_problems`); a missing line or rule warns
before `[flow] brief_study_fails_from` and fails from it; a wrong line, or a change without its
`Reserved:` amendment or quoted items (`> 1. ...` with `> Class:`), fails on any day. A fitted
rule's number limit the Answers state with another number warns.

`--event PAYLOAD` reads a saved `issues` event and prints one JSON line, for the job that labels a
brief filed on GitHub: `ignore`, `fail` with the label, the rules and the comment, or `pass` with
the label to clear and the wave.
Reads the files only: no network, no model. Messages name the rule, never the sentence.
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import brief_study
import design_signoff
import plan_names
import playbook_format
from common import (
    REQ_HEADER,
    CheckError,
    config_source,
    load_config,
    run,
    utc_day,
    utf8_output,
)
from gates.layers import architecture
from impact import is_test_file, matches, testing_table
from rules import IMPORTS_PHRASE, IMPORTS_WARNING
from session import (
    ADDS,
    TOUCHES,
    advances_ids,
    brief_problems,
    contexts_line_problems,
    line_entries,
    plan_issue_set,
    touches_of,
    wave_of,
    wave_problems,
)
from session_plan import touch_problems, touch_rules

from config import brief_code_paths

NAME = "brief"
USAGE = (
    "usage: check_brief.py (FILE | --event PAYLOAD) [--root DIR] [--waves N,N] "
    "[--open-briefs FILE] [--number N]"
)
REQUIREMENTS = "docs/requirements.md"
SCREENS = re.compile(r"Screens: ([vi][1-9]\d*) (\S.*)")
PAIR = re.compile(r"([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*|\*)")
NO_LINE = "rule 10: a brief that touches ui_paths has no Screens line"
SHAPE = "rule 10: the Screens line is not one line Screens: v<n>|i<n> <screen>/<state>, ..."
NOT_SIGNED = f"rule 10: the Screens version is not signed off in {design_signoff.SIGNOFFS}"
NOT_IN = "rule 10: a Screens screen or state is not in the version"
NOT_MAPPED = "rule 10: a Screens screen or state is not covered by the map of the version"
BRIEF_LABEL = "agk-brief"
INVALID_LABEL = "agk-brief-invalid"
COMMENT_MARK = "<!-- agk-brief-check -->"
EVENT_ACTIONS = ("opened", "edited", "labeled")
FLAGS = ("--root", "--event", "--waves", "--open-briefs", "--number")
ONE_LINE = ("Adds:", "Touches:", "Reserved:", "Expected:")  # brief #1425 answer 7
SHAPE_OF = {
    "Adds:": "rule 4: at most one line Adds:",
    "Touches:": "rule 2: exactly one line Touches:",
}
WAVES = re.compile(r"[1-9]\d*(,[1-9]\d*)*")
PROTECTED_PATHS = "config/protected-paths.txt"
ADR_LINE = re.compile(r"(Reserved:.*\bADR-\d+|Covered-by:\s*ADR-\d+)")
LAYER = "Layer:"
FOUNDATION = re.compile(r"^Kind:\s*foundation\s*$", re.M)
NO_LAYER = "SPEC-0072 rule 8: a build brief of a work-type project has no Layer: line, or two"
UNKNOWN_LAYER = "SPEC-0072 rule 8: a Layer: entry is no layer of [architecture] layers"
MISSED_LAYER = "SPEC-0072 rule 8: the Layer: line misses a layer that Touches meets"
WARN_4B = (
    "rule 4b: Touches names a protected path class ({}) and the brief reserves no ADR and "
    "names no Covered-by"
)


def absent_requirements(body: str, root: Path) -> list[str]:
    try:
        text = (root / REQUIREMENTS).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"rule 2: {REQUIREMENTS} cannot be read under the root") from exc
    known = {m.group(1) for m in map(REQ_HEADER.match, text.splitlines()) if m}
    if all(req in known for req in advances_ids(body)):
        return []
    return [f"rule 2: Advances names a requirement that is not a section of {REQUIREMENTS}"]


def ui_paths(root: Path) -> list[str]:
    """The `ui_paths` globs of the `[design]` table (none without it), naming the setting only."""
    try:
        design = config_source(root).get("design", {})
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError("rule 10: agk.toml cannot be read (setting: ui_paths)") from exc
    globs = design.get("ui_paths", []) if isinstance(design, dict) else None
    if not isinstance(globs, list) or not all(isinstance(g, str) and g for g in globs):
        raise CheckError("rule 10: ui_paths in [design] of agk.toml is not a list of globs")
    return globs


def _literal(glob: str) -> str:
    return re.split(r"[*?[]", glob, maxsplit=1)[0]


def touches_ui(touches: list[str], globs: list[str]) -> bool:
    """A `Touches:` glob and a `ui_paths` glob meet: either read as a path against the other with
    `fnmatch`, or the non-empty literal part of one starting with the other's."""
    for a in (t for t in touches if t):
        for b in globs:
            if fnmatch.fnmatchcase(a, b) or fnmatch.fnmatchcase(b, a):
                return True
            la, lb = _literal(a), _literal(b)
            if la and lb and (la.startswith(lb) or lb.startswith(la)):
                return True
    return False


def version_pages(root: Path, version: str) -> list[tuple[str, str]]:
    """The (screen, state) pairs of the `<screen>--<state>.html` pages of a version's folder."""
    folder = root / design_signoff.PROTOTYPE / version
    found = []
    for page in sorted(folder.glob("*.html")) if folder.is_dir() else []:
        screen, sep, state = page.stem.rpartition("--")
        if sep and PAIR.fullmatch(f"{screen}/{state}"):
            found.append((screen, state))
    return found


def imported_map(root: Path, version: str) -> dict[tuple[str, str], str]:
    """{(screen, state): file} of the `<file> -> <screen>/<state>` rows of an imported version's
    `map.md`, in the map's order; an `out:` row and a row of another shape cover nothing, and the
    first row of a pair counts (a second fails `check_design.py`). No map is an empty map."""
    import design_import  # installed beside this script; read only for an imported version

    folder = root / design_import.IMPORTED / version
    found: dict[tuple[str, str], str] = {}
    for name, target in design_import._rows(folder):
        match = design_import.TARGET.match(target)
        if match:
            found.setdefault((match.group(1), match.group(2)), name)
    return found


def screens_named(line: str, root: Path) -> list[tuple[str, str]]:
    """The pairs a `Screens:` line names, `*` expanded to every state of the screen in the
    version, in the line's order; refused naming rule 10 and never a value."""
    match = SCREENS.fullmatch(line.rstrip())
    if match is None:
        raise CheckError(SHAPE)
    pairs = [PAIR.fullmatch(i.strip()) for i in match.group(2).split(",")]
    if not all(pairs):
        raise CheckError(SHAPE)
    version = match.group(1)
    signed = {r["version"] for r in design_signoff.rows(root) if r["kind"] == "design"}
    if version not in signed:
        raise CheckError(NOT_SIGNED)
    imported = version.startswith("i")
    pages = list(imported_map(root, version)) if imported else version_pages(root, version)
    found: list[tuple[str, str]] = []
    for pair in filter(None, pairs):
        screen, state = pair.group(1), pair.group(2)
        named = [p for p in pages if p[0] == screen and state in ("*", p[1])]
        if not named:
            raise CheckError(NOT_MAPPED if imported else NOT_IN)
        found += [p for p in named if p not in found]
    return found


def screens_problems(body: str, root: Path) -> list[str]:
    """SPEC-0037 rule 10: what is wrong with the `Screens:` line of a UI brief, by the rule and
    never a value; nothing for a brief that is not a UI brief."""
    globs = ui_paths(root)
    if not globs or not touches_ui(touches_of(body), globs):
        return []
    lines = [ln for ln in body.splitlines() if ln.startswith("Screens:")]
    if not lines:
        return [NO_LINE]
    if len(lines) != 1:
        return [SHAPE]
    try:
        screens_named(lines[0], root)
    except CheckError as exc:
        return [str(exc)]
    return []


def layer_problems(body: str, root: Path) -> list[str]:
    """SPEC-0072 rule 8 (brief #1588, ADR-0668): a brief of a project with a work type, other than
    its foundation brief, has one `Layer:` line naming layers of the composed `[architecture]`,
    every layer its `Touches:` meets among them (`Q-S0072-15`); by the rule, never a value."""
    if playbook_format.declaration(root)[0] is None or FOUNDATION.search(body):
        return []
    lines = [ln for ln in body.splitlines() if ln.startswith(LAYER)]
    if len(lines) != 1:
        return [NO_LAYER]
    named = {e.strip() for e in lines[0][len(LAYER) :].split(",") if e.strip()}
    layers, _ = architecture(root)
    if not named or not named <= {name for name, _ in layers}:
        return [UNKNOWN_LAYER]
    touches = [t for t in touches_of(body) if t]
    met = {
        name
        for name, globs in layers
        for glob in globs
        if any(matches(t, glob) or matches(glob, t) for t in touches)
    }
    return [] if met <= named else [MISSED_LAYER]


def protected_classes(root: Path) -> list[str]:
    try:
        text = (root / PROTECTED_PATHS).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


def touches_class(touch: str, cls: str) -> bool:
    """A folder class (`x/`) meets a glob below or above it; a file class a glob matching it."""
    if fnmatch.fnmatchcase(cls, touch):
        return True
    if not cls.endswith("/"):
        return False
    lit = _literal(touch)
    return fnmatch.fnmatchcase(touch, cls + "*") or bool(
        lit and (lit.startswith(cls) or cls.startswith(lit))
    )


def protected_warnings(body: str, root: Path | None) -> list[str]:
    """Rule 4b (brief #982): a warning, never a failure, naming the classes and never a value."""
    if root is None or any(ADR_LINE.match(ln) for ln in body.splitlines()):
        return []
    touches = [t for t in touches_of(body) if t]
    named = [c for c in protected_classes(root) if any(touches_class(t, c) for t in touches)]
    return [WARN_4B.format(", ".join(named))] if named else []


KIT_MAKE = "kit/agk-kit.mk"  # only the kit has it, as `check_kit_tests.KIT_MAKE` reads
KIT_SCRIPT = "scripts/agk/*.py"  # one level, as the kit's coverage test globs
NEW_FILE = (
    "rule 4c: Adds names a new {} of the class {} that no [[testing.map]] entry or always_full "
    "covers, and Touches does not name agk.toml (setting: testing.map)"
)
WHOLE = (
    "rule 4c: line {} adds a whole test and Touches does not name agk.toml "
    "(setting: testing.whole_tests)"
)
CLOSED = (
    "rule 4c: an Adds test file of the class {} stands beside an answer **The class stays "
    "closed.**; a whole test joins testing.whole_tests in agk.toml, which Touches does not name"
)
JOINS = (
    "rule 4c: a test file of the class {} is not among the tests of the [[testing.map]] entry of a "
    "code path Touches names; a test that names that code joins the entry in agk.toml, which "
    "Touches does not name (setting: testing.map)"
)
WHOLE_SAID = re.compile(r"whole_tests|whole test", re.I)
CLASSES_LINE = re.compile(r"names the path class(es)?\b")
WARN_4B_TOML = "rule 4b: Touches names agk.toml and the Reserved line's path classes leave it out"


def _folder(path: str) -> str:
    return path.rsplit("/", 1)[0] + "/" if "/" in path else ""


def _sibling_mapped(root: Path, path: str, codes: list[str]) -> bool:
    """Answer 4 (brief #1856): another file of PATH's folder in the tree is a map entry's code."""
    folder = _folder(path)
    found = root / folder if folder else None
    if found is None or not found.is_dir():
        return False
    others = (f"{folder}{x.name}" for x in found.iterdir() if x.is_file())
    return any(o != path and any(matches(o, c) for c in codes) for o in others)


def reserved_warnings(body: str, root: Path, touches: list[str]) -> list[str]:
    """Answer 5 (brief #1856): Touches names agk.toml, a protected class, and the Reserved line's
    path classes leave it out."""
    lines = [x for x in body.splitlines() if x.startswith("Reserved:") and CLASSES_LINE.search(x)]
    named = any(matches("agk.toml", t) for t in touches)
    if not named or "agk.toml" not in protected_classes(root):
        return []
    return [WARN_4B_TOML] if lines and "agk.toml" not in lines[0] else []


def testing_problems(
    body: str, root: Path, today: str | None, filed: object = None
) -> tuple[list[str], list[str]]:
    """Rule 4c (brief #1856, ADR-0774), (failures, warnings): a new kit script no map entry or
    `always_full` covers (answer 1) and a stated whole test (answer 2) fail from `[flow]
    brief_study_fails_from` and warn before it; a closed-class test (answer 2), a test outside the
    touched entry (answer 3) and a project's mapped folder (answer 4) only warn. Each needs a
    `[testing]` table and a Touches line that does not name agk.toml."""
    touches = [t for t in line_entries(body, TOUCHES) if t]
    table = testing_table(root)
    if table is None or any(matches("agk.toml", t) for t in touches):
        return [], reserved_warnings(body, root, touches)
    adds = [a for a in line_entries(body, ADDS) if a]
    codes = [e["code"] for e in table["map"]]
    covered = codes + table["always_full"]
    cfg = load_config(root)
    tests = [p for p in adds + touches if is_test_file(p, cfg["test_dirs"], cfg["test_patterns"])]
    lines = body.splitlines()
    fails, warns = [], []
    new = [a for a in adds if a not in tests and not any(matches(a, g) for g in covered)]
    if (root / KIT_MAKE).is_file():
        if any(matches(a, KIT_SCRIPT) for a in new):
            fails.append(NEW_FILE.format("script", "scripts/agk/"))
    elif table["profile"] != "thorough" and table.get("map_source", "curated") == "curated":
        folders = dict.fromkeys(_folder(a) for a in new if _sibling_mapped(root, a, codes))
        warns += [NEW_FILE.format("file", f) for f in folders]
    added = [t for t in tests if t in adds]
    if table.get("whole_tests") and added:
        said = [
            n for n, x in enumerate(lines, 1)
            if WHOLE_SAID.search(x) and any(t in x or t.rsplit("/", 1)[-1] in x for t in added)
        ]  # fmt: skip
        fails += [WHOLE.format(n) for n in said]
        if not said and any(brief_study.CLOSED_ITEM.match(x) for x in lines):
            warns += [CLOSED.format(f) for f in dict.fromkeys(_folder(t) for t in added)]
    entries = [
        e for e in table["map"]
        if any(matches(t, e["code"]) or matches(e["code"], t) for t in touches if t not in tests)
    ]  # fmt: skip
    outside = [t for t in tests if not any(matches(t, g) for e in entries for g in e["tests"])]
    if entries and outside:
        warns.append(JOINS.format(", ".join(dict.fromkeys(_folder(t) for t in outside))))
    if not brief_study.enforced(root, today, filed):
        fails, warns = [], fails + warns
    return fails, warns


def duplicate_problems(body: str) -> list[str]:
    """Answer 7 of brief #1425: two lines of one key, naming both and the merged line to use."""
    out = []
    for key in ONE_LINE:
        found = [(i + 1, x.rstrip()) for i, x in enumerate(body.splitlines()) if x.startswith(key)]
        if len(found) < 2:
            continue
        lines = " and ".join(f"line {n}" for n, _ in found)
        items = [e.strip() for _, x in found for e in x[len(key) :].split(",") if e.strip()]
        use = f"use one line {key} {', '.join(dict.fromkeys(items))}"
        rule = "rule 2" if key == "Touches:" else "rule 4"
        tail = use if key != "Expected:" else "keep one"
        out.append(f"{rule}: {lines} are both {key} lines; {tail}")
    return out


def open_holders(root: Path, path: str | None) -> plan_names.Holders:
    """The open briefs and pull requests to compare with: the saved file, else the read cache."""
    if path is None:
        return plan_names.Holders(briefs=plan_names.cached_issues(root))
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError(
            "rule 4: the open briefs file cannot be read (option: --open-briefs)"
        ) from exc
    briefs, pulls = (
        (data, []) if isinstance(data, list) else (data.get("briefs"), data.get("pulls"))
    )
    if not isinstance(briefs, list) or not isinstance(pulls, list):
        raise CheckError("rule 4: the open briefs file is not a list (option: --open-briefs)")
    keep = [x for x in briefs if isinstance(x, dict) and "pull_request" not in x]
    return plan_names.Holders(briefs=keep, pulls=[x for x in pulls if isinstance(x, dict)])


INTAKE_ONLY = (
    f"rule 2: Advances: new is only for an intake brief, whose Touches names {REQUIREMENTS}"
    " (SPEC-0034 rule 2)"
)


def intake_problems(body: str) -> list[str]:
    """Brief #1929 (ADR-0797): `Advances: new` only beside a `Touches:` entry that is exactly the
    requirements file; a glob over it does not count. Reads no root."""
    lines = [x.rstrip() for x in body.splitlines()]
    if "Advances: new" not in lines or REQUIREMENTS in line_entries(body, TOUCHES):
        return []
    return [INTAKE_ONLY]


def body_problems(
    body: str, root: Path | None, waves: set[int] | None, opened: dict | None = None
) -> list[str]:
    """Every rule the body breaks: the shape first, then what needs the root. OPENED holds the
    `--open-briefs` file and the brief's own number (brief #1425)."""
    limits = None if root is None else brief_code_paths(root)  # amendment 168
    twice = duplicate_problems(body)
    keys = [k for k in SHAPE_OF if any(f" {k} lines" in p for p in twice)]
    problems = [
        p for p in brief_problems(body, limits) if not any(p.startswith(SHAPE_OF[k]) for k in keys)
    ]
    problems = twice + problems + intake_problems(body) + contexts_line_problems(body)
    if root is None or problems:
        return problems
    opened = opened or {}
    problems = (
        absent_requirements(body, root)
        or screens_problems(body, root)
        or layer_problems(body, root)
        or touch_problems(body, touch_rules(root))
        or plan_names.brief_problems(
            opened.get("number"), body, open_holders(root, opened.get("file"))
        )
    )
    if not problems and plan_issue_set(root):
        problems = wave_problems(body, waves)
    return problems


# --- brief #2002 (ADR-0828): the Spec fit line of each Approved spec a brief names --------------

FIT = "Spec fit:"
FIT_SETTING = "(setting: Spec fit:)"
RULE_LIST = r"\d+[a-z]?(?:(?:,? and |, )\d+[a-z]?)*"
FIT_LINE = re.compile(r"Spec fit: SPEC-(\d{4}) (\S.*)")
FIT_PART = re.compile(rf"rules? ({RULE_LIST}) (?:(within)|change by amendment (\d+))")
NAMED_RULES = re.compile(rf"\bSPEC-(\d{{4}}) rules? ({RULE_LIST})\b")
SPEC_NAMED = re.compile(r"\bSPEC-(\d{4})\b")
RULE_START = re.compile(r"^(\d+[a-z]?)\. ", re.M)
RESERVED_AMENDMENTS = re.compile(r"\bamendments? (\d+(?:(?:,? and |, )\d+)*)")
STUDY_HEAD = re.compile(r"^[A-Z][A-Za-z -]*:(?: |$)")
WORDS = ("one two three four five six seven eight nine ten eleven twelve thirteen fourteen"
         " fifteen sixteen seventeen eighteen nineteen twenty").split()  # fmt: skip
NUM = r"(\d+|" + "|".join(WORDS) + r")"
LIMITS = tuple(
    (name, re.compile(form.format(NUM), re.I))
    for name, form in (("at most", r"\bat most {}\b"), ("up to", r"\bup to {}\b"),
                       ("or fewer", r"\b{} or fewer\b"), ("batches of", r"\bbatches of {}\b"))
)  # fmt: skip


def rule_numbers(text: str) -> list[str]:
    """The rule numbers of a list such as `5, 11 and 12` (a lettered `7a` as written)."""
    return re.findall(r"\d+[a-z]?", text)


def answers_text(body: str) -> str:
    """The Answers section: from its `Answers...:` line to the next `Key:` line at the margin."""
    lines, out, inside = body.splitlines(), [], False
    for line in lines:
        if not inside:
            inside = line.startswith("Answers") and line.rstrip().endswith(":")
            continue
        if STUDY_HEAD.match(line):
            break
        out.append(line)
    return "\n".join(out)


def spec_rules(root: Path, number: str) -> tuple[str | None, dict[str, str]]:
    """(the spec's status or None without a file, {rule: its text}) of SPEC-NUMBER at ROOT."""
    for path in sorted((root / "docs" / "specs").glob(f"{number}-*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None, {}
        status = brief_study.STATUS.search(text)
        part = text.split("\n## Rules", 1)[-1].split("\n## ", 1)[0] if "\n## Rules" in text else ""
        starts = list(RULE_START.finditer(part))
        ends = [m.start() for m in starts[1:]] + [len(part)]
        return (status.group(1) if status else "", {
            m.group(1): part[m.start() : end] for m, end in zip(starts, ends, strict=True)
        })  # fmt: skip
    return None, {}


def fit_lines(body: str) -> list[tuple[int, str, str]]:
    """(index, spec number, rest) of each `Spec fit:` line; a malformed one has spec ``."""
    out = []
    for at, line in enumerate(body.splitlines()):
        if line.startswith(FIT):
            found = FIT_LINE.fullmatch(line.rstrip())
            out.append((at, found.group(1), found.group(2)) if found else (at, "", ""))
    return out


def fit_parts(rest: str) -> list[tuple[list[str], int | None]] | None:
    """[(rules, amendment or None for within)] of a line's parts, None when one is malformed."""
    parts = []
    for part in rest.split("; "):
        found = FIT_PART.fullmatch(part.strip())
        if found is None:
            return None
        parts.append(
            (rule_numbers(found.group(1)), int(found.group(3)) if found.group(3) else None)
        )
    return parts


def fit_items(body: str) -> dict[int, str]:
    """{amendment: its quoted items} of each `change` part (answer 5 reads them at filing)."""
    import check_amendments

    lines, out = body.splitlines(), {}
    for at, number, rest in fit_lines(body):
        for _, amendment in (fit_parts(rest) or []) if number else []:
            if amendment is not None:
                out[amendment] = check_amendments.quoted_items(lines, at)
    return out


def fit_changes(body: str) -> list[int]:
    """The amendments a brief's `Spec fit:` lines change rules by, in order."""
    return sorted(fit_items(body))


def limit_values(text: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for name, form in LIMITS:
        for value in form.findall(text):
            value = value.lower()
            found.setdefault(name, set()).add(
                str(WORDS.index(value) + 1) if value in WORDS else value
            )
    return found


def limit_warnings(body: str, number: str, rules: dict[str, str], named: set[str]) -> list[str]:
    """Answer 2's one heuristic: a fitted rule's number limit the Answers state with another
    number in the same form, while the line leaves that rule out (a warning only)."""
    stated = limit_values(answers_text(body))  # what the brief states it builds
    out = []
    for rule, words in rules.items():
        limits = limit_values(words)
        if rule not in named and any(stated.get(k, set()) - v for k, v in limits.items()):
            out.append(
                f"spec fit: SPEC-{number} rule {rule} states a number limit the brief states"
                f" with another number; name rule {rule} in the Spec fit: line {FIT_SETTING}"
            )
    return out


def spec_fit_problems(
    body: str, root: Path, today: str | None = None, filed: object = None
) -> tuple[list[str], list[str]]:
    """Brief #2002 answers 1, 2, 9 and 10 (ADR-0828): (failures, warnings) of the `Spec fit:`
    lines. A missing line, or a named rule left out of it, warns before `[flow]
    brief_study_fails_from` and fails on and after it; a wrong line fails on any day; a
    `Priority: 0` brief is held only for a `change`. Names the line, spec and rule, never text."""
    import check_amendments

    lines, wrong, late = body.splitlines(), [], []
    reserved = {
        int(n) for x in lines if x.startswith("Reserved:")
        for m in RESERVED_AMENDMENTS.finditer(x) for n in rule_numbers(m.group(1))
    }  # fmt: skip
    named: dict[str, set[str]] = {}
    for found in NAMED_RULES.finditer(body):
        named.setdefault(found.group(1), set()).update(rule_numbers(found.group(2)))
    stated: dict[str, set[str]] = {}
    seen: set[str] = set()
    for at, number, rest in fit_lines(body):
        parts = fit_parts(rest) if number else None
        if parts is None:
            wrong.append(f"spec fit: a Spec fit: line is malformed {FIT_SETTING}")
            continue
        if number in seen:
            wrong.append(
                f"spec fit: two Spec fit: lines for SPEC-{number}; write one {FIT_SETTING}"
            )
        seen.add(number)
        status, rules = spec_rules(root, number)
        if status != "Approved":
            wrong.append(f"spec fit: the Spec fit: line names SPEC-{number}, which is not Approved"
                         f" {FIT_SETTING}")  # fmt: skip
            continue
        within = {r for rs, m in parts if m is None for r in rs}
        changed = {r for rs, m in parts if m is not None for r in rs}
        stated[number] = within | changed
        where = f"spec fit: the Spec fit: line of SPEC-{number}"
        wrong += [f"{where} names rule {r}, which SPEC-{number} does not have {FIT_SETTING}"
                  for r in sorted(stated[number] - set(rules))]  # fmt: skip
        wrong += [f"{where} states rule {r} both within and changed {FIT_SETTING}"
                  for r in sorted(within & changed)]  # fmt: skip
        for m in sorted({m for _, m in parts if m is not None}):
            if m not in reserved:
                wrong.append(f"{where} changes by amendment {m}, which Reserved: does not name"
                             f" {FIT_SETTING}")  # fmt: skip
            quoted = check_amendments.quoted_items(lines, at)
            if not check_amendments.items(quoted):
                wrong.append(f"{where} changes by amendment {m} with no quoted items under the line"
                             f" {FIT_SETTING}")  # fmt: skip
            else:
                wrong += [
                    f"spec fit: {p}"
                    for p in check_amendments.file_problems(
                        f"Spec fit: SPEC-{number}", quoted, root
                    )
                ]
    if re.search(r"(?m)^Priority: 0\s*$", body):
        return wrong, []
    wanted = set(SPEC_NAMED.findall(answers_text(body)))
    advances = set(advances_ids(body))
    warns = []
    for spec in sorted((root / "docs" / "specs").glob("[0-9][0-9][0-9][0-9]-*.md")):
        number = spec.name[:4]
        status, rules = spec_rules(root, number)
        if status != "Approved":
            continue
        if number not in wanted and not spec_requirements(spec) & advances:
            continue
        if number not in seen:
            late.append(f"spec fit: SPEC-{number} has no Spec fit: line {FIT_SETTING}")
        else:
            late += [
                f"spec fit: the Spec fit: line of SPEC-{number} leaves out rule {r} {FIT_SETTING}"
                for r in sorted(named.get(number, set()) - stated.get(number, set()))
            ]
        warns += limit_warnings(body, number, rules, stated.get(number, set()))
    if wrong or brief_study.enforced(root, today, filed):
        return wrong + late, []
    return [], late + warns


def spec_requirements(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    found = re.search(r"(?m)^- Requirements:(.*)$", text)
    return set(re.findall(r"REQ-\d+", found.group(1))) if found else set()


def phrase_warnings(body: str) -> list[str]:
    """Brief #1972 answer 4 (ADR-0824): one warning, never a failure, on the import phrase."""
    return [IMPORTS_WARNING] if IMPORTS_PHRASE.search(body) else []


def brief_result(
    body: str,
    root: Path | None,
    waves: set[int] | None = None,
    opened: dict | None = None,
    today: str | None = None,
    filed: object = None,
) -> tuple[list[str], list[str]]:
    """Brief #1813 (ADR-0756): the one reading of a brief for every writer, (failures, warnings):
    `body_problems`, then, when it passes, the study of `brief_study.study_result` with the
    protected-path warnings. A writer never reads a brief with a part of this file alone. FILED
    is the issue's `created_at`; TODAY, the caller's day, is `common.utc_day()` when not given
    (brief #1815 answer 2)."""
    problems = body_problems(body, root, waves, opened)
    if problems:
        return problems, []
    number = (opened or {}).get("number")
    problems, study = brief_study.study_result(
        body,
        root,
        number if isinstance(number, int) else None,
        today=today or utc_day(),
        filed=filed,
    )
    if problems:
        return problems, []
    if root is None:
        return [], study + phrase_warnings(body)
    fails, testing = testing_problems(body, root, today or utc_day(), filed)  # brief #1856
    if fails:
        return fails, []
    fails, fit = spec_fit_problems(body, root, today or utc_day(), filed)  # brief #2002
    if fails:
        return fails, []
    return [], protected_warnings(body, root) + testing + study + fit + phrase_warnings(body)


def check(
    path: Path, root: Path | None = None, waves: set[int] | None = None, opened: dict | None = None
) -> int:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the brief file cannot be read") from exc
    problems, warnings = brief_result(body, root, waves, opened)
    if problems:
        raise CheckError("; ".join(problems))
    for warning in warnings:
        print(f"warning: {warning}")
    print(f"ok {NAME}")
    return 0


def event_comment(problems: list[str]) -> str:
    items = "\n".join(f"- {p}" for p in problems)
    return (
        f"{COMMENT_MARK}\nThe brief check refuses this brief:\n{items}\n\nEdit the body to fix it."
    )


def event_result(
    payload: dict,
    root: Path | None,
    waves: set[int] | None,
    opened: dict | None = None,
    today: str | None = None,
) -> dict:
    """What the job does for one saved `issues` event: the decision only, nothing is posted. The
    study is judged by the issue's `created_at` (brief #1815 answer 3)."""
    issue = payload.get("issue")
    labels = issue.get("labels") if isinstance(issue, dict) else None
    names = (
        {x.get("name") for x in labels if isinstance(x, dict)} if isinstance(labels, list) else ()
    )
    if (
        not isinstance(issue, dict)
        or payload.get("action") not in EVENT_ACTIONS
        or "pull_request" in issue
        or BRIEF_LABEL not in names
    ):
        return {"action": "ignore"}
    raw = issue.get("body")
    body = raw if isinstance(raw, str) else ""
    number = issue.get("number")
    problems, warnings = brief_result(
        body, root, waves, {**(opened or {}), "number": number}, today, issue.get("created_at")
    )
    if problems:
        return {
            "action": "fail",
            "issue": number,
            "label": INVALID_LABEL,
            "problems": problems,
            "comment": event_comment(problems),
        }
    result = {"action": "pass", "issue": number, "label": INVALID_LABEL, "wave": wave_of(body)}
    return {**result, "warnings": warnings} if warnings else result


def run_event(path: Path, root: Path | None, waves: set[int] | None, opened: dict) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError("the event file cannot be read") from exc
    found = payload if isinstance(payload, dict) else {}
    print(json.dumps(event_result(found, root, waves, opened)))
    return 0


def parsed(args: list[str]) -> tuple[dict[str, str], str | None] | None:
    """(the flags and their values, the one saved brief file); None for a usage error."""
    flags: dict[str, str] = {}
    rest = list(args)
    file = rest.pop(0) if rest and not rest[0].startswith("--") else None
    while len(rest) >= 2 and rest[0] in FLAGS and rest[0] not in flags:
        flags[rest[0]] = rest[1]
        rest = rest[2:]
    return (flags, file) if not rest and (file is None) == ("--event" in flags) else None


def wave_list(text: str | None) -> set[int] | None:
    if text is None:
        return None
    if not WAVES.fullmatch(text):
        raise CheckError("rule 4: --waves is not a comma-separated list of wave numbers")
    return {int(x) for x in text.split(",")}


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = sys.argv[1:] if argv is None else argv
    found = parsed(args)
    if found is None:
        print(USAGE)
        return 2
    flags, file = found
    root = Path(flags["--root"]) if "--root" in flags else None

    def act() -> int:
        waves = wave_list(flags.get("--waves"))
        number = flags.get("--number")
        if number is not None and not number.isdigit():
            raise CheckError("rule 4: --number is not an issue number")
        opened = {"file": flags.get("--open-briefs"), "number": int(number) if number else None}
        if file is None:
            return run_event(Path(flags["--event"]), root, waves, opened)
        return check(Path(file), root, waves, opened)

    return run(NAME, act)


if __name__ == "__main__":
    sys.exit(main())
