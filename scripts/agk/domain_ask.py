# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The domain proposed from signals and confirmed with one yes (SPEC-0074 rule 5; REQ-081 AC3;
brief #1937, ADR-0806).

Usage: python3 scripts/agk/steward_owner.py domain --propose
       python3 scripts/agk/steward_owner.py domain --yes --said FILE --at TIME [--by LOGIN]

`propose` counts each pack's signals: the repository's (`front_door.py detect`'s `domain` fact)
and the pack `words` of `config/domain-signals.toml` found in the recorded vision and discovery
documents, never chat text (Q-D74C-2). It asks one plain question with no kit term, saved as the
one open ask: one candidate, a yes or not yet; several, one choice of the three with most signals
and "none of these", the first recommended. A declared `[domain] packs` proposes nothing. `yes`
takes the person's recorded reply to that ask, as `work-type --yes` does: "not yet" or "none of
these" records a `Decision:` and writes nothing; a yes writes `[domain] packs` and a Proposed
project ADR on the branch `steward/domain` in solo mode with one person, and prints only
otherwise. A plain yes is refused in team mode, naming `review_mode`. `agk.toml` is written only
here, from a recorded ask, after a reply with a question, a condition or a no is refused; a
number is a choice only as the whole reply. A session whose `AGK_ROLE` is not `steward`, or is
unset, is refused. Reads files
and local git only: no network, no model.
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import front_door  # noqa: E402
import steward_owner as owner  # noqa: E402
from common import CheckError  # noqa: E402

from config import domain_settings  # noqa: E402

KIT = Path(__file__).resolve().parents[2]
RULE = "SPEC-0074 rule 5"
BRANCH = "steward/domain"
FORM = "domain"
SOURCES = ("constitution/vision.md", "docs/discovery")
NONE_OF_THESE = re.compile(r"none of these[.!]?", re.IGNORECASE)
TABLE = re.compile(r"^\[domain\][ \t]*(?:#.*)?$", re.M)
PACKS = re.compile(r"^packs[ \t]*=")
CHOICE = re.compile(r"\(?([1-9])\)?[.!]?")
NEGATIVE = re.compile(r"\b(?:no|nope|never|don't|dont|do not|stop|wait)\b", re.IGNORECASE)


def _role() -> str | None:
    if os.environ.get("AGK_ROLE") != "steward":  # an unset role is refused too (fix list item 3)
        return "refused: only the steward asks for the domain (setting: AGK_ROLE)"
    return None


def _texts(root: Path) -> list[str]:
    paths = [root / SOURCES[0], *sorted((root / SOURCES[1]).glob("*.md"))]
    out = []
    for path in paths:
        try:
            out.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return out


def signals(root: Path, kit: Path = KIT) -> dict[str, list[str]]:
    """Each pack's signals: the repository's files and dependencies, then the recorded words."""
    found: dict[str, list[str]] = {}
    fact = front_door.detect_facts(root, kit).get("domain") or {"candidates": []}
    for hit in fact["candidates"]:
        found.setdefault(hit["name"], []).append(f"{hit['signal']} {hit['file']}")
    texts = _texts(root)
    for row in front_door.domain_rows(kit) or []:
        for word in row["words"]:
            pattern = re.compile(front_door.WORD.format(re.escape(word)), re.IGNORECASE)
            if any(pattern.search(text) for text in texts):
                found.setdefault(row["name"], []).append(f"word {word}")
    return found


def offered(counts: dict[str, int]) -> list[str]:
    """At most three packs, the most signals first, ties by name."""
    return sorted(counts, key=lambda name: (-counts[name], name))[:3]


def _title(root: Path, name: str) -> str:
    import check_domains

    path = check_domains.pack_path(root, name)
    title = str((check_domains.load(path) or {}).get("title", name)) if path else name
    return title[:1].lower() + title[1:].rstrip(".")


def question(root: Path, names: list[str]) -> str:
    if len(names) == 1:
        return (
            f"This looks like {_title(root, names[0])}. Shall I use what is known about that"
            " business when I ask my questions? Yes or not yet; I recommend yes."
        )
    choices = "; ".join(f"({n}) {_title(root, name)}" for n, name in enumerate(names, 1))
    return (
        f"This looks like one of these businesses: {choices}; or none of these. Which one shall"
        " I use when I ask my questions? I recommend the first."
    )


def propose(root: Path, now: datetime, kit: Path = KIT) -> tuple[int, list[str]]:
    """One plain question when signals name a pack and `[domain] packs` lists none."""
    if refusal := _role():
        return 2, [refusal]
    declared = domain_settings(root)["packs"]
    found = signals(root, kit)
    if declared:
        if set(found) - set(declared):
            return 0, ["domain: declared; it differs from the signals and the declared one is"
                       " kept (setting: domain.packs)"]  # fmt: skip
        return 0, ["domain: declared; nothing to propose"]
    if not found:
        return 0, ["domain: none; nothing to propose"]
    names = offered({name: len(set(hits)) for name, hits in found.items()})
    sentence = question(root, names)
    if problem := owner.question_problem(sentence):
        return 2, [problem]
    if (sid := owner.steward_session(root)) is None:
        return 2, [
            "refused: no steward session is read (setting: AGK_SESSION, or steward.py start)"
        ]
    asks = owner.load_asks(root)
    for old in asks:  # one open ask stands
        old["open"] = False
    asks.append({"id": FORM, "form": FORM, "packs": names, "target": "agk.toml", "number": None,
                 "head": None, "link": None, "line": "", "question": sentence,
                 "signals": {n: found[n] for n in names}, "at": owner.steward.stamp(now),
                 "open": True, "session": sid})  # fmt: skip
    owner.save_asks(root, asks)
    return 0, [f"ask the person: {sentence}"]


def chosen(words: str, names: list[str]) -> list[str]:
    """The offered packs the words name, in the offer's order: by name anywhere; by number only
    when the whole reply is one number of the offer (fix list item 2)."""
    if found := CHOICE.fullmatch(words.strip()):
        number = int(found[1])
        return names[number - 1 : number] if 1 <= number <= len(names) else []
    said = set(re.findall(r"[a-z0-9-]+", words.lower()))
    return [n for n in names if n in said]


def with_packs(text: str, names: list[str]) -> str:
    line = "packs = [" + ", ".join(f'"{n}"' for n in names) + "]"
    found = TABLE.search(text) if "domain" in tomllib.loads(text) else None
    if found is None:
        return f"{text.rstrip(chr(10))}\n\n[domain]\n{line}\n"
    after = re.search(r"^\[", text[found.end() :], re.M)
    stop = found.end() + (after.start() if after else len(text) - found.end())
    lines = text[found.end() : stop].split("\n")
    at = next((n for n, x in enumerate(lines) if PACKS.match(x)), None)
    if at is None:
        lines.insert(1, line)
    else:  # the whole value, over as many lines as its brackets take (fix list item 4)
        last, depth = at, 0
        for last in range(at, len(lines)):
            depth += lines[last].split("#")[0].count("[") - lines[last].split("#")[0].count("]")
            if depth <= 0:
                break
        lines[at : last + 1] = [line]
    out = text[: found.end()] + "\n".join(lines) + text[stop:]
    if tomllib.loads(out).get("domain", {}).get("packs") != names:
        raise CheckError(f"the [domain] table cannot be rewritten (setting: domain.packs, {RULE})")
    return out


def adr(root: Path, ask: dict, names: list[str], words: str, at: str) -> str:
    number = owner.next_adr(root)
    rel = f"docs/adr/{number:04d}-domain.md"
    listed = ", ".join(f"`{n}`" for n in names)
    text = "\n".join([
        f"# ADR-{number:04d}: The project's domain packs are {', '.join(names)}", "",
        "- Status: Proposed", f"- Date: {datetime.now(UTC):%Y-%m-%d}", "- Deciders: the owner",
        "- Related: agk.toml", f"- Requirements: {owner.ADR_REQUIREMENT}", "",
        f"Protected classes: {owner.record_classes(root, rel)}", "",
        "## Context", "",
        f"The repository and the recorded vision and discovery suggest the domain ({RULE}), and"
        " `agk.toml` listed no `[domain] packs`.", "",
        "## Decision", "",
        f"`agk.toml` lists `[domain] packs` {listed}, so what is known about that business joins"
        " the grill's questions.", "",
        f'Asked ({ask["at"]}): "{ask["question"]}"', f'Owner said ({at}): "{words}"', "",
        "## Consequences", "",
        "The owner's merge of this pull request approves it; no agent merges it.", "",
        *owner.residual(),
    ])  # fmt: skip
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")
    return rel


def _closed(root: Path, asks: list[dict], ask: dict, words: str, at: str) -> tuple[int, list[str]]:
    ask["open"] = False
    owner.save_asks(root, asks)
    code, said = owner.steward.record(
        root,
        "Decision",
        f'domain: not yet, the person said "{words}" at {at}',
        owner.steward.gh_api,
    )
    return code or 1, said if code else ["not yet: recorded, nothing written"]  # as work-type


def yes(
    root: Path, words_file: Path, at: str, by: str | None, now: datetime
) -> tuple[int, list[str]]:
    """The person's recorded reply to the open domain ask; never commits or pushes."""
    import reviewers
    import steward_voice
    from guard import scan_text

    from config import guard_patterns, load_config

    if refusal := _role():
        return 2, [refusal]
    if not owner.TIME.fullmatch(at):
        return 2, [f"refused: the reply time is UTC, YYYY-MM-DDTHH:MMZ (setting: --at, {RULE})"]
    team = owner.review_mode(root) == "team"
    code, refusal, words = owner.yes_of(root, words_file, by, team=True)
    if refusal:
        return code, [refusal]
    asks = owner.load_asks(root)
    open_asks = [x for x in asks if x.get("open")]
    if not open_asks or open_asks[-1].get("form") != FORM:
        return 2, [f"refused: no domain proposal is the latest open ask; propose again ({RULE})"]
    ask = open_asks[-1]
    if owner.steward_session(root) != ask.get("session"):
        return 2, [f"refused: the ask was made in another session; ask again ({RULE})"]
    asked = datetime.strptime(ask["at"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
    if at[:16] + "Z" < ask["at"] or at[:16] + "Z" > owner.steward.stamp(now):
        return 2, ["refused: the reply is older than the ask or in the future (setting: --at)"]
    if now - asked > owner.age_limit(root):
        return 2, ["refused: the ask is too old; ask again (setting: [flow] owner_wait_minutes)"]
    if len(words.splitlines()) != 1 or scan_text(words, guard_patterns(root)):
        return 2, ["refused: the words are one line the data guard passes (setting: [guard])"]
    if owner.NOT_YET.fullmatch(words) or NONE_OF_THESE.fullmatch(words):
        return _closed(root, asks, ask, words, at)
    if owner.BACKSTOP.search(words) or NEGATIVE.search(words):  # before any choice (item 1)
        return 2, ["refused: a question, a condition or a no is not a yes (SPEC-0062 rule 14)"]
    names = chosen(words, ask["packs"])
    plain = not names and steward_voice.is_yes(words)
    if plain and team:
        return 2, ["refused: a plain yes never holds in team mode (setting: review_mode)"]
    if plain:
        names = ask["packs"][:1]
    if not names:
        return 1, ["not a yes: nothing written; ask again in other words (SPEC-0062 rule 14)"]
    if domain_settings(root)["packs"]:
        return 2, [f"refused: the domain changed since the ask; propose again ({RULE})"]
    change = [
        "the one change in agk.toml:",
        "[domain]",
        with_packs("", names).strip().split("\n")[-1],
    ]
    personal = owner.personal_table(root) is not None
    if personal or team or reviewers.solo_person(root) is None:
        why = "your own change" if personal else "a team chooses by its own pull request"
        return 0, [f"printed only ({why}; setting: review_mode):", *change,
                   "with an ADR in the same pull request that names agk.toml"]  # fmt: skip
    branch = load_config(root)["default_branch"]
    base = f"origin/{branch}"
    if owner.git_out(root, "rev-parse", "--verify", "--quiet", base).returncode:
        base = branch
    if owner.git_out(root, "status", "--porcelain").stdout.strip():
        return 2, [
            "refused: the work tree has changes; nothing written (path class: the work tree)"
        ]
    if owner.git_out(root, "rev-parse", "--verify", "--quiet", BRANCH).returncode == 0:
        return 2, [f"refused: the branch {BRANCH} already exists; nothing written"]
    toml = root / "agk.toml"
    rewritten = with_packs(toml.read_text(encoding="utf-8"), names)  # refused before any write
    code, said = owner.steward.record(  # first: a memory that cannot be written writes nothing
        root, "Decision", f'domain: yes, the person said "{words}" at {at}', owner.steward.gh_api
    )
    if code:
        return code, said
    ask["open"] = False
    owner.save_asks(root, asks)
    if owner.git_out(root, "switch", "-q", "-c", BRANCH, base).returncode:
        return 2, [f"refused: the branch {BRANCH} cannot be made; nothing written"]
    toml.write_text(rewritten, encoding="utf-8")
    rel = adr(root, ask, names, words, at)
    return 0, [
        f"wrote agk.toml and {rel} (Proposed) on {BRANCH}; nothing committed or pushed",
        "run, then open the pull request; your merge is the approval:",
        f"git add agk.toml {rel}",
        f'git commit -m "The project\'s domain packs (ADR-{rel[9:13]})"',
        f"git push -u origin {BRANCH}",
    ]
