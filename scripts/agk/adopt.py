"""agk adopt: install the kit into an existing repository, touching no product file (SPEC-0002).

Usage: python3 scripts/agk/adopt.py TARGET [--dry-run]

Standard library only. No network, no git or gh calls, no writes outside TARGET. Target files are
data: they are compared byte for byte, scanned for agk's own marked blocks and for the stamp, and
listed by name; they are never imported, executed or parsed as code. Refuses (exit 1) before any
write; nothing is written when any file conflicts.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from common import detect_default_branch, experimental_enabled, matches, read_list
from init import (
    CREATE_ONLY,
    DATE_RE,
    KIT_ROOT,
    MANIFEST,
    PLACEHOLDER,
    Refusal,
    check_interpreter,
    install_mode,
    passes_symlink,
    path_class,
    print_branch_rules,
    render,
    slug,
)
from reviewers import parse, render_codeowners

TEST_PATTERNS = ("*_test.py", "test_*.py")
SKIP_DIRS = {
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    "build",
    "dist",
    "site-packages",
    "tox",
}
KIT_DIRS = ("tests/kit", "scripts/agk")
MARKERS = {
    "hash": ("# >>> agk", "# <<< agk"),
    "html": ("<!-- >>> agk -->", "<!-- <<< agk -->"),
}
ABSENT_AS_BLOCK = {".gitignore"}


def toml_list(items: list[str]) -> str:
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


def detect_tests(root: Path) -> tuple[list[str], list[str]]:
    """Directories (topmost) holding *_test.py or test_*.py files, and the patterns that matched."""
    dirs: set[str] = set()
    found: set[str] = set()
    for here, dirnames, filenames in os.walk(root):
        rel_here = Path(here).relative_to(root).as_posix()
        rel_here = "" if rel_here == "." else rel_here
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in SKIP_DIRS
            and not any(
                f"{rel_here}/{d}".lstrip("/") == k
                or f"{rel_here}/{d}".lstrip("/").startswith(k + "/")
                for k in KIT_DIRS
            )
        ]
        for name in filenames:
            for pattern in TEST_PATTERNS:
                if fnmatch.fnmatch(name, pattern):
                    found.add(pattern)
                    dirs.add(rel_here)
    top = sorted(d for d in dirs if d and not any(d.startswith(e + "/") for e in dirs if e))
    if "" in dirs:
        top = ["."]
    if not top:
        return ["tests"], ["test_*.py"]
    return top, sorted(found)


def read_stamp(target: Path) -> dict:
    """Values of an existing adopt install (agk.toml), reused so a second run is identical."""
    path = target / "agk.toml"
    if install_mode(target) != "adopt":
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    return data


def block_of(style: str, body: str) -> str:
    begin, end = MARKERS[style]
    return f"{begin}\n{body.rstrip(chr(10))}\n{end}\n"


def find_block(text: str, style: str) -> tuple[str, str | None]:
    """("none"|"broken"|"ok", inner text) for the agk markers of a file."""
    begin, end = MARKERS[style]
    lines = text.splitlines(keepends=True)
    begins = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == begin]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == end]
    if not begins and not ends:
        return "none", None
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        return "broken", None
    return "ok", "".join(lines[begins[0] + 1 : ends[0]])


def existing_protected_files(target: Path, entries: list[str], owned: set[str]) -> list[str]:
    """Project files that fall in a protected class, excluding what adopt itself writes."""
    found: set[str] = set()
    for entry in entries:
        path = target / entry
        if path.is_symlink():
            continue
        if entry.endswith("/"):
            if not path.is_dir():
                continue
            for here, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if not (Path(here) / d).is_symlink()]
                for name in filenames:
                    rel = (Path(here) / name).relative_to(target).as_posix()
                    if rel not in owned and matches(rel, entry):
                        found.add(rel)
        elif path.is_file() and entry not in owned:
            found.add(entry)
    return sorted(found)


def build_plan(target: Path, today: str):
    """(plan entries (rel, action, content, detail), protected entries, default branch)."""
    manifest = json.loads((KIT_ROOT / MANIFEST).read_text(encoding="utf-8"))
    spec = manifest["adopt"]
    stamp = read_stamp(target)
    branch = stamp.get("default_branch") or detect_default_branch(target)
    if not branch:
        raise Refusal(
            "cannot tell the default branch (path class .git/refs/remotes/origin/HEAD); "
            "run `git remote set-head origin --auto` in TARGET, or check out the default branch "
            "of a repository without an origin remote, then run adopt again"
        )
    if "test_dirs" in stamp and "test_patterns" in stamp:
        dirs, patterns = list(stamp["test_dirs"]), list(stamp["test_patterns"])
    else:
        dirs, patterns = detect_tests(target)
    date = stamp.get("installed")
    date = date if isinstance(date, str) and DATE_RE.match(date) else today

    extra = manifest.get("experimental", []) if experimental_enabled(target) else []
    verbatim = set(manifest["verbatim"]) | set(extra)
    owned_created = (verbatim - set(spec["skip"]) - set(spec["blocks"])) | set(spec["templates"])
    owned = owned_created | set(spec["blocks"])
    protected_src = (KIT_ROOT / spec["templates"]["config/protected-paths.txt"]).read_text(
        encoding="utf-8"
    )
    entries = read_list(protected_src)
    variables = {
        "project": slug(target.name),
        "date": date,
        "kit_version": manifest["kit_version"],
        "default_branch": branch,
        "test_dirs": toml_list(dirs),
        "test_patterns": toml_list(patterns),
        "existing_protected": "\n".join(
            f"- `{p}`" for p in existing_protected_files(target, entries, owned)
        )
        or "- none",
    }
    created: dict[str, bytes] = {}
    for rel in sorted(verbatim - set(spec["skip"]) - set(spec["blocks"])):
        created[rel] = (KIT_ROOT / rel).read_bytes()
    for dest, src in spec["templates"].items():
        created[dest] = render((KIT_ROOT / src).read_text(encoding="utf-8"), variables, src).encode(
            "utf-8"
        )
    reviewers_text = created["config/reviewers.yaml"].decode("utf-8")
    codeowners = render_codeowners(parse(reviewers_text))

    plan: list[tuple[str, str, bytes, str]] = []
    for rel, content in sorted(created.items()):
        plan.append(classify_created(target, rel, content, entries))
    for rel, style in sorted(spec["blocks"].items()):
        body = codeowners if rel == ".github/CODEOWNERS" else (KIT_ROOT / rel).read_text("utf-8")
        plan.append(classify_block(target, rel, style, body, entries))
    return sorted(plan), entries, branch


def classify_created(target: Path, rel: str, content: bytes, entries: list[str]):
    path = target / rel
    cls = path_class(rel, entries)
    if passes_symlink(target, rel):
        return (rel, "conflict", content, f" (path class {cls}: symlink)")
    if not path.exists():
        return (rel, "create", content, "")
    if path.is_file() and path.read_bytes() == content:
        return (rel, "unchanged", content, "")
    if path.is_file() and rel in CREATE_ONLY:
        return (rel, "unchanged", content, "")
    return (rel, "conflict", content, f" (path class {cls}: differs)")


def classify_block(target: Path, rel: str, style: str, body: str, entries: list[str]):
    path = target / rel
    cls = path_class(rel, entries)
    whole = body.rstrip("\n") + "\n"
    block = block_of(style, body)
    if passes_symlink(target, rel):
        return (rel, "conflict", b"", f" (path class {cls}: symlink)")
    if not path.exists():
        content = block if rel in ABSENT_AS_BLOCK else whole
        return (rel, "create", content.encode("utf-8"), "")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return (rel, "conflict", b"", f" (path class {cls}: not readable as text)")
    state, inner = find_block(text, style)
    if state == "broken":
        return (rel, "conflict", b"", f" (path class {cls}: broken or duplicated agk block)")
    if state == "ok":
        if inner == whole:
            return (rel, "unchanged", b"", "")
        return (rel, "conflict", b"", f" (path class {cls}: agk block differs)")
    if text == whole and rel not in ABSENT_AS_BLOCK:
        return (rel, "unchanged", b"", "")
    sep = "" if text == "" or text.endswith("\n") else "\n"
    return (rel, "append", (text + sep + block).encode("utf-8"), "")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in args
    rest = [a for a in args if a != "--dry-run"]
    if len(rest) != 1 or rest[0].startswith("-"):
        print("usage: adopt.py TARGET [--dry-run]", file=sys.stderr)
        return 2
    try:
        problem = check_interpreter(tuple(sys.version_info[:3]))
        if problem:
            raise Refusal(problem)
        target = Path(rest[0])
        if not target.is_dir():
            raise Refusal("TARGET is not an existing directory (path class: the target root)")
        target = target.resolve()
        if target == KIT_ROOT or KIT_ROOT in target.parents:
            raise Refusal("TARGET is the kit checkout or inside it (path class kit/)")
        if not (target / ".git").is_dir():
            raise Refusal("TARGET is not a git work tree (path class .git/)")
        mode = install_mode(target)
        if mode == "init":
            raise Refusal("TARGET is already installed by init (path class agk.toml)")
        plan, entries, branch = build_plan(target, datetime.now(UTC).date().isoformat())
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: cannot read the kit sources ({type(exc).__name__})")
        return 3

    for rel, action, _, detail in plan:
        print(f"{action} {rel}{detail}")
    if any(action == "conflict" for _, action, _, _ in plan):
        print("refused: existing files differ; nothing was written")
        print_branch_rules(branch, "adopt")
        return 1
    writes = [(rel, content) for rel, action, content, _ in plan if action in ("create", "append")]
    if dry_run:
        print(f"dry run: {len(writes)} files would change; nothing was written")
    else:
        for rel, content in writes:
            path = target / rel
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            except OSError:
                print(f"error: cannot write {rel} (path class {path_class(rel, entries)})")
                return 3
        print(f"installed {len(writes)} files" if writes else "nothing to do")
    reviewers = target / "config" / "reviewers.yaml"
    text = reviewers.read_text(encoding="utf-8") if reviewers.is_file() else PLACEHOLDER
    if PLACEHOLDER in text:
        print(f"notice: config/reviewers.yaml maps `maintainers` to the placeholder {PLACEHOLDER}")
    print_branch_rules(branch, "adopt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
