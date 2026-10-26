"""Facts: one JSON document that every derived feature reads (SPEC-0009).

Standard library only. The document goes to stdout; nothing is written to a file, no git command
changes anything, and GitHub is read only with `gh api --method GET` (or recorded files with
`--api-dir`). A value that could not be read is the string "unknown", never a default. The script
counts nothing the existing scripts count, judges nothing, and runs no test, no model and no check.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import check_adrs
import check_specs
import drift_audit
import metrics
import shadow_rate
from common import (
    REQ_ID,
    CheckError,
    declares_unchanged,
    find_ac_markers,
    find_questions,
    git,
    installed_version,
    load_config,
    log_lines,
    open_section_ids,
    parse_acceptance,
    parse_estimate,
    parse_requirements,
    ruled_in,
    run,
)

NAME = "facts"
SCHEMA = 1
UNKNOWN = "unknown"
USAGE = (
    "usage: facts.py [--today YYYY-MM-DD] [--repo OWNER/REPO] [--api-dir DIR] [--weeks N] [ROOT]"
)
REQUIREMENTS = "docs/requirements.md"
LOG = "docs/runs/decisions-log.md"
REGISTER = drift_audit.REGISTER
NOTES_FILE = re.compile(r"docs/runs/spec-\d{4}-notes\.md")
ORIGIN = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$")
SPEC_TITLE = re.compile(r"^# SPEC-\d{4}:\s*(.+?)\s*$")
SPEC_STATUSES = ("Draft", "Approved")
LABELS = ("agk-metrics", "agk-drift-audit", "agk-product-report")
BRIEF_LABEL = "agk-brief"
SHADOW_LABEL = "agk-shadow"
BRIEF_LINE = re.compile(r"Brief: #(\d+)")
TAKE_LINE = re.compile(
    r"taken: \S+ \d{4}-\d{2}-\d{2}(?: build \([A-Za-z0-9._-]+\))?( retakes)?( reserves .*)?"
)
ADVANCES = re.compile(r"Advances: (new|none|REQ-\d{3}(?:, REQ-\d{3})*)")
WAITING_ON_BUILDER = ("agk:fix", "agk:conflict", "agk:ci-red")
FLOW_DEFAULTS = {"max_builders": 3, "stall_hours": 4}
OUTCOMES = ("proven", "not-proven", "skipped", "unknown")
REASON = re.compile(r"(?!unknown$)[a-z]+(-[a-z]+)*")


# --- the git facts ----------------------------------------------------------------------------


def check_root(root: Path) -> None:
    if not root.is_dir():
        raise CheckError("ROOT is not a directory (path class: root)")
    inside = git(root, "rev-parse", "--is-inside-work-tree", check=False).strip()
    if inside != "true":
        raise CheckError("ROOT is not a git work tree (path class: root)")
    if not git(root, "rev-parse", "--verify", "-q", "HEAD", check=False).strip():
        raise CheckError("ROOT has no commit (path class: root)")


def dirty_of(root: Path) -> bool | str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return UNKNOWN
    return bool(proc.stdout.strip())


def repo_of(root: Path, given: str | None) -> str:
    if given:
        return given
    url = git(root, "remote", "get-url", "origin", check=False).strip()
    match = ORIGIN.search(url)
    return match.group(1) if match else UNKNOWN


# --- the configuration ------------------------------------------------------------------------


def config_present(root: Path) -> bool:
    if (root / "agk.toml").is_file():
        return True
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    return "agk" in data.get("tool", {})


def load_cfg(root: Path) -> dict | None:
    if not config_present(root):
        return None
    try:
        return load_config(root)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def config_section(cfg: dict | None) -> Any:
    if cfg is None:
        return UNKNOWN
    hours = cfg.get("inbox_hours")
    return {
        "default_branch": cfg["default_branch"],
        "test_dirs": list(cfg["test_dirs"]),
        "test_patterns": list(cfg["test_patterns"]),
        "inbox_hours": hours if isinstance(hours, int) and not isinstance(hours, bool) else UNKNOWN,
        "project_tests_declared": bool(str(cfg.get("project_tests") or "").strip()),
    }


# --- requirements and markers -----------------------------------------------------------------


def done_dates(root: Path) -> dict[str, str] | None:
    """The UTC date of the commit that last set each requirement's `Status:` to `done` (SPEC-0017).

    Read from the first-parent history of the checked-out branch, oldest first: a requirement is
    dated by the latest commit at which it is `done` and was not `done` in the commit before. A
    shallow history gives None: nothing is guessed from a cut-off past.
    """
    if git(root, "rev-parse", "--is-shallow-repository", check=False).strip() != "false":
        return None
    log = git(
        root,
        "log",
        "--first-parent",
        "--reverse",
        "--format=%H %cI",
        "--",
        REQUIREMENTS,
        check=False,
    )
    dates: dict[str, str] = {}
    before: dict[str, str | None] = {}
    for line in log.splitlines():
        sha, _, stamp = line.partition(" ")
        text = git(root, "show", f"{sha}:{REQUIREMENTS}", check=False)
        now = {r["id"]: r["status"] for r in parse_requirements(text)}
        for req_id, status in now.items():
            if status == "done" and before.get(req_id) != "done":
                moment = datetime.fromisoformat(stamp)
                dates[req_id] = moment.astimezone(UTC).date().isoformat()
        before = now
    return dates


def requirements_section(root: Path) -> Any:
    text = drift_audit.read(root, REQUIREMENTS)
    if text is None:
        return UNKNOWN
    dates = done_dates(root)
    found = []
    for req in parse_requirements(text):
        pairs = parse_acceptance(req["acceptance"] or "")
        ids = [ac for ac, _ in pairs]
        criteria: Any = [{"id": ac, "text": body} for ac, body in pairs]
        if len(set(ids)) != len(ids):
            criteria = UNKNOWN
        status = req["status"] if req["status"] in ("planned", "in-progress", "done") else UNKNOWN
        found.append(
            {
                "id": req["id"],
                "title": req["title"] or UNKNOWN,
                "status": status,
                "line": req["line"],
                "done_on": (dates or {}).get(req["id"], UNKNOWN) if status == "done" else None,
                "criteria": criteria,
                "criteria_form": "structured" if pairs else "unstructured",
            }
        )
    return sorted(found, key=lambda r: r["id"])


def markers_section(root: Path, cfg: dict | None) -> Any:
    if cfg is None:
        return UNKNOWN
    return find_ac_markers(root, cfg["test_dirs"], cfg["test_patterns"], [])


# --- specs, ADRs ------------------------------------------------------------------------------


def field_of(text: str, name: str) -> str | None:
    for line in text.splitlines():
        match = check_adrs.FIELD_RE.match(line)
        if match and match.group(1) == name:
            return match.group(2)
    return None


def sorted_reqs(value: str | None) -> list[str]:
    return sorted(set(REQ_ID.findall(value or "")))


def spec_records(root: Path) -> list[dict]:
    records = []
    for rel in drift_audit.docs(root, "specs"):
        text = drift_audit.read(root, rel) or ""
        number = Path(rel).name[:4]
        title = SPEC_TITLE.match(text.splitlines()[0]) if text.strip() else None
        status = check_specs.status_of(text)
        notes = f"docs/runs/spec-{number}-notes.md"
        records.append(
            {
                "id": f"SPEC-{number}",
                "path": rel,
                "title": title.group(1) if title else UNKNOWN,
                "status": status if status in SPEC_STATUSES else UNKNOWN,
                "requirements": sorted_reqs(field_of(text, "Requirements")),
                "notes": notes if (root / notes).is_file() else None,
            }
        )
    return records


def adr_records(root: Path) -> list[dict]:
    records = []
    for rel in drift_audit.docs(root, "adr"):
        name = Path(rel).name
        text = drift_audit.read(root, rel) or ""
        match = check_adrs.FILE_RE.match(name)
        if not match:
            continue
        first = text.splitlines()[0] if text.strip() else ""
        title = first.split(": ", 1)[1].strip() if check_adrs.TITLE_RE.match(first) else UNKNOWN
        status = check_adrs.status_of(text)
        date_text = field_of(text, "Date") or ""
        classes: list[str] = []
        for line in text.splitlines():
            if line.startswith("Protected classes:"):
                classes = re.findall(r"`([^`]+)`", line)
                break
        records.append(
            {
                "id": f"ADR-{match.group(1)}",
                "path": rel,
                "title": title,
                "status": status if status in check_adrs.STATUSES else UNKNOWN,
                "date": date_text if drift_audit.parse_date(date_text) else UNKNOWN,
                "amends": re.findall(r"ADR-\d{4}", field_of(text, "Amends") or ""),
                "requirements": sorted_reqs(field_of(text, "Requirements")),
                "protected_classes": classes,
            }
        )
    return records


# --- questions --------------------------------------------------------------------------------


def open_places(root: Path, specs: list[dict], adrs: list[dict]) -> tuple[set[str], set[str]]:
    """(the files that are open places as a whole, the notes files with an `## Open` section)."""
    whole = {s["notes"] for s in specs if s["status"] == "Draft" and s["notes"]}
    whole |= {a["path"] for a in adrs if a["status"] == "Proposed"}
    notes = {p.relative_to(root).as_posix() for p in (root / "docs/runs").glob("spec-*-notes.md")}
    return whole, {n for n in notes if NOTES_FILE.fullmatch(n)}


def questions_section(root: Path, specs: list[dict], adrs: list[dict]) -> Any:
    base = find_questions(root)
    if base is None:
        return UNKNOWN
    whole, notes = open_places(root, specs, adrs)
    open_ids = {
        n: open_section_ids((root / n).read_text(encoding="utf-8", errors="replace")) for n in notes
    }
    for spec in specs:
        if spec["status"] == "Draft":
            text = (root / spec["path"]).read_text(encoding="utf-8", errors="replace")
            open_ids[spec["path"]] = open_section_ids(text, "Open questions")
    return [
        {
            **record,
            "open_in": sorted(
                f
                for f in record["files"]
                if f in whole or (f in open_ids and record["id"] in open_ids[f])
            ),
        }
        for record in base
    ]


def open_questions_of(root: Path, spec: dict) -> Any:
    lines = log_lines(root)
    if lines is None:
        return UNKNOWN
    if not spec["notes"]:
        return []
    text = (root / spec["notes"]).read_text(encoding="utf-8", errors="replace")
    return sorted(q for q in open_section_ids(text) if ruled_in(lines, q) is False)


# --- residuals --------------------------------------------------------------------------------


def due_of(text: str) -> Any:
    match = drift_audit.DUE.search(text)
    if not match:
        return None
    return match.group(1) if drift_audit.parse_date(match.group(1)) else UNKNOWN


def residuals_section(root: Path, specs: list[dict], adrs: list[dict]) -> Any:
    register = drift_audit.read(root, REGISTER)
    if register is None:
        return UNKNOWN
    found: list[tuple[str, int, dict]] = []
    closed = drift_audit.closed_pairs(register)
    for rel in sorted(s["path"] for s in specs) + sorted(a["path"] for a in adrs):
        bullets = drift_audit.residual_bullets(drift_audit.read(root, rel) or "")
        for position, bullet in enumerate(bullets):
            body = bullet[2:]
            state = "closed" if drift_audit.is_closed(closed, rel, bullet) else "open"
            item = {"source": rel, "text": body, "due": due_of(body), "state": state}
            found.append((rel, position, item))
    for entry in drift_audit.register_lines(register):
        due = entry["due"].isoformat() if entry["due"] else UNKNOWN
        item = {"source": REGISTER, "text": entry["text"], "due": due, "state": "open"}
        found.append((REGISTER, entry["number"], item))
    for number, _source, body in drift_audit.closed_rows(register):
        item = {"source": REGISTER, "text": body, "due": None, "state": "closed"}
        found.append((REGISTER, number, item))
    return [item for _, _, item in sorted(found, key=lambda f: (f[0], f[1]))]


# --- GitHub -----------------------------------------------------------------------------------


def get_list(src: Any, name: str, endpoint: str, until: Any = None) -> list | None:
    if src is None:
        return None
    if isinstance(src, metrics.Gh):
        data = src.pages(endpoint.replace("{repo}", src.repo), until)
    else:
        data = src.get(name, endpoint)
    return data if isinstance(data, list) else None


def get_object(src: Any, name: str, endpoint: str) -> dict | None:
    if src is None:
        return None
    data = src.get(name, endpoint)
    return data if isinstance(data, dict) else None


def window_start(today: date, weeks: int) -> datetime:
    monday = today - timedelta(days=today.weekday()) - timedelta(days=7 * (weeks - 1))
    return metrics.start_of(monday)


def behaviour_of(body: Any) -> str | None:
    if body is None:
        return None
    if not isinstance(body, str):
        return UNKNOWN
    return "unchanged" if declares_unchanged(body) else None


def verdicts_of(comments: list | None, authors: list[str] | None = None) -> Any:
    if comments is None or (authors is not None and not authors):
        return UNKNOWN
    found = []
    for comment in sorted(comments, key=lambda c: (c.get("created_at") or "", c.get("id") or 0)):
        parsed = metrics.verdicts([comment], authors)
        if parsed:
            kind, sha = parsed[0]
            found.append({"kind": kind, "sha": sha or None, "at": comment.get("created_at")})
    return found


def proof_of(src: Any, head: str) -> tuple[str, Any]:
    """(outcome, reason) of the `proof` job on this head: the outcome step that succeeded.

    The reason is in parentheses in the name of a not-proven or unknown step (`outcome: not-proven
    (red-on-head)`). It is None for proven and skipped, and "unknown" when the name carries none
    (a run made before the names did) or the job could not be read.
    """
    runs = get_object(src, f"runs-{head}", f"repos/{{repo}}/actions/runs?head_sha={head}")
    if runs is None or not isinstance(runs.get("workflow_runs"), list):
        return UNKNOWN, UNKNOWN
    named = [r for r in runs["workflow_runs"] if r.get("name") == "proof"]
    if not named:
        return UNKNOWN, UNKNOWN
    latest = max(named, key=lambda r: (r.get("created_at") or "", r.get("id") or 0))
    jobs = get_object(
        src, f"jobs-{latest.get('id')}", f"repos/{{repo}}/actions/runs/{latest.get('id')}/jobs"
    )
    if jobs is None or not isinstance(jobs.get("jobs"), list):
        return UNKNOWN, UNKNOWN
    job = next((j for j in jobs["jobs"] if j.get("name") == "proof"), None)
    steps = job.get("steps") if isinstance(job, dict) else None
    if not isinstance(steps, list):
        return UNKNOWN, UNKNOWN
    won = [
        s["name"][len("outcome: ") :]
        for s in steps
        if str(s.get("name", "")).startswith("outcome: ") and s.get("conclusion") == "success"
    ]
    if len(won) != 1:
        return UNKNOWN, UNKNOWN
    outcome, _, rest = won[0].partition(" (")
    if outcome not in OUTCOMES:
        return UNKNOWN, UNKNOWN
    if outcome in ("proven", "skipped"):
        return outcome, None
    reason = rest[:-1] if rest.endswith(")") else ""
    return outcome, reason if REASON.fullmatch(reason) else UNKNOWN


def flow_limits(root: Path) -> dict[str, Any]:
    """`max_builders` and `stall_hours` of the flow table of agk.toml (3 and 4 by default); a
    value that is not a whole number, 1 or more, is unknown (SPEC-0034 rule 1, SPEC-0033 rule 5)."""
    try:
        data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {key: UNKNOWN for key in FLOW_DEFAULTS}
    table = data.get("flow", {})
    out: dict[str, Any] = {}
    for key, default in FLOW_DEFAULTS.items():
        value = table.get(key, default) if isinstance(table, dict) else default
        ok = isinstance(value, int) and not isinstance(value, bool) and value >= 1
        out[key] = value if ok else UNKNOWN
    return out


def brief_of(body: Any) -> Any:
    """The `n` of the line `Brief: #n` of a pull request body; None without one."""
    if not isinstance(body, str):
        return UNKNOWN
    for line in body.splitlines():
        if found := BRIEF_LINE.fullmatch(line.rstrip()):
            return int(found.group(1))
    return None


def taken_at(src: Any, brief: Any, created: Any) -> Any:
    """When the latest `taken:` comment of the brief before the pull request was posted."""
    if brief is None:
        return None
    if brief == UNKNOWN:
        return UNKNOWN
    comments = get_list(src, f"comments-{brief}", f"repos/{{repo}}/issues/{brief}/comments")
    if comments is None:
        return UNKNOWN
    when = [
        c["created_at"]
        for c in metrics.first_lines(comments, "taken:") or []
        if TAKE_LINE.fullmatch(c["body"].splitlines()[0].strip())
        and (metrics.stamp(c.get("created_at")) or datetime.max.replace(tzinfo=UTC))
        <= (metrics.stamp(created) or datetime.min.replace(tzinfo=UTC))
    ]
    return when[-1] if when else None


def gap(opened: Any, closed: Any) -> Any:
    """Hours between two moments: null when one did not happen, unknown when one cannot be read."""
    if UNKNOWN in (opened, closed):
        return UNKNOWN
    return None if opened is None or closed is None else metrics.hours_between(opened, closed)


def flow_hours(created: Any, taken: Any, verdicts: Any, merged: Any) -> dict[str, Any]:
    """The hours of the four steps of a pull request (SPEC-0034 rule 10)."""
    if verdicts == UNKNOWN:
        first = cleared = UNKNOWN
    else:
        first = verdicts[0]["at"] if verdicts else None
        cleared = next((v["at"] for v in verdicts if v["kind"] == "cleared"), None)
    return {
        "taken_to_pull_request": gap(taken, created),
        "to_first_verdict": gap(created, first),
        "verdict_to_cleared": gap(first, cleared),
        "cleared_to_merge": gap(cleared, merged),
    }


def stalled_of(item: dict, comments: Any, commits: Any, hours: Any, today: date, cleared: Any):
    """Whether work that waits on its builder has not changed for `stall_hours` (SPEC-0033 rule 5):
    a draft or a label agk:fix, agk:conflict or agk:ci-red, and a head that is not cleared. None for
    a pull request that is not open; unknown when a copy it needs cannot be read."""
    if item.get("state") != "open":
        return None
    names = {lab.get("name") for lab in item.get("labels") or []}
    if not (item.get("draft") or names & set(WAITING_ON_BUILDER)) or cleared == "yes":
        return False
    if hours == UNKNOWN or not isinstance(comments, list) or not isinstance(commits, list):
        return UNKNOWN
    moments = [metrics.stamp(item.get("created_at"))]
    for commit in commits:
        author = (
            ((commit.get("commit") or {}).get("author") or {}) if isinstance(commit, dict) else {}
        )
        moments.append(metrics.stamp(author.get("date")))
    for comment in comments:
        moments += [metrics.stamp(comment.get(k)) for k in ("created_at", "updated_at")]
    known = [m for m in moments if m is not None]
    if not known:
        return UNKNOWN
    now = metrics.start_of(today + timedelta(days=1))
    return now - max(known) >= timedelta(hours=hours)


def pull_record(
    src: Any,
    item: dict,
    authors: list[str] | None = None,
    limits: dict | None = None,
    today: date | None = None,
    seen: list | None = None,
    keep: dict | None = None,
) -> dict:
    number = item["number"]
    head = (item.get("head") or {}).get("sha") or ""
    files = get_list(src, f"files-{number}", f"repos/{{repo}}/pulls/{number}/files")
    comments = get_list(src, f"comments-{number}", f"repos/{{repo}}/issues/{number}/comments")
    commits = get_list(src, f"commits-{number}", f"repos/{{repo}}/pulls/{number}/commits")
    authors = metrics.counted_authors(authors, metrics.author_of(item))
    merged = bool(item.get("merged_at"))
    if keep is not None and merged:  # one fetch of the comments serves the flow and the shadow
        keep[number] = (item, comments)
    size, expected = parse_estimate(item["body"]) if "body" in item else (UNKNOWN, UNKNOWN)
    proof = proof_of(src, head) if head else (UNKNOWN, UNKNOWN)
    record = {
        "number": number,
        "state": "open" if item.get("state") == "open" else ("merged" if merged else "closed"),
        "created_at": item.get("created_at"),
        "closed_at": item.get("closed_at"),
        "merged_at": item.get("merged_at"),
        "head": head or UNKNOWN,
        "base": (item.get("base") or {}).get("ref") or UNKNOWN,
        "title": item.get("title") or "",
        "files": UNKNOWN if files is None else sorted(f.get("filename", "") for f in files),
        "proof": proof[0],
        "proof_reason": proof[1],
        "verdicts": verdicts_of(comments, authors),
        "behaviour": behaviour_of(item["body"]) if "body" in item else UNKNOWN,
        "estimated_size": size,
        "estimated_hours": expected,
        "actual_hours": metrics.actual_hours(commits, item.get("merged_at")) if merged else None,
        "usage": metrics.usage_of(comments, (item.get("user") or {}).get("login") or ""),
    }
    brief = brief_of(item["body"]) if "body" in item else UNKNOWN
    record["brief"] = brief
    record["flow"] = flow_hours(
        item.get("created_at"),
        taken_at(src, brief, item.get("created_at")),
        record["verdicts"],
        item.get("merged_at"),
    )
    if isinstance(comments, list):
        found = metrics.first_lines(comments, "conflict needs a person:") or []
        record["conflicts"] = len(found)
    else:
        record["conflicts"] = UNKNOWN
    if seen is not None:
        seen += corrections_of(comments, authors)
    if isinstance(commits, list):
        subjects = [
            str((c.get("commit") or {}).get("message") or "").split("\n")[0] for c in commits
        ]
        record["renumbers"] = sum(1 for subject in subjects if "renumber" in subject.lower())
    else:
        record["renumbers"] = UNKNOWN
    if merged:
        record["head_cleared"] = metrics.merged_head_cleared(src, head, comments, authors)
    elif record["state"] == "open":  # SPEC-0030 rule 8: no verdict yet is `no`, not unknown
        listed = metrics.verdicts(comments if isinstance(comments, list) else None, authors)
        cleared = metrics.merged_head_cleared(src, head, comments, authors)
        record["head_cleared"] = UNKNOWN if listed is None else (cleared if listed else "no")
    stall = (limits or FLOW_DEFAULTS).get("stall_hours", UNKNOWN)
    record["stalled"] = stalled_of(
        item, comments, commits, stall, today or date.today(), record.get("head_cleared")
    )
    return record


def pulls_section(
    src: Any,
    today: date,
    weeks: int,
    authors: list[str] | None = None,
    limits: dict | None = None,
    seen: list | None = None,
    keep: dict | None = None,
) -> Any:
    start = window_start(today, weeks)

    def older(chunk: list[dict]) -> bool:
        last = metrics.stamp(chunk[-1].get("updated_at") or chunk[-1].get("closed_at"))
        return last is not None and last < start

    opened = get_list(src, "pulls-open", "repos/{repo}/pulls?state=open")
    closed = get_list(
        src, "pulls", "repos/{repo}/pulls?state=closed&sort=updated&direction=desc", older
    )
    if opened is None or closed is None:
        return UNKNOWN
    chosen = {p["number"]: p for p in opened}
    for p in closed:
        when = metrics.stamp(p.get("closed_at"))
        if when is not None and when >= start:
            chosen[p["number"]] = p
    last = metrics.start_of(today + timedelta(days=1))
    kept = [p for p in chosen.values() if (metrics.stamp(p.get("created_at")) or last) < last]
    return [
        pull_record(src, p, authors, limits, today, seen, keep)
        for p in sorted(kept, key=lambda p: p["number"])
    ]


def corrections_of(comments: Any, authors: list[str] | None) -> list[tuple]:
    """(author, first line, moment) of the `Correction:` comments of listed authors; a single
    `(None, None, None)` when the comments cannot be read."""
    found = metrics.first_lines(comments, "Correction:", authors)
    if found is None:
        return [(None, None, None)]
    return [
        (metrics.author_of(c), c["body"].splitlines()[0].strip(), c["created_at"]) for c in found
    ]


def distinct_moments(seen: list[tuple]) -> Any:
    """One moment for each distinct (author, first line), the earliest: the conductor posts one
    correction on the brief and on each pull request built from it (SPEC-0032 rule 11)."""
    if any(author is None for author, _, _ in seen):
        return UNKNOWN
    earliest: dict[tuple, str] = {}
    for author, text, at in seen:
        if (author, text) not in earliest or at < earliest[(author, text)]:
            earliest[(author, text)] = at
    return sorted(earliest.values())


def flow_section(
    src: Any, limits: dict, authors: list[str] | None, seen: list | None = None
) -> dict[str, Any]:
    """What the weekly report needs of the flow (SPEC-0034 rule 10): the limits, the open briefs
    with what they advance, the retakes and the corrections as moments; the report counts them."""
    listed = get_list(
        src, "issues-agk-brief", f"repos/{{repo}}/issues?state=all&labels={BRIEF_LABEL}"
    )
    section: dict[str, Any] = {
        **limits,
        "briefs": UNKNOWN,
        "retakes": UNKNOWN,
        "corrections": UNKNOWN,
    }
    if listed is None:
        return section
    briefs, retakes = [], []
    seen = [] if seen is None else seen
    for issue in sorted((i for i in listed if "pull_request" not in i), key=lambda i: i["number"]):
        number = issue["number"]
        comments = get_list(src, f"comments-{number}", f"repos/{{repo}}/issues/{number}/comments")
        if comments is None:
            return section
        retakes += [
            c["created_at"]
            for c in metrics.first_lines(comments, "taken:") or []
            if (m := TAKE_LINE.fullmatch(c["body"].splitlines()[0].strip())) and m.group(1)
        ]
        seen += corrections_of(comments, authors)
        if issue.get("state") == "open":
            line = next(
                (x for x in str(issue.get("body") or "").splitlines() if ADVANCES.fullmatch(x)), ""
            )
            found = ADVANCES.fullmatch(line)
            advances = (
                UNKNOWN
                if not found
                else (
                    found.group(1)
                    if found.group(1) == "new"
                    else ([] if found.group(1) == "none" else found.group(1).split(", "))
                )
            )
            briefs.append(
                {
                    "number": number,
                    "title": issue.get("title") or "",
                    "created_at": issue.get("created_at"),
                    "advances": advances,
                }
            )
    section["briefs"] = briefs
    section["retakes"] = sorted(retakes)
    section["corrections"] = distinct_moments(seen)
    return section


def shadow_section(src: Any, kept: dict, authors: list[str] | None) -> Any:
    """What the weekly report needs of the shadow review (SPEC-0035 rule 5): the counts of
    `shadow_rate.py` for the merged pull requests of the window, per ISO week of the merge and in
    total, from the comments of the one open issue labelled `agk-shadow`. No open issue is a review
    that is not running (`{"issue": null}`); what cannot be read, two open issues and a refused
    mark are `unknown`, never zero."""
    listed = get_list(
        src, f"issues-{SHADOW_LABEL}", f"repos/{{repo}}/issues?state=open&labels={SHADOW_LABEL}"
    )
    if listed is None:
        return UNKNOWN
    opened = [i for i in listed if "pull_request" not in i and i.get("state") == "open"]
    if not opened:
        return {"issue": None}
    if len(opened) > 1:
        return UNKNOWN
    number = opened[0]["number"]
    comments = get_list(src, f"comments-{number}", f"repos/{{repo}}/issues/{number}/comments")
    allowed = {a.lstrip("@").lower() for a in authors or []}
    if comments is None or not allowed:
        return UNKNOWN
    try:
        totals, unpaired, unread = shadow_rate.count_pulls(
            [kept[n] for n in sorted(kept)], comments, allowed
        )
    except CheckError:
        return UNKNOWN
    return {"issue": number, "unpaired": unpaired, "unread": unread, **shadow_rate.summary(totals)}


def issues_section(src: Any) -> Any:
    found = []
    for label in LABELS:
        listed = get_list(src, f"issues-{label}", f"repos/{{repo}}/issues?state=all&labels={label}")
        if listed is None:
            return UNKNOWN
        found += [
            {
                "number": i["number"],
                "title": i.get("title") or "",
                "label": label,
                "state": i.get("state") or UNKNOWN,
            }
            for i in listed
            if "pull_request" not in i
        ]
    return sorted(found, key=lambda i: (i["number"], i["label"]))


# --- the audit's counts -----------------------------------------------------------------------


def drift_section(root: Path, today: date, cfg: dict | None, issues: Any) -> Any:
    if cfg is None:
        return UNKNOWN
    open_numbers: list[int] = []
    if isinstance(issues, list):
        open_numbers = [
            i["number"] for i in issues if i["label"] == "agk-drift-audit" and i["state"] == "open"
        ]
    try:
        found, _ = drift_audit.audit(root, today, cfg["default_branch"], open_numbers)
    except CheckError:
        return UNKNOWN
    counts: dict[str, Any] = {c: sum(1 for f in found if f.code == c) for c in drift_audit.CODES}
    total: Any = len(found)
    if not isinstance(issues, list):
        counts["D6"] = total = UNKNOWN
    return {"counts": counts, "total": total}


# --- the document -----------------------------------------------------------------------------


def build(root: Path, today: date, repo: str, src: Any, weeks: int) -> dict:
    cfg = load_cfg(root)
    specs, adrs = spec_records(root), adr_records(root)
    issues = issues_section(src)
    limits = flow_limits(root)
    authors = metrics.verdict_authors(root)
    seen: list[tuple] = []
    kept: dict = {}
    pulls = pulls_section(src, today, weeks, authors, limits, seen, kept)
    flow = flow_section(src, limits, authors, seen)
    return {
        "schema": SCHEMA,
        "commit": git(root, "rev-parse", "HEAD").strip(),
        "dirty": dirty_of(root),
        "kit_version": installed_version(root) or UNKNOWN,
        "today": today.isoformat(),
        "repo": repo,
        "config": config_section(cfg),
        "requirements": requirements_section(root),
        "markers": markers_section(root, cfg),
        "specs": [
            {
                "id": s["id"],
                "path": s["path"],
                "title": s["title"],
                "status": s["status"],
                "requirements": s["requirements"],
                "notes": s["notes"],
                "open_questions": open_questions_of(root, s),
            }
            for s in specs
        ],
        "adrs": adrs,
        "residuals": residuals_section(root, specs, adrs),
        "questions": questions_section(root, specs, adrs),
        "pull_requests": pulls,
        "flow": flow,
        "shadow": UNKNOWN if pulls == UNKNOWN else shadow_section(src, kept, authors),
        "issues": issues,
        "drift": drift_section(root, today, cfg, issues),
    }


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def source_for(api_dir: str | None, repo: str) -> Any:
    if api_dir:
        return metrics.ApiDir(Path(api_dir))
    if repo == UNKNOWN or shutil.which("gh") is None:
        return None
    return metrics.Gh(repo)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = Parser(prog="facts.py", add_help=False)
    parser.add_argument("--today")
    parser.add_argument("--repo")
    parser.add_argument("--api-dir")
    parser.add_argument("--weeks", type=int, default=8)
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    if args.weeks < 1:
        parser.error("weeks")
    if args.today is not None and drift_audit.parse_date(args.today) is None:
        parser.error("today")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    root = Path(args.root)
    check_root(root)
    today = date.fromisoformat(args.today) if args.today else datetime.now(UTC).date()
    repo = repo_of(root, args.repo)
    try:
        document = build(root, today, repo, source_for(args.api_dir, repo), args.weeks)
    except OSError:
        print("FAIL facts: a required file cannot be read (path class: .git)")
        return 3
    sys.stdout.write(render(document))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
