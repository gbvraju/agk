# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The one whole-history secret scan of an adopted project (brief #1835, ADR-0764; REQ-063).

Usage: python3 scripts/agk/history_scan.py run [--root DIR] [--write] [--sidecar DIR]

Runs gitleaks once over every local and remote-tracking ref (`--log-opts=--all`), offline: no
fetch, no shell, the report in a private temporary file outside the repository, removed after.
Only each finding's `RuleID` and `File` are read; a finding is printed as its rule id, count and
path class, never a path, value, commit or message, then the leaked-secret page. With `--write`
the run is recorded in `config/agk-baseline/history-scan.json` (with `--sidecar`, in the
sidecar's `records/`); a `clean` or `findings` record is never rewritten, an `incomplete` one is
replaced by a later complete scan, and a scan that could not run writes nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import guard  # noqa: E402
from common import GITLEAKS_INSTALL, matches, read_list, utf8_output  # noqa: E402

TIMEOUT = 600  # seconds; a constant, never a setting (Q-HB-2)
RECORD = "config/agk-baseline/history-scan.json"
PRIVATE = "records/history-scan.json"
CLASS = "(path class: config/agk-baseline/)"
LEAK_RUNBOOK = (  # prepush.LEAK_RUNBOOK, kept equal by a test (prepush imports far more)
    "if this is a finding: follow docs/runbooks/leaked-secret.md; never paste the value anywhere"
)
SHALLOW = "shallow clone (setting: git fetch --unshallow, run by a person)"
NOT_INSTALLED = (
    "history scan: not run: gitleaks is not installed (tool: gitleaks); "
    + GITLEAKS_INSTALL
    + "; run history_scan.py run --write again after"
)
FAILED = "history scan: not run: the scanner failed (tool: gitleaks)"
SYMLINK = f"history scan: record not written: a symbolic link is refused {CLASS}"
NEVER = f"the whole history was never scanned for secrets; run history_scan.py run --write {CLASS}"
UNREADABLE = f"the record cannot be read {CLASS}"
USAGE = "usage: history_scan.py run [--root DIR] [--write] [--sidecar DIR]"


def git(root: Path, *args: str) -> tuple[int, str]:
    done = subprocess.run(  # nosec B603 B607 - fixed read-only git argument list, no shell
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return done.returncode, done.stdout.strip()


def path_class(rel: str, entries: list[str]) -> str:
    """`init.path_class` (init is not installed in a project): the protected entry, or the top
    folder, or the repository root."""
    for entry in entries:
        if matches(rel, entry):
            return entry
    return rel.split("/", 1)[0] + "/" if "/" in rel else "(repository root)"


def version(tool: str) -> str:
    try:
        done = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [tool, "version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        out = done.stdout.strip().splitlines() if done.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        out = []
    return out[0].strip().removeprefix("v") if out and out[0].strip() else "unknown"


def scan(tool: str, root: Path) -> tuple[list[tuple[str, str]] | None, str]:
    """((rule id, file) of each finding, or None when the scanner failed; '' or the timeout)."""
    fd, name = tempfile.mkstemp(prefix="agk-history-", suffix=".json")  # 0600, outside the root
    os.close(fd)
    try:
        cmd = [tool, "git", "--no-banner", "--redact", "--exit-code", "1", "--log-opts=--all"]
        cmd += ["--report-format", "json", "--report-path", name, str(root)]
        try:
            done = subprocess.run(  # nosec B603 - fixed argument list, no shell; output never shown
                cmd, capture_output=True, timeout=TIMEOUT, check=False
            )
        except subprocess.TimeoutExpired:
            return [], f"not finished within {TIMEOUT} s"
        except OSError:
            return None, ""
        if done.returncode not in (0, 1):
            return None, ""
        try:
            rows = json.loads(Path(name).read_text(encoding="utf-8") or "[]")
            return [(str(r["RuleID"]), str(r["File"])) for r in rows], ""
        except (OSError, ValueError, TypeError, KeyError):
            return None, ""
    finally:
        Path(name).unlink(missing_ok=True)


def read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save(path: Path, text: str, private: bool) -> str | None:
    """Write TEXT at PATH; a refusal line, else None."""
    kinds = sorted({f.kind for f in guard.scan_text(text)})
    if kinds:
        return f"history scan: record not written: it holds a secret shape (kind: {kinds[0]})"
    if any(p.is_symlink() for p in (path, path.parent)):
        return SYMLINK
    if private:
        from survey import write_private  # noqa: PLC0415 - the sidecar's writer (rule 28)

        write_private(path, text)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return None


def run(root: Path, sidecar: Path | None = None, write: bool = False) -> tuple[int, list[str]]:
    """(exit code, lines) of one scan; WRITE records it."""
    path = Path(sidecar) / PRIVATE if sidecar else Path(root) / RECORD
    old = read(path) if write and path.is_file() else None
    if old and old.get("outcome") in ("clean", "findings"):
        outcome = old["outcome"]
        return (0 if outcome == "clean" else 1), [
            f"history scan: recorded {old.get('scanned')} ({outcome})"
        ]
    code, head = git(root, "rev-parse", "--verify", "-q", "HEAD")
    if code != 0 or not head:
        return 0, ["history scan: nothing to scan (no commit)"]
    tool = shutil.which("gitleaks")
    if tool is None:
        return 1, [NOT_INSTALLED]
    found, reason = scan(tool, root)
    if found is None:
        return 1, [FAILED]
    if not reason and git(root, "rev-parse", "--is-shallow-repository")[1] == "true":
        reason = SHALLOW
    listed = Path(root) / "config" / "protected-paths.txt"
    entries = read_list(listed.read_text(encoding="utf-8")) if listed.is_file() else []
    counts = Counter((rule, path_class(file, entries)) for rule, file in found)
    rows = [{"rule": r, "class": c, "count": n} for (r, c), n in sorted(counts.items())]
    lines = [f"history scan: {x['rule']} {x['count']} (path class: {x['class']})" for x in rows]
    commits = int(git(root, "rev-list", "--all", "--count")[1] or 0)
    tool_version = version(tool)
    outcome = "incomplete" if reason else ("findings" if rows else "clean")
    if outcome == "incomplete":
        lines.append(f"history scan: incomplete ({reason})")
    elif outcome == "clean":
        lines.append(f"history scan: clean ({commits} commits, gitleaks {tool_version})")
    if rows:
        lines.append(LEAK_RUNBOOK)
    shapes = sorted({f.kind for f in guard.scan_text("\n".join(lines))})
    if shapes:  # a corrupted rule id: nothing of it is printed
        return 1, [f"history scan: record not written: it holds a secret shape (kind: {shapes[0]})"]
    if write:
        note = "ignore file present" if (Path(root) / ".gitleaksignore").exists() else ""
        data = {
            "scanned": datetime.now(UTC).date().isoformat(),
            "head": head,
            "commits": commits,
            "tool": f"gitleaks {tool_version}",
            "outcome": outcome,
            "reason": reason,
            "note": note,
            "findings": rows,
        }
        refused = save(path, json.dumps(data, indent=1, sort_keys=True) + "\n", bool(sidecar))
        if refused:
            return 1, [*lines, refused]
    return (0 if outcome == "clean" else 1), lines


def state(path: Path) -> tuple[str, str]:
    """(`ok` or `warn`, the text) of a record, as doctor and `personal.py status` print it."""
    if not path.exists():
        return "warn", NEVER
    data = read(path)
    if data is None:
        return "warn", UNREADABLE
    outcome = data.get("outcome")
    if outcome == "clean":
        return "ok", f"scanned {data.get('scanned')}, {data.get('commits')} commits, no finding"
    if outcome == "incomplete":
        return "warn", f"incomplete ({data.get('reason')}); run it again"
    if outcome == "findings":
        rows = data.get("findings") or []
        try:
            n = sum(int(r["count"]) for r in rows)
            rules = ", ".join(sorted({str(r["rule"]) for r in rows}))
            classes = ", ".join(sorted({str(r["class"]) for r in rows}))
        except (TypeError, KeyError, ValueError):
            return "warn", UNREADABLE
        return "warn", (
            f"{n} findings in history ({rules}; path classes {classes}); follow "
            "docs/runbooks/leaked-secret.md, revoke each at its provider; a revoked value in "
            "history is harmless"
        )
    return "warn", UNREADABLE


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] != ["run"]:
        print(USAGE, file=sys.stderr)
        return 2
    options: dict = {"--root": ".", "--sidecar": None}
    write_record, rest = False, args[1:]
    while rest:
        flag = rest.pop(0)
        if flag == "--write":
            write_record = True
        elif flag in options and rest:
            options[flag] = rest.pop(0)
        else:
            print(USAGE, file=sys.stderr)
            return 2
    sidecar = Path(options["--sidecar"]) if options["--sidecar"] else None
    code, lines = run(Path(options["--root"]).resolve(), sidecar, write_record)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
