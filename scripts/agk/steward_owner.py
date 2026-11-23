# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The steward's owner question, its relay, its parking and its start of the conductor (SPEC-0059
rules 2, 5, 10 and 14; brief #1322, ADR-0559).

Usage: python3 scripts/agk/steward_owner.py ask --qid Q --on N --file FILE
       python3 scripts/agk/steward_owner.py ask --target pr:N --qid Q --file FILE --line FILE
       python3 scripts/agk/steward_owner.py approve --ask Q --said FILE --at TIME [--by LOGIN]
       python3 scripts/agk/steward_owner.py relay --qid Q --on N --answer TEXT --said FILE --at TIME
                                           [--conductor ID]
       python3 scripts/agk/steward_owner.py park --pr N [--conductor ID]
       python3 scripts/agk/steward_owner.py ready --plan FILE --trace FILE --session ID [--start]
       python3 scripts/agk/steward_owner.py defect --title TEXT --file FILE [--refusals N] [--post]
       python3 scripts/agk/steward_owner.py defects
       python3 scripts/agk/steward_owner.py reads [--session ID] [--refused]
       python3 scripts/agk/steward_owner.py standard [--playbook SLUG]
       python3 scripts/agk/steward_owner.py confirm --said FILE --at TIME [--by LOGIN]
       python3 scripts/agk/steward_owner.py research --said FILE --at TIME --describe TEXT
       python3 scripts/agk/steward_owner.py draft --slug SLUG [--layers FILE]
       python3 scripts/agk/steward_owner.py fix-brief --brief N --file FILE --seen UPDATED_AT
       python3 scripts/agk/steward_owner.py file-brief --file FILE --title TEXT
                                           [--said FILE --at TIME [--by LOGIN] [--name NAME]]
       python3 scripts/agk/steward_owner.py work-type --propose
       python3 scripts/agk/steward_owner.py work-type --yes --said FILE --at TIME [--by LOGIN]

`ask` takes one plain business sentence (FILE): one line, a question with its choices and `I
recommend`, and no kit term (a file name, label, rule number, id or command); it records it as an
`Owner question:` memory entry, prints it for the chat and posts `Question: <Q> for the
maintainers: <the sentence>` on #N. `relay` posts the owner's reply as three lines,
`Maintainer answer: <Q> <answer>`, `Owner said (<UTC time>): "<the words of FILE, verbatim>"` and
`Who: ProductOwner`, and refuses a body without that second line or with a malformed one; it then
removes the `agk:parked` that the owner wait set on #N and tells the conductor
`parked #<n> answered <Q>`. `park` is the steward's pass of the bounded owner wait on one pull
request (`session.owner_step`): it parks a wait that has passed and unparks an answered one, with
the same tell. In personal mode (a `[personal]` table) every text is printed, nothing is posted
and nothing is parked. `ready` starts the conductor only when the plan passes every check: the
trace of `check_plan.py --trace` ends `ok plan`, the plan of `session.py plan --json` lists no
malformed brief, `docs/plan/scope-lock.md` exists, and no open owner question of the memory blocks
the first milestone (one that names `M1` or names no milestone); else it prints `not ready: <check>`
for each and starts nothing (exit 1). A refusal names the rule or setting, never the value (exit 2).

Brief #1387 (SPEC-0064 rules 6 and 14, ADR-0585): with `auto_start` and `launch_adapter` set,
`ready --start` starts nothing itself and prints that the supervisor's next pass
(`conductor.py watchdog --pass`) starts the conductor; without them it prints the conductor's
prompt as before. A steward the supervisor started (`AGK_STEWARD_START=conductor`) relays nothing:
`relay` refuses (exit 2).

Brief #1411 (ADR-0594): `defect` drafts one kit-defect report: the title, the kit version
(`version` of `agk.toml`), the operating system and shell, the reason codes and the newest N (5)
redacted lines of the refusal log (`guard_logs`, ADR-0593) and what should happen instead (FILE).
The outbound data guard (`steward_outbound.check`) checks the title and body first, fail closed
(exit 2). It prints the draft; `--post` opens it as one issue in the project's own repository
labelled `agk-kit-defect`, never `agk-brief`, so the plan never offers it; in personal mode nothing
is posted. `defects` lists the open kit defects, one line each, or `kit defects: none open`.
`reads` checks one read, `gh api rate_limit`: `reads: ok`, or once per session one line naming the
setting or permission mode that refuses it and the one step that restores it (exit 1); `--refused`
says the runtime itself refused the steward's own `gh api` call, and names the permission entry of
`.claude/settings*.json` that explains it, else the session's permission mode `(verify)`.

Brief #1601 (SPEC-0072 rule 8, ADR-0681): `standard` prints the composed standard of the declared
work type (or `--playbook`): one plain screen in solo mode, the full list (layers, directions,
packs, every gate with its step or reason) in team mode, or, with neither, the work-type question.
`confirm` records one `Setup: standard: confirmed because the person said "<words>" at <time>`
only on an explicit yes (in team mode `--by` a spec approver), else `not confirmed: nothing
applied` (exit 1); `ready` is `not ready` without it while a work type is declared. `research`
records the web-research permission and, only on a yes, prints `search: <TEXT>` for a generic
description (exit 2 for anything else). `draft` writes the project playbook (`front_door.py
derive-write`) and its Proposed ADR, never `[delivery] work_type`.

Brief #1690 (SPEC-0062 rules 13, 14 and 16, ADR-0703): `ask --target pr:N --line FILE` pins the
pull request's full head and the exact line to write as the session's one open ask; `approve`
takes the person's yes to that latest open ask, re-reads the head, and posts a `Maintainer answer:`
form with `Owner said`, `Asked` and `Who: ProductOwner`, or prints an `Approve:` or `Confirmed:`
body ready to paste; anything else posts nothing.

Brief #1715 (SPEC-0059 rule 6, ADR-0714): with `[steward] fix_briefs = true` and solo mode with
one person listed, `fix-brief` replaces an open, untaken `agk-brief` issue's body (never an
`Intake:`) when every changed line is an `Adds:`, `Touches:`, `Reserved:`, `Depends-on:` or
`Evidence` line, its `updated_at` still equals `--seen` and the new body passes `check_brief.py
--root` and the neutrality lists: it posts the old body as one `Body fixed:` comment first, then
the body, records one note and prints the new `seen:`; anything else prints `Proposed body:` and
writes nothing (exit 1). `file-brief` opens one issue labelled `agk-brief` when the draft passes
the same checks and its `Priority:` is at or below `[steward] auto_file`, or on the person's
explicit yes (`--said`, `--at`; in team mode `--by` a spec approver), no older than four times
`[flow] owner_wait_minutes` (24 hours unset), quoted in an `Owner said` line; with `--name`, also
`Yes, file the <NAME> brief` (brief #1753). It files nothing when an open brief has the same title
or body. In personal mode both print and write nothing; a steward the supervisor started runs
neither (exit 2).

Brief #1757 (ADR-0735, amendment 218 to SPEC-0038 rule 5): with no `[delivery] work_type` and one
work type other than `pilot` named by the discovery documents, `work-type --propose` records one
plain owner question as the session's open ask; two named types give a question naming both and
no proposal. `work-type --yes` takes the person's plain yes to that ask by the `approve` rules (no
condition, not older than the ask, no older than four times `[flow] owner_wait_minutes`) and, in
solo mode with one person listed, writes on a new branch from the default branch the `[delivery]`
line and a Proposed ADR quoting the words, then prints the commit and push commands: it never
commits or pushes, and the owner's merge approves it. In team mode, in personal mode or for one
listed person short it prints the change only; `not yet` is recorded and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess  # nosec B404 - one fixed argument list (`gh api rate_limit`), no shell
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard_logs  # noqa: E402
import launch  # noqa: E402
import session  # noqa: E402
import steward  # noqa: E402
from common import (  # noqa: E402
    OUTSIDE_PROJECT,
    REMOTE_RUNTIME,
    CheckError,
    agent_apps,
    personal_table,
    repo_root,
    review_mode,
    utf8_output,
)
from session_plan import KIT_DEFECT_LABEL  # noqa: E402

RULE = "SPEC-0059 rule 5"
QID = re.compile(r"Q-\d+-\w+")
KIT_TERMS = re.compile(
    r"`|\bagk[:-]\w|\b[\w./-]+\.(?:py|md|toml|json|ya?ml|txt|sh)\b|\bscripts?/|(?<!\w)--?\w"
    r"|\b(?:rule|principle|item)\s+\d|\b(?:SPEC|ADR|REQ|Q)-\d|#\d"
    r"|\b(?:python3?|gh|git|make|pytest|claude)\b"
    r"|\b(?:pull request|brief|verdict|conductor|builder|commit|branch|label)s?\b",
    re.IGNORECASE,
)
OWNER_SAID = re.compile(r'Owner said \(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z\): ".+"')
ANSWER_FIRST = re.compile(r"Maintainer answer: Q-\d+-\w+ \S.*")
OWNER_WHO = "Who: ProductOwner"
STEWARD_WHO = "Who: AGK steward"
MILESTONE = re.compile(r"\bM(\d+)\b")


def question_problem(text: str) -> str | None:
    """Why TEXT is not one plain owner question, naming the rule, never the text."""
    if not text.strip() or len(text.strip().splitlines()) != 1 or len(text) > 500:
        return f"refused: the owner question is one line of at most 500 characters ({RULE})"
    if "?" not in text or "I recommend" not in text:
        return f"refused: the owner question gives its choices and a recommendation ({RULE})"
    if KIT_TERMS.search(text):
        return f"refused: the owner question holds a kit term ({RULE})"
    return None


def relay_body(qid: str, answer: str, words: str, at: str) -> str:
    return f'Maintainer answer: {qid} {answer}\nOwner said ({at}): "{words}"\n{OWNER_WHO}\n'


def relay_problem(body: str) -> str | None:
    """A relayed owner answer: rule 5's first line, the `Owner said` quote, `Who: ProductOwner`."""
    lines = body.strip().splitlines()
    if not lines or not ANSWER_FIRST.fullmatch(lines[0]):
        return f"refused: the first line is `Maintainer answer: Q-<id> <answer>` ({RULE})"
    if len(lines) < 2 or not OWNER_SAID.fullmatch(lines[1]):
        return f"refused: the second line is the owner's quote with its UTC time ({RULE})"
    if lines[-1] != OWNER_WHO:
        return f"refused: the last line is `{OWNER_WHO}` ({RULE})"
    return None


def post(repo: str, number: int, body: str) -> None:
    endpoint = f"repos/{repo}/issues/{number}/comments"
    if session.gh(endpoint, "-f", f"body={body}", method="POST") is None:
        raise CheckError(f"the comment on #{number} could not be posted")


def tell(root: Path, conductor: str | None, number: int, qid: str) -> list[str]:
    if not conductor:
        return [f"tell: no conductor named; it resumes #{number} from its sweep"]
    session.tell(root, conductor, f"parked #{number} answered {qid}")
    return []


def ask(root: Path, qid: str, number: int, text: str) -> tuple[int, list[str]]:
    sentence = text.strip()
    if problem := question_problem(sentence) or (None if QID.fullmatch(qid) else "refused: Q id"):
        return 2, [problem]
    line = f"Question: {qid} for the maintainers: {sentence}"
    code, said = steward.record(root, "Owner question", f"{qid} {sentence}", steward.gh_api)
    if code:
        return code, said
    if personal_table(root) is not None:
        return 0, [f"ask the owner: {sentence}", f"post on #{number}: {line}", *said]
    post(session.repo_name(root), number, f"{line}\n\n{STEWARD_WHO}")
    return 0, [f"ask the owner: {sentence}", f"asked on #{number}", *said]


def unpark(root: Path, repo: str, number: int, qid: str, conductor: str | None) -> list[str]:
    """Remove the owner wait's `agk:parked` on #N when the wait set it and the relayed answer
    closed the item it parked for, read fresh (brief #1534 answer 3), and tell the conductor."""
    pull = session.gh(f"repos/{repo}/pulls/{number}")
    if not isinstance(pull, dict):
        return []  # a brief, or unreadable: the conductor's sweep unparks it
    listed, answerers = session.owner_people(root, pull)
    found = session.owner_apply(repo, number, {"minutes": 0}, listed, answerers,
                                datetime.now(UTC), unpark_only=True,
                                carried=session.carried_check(root))  # fmt: skip
    if found is None:
        return []
    return [f"unparked #{number} {found[1]}", *tell(root, conductor, number, found[1])]


def relay(root: Path, opts: argparse.Namespace) -> tuple[int, list[str]]:
    if os.environ.get("AGK_STEWARD_START") == "conductor":  # brief #1387, SPEC-0063 rule 4
        return 2, ["refused: a steward the supervisor started relays nothing "
                   "(setting: AGK_STEWARD_START)"]  # fmt: skip
    words = opts.said.read_text(encoding="utf-8").strip()
    if len(words.splitlines()) != 1:
        return 2, [f"refused: the owner's words are one line, verbatim ({RULE})"]
    body = relay_body(opts.qid, opts.answer.strip(), words, opts.at)
    if problem := relay_problem(body):
        return 2, [problem]
    if personal_table(root) is not None:
        return 0, [f"post on #{opts.on}:", *body.splitlines()]
    repo = session.repo_name(root)
    post(repo, opts.on, body)
    return 0, [
        f"relayed {opts.qid} on #{opts.on}",
        *unpark(root, repo, opts.on, opts.qid, opts.conductor),
    ]


def park(root: Path, number: int, conductor: str | None, now: datetime) -> tuple[int, list[str]]:
    """The steward's owner-wait pass on one pull request (SPEC-0059 rule 10)."""
    if personal_table(root) is not None:
        return 0, ["personal mode: nothing is parked"]
    repo = session.repo_name(root)
    pull = session.gh(f"repos/{repo}/pulls/{number}")
    if not isinstance(pull, dict):
        raise steward.Unreadable(f"#{number}")
    listed, answerers = session.owner_people(root, pull)
    settings = session.owner_wait_settings(root)
    found = session.owner_apply(repo, number, settings, listed, answerers, now,
                                carried=session.carried_check(root))  # fmt: skip  # brief #1534
    if found and found[0] == "park":
        return 0, [f"parked #{number} {found[1]}"]
    if found:
        return 0, [f"unparked #{number} {found[1]}", *tell(root, conductor, number, found[1])]
    return 0, [f"#{number}: nothing to park"]


def memory_questions(root: Path) -> list[str] | None:
    """The open `Owner question:` lines of the memory as `steward.py start` last read it."""
    if personal_table(root) is not None:
        return steward.open_questions(steward.personal_entries(root))
    cache = steward.load_cache(root)
    return steward.open_questions(cache["comments"]) if "comments" in cache else None


def not_ready(root: Path, plan_text: str, trace_text: str) -> list[str]:
    """Each failed check of the plan's hand-over to the conductor (SPEC-0059 rule 2)."""
    out = []
    lines = [x for x in trace_text.splitlines() if x.strip()]
    if not lines or not lines[-1].startswith("ok plan"):
        out.append("not ready: the plan check's trace does not end `ok plan`")
    try:
        plan = json.loads(plan_text)
    except ValueError:
        plan = None
    if not isinstance(plan, dict) or plan.get("malformed") != []:
        out.append("not ready: the plan lists a malformed brief, or cannot be read")
    if not (root / "docs" / "plan" / "scope-lock.md").is_file():
        out.append("not ready: the scope is not locked")
    asked = memory_questions(root)
    if asked is None:
        out.append("not ready: the memory is not read (run steward.py start)")
    elif any(not (named := MILESTONE.findall(q)) or "1" in named for q in asked):
        out.append("not ready: an open owner question blocks the first milestone")
    import playbook_format

    if playbook_format.selected(root) is not None and not confirmed(root):
        out.append(UNCONFIRMED)  # SPEC-0072 rule 8 (brief #1601): nothing before the one yes
    return out


def ready(root: Path, opts: argparse.Namespace) -> tuple[int, list[str]]:
    failed = not_ready(
        root, opts.plan.read_text(encoding="utf-8"), opts.trace.read_text(encoding="utf-8")
    )
    if failed:
        return 1, [*failed, "conductor: not started"]
    args = ["role", "--role", "conductor", "--session", opts.session]
    if not opts.start:
        return 0, ["ready: run python3 scripts/agk/launch.py " + " ".join(args)]
    auto, adapter = launch.launch_settings(root)
    if auto and adapter:  # brief #1387 (ADR-0585): this start is the supervisor's
        return 0, ["ready: the supervisor starts the conductor at its next pass "
                   "(python3 scripts/agk/conductor.py watchdog --pass)"]  # fmt: skip
    return launch.role_main(args), []


# --- the standard: shown, confirmed on one yes, the work-type path (brief #1601, ADR-0681) -------

YES_ASK = "Shall I hold the product to all of this? Say yes, or tell me what to change."
NO_WORK_TYPE = (
    "No kind of product I know fits yours. May I look it up, in general words only? Yes or no."
)
NOT_CONFIRMED = (
    "not confirmed: nothing applied (setting: the confirmation Setup entry, SPEC-0062 rule 14)"
)
UNCONFIRMED = "not ready: the standard is not confirmed (setting: the confirmation Setup entry)"
NO_SEARCH = "search: none; the playbook is drafted from the requirements alone"
STANDARD = "Setup: standard: confirmed because"
PLAIN = (  # SPEC-0072 rule 8: the business user's screen, one plain sentence per group of gates
    (("tests-first", "definition-of-done"), "Every change comes with its tests, written first."),
    (("secrets", "environment-settings"),
     "No password or key is stored with the code; settings come from where it runs."),
    (("sign-in-permissions", "input-validation", "logging-tracing", "migrations", "rollback",
      "contract-first", "evidence-per-gate"),
     "Sign-in, inputs, event records and data changes are reviewed; every change can be undone."),
    (("accessibility", "performance"),
     "Screens are reviewed so everyone can use them; speed is held to your budget."),
)  # fmt: skip
GENERIC_BAD = re.compile(r"@|://|\bwww\.|\d|\s[A-Z]")


def composed_standard(root: Path, slug: str | None) -> tuple[list, dict, list] | None:
    """The composed gates, architecture and packs of the declared (or named) playbook."""
    import check_playbooks
    import playbook_format

    path = (
        playbook_format.selected(root)
        if slug is None
        else root / playbook_format.FOLDER / f"{slug}.toml"
    )
    if path is None or not playbook_format.DERIVED_NAME.match(path.stem) or not path.is_file():
        return None
    gates, _, _ = check_playbooks.composed(path, root)
    architecture, packs, _ = check_playbooks.standard(path, root)
    return gates, architecture, packs


def tree_draft(root: Path) -> tuple[list, list, str] | None:
    """Brief #1842 answer 2: in adopt mode, the layers drafted from the tree when the composed
    layers hold no source file of it; None otherwise."""
    from gates import layers  # noqa: PLC0415 - only the standard screen needs it

    if not layers.adopted(root) or not layers.empty(root):
        return None
    return layers.draft(root)[1]


def standard_screen(root: Path, slug: str | None) -> tuple[int, list[str]]:
    """Rule 8: one plain screen in solo mode, the full list in team mode; nothing is applied."""
    found = composed_standard(root, slug)
    if found is None:
        return 1, [NO_WORK_TYPE]
    gates, architecture, packs = found
    layers = [x for x in architecture.get("layers", []) if isinstance(x, dict)]
    drafted = tree_draft(root)
    if review_mode(root) == "team":
        out = [f"Layer {x.get('name')}: {', '.join(x.get('paths', []))}" for x in layers]
        out += [f"Allowed: {a.get('from')} -> {a.get('to')}" for a in architecture.get("allow", [])]
        if drafted:  # beside the playbook's: the tree's own parts and the directions used today
            out += [f"Drafted layer {n}: {', '.join(ps)}" for n, ps in drafted[0]]
            out += [f"Drafted allowed: {a} -> {b}" for a, b in drafted[1]]
        for p in packs:
            rules = p.get("rules") or {}
            out.append(f"Pack {p.get('stack')}: lint {p.get('lint')}, format {p.get('format')},"
                       " type"
                       f" {p.get('type')}; rules {rules.get('tool')} {rules.get('version')}"
                       f" {', '.join(rules.get('codes', []))}")  # fmt: skip
        for g in gates:
            why = (
                f"step {g.get('step')}"
                if g.get("kind") == "check"
                else g.get("reason") or g.get("text")
            )
            out.append(f"Gate {g['id']}: {g['kind']} ({why})")
        return 0, [*out, YES_ASK]
    ids = {g["id"] for g in gates}
    more = len(ids - {n for names, _ in PLAIN for n in names})
    extra = f" (and {more} more checks your reviewers can list)" if more else ""
    out = [f"Your product will be held to this{extra}:"]
    out += [f"- {line}" for names, line in PLAIN if ids & set(names)]
    parts = f"kept in {len(layers)} separate parts" if len(layers) > 1 else ""
    if drafted:  # brief #1842: the tree's own parts, in place of the playbook's
        parts = f"kept in {len(drafted[0])} parts as it is today"
    checked = "checked for style and type mistakes on each change" if packs else ""
    if parts or checked:  # at most five bullets and 100 characters a line (the steward's voice)
        joined = " and ".join(x for x in (parts, checked) if x)
        if drafted:
            out.append(f"- Your code is {joined.replace(' on each change', '')}.")
        else:
            out.append(
                f"- The code is {joined}{' that use each other only in set ways' * (not checked)}."
            )
    return 0, [*out, YES_ASK]


def yes_of(
    root: Path, words_file: Path, by: str | None, team: bool = True
) -> tuple[int, str | None, str]:
    """(refusal code, refusal line, the words): rule 8's explicit yes, by whom it counts."""
    import reviewers

    words = words_file.read_text(encoding="utf-8").strip()
    if os.environ.get("AGK_STEWARD_START") == "conductor":
        return (
            2,
            "refused: a steward the supervisor started confirms nothing"
            " (setting: AGK_STEWARD_START)",
            words,
        )
    if (
        team
        and review_mode(root) == "team"
        and (by or "").lower() not in {a.lower() for a in reviewers.spec_approvers(root)}
    ):
        return (
            2,
            "refused: in team mode only a spec approver's yes counts (setting: spec_approvers)",
            words,
        )
    return 0, None, words


def confirm(root: Path, words_file: Path, at: str, by: str | None, gh) -> tuple[int, list[str]]:
    """Rule 8: one explicit yes records one Setup entry; any other reply records nothing."""
    import steward_voice

    code, refusal, words = yes_of(root, words_file, by)
    if refusal:
        return code, [refusal]
    if not words or not steward_voice.is_yes(words):
        return 1, [NOT_CONFIRMED]
    who = f" (by {by})" if by and review_mode(root) == "team" else ""
    return steward.record(
        root, "Setup", f'standard: confirmed because the person said "{words}" at {at}{who}', gh
    )


def confirmed(root: Path) -> bool:
    """A `Setup: standard: confirmed` entry in the memory as `steward.py start` last read it."""
    if personal_table(root) is not None:
        items = steward.personal_entries(root)
    else:
        items = steward.load_cache(root).get("comments", [])
    return any(str(i.get("body", "")).startswith(STANDARD) for i in items)


def generic_problem(root: Path, text: str) -> str | None:
    """Rule 8: a generic description of the product type, never a name, address or number."""
    from guard import scan_text

    from config import guard_patterns

    if not text or len(text) > 120 or "\n" in text or GENERIC_BAD.search(text):
        return "refused: not a generic description (setting: the web-research description, rule 8)"
    if scan_text(text, guard_patterns(root)):
        return "refused: the description holds data the guard finds (setting: [guard])"
    return None


def research(root: Path, words_file: Path, at: str, text: str, gh, search) -> tuple[int, list[str]]:
    """Rule 8: the permission is recorded; only on a yes, the generic description is searched."""
    import steward_voice

    code, refusal, words = yes_of(root, words_file, None, team=False)
    if refusal:
        return code, [refusal]
    yes = bool(words) and steward_voice.is_yes(words)
    if yes and (problem := generic_problem(root, text.strip())):
        return 2, [problem]
    choice = "yes" if yes else "no"
    code, lines = steward.record(
        root, "Setup", f'web-research: {choice} because the person said "{words}" at {at}', gh
    )
    if code or not yes:
        return code, [*lines, NO_SEARCH]
    search(text.strip())
    return 0, [*lines, f"search: {text.strip()}"]


# Brief #1827 (ADR-0760): the two records carry what the project's `check_adrs` requires; the
# requirement and its reason are `wsl.REQUIREMENT`'s (protected paths change only with an ADR).
ADR_REQUIREMENT = "REQ-001"


def residual() -> list[str]:
    return ["## Residual", "",
            f"- {datetime.now(UTC):%Y-%m-%d}: none; the owner reviews the change before the merge.",
            ""]  # fmt: skip


def next_adr(root: Path) -> int:
    numbers = [int(p.name[:4]) for p in (root / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")]
    return max(numbers, default=0) + 1


def drafted_lines(layers_file: Path | None) -> list[str]:
    """Brief #1842: the ADR's list of the drafted layers and directions, from the saved draft."""
    if layers_file is None:
        return []
    try:
        text = layers_file.read_text(encoding="utf-8")
        data = tomllib.loads("\n".join(x for x in text.splitlines() if not x.startswith("draft ")))
        arch = data["architecture"]
        out = [f"- `{x['name']}`: {', '.join(f'`{g}`' for g in x['paths'])}" for x in arch["layers"]]
        out += [f"- `{e['from']}` may import `{e['to']}`" for e in arch.get("allow", [])]
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return []  # derive-write refuses it, naming the key
    return ["", "The layers drafted from the project's own folders, with the directions used today:",
            "", *out]  # fmt: skip


def draft(root: Path, slug: str, layers_file: Path | None = None) -> tuple[int, list[str]]:
    """Rule 8: the project playbook on `default.toml` and its Proposed ADR; never the work type.
    Brief #1842: `--layers FILE` carries the drafted layers, only after the recorded yes."""
    import front_door
    import playbook_format

    if layers_file is not None and not confirmed(root):
        return 2, ["refused: the person's yes to the standard is not recorded (setting: Setup)"]
    number = next_adr(root)
    rel = f"docs/adr/{number:04d}-the-project-s-work-type-{slug}.md"
    opts = {"--slug": slug}
    listed = drafted_lines(layers_file)
    if layers_file is not None:  # its `allow` entries name this ADR, written first
        declared = playbook_format.declaration(root)[0]
        shipped = declared in playbook_format.WORK_TYPES
        opts.update({"--layers": str(layers_file), "--adr": f"ADR-{number:04d}"})
        opts.update({"--modules": declared} if shipped and declared else {})
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(f"# ADR-{number:04d}: drafted\n", encoding="utf-8")
    try:
        front_door.derive_write(opts, root)
    except front_door.Refusal as exc:
        (root / rel).unlink(missing_ok=True)
        return 2, [f"refused: {line}" for line in exc.problems]
    record = (root / front_door.RESEARCH / f"{slug}.md").read_text(encoding="utf-8")
    sources = [ln for ln in record.splitlines() if ln.startswith("- Source:")]
    text = "\n".join([
        f"# ADR-{number:04d}: The project's work type {slug}, drafted on the default playbook", "",
        "- Status: Proposed", f"- Date: {datetime.now(UTC):%Y-%m-%d}", "- Deciders: maintainers",
        f"- Related: config/playbooks/{slug}.toml, {front_door.RESEARCH}/{slug}.md",
        f"- Requirements: {ADR_REQUIREMENT}", "",
        "## Context", "",
        "No shipped playbook fits the requirements the steward gathered (SPEC-0072 rule 8).", "",
        "## Decision", "",
        f"The project's own playbook `{slug}` is composed on `default.toml`, keeping every gate"
        " at its kind;"
        " the owner names it in `[delivery] work_type` after the person's yes.", *listed, "",
        "## Sources", "", *(sources or ["- the project's requirements only"]), "",
        "## Consequences", "", "Accepted by the project's maintainers, never by an agent.", "",
        *residual(),
    ])  # fmt: skip
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")
    return 0, [f"drafted config/playbooks/{slug}.toml and {rel} (Proposed)"]


# --- kit defects and the steward's reads (brief #1411, ADR-0594) -------------------------------


def kit_version(root: Path) -> str:
    try:
        value = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return "unknown"
    return str(value) if isinstance(value, str) and guard_logs.NAME.fullmatch(value) else "unknown"


def shell_name() -> str:
    found = os.environ.get("SHELL") or os.environ.get("COMSPEC") or ""
    name = re.split(r"[\\/]", found)[-1] if found else "unknown"
    return name if guard_logs.NAME.fullmatch(name) else "unknown"


def refusal_lines(root: Path, count: int) -> list[dict]:
    """The newest COUNT lines of the refusal log, each field redacted again."""
    out: list[dict] = []
    for path in guard_logs.refusal_files(root):
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                line = json.loads(raw)
            except ValueError:
                continue
            if isinstance(line, dict):
                out.append(line)
    try:
        patterns = guard_logs.config.guard_patterns(root)
    except Exception:  # noqa: BLE001 - a refused table: the built-in detectors still redact
        patterns = []
    keep = ("at", "hook", "reason", "text", "error")
    return [
        {
            k: guard_logs.redact(json.dumps(x[k]) if k == "error" else str(x[k]), patterns)[0]
            for k in keep
            if k in x
        }  # fmt: skip
        for x in out[-count:]
        if count > 0
    ]


def defect_body(root: Path, title: str, expected: str, count: int) -> str:
    lines = refusal_lines(root, count)
    codes = sorted({x["reason"] for x in lines if x.get("reason")})
    body = [
        f"Kit defect: {title}",
        "",
        f"Kit version: {kit_version(root)}",
        f"Machine: {platform.system() or 'unknown'}; shell: {shell_name()}",
        f"Reason codes: {', '.join(codes) if codes else 'none recorded'}",
        "Refusals (redacted, from agk logs --refusals):",
        *([f"    {json.dumps(x, sort_keys=True)}" for x in lines] or ["    none recorded"]),
        "",
        f"What should happen instead: {expected}",
        "",
        "Not product work: never scheduled by the plan; the owner decides whether it goes to the "
        "kit's maintainers.",
        "",
        STEWARD_WHO,
    ]
    return "\n".join(body) + "\n"


def defect(root: Path, opts: argparse.Namespace) -> tuple[int, list[str]]:
    import steward_outbound  # noqa: PLC0415 - only for a report

    title, expected = opts.title.strip(), opts.file.read_text(encoding="utf-8").strip()
    if not title or len(title) > 200 or "\n" in title or not expected:
        return 2, ["refused: a kit defect has a one-line title and what should happen instead"]
    body = defect_body(root, title, expected, opts.refusals)
    if refused := steward_outbound.check(f"{title}\n{body}", root):
        return 2, refused
    draft = [f"kit defect draft ({KIT_DEFECT_LABEL}): {title}", *body.splitlines()]
    if personal_table(root) is not None:
        return 0, [*draft, "personal mode: nothing is posted; it is the person's to send"]
    if not opts.post:
        return 0, [*draft, "not posted: run again with --post on the owner's word"]
    repo = session.repo_name(root)
    made = session.gh(
        f"repos/{repo}/issues", "-f", f"title=Kit defect: {title}", "-f", f"body={body}",
        "-f", f"labels[]={KIT_DEFECT_LABEL}", method="POST",
    )  # fmt: skip
    if not isinstance(made, dict) or not made.get("number"):
        raise CheckError("the kit defect could not be posted")
    return 0, [f"kit defect filed: #{made['number']} ({KIT_DEFECT_LABEL})"]


def defects(root: Path) -> tuple[int, list[str]]:
    """The open kit defects, one line each (answer 1): the owner sees them, the plan never."""
    if personal_table(root) is not None:
        return 0, ["kit defects: personal mode keeps none on GitHub"]
    repo = session.repo_name(root)
    found = session.pages(f"repos/{repo}/issues?state=open&labels={KIT_DEFECT_LABEL}")
    if found is None:
        raise steward.Unreadable("the open kit defects")
    found = [i for i in found if isinstance(i, dict) and "pull_request" not in i]
    if not found:
        return 0, ["kit defects: none open"]
    return 0, [
        f"kit defect #{i.get('number')}: {' '.join(str(i.get('title') or '').split())[:100]} "
        f"(opened {str(i.get('created_at') or '')[:10]})"
        for i in sorted(found, key=lambda i: int(i.get("number") or 0))
    ]


RESTART = "restart the steward session (claude --agent steward)"


def permission_setting(root: Path) -> tuple[str, str]:
    """(setting, step) that explains a refused `gh api` read in this session (answer 2)."""
    allowed = False
    for name in ("settings.local.json", "settings.json"):
        try:
            data = json.loads((root / ".claude" / name).read_text(encoding="utf-8"))
            rules = data.get("permissions") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for kind in ("deny", "ask"):
            entries = rules.get(kind) if isinstance(rules, dict) else None
            if any(str(e).startswith(("Bash(gh", "Bash(*")) for e in entries or []):
                return f"permissions.{kind} of .claude/{name}", f"remove that entry, then {RESTART}"
        entries = rules.get("allow") if isinstance(rules, dict) else None
        allowed |= any(re.match(r"Bash\(gh(?: api)?(?:[ :]\*|\*)", str(e)) for e in entries or [])
    if not allowed:
        mode = "the session's permission mode, with no permissions.allow entry for gh api (verify)"
        return mode, f"{RESTART}, or approve the read when asked"
    return "the session's permission mode (verify)", RESTART


def gh_refusal() -> tuple[str, str] | None:
    """None when `gh api rate_limit` answers; else (setting, step)."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - one fixed argument list, no shell
            ["gh", "api", "rate_limit", "--jq", ".rate.remaining"],
            capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
        )  # fmt: skip
    except FileNotFoundError:
        return "gh on PATH", "install gh, then run gh auth login"
    except (OSError, subprocess.TimeoutExpired):
        return "the network or proxy (verify)", "check the connection, then run reads again"
    if proc.returncode == 0:
        return None
    if re.search(r"auth|log ?in|token", proc.stderr or "", re.IGNORECASE):
        return "gh auth", "run gh auth status, then gh auth login"
    return "the token's access to the repository", "run gh auth status, then gh auth refresh"


def reads(root: Path, session_id: str | None, refused: bool) -> tuple[int, list[str]]:
    found = permission_setting(root) if refused else gh_refusal()
    if found is None:
        return 0, ["reads: ok"]
    line = (
        f"reads: gh api refused (setting: {found[0]}); restore: {found[1]}; "
        "meanwhile the steward reads through the kit's scripts"
    )
    sid = session_id or os.environ.get("AGK_SESSION") or ""
    mark = guard_logs.refusal_path(root)
    if not mark or not guard_logs.NAME.fullmatch(sid):
        return 1, [line]
    mark = mark.with_name(f"steward-reads-{sid}")
    try:
        if mark.is_file() and mark.read_text(encoding="utf-8").strip() == line:
            return 1, []  # said once in this session
        mark.parent.mkdir(exist_ok=True)
        mark.write_text(line + "\n", encoding="utf-8")
    except OSError:
        pass
    return 1, [line]


# --- the one-yes approval: one pinned ask, the exact line on a yes (brief #1690, ADR-0703) -------

APPROVE_RULE = "SPEC-0062 rule 13"
BACKSTOP = re.compile(r"\?|\b(?:but|if|except|unless|change|not|later)\b", re.IGNORECASE)
NOT_YET = re.compile(r"not yet[.!]?", re.IGNORECASE)
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z")
SHA = re.compile(r"\b[0-9a-f]{40}\b")
TARGET = re.compile(r"(?:pr:)?(\d+)")
RECORD_ID = re.compile(r"SPEC-\d{4}|ADR-\d{4}|REQ-\d{3}")
NEVER = re.compile(r"(?:Merge|Verdict|Final|Correction):")
POSTED = (  # (form, pattern): the Maintainer answer forms, which count by login
    ("answer", re.compile(r"Maintainer answer: (Q-\d+-\w+) \S.*")),
    ("accept", re.compile(r"Maintainer answer: accept ([0-9a-f]{40})")),
    ("amendment", re.compile(r"Maintainer answer: amendment \d+ approved")),
)
PRINTED = (  # an app-marked approval approves nothing (ADR-0661 decision 8): printed to paste
    ("spec", re.compile(r"Approve: ([0-9a-f]{40}) SPEC-\d{4}")),
    ("signoff", re.compile(r"Approve: (?:design|inventory|plan|scope) .*\b([0-9a-f]{40})")),
)
DAY = timedelta(hours=24)


def asks_file(root: Path) -> Path:
    """The session's own pending asks, beside the memory cache (never a tracked file)."""
    return steward.cache_file(root).with_name("agk-steward-asks.json")


def load_asks(root: Path) -> list[dict]:
    path = asks_file(root)
    if not path.exists():
        return []
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = None
    if not isinstance(found, list):
        raise CheckError("the pending ask cannot be read (setting: the steward's ask state)")
    return found


def save_asks(root: Path, asks: list[dict]) -> None:
    path = asks_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asks), encoding="utf-8")


def line_form(root: Path, qid: str, text: str, head: str | None) -> str | None:
    """The form of the asked line, or None when this command never writes it."""
    lines = text.replace("\r\n", "\n").strip().splitlines()
    if not lines or NEVER.match(lines[0]):
        return None
    if lines[0].startswith("Confirmed:"):
        named = head is None or head in SHA.findall(text)
        shown = any(x.startswith("Shown:") for x in lines)
        return "confirmed" if named and shown else None
    if len(lines) != 1:
        return None
    for form, pattern in (*POSTED, *PRINTED):
        if found := pattern.fullmatch(lines[0]):
            if form == "answer" and found[1] != qid:
                return None
            if form in ("accept", "spec", "signoff") and head and found[1] != head:
                return None
            return form
    return None


def pull_state(root: Path, number: int) -> tuple[str, str, str]:
    """(state, full head, link) of pull request N, read with one GET."""
    repo = session.repo_name(root)
    pull = session.gh(f"repos/{repo}/pulls/{number}")
    if not isinstance(pull, dict) or not isinstance(pull.get("head"), dict):
        raise steward.Unreadable(f"#{number}")
    link = pull.get("html_url") or f"https://github.com/{repo}/pull/{number}"
    return str(pull.get("state")), str(pull["head"].get("sha")), link


def steward_session(root: Path) -> str | None:
    """The steward session asking now: `AGK_SESSION`, else the memory's newest
    `Started: steward <id>` with no `Ended:` after it (rule 13: an ask ends with its session)."""
    if found := os.environ.get("AGK_SESSION"):
        return found
    personal = personal_table(root) is not None
    items = steward.personal_entries(root) if personal else steward.load_cache(root).get("comments")
    for item in reversed(items if isinstance(items, list) else []):
        body = str(item.get("body", "")) if isinstance(item, dict) else ""
        if steward.ENDED.match(body):
            return None
        if started := steward.STARTED.match(body):
            return started[1]
    return None


def ask_target(
    root: Path, qid: str, target: str, text: str, line_file: Path, now: datetime
) -> tuple[int, list[str]]:
    """Rule 13: one plain question about one pull request head, pinned and recorded."""
    sentence = text.strip()
    if problem := question_problem(sentence) or (None if QID.fullmatch(qid) else "refused: Q id"):
        return 2, [problem]
    personal = personal_table(root) is not None
    found = TARGET.fullmatch(target)
    number = int(found[1]) if found else None
    if not personal and number is None:
        return 2, [f"refused: the target is one pull request, pr:<n> (setting: --target, {RULE})"]
    if personal and not RECORD_ID.fullmatch(target):  # what `personal.py confirm` takes
        return 2, ["refused: the target is REQ-nnn, SPEC-nnnn or ADR-nnnn (setting: --target)"]
    head = link = None
    if number is not None and not personal:
        state, head, link = pull_state(root, number)
        if state != "open":
            return 2, [f"refused: the target is closed ({APPROVE_RULE})"]
    line = line_file.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    form = line_form(root, qid, line, head)
    if form is None:
        return 2, [f"refused: not a line this command writes (setting: --line, {APPROVE_RULE})"]
    if form == "confirmed" and review_mode(root) == "team":
        return 2, ["refused: `Confirmed:` is never written in team mode (setting: review_mode)"]
    if (sid := steward_session(root)) is None:
        return 2, [
            "refused: no steward session is read (setting: AGK_SESSION, or steward.py start)"
        ]
    try:
        asks = load_asks(root)
    except CheckError as exc:
        return 2, [f"refused: {exc}"]
    pinned = f" (pinned {head} {link})" if head else ""
    code, said = steward.record(root, "Owner question", f"{qid} {sentence}{pinned}", steward.gh_api)
    if code:
        return code, said
    for old in asks:  # one open ask stands: the newer closes every older one
        old["open"] = False
    asks.append({"id": qid, "target": target, "number": number,
                 "head": head, "link": link, "question": sentence, "line": line,
                 "form": form, "at": steward.stamp(now), "open": True, "session": sid})  # fmt: skip
    save_asks(root, asks)
    asked = f"Question: {qid} for the maintainers: {sentence}"
    if personal or number is None:
        return 0, [f"ask the person: {sentence}", f"post: {asked}", *said]
    post(session.repo_name(root), number, f"{asked}\n\n{STEWARD_WHO}")
    return 0, [f"ask the person: {sentence}", f"asked on #{number}", *said]


def age_limit(root: Path) -> timedelta:
    """Q-1690-2: four times `[flow] owner_wait_minutes`, 24 hours when unset or 0."""
    from config import config_source, owner_wait_settings

    minutes = owner_wait_settings(root)["minutes"]  # refuses a bad value naming the setting
    flow = config_source(root).get("flow", {})
    if not isinstance(flow, dict) or "owner_wait_minutes" not in flow or not minutes:
        return DAY
    return timedelta(minutes=4 * minutes)


def approve_body(ask: dict, words: str, at: str) -> str:
    quotes = [
        f'Owner said ({at}): "{words}"',
        f'Asked ({ask["at"]}): "{ask["question"]}" {ask["link"]}',
    ]
    lines = ask["line"].splitlines()
    shown = next((i for i, x in enumerate(lines) if x.startswith("Shown:")), len(lines))
    return "\n".join([*lines[:shown], *quotes, *lines[shown:], OWNER_WHO]) + "\n"


def approve(
    root: Path, qid: str, words_file: Path, at: str, by: str | None, now: datetime
) -> tuple[int, list[str]]:
    """Rule 13: on the person's yes to the latest open ask, the exact line, else nothing."""
    import steward_voice
    from guard import scan_text

    from config import guard_patterns

    if not TIME.fullmatch(at):
        return 2, [
            f"refused: the reply time is UTC, YYYY-MM-DDTHH:MMZ (setting: --at, {APPROVE_RULE})"
        ]
    code, refusal, words = yes_of(root, words_file, by)
    if refusal:
        return code, [refusal]
    if len(words_file.read_text(encoding="utf-8").strip().splitlines()) != 1:
        return 2, [f"refused: the person's words are one line, verbatim ({APPROVE_RULE})"]
    try:
        asks = load_asks(root)
        limit = age_limit(root)
    except CheckError as exc:
        return 2, [f"refused: {exc}"]
    open_asks = [x for x in asks if x.get("open")]
    if not open_asks or open_asks[-1].get("id") != qid:
        return 2, [f"refused: not the session's latest open ask; ask again ({APPROVE_RULE})"]
    ask = open_asks[-1]
    if steward_session(root) != ask.get("session"):
        return 2, [f"refused: the ask was made in another session; ask again ({APPROVE_RULE})"]
    asked = datetime.strptime(ask["at"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
    if at[:16] + "Z" < ask["at"]:
        return 2, [f"refused: the reply is older than the ask (setting: --at, {APPROVE_RULE})"]
    if at[:16] + "Z" > steward.stamp(now):
        return 2, [f"refused: the reply time is in the future (setting: --at, {APPROVE_RULE})"]
    if now - asked > limit:
        return 2, ["refused: the ask is too old; ask again (setting: [flow] owner_wait_minutes)"]
    if findings := scan_text(words, guard_patterns(root)):
        classes = ", ".join(sorted({f.kind for f in findings}))
        return 2, [f"refused: the words hold {classes} (setting: [guard]; data guard, SPEC-0042)"]
    if NOT_YET.fullmatch(words):
        code, said = steward.record(
            root, "Decision", f'{qid}: not yet, the person said "{words}" at {at}', steward.gh_api
        )
        return code or 1, said if code else ["not yet: recorded, nothing posted"]
    if BACKSTOP.search(words):
        return 2, ["refused: a question or a condition is not a yes; a change is a new decision,"
                   " asked again (SPEC-0062 rule 14)"]  # fmt: skip
    if not steward_voice.is_yes(words):
        return 1, ["not a yes: nothing posted; ask again in other words (SPEC-0062 rule 14)"]
    personal = personal_table(root) is not None
    head = None
    if not personal:
        state, head, _ = pull_state(root, ask["number"])
        if state != "open":
            return 2, [f"refused: the target is closed; nothing posted ({APPROVE_RULE})"]
        if head != ask["head"]:
            return 2, [f"refused: the head moved since the ask; ask again ({APPROVE_RULE})"]
    form = line_form(root, qid, str(ask.get("line", "")), head)  # read again: never the stored form
    if form is None or (form == "confirmed" and review_mode(root) == "team"):
        return 2, [f"refused: not a line this command writes (setting: --line, {APPROVE_RULE})"]
    body = approve_body(ask, words, at)
    approval = form not in ("answer", "accept", "amendment") and not personal
    if approval and review_mode(root) == "team":  # Q-1691-1: until the kept login is built
        return 2, [
            "refused: the steward posts no approval in team mode"
            f" (setting: review_mode, {APPROVE_RULE})"
        ]
    if approval and not posts_approval(root):
        ask["open"] = False
        save_asks(root, asks)
        return 0, [f"paste on #{ask['number']} ({ask['link']}):", *body.splitlines()]
    if approval and form != ask.get("form"):  # posted only as asked: an edited state is refused
        return 2, [f"refused: not the line asked (setting: --line, {APPROVE_RULE})"]
    where = f"{ask['target']}" if personal else f"#{ask['number']} at {head} {ask['link']}"
    code, said = steward.record(  # first: a memory that cannot be written posts nothing
        root, "Decision", f'{qid}: yes on {where}, the person said "{words}" at {at}',
        steward.gh_api,
    )  # fmt: skip
    if code:
        return code, said
    ask["open"] = False
    save_asks(root, asks)
    if personal:
        return 0, [
            "run in your own terminal:",
            f"python3 scripts/agk/personal.py confirm {ask['target']}",
        ]
    found = post_file(root, ask["number"], body)
    link = str(found.get("html_url", ""))
    if approval and (problem := read_back(root, found)):  # brief #1691 answer 2
        steward.record(root, "Decision", f"{qid}: {problem}; printed to paste", steward.gh_api)
        return 1, [problem, f"paste on #{ask['number']} ({ask['link']}):", *body.splitlines()]
    return 0, [f"posted on #{ask['number']}: {body.splitlines()[0]}", link]


def posts_approval(root: Path) -> bool:
    """Brief #1691 answer 1 (ADR-0704): the steward posts an `Approve:` or `Confirmed:` itself only
    in solo mode with one person listed, and not where the runtime posts through an agent app by
    its own mark (`common.REMOTE_RUNTIME`, SPEC-0062 rule 13; Q-1691-3)."""
    import reviewers

    return reviewers.solo_person(root) is not None and os.environ.get(REMOTE_RUNTIME) != "true"


def read_back(root: Path, posted: dict) -> str | None:
    """Brief #1691 answer 2: the posted comment read with one GET; the line that says it does not
    count when GitHub marks it with an app of `agent_apps` or it cannot be read; nothing deleted."""
    import reviewers

    found = session.gh(f"repos/{session.repo_name(root)}/issues/comments/{posted.get('id')}")
    if not isinstance(found, dict):
        return "this approval cannot be read back; it may not count (setting: agent_apps)"
    if reviewers.via_agent(found, agent_apps(root)):
        return (
            "this approval does not count: it was posted through an agent app (setting: agent_apps)"
        )
    return None


def post_file(
    root: Path, number: int, body: str, endpoint: str = "", method: str = "POST", extra=()
) -> dict:
    """Post BODY with `-F body=@<file>` (UTF-8, LF), the file kept beside the ask state; by
    default a comment on #NUMBER, else ENDPOINT with EXTRA fields (brief #1715)."""
    folder = asks_file(root).parent
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"agk-steward-approve-{number}.md"
    path.write_bytes(body.encode("utf-8"))
    try:
        endpoint = endpoint or f"repos/{session.repo_name(root)}/issues/{number}/comments"
        found = session.gh(endpoint, *extra, "-F", f"body=@{path}", method=method)
    finally:
        path.unlink(missing_ok=True)
    if found is None:
        raise CheckError(f"the comment on #{number} could not be posted")
    return found if isinstance(found, dict) else {}


# --- brief #1715 (ADR-0714): a brief's mechanical lines fixed, an approved draft filed ----------

FIX_RULE = "SPEC-0059 rule 6"
MECHANICAL = ("Adds:", "Touches:", "Reserved:", "Depends-on:", "Evidence")
PRIORITY = re.compile(r"^Priority:\s*(\d+)", re.M)
TAKE = re.compile(r"(taken|Started|released):")


def gate(root: Path) -> str | None:
    """Neither command runs in a steward the supervisor started; a bad layout is refused by name."""
    import kit_root

    if os.environ.get("AGK_STEWARD_START") == "conductor":
        return ("refused: a steward the supervisor started fixes and files nothing"
                " (setting: AGK_STEWARD_START)")  # fmt: skip
    try:
        kit_root.layout(root)
    except kit_root.Refused as exc:
        raise CheckError(str(exc)) from None
    return None


def brief_refusal(
    root: Path, body: str, number: int | None, warned: list[str] | None = None
) -> str | None:
    """The in-command checks: `check_brief.py --root` on the body, its study included (brief
    #1813), then the neutrality lists. Each study warning goes into WARNED as `warning: ...`."""
    import check_brief
    import steward_outbound

    problems, warnings = check_brief.brief_result(body, root, None, {"number": number})
    if problems:
        return f"refused: the body fails the brief check: {'; '.join(problems)} ({FIX_RULE})"
    lists = steward_outbound.tokens(root)
    if isinstance(lists, str):
        return f"refused: the neutrality list cannot be read (setting: {lists})"
    for setting, tokens in lists:
        if any(t in body.lower() for t in tokens):
            return f"refused: the body holds a token of {setting} (setting: {setting})"
    if warned is not None:
        warned += [f"warning: {w}" for w in warnings]
    return None


def proposed(number: int, body: str, setting: str) -> tuple[int, list[str]]:
    return 1, [f"Proposed body: brief #{number}", *body.rstrip().splitlines(),
               f"not written: the owner applies it (setting: {setting})"]  # fmt: skip


def take_refusal(issue: dict, comments: list) -> str | None:
    """The brief as read is the brief fixed: open, an `agk-brief`, no intake, no live take."""
    labels = {str(x.get("name")) for x in issue.get("labels") or [] if isinstance(x, dict)}
    taken = False
    for c in comments:
        first = (str(c.get("body") or "").strip().splitlines() or [""])[0]
        if found := TAKE.match(first):
            taken = found[1] != "released"
    for bad, setting in (
        (issue.get("state") != "open" or "pull_request" in issue, "state"),
        (session.LABEL not in labels, session.LABEL),
        (str(issue.get("title") or "").startswith("Intake:"), "Intake:"),
        (session.TAKEN_LABEL in labels or taken, session.TAKEN_LABEL),
    ):
        if bad:
            number = issue.get("number")
            return f"refused: #{number} is not a brief the steward fixes (setting: {setting})"
    return None


def fix_brief(root: Path, number: int, new_file: Path, seen: str) -> tuple[int, list[str]]:
    """Answer 1: replace an open brief's body when only its mechanical lines change."""
    import difflib

    import reviewers

    from config import steward_settings

    if refusal := gate(root):
        return 2, [refusal]
    new = new_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    warned: list[str] = []  # brief #1813: the study's warnings, after the lines below
    settings = steward_settings(root)  # a malformed table is refused naming the setting
    if personal_table(root) is not None:
        if refusal := brief_refusal(root, new, number, warned):
            return 2, [refusal]
        return 0, ["personal mode: nothing is posted or patched; the developer applies this body:",
                   *new.rstrip().splitlines(), *warned]  # fmt: skip
    if settings["fix_briefs"] is not True:
        return proposed(number, new, "steward.fix_briefs")
    if reviewers.solo_person(root) is None:
        return proposed(number, new, "review_mode")
    repo = session.repo_name(root)
    issue = session.gh(f"repos/{repo}/issues/{number}")
    comments = session.pages(f"repos/{repo}/issues/{number}/comments") if issue else None
    if not isinstance(issue, dict) or comments is None:
        raise steward.Unreadable(f"#{number}")
    if refusal := take_refusal(issue, comments):
        return 2, [refusal]
    if issue.get("updated_at") != seen:
        return 2, [f"refused: #{number} changed since it was read; read it again (setting: --seen)"]
    old = str(issue.get("body") or "").replace("\r\n", "\n")
    changed = [
        x[2:] for x in difflib.ndiff(old.splitlines(), new.splitlines()) if x[:2] in ("- ", "+ ")
    ]
    if not changed:
        return 0, [f"#{number}: nothing to change"]
    if any(x.strip() and not x.strip().startswith(MECHANICAL) for x in changed):
        return proposed(number, new, "a line that is not mechanical")
    if refusal := brief_refusal(root, new, number, warned):
        return 2, [refusal]
    saved = (f"Body fixed: #{number} by the steward, its mechanical lines only; the old body "
             f"follows, one copy restores it.\n\n{old.rstrip()}\n\n{STEWARD_WHO}\n")  # fmt: skip
    post_file(root, number, saved)  # first: a failed post writes no body
    found = post_file(root, number, new, f"repos/{repo}/issues/{number}", "PATCH")
    keys = sorted({x.strip().split(":")[0].split(" ")[0] for x in changed if x.strip()})
    code, said = steward.record(
        root, "Decision", f"#{number} body fixed by the steward: {', '.join(keys)} lines "
        "(the old body is its Body fixed: comment)", steward.gh_api,
    )  # fmt: skip
    return code, [
        f"fixed #{number}: {len(changed)} lines",
        f"seen: {found.get('updated_at')}",
        *said,
        *warned,
    ]


def with_owner_said(body: str, at: str, words: str) -> str:
    lines = body.rstrip().splitlines()
    who = [STEWARD_WHO] if lines and lines[-1] == STEWARD_WHO else []
    return (
        "\n".join([*lines[: len(lines) - len(who)], f'Owner said ({at}): "{words}"', STEWARD_WHO])
        + "\n"
    )


def named_yes(words: str, name: str) -> bool:
    """Brief #1753 answer 1: `yes, file the <name> brief` and its three shorter forms."""
    said, name = (" ".join(x.lower().split()) for x in (words.strip().removesuffix("."), name))
    n = re.escape(name)
    return bool(
        re.fullmatch(rf"yes,? (?:file the {n} brief|file {n}|brief the {n}|brief {n})", said)
    )


def flat(text: object) -> str:
    return " ".join(str(text or "").lower().split())


def duplicate(root: Path, title: str, body: str) -> int | None:
    """Brief #1753 answer 3: the open brief with this title or body (no `Owner said` line)."""

    def bare(text: object) -> str:
        lines = str(text or "").replace("\r\n", "\n").splitlines()
        return "\n".join(x for x in lines if not x.startswith("Owner said (")).strip()

    found = session.pages(
        f"repos/{session.repo_name(root)}/issues?labels={session.LABEL}&state=open"
    )
    if found is None:
        raise steward.Unreadable("the open briefs")
    for issue in found:
        if (
            isinstance(issue, dict)
            and "pull_request" not in issue
            and (flat(issue.get("title")) == flat(title) or bare(issue.get("body")) == bare(body))
        ):
            return issue.get("number")
    return None


def file_brief(
    root: Path, draft_file: Path, title: str, said: Path | None, at: str | None,
    by: str | None, now: datetime, name: str | None = None,
) -> tuple[int, list[str]]:  # fmt: skip
    """Answer 2: open one `agk-brief` at or below `auto_file`, or on the person's explicit yes."""
    import reviewers
    import steward_outbound as outbound
    import steward_voice

    from config import steward_settings

    if refusal := gate(root):
        return 2, [refusal]
    if name is not None and said is None:
        return 2, ["refused: --name goes with --said (setting: --name)"]
    if name is not None and not (0 < len(name) <= 80 and "`" not in name and name.isprintable()):
        return 2, [
            "refused: --name is one line of 1 to 80 characters, no backquote (setting: --name)"
        ]
    body, title = (
        draft_file.read_text(encoding="utf-8").replace("\r\n", "\n"),
        " ".join(title.split()),
    )
    if not title or len(title) > 200:
        return 2, ["refused: a brief has a one-line title (setting: --title)"]
    limit = steward_settings(root)["auto_file"]
    draft = [f"brief draft: {title}", *body.rstrip().splitlines()]
    if said is None:
        priority = PRIORITY.search(body)
        if limit is False or priority is None or int(priority[1]) > limit:
            return 1, [*draft, "not filed: above what the steward files without the person's yes"
                       " (setting: steward.auto_file)"]  # fmt: skip
    else:
        words = said.read_text(encoding="utf-8").strip()
        if not at or not TIME.fullmatch(at) or len(words.splitlines()) != 1:
            return 2, ["refused: the person's words are one line with a UTC time (setting: --at)"]
        approvers = {a.lower() for a in reviewers.spec_approvers(root)}
        if reviewers.solo_person(root) is None and (by or "").lower() not in approvers:
            return 2, [
                "refused: in team mode only a spec approver's yes counts (setting: spec_approvers)"
            ]
        if BACKSTOP.search(words) or not (
            steward_voice.is_yes(words) or (name is not None and named_yes(words, name))
        ):
            return 1, [*draft, "not a yes: nothing filed; ask again in other words"]
        moment = datetime.strptime(at[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
        if moment > now or now - moment > age_limit(root):
            return 2, [
                "refused: the yes is too old or in the future (setting: [flow] owner_wait_minutes)"
            ]
        body = with_owner_said(body, at, words)
    warned: list[str] = []
    if refusal := brief_refusal(root, body, None, warned):
        return 2, [refusal]
    if personal_table(root) is not None:
        return 0, ["personal mode: nothing is posted; the developer files this brief:", *draft,
                   *warned]  # fmt: skip
    if (held := duplicate(root, title, body)) is not None:
        return 2, [f"refused: #{held} is an open brief with this title or body; nothing filed"
                   " (setting: --title)"]  # fmt: skip
    repo = session.repo_name(root)
    kit = outbound.kit_repo(root)
    if kit == repo.lower() and not outbound.is_kit(outbound.remotes(root), kit):
        if refused := outbound.check(f"{title}\n{body}", root):
            return 2, refused
    made = post_file(root, 0, body, f"repos/{repo}/issues", "POST",
                     ("-f", f"title={title}", "-f", f"labels[]={session.LABEL}"))  # fmt: skip
    if not made.get("number"):
        raise CheckError("the brief could not be filed")
    why = "the person's yes" if said else "at or below steward.auto_file"
    code, lines = steward.record(
        root, "Decision", f"#{made['number']} filed as a brief: {why}", steward.gh_api
    )
    return code, [f"brief filed: #{made['number']} ({session.LABEL})", *lines, *warned]


# --- brief #1757 (ADR-0735, amendment 218): the work type named in discovery, on the owner's yes

WORK_TYPE_RULE = "SPEC-0038 rule 5"
WORK_TYPE_BRANCH = "steward/work-type"
PLAIN_KIND = {
    "web-app": "a web app", "mobile": "a mobile app", "cloud-migration": "a move to the cloud",
    "rag-app": "an app that answers from your documents", "mcp-server": "a tool server for AI",
    "multi-agent": "a team of AI helpers", "voice-agent": "a voice assistant",
    "data-pipeline": "a data pipeline",
}  # fmt: skip
DELIVERY = re.compile(r"^\[delivery\][ \t]*(?:#.*)?$", re.M)


def work_type_state(root: Path) -> tuple[str | None, dict[str, list[str]]]:
    """(the declared work type, the work types discovery names); a bad declaration is refused."""
    import playbook_format

    value, problems = playbook_format.declaration(root)
    if problems:
        raise CheckError(problems[0])
    return value, playbook_format.discovered_work_types(root)


def work_type_propose(root: Path, now: datetime) -> tuple[int, list[str]]:
    """Answer 1: one owner question when discovery names one work type and none is declared."""
    value, found = work_type_state(root)
    if value is not None:
        if found and value not in found:
            return 0, ["work type: declared; it differs from discovery and the declared one is"
                       " kept (setting: work_type)"]  # fmt: skip
        return 0, ["work type: declared; nothing to propose"]
    if not found:
        return 0, ["work type: discovery names none; nothing to propose"]
    kinds = sorted(found)
    if len(kinds) > 1:  # answer 7: no proposal, the owner chooses between them
        named = ", ".join(PLAIN_KIND[k] for k in kinds[:-1]) + f" and {PLAIN_KIND[kinds[-1]]}"
        return 0, [f"ask the person: Your discovery names both {named}. Which one is it?"
                   " I recommend you choose one before the tools are picked."]  # fmt: skip
    kind = kinds[0]
    sentence = (
        f"Your discovery says this is {PLAIN_KIND[kind]}. Shall I set that up, so the {kind}"
        " checks run? Yes or not yet; I recommend yes."
    )
    if problem := question_problem(sentence):
        return 2, [problem]
    if (sid := steward_session(root)) is None:
        return 2, [
            "refused: no steward session is read (setting: AGK_SESSION, or steward.py start)"
        ]
    asks = load_asks(root)
    for old in asks:  # one open ask stands
        old["open"] = False
    asks.append({"id": "work-type", "form": "work-type", "work_type": kind, "target": "agk.toml",
                 "number": None, "head": None, "link": None, "line": "", "question": sentence,
                 "discovery": found[kind], "at": steward.stamp(now), "open": True,
                 "session": sid})  # fmt: skip
    save_asks(root, asks)
    return 0, [f"ask the person: {sentence}"]


def git_out(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed git argument lists, no shell
        ["git", "-C", str(root), *args], capture_output=True, encoding="utf-8", check=False
    )


def with_work_type(text: str, kind: str) -> str:
    line = f'work_type = "{kind}"'
    if "delivery" in tomllib.loads(text) and (found := DELIVERY.search(text)):
        return f"{text[: found.end()]}\n{line}{text[found.end() :]}"
    return f"{text.rstrip(chr(10))}\n\n[delivery]\n{line}\n"


def record_classes(root: Path, rel: str) -> str:
    """Brief #1829 answer 3: the classes the work-type change meets, as `stack-write` names
    them; `agk.toml` alone when the project's list cannot be read."""
    import check_protected_changes as protected

    try:
        return protected.backticked(protected.step_classes(root, ["agk.toml", rel]))
    except CheckError:
        return "`agk.toml`"


def work_type_adr(root: Path, ask: dict, words: str, at: str) -> str:
    number = next_adr(root)
    kind = ask["work_type"]
    rel = f"docs/adr/{number:04d}-work-type.md"
    text = "\n".join([
        f"# ADR-{number:04d}: The project's work type is {kind}", "",
        "- Status: Proposed", f"- Date: {datetime.now(UTC):%Y-%m-%d}", "- Deciders: the owner",
        f"- Related: agk.toml, {', '.join(ask.get('discovery') or [])}",
        f"- Requirements: {ADR_REQUIREMENT}", "",
        f"Protected classes: {record_classes(root, rel)}", "",
        "## Context", "",
        f"The discovery document names the work type {kind}, and `agk.toml` declared none"
        f" ({WORK_TYPE_RULE}, amendment 218).", "",
        "## Decision", "",
        f'`agk.toml` declares `[delivery] work_type = "{kind}"`, so the {kind} playbook\'s'
        " checks run before the stack is chosen.", "",
        f'Asked ({ask["at"]}): "{ask["question"]}"', f'Owner said ({at}): "{words}"', "",
        "## Consequences", "",
        "The owner's merge of this pull request approves it; no agent merges it.", "",
        *residual(),
    ])  # fmt: skip
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")
    return rel


def work_type_yes(
    root: Path, words_file: Path, at: str, by: str | None, now: datetime
) -> tuple[int, list[str]]:
    """Answer 2: on the person's recorded plain yes, in solo mode with one person, the line and
    its Proposed ADR on a new branch; printed only otherwise. Never commits or pushes."""
    import reviewers
    import steward_voice
    from guard import scan_text

    from config import guard_patterns, load_config

    if not TIME.fullmatch(at):
        return 2, [
            f"refused: the reply time is UTC, YYYY-MM-DDTHH:MMZ (setting: --at, {APPROVE_RULE})"
        ]
    code, refusal, words = yes_of(root, words_file, by, team=False)
    if refusal:
        return code, [refusal]
    asks = load_asks(root)
    open_asks = [x for x in asks if x.get("open")]
    if not open_asks or open_asks[-1].get("form") != "work-type":
        return 2, [
            f"refused: no work-type proposal is the latest open ask; propose again ({APPROVE_RULE})"
        ]
    ask = open_asks[-1]
    if steward_session(root) != ask.get("session"):
        return 2, [f"refused: the ask was made in another session; ask again ({APPROVE_RULE})"]
    asked = datetime.strptime(ask["at"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
    if at[:16] + "Z" < ask["at"] or at[:16] + "Z" > steward.stamp(now):
        return 2, ["refused: the reply is older than the ask or in the future (setting: --at)"]
    if now - asked > age_limit(root):
        return 2, ["refused: the ask is too old; ask again (setting: [flow] owner_wait_minutes)"]
    if len(words.splitlines()) != 1 or scan_text(words, guard_patterns(root)):
        return 2, ["refused: the words are one line the data guard passes (setting: [guard])"]
    if NOT_YET.fullmatch(words):
        ask["open"] = False
        save_asks(root, asks)
        code, said = steward.record(
            root,
            "Decision",
            f'work-type: not yet, the person said "{words}" at {at}',
            steward.gh_api,
        )
        return code or 1, said if code else ["not yet: recorded, nothing written"]
    if BACKSTOP.search(words):
        return 2, ["refused: a question or a condition is not a yes (SPEC-0062 rule 14)"]
    if not steward_voice.is_yes(words):
        return 1, ["not a yes: nothing written; ask again in other words (SPEC-0062 rule 14)"]
    kind = ask["work_type"]
    if work_type_state(root) != (None, {kind: ask.get("discovery")}):
        return 2, [
            f"refused: the work type changed since the ask; propose again ({WORK_TYPE_RULE})"
        ]
    change = ["the one change in agk.toml:", "[delivery]", f'work_type = "{kind}"']
    personal = personal_table(root) is not None
    if personal or review_mode(root) != "solo" or reviewers.solo_person(root) is None:
        why = "your own change" if personal else "a team chooses by its own pull request"
        return 0, [f"printed only ({why}; setting: review_mode):", *change,
                   "with an ADR in the same pull request that names agk.toml"]  # fmt: skip
    branch = load_config(root)["default_branch"]
    base = f"origin/{branch}"
    if git_out(root, "rev-parse", "--verify", "--quiet", base).returncode:
        base = branch
    if git_out(root, "status", "--porcelain").stdout.strip():
        return 2, [
            "refused: the work tree has changes; nothing written (path class: the work tree)"
        ]
    if git_out(root, "rev-parse", "--verify", "--quiet", WORK_TYPE_BRANCH).returncode == 0:
        return 2, [f"refused: the branch {WORK_TYPE_BRANCH} already exists; nothing written"]
    code, said = steward.record(  # first: a memory that cannot be written writes nothing
        root, "Decision", f'work-type: yes, the person said "{words}" at {at}', steward.gh_api
    )
    if code:
        return code, said
    ask["open"] = False
    save_asks(root, asks)
    if git_out(root, "switch", "-q", "-c", WORK_TYPE_BRANCH, base).returncode:
        return 2, [f"refused: the branch {WORK_TYPE_BRANCH} cannot be made; nothing written"]
    toml = root / "agk.toml"
    toml.write_text(with_work_type(toml.read_text(encoding="utf-8"), kind), encoding="utf-8")
    rel = work_type_adr(root, ask, words, at)
    return 0, [
        f"wrote agk.toml and {rel} (Proposed) on {WORK_TYPE_BRANCH}; nothing committed or pushed",
        "run, then open the pull request; your merge is the approval:",
        f"git add agk.toml {rel}",
        f'git commit -m "The project\'s work type is {kind} (ADR-{rel[9:13]})"',
        f"git push -u origin {WORK_TYPE_BRANCH}",
    ]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="steward_owner.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("ask")
    a.add_argument("--qid", required=True)
    a.add_argument("--on", type=int)
    a.add_argument("--file", type=Path, required=True)
    a.add_argument("--target")  # brief #1690: with --line, one pinned pull request head
    a.add_argument("--line", type=Path)
    y = sub.add_parser("approve")
    y.add_argument("--ask", required=True)
    y.add_argument("--said", type=Path, required=True)
    y.add_argument("--at", required=True)
    y.add_argument("--by")
    r = sub.add_parser("relay")
    for name in ("--qid", "--answer", "--at"):
        r.add_argument(name, required=True)
    r.add_argument("--on", type=int, required=True)
    r.add_argument("--said", type=Path, required=True)
    r.add_argument("--conductor")
    p = sub.add_parser("park")
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--conductor")
    d = sub.add_parser("ready")
    d.add_argument("--plan", type=Path, required=True)
    d.add_argument("--trace", type=Path, required=True)
    d.add_argument("--session", required=True)
    d.add_argument("--start", action="store_true")
    k = sub.add_parser("defect")
    k.add_argument("--title", required=True)
    k.add_argument("--file", type=Path, required=True)
    k.add_argument("--refusals", type=int, default=5)
    k.add_argument("--post", action="store_true")
    sub.add_parser("defects")
    s = sub.add_parser("standard")  # SPEC-0072 rule 8 (brief #1601, ADR-0681)
    s.add_argument("--playbook")
    for name in ("confirm", "research"):
        c = sub.add_parser(name)
        c.add_argument("--said", type=Path, required=True)
        c.add_argument("--at", required=True)
        c.add_argument("--by" if name == "confirm" else "--describe", required=name == "research")
    r = sub.add_parser("draft")
    r.add_argument("--slug", required=True)
    r.add_argument("--layers", type=Path)  # brief #1842: a saved `layers.py --draft`
    f = sub.add_parser("fix-brief")  # brief #1715 (ADR-0714)
    f.add_argument("--brief", type=int, required=True)
    f.add_argument("--file", type=Path, required=True)
    f.add_argument("--seen", required=True)
    b = sub.add_parser("file-brief")
    b.add_argument("--file", type=Path, required=True)
    b.add_argument("--title", required=True)
    b.add_argument("--said", type=Path)
    b.add_argument("--at")
    b.add_argument("--by")
    b.add_argument("--name")  # brief #1753: the short name the steward offered for this draft
    t = sub.add_parser("work-type")  # brief #1757 (ADR-0735)
    t.add_argument("--propose", action="store_true")
    t.add_argument("--yes", action="store_true")
    t.add_argument("--said", type=Path)
    t.add_argument("--at")
    t.add_argument("--by")
    w = sub.add_parser("reads")
    w.add_argument("--session")
    w.add_argument("--refused", action="store_true")
    opts = parser.parse_args(argv)
    try:
        root = repo_root()
    except CheckError:
        print(OUTSIDE_PROJECT)
        return 3
    try:
        if opts.command == "ask" and (opts.target is None) != (opts.line is None):
            code, lines = 2, ["refused: --target and --line go together (setting: --target)"]
        elif opts.command == "ask" and opts.target is not None:
            text = opts.file.read_text(encoding="utf-8")
            code, lines = ask_target(
                root, opts.qid, opts.target, text, opts.line, datetime.now(UTC)
            )
        elif opts.command == "ask" and opts.on is None:
            code, lines = 2, ["refused: --on or --target names where the question goes"]
        elif opts.command == "ask":
            code, lines = ask(root, opts.qid, opts.on, opts.file.read_text(encoding="utf-8"))
        elif opts.command == "approve":
            code, lines = approve(root, opts.ask, opts.said, opts.at, opts.by, datetime.now(UTC))
        elif opts.command == "relay":
            code, lines = relay(root, opts)
        elif opts.command == "park":
            code, lines = park(root, opts.pr, opts.conductor, datetime.now(UTC))
        elif opts.command == "defect":
            code, lines = defect(root, opts)
        elif opts.command == "defects":
            code, lines = defects(root)
        elif opts.command == "standard":
            code, lines = standard_screen(root, opts.playbook)
        elif opts.command == "confirm":
            code, lines = confirm(root, opts.said, opts.at, opts.by, steward.gh_api)
        elif opts.command == "research":
            code, lines = research(root, opts.said, opts.at, opts.describe, steward.gh_api, len)
        elif opts.command == "draft":
            code, lines = draft(root, opts.slug, opts.layers)
        elif opts.command == "fix-brief":
            code, lines = fix_brief(root, opts.brief, opts.file, opts.seen)
        elif opts.command == "file-brief":
            code, lines = file_brief(
                root,
                opts.file,
                opts.title,
                opts.said,
                opts.at,
                opts.by,
                datetime.now(UTC),
                name=opts.name,
            )
        elif opts.command == "work-type" and opts.propose != opts.yes:
            if opts.propose:
                code, lines = work_type_propose(root, datetime.now(UTC))
            elif opts.said is None or opts.at is None:
                code, lines = 2, ["refused: --yes takes --said and --at (setting: --said)"]
            else:
                code, lines = work_type_yes(root, opts.said, opts.at, opts.by, datetime.now(UTC))
        elif opts.command == "work-type":
            code, lines = 2, ["refused: one of --propose or --yes (setting: work-type)"]
        elif opts.command == "reads":
            code, lines = reads(root, opts.session, opts.refused)
        else:
            code, lines = ready(root, opts)
    except steward.Unreadable as exc:
        print(f"error: {exc} cannot be read", file=sys.stderr)
        return 4
    except (CheckError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    if lines:
        print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
