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
Reads the file only: no network, no model. Messages name the rule, never the sentence.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_signoff
from common import REQ_HEADER, CheckError, config_source, run
from session import advances_ids, brief_problems, touches_of

NAME = "brief"
USAGE = "usage: check_brief.py FILE [--root DIR]"
REQUIREMENTS = "docs/requirements.md"
SCREENS = re.compile(r"Screens: (v[1-9]\d*) (\S.*)")
PAIR = re.compile(r"([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*|\*)")
NO_LINE = "rule 10: a brief that touches ui_paths has no Screens line"
SHAPE = "rule 10: the Screens line is not one line Screens: v<n> <screen>/<state>, ..."
NOT_SIGNED = f"rule 10: the Screens version is not signed off in {design_signoff.SIGNOFFS}"
NOT_IN = "rule 10: a Screens screen or state is not in the version"


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
    `fnmatch`, or the literal part of one starting with the other's."""
    for a in (t for t in touches if t):
        for b in globs:
            if fnmatch.fnmatchcase(a, b) or fnmatch.fnmatchcase(b, a):
                return True
            if _literal(a).startswith(_literal(b)) or _literal(b).startswith(_literal(a)):
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
    lines = [ln for ln in body.splitlines() if ln.startswith("Screens")]
    if not lines:
        return [NO_LINE]
    if len(lines) != 1:
        return [SHAPE]
    try:
        screens_named(lines[0], root)
    except CheckError as exc:
        return [str(exc)]
    return []


def check(path: Path, root: Path | None = None) -> int:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the brief file cannot be read") from exc
    problems = brief_problems(body)
    if root is not None and not problems:
        problems = absent_requirements(body, root) or screens_problems(body, root)
    if problems:
        raise CheckError("; ".join(problems))
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[2]) if len(args) == 3 and args[1] == "--root" else None
    if len(args) != 1 and root is None:
        print(USAGE)
        return 2
    return run(NAME, lambda: check(Path(args[0]), root))


if __name__ == "__main__":
    sys.exit(main())
