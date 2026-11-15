"""The steward's evidence rule, answer form, stage and triage (SPEC-0059 rules 2, 3, 4, 6, 7, 9, 12
and 19; brief #1321, ADR-0558).

Usage: python3 scripts/agk/steward_evidence.py stage [--date YYYY-MM-DD]
       python3 scripts/agk/steward_evidence.py settle --question FILE [--stage STAGE]
       python3 scripts/agk/steward_evidence.py answer --question FILE --number N [--recheck FILE]
       python3 scripts/agk/steward_evidence.py triage --finding FILE
       python3 scripts/agk/steward_evidence.py skill --step STEP

The steward reads the sources; this script applies the rule to what it read. A question file is
JSON: `id` (Q-...), `class` (one of CLASSES), optional `changes` (of scope, date, cost, signoff),
`reverses` (true when the answer reverses an owner decision), `findings` (each `source` 1 to 5 of
rule 3's order, `answer`, `place`, `rule`) and `ranking` (`source` and `place` of an earlier
decision that ranks disagreeing sources). `stage` prints the stage in the owner's words, read from
the files and one GET of the open `agk-conductor` issue (never in personal mode). `settle` prints
the `Answer:` comment (exit 0) or `owner: <reason>` with the recommendation and any `Gap:` to record
(exit 3); `answer` posts that one comment on issue or pull request N, and nothing when the question
goes to the owner. A requirement answer is posted only when the fresh reviewer's answer
(`--recheck`, JSON `answer`; build (d), ADR-0560) agrees; otherwise both go to the owner, as does a
class the owner overrode twice in seven days (`steward_daily.py`). `triage` judges one finding
(JSON: `id`, `triage`, `why`, `text`, optional `cause` and `reproduced`): exit 0 with `file`,
`draft` or `ask` and its `Triage:` entry, 2 when refused, naming the setting or list, never the
value. `skill` prints the step's skill from the agent file's table, or `no skill:` and one kit brief
to file (exit 3). Exit 4: GitHub unread.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, personal_table, read_list, repo_root, utf8_output  # noqa: E402

SOURCES = (
    "owner decision",
    "Approved spec or requirement",
    "signed-off prototype",
    "source document",
    "AGK rule or code",
)
OWNER_CLASSES = frozenset({"business", "scope", "date", "cost", "signoff"})
CLASSES = OWNER_CLASSES | {"technical", "requirement"}
STAGES = (
    "start",
    "vision and discovery",
    "scope",
    "prototype and design",
    "stack and technical design",
    "plan",
    "build",
)
TRIAGES = ("kit brief", "kit correction", "kit question", "project brief", "owner question")
MODES = re.compile(r"^Modes: github \S.*; local \S.*; personal \S", re.M)
OWNER_LINE = re.compile(r'^Owner said \(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z\): ".+"', re.M)
PRIORITY = re.compile(r"^Priority: ([0-3])\s*$", re.M)
CONDUCTOR = "repos/{owner}/{repo}/issues?labels=agk-conductor&state=open&per_page=1"
AGENT = Path(".claude") / "agents" / "steward.md"
WHO = "Who: AGK steward"


def building(stage: str) -> bool:
    return stage == "build"


def stage_of(root: Path, today: date, conductor_open: bool) -> str:
    """Rule 2, Q-S0059-10: the newest stage whose record is on disk; build once a conductor runs."""
    from front_door import phase_of

    exists = lambda rel: (root / rel).is_file()  # noqa: E731
    if conductor_open:
        return "build"
    if exists("docs/plan/milestones.md") or exists("docs/plan/scope-lock.md"):
        return "plan"
    if any((root / "docs" / "adr").glob("*-stack-options.md")):
        return "stack and technical design"
    names = sorted(p.stem for p in (root / "docs" / "discovery").glob("*.md"))
    if any(phase_of(root, n, today).startswith(("phase 4", "phase 5")) for n in names):
        return "prototype and design"
    if exists("docs/plan/scope.md"):
        return "scope"
    return "vision and discovery" if names else "start"


def checked(question: object) -> dict:
    """The question file's fields, refused naming the field, never the value."""
    if not isinstance(question, dict) or not re.fullmatch(r"Q-[\w-]+", str(question.get("id"))):
        raise CheckError("the question is refused (field: id)")
    if question.get("class") not in CLASSES:
        raise CheckError("the question is refused (field: class)")
    for item in question.get("findings", []):
        if not (
            isinstance(item, dict) and item.get("source") in range(1, 6) and item.get("answer")
        ):
            raise CheckError("the question is refused (field: findings)")
    return question


def one_line(text: object) -> str:
    return " ".join(str(text).split())


def settle(
    question: dict, stage: str, recheck: dict | None = None, warned: frozenset | set = frozenset()
) -> dict:
    """Rule 3: the first source that answers wins; its negative cases and authority by stage."""
    question = checked(question)
    qid, cls, findings = question["id"], question["class"], question.get("findings", [])
    findings = sorted(findings, key=lambda f: f["source"])
    answers = {one_line(f["answer"]) for f in findings}
    out = {"to": "owner", "line": None, "recommendation": None, "evidence": None, "gap": False}
    out["class"] = cls
    ranking = question.get("ranking")
    if len(answers) > 1 and isinstance(ranking, dict):
        findings = [f for f in findings if f["source"] == ranking.get("source")]
    win = findings[0] if findings and len({one_line(f["answer"]) for f in findings}) == 1 else None
    if win:
        place = f"{SOURCES[win['source'] - 1]} {one_line(win.get('place', ''))}"
        if len(answers) > 1:
            place += f"; ranking {one_line((ranking or {}).get('place', ''))}"
        out["evidence"] = place
        out["recommendation"] = one_line(win["answer"])
    requirement = cls == "requirement" or (win is not None and win["source"] in (2, 3, 4))
    if cls in OWNER_CLASSES or set(question.get("changes", [])) & OWNER_CLASSES:
        reason = "it changes scope, a date, a cost or what the customer signs off"
    elif question.get("reverses"):
        reason = "it reverses an earlier owner decision"
    elif cls in warned:
        reason = "the owner overrode this class twice in seven days (rule 3)"
    elif building(stage) and cls == "requirement" and not any(f["source"] < 5 for f in findings):
        reason, out["gap"] = "a planning gap: nothing the plan decided names it", True
        out["record"] = f"Gap: {qid} {reason} (stage: {stage})"
    elif win is None:
        reason = "sources disagree with no ranking" if answers else "no source answers it"
    elif requirement and not building(stage):
        reason = "a requirement question in planning goes to the owner"
    elif requirement and not (second := (recheck or {}).get("answer")):
        reason = "a requirement answer needs the fresh re-check (rule 13)"
    elif requirement and norm(second) != norm(win["answer"]):
        reason = (
            f"the re-check disagrees: steward {one_line(win['answer'])}; "
            f"re-check {one_line(second)}"
        )
    else:
        out["to"], reason = "answer", f"settled by source {win['source']} of rule 3"
        out["line"] = (
            f"Answer: {qid} {out['recommendation']} (evidence: {place}; "
            f"rule: {one_line(win.get('rule', ''))})"
        )
    out["reason"] = reason
    return out


def norm(text: object) -> str:
    return one_line(text).casefold().rstrip(".")


def answer_body(found: dict) -> str:
    return f"{found['line']}\nClass: {found['class']}\n\n{WHO}\n"


def owner_lines(found: dict) -> list[str]:
    lines = [f"owner: {found['reason']}"]
    if found["recommendation"]:
        lines.append(f"recommendation: {found['recommendation']} (evidence: {found['evidence']})")
    return lines + ([f"record: {found['record']}"] if found["gap"] else [])


def conductor_open(root: Path, gh) -> bool:
    if personal_table(root) is not None:
        return False
    listed = gh("GET", CONDUCTOR)
    if listed is None:
        from steward import Unreadable

        raise Unreadable("issues")
    return bool(listed)


def answer(
    root: Path, question: dict, number: int, gh, today: date, recheck: dict | None = None
) -> tuple[int, list[str]]:
    """Rules 4, 13 and 18: one comment, only for a question the steward may answer."""
    from steward import load_cache
    from steward_daily import warned

    now = datetime.combine(today, datetime.min.time(), UTC)
    classes = warned(load_cache(root).get("comments", []), now)  # the start's cache: no call
    found = settle(question, stage_of(root, today, conductor_open(root, gh)), recheck, classes)
    if found["to"] != "answer":
        return 3, owner_lines(found)
    posted = gh(
        "POST", f"repos/{{owner}}/{{repo}}/issues/{number}/comments", {"body": answer_body(found)}
    )
    return (
        (0, [found["line"]]) if posted is not None else (4, ["error: comments cannot be written"])
    )


def neutral(text: str, root: Path) -> str | None:
    """check_neutrality.py's list on a text: the token's number, never its value; fail closed."""
    try:
        tokens = [t.lower() for t in read_list((root / "config/neutrality.txt").read_text("utf-8"))]
    except (OSError, UnicodeDecodeError):
        return "config/neutrality.txt cannot be read"
    hits = [n for n, t in enumerate(tokens, 1) if t in text.lower()]
    return f"token #{hits[0]} of config/neutrality.txt" if hits else None


def triage(item: dict, root: Path) -> dict:
    """Rules 6, 7 and 12: one triage per finding, and a filing only when every check passes."""
    from check_brief import body_problems

    from config import steward_settings

    choice, text = item.get("triage"), str(item.get("text", ""))
    entry = f"Triage: {item.get('id')} {choice}: {one_line(item.get('why', ''))}"
    refused = lambda why: {"action": "refused", "lines": [f"refused: {why}"], "entry": None}  # noqa: E731
    if choice not in TRIAGES:
        return refused("not one triage of rule 6 (setting: the triage)")
    if choice == "owner question":
        return {"action": "ask", "lines": ["ask: the owner, in one plain sentence"], "entry": entry}
    if not MODES.search(text):
        return refused(
            "no `Modes: github <effect>; local <effect>; personal <effect>` line (rule 7)"
        )
    if item.get("cause") and not str(item.get("reproduced", "")).strip():
        return refused("the cause is not reproduced on the default branch (rule 7)")
    kit = choice.startswith("kit")
    if choice.endswith("brief"):
        try:
            problems = body_problems(text, None if kit else root, None)
        except CheckError as exc:
            problems = [str(exc)]
        if problems:
            return refused(f"check_brief: {problems[0]}")
    if hit := neutral(text, root):
        return refused(f"check_neutrality: {hit}")
    priority = PRIORITY.search(text) if choice.endswith("brief") else None
    auto = steward_settings(root)["auto_file"]
    within = priority and auto is not False and int(priority[1]) <= auto
    if not within and not OWNER_LINE.search(text):
        return refused(
            "filing needs the owner's word above [steward] auto_file (setting: steward.auto_file)"
        )
    if kit and not (root / "kit" / "manifest.json").is_file():
        line = "draft: for the owner; nothing goes to the kit from a project before build (e)"
        return {"action": "draft", "lines": [line], "entry": entry}
    return {
        "action": "file",
        "lines": [f"file: {choice} (skill: `brief` or `issue`)"],
        "entry": entry,
    }


def skills(root: Path) -> dict[str, str]:
    """Rule 19: the stage-to-skill table of the agent file, the one copy."""
    rows = re.findall(
        r"^\| ([^|`][^|]*?) \| (`[^|]+?) \|$", (root / AGENT).read_text("utf-8"), re.M
    )
    return {step: skill for step, skill in rows}


def skill_line(root: Path, step: str) -> str:
    table = skills(root)
    found = table.get(step) or next((s for k, s in table.items() if step in k.split(" and ")), None)
    if found:
        return f"skill: {found}"
    return f"no skill: do `{step}` once by hand and triage one kit brief for the missing skill"


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(
        prog="steward_evidence.py", description=__doc__.split("\n\n")[0]
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stage").add_argument("--date")
    settle_p = sub.add_parser("settle")
    settle_p.add_argument("--question", type=Path, required=True)
    settle_p.add_argument("--stage", choices=STAGES)
    answer_p = sub.add_parser("answer")
    answer_p.add_argument("--question", type=Path, required=True)
    answer_p.add_argument("--number", type=int, required=True)
    answer_p.add_argument("--recheck", type=Path)
    sub.add_parser("triage").add_argument("--finding", type=Path, required=True)
    sub.add_parser("skill").add_argument("--step", required=True)
    opts = parser.parse_args(argv)
    from steward import Unreadable, gh_api

    root, today = repo_root(), datetime.now(UTC).date()
    try:
        if opts.command == "skill":
            line = skill_line(root, opts.step)
            print(line)
            return 3 if line.startswith("no skill") else 0
        if opts.command == "stage":
            when = date.fromisoformat(opts.date) if opts.date else today
            print(f"stage: {stage_of(root, when, conductor_open(root, gh_api))}")
            return 0
        if opts.command == "triage":
            found = triage(json.loads(opts.finding.read_text(encoding="utf-8")), root)
            print(
                "\n".join(
                    found["lines"] + ([f"record: {found['entry']}"] if found["entry"] else [])
                )
            )
            return 2 if found["action"] == "refused" else 0
        question = json.loads(opts.question.read_text(encoding="utf-8"))
        if opts.command == "answer":
            recheck = json.loads(opts.recheck.read_text("utf-8")) if opts.recheck else None
            code, lines = answer(root, question, opts.number, gh_api, today, recheck)
            print("\n".join(lines))
            return code
        stage = opts.stage or stage_of(root, today, conductor_open(root, gh_api))
        found = settle(question, stage)
        print(answer_body(found) if found["to"] == "answer" else "\n".join(owner_lines(found)))
        return 0 if found["to"] == "answer" else 3
    except Unreadable as exc:
        print(f"error: {exc} cannot be read", file=sys.stderr)
        return 4
    except (CheckError, OSError, ValueError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
