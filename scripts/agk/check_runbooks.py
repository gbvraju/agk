"""The runbook check (SPEC-0056 rules 4 to 7; REQ-063 AC2, AC3 and AC4). Installed: a verbatim entry
of `kit/manifest.json`; a step of `agk-governance` after `check_playbooks.py`.

    python3 scripts/agk/check_runbooks.py [--root DIR]

Reads every `docs/runbooks/*.md` and prints `ok runbooks`, or one `FAIL runbooks: <page> rule <n>:
<problem>` line per problem and exits 1, naming the page, the rule and a fixed word for the problem
and never the page's text. With no `docs/runbooks/` folder it prints `skipped (no runbooks)` and
passes; with the folder, a kit page that is absent fails. Files only: no network, and no command a
page names is ever run. It imports the standard library, `common.py` and, for rule 7, `guard.py`.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard
from common import CheckError, repo_root, run

NAME = "runbooks"
FOLDER = "docs/runbooks"
KIT_PAGES = ("actions-blocked.md", "leaked-secret.md", "red-default-branch.md")
SECTIONS = ("When this applies", "Who acts", "Steps", "Over when", "By mode")
MODES = ["GitHub", "Local", "Personal"]
MAX_LINES = 60
MAX_WORDS = 500
PROGRAMS = {"python3", "gh", "git", "make", "date", "gitleaks"}
GH_VERBS = {"api", "issue", "run", "workflow", "label"}
GIT_PLAIN = {"fetch", "status", "rev-parse"}

FENCE = re.compile(r"\s*(`{3,}|~{3,})(.*)$")
PLACEHOLDER = re.compile(r"<[^\s<>](?:[^<>]*[^\s<>])?>")
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
BLOCK_START = re.compile(r"\s*(#|[-*+]\s|\d+\.\s)")
INLINE_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)")
REFERENCE_LINK = re.compile(r"\s{0,3}\[[^\]]+\]:\s*<?([^\s>]+)")
SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
SCRIPT = re.compile(r"scripts/agk/[A-Za-z0-9_]+\.py")
STEP = re.compile(r"([1-9]\d*)\.\s")
NESTED_STEP = re.compile(r"\s+\d+\.\s")
BULLET = re.compile(r"[-*+]\s+[*_`]*(\w+)")
MAKE_RULE = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_.% -]*?)\s*:(?!=)")
OPERATORS = set("();<>|&")

Line = tuple[int, str]


def split_page(text: str) -> tuple[list[Line], list[Line]]:
    """The lines outside fenced blocks (with each opening fence), and the lines inside them."""
    prose: list[Line] = []
    code: list[Line] = []
    fence = ""
    for number, line in enumerate(text.splitlines(), 1):
        found = FENCE.match(line)
        if fence:
            closes = found and found[1][0] == fence[0] and len(found[1]) >= len(fence)
            if closes and not found[2].strip():
                fence = ""
            elif line.strip():
                code.append((number, line.strip()))
        elif found and not (found[1][0] == "`" and "`" in found[2]):
            fence = found[1]
            prose.append((number, line))
        else:
            prose.append((number, line))
    return prose, code


def sections(prose: list[Line]) -> tuple[list[Line], list[Line], list[tuple[str, list[Line]]]]:
    """The `# ` title lines, the non-blank lines before the first `## `, and the sections."""
    titles: list[Line] = []
    before: list[Line] = []
    found: list[tuple[str, list[Line]]] = []
    for number, line in prose:
        if line.startswith("# "):
            titles.append((number, line))
        elif line.startswith("## "):
            found.append((line[3:].strip(), []))
        elif found:
            found[-1][1].append((number, line))
        elif line.strip():
            before.append((number, line))
    return titles, before, found


def steps_problem(body: list[Line]) -> str | None:
    """Rule 4: one list, numbered from 1 in order; an indented line continues the item above."""
    expected = 1
    for _, line in body:
        item = STEP.match(line)
        if item:
            if int(item[1]) != expected:
                return "steps-out-of-order"
            expected += 1
        elif NESTED_STEP.match(line):
            return "steps-nested-list"
        elif line.strip() and not line[0].isspace():
            return "steps-not-numbered"
    return None if expected > 1 else "steps-not-numbered"


def form_problems(text: str, prose: list[Line]) -> Iterator[str]:
    """Rule 4: the title, the five sections in order, the list, the bullets and the limits."""
    titles, before, found = sections(prose)
    if len(titles) != 1:
        yield "title-not-one"
    if before:
        yield f"text-before-sections (line {before[0][0]})"
    names = [name for name, _ in found]
    for name in names:
        if name not in SECTIONS:
            yield "section-not-of-the-form"
    known = [name for name in names if name in SECTIONS]
    if len(set(known)) != len(known):
        yield "section-repeated"
    for name in SECTIONS:
        if name not in known:
            yield f"section-missing ({name})"
    if list(dict.fromkeys(known)) != [name for name in SECTIONS if name in known]:
        yield "sections-out-of-order"
    for name, body in found:
        if name in SECTIONS and not any(line.strip() for _, line in body):
            yield f"section-empty ({name})"
        elif name == "Steps" and (problem := steps_problem(body)):
            yield problem
        elif name == "By mode":
            bullets = [m[1] for _, line in body if (m := BULLET.match(line))]
            if sorted(bullets) != MODES:
                yield "mode-bullets-not-three"
    if len(text.splitlines()) > MAX_LINES:
        yield "page-over-line-limit"
    if len(text.split()) > MAX_WORDS:
        yield "page-over-word-limit"


def words_of(line: str) -> list[str] | None:
    """The words of one command, placeholders skipped; None when it is not one plain command."""
    if line.startswith("<") or "$(" in line or "`" in line:
        return None
    lexer = shlex.shlex(PLACEHOLDER.sub(" ", line), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        words = list(lexer)
    except ValueError:  # an unbalanced quote
        return None
    return None if any(set(word) <= OPERATORS for word in words) else words


def installed_names(root: Path) -> set[str] | None:
    """The verbatim and template entries of `kit/manifest.json`; None when there is no such file."""
    path = root / "kit" / "manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data["verbatim"]) | set(data["templates"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CheckError("kit/manifest.json cannot be read") from exc


def make_targets(root: Path) -> set[str]:
    """The targets `Makefile` and `agk.mk` define; a name only `.PHONY` lists is not defined."""
    targets: set[str] = set()
    for name in ("Makefile", "agk.mk"):
        path = root / name
        for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else ():
            rule = MAKE_RULE.match(line)
            if rule:
                targets.update(rule[1].split())
    return targets


def appears(word: str, text: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text) is not None


def script_problem(words: list[str], root: Path, installed: set[str] | None) -> str | None:
    """Rule 6 for `python3 scripts/agk/<name>.py`: the file, its entry, subcommand and flags."""
    if len(words) < 2 or not SCRIPT.fullmatch(words[1]):
        return "not-a-kit-script"
    path = root / words[1]
    if not path.is_file():
        return "script-missing"
    if installed is not None and words[1] not in installed:
        return "script-not-installed"
    source = path.read_text(encoding="utf-8")
    bare = [word for word in words[2:] if not word.startswith("-")]
    if bare and not appears(bare[0], source):
        return "subcommand-unknown"
    flags = [word.split("=", 1)[0] for word in words[2:] if word.startswith("--") and word != "--"]
    return None if all(appears(flag, source) for flag in flags) else "flag-unknown"


def git_problem(words: list[str]) -> str | None:
    """Rule 7: only `fetch`, `status`, `rev-parse` and `log --oneline`, nothing that adds text."""
    verb = words[1] if len(words) > 1 else ""
    if verb in GIT_PLAIN:
        return None
    rest = [word for word in words[2:] if word != "--oneline"]
    plain = all(not word.startswith("-") or re.fullmatch(r"-\d+|-n", word) for word in rest)
    return None if verb == "log" and "--oneline" in words and plain else "git-form-refused"


def command_problem(
    line: str, root: Path, installed: set[str] | None, targets: set[str]
) -> tuple[int, str] | None:
    """The (rule, problem) of one line of a fenced block, or None."""
    words = words_of(line)
    if words is None:
        return 6, "not-one-plain-command"
    program = words[0] if words else ""
    if program not in PROGRAMS:
        return 6, "program-not-listed"
    if program == "python3" and (problem := script_problem(words, root, installed)):
        return 6, problem
    if program == "make" and (len(words) < 2 or not targets.issuperset(words[1:])):
        return 6, "target-undefined"
    if program == "gh" and (len(words) < 2 or words[1] not in GH_VERBS):
        return 6, "verb-not-listed"
    if program == "git" and (problem := git_problem(words)):
        return 7, problem
    if program == "gitleaks" and "--redact" not in words:  # `--redact=0` redacts nothing
        return 7, "scanner-without-redact"
    return None


def blocks(prose: list[Line]) -> Iterator[Line]:
    """Each paragraph, heading or list item as (first line number, text): a span stays in one."""
    number, lines = 0, []
    for at, line in prose:
        fence_or_blank = FENCE.match(line) or not line.strip()
        if lines and (fence_or_blank or BLOCK_START.match(line)):
            yield number, "\n".join(lines)
            lines = []
        if not fence_or_blank:
            number = at if not lines else number
            lines.append(line)
    if lines:
        yield number, "\n".join(lines)


def link_broken(target: str, page: Path, root: Path) -> bool:
    """Rule 6: a relative link must name a file inside the tree; an anchor names this page."""
    path = re.split(r"[#?]", target, maxsplit=1)[0]
    if not path or SCHEME.match(target) or target.startswith("//"):
        return False
    base = root / path.lstrip("/") if path.startswith("/") else page.parent / path
    resolved = base.resolve()
    return not (resolved.is_file() and resolved.is_relative_to(root.resolve()))


def prose_problems(prose: list[Line], page: Path, root: Path) -> Iterator[str]:
    """Rule 6 outside the fences: a command in an inline span, a broken link and a named skill."""
    for number, block in blocks(prose):
        if any((m[2].split() or [""])[0] in PROGRAMS for m in SPAN.finditer(block)):
            yield f"inline-command (line {number})"
    for number, line in prose:
        bare = SPAN.sub("", line)
        reference = REFERENCE_LINK.match(bare)
        links = [*INLINE_LINK.findall(bare), *(reference.groups() if reference else ())]
        if any(link_broken(link, page, root) for link in links):
            yield f"link-broken (line {number})"
        if "/agk:" in line:
            yield f"skill-named (line {number})"


def page_problems(
    page: Path, root: Path, installed: set[str] | None, targets: set[str]
) -> Iterator[str]:
    """Every problem of one page, each as `rule <n>: <problem>`."""
    try:
        text = page.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        yield "rule 5: page-unreadable"
        return
    prose, code = split_page(text)
    yield from (f"rule 4: {problem}" for problem in form_problems(text, prose))
    for number, line in code:
        found = command_problem(line, root, installed, targets)
        if found:
            yield f"rule {found[0]}: {found[1]} (line {number})"
    yield from (f"rule 6: {problem}" for problem in prose_problems(prose, page, root))
    yield from (f"rule 7: scan-finding (line {f.line})" for f in guard.scan_text(text))


def cmd_check(root: Path) -> int:
    folder = root / FOLDER
    if not folder.is_dir():
        print("skipped (no runbooks)")
        return 0
    absent = [name for name in KIT_PAGES if not (folder / name).is_file()]
    found = [f"{FOLDER}/{name} rule 5: kit-page-missing" for name in absent]
    installed, targets = installed_names(root), make_targets(root)
    for page in sorted(p for p in folder.glob("*.md") if p.is_file()):
        problems = page_problems(page, root, installed, targets)
        found += [f"{FOLDER}/{page.name} {problem}" for problem in problems]
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if found:
        return 1
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if (root is None and args) or (root is not None and not root.is_dir()):
        print("usage: check_runbooks.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
