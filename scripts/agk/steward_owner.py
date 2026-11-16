"""The steward's owner question, its relay, its parking and its start of the conductor (SPEC-0059
rules 2, 5, 10 and 14; brief #1322, ADR-0559).

Usage: python3 scripts/agk/steward_owner.py ask --qid Q --on N --file FILE
       python3 scripts/agk/steward_owner.py relay --qid Q --on N --answer TEXT --said FILE --at TIME
                                           [--conductor ID]
       python3 scripts/agk/steward_owner.py park --pr N [--conductor ID]
       python3 scripts/agk/steward_owner.py ready --plan FILE --trace FILE --session ID [--start]
       python3 scripts/agk/steward_owner.py defect --title TEXT --file FILE [--refusals N] [--post]
       python3 scripts/agk/steward_owner.py defects
       python3 scripts/agk/steward_owner.py reads [--session ID] [--refused]

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
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard_logs  # noqa: E402
import launch  # noqa: E402
import session  # noqa: E402
import steward  # noqa: E402
from common import CheckError, personal_table, repo_root, utf8_output  # noqa: E402
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
    """Remove the owner wait's `agk:parked` on #N when the wait set it, and tell the conductor."""
    pull = session.gh(f"repos/{repo}/pulls/{number}")
    comments = session.gh(f"repos/{repo}/issues/{number}/comments?per_page=100")
    if not isinstance(pull, dict) or not isinstance(comments, list):
        return []  # a brief, or unreadable: the conductor's sweep unparks it
    if session.PARKED_LABEL not in session.labels_of(pull) or session.own_park(comments) is None:
        return []
    if not session.unpark_pull(repo, number, qid):
        raise CheckError(f"#{number} could not be unparked")
    return [f"unparked #{number} {qid}", *tell(root, conductor, number, qid)]


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
    comments = session.gh(f"repos/{repo}/issues/{number}/comments?per_page=100")
    if not isinstance(pull, dict) or not isinstance(comments, list):
        raise steward.Unreadable(f"#{number}")
    listed, answerers = session.owner_people(root, pull)
    settings = session.owner_wait_settings(root)
    found = session.owner_step(pull, comments, settings, now, listed, answerers)
    if found and found[0] == "park" and session.park_pull(repo, number, found[1]):
        return 0, [f"parked #{number} {found[1]}"]
    if found and found[0] == "unpark" and session.unpark_pull(repo, number, found[1]):
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
        {k: guard_logs.redact(json.dumps(x[k]) if k == "error" else str(x[k]), patterns)[0]
         for k in keep if k in x}  # fmt: skip
        for x in out[-count:] if count > 0
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
            capture_output=True, text=True, timeout=60, check=False,
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


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="steward_owner.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("ask")
    a.add_argument("--qid", required=True)
    a.add_argument("--on", type=int, required=True)
    a.add_argument("--file", type=Path, required=True)
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
    w = sub.add_parser("reads")
    w.add_argument("--session")
    w.add_argument("--refused", action="store_true")
    opts = parser.parse_args(argv)
    root = repo_root()
    try:
        if opts.command == "ask":
            code, lines = ask(root, opts.qid, opts.on, opts.file.read_text(encoding="utf-8"))
        elif opts.command == "relay":
            code, lines = relay(root, opts)
        elif opts.command == "park":
            code, lines = park(root, opts.pr, opts.conductor, datetime.now(UTC))
        elif opts.command == "defect":
            code, lines = defect(root, opts)
        elif opts.command == "defects":
            code, lines = defects(root)
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
