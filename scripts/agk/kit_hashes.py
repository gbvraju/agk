"""Build and check kit/hashes.json (SPEC-0008 rules 1, 2, 22, 25). Kit-only: never installed.

The table keeps, for every released kit version, the SHA-256 of every file an installer writes, so
`upgrade.py` can tell a locally edited file from an outdated one without a lock file in the target.
It is a committed generated file (an exception to principle 5, ADR-0018): it is written from git
history and this script regenerates and compares every row, so it cannot drift.

    python3 scripts/agk/kit_hashes.py            check the committed table against the history
    python3 scripts/agk/kit_hashes.py --write    regenerate kit/hashes.json

History is the first-parent history up to the merge base with the base ref (the default branch), so
a pull request sees the default branch plus its own working tree. The version of the working tree is
the current one: its row is taken from the working tree; a past version's row is taken from the
commits where its files changed. A version other than 0.1.0 with two different files at one path is
a change without a version bump (the bump rule).
"""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path
from typing import Any

from changelog_fragments import FRAG_DIR, tree_fragments, well_formed
from common import CheckError, merge_base, pr_mode, repo_root, resolve_base, run

NAME = "kit-hashes"
USAGE = "usage: kit_hashes.py [--check | --write]"
TABLE = "kit/hashes.json"
MANIFEST = "kit/manifest.json"
EXCEPTION = "0.1.0"  # the one version whose files changed without a bump (SPEC-0008 rule 22)
MAPS = ("verbatim", "blocks", "templates")
Snapshot = dict[str, dict[str, str]]


def git_out(root: Path, *args: str, data: bytes | None = None) -> bytes:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, input=data
    )
    if proc.returncode != 0:
        raise CheckError(f"git {args[0]} failed")
    return proc.stdout


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def normalized(data: bytes) -> bytes:
    """The text of a marked block: the kit file without trailing newlines, then one newline."""
    return data.rstrip(b"\n") + b"\n"


def snapshot_of(manifest: dict, read: Any) -> Snapshot:
    """Hashes of what the installers write; `read(path)` gives the file bytes or None."""
    adopt = manifest.get("adopt") or {}
    rendered = set(manifest.get("rendered") or [])
    sources = set(manifest.get("templates", {}).values()) | set(
        (adopt.get("templates") or {}).values()
    )
    snap: Snapshot = {name: {} for name in MAPS}
    for path in [*manifest.get("verbatim", []), *manifest.get("experimental", [])]:
        data = read(path)
        if data is not None:
            snap["verbatim"][path] = hashlib.sha256(data).hexdigest()
    block_sources = adopt.get("block_sources") or {}
    for path in sorted(set(adopt.get("blocks") or {}) - rendered):
        data = read(block_sources.get(path, path))
        if data is not None:
            snap["blocks"][path] = hashlib.sha256(normalized(data)).hexdigest()
    for path in sorted(sources):
        data = read(path)
        if data is not None:
            snap["templates"][path] = hashlib.sha256(data).hexdigest()
    return snap


def snapshot_worktree(root: Path) -> tuple[str, Snapshot]:
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))

    def read(path: str) -> bytes | None:
        file = root / path
        return file.read_bytes() if file.is_file() else None

    return str(manifest["kit_version"]), snapshot_of(manifest, read)


class Blobs:
    """File contents of commits through one `git cat-file --batch` per request."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache: dict[str, bytes] = {}

    def fetch(self, ids: list[str]) -> None:
        need = [i for i in dict.fromkeys(ids) if i not in self.cache]
        if not need:
            return
        out = git_out(self.root, "cat-file", "--batch", data=("\n".join(need) + "\n").encode())
        pos = 0
        for blob in need:
            end = out.index(b"\n", pos)
            header = out[pos:end].split()
            size = int(header[2])
            self.cache[blob] = out[end + 1 : end + 1 + size]
            pos = end + 1 + size + 1


def snapshot_commit(root: Path, blobs: Blobs, commit: str) -> tuple[str, Snapshot] | None:
    listing = git_out(root, "ls-tree", "-r", "-z", commit).split(b"\0")
    tree: dict[str, str] = {}
    for entry in filter(None, listing):
        meta, _, path = entry.partition(b"\t")
        tree[path.decode()] = meta.split()[2].decode()
    if MANIFEST not in tree:
        return None
    blobs.fetch([tree[MANIFEST]])
    manifest = json.loads(blobs.cache[tree[MANIFEST]].decode("utf-8"))
    wanted = set(manifest.get("verbatim", [])) | set(manifest.get("experimental", []))
    wanted |= set(manifest.get("templates", {}).values())
    wanted |= set((manifest.get("adopt") or {}).get("templates", {}).values())
    wanted |= set((manifest.get("adopt") or {}).get("blocks", {}))
    wanted |= set(((manifest.get("adopt") or {}).get("block_sources") or {}).values())
    blobs.fetch([tree[p] for p in wanted if p in tree])

    def read(path: str) -> bytes | None:
        return blobs.cache[tree[path]] if path in tree else None

    return str(manifest["kit_version"]), snapshot_of(manifest, read)


def history(root: Path, base: str) -> list[tuple[str, str, Snapshot]]:
    """(commit, version, snapshot) of the first-parent history up to `base`, oldest first."""
    commits = git_out(root, "rev-list", "--first-parent", "--reverse", base).decode().split()
    blobs = Blobs(root)
    out = []
    for commit in commits:
        found = snapshot_commit(root, blobs, commit)
        if found:
            out.append((commit, found[0], found[1]))
    return out


def build_table(root: Path, base: str) -> dict:
    """The table from history up to `base`, plus the working tree as the current version."""
    snaps: dict[str, list[Snapshot]] = {}
    commits: dict[str, list[str]] = {}
    flow = pr_mode(root) == "flow"
    for commit, version, snap in history(root, base):
        if flow and version != EXCEPTION and version in snaps:
            continue  # a build after the release of this version belongs to the next version
        if snap not in snaps.setdefault(version, []):
            snaps[version].append(snap)
            commits.setdefault(version, []).append(commit)
    current, here = snapshot_worktree(root)
    if flow and current != EXCEPTION and current in snaps:
        pass  # between two releases the row of the current version stays the release's
    elif here not in snaps.setdefault(current, []):
        snaps[current].append(here)
    releases = {}
    for version in sorted(snaps, key=version_key):
        row: dict[str, Any] = {"commits": commits.get(version, [])}
        for name in MAPS:
            merged: dict[str, list[str]] = {}
            for snap in snaps[version]:
                for path, digest in snap[name].items():
                    if digest not in merged.setdefault(path, []):
                        merged[path].append(digest)
            row[name] = merged
        releases[version] = row
    return {"table": 1, "releases": releases}


def dump(table: dict) -> str:
    """One line per path, so a diff of the table is readable."""
    lines = ["{", f' "table": {table["table"]},', ' "releases": {']
    versions = sorted(table["releases"], key=version_key)
    for v, version in enumerate(versions):
        row = table["releases"][version]
        lines.append(f'  "{version}": {{')
        lines.append(f'   "commits": {json.dumps(row["commits"])},')
        for n, name in enumerate(MAPS):
            lines.append(f'   "{name}": {{')
            paths = sorted(row[name])
            for p, path in enumerate(paths):
                comma = "," if p + 1 < len(paths) else ""
                lines.append(f"    {json.dumps(path)}: {json.dumps(row[name][path])}{comma}")
            lines.append("   }" + ("," if n + 1 < len(MAPS) else ""))
        lines.append("  }" + ("," if v + 1 < len(versions) else ""))
    lines += [" }", "}"]
    return "\n".join(lines) + "\n"


CHANGELOG = "CHANGELOG.md"


def path_class(path: str) -> str:
    return path.rsplit("/", 1)[0] + "/" if "/" in path else path


def base_text(root: Path, base: str, path: str) -> str | None:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "show", f"{base}:{path}"], cwd=root, capture_output=True
    )
    return proc.stdout.decode("utf-8", "replace") if proc.returncode == 0 else None


def now_text(root: Path, path: str) -> str | None:
    file = root / path
    return file.read_text(encoding="utf-8", errors="replace") if file.is_file() else None


def flow_problems(root: Path, base: str) -> list[str]:
    """In flow mode a build adds one changelog fragment (SPEC-0031 rules 1, 2 and 6).

    Compared with the base, for a pull request that leaves `kit_version` as it is: the build does
    not edit `CHANGELOG.md` or `kit/hashes.json`; the installed files whose hashes differ (the
    trigger of SPEC-0028 rule 2) need exactly one new fragment, and any new fragment is one line
    `- <one-line change>`. A raised version is a release pull request, which `check_release.py`
    checks, and its table is compared in full."""
    found = snapshot_commit(root, Blobs(root), base)
    if found is None:
        return []
    old_version, old = found
    version, now = snapshot_worktree(root)
    if version != old_version:
        return []
    changed = sorted(
        path for name in MAPS for path, digest in now[name].items() if old[name].get(path) != digest
    )
    problems: list[str] = []
    if now_text(root, CHANGELOG) != base_text(root, base, CHANGELOG):
        problems.append(
            f"{CHANGELOG}: in flow mode a build does not edit the changelog; "
            f"it adds one fragment under {FRAG_DIR}"
        )
    if now_text(root, TABLE) != base_text(root, base, TABLE):
        problems.append(
            f"{TABLE}: in flow mode a build does not edit the table; the release regenerates it"
        )
    before = set(tree_fragments(root, base))
    folder = root / FRAG_DIR
    here = (
        sorted(f"{FRAG_DIR}{p.name}" for p in folder.iterdir() if p.is_file())
        if folder.is_dir()
        else []
    )
    added = [path for path in here if path not in before]
    if before - set(here) or any(
        now_text(root, path) != base_text(root, base, path) for path in before & set(here)
    ):
        problems.append(f"{FRAG_DIR}: a build does not remove or edit a fragment; the release does")
    if changed and not added:
        classes = ", ".join(sorted({path_class(path) for path in changed}))
        problems.append(
            f"{classes}: in flow mode a change to an installed path needs one fragment "
            f"under {FRAG_DIR}"
        )
    if len(added) > 1:
        problems.append(f"{FRAG_DIR}: in flow mode a build adds exactly one fragment")
    if any(not well_formed(path, now_text(root, path) or "") for path in added):
        problems.append(
            f"{FRAG_DIR}: a fragment is one line `- <one-line change>` without a pull request "
            "number, in a file named <slug>.md of [a-z0-9-]"
        )
    return problems


def has_file(root: Path, base: str) -> bool:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "cat-file", "-e", f"{base}:{CHANGELOG}"], cwd=root, capture_output=True
    )
    return proc.returncode == 0


def base_of(root: Path) -> str:
    base = resolve_base(root, None)
    return merge_base(root, base) if base else "HEAD"


def problems(root: Path, base: str | None = None) -> list[str]:
    """Differences between the committed table and the regenerated one (empty: it cannot drift)."""
    base = base or base_of(root)
    if git_out(root, "rev-parse", "--is-shallow-repository").strip() == b"true":
        return ["the repository is a shallow clone; the table is checked against the full history"]
    path = root / TABLE
    if not path.is_file():
        return [f"{TABLE} is missing"]
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = build_table(root, base)
    current, _ = snapshot_worktree(root)
    found: list[str] = []
    old_row = snapshot_commit(root, Blobs(root), base)
    between = pr_mode(root) == "flow" and old_row is not None and old_row[0] == current
    if committed.get("table") != 1:
        found.append(f"{TABLE}: table version is not 1")
    if current not in committed.get("releases", {}):
        found.append(f"{TABLE} has no row for kit_version {current}")
    for version in sorted(
        set(committed.get("releases", {})) | set(fresh["releases"]), key=version_key
    ):
        have = committed.get("releases", {}).get(version)
        want = fresh["releases"].get(version)
        if between and version == current and have is not None:
            continue  # SPEC-0031 rule 6: the release regenerates the current row
        if have is None or want is None:
            found.append(
                f"{TABLE}: row {version} {'is missing' if have is None else 'has no source'}"
            )
            continue
        for name in MAPS:
            if have.get(name) != want[name]:
                found.append(f"{TABLE}: row {version} differs from the history in {name}")
        listed = have.get("commits", [])
        regenerated = want["commits"]
        if version == current:
            ok = listed == regenerated[: len(listed)]
        else:
            ok = listed == regenerated
        if not ok:
            found.append(f"{TABLE}: row {version} names commits that differ from the history")
    if pr_mode(root) == "flow":
        return found + flow_problems(root, base)
    for version, row in fresh["releases"].items():
        if version == EXCEPTION:
            continue
        for name in MAPS:
            for path_, digests in row[name].items():
                if len(digests) > 1:
                    found.append(
                        f"{version}: {path_} has more than one version of its file; "
                        "a change to an installed path needs a kit_version bump"
                    )
    return found


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args not in ([], ["--check"], ["--write"]):
        print(USAGE, file=sys.stderr)
        return 2
    root = repo_root()
    if args == ["--write"]:
        (root / TABLE).write_text(dump(build_table(root, base_of(root))), encoding="utf-8")
        print(f"wrote {TABLE}")
        return 0
    found = problems(root)
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if not found:
        print(f"ok {NAME}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
