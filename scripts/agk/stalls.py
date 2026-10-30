"""stalls.py: one read-only list of every stall, each with its cause and its fix (brief #367).

    python3 scripts/agk/stalls.py [--json]

It prints one line per stall of the project's pull requests and sessions,
`stall <kind> #<n>: <cause>; fix: <one plain step>`, or `no stall`; `--json` gives the same as
data. Exit 0 with no stall, 3 with any, 1 when the repository cannot be read (the message names
the rule, never a value), 2 for a usage error. It reads with `gh api` GET only, writes nothing,
posts nothing and runs no model (ADR-0205, REQ-040).

The kinds are the rows of `KINDS`, each with how it is detected, its cause line and its fix line.
The reads are those of `route.py` (the facts of a pull request and its one label, `decide`, the
judged required checks) and of `session.py` and `session_plan.py` (the takes, the plan of the
sessions to start), imported and unchanged, so the plan, the router and the stalls never disagree.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, repo_root, required_checks
from route import FAILED_RUN, FAILED_STATUS, decide, judged, listing, read_facts
from session import (
    CLAIM_HOURS,
    all_takes,
    flow_int,
    gh,
    is_red,
    live_takes,
    moment,
    pages,
    repo_name,
)
from session_plan import conductor_comments, fits, own_posts

USAGE = "usage: stalls.py [--json]"
LABEL = "agk-brief"


@dataclass(frozen=True)
class Kind:
    name: str
    minutes: int | None  # the limit; None when the kind has none
    detected: str
    cause: str
    fix: str


KINDS = (
    Kind(
        "stale-label",
        10,
        "the required checks of the head are green and `agk:ci-running` has stayed on the pull "
        "request for more than 10 minutes since they finished and since the label was set",
        "its required checks are green but agk:ci-running has stayed on it for {age}",
        "relabel it with python3 scripts/agk/route.py --pr {n}, or re-run the agk-route job",
    ),
    Kind(
        "no-verdict",
        30,
        "`agk:review` for more than 30 minutes, and the router's own reading finds no verdict "
        "that names the head",
        "it has waited at agk:review for {age} with no verdict that names its head",
        "the conductor reviews it and posts a Verdict: that names its head",
    ),
    Kind(
        "stuck-run",
        60,
        "the latest run of a required check is queued or in progress for more than 60 minutes "
        "since it started, or was cancelled with no newer run",
        "the required check {check} {state}",
        "re-run {check} from the Checks tab of the pull request, or push a new commit",
    ),
    Kind(
        "red-default",
        None,
        'the issue "The default branch is red" that the router writes is open',
        'the required checks of the default branch fail ("The default branch is red" is open)',
        "a builder takes brief #{n} first; python3 scripts/agk/session.py next offers it first",
    ),
    Kind(
        "idle-capacity",
        15,
        "the plan of `session.py plan` names sessions to start and no `taken:` was posted on an "
        "open brief for 15 minutes",
        "the plan starts {session} on it and {since}",
        "start a builder session that runs "
        "python3 scripts/agk/session.py claim --session {session} --brief {n}{build}",
    ),
    Kind(
        "claim-no-pr",
        120,
        "a live `taken:` with no pull request of its work and no `taken:`, `Progress:`, "
        "`Report:` or `Request:` by that session for 2 hours",
        "{session} took it and has opened no pull request and posted nothing for {age}",
        "{session} opens its draft pull request, or posts released: {session} on the brief "
        "to free it",
    ),
)
BY_NAME = {k.name: k for k in KINDS}


def age(delta: timedelta) -> str:
    minutes = max(0, int(delta.total_seconds() // 60))
    if minutes < 120:
        return f"{minutes} minute" + ("" if minutes == 1 else "s")
    hours = minutes // 60
    return f"{hours} hours" if hours < 48 else f"{hours // 24} days"


def over(kind: str, delta: timedelta) -> bool:
    limit = BY_NAME[kind].minutes
    return limit is not None and delta > timedelta(minutes=limit)


def stall(kind: str, n: int, **values: object) -> dict:
    row = BY_NAME[kind]
    return {
        "kind": kind,
        "number": n,
        "cause": row.cause.format(n=n, **values),
        "fix": row.fix.format(n=n, **values),
    }


def line(s: dict) -> str:
    return f"stall {s['kind']} #{s['number']}: {s['cause']}; fix: {s['fix']}"


def when(text: object) -> datetime | None:
    return moment(text) if text else None


def labelled_at(events: list, label: str) -> datetime | None:
    """When LABEL was last set on the issue, from its events."""
    times = [
        moment(e.get("created_at"))
        for e in events
        if isinstance(e, dict)
        and e.get("event") == "labeled"
        and (e.get("label") or {}).get("name") == label
    ]
    return max(times) if times else None


# --- the pull requests: stale-label, no-verdict, stuck-run --------------------------------------


def green_since(facts: dict) -> datetime | None:
    """When the required checks of the head all finished green, or None when they are not."""
    runs, statuses, missing = judged(facts["checks"], facts["statuses"], facts["required"])
    if missing or (not runs and not statuses):
        return None
    if any(r.get("status") != "completed" or r.get("conclusion") in FAILED_RUN for r in runs):
        return None
    if any(s.get("state") == "pending" or s.get("state") in FAILED_STATUS for s in statuses):
        return None
    times = [when(r.get("completed_at")) for r in runs]
    times += [when(s.get("updated_at") or s.get("created_at")) for s in statuses]
    known = [t for t in times if t is not None]
    return max(known) if known else None


def stuck(n: int, checks: list, required: list[str], now: datetime) -> list[dict]:
    runs, _, _ = judged(checks, [], required)
    out = []
    for r in sorted(runs, key=lambda x: str(x.get("name") or "")):
        name = str(r.get("name") or "")
        if r.get("status") == "completed":
            if r.get("conclusion") == "cancelled":
                state = "was cancelled and no newer run followed"
                out.append(stall("stuck-run", n, check=name, state=state))
            continue
        started = when(r.get("started_at"))
        if started is not None and over("stuck-run", now - started):
            word = "queued" if r.get("status") == "queued" else "in progress"
            state = f"has been {word} for {age(now - started)}"
            out.append(stall("stuck-run", n, check=name, state=state))
    return out


def pull_stalls(repo: str, root: Path, prs: list, now: datetime) -> list[dict]:
    required = required_checks(root)
    out: list[dict] = []
    for pr in sorted(prs, key=lambda p: p["number"]):
        n = pr["number"]
        labels = {str(x.get("name")) for x in pr.get("labels") or [] if isinstance(x, dict)}
        watched = labels & {"agk:ci-running", "agk:review"}
        if not watched:
            head = str((pr.get("head") or {}).get("sha") or "")
            checks = listing(f"repos/{repo}/commits/{head}/check-runs", "check_runs")
            if checks is None:
                raise CheckError(
                    "rule 2 (stuck-run): the checks of an open pull request cannot be read"
                )
            out += stuck(n, checks, required, now)
            continue
        got = read_facts(repo, n, root)
        events = pages(f"repos/{repo}/issues/{n}/events")
        if got is None or events is None:
            raise CheckError("rule 2 (stale-label, no-verdict): the facts of an open pull request "
                             "cannot be read")  # fmt: skip
        _, facts = got
        # route.read_facts reads a failed status as no status; a stall list must not (the verdict
        # on b0b3ef3, item 3), so the status of the head is read again and must be readable.
        status = gh(f"repos/{repo}/commits/{facts['head']}/status")
        if not isinstance(status, dict) or not isinstance(status.get("statuses", []), list):
            raise CheckError(
                "rule 2 (stale-label, no-verdict): the status of an open pull request "
                "cannot be read"
            )
        facts["statuses"] = status.get("statuses", [])
        out += stuck(n, facts["checks"], facts["required"], now)
        done = green_since(facts)
        if "agk:ci-running" in watched and done is not None:
            since = max(t for t in (done, labelled_at(events, "agk:ci-running")) if t is not None)
            if over("stale-label", now - since):
                out.append(stall("stale-label", n, age=age(now - since)))
        if "agk:review" in watched and decide(facts) == "agk:review":
            since = labelled_at(events, "agk:review") or done
            if since is not None and over("no-verdict", now - since):
                out.append(stall("no-verdict", n, age=age(now - since)))
    return out


# --- the briefs: red-default, claim-no-pr, idle-capacity ----------------------------------------


def brief_comments(repo: str, briefs: list) -> dict[int, list]:
    out = {}
    for b in briefs:
        found = pages(f"repos/{repo}/issues/{b['number']}/comments")
        if found is None:
            raise CheckError("rule 2 (claim-no-pr): the comments of an open brief cannot be read")
        out[b["number"]] = found
    return out


def claim_stalls(repo: str, root: Path, comments: dict, prs: list, now: datetime) -> list[dict]:
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 5)
    takes = {n: all_takes(c) for n, c in comments.items()}
    board: list | None = None
    out = []
    for n in sorted(comments):
        for t in live_takes(comments[n], n, prs, hours):
            name = t[2]
            moved = any(o != n and x[2] == name and x[0] > t[0] for o in takes for x in takes[o])
            if moved or any(fits(pr, n, t) for pr in prs):
                continue
            seen = [t[0]]
            for c in comments.values():
                seen += own_posts(c, name, True)
                seen += [x[0] for x in all_takes(c) if x[2] == name]
            if over("claim-no-pr", now - max(seen)):
                if board is None:
                    board = conductor_comments(repo)
                    if board is None:
                        raise CheckError(
                            "rule 2 (claim-no-pr): the conductor's issue cannot be read"
                        )
                seen += own_posts(board, name, True)
            if over("claim-no-pr", now - max(seen)):
                out.append(stall("claim-no-pr", n, session=name, age=age(now - max(seen))))
    return out


def idle_stalls(root: Path, comments: dict, now: datetime) -> list[dict]:
    from session_plan import build

    plan = build(root)
    # The plan skips a brief it cannot read; a stall list must not read that as no stall (the
    # verdict on b0b3ef3, items 1 and 2).
    if any("cannot be read" in str(s.get("why")) for s in plan["skipped"]):
        raise CheckError("rule 2 (idle-capacity): the plan cannot be read")
    if not plan["start"]:
        return []
    times = [t[0] for c in comments.values() for t in all_takes(c)]
    newest = max(times) if times else None
    if newest is not None and not over("idle-capacity", now - newest):
        return []
    since = (
        "no brief has been taken yet"
        if newest is None
        else f"no brief has been taken for {age(now - newest)}"
    )
    return [
        stall(
            "idle-capacity",
            s["brief"],
            session=s["session"],
            since=since,
            build=f" --build {s['build']}" if s.get("build") else "",
        )
        for s in plan["start"]
    ]


def find(root: Path) -> list[dict]:
    repo = repo_name(root)
    now = datetime.now(UTC)
    issues = pages(f"repos/{repo}/issues?state=open&labels={LABEL}")
    if issues is None:
        raise CheckError("rule 2 (red-default, claim-no-pr): the open briefs cannot be read")
    briefs = [i for i in issues if isinstance(i, dict) and "pull_request" not in i]
    prs = pages(f"repos/{repo}/pulls?state=all")
    if prs is None:
        raise CheckError(
            "rule 2 (stale-label, no-verdict, stuck-run): the pull requests cannot be read"
        )
    open_prs = [p for p in prs if p.get("state") == "open" and isinstance(p.get("number"), int)]
    found = pull_stalls(repo, root, open_prs, now)
    found += [stall("red-default", b["number"]) for b in briefs if is_red(b)]
    comments = brief_comments(repo, briefs)
    found += idle_stalls(root, comments, now)
    found += claim_stalls(repo, root, comments, prs, now)
    order = {k.name: i for i, k in enumerate(KINDS)}
    return sorted(found, key=lambda s: (order[s["kind"]], s["number"]))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in ([], ["--json"]):
        print(USAGE)
        return 2
    try:
        found = find(repo_root())
    except CheckError as exc:
        print(f"error: {exc}")
        return 1
    if args == ["--json"]:
        print(json.dumps({"stalls": found}, indent=2))
    else:
        print("\n".join(line(s) for s in found) if found else "no stall")
    return 3 if found else 0


if __name__ == "__main__":
    sys.exit(main())
