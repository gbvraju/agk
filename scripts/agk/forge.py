"""One record interface for the readers: GitHub's, or a sidecar's files (SPEC-0041 rule 6).

`get(name, endpoint)` answers with the names of SPEC-0007 rule 20; `create_issue`, `comment` and
`record_pull` are the writes personal mode needs. `GithubForge` wraps `metrics.Gh` and
`metrics.ApiDir` unchanged and writes nothing. `FilesForge` keeps GitHub-shaped JSON under `forge/`
of the sidecar: `issues/<n>.json`, `pulls/<n>.json` and `comments-<n>.json`, one number sequence,
each write a temporary file and a rename, committed to the sidecar with only that file. It runs
`git` and never `gh`, and opens no connection. A comment written in an agent session carries the
agent mark (rule 8). Refusals name the setting or the path class, never a value.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, agent_apps, personal_table  # noqa: E402
from local_mode import SESSION_SETTING  # noqa: E402
from lock import Usage, clear_if_same, stale_minutes, take  # noqa: E402
from metrics import ApiDir, Gh  # noqa: E402
from reviewers import solo_person  # noqa: E402

AGENT_APP = "claude"
NO_GITHUB_WRITE = "personal mode never writes to GitHub (setting: forge)"
NUMBERED = re.compile(r"(pull|issue|comments|files|commits)-(\d+)")
LOCK_WAIT = 10.0  # seconds a write waits for another write
STATUS = dict(A="added", C="copied", D="removed", M="modified", R="renamed", T="changed")
LOG_FIELDS = "%x00".join(("%H", "%P", "%an", "%ae", "%at", "%cn", "%ce", "%ct", "%B"))


class GithubForge:
    """The existing readers behind the interface, their behaviour unchanged; no write."""

    def __init__(self, source: Any) -> None:
        self.source = source

    @classmethod
    def live(cls, repo: str) -> GithubForge:
        return cls(Gh(repo))

    @classmethod
    def saved(cls, path: Path) -> GithubForge:
        return cls(ApiDir(Path(path)))

    def get(self, name: str, endpoint: str, until: Any = None) -> Any:
        return self.source.get(name, endpoint, until)

    def refuse(self, *_args: Any, **_kw: Any) -> Any:
        raise CheckError(NO_GITHUB_WRITE)

    create_issue = comment = record_pull = refuse


def stamp_of(seconds: str) -> str:
    return datetime.fromtimestamp(int(seconds), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def state_of(endpoint: str) -> str:
    """The `state=` of a list endpoint; GitHub's default is `open`."""
    found = re.search(r"[?&]state=(open|closed|all)\b", endpoint)
    return found.group(1) if found else "open"


class FilesForge:
    """A sidecar's records, GitHub-shaped; `clone` is the product, read for files and commits."""

    def __init__(
        self,
        sidecar: Path,
        clone: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.root = Path(sidecar)
        self.clone = clone
        self.env = os.environ if env is None else env
        if personal_table(self.root) is None:
            raise CheckError("a files forge needs a sidecar (setting: personal)")
        if AGENT_APP not in agent_apps(self.root):
            raise CheckError("a sidecar keeps the agent app listed (setting: agent_apps)")
        person = solo_person(self.root)
        if not person:
            raise CheckError("a sidecar lists one person (setting: verdict_authors)")
        self.person = person

    # --- the reads ----------------------------------------------------------------------------

    @property
    def forge(self) -> Path:
        return self.root / "forge"

    def numbers(self, kind: str) -> list[int]:
        """The numbers of `issues` or `pulls`, ascending."""
        folder = self.forge / kind
        return sorted(int(p.stem) for p in folder.glob("*.json") if p.stem.isdigit())

    def load(self, rel: str) -> Any:
        path = self.forge / rel
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise CheckError("a record is not JSON (path class: forge)") from None

    def listed(self, kind: str, endpoint: str) -> list[dict]:
        """The records whose state the endpoint asks for, newest update first, as GitHub lists."""
        state = state_of(endpoint)
        found = [self.load(f"{kind}/{n}.json") for n in self.numbers(kind)]
        kept = [r for r in found if state == "all" or r.get("state") == state]
        return sorted(kept, key=lambda r: (r.get("updated_at") or "", r["number"]), reverse=True)

    def get(self, name: str, endpoint: str, until: Any = None) -> Any:
        if name in ("pulls", "pulls-open"):
            return self.listed("pulls", endpoint)
        if name.startswith("issues-"):
            label = name.removeprefix("issues-")
            return [
                i
                for i in self.listed("issues", endpoint)
                if label in {x.get("name") for x in i.get("labels") or []}
            ]
        match = NUMBERED.fullmatch(name)
        if not match:
            return None  # a record no sidecar holds (checks, jobs, runs) reads as unknown
        kind, number = match.group(1), int(match.group(2))
        if kind == "pull":
            return self.load(f"pulls/{number}.json")
        if kind == "issue":
            return self.load(f"issues/{number}.json")
        if kind == "comments":
            return self.load(f"comments-{number}.json")
        return self.from_git(kind, number)

    # --- the product's git, read-only ---------------------------------------------------------

    def product(self, *args: str) -> str | None:
        """A read-only git call on the clone (rule 4), its bytes kept; None on failure."""
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "-C", str(self.clone), "--no-optional-locks", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
        )
        return proc.stdout if proc.returncode == 0 else None

    def commit_of(self, ref: Any) -> str | None:
        if not isinstance(ref, str) or not ref:
            return None
        out = self.product("rev-parse", "--verify", "-q", "--end-of-options", f"{ref}^{{commit}}")
        return out.strip() if out else None

    def from_git(self, kind: str, number: int) -> Any:
        """`files-<n>` or `commits-<n>` from the clone; None when its commits cannot be read."""
        record = self.load(f"pulls/{number}.json")
        if self.clone is None or record is None:
            return None
        head = self.commit_of((record.get("head") or {}).get("sha"))
        base = record.get("base") or {}
        tip = self.commit_of(base.get("sha") or base.get("ref"))
        if head is None or tip is None:
            return None
        fork = self.product("merge-base", tip, head)
        if not fork:
            return None
        fork = fork.strip()
        return self.commits(fork, head) if kind == "commits" else self.files(fork, head)

    def commits(self, fork: str, head: str) -> list[dict] | None:
        out = self.product(
            "log", "-z", "--reverse", "--no-show-signature", f"--format={LOG_FIELDS}",
            f"{fork}..{head}",
        )  # fmt: skip
        if out is None:
            return None
        cells = out.split("\0")[:-1]
        found = []
        for at in range(0, len(cells), 9):
            sha, parents, an, ae, at_a, cn, ce, at_c, message = cells[at : at + 9]
            found.append(
                {
                    "sha": sha,
                    "parents": [{"sha": p} for p in parents.split()],
                    "commit": {
                        "author": {"name": an, "email": ae, "date": stamp_of(at_a)},
                        "committer": {"name": cn, "email": ce, "date": stamp_of(at_c)},
                        "message": message.rstrip("\n"),
                    },
                }
            )
        return found

    def files(self, fork: str, head: str) -> list[dict] | None:
        common = ("diff", "-z", "-M", "--no-ext-diff", "--no-textconv")
        names = self.product(*common, "--name-status", fork, head)
        counts = self.product(*common, "--numstat", fork, head)
        if names is None or counts is None:
            return None
        cells, stats = names.split("\0")[:-1], counts.split("\0")[:-1]
        found = []
        while cells:
            letter, first = cells.pop(0)[0], cells.pop(0)
            second = cells.pop(0) if letter in "RC" else None
            added, deleted = stats.pop(0).split("\t")[:2]
            if second is not None:
                del stats[:2]  # numstat -z spells a rename's two paths apart
            plus, minus = (0 if v == "-" else int(v) for v in (added, deleted))
            entry = {
                "filename": second or first,
                "status": STATUS.get(letter, "modified"),
                "additions": plus,
                "deletions": minus,
                "changes": plus + minus,
            }
            if second is not None:
                entry["previous_filename"] = first
            found.append(entry)
        return found

    # --- the writes ---------------------------------------------------------------------------

    def now(self) -> str:
        return stamp_of(str(int(time.time())))

    def run_git(self, *args: str) -> None:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=self.root, capture_output=True, text=True, encoding="utf-8"
        )
        if proc.returncode != 0:
            raise CheckError("the sidecar commit failed (path class: forge)")

    @contextmanager
    def locked(self) -> Iterator[None]:
        """One writer at a time, so a number or a comment is never lost to a second session; the
        take and release of `lock.py`, so a holder that no longer runs is cleared (ADR-0295)."""
        held = self.root / "cache" / "forge.lock"
        token = uuid.uuid4().hex
        host = socket.gethostname()
        owner = dict(session="forge", pid=os.getpid(), host=host, started=self.now(), token=token)
        try:
            limit = stale_minutes(self.root)
        except Usage as exc:
            raise CheckError(str(exc)) from None
        if take(held, "forge", owner, limit, LOCK_WAIT) is None:
            raise CheckError("another write holds the forge (path class: cache/forge.lock)")
        try:
            yield
        finally:
            clear_if_same(held, token)

    def write(self, subject: str, records: dict[str, Any]) -> None:
        """Each record a temporary file and a rename, then one commit of exactly those files."""
        for rel, value in records.items():
            target = self.forge / rel
            target.parent.mkdir(mode=0o700, exist_ok=True)
            handle, tmp = tempfile.mkstemp(dir=target.parent, prefix="tmp")
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as out:
                    out.write(dump(value))
                os.replace(tmp, target)
            finally:
                Path(tmp).unlink(missing_ok=True)
        paths = [f"forge/{rel}" for rel in records]
        self.run_git("add", "--", *paths)
        self.run_git(
            *("-c", f"user.name={self.person}", "-c", f"user.email={self.person}@personal.invalid"),
            *("-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "-m", subject),
            "--",
            *paths,
        )

    def next_number(self) -> int:
        return max([0, *self.numbers("issues"), *self.numbers("pulls")]) + 1

    def base_record(self, number: int, title: str, body: str) -> dict:
        at = self.now()
        return {
            "number": number,
            "title": title,
            "body": body,
            "state": "open",
            "user": {"login": self.person},
            "labels": [],
            "created_at": at,
            "updated_at": at,
            "closed_at": None,
        }

    def create_issue(self, title: str, body: str, labels: list[str]) -> int:
        with self.locked():
            number = self.next_number()
            record = self.base_record(number, title, body)
            record["labels"] = [{"name": label} for label in labels]
            self.write(
                f"forge: issue {number}",
                {f"issues/{number}.json": record, f"comments-{number}.json": []},
            )
        return number

    def record_pull(
        self, title: str, body: str, head_sha: str, head_ref: str, base_ref: str
    ) -> int:
        """The review record of a local branch (rule 6)."""
        with self.locked():
            number = self.next_number()
            record = self.base_record(number, title, body)
            record.update(
                draft=False,
                merged=False,
                merged_at=None,
                head={"sha": head_sha, "ref": head_ref},
                base={"ref": base_ref},
            )
            self.write(
                f"forge: pull {number}",
                {f"pulls/{number}.json": record, f"comments-{number}.json": []},
            )
        return number

    def comment(self, number: int, body: str) -> None:
        with self.locked():
            if (
                not (self.forge / "issues" / f"{number}.json").is_file()
                and not (self.forge / "pulls" / f"{number}.json").is_file()
            ):
                raise CheckError("a comment needs an issue or a pull (path class: forge)")
            existing = self.load(f"comments-{number}.json") or []
            at = self.now()
            mark = {"slug": AGENT_APP} if self.env.get(SESSION_SETTING) else None
            entry = {
                "id": number * 1_000_000 + len(existing) + 1,
                "body": body,
                "user": {"login": self.person},
                "created_at": at,
                "updated_at": at,
                "performed_via_github_app": mark,
            }
            self.write(
                f"forge: comment on {number}", {f"comments-{number}.json": [*existing, entry]}
            )
