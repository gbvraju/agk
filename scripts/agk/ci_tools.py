"""ci_tools.py: the pinned CI test tools of `config/ci-tools.txt` (brief #698, ADR-0328).

    python3 scripts/agk/ci_tools.py check [--root DIR] [--upstream] [--responses DIR]

`check` reads the pin file the governance workflow's `Install tooling` step installs: one exact
`<name>==<version>` per line, in name order, one line per tool, `#` comments allowed. It prints
`pin <name> <version>` per line and `ok ci-tools: <n> pins`; a line that is not an exact pin, a
repeated tool, a tool out of name order, an empty or a missing file fails (exit 1) naming the path,
never a value (principle 8). It makes no network call.

`--upstream` (a person's run) reads the package index's JSON once per pin and prints, per pin,
`behind <name> <pinned> newest <newest> gap <days> days`, `current <name> <version>` or
`unknown <name> <version>` for an upstream it cannot read, then `pins_behind` and
`pins_oldest_gap_days` (SPEC-0047 rule 8's numbers; `unknown`, never `0`, when nothing was read).
`--responses DIR` reads saved responses `DIR/<name>.json` instead of the network. A person opens
the update pull request from that output. Exit 2 for a usage error.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, repo_root

NAME = "ci-tools"
PIN_FILE = "config/ci-tools.txt"
USAGE = "usage: ci_tools.py check [--root DIR] [--upstream] [--responses DIR]"
INDEX = "https://pypi.org/pypi/{name}/json"
LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][0-9A-Za-z.+!-]*)$")
Fetch = Callable[[str], "dict | None"]


def read_pins(root: Path) -> list[tuple[str, str]]:
    """The pins of the pin file, in file order; a malformed file raises naming the path only."""
    path = root / PIN_FILE
    if not path.is_file():
        raise CheckError(f"no pin file (path: {PIN_FILE})")
    pins: list[tuple[str, str]] = []
    seen: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        match = LINE.match(text)
        if not match:
            raise CheckError(f"line {number} is not <name>==<version> (path: {PIN_FILE})")
        key = match.group(1).lower()
        if key in seen:
            raise CheckError(f"line {number} repeats a tool (path: {PIN_FILE})")
        if pins and key < pins[-1][0].lower():
            raise CheckError(f"line {number} is out of name order (path: {PIN_FILE})")
        seen.add(key)
        pins.append((match.group(1), match.group(2)))
    if not pins:
        raise CheckError(f"no pin (path: {PIN_FILE})")
    return pins


def fetch_index(name: str) -> dict | None:
    """One GET of the package index's JSON for one tool; None when it cannot be read."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["curl", "-fsS", "--max-time", "30", INDEX.format(name=name)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return parse(proc.stdout) if proc.returncode == 0 else None


def saved_responses(folder: Path) -> Fetch:
    def fetch(name: str) -> dict | None:
        path = folder / f"{name}.json"
        return parse(path.read_text(encoding="utf-8")) if path.is_file() else None

    return fetch


def parse(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def released(data: dict, version: str) -> date | None:
    """The upload date of a version in an index answer, or None."""
    files = (data.get("releases") or {}).get(version)
    if not isinstance(files, list):
        return None
    days = [
        f["upload_time_iso_8601"][:10]
        for f in files
        if isinstance(f, dict) and isinstance(f.get("upload_time_iso_8601"), str)
    ]
    try:
        return date.fromisoformat(min(days)) if days else None
    except ValueError:
        return None


def upstream_line(name: str, pinned: str, data: dict | None) -> tuple[str, int | None, bool]:
    """One output line, the gap in days when behind, and whether the upstream was read."""
    info = (data or {}).get("info")
    newest = info.get("version") if isinstance(info, dict) else None
    if not isinstance(newest, str) or not newest:
        return f"unknown {name} {pinned}", None, False
    if newest == pinned:
        return f"current {name} {pinned}", None, True
    old, new = released(data or {}, pinned), released(data or {}, newest)
    if old is None or new is None:
        return f"unknown {name} {pinned}", None, False
    gap = max(0, (new - old).days)
    return f"behind {name} {pinned} newest {newest} gap {gap} days", gap, True


def report(pins: list[tuple[str, str]], fetch: Fetch) -> list[str]:
    lines: list[str] = []
    gaps: list[int] = []
    read = unknown = 0
    for name, version in pins:
        text, gap, ok = upstream_line(name, version, fetch(name))
        lines.append(text)
        read += ok
        unknown += not ok
        if gap is not None:
            gaps.append(gap)
    lines.append(f"pins_behind {len(gaps) if read else 'unknown'}")
    lines.append(f"pins_oldest_gap_days {max(gaps) if gaps else (0 if read else 'unknown')}")
    lines.append(f"ok {NAME}: {len(pins)} pins, {len(gaps)} behind, {unknown} unknown")
    return lines


def options(args: list[str]) -> dict | None:
    if not args or args[0] != "check":
        return None
    found: dict = {"root": None, "upstream": False, "responses": None}
    rest = args[1:]
    while rest:
        flag = rest.pop(0)
        if flag == "--upstream":
            found["upstream"] = True
        elif flag in ("--root", "--responses") and rest:
            found[flag[2:]] = Path(rest.pop(0))
        else:
            return None
    if found["responses"] is not None and not found["upstream"]:
        return None
    return found


def main(argv: list[str] | None = None) -> int:
    opts = options(list(sys.argv[1:] if argv is None else argv))
    if opts is None:
        print(USAGE)
        return 2
    try:
        root = opts["root"] or repo_root()
        pins = read_pins(root)
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 1
    if not opts["upstream"]:
        print("\n".join(f"pin {n} {v}" for n, v in pins))
        print(f"ok {NAME}: {len(pins)} pins")
        return 0
    responses = opts["responses"]
    fetch = saved_responses(responses) if responses is not None else fetch_index
    print("\n".join(report(pins, fetch)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
