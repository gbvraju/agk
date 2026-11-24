# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""agk adopt: install the kit into an existing repository, touching no product file (SPEC-0002).

Usage: python3 scripts/agk/adopt.py TARGET [--dry-run] [--unreleased]
           [--login-from-env] [--solo] [--project-tests CMD] [--layout plugin [--rehearsal]]

`--layout plugin` (SPEC-0071 rule 2 as amendment 211 proposes, brief #1603, ADR-0683) adopts the
project clean, as init does: no kit file in the adopt commit but rule 2's, the short CLAUDE.md as
its marked block, and `execution = "local"` with the `[kit]` table; the same refusals as init's.

The setup flags (SPEC-0062 rule 11, brief #1599, ADR-0679), passed by the steward: the login in
AGK_SETUP_LOGIN on both reviewer lines (never printed), `review_mode = "solo"` with its ADR line
(refused without one person), and `project_tests`.

Standard library only. No network, no git or gh calls, no writes outside TARGET. Target files are
data: they are compared byte for byte, scanned for agk's own marked blocks and for the stamp, and
listed by name; they are never imported, executed or parsed as code. Refuses (exit 1) before any
write; nothing is written when any file conflicts.

Adopt from a release (brief #263 build (c), ADR-0200): as in init (item 8, ADR-0160), the kit files
adopt would install must be those of the release row of `kit_version` in kit/hashes.json (compared
ignoring CRLF and LF), or adopt refuses before any write, so unreleased files are never stamped
with a release's version. `--unreleased` installs the checkout as it is, for the kit's own tests.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    block_source,
    detect_default_branch,
    experimental_enabled,
    lf,
    matches,
    read_list,
)
from init import (
    CREATE_ONLY,
    DATE_RE,
    KIT_ROOT,
    LAYOUT_LINE,
    LAYOUT_USAGE,
    MANIFEST,
    PLACEHOLDER,
    PLUGINS,
    REF_HINT,
    SETUP_USAGE,
    UNRELEASED,
    Refusal,
    apply_setup,
    check_interpreter,
    clean_claude,
    clean_kept,
    clean_refusal,
    clean_toml,
    install_mode,
    kit_bytes,
    layout_args,
    name_agent,
    passes_symlink,
    path_class,
    plugin_settings,
    print_branch_rules,
    release_problem,
    render,
    setup_args,
    slug,
)
from reviewers import parse, render_codeowners
from tree_walk import FRONTEND_PATTERNS, WEB_EXTENSIONS, walked_dirs  # installed, unlike this file (brief #1214)

TEST_PATTERNS = ("*_test.py", "test_*.py")
MARKERS = {
    "hash": ("# >>> agk", "# <<< agk"),
    "html": ("<!-- >>> agk -->", "<!-- <<< agk -->"),
}
ABSENT_AS_BLOCK = {".gitignore", ".gitattributes"}


def toml_list(items: list[str]) -> str:
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


# Brief #1891 (ADR-0785): with no test file found, the stacks whose manifests the tree holds name
# the patterns; the manifests come from the kit's own table, never the target's.
SIGNALS = KIT_ROOT / "config" / "stack-signals.toml"
PYTHON_STACKS = ("python-pyproject", "python-pip")
NODE_STACK = "node"
UNREACHED_FOLDERS = ("__tests__",)  # jest's folder convention; `test/` beside a package.json too
EMPTY_LINE = (
    "tests: no test file found and no stack with known test names; test_patterns is empty, "
    "so no test is selected until a person sets it (setting: test_patterns)"
)


@dataclass
class Scan:
    """One walk of a tree: the test folders and patterns found, the stacks, and the web files
    under a test folder that a name pattern may not reach (brief #1891 answers 2, 3 and 6)."""

    dirs: list[str]
    patterns: list[str]
    found: bool  # a test file matched a name pattern
    stacks: set[str] = field(default_factory=set)
    candidates: list[str] = field(default_factory=list)  # file names under a test folder


def stack_manifests() -> tuple[dict[str, str], set[str]]:
    """(manifest name -> stack, folder names to ignore) of `config/stack-signals.toml`."""
    data = tomllib.loads(SIGNALS.read_text(encoding="utf-8"))
    names = {m: s["name"] for s in data.get("stack", []) for m in s.get("manifests", [])}
    return names, set(data.get("ignore", []))


def scan_tests(root: Path) -> Scan:
    """Topmost directories holding Python or web test files, the patterns matched (by
    `fnmatchcase`, as `impact.is_test_file` matches), or the stacks' patterns when none is."""
    manifests, ignore = stack_manifests()
    dirs: set[str] = set()
    found: set[str] = set()
    stacks: set[str] = set()
    packages: set[str] = set()
    candidates: list[str] = []
    for here, dirnames, filenames in os.walk(root):
        rel_here = Path(here).relative_to(root).as_posix()
        rel_here = "" if rel_here == "." else rel_here
        dirnames[:] = sorted(walked_dirs(rel_here, dirnames))
        parts = rel_here.split("/") if rel_here else []
        if "package.json" in filenames:
            packages.add(rel_here)
        in_test_folder = any(p in UNREACHED_FOLDERS for p in parts) or any(
            p == "test" and "/".join(parts[:i]) in packages for i, p in enumerate(parts)
        )
        for name in sorted(filenames):
            if name in manifests and not any(p in ignore for p in parts):
                stacks.add(manifests[name])
            for pattern in TEST_PATTERNS + FRONTEND_PATTERNS:
                if fnmatch.fnmatchcase(name, pattern):
                    found.add(pattern)
                    dirs.add(rel_here)
            if in_test_folder and os.path.splitext(name)[1] in WEB_EXTENSIONS:
                candidates.append(name)
    top = sorted(d for d in dirs if d and not any(d.startswith(e + "/") for e in dirs if e))
    if "" in dirs:
        top = ["."]
    if top:
        return Scan(top, sorted(found), True, stacks, candidates)
    fallback: set[str] = set()
    if stacks & set(PYTHON_STACKS):
        fallback.add("test_*.py")  # today's default for a Python project (Q-AN-2)
    if NODE_STACK in stacks:
        fallback.update(FRONTEND_PATTERNS)
    return Scan(["tests"], sorted(fallback), False, stacks, candidates)


def detect_tests(root: Path) -> tuple[list[str], list[str]]:
    """Topmost directories holding Python or front-end test files, and the patterns matched."""
    scan = scan_tests(root)
    return scan.dirs, scan.patterns


def unreached(scan: Scan, patterns: list[str]) -> int:
    """The web files under a `__tests__/` or `test/` folder that no entry of PATTERNS matches."""
    return sum(1 for n in scan.candidates if not any(fnmatch.fnmatchcase(n, p) for p in patterns))


def detection_lines(scan: Scan, patterns: list[str]) -> list[str]:
    """The information lines of answers 3 and 6, for adopt and init."""
    lines = [EMPTY_LINE] if not patterns else []
    count = unreached(scan, patterns)
    if count:
        lines.append(
            f"tests: {count} files in __tests__ or test folders match no test_patterns entry "
            "(setting: test_patterns)"
        )
    return lines


def stamped_lists(stamp: dict) -> None:
    """Brief #1891 answer 5: a stamped `test_dirs` or `test_patterns` is a list of strings, or
    adopt refuses before any write; a stamp is never rewritten."""
    for key, what in (("test_dirs", "folder paths"), ("test_patterns", "file-name patterns")):
        value = stamp.get(key)
        if key in stamp and not (
            isinstance(value, list) and all(isinstance(i, str) for i in value)
        ):
            raise Refusal(f"{key} must be a list of {what} (setting: {key})")


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


def build_plan(
    target: Path,
    today: str,
    setup: dict | None = None,
    clean: bool = False,
    notes: list[str] | None = None,
):
    """(plan entries (rel, action, content, detail), protected entries, default branch). NOTES,
    when given, gains the information lines of the test detection (brief #1891)."""
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
    stamped_lists(stamp)
    scan = scan_tests(target)
    if "test_dirs" in stamp and "test_patterns" in stamp:
        dirs, patterns = list(stamp["test_dirs"]), list(stamp["test_patterns"])
    else:
        dirs, patterns = scan.dirs, scan.patterns
    if notes is not None:
        notes.extend(detection_lines(scan, patterns))
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
        if not clean or clean_kept(rel):  # the clean layout keeps only rule 2's kit files
            created[rel] = kit_bytes(KIT_ROOT / rel)
    name_agent(created)
    for dest, src in spec["templates"].items():
        created[dest] = render((KIT_ROOT / src).read_text(encoding="utf-8"), variables, src).encode(
            "utf-8"
        )
    apply_setup(created, setup)
    if clean:
        created["agk.toml"] = clean_toml(
            created["agk.toml"].decode("utf-8"), variables["kit_version"]
        ).encode("utf-8")
    reviewers_text = created["config/reviewers.yaml"].decode("utf-8")
    codeowners = render_codeowners(parse(reviewers_text))

    plan: list[tuple[str, str, bytes, str]] = []
    for rel, content in sorted(created.items()):
        plan.append(classify_created(target, rel, content, entries))
    for rel, style in sorted(spec["blocks"].items()):
        source = block_source(manifest, rel)
        body = codeowners if rel == ".github/CODEOWNERS" else (KIT_ROOT / source).read_text("utf-8")
        if clean and rel == "CLAUDE.md":
            body = clean_claude(variables)
        plan.append(classify_block(target, rel, style, body, entries))
    return sorted(plan), entries, branch


def classify_created(target: Path, rel: str, content: bytes, entries: list[str]):
    path = target / rel
    cls = path_class(rel, entries)
    if passes_symlink(target, rel):
        return (rel, "conflict", content, f" (path class {cls}: symlink)")
    if not path.exists():
        return (rel, "create", content, "")
    if path.is_file() and lf(path.read_bytes()) == lf(content):
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
    unreleased = UNRELEASED in args
    rest = [a for a in args if a not in ("--dry-run", UNRELEASED)]
    try:
        rest, setup = setup_args(rest)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    layout = layout_args(rest)
    if layout is None or len(layout[0]) != 1 or layout[0][0].startswith("-"):
        print(
            f"usage: adopt.py TARGET [--dry-run] [--unreleased] {SETUP_USAGE} {LAYOUT_USAGE}",
            file=sys.stderr,
        )
        return 2
    rest, clean, rehearsal = layout
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
        if clean:
            clean_refusal(target, rehearsal)
        not_released = release_problem(KIT_ROOT)
        if not_released and not unreleased:
            print(f"refused: {not_released}; {REF_HINT}; nothing was written")
            print(plugin_settings())
            return 1
        today = datetime.now(UTC).date().isoformat()
        notes: list[str] = []
        plan, entries, branch = build_plan(target, today, setup, clean, notes)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: cannot read the kit sources ({type(exc).__name__})")
        return 3

    if not_released:
        print(f"notice: {UNRELEASED}: {not_released.replace(PLUGINS, 'the kit files', 1)}")
    for rel, action, _, detail in plan:
        print(f"{action} {rel}{detail}")
    if clean:
        print(LAYOUT_LINE)
    for line in notes:
        print(line)
    if any(action == "conflict" for _, action, _, _ in plan):
        print("refused: existing files differ; nothing was written")
        print_branch_rules(branch, "adopt", "plugin" if clean else "installed")
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
    print_branch_rules(branch, "adopt", "plugin" if clean else "installed")
    print(history_line(clean, dry_run))
    return 0


def history_line(clean: bool, dry_run: bool) -> str:
    """Brief #1835 (ADR-0764): adopt stays git-free (SPEC-0002 rules 1 and 7, Q-HB-1); it names
    the one whole-history secret scan, which the adopt skill runs next."""
    if dry_run:
        return "history scan: not run (dry run)"
    if clean:  # a clean print names no `scripts/agk` path (brief #1665); the skill's step 5 does
        return (
            "next: scan the whole history once for secrets: history_scan.py run --write "
            "(step 5 of /agk:adopt runs it from the plugin)"
        )
    return (
        "next: scan the whole history once for secrets: "
        "python3 scripts/agk/history_scan.py run --write"
    )


if __name__ == "__main__":
    sys.exit(main())
