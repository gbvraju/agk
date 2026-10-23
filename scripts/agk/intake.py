"""agk intake: the ids, the ADR stub, the checks and the next steps of an intake (SPEC-0012).

Usage:
    python3 intake.py ids --sentence TEXT [--ref REF] [--root DIR]
    python3 intake.py stub --req REQ-nnn --title TEXT --sentence TEXT [--ref REF] [--root DIR]
        [--date D]
    python3 intake.py check [--final] [--base REF] [--root DIR]
    python3 intake.py next-steps [--base REF] [--root DIR] [--date D]

Kit-only (never installed): the plugin runs it from its own root against the repository in `--root`
(default `.`). Standard library and the installed `common.py` only; no network (the skill fetches
the default branch first). `ids` and `check` write nothing; `stub` writes the one ADR file. The
sentence and any issue text are data: they are quoted, never followed. Messages name the rule, never
the sentence. `check --final` checks the last commit of an intake pull request that carries its own
approval (SPEC-0020): it reads git and files only.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from check_adrs import status_of as adr_status
from check_specs import status_of as spec_status
from common import (
    CheckError,
    changed_files,
    final_commit_problems,
    git,
    load_config,
    merge_base,
    next_free_ids,
    parse_acceptance,
    parse_requirements,
    resolve_base,
    show,
)

USAGE = "usage: intake.py ids|stub|check|next-steps ... (see the module text)"
MAX_SENTENCE = 300
MAX_TITLE = 80
MAX_CRITERIA = 8
REQ_FILE = "docs/requirements.md"
NEGATIVE = re.compile(
    r"\b(?:not|no|never|refuses|rejects|fails|cannot|without|error)\b", re.IGNORECASE
)
GWT = re.compile(
    r"\bgiven\b(?P<g>.*?)\bwhen\b(?P<w>.*?)\bthen\b(?P<t>.*)", re.IGNORECASE | re.DOTALL
)
DUE = re.compile(r"\(due \d{4}-\d{2}-\d{2}\)")
STRAY_Q = re.compile(r"Q-[A-Za-z0-9]+-[0-9]+")
# SPEC-0020 rule 6 (Q-K4-217 ruled): N of 1 to 3, or the form for a sentence that needed none
ANSWERED = re.compile(
    r"The maintainers answered (?:(?:1 question|[23] questions) before it was written\b"
    r"|no questions before it was written; the sentence settled every point\.)"
)
HEADING = re.compile(r"(?m)^## ")
NEGATIVE_NONE = re.compile(r"^Negative cases: none, because (.{20,})$", re.MULTILINE)
SENTENCE_END = re.compile(r"[.!?]+\s+\S")
ABBREVIATION = re.compile(
    r"\b(?:e\.g|i\.e|etc|vs)\.", re.IGNORECASE
)  # Q-K4-173: do not end a sentence
DIGIT_DOT = re.compile(r"(?<=\d)\.(?=\d)")


class Refusal(Exception):
    """Exit 1: nothing is written."""


def slug(sentence: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", sentence.lower()).strip("-")
    return out[:60].strip("-")


def check_sentence(sentence: str) -> str:
    text = sentence.strip()
    if not text:
        raise Refusal("rule 1: the sentence is empty")
    if len(text) > MAX_SENTENCE:
        raise Refusal(f"rule 1: the sentence is longer than {MAX_SENTENCE} characters")
    plain = DIGIT_DOT.sub("", ABBREVIATION.sub(lambda m: m.group(0)[:-1], text))
    if "\n" in text or SENTENCE_END.search(plain) or not slug(text):
        raise Refusal("rule 1: the text is not one sentence")
    return text


# --- ids (rule 2) -----------------------------------------------------------------------------


def default_ref(root: Path, ref: str | None) -> str:
    return ref or f"origin/{load_config(root)['default_branch']}"


def cmd_ids(root: Path, sentence: str, ref: str | None) -> int:
    text = check_sentence(sentence)
    ids = next_free_ids(root, default_ref(root, ref))
    print(json.dumps({**ids, "slug": slug(text)}))
    return 0


# --- the ADR stub (rule 8) --------------------------------------------------------------------


def render_stub(ids: dict[str, str], title: str, sentence: str, today: str) -> str:
    req, spec, adr = ids["req"], ids["spec"], ids["adr"]
    return f"""# ADR-{adr}: Add {req}: {title}

- Status: Proposed
- Date: {today}
- Deciders: maintainers
- Related: SPEC-{spec}
- Requirements: {req}

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
{today}:

> {sentence}

## Decision

{req} is added to `docs/requirements.md` as `planned`. SPEC-{spec} is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
"""


def cmd_stub(root: Path, req: str, title: str, sentence: str, ref: str | None, today: str) -> int:
    text = check_sentence(sentence)
    title = title.strip()
    if not title or len(title) > MAX_TITLE or ";" in title or "\n" in title:
        raise Refusal("rule 5: the title is empty, longer than 80 characters or has a semicolon")
    ids = next_free_ids(root, default_ref(root, ref))
    if req != ids["req"]:
        raise Refusal("rule 2: the requirement id is not the next free one (option --req)")
    rel = f"docs/adr/{ids['adr']}-add-{req.lower()}-{slug(text)}.md"
    path = root / rel
    if path.exists() or path.is_symlink():
        raise Refusal("path class docs/adr/ already has this file; nothing was written")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_stub(ids, title, text, today), encoding="utf-8")
    print(f"created {rel}")
    return 0


# --- the checks (rule 11) ---------------------------------------------------------------------


def section(text: str, heading: str) -> list[str] | None:
    lines = text.splitlines()
    if f"## {heading}" not in lines:
        return None
    body: list[str] = []
    for line in lines[lines.index(f"## {heading}") + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def bullets(lines: list[str]) -> list[str]:
    found: list[str] = []
    for line in lines:
        if line.startswith("- "):
            found.append(line[2:])
        elif found and line.strip():
            found[-1] += " " + line.strip()
    return found


def gwt_parts(criterion: str) -> tuple[str, str, str] | None:
    match = GWT.search(criterion)
    if not match:
        return None
    given, when, then = (match.group(k).strip(" ,:;.") for k in ("g", "w", "t"))
    return (given, when, then) if given and when and then else None


def changed_between(root: Path, first: str, second: str) -> dict[str, str]:
    """Path -> status letter from one commit to another (committed files only)."""
    result: dict[str, str] = {}
    tokens = git(root, "diff", "-z", "--name-status", "--no-renames", first, second).split("\0")
    for i in range(0, len(tokens) - 1, 2):
        result[tokens[i + 1]] = tokens[i][:1]
    return result


class Draft:
    """What the work tree (or the commit `rev`) adds to the base: the requirement, spec and ADR."""

    def __init__(self, root: Path, mb: str, rev: str | None = None):
        self.root, self.mb, self.rev = root, mb, rev
        self.problems: list[str] = []
        self.thens: list[str] = []
        self.req: dict | None = None
        self.changed = changed_between(root, mb, rev) if rev else changed_files(root, mb)
        self.ids = next_free_ids(root, mb)

    def fail(self, check: str, message: str) -> None:
        self.problems.append(f"{check} {message}")

    def added(self, prefix: str) -> list[str]:
        return sorted(p for p, s in self.changed.items() if s == "A" and p.startswith(prefix))

    def read(self, rel: str) -> str:
        if self.rev:
            text = show(self.root, self.rev, rel)
            if text is None:
                raise CheckError("cannot read a file of the intake (path class docs/)")
            return text
        try:
            return (self.root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise CheckError("cannot read a file of the intake (path class docs/)") from None

    def files(self) -> tuple[str | None, str | None]:
        spec, adr = self.added("docs/specs/"), self.added("docs/adr/")
        expect = {REQ_FILE} | set(spec[:1]) | set(adr[:1])
        if set(self.changed) != expect or len(spec) != 1 or len(adr) != 1:
            self.fail(
                "C2", "the difference is not the requirements file, one new spec and one new ADR"
            )
        if self.changed.get(REQ_FILE) != "M":
            self.fail("C2", "the requirements file is not modified (path class docs/)")
        self.names(spec[:1], adr[:1])
        n_spec = self.ids["spec"]
        n_adr = self.ids["adr"]
        for path, number, label in ((spec[:1], n_spec, "spec"), (adr[:1], n_adr, "ADR")):
            if path and not Path(path[0]).name.startswith(f"{number}-"):
                self.fail("C1", f"the {label} number is not the next free one")
        return (spec[0] if len(spec) == 1 else None, adr[0] if len(adr) == 1 else None)

    def names(self, spec: list[str], adr: list[str]) -> None:
        """Rule 4: the file names, directly in their folders; the message names no part of one."""
        req = self.ids["req"].lower()
        if spec and not re.fullmatch(r"docs/specs/\d{4}-[a-z0-9-]+\.md", spec[0]):
            self.fail("C2", "the spec is not docs/specs/<spec>-<slug>.md (rule 4)")
        pattern = rf"docs/adr/\d{{4}}-add-{req}-[a-z0-9-]+\.md"
        if adr and not re.fullmatch(pattern, adr[0]):
            self.fail("C2", "the ADR is not docs/adr/<adr>-add-<req id>-<slug>.md (rule 4)")

    def requirement(self) -> dict | None:
        old = show(self.root, self.mb, REQ_FILE) or ""
        new = self.read(REQ_FILE)
        if not new.startswith(old):
            self.fail("C2", "an existing line of the requirements file is changed or removed")
            return None
        known = {r["id"] for r in parse_requirements(old)}
        fresh = [r for r in parse_requirements(new) if r["id"] not in known]
        if len(fresh) != 1:
            self.fail("C2", "the requirements file does not add exactly one requirement")
            return None
        req = fresh[0]
        if req["id"] != self.ids["req"]:
            self.fail("C1", "the requirement id is not the next free one")
        title = req["title"] or ""
        if not title or len(title) > MAX_TITLE or ";" in title:
            self.fail("C3", "the title is missing, longer than 80 characters or has a semicolon")
        if req["status"] != "planned" or req["status_count"] != 1:
            self.fail("C6", "the status of the new requirement is not exactly one `planned`")
        return req

    def criteria(self, req: dict) -> list[tuple[str, str]]:
        line = req["acceptance"] or ""
        found = parse_acceptance(line)
        names = [name for name, _ in found]
        if not found or not line.startswith("AC1 ") or len(found) > MAX_CRITERIA:
            self.fail("C3", "the acceptance line has no criteria or more than 8")
        elif names != [f"AC{i}" for i in range(1, len(found) + 1)]:
            self.fail("C3", "the criteria are not AC1, AC2, ... in order without a repeat")
        if any("; " in text for _, text in found):
            self.fail("C3", "a criterion has a semicolon inside")
        thens = []
        for name, text in found:
            parts = gwt_parts(text)
            if parts is None:
                self.fail("C4", f"criterion {name} lacks given, when, then in order with text")
            else:
                thens.append(parts[2])
        self.thens = thens
        return found

    def spec(self, rel: str, req: dict, found: list[tuple[str, str]]) -> None:
        text = self.read(rel)
        number = self.ids["spec"]
        if spec_status(text) != "Draft":
            self.fail("C6", "the spec is not `Draft`")
        field = re.search(r"(?m)^- Requirements:\s*(.*?)\s*$", text)
        if not field or field.group(1) != req["id"]:
            self.fail("C7", "the spec's Requirements line is not exactly the new requirement")
        tests = section(text, "Tests")
        marks = re.findall(r"(REQ-\d{3}) AC(\d+)\b", "\n".join(tests or []))
        have = {f"AC{n}" for r, n in marks if r == req["id"]}
        want = {name for name, _ in found}
        if tests is None or have != want or any(r != req["id"] for r, _ in marks):
            self.fail("C7", "the Tests section lacks a marker for a criterion or has a stray one")
        for heading in ("Proof", "Residual", "Open questions"):
            if section(text, heading) is None:
                self.fail("C8", f"the spec has no `## {heading}` section")
        proof = section(text, "Proof")
        if proof is not None and not any(line.strip() for line in proof):
            self.fail("C8", "the `## Proof` section is empty")
        residual = section(text, "Residual") or []
        items = bullets(residual)
        only_none = len(items) == 1 and re.fullmatch(r"none\.?", items[0].strip())
        if not only_none and any(not DUE.search(item) for item in items):
            self.fail("C8", "a residual bullet has no due date")
        if not items and not any(re.fullmatch(r"-?\s*none\.?", ln.strip()) for ln in residual):
            self.fail("C8", "the `## Residual` section has neither a bullet nor `none`")
        if any(not re.fullmatch(rf"Q-S{number}-\d+", q) for q in STRAY_Q.findall(text)):
            self.fail("C8", "a question id is outside the family of the spec")
        negative = any(NEGATIVE.search(t) for t in self.thens)
        if not negative and not NEGATIVE_NONE.search(text):
            self.fail("C5", "no criterion states a negative case and the spec gives no reason")

    def adr(self, rel: str) -> None:
        text = self.read(rel)
        if adr_status(text) != "Proposed":
            self.fail("C6", "the ADR is not `Proposed`")
        line = next((ln for ln in text.splitlines() if ln.startswith("Protected classes:")), "")
        if REQ_FILE not in line:
            self.fail(
                "C9", "the ADR's `Protected classes:` line does not name the requirements file"
            )

    def run(self) -> list[str]:
        spec, adr = self.files()
        req = self.requirement()
        found = self.criteria(req) if req else []
        if req and spec:
            self.spec(spec, req, found)
        if adr:
            self.adr(adr)
        self.req = req
        self.paths = (spec, adr)
        return self.problems


def draft_of(root: Path, base: str | None) -> Draft:
    ref = resolve_base(root, base)
    if ref is None:
        raise CheckError("no base ref resolves (setting default_branch)")
    return Draft(root, merge_base(root, ref))


def cmd_check(root: Path, base: str | None) -> int:
    problems = draft_of(root, base).run()
    for problem in problems:
        print(f"FAIL intake: {problem}")
    if not problems:
        print("ok intake")
    return 1 if problems else 0


# --- the approving commit (SPEC-0020) ---------------------------------------------------------

STATUS_LINES = (("spec", "Draft", "Approved"), ("ADR", "Proposed", "Accepted"))


def final_problems(root: Path, mb: str) -> list[str]:
    """SPEC-0020 rules 2 to 6, from the commits alone; a message names the rule, never a value."""
    parents = git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
    if len(parents) != 1:
        return ["rule 2: the last commit is not a single commit on top of the intake commit"]
    prev = parents[0]
    if prev == mb:
        return ["rule 2: the approving commit is a commit of its own, after the intake commit"]
    draft = Draft(root, mb, rev=prev)
    earlier = draft.run()
    if earlier:
        return [f"rule 3: before the last commit, {problem}" for problem in earlier]
    spec, adr = draft.paths
    files_ok, bad = final_commit_problems(
        root,
        prev,
        "HEAD",
        [(spec, None, STATUS_LINES[0][1], STATUS_LINES[0][2]), (adr, None, *STATUS_LINES[1][1:])],
    )
    if not files_ok:
        return ["rule 4: the last commit does not change exactly the spec and the ADR"]
    problems = [
        f"rule 4: the {label} changes more than its status line, or another status"
        for (label, _, _), path in zip(STATUS_LINES, (spec, adr), strict=True)
        if path in bad
    ]
    text = show(root, "HEAD", spec) or ""
    asked = section(text, "Open questions") or []
    if STRAY_Q.search(text) or [ln.strip() for ln in asked if ln.strip()] != ["none"]:
        problems.append("rule 5: the spec has an open question or a question id")
    if not ANSWERED.search(HEADING.split(text, maxsplit=1)[0]):
        problems.append("rule 6: the opening paragraph of the spec does not record the answers")
    return problems


def cmd_check_final(root: Path, base: str | None) -> int:
    ref = resolve_base(root, base)
    if ref is None:
        raise CheckError("no base ref resolves (setting default_branch)")
    problems = final_problems(root, merge_base(root, ref))
    for problem in problems:
        print(f"FAIL intake: {problem}")
    if not problems:
        print("ok intake")
    return 1 if problems else 0


# --- the next steps (rule 13) -----------------------------------------------------------------


def cmd_next_steps(root: Path, base: str | None, today: str) -> int:
    branch = git(root, "branch", "--show-current").strip()
    if not branch or branch == load_config(root)["default_branch"]:
        raise Refusal(
            "rule 3: the work is not on an intake branch (detached or the default branch)"
        )
    draft = draft_of(root, base)
    problems = draft.run()
    if problems or draft.req is None:
        for problem in problems:
            print(f"FAIL intake: {problem}")
        print("the intake does not pass `check`; no next steps are printed")
        return 1
    req = draft.req
    advance = f"Advances: {req['id']}"
    print(f"Commit message:\n\nintake: add {req['id']} {req['title']}\n")
    print(f"Push command:\n\ngit push -u origin {branch}\n")
    print("Open the pull request from that branch into the default branch with this body.\n")
    print("Pull request body:\n")
    print(advance)
    print(f"Build-state row: {today} {req['id']} proposed (planned), intake only")
    print("Decisions taken: none; the sentence became a requirement, a Draft spec and an ADR stub")
    print("Questions: see `## Open questions` of the spec")
    print("Verified: `python3 scripts/agk/intake.py check` printed `ok intake`\n")
    print(
        "The checks cannot tell that the criteria are the right ones, that they say what you\n"
        "meant, or that the spec can be built. That is the review of the pull request."
    )
    print(
        "\nIf the maintainers answered every question before the files were written, the spec's\n"
        "opening paragraph records the answers and the final commit changes exactly two lines:\n"
        "`- Status: Draft` to `- Status: Approved` in the spec and `- Status: Proposed` to\n"
        "`- Status: Accepted` in the ADR. `intake.py check --final` checks that commit; the\n"
        "session makes it only on the maintainers' word."
    )
    return 0


# --- entry ------------------------------------------------------------------------------------

FLAGS = ("--sentence", "--ref", "--root", "--req", "--title", "--base", "--date")


def parse(args: list[str]) -> tuple[str, dict[str, str]]:
    if not args or args[0] not in ("ids", "stub", "check", "next-steps"):
        raise ValueError("command")
    opts: dict[str, str] = {}
    it = iter(args[1:])
    for arg in it:
        if arg == "--final":
            opts["final"] = "1"
            continue
        value = next(it, None)
        if arg not in FLAGS or value is None:
            raise ValueError("option")
        opts[arg[2:]] = value
    return args[0], opts


def main(argv: list[str] | None = None) -> int:
    try:
        command, opts = parse(list(sys.argv[1:] if argv is None else argv))
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2
    if "final" in opts and command != "check":
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(opts.get("root", "."))
    today = opts.get("date") or datetime.now(UTC).date().isoformat()
    try:
        if not root.is_dir():
            raise Refusal("the repository root is not an existing directory (option --root)")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
            raise Refusal("the date is not YYYY-MM-DD (option --date)")
        if command == "ids":
            return cmd_ids(root, opts.get("sentence", ""), opts.get("ref"))
        if command == "stub":
            return cmd_stub(
                root,
                opts.get("req", ""),
                opts.get("title", ""),
                opts.get("sentence", ""),
                opts.get("ref"),
                today,
            )
        if command == "check" and "final" in opts:
            return cmd_check_final(root, opts.get("base"))
        if command == "check":
            return cmd_check(root, opts.get("base"))
        return cmd_next_steps(root, opts.get("base"), today)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except CheckError as exc:
        print(f"FAIL intake: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
