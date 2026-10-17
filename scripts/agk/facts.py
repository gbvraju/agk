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
from common import (
    REQ_ID,
    CheckError,
    declares_unchanged,
    find_ac_markers,
    git,
    load_config,
    parse_acceptance,
    parse_requirements,
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
QUESTION = re.compile(r"Q-[A-Z0-9]+-[0-9]+")
NOTES_FILE = re.compile(r"docs/runs/spec-\d{4}-notes\.md")
ORIGIN = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$")
SPEC_TITLE = re.compile(r"^# SPEC-\d{4}:\s*(.+?)\s*$")
SPEC_STATUSES = ("Draft", "Approved")
LABELS = ("agk-metrics", "agk-drift-audit", "agk-product-report")
OUTCOMES = ("proven", "not-proven", "skipped", "unknown")


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


def requirements_section(root: Path) -> Any:
    text = drift_audit.read(root, REQUIREMENTS)
    if text is None:
        return UNKNOWN
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
                "criteria": criteria,
                "criteria_form": "structured" if pairs else "unstructured",
            }
        )
    return sorted(found, key=lambda r: r["id"])


def markers_section(root: Path, cfg: dict | None) -> Any:
    if cfg is None:
        return UNKNOWN
    exclude = ["tests/kit"] if cfg["mode"] == "adopt" else []
    return find_ac_markers(root, cfg["test_dirs"], cfg["test_patterns"], exclude)


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


def log_lines(root: Path) -> list[str] | None:
    text = drift_audit.read(root, LOG)
    return None if text is None else text.splitlines()


def whole_id(question: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(question) + r"(?![A-Za-z0-9-])")


def ruled_in(lines: list[str] | None, question: str) -> bool | str:
    if lines is None:
        return UNKNOWN
    return any(re.search(whole_id(question).pattern + r" ruled", ln) for ln in lines)


def open_section_ids(text: str) -> set[str]:
    found: set[str] = set()
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Open"
        elif inside:
            found.update(QUESTION.findall(line))
    return found


def question_index(root: Path) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    base = root / "docs"
    for path in sorted(base.rglob("*.md")) if base.is_dir() else []:
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for question in QUESTION.findall(text):
            index.setdefault(question, set()).add(rel)
    return index


def open_places(root: Path, specs: list[dict], adrs: list[dict]) -> tuple[set[str], set[str]]:
    """(the files that are open places as a whole, the notes files with an `## Open` section)."""
    whole = {s["notes"] for s in specs if s["status"] == "Draft" and s["notes"]}
    whole |= {a["path"] for a in adrs if a["status"] == "Proposed"}
    notes = {p.relative_to(root).as_posix() for p in (root / "docs/runs").glob("spec-*-notes.md")}
    return whole, {n for n in notes if NOTES_FILE.fullmatch(n)}


def questions_section(root: Path, specs: list[dict], adrs: list[dict]) -> Any:
    lines = log_lines(root)
    if lines is None:
        return UNKNOWN
    whole, notes = open_places(root, specs, adrs)
    open_ids = {
        n: open_section_ids((root / n).read_text(encoding="utf-8", errors="replace")) for n in notes
    }
    found = []
    for question, files in sorted(question_index(root).items()):
        places = sorted(
            f for f in files if f in whole or (f in open_ids and question in open_ids[f])
        )
        found.append(
            {
                "id": question,
                "files": sorted(files),
                "ruled": ruled_in(lines, question),
                "named_in_log": any(whole_id(question).search(ln) for ln in lines),
                "open_in": places,
            }
        )
    return found


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


def closed_rows(text: str) -> list[tuple[int, str, str]]:
    rows, inside = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            inside = line.strip().startswith("## Closed")
        elif inside and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] not in ("Source", "") and not set(cells[0]) <= {"-"}:
                rows.append((number, cells[0], cells[1]))
    return rows


def residuals_section(root: Path, specs: list[dict], adrs: list[dict]) -> Any:
    register = drift_audit.read(root, REGISTER)
    if register is None:
        return UNKNOWN
    found: list[tuple[str, int, dict]] = []
    for rel in sorted(s["path"] for s in specs) + sorted(a["path"] for a in adrs):
        bullets = drift_audit.residual_bullets(drift_audit.read(root, rel) or "")
        for position, bullet in enumerate(bullets):
            body = bullet[2:]
            item = {"source": rel, "text": body, "due": due_of(body), "state": "open"}
            found.append((rel, position, item))
    for entry in drift_audit.register_lines(register):
        due = entry["due"].isoformat() if entry["due"] else UNKNOWN
        item = {"source": REGISTER, "text": entry["text"], "due": due, "state": "open"}
        found.append((REGISTER, entry["number"], item))
    for number, _source, body in closed_rows(register):
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


def verdicts_of(comments: list | None) -> Any:
    if comments is None:
        return UNKNOWN
    found = []
    for comment in sorted(comments, key=lambda c: (c.get("created_at") or "", c.get("id") or 0)):
        parsed = metrics.verdicts([comment])
        if parsed:
            kind, sha = parsed[0]
            found.append({"kind": kind, "sha": sha or None, "at": comment.get("created_at")})
    return found


def proof_of(src: Any, head: str) -> str:
    runs = get_object(src, f"runs-{head}", f"repos/{{repo}}/actions/runs?head_sha={head}")
    if runs is None or not isinstance(runs.get("workflow_runs"), list):
        return UNKNOWN
    named = [r for r in runs["workflow_runs"] if r.get("name") == "proof"]
    if not named:
        return UNKNOWN
    latest = max(named, key=lambda r: (r.get("created_at") or "", r.get("id") or 0))
    jobs = get_object(
        src, f"jobs-{latest.get('id')}", f"repos/{{repo}}/actions/runs/{latest.get('id')}/jobs"
    )
    if jobs is None or not isinstance(jobs.get("jobs"), list):
        return UNKNOWN
    job = next((j for j in jobs["jobs"] if j.get("name") == "proof"), None)
    steps = job.get("steps") if isinstance(job, dict) else None
    if not isinstance(steps, list):
        return UNKNOWN
    won = [
        s["name"][len("outcome: ") :]
        for s in steps
        if str(s.get("name", "")).startswith("outcome: ") and s.get("conclusion") == "success"
    ]
    return won[0] if len(won) == 1 and won[0] in OUTCOMES else UNKNOWN


def pull_record(src: Any, item: dict) -> dict:
    number = item["number"]
    head = (item.get("head") or {}).get("sha") or ""
    files = get_list(src, f"files-{number}", f"repos/{{repo}}/pulls/{number}/files")
    comments = get_list(src, f"comments-{number}", f"repos/{{repo}}/issues/{number}/comments")
    merged = bool(item.get("merged_at"))
    return {
        "number": number,
        "state": "open" if item.get("state") == "open" else ("merged" if merged else "closed"),
        "created_at": item.get("created_at"),
        "closed_at": item.get("closed_at"),
        "merged_at": item.get("merged_at"),
        "head": head or UNKNOWN,
        "base": (item.get("base") or {}).get("ref") or UNKNOWN,
        "title": item.get("title") or "",
        "files": UNKNOWN if files is None else sorted(f.get("filename", "") for f in files),
        "proof": proof_of(src, head) if head else UNKNOWN,
        "verdicts": verdicts_of(comments),
        "behaviour": behaviour_of(item["body"]) if "body" in item else UNKNOWN,
    }


def pulls_section(src: Any, today: date, weeks: int) -> Any:
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
    return [pull_record(src, p) for p in sorted(kept, key=lambda p: p["number"])]


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
    return {
        "schema": SCHEMA,
        "commit": git(root, "rev-parse", "HEAD").strip(),
        "dirty": dirty_of(root),
        "today": today.isoformat(),
        "repo": repo,
        "config": config_section(cfg),
        "requirements": requirements_section(root),
        "markers": markers_section(root, cfg),
        "specs": [
            {
                "id": s["id"],
                "title": s["title"],
                "status": s["status"],
                "requirements": s["requirements"],
                "notes": s["notes"],
                "open_questions": open_questions_of(root, s),
            }
            for s in specs
        ],
        "adrs": [{k: v for k, v in a.items() if k != "path"} for a in adrs],
        "residuals": residuals_section(root, specs, adrs),
        "questions": questions_section(root, specs, adrs),
        "pull_requests": pulls_section(src, today, weeks),
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
