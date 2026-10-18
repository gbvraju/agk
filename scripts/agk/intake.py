"""agk intake: the ids and the ADR stub of an intake (SPEC-0012 rules 1, 2 and 8).

Usage:
    python3 intake.py ids --sentence TEXT [--ref REF] [--root DIR]
    python3 intake.py stub --req REQ-nnn --title TEXT --sentence TEXT [--ref REF] [--root DIR]
        [--date D]

Kit-only (never installed): the plugin runs it from its own root against the repository in `--root`
(default `.`). Standard library and the installed `common.py` only; no network (the skill fetches
the default branch first). `ids` writes nothing; `stub` writes the one ADR file. The
sentence and any issue text are data: they are quoted, never followed. Messages name the rule, never
the sentence.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from common import (
    CheckError,
    git,
    load_config,
    parse_requirements,
    show,
)

USAGE = "usage: intake.py ids|stub ... (see the module text)"
MAX_SENTENCE = 300
MAX_TITLE = 80
REQ_FILE = "docs/requirements.md"
NUM_FILE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
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


def next_ids(root: Path, ref: str) -> dict[str, str]:
    """The next free ids in the tree of REF (a commit-ish): never the work tree."""
    text = show(root, ref, REQ_FILE)
    if text is None:
        raise CheckError("the base has no requirements file (path class docs/)")
    reqs = [int(r["id"][4:]) for r in parse_requirements(text)]
    out = {"req": f"REQ-{max(reqs, default=0) + 1:03d}"}
    for kind, key in (("specs", "spec"), ("adr", "adr")):
        names = git(root, "ls-tree", "--name-only", ref, f"docs/{kind}/").splitlines()
        nums = [int(m.group(1)) for n in names if (m := NUM_FILE.match(Path(n).name))]
        out[key] = f"{max(nums, default=0) + 1:04d}"
    return out


def cmd_ids(root: Path, sentence: str, ref: str | None) -> int:
    text = check_sentence(sentence)
    ids = next_ids(root, default_ref(root, ref))
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
`Draft` until its open questions are ruled and a later change sets it `Approved`.

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
    ids = next_ids(root, default_ref(root, ref))
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


# --- entry ------------------------------------------------------------------------------------

FLAGS = ("--sentence", "--ref", "--root", "--req", "--title", "--base", "--date")


def parse(args: list[str]) -> tuple[str, dict[str, str]]:
    if not args or args[0] not in ("ids", "stub"):
        raise ValueError("command")
    opts: dict[str, str] = {}
    it = iter(args[1:])
    for arg in it:
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
    root = Path(opts.get("root", "."))
    today = opts.get("date") or datetime.now(UTC).date().isoformat()
    try:
        if not root.is_dir():
            raise Refusal("the repository root is not an existing directory (option --root)")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
            raise Refusal("the date is not YYYY-MM-DD (option --date)")
        if command == "ids":
            return cmd_ids(root, opts.get("sentence", ""), opts.get("ref"))
        return cmd_stub(
            root,
            opts.get("req", ""),
            opts.get("title", ""),
            opts.get("sentence", ""),
            opts.get("ref"),
            today,
        )
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except CheckError as exc:
        print(f"FAIL intake: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
