"""agk uninstall (brief #348 build (b), ADR-0203): pause the kit, or remove it in one branch.

Kit-only (never installed): run it from the kit checkout or the plugin root, as upgrade.py, since
the removal deletes the target's own copy of the kit's scripts. Standard library only; no network,
no `gh`. A dry run is the default and writes nothing; `--write` makes one new branch in the target
(`git switch -c`), writes the change there and commits nothing, so the person reviews it, commits
it and opens one pull request, which git can revert.

    python3 scripts/agk/uninstall.py TARGET [--write] [--remove-docs]
    python3 scripts/agk/uninstall.py TARGET --pause [--write]

Removal (answer 2): every kit file whose bytes (CRLF read as LF) equal a copy that some release
row of `kit/hashes.json` lists for its path is deleted, whatever version the target was installed
at; a kit file the project changed is listed, never deleted. A marked agk block is taken out of a
file that holds the project's own lines too, and only when the block is one a release shipped; the
line `include agk.mk` leaves the project's Makefile when `agk.mk` goes. `agk.toml` goes when it
holds only the kit's settings. The project's own work (answer 3: requirements, ADRs, specs, briefs,
the vision, the design documents, the records under docs/runs/, the tests) is never deleted or
edited; `--remove-docs` lists it for the person to delete by hand. The GitHub side (answer 4) is
printed, never done. `--pause` (answer 1) adds the top-level line `paused = true` to agk.toml.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from adopt import MARKERS
from common import DEFAULT_CONFIG, CheckError, lf, matches, paused, read_list
from init import KIT_ROOT as KIT_ROOT  # noqa: PLC0414 - tests point it at a fixture kit
from init import MANIFEST, TABLE, Refusal, check_interpreter, passes_symlink, path_class
from reviewers import ReviewerError, parse, render_codeowners

USAGE = (
    "usage: uninstall.py TARGET [--write] [--remove-docs] | uninstall.py TARGET --pause [--write]"
)
BRANCH = "agk-uninstall"
PAUSE_BRANCH = "agk-pause"
PAUSE_LINE = "paused = true"
CODEOWNERS = ".github/CODEOWNERS"
RULESET = "kit/templates/ruleset.json"
INCLUDE = re.compile(r"^-?include\s+agk\.mk\s*$")
# The kit's labels: the router's seven states, then the labels of the issues the kit reads or opens.
LABELS = (
    "agk:ci-running",
    "agk:ci-red",
    "agk:conflict",
    "agk:review",
    "agk:fix",
    "agk:approve",
    "agk:ready",
    "agk-brief",
    "agk-conductor",
    "agk-shadow",
    "agk-drift-audit",
    "agk-metrics",
    "agk-product-report",
)
RED_TITLE = "The default branch is red"  # session.RED_TITLE; a test keeps the two equal
PLUGIN_COMMANDS = ("claude plugin uninstall agk@agk", "claude plugin marketplace remove agk")
# The project's own work (answer 3), never deleted or edited; a kit TEMPLATE.md is not in it.
OWN_FILES = ("docs/requirements.md", "docs/build-state.md", "constitution/vision.md")
OWN_DIRS = ("docs/adr/", "docs/specs/", "docs/briefs/", "docs/runs/", "docs/design/", "tests/")
# Settings the kit reads that its templates do not list as `key =` lines.
MORE_SETTINGS = {"version", "installed", "mode", "paused", "experimental_reviewer"}
SETTING_LINE = re.compile(r"^#?\s*\[?([A-Za-z_][\w-]*)\]?\s*(=|$)")


@dataclass
class Item:
    rel: str
    action: str  # delete, edit, changed, kept
    detail: str = ""
    content: bytes | None = None


@dataclass
class Plan:
    items: list[Item] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)
    own: list[str] = field(default_factory=list)

    def of(self, action: str) -> list[Item]:
        return [i for i in self.items if i.action == action]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(data: bytes) -> bytes:
    return data.rstrip(b"\n") + b"\n"


def own_work(rel: str) -> bool:
    """The project's own work (answer 3); a kit `TEMPLATE.md` under docs/ is the kit's."""
    if rel.endswith("/TEMPLATE.md") and rel.startswith(
        ("docs/adr/", "docs/specs/", "docs/briefs/")
    ):
        return False
    return rel in OWN_FILES or rel.startswith(OWN_DIRS)


def load_table(kit_root: Path) -> dict:
    try:
        table = json.loads((kit_root / TABLE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Refusal(f"{TABLE} is missing or not JSON (path class {TABLE})") from None
    if not isinstance(table, dict) or not isinstance(table.get("releases"), dict):
        raise Refusal(f"{TABLE} has no release rows (path class {TABLE})")
    return table


def released(table: dict, name: str) -> dict[str, set[str]]:
    """Path -> every digest that any release row lists for it in the map NAME (answer 6: a target
    installed at an older release is read by that release's row as by the newest)."""
    seen: dict[str, set[str]] = {}
    for row in table["releases"].values():
        for rel, hashes in (row.get(name) or {}).items():
            seen.setdefault(rel, set()).update(hashes)
    return seen


def block_styles(manifest: dict) -> dict[str, str]:
    styles = {".gitignore": "hash", ".gitattributes": "hash"}
    styles.update((manifest.get("adopt") or {}).get("blocks") or {})
    styles.update(manifest.get("extendable") or {})
    return styles


def template_sources(manifest: dict) -> dict[str, set[str]]:
    """Destination -> the kit templates that init or adopt render to it."""
    out: dict[str, set[str]] = {}
    for spec in (manifest.get("templates") or {}, (manifest.get("adopt") or {}).get("templates")):
        for dest, src in (spec or {}).items():
            out.setdefault(dest, set()).add(src)
    return out


def kit_settings(kit_root: Path, manifest: dict) -> set[str]:
    """Every top-level key and table name the kit reads in agk.toml: its defaults, the lines of its
    templates (set or commented out), and the few it reads that no template line sets."""
    names = set(DEFAULT_CONFIG) | MORE_SETTINGS
    for src in template_sources(manifest).get("agk.toml", set()):
        try:
            text = (kit_root / src).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            match = SETTING_LINE.match(line)
            if match and (match.group(2) == "=" or line.lstrip("# ").startswith("[")):
                names.add(match.group(1))
    return names


def locate(text: str, style: str) -> tuple[str, int, int, list[str]]:
    begin, end = MARKERS[style]
    lines = text.splitlines(keepends=True)
    begins = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == begin]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == end]
    if not begins and not ends:
        return "none", -1, -1, lines
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        return "broken", -1, -1, lines
    return "ok", begins[0], ends[0], lines


def codeowners_of_text(text: str) -> str:
    """The CODEOWNERS that `reviewers.py --codeowners` writes from the text of reviewers.yaml."""
    return render_codeowners(parse(text))


def codeowners_of(target: Path) -> str | None:
    """The CODEOWNERS the kit generates from the target's config/reviewers.yaml, if it reads."""
    path = target / "config" / "reviewers.yaml"
    try:
        return codeowners_of_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ReviewerError, KeyError, TypeError, AttributeError):
        return None


class Reader:
    """What the kit once shipped, read from the table and the manifest of the kit run."""

    def __init__(self, target: Path, kit_root: Path) -> None:
        self.manifest = json.loads((kit_root / MANIFEST).read_text(encoding="utf-8"))
        table = load_table(kit_root)
        self.verbatim = released(table, "verbatim")
        self.blocks = released(table, "blocks")
        self.templates = released(table, "templates")
        self.sources = template_sources(self.manifest)
        self.styles = block_styles(self.manifest)
        self.settings = kit_settings(kit_root, self.manifest)
        self.codeowners = codeowners_of(target)

    def paths(self) -> list[str]:
        found = set(self.verbatim) | set(self.blocks) | set(self.sources)
        found |= set(self.manifest.get("rendered") or []) | {"agk.toml"}
        return sorted(found)

    def is_kit_copy(self, rel: str, data: bytes) -> bool:
        mark = digest(data)
        if mark in self.verbatim.get(rel, set()):
            return True
        if any(mark in self.templates.get(src, set()) for src in self.sources.get(rel, set())):
            return True
        if digest(normalized(data)) in self.blocks.get(rel, set()):
            return True  # a file that adopt wrote whole, as its block's text
        return (
            rel == CODEOWNERS
            and self.codeowners is not None
            and data == lf(self.codeowners.encode("utf-8"))
        )

    def is_kit_block(self, rel: str, inner: str) -> bool:
        data = inner.encode("utf-8")
        if digest(normalized(data)) in self.blocks.get(rel, set()):
            return True
        if digest(data) in self.verbatim.get(rel, set()):
            return True
        return (
            rel == CODEOWNERS
            and self.codeowners is not None
            and (normalized(data) == normalized(self.codeowners.encode("utf-8")))
        )


def changed(rel: str, entries: list[str], why: str) -> Item:
    cls = path_class(rel, entries)
    return Item(rel, "changed", f" (path class {cls}: {why}; kept for you to decide)")


def agk_toml_item(target: Path, reader: Reader, entries: list[str]) -> Item:
    try:
        data = tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return changed("agk.toml", entries, "not readable TOML")
    unknown = sorted(k for k in data if k not in reader.settings)
    if unknown:
        return changed("agk.toml", entries, f"settings the kit does not read: {', '.join(unknown)}")
    return Item("agk.toml", "delete", " (the kit's settings only)")


def block_item(rel: str, text: str, style: str, reader: Reader, entries: list[str]) -> Item:
    state, begin, end, lines = locate(text, style)
    if state == "broken":
        return changed(rel, entries, "broken or duplicated agk block")
    if state == "none":
        return changed(rel, entries, "differs from every released copy")
    if not reader.is_kit_block(rel, "".join(lines[begin + 1 : end])):
        return changed(rel, entries, "the agk block differs from every released copy")
    rest = [*lines[:begin], *lines[end + 1 :]]
    if not "".join(rest).strip():
        return Item(rel, "delete", " (the kit's block only)")
    kept = sum(1 for ln in rest if ln.strip())
    content = "".join(rest).encode("utf-8")
    return Item(rel, "edit", f" (agk block removed; project lines kept: {kept})", content=content)


def classify(target: Path, rel: str, reader: Reader, entries: list[str]) -> Item | None:
    path = target / rel
    if not path.exists() and not path.is_symlink():
        return None
    if passes_symlink(target, rel) or not path.is_file():
        return changed(rel, entries, "not a regular file")
    if rel == "agk.toml":
        return agk_toml_item(target, reader, entries)
    data = lf(path.read_bytes())
    if reader.is_kit_copy(rel, data):
        return Item(rel, "delete", " (unchanged kit file)")
    style = reader.styles.get(rel)
    if style in MARKERS:
        try:
            return block_item(rel, data.decode("utf-8"), style, reader, entries)
        except UnicodeDecodeError:
            return changed(rel, entries, "not readable as text")
    return changed(rel, entries, "differs from every released copy")


def makefile_item(target: Path, plan: Plan) -> None:
    """When agk.mk goes and the project keeps its Makefile, the kit's line `include agk.mk` goes."""
    if not any(i.rel == "agk.mk" and i.action == "delete" for i in plan.items):
        return
    path = target / "Makefile"
    if passes_symlink(target, "Makefile") or not path.is_file():
        return
    current = next((i for i in plan.items if i.rel == "Makefile"), None)
    if current is not None and current.action == "delete":
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeDecodeError):
        return
    rest = [ln for ln in lines if not INCLUDE.match(ln.rstrip("\r\n"))]
    if len(rest) == len(lines):
        return
    detail = " (the kit's line `include agk.mk` removed"
    if current is not None:
        detail += "; the rest differs from every released copy, kept for you to decide"
        plan.items.remove(current)
    detail += "; targets that call agk-* are yours to change)"
    plan.items.append(Item("Makefile", "edit", detail, content="".join(rest).encode("utf-8")))


def own_files(target: Path) -> list[str]:
    found: list[str] = []
    for rel in OWN_FILES:
        if (target / rel).is_file():
            found.append(rel)
    for top in OWN_DIRS:
        if top == "tests/":
            continue  # the tests are kept and are not documents to list
        base = target / top
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                rel = path.relative_to(target).as_posix()
                if path.is_file() and own_work(rel):
                    found.append(rel)
    return sorted(found)


def build_plan(target: Path, kit_root: Path) -> Plan:
    if not (target / "agk.toml").is_file():
        raise Refusal("agk.toml is missing (path class agk.toml): no kit installed")
    listed = target / "config" / "protected-paths.txt"
    entries = read_list(listed.read_text(encoding="utf-8")) if listed.is_file() else []
    reader = Reader(target, kit_root)
    plan = Plan(entries=entries)
    for rel in reader.paths():
        if own_work(rel):
            continue
        if rel == "pyproject.toml" and (target / rel).is_file():
            plan.items.append(
                Item(
                    rel,
                    "kept",
                    " (rendered from the kit's template; it may hold the project's "
                    "own settings: edit it by hand)",
                )  # fmt: skip
            )
            continue
        item = classify(target, rel, reader, entries)
        if item is not None:
            plan.items.append(item)
    makefile_item(target, plan)
    plan.items.sort(key=lambda i: i.rel)
    plan.own = own_files(target)
    return plan


def protected_classes(paths: list[str], entries: list[str]) -> list[str]:
    found: list[str] = []
    for rel in paths:
        for entry in entries:
            if matches(rel, entry):
                if entry not in found:
                    found.append(entry)
                break
    return found


def adr_skeleton(title: str, classes: list[str]) -> list[str]:
    if not classes:
        return []
    names = ", ".join(f"`{c}`" for c in classes)
    return [
        f"Protected classes: {names}",
        "The project's check needs an ADR in the same pull request that names each class. "
        "Skeleton (write the ADR yourself; the tool writes none):",
        f"# ADR-NNNN: {title}",
        "- Status: Proposed",
        "- Date: YYYY-MM-DD",
        "- Deciders: maintainers",
        "- Related: none",
        "- Requirements: REQ-nnn",
        f"Protected classes: {names}",
        "## Context",
        "## Decision",
    ]


def ruleset_name(kit_root: Path) -> str:
    try:
        data = json.loads((kit_root / RULESET).read_text(encoding="utf-8"))
        name = data["ruleset"]["name"]
    except (OSError, ValueError, KeyError, TypeError):
        return "the ruleset of the default branch"
    return f'"{name}"' if isinstance(name, str) else "the ruleset of the default branch"


def github_lines(kit_root: Path) -> list[str]:
    """Answer 4: printed, never done; each is a person's act with admin rights."""
    return [
        "GitHub (print only; each is a person's act with admin rights; this tool does none):",
        f"- ruleset: delete or relax the ruleset {ruleset_name(kit_root)} of the default branch "
        "(Settings, Rules, Rulesets); its required checks name workflows this removal deletes",
        f"- labels: delete {', '.join(LABELS)}",
        f'- issues: close the issue "{RED_TITLE}" (label agk-brief) and the open issues labelled '
        "agk-drift-audit, agk-metrics and agk-product-report",
        "- plugin: on each machine, "
        + " and then ".join(f"`{c}`" for c in PLUGIN_COMMANDS)
        + " (verify)",
    ]


def report(plan: Plan, kit_root: Path, write: bool, docs: bool) -> list[str]:
    lines = [f"{i.action} {i.rel}{i.detail}" for i in plan.items]
    if docs:
        lines += [f"remove by hand: {rel}" for rel in plan.own]
        lines.append(
            "the tool never deletes the project's own documents: delete those you no longer want "
            "in your own change"
        )
    else:
        lines.append(
            "kept: the project's own work (requirements, ADRs, specs, briefs, the vision, design "
            "documents, docs/runs/, tests); --remove-docs lists it"
        )
    gone, edited, kept = len(plan.of("delete")), len(plan.of("edit")), len(plan.of("changed"))
    if not gone and not edited:
        lines.append(f"nothing to remove; {kept} changed kit files listed")
    elif write:
        lines.append(
            f"branch {BRANCH}: deleted {gone} files, edited {edited}; {kept} changed kit files "
            "listed and kept; nothing was committed"
        )
    else:
        lines.append(
            f"dry run: {gone} files would be deleted, {edited} edited; {kept} changed kit files "
            "listed; nothing was written"
        )
    touched = [i.rel for i in plan.items if i.action in ("delete", "edit")]
    lines += adr_skeleton("Remove agk from the project", protected_classes(touched, plan.entries))
    lines += github_lines(kit_root)
    if write and (gone or edited):
        lines.append(
            f"next: review the change on the branch {BRANCH}, commit it, push it and open one "
            "pull request; git reverts it if you change your mind"
        )
    elif gone or edited:
        lines.append("next: run again with --write to build the branch")
    return lines


# --- git: one new branch, nothing committed -----------------------------------------------------


def git(target: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=target, capture_output=True, text=True
    )


def new_branch(target: Path, name: str) -> None:
    """Refuse a work tree with changes or an existing branch NAME, then switch to a new NAME."""
    status = git(target, "status", "--porcelain")
    if status.returncode != 0:
        raise Refusal("git cannot read the work tree (path class .git/)")
    if status.stdout.strip():
        raise Refusal("the work tree has changes; commit or stash them first (path class .git/)")
    if git(target, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
        raise Refusal(f"the branch {name} exists already (path class .git/)")
    if git(target, "switch", "-q", "-c", name).returncode != 0:
        raise Refusal(f"git cannot make the branch {name} (path class .git/)")


def remove(target: Path, rel: str) -> None:
    """Delete one file (and, for a script, its bytecode in `__pycache__/`, which the kit's
    .gitignore hid), then each directory below TARGET that the deletion emptied."""
    path = target / rel
    path.unlink()
    cache = path.parent / "__pycache__"
    if path.suffix == ".py" and cache.is_dir() and not cache.is_symlink():
        for pyc in cache.glob(f"{path.stem}.*.pyc"):
            pyc.unlink()
        try:
            cache.rmdir()
        except OSError:
            pass
    parent = path.parent
    while parent != target and target in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def apply(target: Path, plan: Plan) -> None:
    for item in plan.of("edit"):
        temp = (target / item.rel).with_name(f".{Path(item.rel).name}.agk-uninstall")
        temp.write_bytes(item.content or b"")
        os.replace(temp, target / item.rel)
    for item in plan.of("delete"):
        remove(target, item.rel)


# --- pause (answer 1) ---------------------------------------------------------------------------


def paused_text(text: str) -> str:
    """agk.toml with the top-level line `paused = true`: a top-level `paused = false` is replaced,
    otherwise the line goes before the first line that is neither blank nor a comment, so it is
    never inside a table or a value that spans lines."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            break
        if re.match(r"^paused\s*=\s*false\s*(#.*)?$", stripped):
            lines[i] = PAUSE_LINE + "\n"
            return "".join(lines)
    for i, line in enumerate(lines):
        if line.strip() and not line.lstrip().startswith("#"):
            lines.insert(i, PAUSE_LINE + "\n")
            return "".join(lines)
    sep = "" if not text or text.endswith("\n") else "\n"
    return text + sep + PAUSE_LINE + "\n"


def pause(target: Path, write: bool) -> int:
    path = target / "agk.toml"
    if not path.is_file() or passes_symlink(target, "agk.toml"):
        raise Refusal("agk.toml is missing (path class agk.toml): no kit installed")
    try:
        if paused(target):
            print("nothing to do: agk paused already (setting: paused in agk.toml)")
            return 0
    except CheckError as exc:
        raise Refusal(str(exc)) from None
    new = paused_text(path.read_text(encoding="utf-8"))
    try:
        if tomllib.loads(new).get("paused") is not True:
            raise ValueError
    except (tomllib.TOMLDecodeError, ValueError):
        raise Refusal(
            "the line cannot be added at the top level (setting: paused in agk.toml)"
        ) from None
    listed = target / "config" / "protected-paths.txt"
    entries = read_list(listed.read_text(encoding="utf-8")) if listed.is_file() else []
    if write:
        new_branch(target, PAUSE_BRANCH)
        path.write_text(new, encoding="utf-8")
    print(f"edit agk.toml (adds the top-level line `{PAUSE_LINE}`)")
    if write:
        print(f"branch {PAUSE_BRANCH}: agk.toml edited; nothing was committed")
    else:
        print("dry run: 1 file would be edited; nothing was written")
    for line in adr_skeleton("Pause agk", protected_classes(["agk.toml"], entries)):
        print(line)
    print(
        "while paused, governance and proof report success with the one line `agk paused`, the "
        "router writes no label and no session acts; removing the line resumes, nothing is deleted"
    )
    if write:
        print(
            f"next: write the ADR on the branch {PAUSE_BRANCH}, commit, push and open one pull "
            "request"
        )
    else:
        print("next: run again with --write to build the branch")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    flags = {"--write", "--remove-docs", "--pause"}
    rest = [a for a in args if a not in flags]
    if len(rest) != 1 or rest[0].startswith("-") or len(set(args) & flags) != len(args) - 1:
        print(USAGE, file=sys.stderr)
        return 2
    write, docs, pausing = "--write" in args, "--remove-docs" in args, "--pause" in args
    if pausing and docs:
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
        if pausing:
            return pause(target, write)
        plan = build_plan(target, kit_root)
        if write and (plan.of("delete") or plan.of("edit")):
            new_branch(target, BRANCH)
            apply(target, plan)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except (OSError, ValueError, KeyError):
        print(
            "error: cannot read or write the target or the kit sources "
            "(path class: the target root)"
        )
        return 3
    for line in report(plan, kit_root, write, docs):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
