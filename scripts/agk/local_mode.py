"""Enter and leave local mode with one command (brief 371, ADR-0213).

Usage: python3 scripts/agk/local_mode.py enter|leave [--write] [--since YYYY-MM-DD]
                                         [--repo OWNER/REPO] [--api-dir DIR]

Standard library only. `enter` lists every active workflow of the repository, the kit's and the
project's, with the one `gh api --method PUT .../actions/workflows/<id>/disable` call for each;
`leave` lists every workflow disabled by hand with its `enable` call, then the pull requests merged
into the default branch since the oldest of them was disabled (or since `--since`, midnight UTC),
and the state of the catch-up run: the latest run of each check of `required_checks` on the head of
the default branch that started after local mode began. It is a dry run by default and changes
nothing; `--write` makes the calls, one line per workflow, and reports a refused call while it still
makes the rest. `gh` holds the credential and this script holds none: the person runs `--write` with
a token that may change workflows, which no session holds (session rule 30).

Recorded responses (`--api-dir`) stand in for `gh`: `<name>.json` answers a read, `<name>.status`
holds the HTTP status of a refused one; each write is appended to `calls.log` and is refused when
`put-<id>-<verb>.status` exists.

Exit: 0 done, 3 a call was refused or the catch-up is red, 1 refused (the workflows cannot be read
or a setting is invalid), 2 usage.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, load_config, repo_root, required_checks, run

NAME = "local-mode"
USAGE = (
    "usage: local_mode.py enter|leave [--write] [--since YYYY-MM-DD] [--repo OWNER/REPO] "
    "[--api-dir DIR]"
)
PAGE = 100
GUIDE = "docs/guides/local-mode.md"
VERBS = {
    "enter": ("active", "disable", "disabled"),
    "leave": ("disabled_manually", "enable", "enabled"),
}
OK_CONCLUSIONS = {"success", "neutral", "skipped"}


def reason_of(status: int) -> str:
    """The reason class of a read that did not answer: refused, missing or unreadable."""
    if status in (401, 403):
        return "refused"
    if status in (404, 410):
        return "missing"
    return "unreadable"


def origin_repo() -> str:
    from metrics import origin_repo as read_origin

    return read_origin()


# --- the sources ------------------------------------------------------------------------------


class ApiDir:
    """Recorded responses; writes are logged, never made."""

    def __init__(self, path: Path, repo: str) -> None:
        self.path = path
        self.repo = repo

    def get(self, name: str, endpoint: str, until: Any = None) -> tuple[int, Any]:
        status = self.path / f"{name}.status"
        if status.is_file():
            text = status.read_text(encoding="utf-8").strip()
            return (int(text) if text.isdigit() else 0), None
        file = self.path / f"{name}.json"
        if not file.is_file():
            return 404, None
        try:
            return 200, json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise CheckError(f"{name}.json in --api-dir is not JSON (path class api-dir)") from None

    def put(self, name: str, endpoint: str) -> int:
        with (self.path / "calls.log").open("a", encoding="utf-8") as log:
            log.write(f"PUT {endpoint.replace('{repo}', self.repo)}\n")
        status = self.path / f"{name}.status"
        if status.is_file():
            text = status.read_text(encoding="utf-8").strip()
            return int(text) if text.isdigit() else 0
        return 204


class Gh:
    """Live calls through `gh api`: reads with GET, paged by hand; writes with PUT."""

    def __init__(self, repo: str) -> None:
        self.repo = repo

    def call(self, method: str, endpoint: str) -> tuple[int, str]:
        try:
            proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
                ["gh", "api", "--method", method, endpoint],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except OSError:
            return 0, ""
        if proc.returncode != 0:
            match = re.search(r"\(HTTP (\d{3})\)", proc.stderr or "")
            return (int(match.group(1)) if match else 0), ""
        return 200, proc.stdout

    def one(self, endpoint: str) -> tuple[int, Any]:
        status, text = self.call("GET", endpoint)
        if status != 200:
            return status, None
        try:
            return 200, json.loads(text)
        except ValueError:
            return 0, None

    def get(self, name: str, endpoint: str, until: Any = None) -> tuple[int, Any]:
        endpoint = endpoint.replace("{repo}", self.repo)
        if name == "workflows":
            return self.keyed(endpoint, "workflows")
        if name == "check-runs":
            return self.keyed(endpoint, "check_runs")
        if name == "pulls":
            return self.listed(endpoint, until)
        return self.one(endpoint)

    def keyed(self, endpoint: str, key: str) -> tuple[int, Any]:
        out: dict = {"total_count": 0, key: []}
        sep = "&" if "?" in endpoint else "?"
        page = 1
        while True:
            status, chunk = self.one(f"{endpoint}{sep}per_page={PAGE}&page={page}")
            if status != 200 or not isinstance(chunk, dict):
                return status, None
            out["total_count"] = chunk.get("total_count", 0)
            items = chunk.get(key) or []
            out[key] += items
            if len(items) < PAGE or len(out[key]) >= out["total_count"]:
                return 200, out
            page += 1

    def listed(self, endpoint: str, until: Any) -> tuple[int, Any]:
        out: list = []
        page = 1
        while True:
            status, chunk = self.one(f"{endpoint}&per_page={PAGE}&page={page}")
            if status != 200 or not isinstance(chunk, list):
                return status, None
            out += chunk
            if len(chunk) < PAGE or (until and until(chunk)):
                return 200, out
            page += 1

    def put(self, name: str, endpoint: str) -> int:
        status, _ = self.call("PUT", endpoint.replace("{repo}", self.repo))
        return 204 if status == 200 else status


# --- reading ----------------------------------------------------------------------------------


def stamp(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_of(wf: dict) -> str:
    return str(wf.get("path") or wf.get("name") or "unknown").rsplit("/", 1)[-1]


def workflows(src: Any) -> list[dict]:
    status, data = src.get("workflows", "/repos/{repo}/actions/workflows")
    if status != 200 or not isinstance(data, dict):
        raise CheckError(
            f"the workflows cannot be read ({reason_of(status)}; path class: repository)"
        )
    items = [w for w in data.get("workflows") or [] if isinstance(w, dict)]
    return sorted(items, key=lambda w: w.get("id") or 0)


def merges(src: Any, branch: str, since: datetime) -> tuple[list[dict] | None, str | None]:
    """The pull requests merged into `branch` at or after `since`, oldest first, or a reason."""

    def older(chunk: list) -> bool:
        last = stamp(chunk[-1].get("updated_at")) if chunk else None
        return last is not None and last < since

    status, pulls = src.get(
        "pulls",
        f"/repos/{{repo}}/pulls?state=closed&base={branch}&sort=updated&direction=desc",
        older,
    )
    if status != 200 or not isinstance(pulls, list):
        return None, reason_of(status)
    found = []
    for item in pulls:
        merged = stamp(item.get("merged_at"))
        base = (item.get("base") or {}).get("ref")
        if merged is None or merged < since or (base is not None and base != branch):
            continue
        found.append(item)
    found.sort(key=lambda p: (stamp(p.get("merged_at")), p.get("number") or 0))
    return found, None


@dataclass
class CatchUp:
    lines: list[str]
    red: bool


def catch_up(src: Any, branch: str, since: datetime | None, required: list[str]) -> CatchUp:
    """The latest run of each required check on the head of `branch` since local mode began."""
    from route import latest_runs

    status, head = src.get("commit", f"/repos/{{repo}}/commits/{branch}")
    sha = head.get("sha") if status == 200 and isinstance(head, dict) else None
    if not isinstance(sha, str) or not sha:
        return CatchUp(
            [f"catch-up: unknown (the default branch cannot be read: {reason_of(status)})"], False
        )
    status, data = src.get("check-runs", f"/repos/{{repo}}/commits/{sha}/check-runs")
    if status != 200 or not isinstance(data, dict):
        return CatchUp(
            [f"catch-up: unknown (the check runs cannot be read: {reason_of(status)})"], False
        )
    runs = [
        r
        for r in data.get("check_runs") or []
        if isinstance(r, dict)
        and r.get("name") in required
        and r.get("head_sha", sha) == sha
        and (since is None or ((s := stamp(r.get("started_at"))) is not None and s >= since))
    ]
    latest = {str(r.get("name")): r for r in latest_runs(runs)}
    if not latest:
        return CatchUp(["catch-up: not run yet"], False)
    lines, failed, done = [], [], True
    for name in required:
        item = latest.get(name)
        if item is None:
            lines.append(f"catch-up {name}: not run yet")
            done = False
        elif item.get("status") != "completed":
            lines.append(f"catch-up {name}: running on {sha[:7]}")
            done = False
        else:
            conclusion = str(item.get("conclusion") or "unknown")
            lines.append(f"catch-up {name}: {conclusion} on {sha[:7]}")
            if conclusion not in OK_CONCLUSIONS:
                failed.append(name)
    if failed:
        lines.append(
            f"catch-up: red on {sha[:7]} ({', '.join(failed)}): file a priority-0 brief that names "
            "the failing run and the merges above"
        )
    elif done:
        lines.append("catch-up: green")
    return CatchUp(lines, bool(failed))


# --- the command ------------------------------------------------------------------------------


def call_line(repo: str, wid: Any, verb: str) -> str:
    return f"gh api --method PUT repos/{repo}/actions/workflows/{wid}/{verb}"


def act(
    src: Any, repo: str, chosen: list[dict], verb: str, done: str, write: bool
) -> tuple[list[str], int]:
    lines, refused = [], 0
    for wf in chosen:
        wid, name = wf.get("id"), file_of(wf)
        line = call_line(repo, wid, verb)
        if not write:
            lines.append(f"  {name} (id {wid}): {line}")
            continue
        status = src.put(f"put-{wid}-{verb}", f"/repos/{{repo}}/actions/workflows/{wid}/{verb}")
        if status in (200, 204):
            lines.append(f"{done} {name} (id {wid})")
        else:
            refused += 1
            shown = f"HTTP {status}" if status else "no answer"
            lines.append(f"refused {name} (id {wid}): {shown}; a person with admin runs: {line}")
    return lines, refused


def main_of(command: str, write: bool, since_arg: datetime | None, repo: str, src: Any) -> int:
    root = repo_root()
    branch = str(load_config(root).get("default_branch") or "main")
    required = required_checks(root) if command == "leave" else []
    state, verb, done = VERBS[command]
    every = workflows(src)
    chosen = [w for w in every if w.get("state") == state]
    out = [
        f"agk local mode: {command} {repo}"
        + ("" if write else " (dry run: nothing is changed; --write makes the calls)")
    ]
    label = "active workflows" if command == "enter" else "workflows disabled by hand"
    out.append(f"{label}: {len(chosen)}")
    left = []
    since, since_from = since_arg, "--since"
    pulls_lines: list[str] = []
    if command == "leave":
        for wf in every:
            other = str(wf.get("state") or "")
            if other.startswith("disabled") and other != state:
                left.append(f"left as is: {file_of(wf)} (id {wf.get('id')}, {other})")
        if since is None:
            stamps = [s for w in chosen if (s := stamp(w.get("updated_at"))) is not None]
            if stamps:
                since, since_from = min(stamps), "the oldest workflow disabled by hand"
        if since is None:
            pulls_lines.append(
                "merged on local evidence: unknown (no workflow is disabled by hand; give --since "
                "YYYY-MM-DD, the day local mode began)"
            )
        else:
            pulls_lines.append(f"local mode since: {iso(since)} ({since_from})")
            found, reason = merges(src, branch, since)
            if found is None:
                pulls_lines.append(
                    "merged on local evidence: unknown "
                    f"(the pull requests cannot be read: {reason})"
                )
            else:
                pulls_lines.append(f"merged on local evidence: {len(found)}")
                for item in found:
                    sha = str(item.get("merge_commit_sha") or "")[:7] or "-------"
                    pulls_lines.append(
                        f"  #{item.get('number')} {iso(stamp(item.get('merged_at')))} {sha} "
                        f"{item.get('title') or ''}".rstrip()
                    )
    lines, refused = act(src, repo, chosen, verb, done, write)
    red = False
    if command == "enter":
        out += lines
        if not write and chosen:
            out.append(f"the person runs these with admin rights; see {GUIDE}")
        if write:
            out.append(f"next: open the record issue, as {GUIDE} says")
    else:
        out += lines + left + pulls_lines  # the merges were read before any workflow was enabled
        result = catch_up(src, branch, since, required)
        out += result.lines
        red = result.red
    sys.stdout.write("\n".join(out) + "\n")
    return 3 if refused or red else 0


def parse_args(args: list[str]) -> dict | None:
    if not args or args[0] not in VERBS:
        return None
    options: dict = {"command": args[0], "write": False, "since": None, "repo": None, "api": None}
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--write":
            options["write"] = True
            i += 1
        elif arg in ("--since", "--repo", "--api-dir") and i + 1 < len(args):
            value = args[i + 1]
            if arg == "--since":
                if options["command"] != "leave" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    return None
                try:
                    options["since"] = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
                except ValueError:
                    return None
            else:
                options[{"--repo": "repo", "--api-dir": "api"}[arg]] = value
            i += 2
        else:
            return None
    return options


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    name = options["repo"] or origin_repo()
    src: Any = ApiDir(Path(options["api"]), name) if options["api"] else Gh(name)
    return main_of(options["command"], options["write"], options["since"], name, src)


if __name__ == "__main__":
    sys.exit(run(NAME, main))
