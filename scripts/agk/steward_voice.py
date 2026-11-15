"""The steward's voice: short, well-formatted pointers (brief #1382, ADR-0582; REQ-069 AC2).

Usage: python3 scripts/agk/steward_voice.py check FILE
       python3 scripts/agk/steward_voice.py choose FILE
       python3 scripts/agk/steward_voice.py form FILE
       python3 scripts/agk/steward_voice.py confirm FILE --answers FILE
       python3 scripts/agk/steward_voice.py shortened --rules N[,N]

`check` reads a reply the steward is about to give a person and prints one line per broken rule
of ADR-0582, naming the rule and never the text, exit 1, or `voice: ok`, exit 0: rule 1, the
first line is an ask or an answer, not a heading or a greeting only; rule 2, at most 5 bullets,
12 lines and 100 characters a line; rule 3, more than three choices only with a "more"; rule 4,
a decision names its recommendation; rule 5, a status is three lines (done, in progress, waiting
on you); rule 8, no kit term (the planted list of SPEC-0059 rule 5). `choose` renders a decision
(JSON: decision, options of label with an optional score, group or ruled_out, recommend,
because, and an optional sharper `ask`) as rule 4's one shape with at most three choices: it
drops what the evidence rules out and says how many, groups kinds, keeps the best three by score
with "say more for N other options", or asks the one sharper question. `form` renders up to five
inputs as one short form with each default filled in, and `confirm` plays the answers back in at
most three lines. `shortened` records one `Shortened:` marker in the steward's memory, which the
daily list counts. No network but `shortened`'s one post, no model.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import repo_root, utf8_output  # noqa: E402

ADR = "ADR-0582"
MAX_BULLETS, MAX_LINES, MAX_WIDTH, MAX_CHOICES, MAX_FIELDS = 5, 12, 100, 3, 5
SEP = " · "
LETTERS = "ABCDEFGH"
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
GREETING = re.compile(
    r"^(?:hi|hello|hey|sure|okay|ok|great|thanks|thank you|great question|good question|"
    r"certainly|of course|absolutely|happy to help)\b[\s!.,]*$",
    re.IGNORECASE,
)
LETTERED = re.compile(r"^\s*(?:[-*•]\s+)?\(?([A-H])[).:]?\s+\S")
OPTIONS = re.compile(r"Options: (.*?)(?: · |$)", re.M)
STATUS = ("Done:", "In progress:", "Waiting on you:")


def kit_terms() -> re.Pattern:
    from steward_owner import KIT_TERMS

    return KIT_TERMS


def choices(text: str) -> int:
    """The lettered choices on screen: the longest run A, B, C... or the parts of `Options:`."""
    seen = {m[1] for line in text.splitlines() if (m := LETTERED.match(line))}
    run = 0
    while run < len(LETTERS) and LETTERS[run] in seen:
        run += 1
    parts = max((len(m.split(" / ")) for m in OPTIONS.findall(text)), default=0)
    return max(run, parts)


def problems(text: str) -> list[str]:
    """Each broken rule of ADR-0582, naming the rule, never the text."""
    rows = [line for line in text.splitlines() if line.strip()]
    out = []
    first = rows[0].strip() if rows else ""
    if not first or first.startswith("#") or GREETING.match(first):
        out.append(f"voice: rule 1: the first line is not an ask or an answer ({ADR})")
    if sum(1 for line in rows if BULLET.match(line)) > MAX_BULLETS:
        out.append(f"voice: rule 2: more than {MAX_BULLETS} bullets ({ADR})")
    if len(rows) > MAX_LINES:
        out.append(f"voice: rule 2: more than {MAX_LINES} lines; link the rest ({ADR})")
    if any(len(line) > MAX_WIDTH for line in rows):
        out.append(f"voice: rule 2: a line over {MAX_WIDTH} characters ({ADR})")
    many = choices(text)
    if many > MAX_CHOICES and not re.search(r"\bmore\b", text, re.IGNORECASE):
        out.append(f"voice: rule 3: more than {MAX_CHOICES} choices without a more ({ADR})")
    decision = "Decision:" in text or many >= 2
    if decision and not re.search(r"\brecommend", text, re.IGNORECASE):
        out.append(f"voice: rule 4: a decision without a recommendation ({ADR})")
    if first.startswith(STATUS[0]) and (
        len(rows) != 3 or any(not r.startswith(s) for r, s in zip(rows, STATUS, strict=False))
    ):
        out.append(f"voice: rule 5: a status is three lines: {', '.join(STATUS)} ({ADR})")
    if kit_terms().search(text):
        out.append("voice: rule 8: a kit term (setting: the plain-words list, SPEC-0062 rule 5)")
    return out


def shape(parts: list[str]) -> str:
    """Rule 4's one shape: one line when it fits, else one line per part."""
    line = SEP.join(parts)
    return line if len(line) <= MAX_WIDTH else "\n".join(parts)


def reply_letters(n: int) -> str:
    names = list(LETTERS[:n])
    return names[0] if n == 1 else f"{', '.join(names[:-1])} or {names[-1]}"


def choose(data: dict) -> str:
    """A decision with at most three choices on screen, one recommended (rule 3)."""
    what, because = data["decision"], data.get("because", "")
    options = list(data.get("options", []))
    kept = [o for o in options if not o.get("ruled_out")]
    dropped = len(options) - len(kept)
    note = [f"Dropped {dropped} options the evidence rules out"] if dropped else []
    head = f"Decision: {what}"
    if len(kept) > MAX_CHOICES and all(o.get("group") for o in kept):
        groups: dict[str, int] = {}
        for o in kept:
            groups[o["group"]] = groups.get(o["group"], 0) + 1
        listed = ", ".join(f"{n} {g}" for g, n in groups.items())
        return shape(
            [
                head,
                listed,
                *note,
                f"I recommend {data['recommend']} because {because}",
                "Reply with which group to open",
            ]
        )
    if len(kept) > MAX_CHOICES and data.get("ask") and not any("score" in o for o in kept):
        ask = data["ask"]
        return shape(
            [
                head,
                f"{ask['question']} ({' / '.join(ask['choices'])})",
                *note,
                f"I recommend {ask['recommend']} because {ask['because']}",
                f"Reply {' or '.join(ask['choices'])}",
            ]
        )
    more = []
    if len(kept) > MAX_CHOICES:
        ranked = sorted(kept, key=lambda o: -float(o.get("score", 0)))
        shown = ranked[:MAX_CHOICES]
        if not any(o["label"] == data["recommend"] for o in shown):
            shown[-1] = next(o for o in kept if o["label"] == data["recommend"])
        more = [f"say more for {len(kept) - len(shown)} other options"]
        kept = shown
    letter = {o["label"]: LETTERS[n] for n, o in enumerate(kept)}
    listed = " / ".join(f"{letter[o['label']]} {o['label']}" for o in kept)
    pick = data["recommend"]
    return shape(
        [
            head,
            f"Options: {listed}",
            *note,
            f"I recommend {letter.get(pick, '')} {pick} because {because}".replace("  ", " "),
            *more,
            f"Reply {reply_letters(len(kept))}",
        ]
    )


def form(fields: list[dict]) -> str:
    """Rule 7: one short form of up to five inputs, each default filled in."""
    if not fields or len(fields) > MAX_FIELDS:
        raise ValueError(f"a form holds 1 to {MAX_FIELDS} inputs; ask in two forms ({ADR} rule 7)")
    rows = [f"{len(fields)} answers needed; reply yes to accept these, or change a line:"]
    for f in fields:
        extra = (
            f" (or {' / '.join(c for c in f['choices'] if c != f['default'])})"
            if f.get("choices")
            else ""
        )
        rows.append(f"- {f['name']}: {f['default']}{extra}")
    return "\n".join(rows)


def confirm(fields: list[dict], answers: dict) -> str:
    """Rule 7: the answers played back in at most three lines."""
    pairs = [f"{f['name']}: {answers.get(f['name'], f['default'])}" for f in fields]
    rows, line = [], "Noted:"
    for pair in pairs:
        piece = f"{line} {pair}" if line == "Noted:" else f"{line}{SEP}{pair}"
        if len(piece) > MAX_WIDTH and line != "Noted:":
            rows.append(line)
            line = pair
        else:
            line = piece
    rows.append(line)
    if len(rows) > 3:
        raise ValueError(f"the play-back is over three lines ({ADR} rule 7)")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="steward_voice.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "choose", "form"):
        sub.add_parser(name).add_argument("file", type=Path)
    con = sub.add_parser("confirm")
    con.add_argument("file", type=Path)
    con.add_argument("--answers", type=Path, required=True)
    sub.add_parser("shortened").add_argument("--rules", required=True)
    opts = parser.parse_args(argv)
    try:
        if opts.command == "shortened":
            import steward

            if not re.fullmatch(r"\d(?:\s*,\s*\d)*", opts.rules.strip()):
                raise ValueError("--rules takes rule numbers, as 2,3")
            rules = ", ".join(r.strip() for r in opts.rules.split(",") if r.strip())
            try:
                code, lines = steward.write(
                    repo_root(), f"Shortened: steward reply (voice rules {rules})", steward.gh_api
                )
            except steward.Unreadable as exc:
                print(f"error: {exc} cannot be read", file=sys.stderr)
                return 4
            print("\n".join(lines))
            return code
        text = opts.file.read_text(encoding="utf-8")
        if opts.command == "check":
            found = problems(text)
            print("\n".join(found) if found else "voice: ok")
            return 1 if found else 0
        data = json.loads(text)
        if opts.command == "choose":
            print(choose(data))
        elif opts.command == "form":
            print(form(data))
        else:
            print(confirm(data, json.loads(opts.answers.read_text(encoding="utf-8"))))
    except (OSError, ValueError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
