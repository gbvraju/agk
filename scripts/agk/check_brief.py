"""A saved copy of a brief has the shape of SPEC-0030 rule 4.

    python3 check_brief.py FILE [--root DIR]

The body has one line `Sentence:` with the sentence in quotation marks (1 to 300 characters), one
line that starts `Answers` and ends with a colon followed by numbered items without a gap, zero or
more lines `Depends-on: #n`, one line `Size: S`, `Size: M` or `Size: L`, and (SPEC-0034 rule 2) one
line `Advances:` (REQ ids or `new`), one line `Touches:` (globs) and at most one `Priority:`
(0 to 3; SPEC-0032 rule 9: a `Priority: 0` brief needs one line `Measured:` with the command and the
output before and after a change that turns it green, except the red-branch brief of the
router). The
shape is the function `brief_problems` of `session.py`, which `session.py next` applies to the body
it reads. With `--root DIR` an `Advances:` that names a requirement that is not a `### REQ-n`
section of `DIR/docs/requirements.md` also fails, and (SPEC-0037 rule 10) a UI brief, one whose
`Touches:` glob meets a glob of `ui_paths` in the `[design]` table of `DIR/agk.toml`, needs exactly
one line `Screens: v<n> <screen>/<state>, ...` (`*` is every state of the screen) whose version has
a `design` row in `docs/design/signoffs.md` and a page `<screen>--<state>.html` for each pair in
its frozen folder. No `ui_paths` means no UI briefs.
With `--root DIR` and `plan_issue` in the `[flow]` table of `DIR/agk.toml` a brief also needs one
line `Wave: n` (amendment 140), a wave of `--waves` when that list is given. With `--root DIR` the
`Touches:` and `Adds:` lines are also judged against the tree (amendment 141 item 1); an optional
line `Adds:` lists the new files a brief creates and `Broad: <reason>` says that it is a sweep.
Amendment 142: one line `Contexts:` states every context of `session.CONTEXTS`, each with how the
change works there or `not applicable: <reason>`.
Brief #982 (rule 4b): with `--root DIR`, a `Touches:` glob that meets a class of
`DIR/config/protected-paths.txt` in a brief that reserves no ADR and names no `Covered-by:` is
warned (`warning: ...` before `ok brief`, a `warnings` list in a passing event), never failed.

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

import design_signoff
from common import REQ_HEADER, CheckError, config_source, run
from session import (
    advances_ids,
    brief_problems,
    contexts_line_problems,
    plan_issue_set,
    touches_of,
    wave_of,
    wave_problems,
)
from session_plan import touch_problems, touch_rules

NAME = "brief"
USAGE = "usage: check_brief.py (FILE | --event PAYLOAD) [--root DIR] [--waves N,N]"
REQUIREMENTS = "docs/requirements.md"
SCREENS = re.compile(r"Screens: (v[1-9]\d*) (\S.*)")
PAIR = re.compile(r"([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*|\*)")
NO_LINE = "rule 10: a brief that touches ui_paths has no Screens line"
SHAPE = "rule 10: the Screens line is not one line Screens: v<n> <screen>/<state>, ..."
NOT_SIGNED = f"rule 10: the Screens version is not signed off in {design_signoff.SIGNOFFS}"
NOT_IN = "rule 10: a Screens screen or state is not in the version"
BRIEF_LABEL = "agk-brief"
INVALID_LABEL = "agk-brief-invalid"
COMMENT_MARK = "<!-- agk-brief-check -->"
EVENT_ACTIONS = ("opened", "edited", "labeled")
FLAGS = ("--root", "--event", "--waves")
WAVES = re.compile(r"[1-9]\d*(,[1-9]\d*)*")
PROTECTED_PATHS = "config/protected-paths.txt"
ADR_LINE = re.compile(r"(Reserved:.*\bADR-\d+|Covered-by:\s*ADR-\d+)")
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
    pages = version_pages(root, version)
    found: list[tuple[str, str]] = []
    for pair in filter(None, pairs):
        screen, state = pair.group(1), pair.group(2)
        named = [p for p in pages if p[0] == screen and state in ("*", p[1])]
        if not named:
            raise CheckError(NOT_IN)
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


def body_problems(body: str, root: Path | None, waves: set[int] | None) -> list[str]:
    """Every rule the body breaks: the shape first, then what needs the root."""
    problems = brief_problems(body) + contexts_line_problems(body)
    if root is None or problems:
        return problems
    problems = (
        absent_requirements(body, root)
        or screens_problems(body, root)
        or touch_problems(body, touch_rules(root))
    )
    if not problems and plan_issue_set(root):
        problems = wave_problems(body, waves)
    return problems


def check(path: Path, root: Path | None = None, waves: set[int] | None = None) -> int:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the brief file cannot be read") from exc
    problems = body_problems(body, root, waves)
    if problems:
        raise CheckError("; ".join(problems))
    for warning in protected_warnings(body, root):
        print(f"warning: {warning}")
    print(f"ok {NAME}")
    return 0


def event_comment(problems: list[str]) -> str:
    items = "\n".join(f"- {p}" for p in problems)
    return (
        f"{COMMENT_MARK}\nThe brief check refuses this brief:\n{items}\n\nEdit the body to fix it."
    )


def event_result(payload: dict, root: Path | None, waves: set[int] | None) -> dict:
    """What the job does for one saved `issues` event: the decision only, nothing is posted."""
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
    number, problems = issue.get("number"), body_problems(body, root, waves)
    if problems:
        return {
            "action": "fail",
            "issue": number,
            "label": INVALID_LABEL,
            "problems": problems,
            "comment": event_comment(problems),
        }
    result = {"action": "pass", "issue": number, "label": INVALID_LABEL, "wave": wave_of(body)}
    warnings = protected_warnings(body, root)
    return {**result, "warnings": warnings} if warnings else result


def run_event(path: Path, root: Path | None, waves: set[int] | None) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError("the event file cannot be read") from exc
    print(json.dumps(event_result(payload if isinstance(payload, dict) else {}, root, waves)))
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
    args = sys.argv[1:] if argv is None else argv
    found = parsed(args)
    if found is None:
        print(USAGE)
        return 2
    flags, file = found
    root = Path(flags["--root"]) if "--root" in flags else None

    def act() -> int:
        waves = wave_list(flags.get("--waves"))
        if file is None:
            return run_event(Path(flags["--event"]), root, waves)
        return check(Path(file), root, waves)

    return run(NAME, act)


if __name__ == "__main__":
    sys.exit(main())
