"""agk upgrade (SPEC-0008): bring an init or adopt target from kit version X to this kit.

Kit-only (never installed): run it from the kit checkout or the plugin root, as init.py and
adopt.py. Standard library only; no network, no `git`, no commit. The target keeps no lock file: the
installed version is `version` in `agk.toml`, and `kit/hashes.json` says what each file was at that
version, so a locally edited file is told from an outdated one. An edited file stops the whole run;
nothing is written. Files the user owns are never rewritten; only the `version = "..."` line of
`agk.toml` is set, as the last write.

    python3 scripts/agk/upgrade.py TARGET [--dry-run]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from adopt import ABSENT_AS_BLOCK, MARKERS, block_of
from common import block_source, experimental_enabled, installed_version, lf, matches, read_list
from init import (
    CREATE_ONLY,
    DATE_RE,
    MANIFEST,
    Refusal,
    check_interpreter,
    passes_symlink,
    path_class,
    render,
    slug,
)
from init import KIT_ROOT as KIT_ROOT  # noqa: PLC0414 - tests point it at an older kit fixture

USAGE = "usage: upgrade.py TARGET [--dry-run]"
TABLE = "kit/hashes.json"
KIT_ONLY = ("kit/", "tests/kit_dev/")
KIT_ONLY_FILES = ("scripts/agk/init.py", "scripts/agk/adopt.py")
LINE_TEMPLATES = ("config/protected-paths.txt", "config/neutrality.txt")
GENERATOR = "scripts/agk/reviewers.py"
CODEOWNERS_COMMAND = "python3 scripts/agk/reviewers.py --codeowners --write"
# Brief 236: the root pyproject.toml installs as nothing, so a host that runs `pip install .` at the
# root succeeds. The same two tables are in kit/templates/pyproject.toml (a test compares them).
INSTALLS_AS_NOTHING = (
    '[build-system]\nrequires = ["setuptools>=61"]\nbuild-backend = "setuptools.build_meta"\n'
    "\n[tool.setuptools]\npackages = []\n"
)
PYPROJECT_DETAIL = (
    " (adds [build-system] and [tool.setuptools] packages = []; no other line changes)"
)
LEGACY_NOTE = (
    "legacy-stamp pyproject.toml [tool.agk]: obsolete after this upgrade; "
    "remove it in your own change"
)
FIX = (
    "fix: restore the kit's copy of each edited file by hand, or move the edit out of the vendored "
    "file, then run again"
)


@dataclass
class Item:
    rel: str
    action: str
    detail: str = ""
    content: bytes | None = None
    delete: bool = False  # an unmodified kit file the new kit no longer ships (ADR-0031)


@dataclass
class Plan:
    version: str
    kit_version: str
    mode: str
    items: list[Item] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)
    legacy: bool = False  # the stamp is [tool.agk] in pyproject.toml; agk.toml is created, last

    @property
    def writes(self) -> list[Item]:
        return [i for i in self.items if i.action in ("create", "replace")]

    @property
    def deletions(self) -> list[Item]:
        return [i for i in self.items if i.delete]

    @property
    def stamp(self) -> bool:
        """True when the version line of an existing agk.toml is to be set."""
        return not self.legacy and self.version != self.kit_version

    @property
    def conflicts(self) -> list[Item]:
        return [i for i in self.items if i.action == "conflict"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def version_key(text: str) -> tuple[int, ...]:
    parts = text.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(text)
    return tuple(int(p) for p in parts)


def legacy_stamp(target: Path) -> dict | None:
    """The `[tool.agk]` table of pyproject.toml when it carries a version (kits 0.1.0 and 0.2.0)."""
    path = target / "pyproject.toml"
    if not path.is_file():
        return None
    try:
        table = tomllib.loads(path.read_text(encoding="utf-8")).get("tool", {}).get("agk")
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    return table if isinstance(table, dict) and isinstance(table.get("version"), str) else None


def read_stamp(target: Path) -> tuple[str, str, dict | None]:
    """(version, mode, legacy stamp). Without agk.toml a `[tool.agk]` version means mode init."""
    path = target / "agk.toml"
    version = installed_version(target)
    if not path.is_file():
        stamp = legacy_stamp(target)
        if version is None or stamp is None:
            raise Refusal(
                "agk.toml is missing and pyproject.toml has no [tool.agk] version "
                "(path class agk.toml)"
            )
        return version, "init", stamp
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise Refusal("agk.toml is not readable TOML (path class agk.toml)") from None
    mode = data.get("mode")
    if version is None:
        raise Refusal("agk.toml has no version (path class agk.toml)")
    if mode not in ("init", "adopt"):
        raise Refusal("mode in agk.toml is not init or adopt (path class agk.toml)")
    return version, mode, None


def legacy_agk_toml(target: Path, kit_root: Path, manifest: dict, stamp: dict) -> bytes:
    """agk.toml from the kit's template: the stamp's installed and default_branch, kit version."""
    installed = stamp.get("installed")
    if not (isinstance(installed, str) and DATE_RE.match(installed)):
        installed = datetime.now(UTC).date().isoformat()
    branch = stamp.get("default_branch")
    variables = {
        "project": slug(target.name),
        "date": installed,
        "kit_version": str(manifest["kit_version"]),
        "default_branch": branch if isinstance(branch, str) and branch else "main",
    }
    src = manifest["templates"]["agk.toml"]
    return render((kit_root / src).read_text(encoding="utf-8"), variables, src).encode("utf-8")


def locate(text: str, style: str) -> tuple[str, int, int, list[str]]:
    """("none"|"broken"|"ok", begin line, end line, lines) for the agk markers of a file."""
    begin, end = MARKERS[style]
    lines = text.splitlines(keepends=True)
    begins = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == begin]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == end]
    if not begins and not ends:
        return "none", -1, -1, lines
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        return "broken", -1, -1, lines
    return "ok", begins[0], ends[0], lines


def installed_set(
    manifest: dict, mode: str, experimental: bool = False
) -> tuple[list[str], dict[str, str]]:
    """(whole-file paths the installer for `mode` writes, marked blocks of an adopt install)."""
    listed = [*manifest["verbatim"], *(manifest.get("experimental", []) if experimental else [])]
    verbatim = [p for p in listed if not p.startswith(KIT_ONLY) and p not in KIT_ONLY_FILES]
    if mode == "init":
        return sorted(verbatim), {}
    spec = manifest["adopt"]
    rendered = set(manifest.get("rendered") or [])
    blocks = {p: s for p, s in spec["blocks"].items() if p not in rendered}
    whole = set(verbatim) - set(spec["skip"]) - set(spec["blocks"])
    return sorted(whole), dict(sorted(blocks.items()))


def whole_file(target: Path, rel: str, new: bytes, old: set[str], entries: list[str]) -> Item:
    path = target / rel
    cls = path_class(rel, entries)
    if not path.exists() and not path.is_symlink():
        return Item(rel, "deleted-locally") if old else Item(rel, "create", content=new)
    if not path.is_file():
        return Item(rel, "conflict", f" (path class {cls}: not a file)")
    data = lf(path.read_bytes())  # a Windows checkout is CRLF; the release rows are LF
    if data == new:
        return Item(rel, "unchanged")
    if digest(data) in old:
        return Item(rel, "replace", content=new)
    return Item(rel, "conflict", f" (path class {cls}: differs from every released copy)")


def block_file(
    target: Path, rel: str, style: str, body: str, old: set[str], entries: list[str]
) -> Item:
    path = target / rel
    cls = path_class(rel, entries)
    whole = body.rstrip("\n") + "\n"
    if not path.exists() and not path.is_symlink():
        if old:
            return Item(rel, "deleted-locally")
        content = block_of(style, body) if rel in ABSENT_AS_BLOCK else whole
        return Item(rel, "create", content=content.encode("utf-8"))
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Item(rel, "conflict", f" (path class {cls}: not readable as text)")
    state, begin, end, lines = locate(text, style)
    if state == "broken":
        return Item(rel, "conflict", f" (path class {cls}: broken or duplicated agk block)")
    if state == "none":
        # adopt writes a whole file, without markers, when the file did not exist
        if rel in ABSENT_AS_BLOCK:
            if not old:  # a block no release has shipped yet: add it, as adopt does
                sep = "" if text == "" or text.endswith("\n") else "\n"
                return Item(
                    rel,
                    "replace",
                    " (agk block added)",
                    content=(text + sep + block_of(style, body)).encode("utf-8"),
                )
            return Item(rel, "conflict", f" (path class {cls}: marked block, no agk markers)")
        if text == whole:
            return Item(rel, "unchanged")
        if digest(text.rstrip("\n").encode() + b"\n") in old:
            return Item(rel, "replace", content=whole.encode("utf-8"))
        return Item(rel, "conflict", f" (path class {cls}: marked block, no agk markers)")
    inner = "".join(lines[begin + 1 : end])
    if inner == whole:
        return Item(rel, "unchanged")
    if digest(inner.encode("utf-8")) in old:
        fresh = "".join([*lines[: begin + 1], whole, *lines[end:]])
        return Item(rel, "replace", content=fresh.encode("utf-8"))
    return Item(rel, "conflict", f" (path class {cls}: marked block, agk block differs)")


def history(table: dict) -> dict[str, set[str]]:
    """Path -> every hash the table lists for it in any release (every copy the kit shipped)."""
    seen: dict[str, set[str]] = {}
    for row in table.get("releases", {}).values():
        for rel, hashes in row.get("verbatim", {}).items():
            seen.setdefault(rel, set()).update(hashes)
    return seen


def removed_item(
    target: Path, rel: str, seen: dict[str, set[str]], optional: set[str], kept: set[str]
) -> Item:
    """A path the row of the installed version lists and the present manifest does not.

    Deleted only when it is a regular file whose bytes equal a copy the kit once shipped at that
    path; a modified file, a file the project owns, a symlink and an optional file are kept.
    """
    path = target / rel
    if rel in optional:
        return Item(rel, "removed-in-kit", " (optional file, kept)")
    if rel in kept:
        return Item(rel, "removed-in-kit", " (kept: left to the project in adopt mode)")
    if path.is_symlink() or not path.is_file() or passes_symlink(target, rel):
        return Item(rel, "removed-in-kit", " (not a regular file, kept)")
    try:
        data = lf(path.read_bytes())
    except OSError:
        return Item(rel, "removed-in-kit", " (not readable, kept)")
    if digest(data) in seen.get(rel, set()):
        return Item(rel, "removed-in-kit", " (unmodified, deleted)", delete=True)
    return Item(rel, "removed-in-kit", " (modified, kept)")


def template_notes(target: Path, kit_root: Path, templates: dict[str, str], row: dict) -> list[str]:
    notes = []
    for dest, src in sorted(templates.items()):
        source = lf((kit_root / src).read_bytes())
        if digest(source) in row["templates"].get(src, []):
            continue
        notes.append(f"template-changed {dest} ({src})")
        text = source.decode("utf-8")
        have = target / dest
        if dest in LINE_TEMPLATES:
            mine = read_list(have.read_text(encoding="utf-8")) if have.is_file() else []
            for line in read_list(text):
                if "{{" not in line and line not in mine:
                    notes.append(f"template-line {dest} {line}")
        if dest == "agk.toml" and have.is_file():
            keys = set(tomllib.loads(have.read_text(encoding="utf-8")))
            for line in text.split("\n[", 1)[0].splitlines():
                match = re.match(r"^([A-Za-z_][\w-]*)\s*=\s*(.*)$", line)
                if match and match.group(1) not in keys:
                    notes.append(f"template-key {dest} {match.group(1)} = {match.group(2)}")
    return notes


def absent_templates(
    target: Path, kit_root: Path, manifest: dict, templates: dict[str, str]
) -> list[Item]:
    """Every create-only template that is absent from the target (rule of init and adopt).

    Created only when absent, never compared and never overwritten: a file that exists, with any
    content, is left alone and not listed. A symlink or a non-file at the path stops the run.
    """
    items: list[Item] = []
    variables: dict[str, str] | None = None
    for rel in CREATE_ONLY:
        src = templates.get(rel)
        path = target / rel
        if src is None:
            continue
        if path.is_symlink():
            items.append(Item(rel, "conflict", " (not a regular file: symlink)"))
        elif path.exists():
            if not path.is_file():
                items.append(Item(rel, "conflict", " (not a regular file)"))
        else:
            if variables is None:
                variables = template_variables(target, manifest)
            text = render((kit_root / src).read_text(encoding="utf-8"), variables, src)
            items.append(Item(rel, "create", " (absent)", content=text.encode("utf-8")))
    return items


def template_project(table: object) -> bool:
    """True when the `[project]` table is still the one the template rendered: the keys `name`,
    `version`, `requires-python` and `dependencies` and no others, `version = "0.0.0"` and
    `dependencies = []`. Any other table may build a real package, which `packages = []` would
    empty without an error."""
    return (
        isinstance(table, dict)
        and set(table) == {"name", "version", "requires-python", "dependencies"}
        and table["version"] == "0.0.0"
        and table["dependencies"] == []
    )


def pyproject_fix(target: Path, mode: str) -> tuple[Item | None, str | None]:
    """The root pyproject.toml of an init install, made installable as nothing (brief 236).

    After init the file belongs to the project, so it is never rewritten: the two tables are
    appended when the file has a `[project]` table that is still the template's (`template_project`)
    and neither a `[build-system]` table nor a `[tool.setuptools]` table, and every existing byte
    stays; a `[project]` table of the project's own is left alone with a note (it may build a real
    package). A file with one of the tables is left
    alone and a note says so when it has only one of them; a file that is not valid TOML, a symlink,
    the pyproject.toml of an adopted project (the project's own) and the one that still holds the
    legacy `[tool.agk]` stamp (never written, Q-K3-71; the project removes it in its own change)
    are left alone."""
    path = target / "pyproject.toml"
    if mode != "init" or path.is_symlink() or not path.is_file():
        return None, None
    try:
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None, None
    if "project" not in data or "agk" in (data.get("tool") or {}):
        return None, None  # no [project]; or the legacy [tool.agk] stamp is still there (Q-K3-71)
    has_build = "build-system" in data
    has_setuptools = "setuptools" in (data.get("tool") or {})
    if has_build and has_setuptools:
        return None, None
    if has_build or has_setuptools:
        have = "[build-system]" if has_build else "[tool.setuptools]"
        return None, f"pyproject-unchanged pyproject.toml has {have} already; left as it is"
    if not template_project(data["project"]):
        return None, (
            "pyproject-unchanged pyproject.toml the [project] table is the project's own; add "
            "[build-system] and [tool.setuptools] packages = [] only if it builds no package"
        )
    newline = "\r\n" if b"\r\n" in raw else "\n"
    tables = INSTALLS_AS_NOTHING.replace("\n", newline)
    gap = b"" if not raw or raw.endswith(newline.encode()) else newline.encode()
    separator = newline.encode() if raw else b""
    content = raw + gap + separator + tables.encode("utf-8")
    return Item("pyproject.toml", "replace", PYPROJECT_DETAIL, content=content), None


def template_variables(target: Path, manifest: dict) -> dict[str, str]:
    """The variables of the templates: the stamp's date and default branch, else today and main."""
    data: dict = {}
    try:
        data = tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        pass
    installed, branch = data.get("installed"), data.get("default_branch")
    return {
        "project": slug(target.name),
        "date": installed
        if isinstance(installed, str) and DATE_RE.match(installed)
        else datetime.now(UTC).date().isoformat(),
        "kit_version": str(manifest["kit_version"]),
        "default_branch": branch if isinstance(branch, str) and branch else "main",
    }


def build_plan(target: Path, kit_root: Path) -> Plan:
    version, mode, legacy = read_stamp(target)
    manifest = json.loads((kit_root / MANIFEST).read_text(encoding="utf-8"))
    try:
        table = json.loads((kit_root / TABLE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Refusal(f"{TABLE} is missing or not JSON (path class {TABLE})") from None
    kit_version = str(manifest["kit_version"])
    if version_key(version) > version_key(kit_version):
        raise Refusal("version in agk.toml is newer than this kit (path class agk.toml)")
    row = table.get("releases", {}).get(version)
    if row is None:
        raise Refusal(f"version in agk.toml is not in the table (path class {TABLE})")
    listed = target / "config" / "protected-paths.txt"
    entries = read_list(listed.read_text(encoding="utf-8")) if listed.is_file() else []
    plan = Plan(version, kit_version, mode, entries=entries, legacy=legacy is not None)

    enabled = experimental_enabled(target)
    optional = set(manifest.get("experimental", []))
    whole, blocks = installed_set(manifest, mode, enabled)
    for rel in whole:
        new = lf((kit_root / rel).read_bytes())  # a CRLF plugin cache is written as LF
        old = set(row["verbatim"].get(rel, []))
        if rel in optional and not (target / rel).exists():
            old = set()  # opting in creates the file; it was never installed, so it is not deleted
        plan.items.append(whole_file(target, rel, new, old, entries))
    for rel, style in blocks.items():
        body = (kit_root / block_source(manifest, rel)).read_text(encoding="utf-8")
        old = set(row["blocks"].get(rel, []))
        plan.items.append(block_file(target, rel, style, body, old, entries))
    current = set(manifest["verbatim"]) | (optional if enabled else set())
    seen = history(table)
    kept = (
        set(manifest["adopt"]["skip"]) | set(manifest["adopt"]["blocks"])
        if mode == "adopt"
        else set()
    )
    for rel in sorted(set(row["verbatim"]) - current):
        if (target / rel).exists() or (target / rel).is_symlink():
            plan.items.append(removed_item(target, rel, seen, optional, kept))
    plan.items.sort(key=lambda i: i.rel)

    templates = manifest["templates"] if mode == "init" else manifest["adopt"]["templates"]
    plan.items += absent_templates(target, kit_root, manifest, templates)
    fix, fix_note = pyproject_fix(target, mode) if legacy is None else (None, None)
    if fix is not None:
        plan.items.append(fix)
    plan.items.sort(key=lambda i: i.rel)
    plan.notes = [
        n
        for n in template_notes(target, kit_root, templates, row)
        if not any(n.startswith(f"template-changed {rel} ") for rel in CREATE_ONLY)
    ]
    if fix_note is not None:
        plan.notes.append(fix_note)
    if legacy is not None:
        plan.notes = [n for n in plan.notes if not n.startswith("template-changed agk.toml ")]
        plan.notes.insert(0, LEGACY_NOTE)
        content = legacy_agk_toml(target, kit_root, manifest, legacy)
        plan.items.append(Item("agk.toml", "create", content=content))
        plan.items.sort(key=lambda i: i.rel)
    for item in plan.writes:
        if passes_symlink(target, item.rel):
            raise Refusal(f"{item.rel} passes through a symlink (path class symlink)")
    return plan


def protected_classes(plan: Plan) -> list[str]:
    paths = [i.rel for i in plan.writes + plan.deletions] + (["agk.toml"] if plan.stamp else [])
    found: list[str] = []
    for rel in paths:
        for entry in plan.entries:
            if matches(rel, entry):
                if entry not in found:
                    found.append(entry)
                break
    return found


def report(plan: Plan, dry_run: bool) -> list[str]:
    lines = [f"{i.action} {i.rel}{i.detail}" for i in plan.items]
    lines += plan.notes
    if plan.conflicts:
        lines.append(
            "refused: edited vendored files differ from every released copy; nothing was written"
        )
        lines.append(FIX)
        return lines
    count = len(plan.writes)
    gone = len(plan.deletions)
    stamp = plan.stamp
    where = f"the version line of agk.toml is set to {plan.kit_version}"
    if plan.legacy:
        where = f"agk.toml is created with version {plan.kit_version}"
    elif not stamp:
        where = "the version line is unchanged"
    if dry_run:
        tail = f"; {where.replace('is ', 'would be ', 1)}" if stamp else ""
        if plan.legacy:
            tail = f"; {where.replace('is ', 'would be ', 1)}"
        more = f", {gone} would be deleted" if gone else ""
        lines.append(f"dry run: {count} files would change{more}{tail}; nothing was written")
    elif count == 0 and not stamp and not gone:
        lines.append("nothing to do")
    else:
        more = f" and deleted {gone}" if gone else ""
        lines.append(f"upgraded {count} files{more}; {where}")
    classes = protected_classes(plan)
    if classes:
        lines += [
            f"Protected classes: {', '.join(f'`{c}`' for c in classes)}",
            "The target's check needs an ADR in the same pull request that names each class. "
            "Skeleton (write the ADR yourself; the upgrade writes none):",
            f"# ADR-NNNN: Upgrade agk from {plan.version} to {plan.kit_version}",
            "- Status: Proposed",
            "- Date: YYYY-MM-DD",
            "- Deciders: maintainers",
            "- Related: none",
            "- Requirements: REQ-nnn",
            f"Protected classes: {', '.join(f'`{c}`' for c in classes)}",
            "## Context",
            "## Decision",
        ]
    touched = {i.rel for i in plan.writes}
    changes = bool(count or stamp or gone)  # never after `nothing to do` (brief #254, Q-254-3)
    if GENERATOR in touched or (
        changes and any(n.startswith("template-changed config/reviewers.yaml") for n in plan.notes)
    ):
        lines.append(f"run: {CODEOWNERS_COMMAND}")
    return lines


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.agk-upgrade")
    try:
        temp.write_bytes(data)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def remove_file(target: Path, rel: str) -> None:
    """Delete one file, then the directories that deletion emptied.

    Never the target itself and never a directory directly under it: a project whose only
    `tests/` content was the kit's own tests keeps its `tests/` for its own tests to come.
    """
    path = target / rel
    path.unlink()
    parent = path.parent
    while parent.parent != target and target in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def apply(target: Path, plan: Plan) -> tuple[bool, list[str]]:
    """Write in sorted path order, delete unmodified removed files, then agk.toml last.

    (ok, files already written or deleted)."""
    done: list[str] = []
    last = [i for i in plan.writes if plan.legacy and i.rel == "agk.toml"]
    for item in [i for i in plan.writes if i not in last]:
        try:
            write_atomic(target / item.rel, item.content or b"")
        except OSError:
            print(
                f"error: cannot write {item.rel} (path class {path_class(item.rel, plan.entries)})"
            )
            return False, done
        done.append(item.rel)
    for item in plan.deletions:
        try:
            remove_file(target, item.rel)
        except OSError:
            print(
                f"error: cannot delete {item.rel} (path class {path_class(item.rel, plan.entries)})"
            )
            return False, done
        done.append(item.rel)
    path = target / "agk.toml"
    try:
        if last:
            write_atomic(path, last[0].content or b"")
        elif plan.stamp:
            pattern = rb'(?m)^(version\s*=\s*)"[^"]*"'
            replacement = rb'\1"' + plan.kit_version.encode() + b'"'
            write_atomic(path, re.sub(pattern, replacement, path.read_bytes(), count=1))
    except OSError:
        print("error: cannot write agk.toml (path class agk.toml)")
        return False, done
    return True, done


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in args
    rest = [a for a in args if a != "--dry-run"]
    if len(rest) != 1 or rest[0].startswith("-"):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        problem = check_interpreter(tuple(sys.version_info[:3]))
        if problem:
            raise Refusal(problem)
        target = Path(rest[0])
        if not target.is_dir():
            raise Refusal("TARGET is not an existing directory (path class: the target root)")
        target = target.resolve()
        kit_root = Path(KIT_ROOT)
        if target == kit_root or kit_root in target.parents:
            raise Refusal("TARGET is the kit checkout or inside it (path class kit/)")
        if not (target / ".git").exists():
            raise Refusal("TARGET is not a git work tree (path class .git/)")
        plan = build_plan(target, kit_root)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except (OSError, ValueError, KeyError):
        print("error: cannot read the target or the kit sources (path class: the target root)")
        return 3

    for line in report(plan, dry_run):
        print(line)
    if plan.conflicts:
        return 1
    if dry_run or (not plan.writes and not plan.deletions and not plan.stamp):
        return 0
    ok, done = apply(target, plan)
    if not ok:
        print(f"already written: {', '.join(done) if done else 'none'}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
