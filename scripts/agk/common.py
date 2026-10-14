"""Shared helpers for the agk checks. Standard library only; no network."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path

REQ_ID = re.compile(r"REQ-\d{3}")
REQ_HEADER = re.compile(r"^###\s+(REQ-\d{3})\b")
STATUS_LINE = re.compile(r"^- Status:\s*(.*?)\s*$")
ALLOWED_STATUS = ("planned", "in-progress", "done")


class CheckError(Exception):
    """A check failed; the message names a setting or path class, never a value."""


def git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise CheckError(f"git {args[0]} failed")
    return proc.stdout


def repo_root() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise CheckError("not inside a git repository")
    return Path(proc.stdout.strip())


def _verify(root: Path, ref: str) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def resolve_base(root: Path, cli_base: str | None = None) -> str | None:
    """Base commit: --base, AGK_BASE, GITHUB_BASE_REF, then the default branch (agk.toml or main).

    Returns None only outside CI when nothing resolves (the check is then skipped).
    """
    explicit = cli_base or os.environ.get("AGK_BASE")
    if explicit:
        sha = _verify(root, explicit)
        if not sha:
            raise CheckError("the given base ref does not resolve")
        return sha
    ref = os.environ.get("GITHUB_BASE_REF")
    if ref:
        for candidate in (f"origin/{ref}", ref):
            sha = _verify(root, candidate)
            if sha:
                return sha
        raise CheckError("GITHUB_BASE_REF does not resolve")
    branch = load_config(root)["default_branch"]
    for candidate in (f"origin/{branch}", branch):
        sha = _verify(root, candidate)
        if sha:
            return sha
    if os.environ.get("CI"):
        raise CheckError("no base ref resolves in CI")
    return None


def merge_base(root: Path, base: str) -> str:
    out = git(root, "merge-base", base, "HEAD", check=False).strip()
    if not out:
        raise CheckError("no merge base with the base ref (shallow clone?)")
    return out


def changed_files(root: Path, mb: str) -> dict[str, str]:
    """Path -> status letter (A, M, D, ...) from merge base to the working tree."""
    result: dict[str, str] = {}
    tokens = git(root, "diff", "-z", "--name-status", "--no-renames", mb).split("\0")
    i = 0
    while i + 1 < len(tokens):
        result[tokens[i + 1]] = tokens[i][:1]
        i += 2
    untracked = git(root, "ls-files", "-z", "--others", "--exclude-standard")
    for path in filter(None, untracked.split("\0")):
        result[path] = "A"
    return result


def changed_lines(root: Path, mb: str, path: str) -> list[str]:
    """Added/removed lines of one file (with +/- prefix), hunk bodies only."""
    out = git(root, "diff", "-U0", "--no-renames", mb, "--", path)
    lines: list[str] = []
    in_hunk = False
    for line in out.splitlines():
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line[:1] in "+-":
            lines.append(line)
    return lines


def show(root: Path, rev: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"], cwd=root, capture_output=True, text=True
    )
    return proc.stdout if proc.returncode == 0 else None


def read_list(text: str) -> list[str]:
    """Non-blank, non-comment lines."""
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def matches(path: str, entry: str) -> bool:
    return path.startswith(entry) if entry.endswith("/") else path == entry


def parse_requirements(text: str) -> list[dict]:
    """Each: {id, status (str|None), status_count, line}."""
    reqs: list[dict] = []
    for n, line in enumerate(text.splitlines(), 1):
        header = REQ_HEADER.match(line)
        if header:
            reqs.append({"id": header.group(1), "status": None, "status_count": 0, "line": n})
            continue
        status = STATUS_LINE.match(line)
        if status and reqs:
            reqs[-1]["status"] = status.group(1)
            reqs[-1]["status_count"] += 1
    return reqs


DEFAULT_CONFIG = {
    "default_branch": "main",
    "test_dirs": ["tests"],
    "lint_paths": ["scripts/agk", "tests/kit", ".claude/hooks"],
    "project_tests": "",
    "test_patterns": ["test_*.py"],
    "mode": "",
}


def load_config(root: Path) -> dict:
    """agk.toml first, then [tool.agk] in pyproject.toml (earlier installs); defaults fill gaps."""
    cfg = {k: list(v) if isinstance(v, list) else v for k, v in DEFAULT_CONFIG.items()}
    source: dict = {}
    agk_toml = root / "agk.toml"
    pyproject = root / "pyproject.toml"
    if agk_toml.is_file():
        source = tomllib.loads(agk_toml.read_text(encoding="utf-8"))
    elif pyproject.is_file():
        source = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}).get("agk", {})
    for key in DEFAULT_CONFIG:
        if key in source:
            cfg[key] = source[key]
    return cfg


def detect_default_branch(target: Path) -> str | None:
    """Default branch from .git files, without calling git; None when it cannot be told."""
    git = target / ".git"
    if not git.is_dir():
        return None
    head = git / "refs" / "remotes" / "origin" / "HEAD"
    prefix = "ref: refs/remotes/origin/"
    if head.is_file():
        line = head.read_text(encoding="utf-8").strip()
        return line[len(prefix) :] if line.startswith(prefix) and line[len(prefix) :] else None
    config = git / "config"
    has_origin = (git / "refs" / "remotes" / "origin").exists() or (
        config.is_file() and '[remote "origin"]' in config.read_text(encoding="utf-8")
    )
    if has_origin:
        return None
    line = (git / "HEAD").read_text(encoding="utf-8").strip() if (git / "HEAD").is_file() else ""
    prefix = "ref: refs/heads/"
    return line[len(prefix) :] if line.startswith(prefix) and line[len(prefix) :] else None


def test_dirs(root: Path, cli_dirs: Sequence[str] | None = None) -> list[str]:
    if cli_dirs:
        return list(cli_dirs)
    return list(load_config(root)["test_dirs"])


def find_markers(
    root: Path,
    dirs: Sequence[str],
    patterns: Sequence[str] = ("test_*.py",),
    exclude: Sequence[str] = (),
) -> dict[str, list[str]]:
    """REQ id -> sorted files (relative) matching patterns under dirs that contain the marker.

    Files under an excluded directory are skipped unless a listed dir is inside that directory.
    """
    found: dict[str, set[str]] = {}
    skip = tuple(
        e.strip("/") + "/"
        for e in exclude
        if not any(d.strip("/").startswith(e.strip("/")) for d in dirs)
    )
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        paths = {p for pattern in patterns for p in base.rglob(pattern)}
        for path in sorted(paths):
            rel = path.relative_to(root).as_posix()
            if not path.is_file() or "__pycache__" in path.parts or rel.startswith(skip):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for req in set(REQ_ID.findall(text)):
                found.setdefault(req, set()).add(rel)
    return {k: sorted(v) for k, v in found.items()}


def markers_for(root: Path, cli_dirs: Sequence[str] | None = None) -> dict[str, list[str]]:
    """Markers from the configured directories and patterns (agk.toml).

    In adopt mode tests/kit is left out of the search unless a listed directory is inside it.
    """
    cfg = load_config(root)
    exclude = ["tests/kit"] if cfg["mode"] == "adopt" else []
    return find_markers(root, test_dirs(root, cli_dirs), cfg["test_patterns"], exclude)


def run(name: str, fn: Callable[[], int]) -> int:
    try:
        return fn()
    except CheckError as exc:
        print(f"FAIL {name}: {exc}")
        return 1


def base_context(root: Path, name: str, cli_base: str | None) -> str | None:
    """Merge base for diff checks, or None (with a notice) when no base is available."""
    base = resolve_base(root, cli_base)
    if base is None:
        print(f"{name}: no base ref available outside CI; skipped")
        return None
    return merge_base(root, base)


def base_arg(argv: Sequence[str] | None) -> str | None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--base" in args:
        i = args.index("--base")
        if i + 1 >= len(args):
            raise CheckError("--base needs a value")
        return args[i + 1]
    return None
