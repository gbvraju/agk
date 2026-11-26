# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Read the test suite as a whole: size, growth and five candidate lists (brief #2007, ADR-0831).

For the test files of the `[proof]` areas (absent: `tests/` with `test_*.py`) it prints the files,
the test functions (read with `ast`, never imported or run), the test lines, the code lines of the
`[[testing.map]]` `code` entries and their ratio; with `--since YYYY-MM-DD` the `def test_` lines
git added and removed since that day; and five lists, each a candidate for a person to review,
never a ruling: equal tests, wording-only tests, brief-pinned names, unselected files and the
slowest files of the newest prepush record. `--json` prints one object; `--limit N` (default 20)
caps each list. It reads tracked files and local git only, writes nothing, makes no network call
and exits 0; a malformed option exits 2 naming the option, a malformed setting naming the setting.
Usage: python3 scripts/agk/test_audit.py [--json] [--since YYYY-MM-DD] [--limit N]
"""

from __future__ import annotations

import ast
import functools
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, config_source, git, proof_areas, repo_root, utf8_output

USAGE = "usage: test_audit.py [--json] [--since YYYY-MM-DD] [--limit N]"
DEFAULT_AREA = {"dirs": ["tests"], "patterns": ["test_*.py"]}
PINNED = re.compile(r"(brief|adr|amendment)_?\d+", re.I)
DEF_TEST = re.compile(r"^([+-])\s*(?:async\s+)?def test_")
RUNS = frozenset({"run", "check_output", "check_call", "Popen", "call"})
UNKNOWN = "per-file timing: unknown"
NO_MAP = "no testing map"
EVIDENCE = "agk-evidence"  # prepush's record folder in the git common dir (EVIDENCE_FOLDER)


@functools.cache
def glob_rx(glob: str) -> re.Pattern[str]:
    """A testing glob: `**` crosses folders, `*` and `?` stay in one, a trailing `/` is a folder."""
    if glob.endswith("/"):
        return re.compile(re.escape(glob) + ".*")
    out = glob.replace("**/", "\0").replace("**", "\1")
    out = re.escape(out).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    return re.compile(out.replace("\0", "(?:.*/)?").replace("\1", ".*"))


def is_test(path: str, area: dict) -> bool:
    name = path.rsplit("/", 1)[-1]
    inside = any(
        d.strip("/") in ("", ".") or path.startswith(d.strip("/") + "/") for d in area["dirs"]
    )
    return inside and any(glob_rx(p.replace("/", "")).fullmatch(name) for p in area["patterns"])


def testing_map(root: Path) -> list[str] | None:
    """The globs that name a test file for list (d), or None without a `[testing]` map."""
    table = config_source(root).get("testing")
    if table is None:
        return None
    if not isinstance(table, dict):
        raise CheckError("[testing] must be a table (setting: testing)")
    globs: list[str] = []
    for key in ("whole_tests", "always_full"):
        value = table.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise CheckError(f"{key} must be a list of paths (setting: testing.{key})")
        globs += value
    entries = table.get("map")
    if entries is None:
        return globs or None
    if not isinstance(entries, list):
        raise CheckError("map must be a list of code and tests entries (setting: testing.map)")
    for n, entry in enumerate(entries):
        tests = entry.get("tests") if isinstance(entry, dict) else None
        if not isinstance(tests, list) or not all(isinstance(t, str) for t in tests):
            raise CheckError(f"a map entry needs a tests list (setting: testing.map[{n}].tests)")
        globs += tests
    return globs


def code_globs(root: Path) -> list[str]:
    table = config_source(root).get("testing") or {}
    entries = table.get("map") or [] if isinstance(table, dict) else []
    return [e["code"] for e in entries if isinstance(e, dict) and isinstance(e.get("code"), str)]


def body_key(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    body = list(node.body)
    first = body[0].value if body and isinstance(body[0], ast.Expr) else None
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        body = body[1:]
    return "\n".join(ast.dump(s) for s in body)


def mentions_md(node: ast.AST, md_names: set[str], md_helpers: set[str]) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and ".md" in sub.value:
            return True
        if isinstance(sub, ast.Name) and (sub.id in md_names or sub.id in md_helpers):
            return True
    return False


def string_in(test: ast.AST) -> bool:
    if isinstance(test, ast.BoolOp):
        return all(string_in(v) for v in test.values)
    return isinstance(test, ast.Compare) and all(
        isinstance(o, ast.In | ast.NotIn) for o in test.ops
    )


def runs_code(node: ast.AST, kit_names: set[str]) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in kit_names | {"subprocess"}:
            return True
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr in RUNS
        ):
            return True
    return False


def read_file(rel: str, tree: ast.Module, kit: set[str]) -> list[tuple[str, str, bool]]:
    """(name, body key, wording-only) of each test function of one parsed file."""
    kit_names: set[str] = set()
    for n in tree.body:
        if isinstance(n, ast.Import):
            kit_names |= {(a.asname or a.name) for a in n.names if a.name.split(".")[0] in kit}
        elif isinstance(n, ast.ImportFrom) and n.module in kit:
            kit_names |= {(a.asname or a.name) for a in n.names}
    md_names = {
        t.id
        for n in tree.body
        if isinstance(n, ast.Assign) and mentions_md(n.value, set(), set())
        for t in n.targets
        if isinstance(t, ast.Name)
    }
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    others = [f for f in funcs if not f.name.startswith("test")]
    helpers = {f.name for f in others if mentions_md(f, md_names, set())}
    kit_names |= {
        f.name for f in others if runs_code(f, kit_names)
    }  # a local helper that runs code
    rows = []
    for f in funcs:
        if not f.name.startswith("test"):
            continue
        asserts = [s.test for s in ast.walk(f) if isinstance(s, ast.Assert)]
        wording = (
            bool(asserts)
            and all(string_in(t) for t in asserts)
            and mentions_md(f, md_names, helpers)
            and not runs_code(f, kit_names)
        )
        rows.append((f"{rel}::{f.name}", body_key(f), wording))
    return rows


def since_lines(root: Path, day: str, dirs: list[str]) -> dict:
    """A shallow clone's boundary commits add every file, so they are left out (`--not`)."""
    shallow = Path(git(root, "rev-parse", "--git-path", "shallow", check=False).strip() or "none")
    shallow = shallow if shallow.is_absolute() else root / shallow
    cut = shallow.read_text(encoding="utf-8").split() if shallow.is_file() else []
    since = f"--since={day} 00:00:00 +0000"
    out = git(
        root,
        "log",
        since,
        "-p",
        "--format=",
        "HEAD",
        *(["--not", *cut] if cut else []),
        "--",
        *dirs,
        check=False,
    )
    signs = [m.group(1) for m in map(DEF_TEST.match, out.splitlines()) if m]
    return {"day": day, "added": signs.count("+"), "removed": signs.count("-")}


def slowest(root: Path, limit: int) -> dict:
    common = git(root, "rev-parse", "--git-common-dir", check=False).strip()
    folder = (root / common / EVIDENCE) if common else None
    records = (
        sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if folder and folder.is_dir()
        else []
    )
    seconds: dict[str, float] = {}
    try:
        record = json.loads(records[-1].read_text(encoding="utf-8")) if records else {}
        for step in record.get("steps") or []:
            for run in step.get("runs") or []:
                for row in (run.get("timing") or {}).get("files") or []:
                    seconds[row["path"]] = max(seconds.get(row["path"], 0), row["seconds"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        seconds = {}
    if not seconds:
        return {"note": UNKNOWN}
    ranked = sorted(seconds.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"count": len(ranked), "files": [{"path": p, "seconds": s} for p, s in ranked[:limit]]}


def audit(root: Path, since: str | None, limit: int) -> dict:
    areas = proof_areas(root) or [DEFAULT_AREA]
    named = testing_map(root)
    tracked = git(root, "ls-files", check=False).splitlines()
    kit = {Path(p).stem for p in tracked if p.startswith("scripts/agk/") and p.endswith(".py")}
    files = sorted(p for p in tracked if any(is_test(p, a) for a in areas))
    rows, not_read, lines, other = [], [], 0, 0
    for rel in files:
        if not rel.endswith(".py"):
            other += 1
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        lines += len(text.splitlines())
        try:
            rows += read_file(rel, ast.parse(text), kit)
        except (SyntaxError, ValueError):
            not_read.append(rel)
    code_rx = [glob_rx(g) for g in code_globs(root)]
    code = {p for p in tracked if any(rx.fullmatch(p) for rx in code_rx)}
    code_lines = sum(
        len((root / p).read_text(encoding="utf-8", errors="replace").splitlines())
        for p in code
        if (root / p).is_file()
    )
    groups: dict[str, list[str]] = {}
    for name, key, _ in rows:
        groups.setdefault(key, []).append(name)
    equal = sorted(g for g in groups.values() if len(g) > 1)
    wording = [n for n, _, w in rows if w]
    pinned = [n for n, _, _ in rows if PINNED.search(n.rsplit("::", 1)[1])]
    unselected = (
        {"note": NO_MAP}
        if named is None
        else capped([f for f in files if not any(glob_rx(g).fullmatch(f) for g in named)], limit)
    )
    py = [f for f in files if f.endswith(".py")]
    dirs = sorted({d for a in areas for d in a["dirs"]})
    return {
        "files": len(py),
        "functions": len(rows),
        "test_lines": lines,
        "code_lines": code_lines,
        "ratio": round(lines / code_lines, 2) if code_lines else None,
        "other_files": other,
        "not_read": not_read,
        "since": since_lines(root, since, dirs) if since else None,
        "equal": {
            "count": len(equal),
            "extra": sum(len(g) - 1 for g in equal),
            "groups": equal[:limit],
        },
        "wording": capped(wording, limit),
        "pinned": capped(pinned, limit),
        "unselected": unselected,
        "slowest": slowest(root, limit),
    }


def capped(names: list[str], limit: int) -> dict:
    return {"count": len(names), "names": names[:limit]}


def report(got: dict) -> list[str]:
    out = [
        f"test audit: {got['files']} test files, {got['functions']} test functions, "
        f"{got['test_lines']} test lines; code lines {got['code_lines']} (ratio {got['ratio']})"
    ]
    if got["other_files"]:
        out.append(f"other test files: {got['other_files']}, not read")
    out += [f"not read: {f}" for f in got["not_read"]]
    if got["since"]:
        s = got["since"]
        out.append(f"since {s['day']}: {s['added']} test functions added, {s['removed']} removed")
    eq = got["equal"]
    out.append(f"equal tests: {eq['count']} groups, {eq['extra']} extra copies")
    out += ["  " + ", ".join(g) for g in eq["groups"]]
    for key, title in (
        ("wording", "wording-only tests"),
        ("pinned", "brief-pinned names"),
        ("unselected", "unselected files"),
    ):
        part = got[key]
        if "note" in part:
            out.append(f"{title}: {part['note']}")
        else:
            out += [f"{title}: {part['count']}", *(f"  {n}" for n in part["names"])]
    slow = got["slowest"]
    if "note" in slow:
        out.append(slow["note"])
    else:
        out += [
            f"slowest files: {slow['count']}",
            *(f"  {r['path']} {r['seconds']}s" for r in slow["files"]),
        ]
    out.append(
        "each list is a candidate for a person to review, never a ruling (docs/guides/testing.md)"
    )
    return out


def parse(args: list[str]) -> dict | str:
    """The options, or the name of the option that is missing or malformed."""
    options: dict = {"json": False, "since": None, "limit": 20}
    while args:
        flag = args.pop(0)
        if flag == "--json":
            options["json"] = True
            continue
        if flag not in ("--since", "--limit") or not args:
            return flag
        value = args.pop(0)
        if flag == "--limit":
            if not value.isdigit() or int(value) < 1:
                return flag
            options["limit"] = int(value)
        else:
            try:
                date.fromisoformat(value)
            except ValueError:
                return flag
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                return flag
            options["since"] = value
    return options


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if isinstance(options, str):
        print(f"{USAGE}\n(refused: option {options} is missing or malformed)", file=sys.stderr)
        return 2
    try:
        got = audit(repo_root(), options["since"], options["limit"])
    except CheckError as err:
        print(f"test_audit: {err}", file=sys.stderr)
        return 2
    print(json.dumps(got, indent=2) if options["json"] else "\n".join(report(got)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
