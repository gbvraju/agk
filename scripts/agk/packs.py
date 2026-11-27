# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The knowledge resolver (SPEC-0077 rule 5; REQ-084 AC2; brief #2032, ADR-0839).
Installed: `kit/manifest.json` lists it in `verbatim`.

`files(root, kind)` gives each file of one of rule 2's nine kinds as `(layer, path)`, in one order:
`agk-core` (the kit's file or folder through `kit_root.kit_file`), then each pack of `[packs] use`
in its listed order (the files its manifest lists under `<kind>/`), then the project's own files.
In the installed layout the kit's file is the project's path, so it is read once, as `agk-core`
(`Q-2032-1`). A refused `[packs]` table, or a pack in use that `check_packs.problems` fails, raises
`Refused` with one line naming the setting or the rule and the pack, never a value: a reader stops
there, never with a partial read. `rows` composes rows by a key, a later layer's rows of a name
replacing the earlier ones (a proposal for a person to confirm, `Q-PB-1`). Standard library,
`config`, `check_packs` and `kit_root` only; reads files only: no network, no model.

The lock (SPEC-0077 rule 4; REQ-084 AC3; brief #2033, ADR-0840), `config/packs.lock`: one `[[pack]]`
per pack with `id`, `version`, `sha256` (its manifest's) and `files = [{ path, sha256 }]`.
`verify` (offline; `check_packs.findings` calls it, so it runs in the `playbooks` step) fails a
locked file whose hash differs, a file the lock does not hold, a lock entry whose folder is
missing, a locked pack `[packs] use` does not list and a use entry the lock does not hold or that
differs from it, each `rule 4: <path class>: <what> (key|setting: ...)`, never a value. `add` and
`update --check` read a source only on the person's recorded yes (`steward_owner.yes_of`, as
`research` does) and never in a builder session; `add` copies a pack only after `check_packs`
passed on it, writes the lock and prints the `[packs] use` entry, never `agk.toml` (`Q-PC-2`).

    python3 scripts/agk/packs.py verify [--root DIR]
    python3 scripts/agk/packs.py add SOURCE [--tag TAG] --said FILE --at TIME [--by LOGIN]
    python3 scripts/agk/packs.py update --check --said FILE --at TIME [--by LOGIN] [--root DIR]

Exit 0 ok, 1 a finding or no yes, 2 a refusal or usage, 4 a source that cannot be read.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess  # nosec B404 - git with a fixed argument list, only after the person's yes
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import kit_root
from common import CheckError, run, utf8_output

CORE = "agk-core"
PROJECT = "project"
# Rule 2: where `agk-core` keeps each kind today; None: no built-in file of the kind yet.
KIT = {
    "playbooks": "config/playbooks",
    "domains": "config/domains",
    "standards": "config/standards.toml",
    "stack-defaults": "config/stack-defaults.toml",
    "stack-signals": "config/stack-signals.toml",
    "domain-signals": "config/domain-signals.toml",
    "data-patterns": None,
    "parts": None,
    "skills": "skills",
}
PROVENANCE = ("source", "basis")  # rule 3's keys of a pack's entry, not the reader's format


class Refused(CheckError):
    """A pack in use cannot be read; the line names the setting or the rule, never a value."""


def _expand(path: Path | None, kind: str) -> list[Path]:
    if path is None:
        return []
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(path.glob("*/SKILL.md" if kind == "skills" else "*.toml"))


def used(root: Path) -> list[tuple[str, Path]]:
    """Each pack of `[packs] use` in its order with its folder; raises `Refused`."""
    import check_packs  # here: check_packs imports playbook_format, which imports this module

    import config

    try:
        ids = [entry["id"] for entry in config.packs_settings(Path(root))["use"]]
    except config.PacksSettingError as exc:
        raise Refused(f"packs: {exc}") from None
    out = []
    for pid in ids:
        folder = Path(root) / check_packs.FOLDER / pid
        found = check_packs.problems(folder)
        if found:
            raise Refused(f"packs: {found[0]}")
        out.append((pid, folder))
    return out


def files(root: Path, kind: str, core: Path | None = None) -> list[tuple[str, Path]]:
    """Rule 5: the `(layer, path)` of each file of KIND, `agk-core` first, the project's last.
    CORE names `agk-core`'s file in place of `kit_root.kit_file` (a reader given its kit root).
    Raises `Refused`, and `kit_root.Refused` as `kit_file` does, each naming the setting."""
    import check_packs

    if kind not in KIT:
        raise ValueError(kind)
    root = Path(root)
    rel = KIT[kind]
    if core is None and rel is not None:
        core = kit_root.kit_file(root, rel)
    out = [(CORE, path) for path in _expand(core, kind)]
    for pid, folder in used(root):
        listed = (check_packs.load(folder / check_packs.MANIFEST) or {}).get("files", {})
        out += [(pid, folder / name) for name in sorted(listed) if name.startswith(f"{kind}/")]
    own = root / rel if rel is not None else None
    if own is not None and core is not None and own.resolve() != core.resolve():
        out += [(PROJECT, path) for path in _expand(own, kind)]
    return out


def label(layer: str, rel: str) -> str:
    """The path class a reader names for a layer's file: a pack's folder, else REL."""
    return f"config/packs/{layer}" if layer not in (CORE, PROJECT) else rel


def plain(entry: dict, layer: str) -> dict:
    """A pack's entry without its provenance keys (rule 3); the kit's and project's as they are."""
    if layer in (CORE, PROJECT):
        return entry
    return {k: v for k, v in entry.items() if k not in PROVENANCE}


def rows(layers: list[tuple[str, list[dict]]], key: str) -> list[dict]:
    """`Q-PB-1`: the rows of each layer in order, a later layer's rows of one KEY value replacing
    every earlier row of that value; the first place of a value is kept."""
    out: dict[object, list[dict]] = {}
    for layer, found in layers:
        mine: dict[object, list[dict]] = {}
        for row in found:
            mine.setdefault(row.get(key), []).append(plain(row, layer))
        out.update(mine)
    return [row for group in out.values() for row in group]


# --- the lock (SPEC-0077 rule 4, brief #2033, ADR-0840) -------------------------------------------

LOCK = "config/packs.lock"
LOCK_CLASS = f"rule 4: {LOCK}: the lock is not readable or out of form (key: pack)"
NO_YES = "nothing added or read: the person's yes is not recorded (setting: the recorded yes)"
TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
NAME = re.compile(r"^[A-Za-z0-9._/-]+$")  # a pack's file names: nothing the lock must escape


def lock_entry(folder: Path) -> dict:
    """The lock's entry of the pack at FOLDER: every file of it with its SHA-256."""
    import check_packs

    data = check_packs.load(folder / check_packs.MANIFEST) or {}
    files = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())
    return {
        "id": folder.name,
        "version": data.get("version"),
        "sha256": check_packs.digest(folder / check_packs.MANIFEST),
        "files": [{"path": f, "sha256": check_packs.digest(folder / f)} for f in files],
    }


def lock_text(entries: list[dict]) -> str:
    out = []
    for e in sorted(entries, key=lambda e: e["id"]):
        rows = ",\n".join(
            f'  {{ path = "{f["path"]}", sha256 = "{f["sha256"]}" }}' for f in e["files"]
        )
        out.append(
            f'[[pack]]\nid = "{e["id"]}"\nversion = "{e["version"]}"\n'
            f'sha256 = "{e["sha256"]}"\nfiles = [\n{rows},\n]\n'
        )
    return "\n".join(out)


def _in_form(e: object) -> bool:
    import check_packs

    keys = {"id", "version", "sha256", "files"}
    if not isinstance(e, dict) or set(e) != keys or not isinstance(e["files"], list):
        return False
    if not all(isinstance(e[k], str) for k in ("id", "version", "sha256")):
        return False
    files_ok = all(
        isinstance(f, dict)
        and set(f) == {"path", "sha256"}
        and all(isinstance(v, str) for v in f.values())
        and not Path(f["path"]).is_absolute()
        and ".." not in Path(f["path"]).parts
        for f in e["files"]
    )
    return files_ok and bool(check_packs.SLUG.match(e["id"])) and e["id"] != check_packs.CORE


def read_lock(root: Path) -> list[dict] | None:
    """The lock's entries (`[]` with no lock); None when it is not TOML or out of form."""
    path = Path(root) / LOCK
    if not path.is_file():
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    entries = data.get("pack", [])
    if set(data) - {"pack"} or not isinstance(entries, list) or not all(map(_in_form, entries)):
        return None
    return entries


def verify(root: Path, use: list[dict] | None) -> list[str]:
    """Rule 4 (offline): each lock problem; USE is `[packs] use`, None when the table is refused
    (its `rule 12:` line names it), and then use entries are not compared."""
    import check_packs

    root = Path(root)
    entries = read_lock(root)
    if entries is None:
        return [LOCK_CLASS]
    out = []
    by_id = {e["id"]: e for e in entries}
    trust = None
    if use is not None and entries:
        import config

        trust = config.packs_settings(root)["trust"]  # USE was read from it: not refused
    for e in entries:
        folder = root / check_packs.FOLDER / e["id"]
        label = f"rule 4: {check_packs.FOLDER}/{e['id']}"
        if not folder.is_dir():
            out.append(f"{label}: a lock entry's pack folder is missing (key: pack)")
            continue
        held = {f["path"]: f["sha256"] for f in e["files"]}
        on_disk = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
        for rel in sorted(held):
            if rel not in on_disk or check_packs.digest(folder / rel) != held[rel]:
                out.append(f"{label}: a locked file's SHA-256 differs (key: files)")
        if on_disk - set(held):
            out.append(f"{label}: a file the lock does not hold (key: files)")
        manifest = folder / check_packs.MANIFEST
        if manifest.is_file() and check_packs.digest(manifest) != e["sha256"]:
            out.append(f"{label}: a locked file's SHA-256 differs (key: sha256)")
        if trust is not None and manifest.is_file():
            import pack_scan  # rule 6 (brief #2034, ADR-0841): trust and `kit` at verify too

            data = check_packs.load(manifest) or {}
            out += pack_scan.admitted(root, data, f"{check_packs.FOLDER}/{e['id']}", trust)
        if use is not None and e["id"] not in {u["id"] for u in use}:
            out.append(f"{label}: a locked pack is not listed in use (setting: packs.use)")
    for u in use or []:
        label = f"rule 4: {check_packs.FOLDER}/{u['id']}"
        found = by_id.get(u["id"])
        if found is None:
            out.append(f"{label}: a use entry the lock does not hold (setting: packs.use)")
        elif (found["version"], found["sha256"]) != (u["version"], u["sha256"]):
            out.append(f"{label}: a use entry differs from the lock (setting: packs.use)")
    return list(dict.fromkeys(out))


def check(root: Path) -> list[str]:
    """`verify` with `[packs] use` read here; a refused table is its `rule 12:` line."""
    import config

    try:
        use = config.packs_settings(Path(root))["use"]
    except CheckError as exc:
        return [f"rule 12: {exc}", *verify(root, None)]
    return verify(root, use)


# --- add and update --check: a source is read only on the person's recorded yes -----------------


def _builder() -> bool:
    return "builder" in (os.environ.get("AGK_AGENT"), os.environ.get("AGK_ROLE"))


def _yes(
    root: Path, said: Path, at: str, by: str | None, what: str, record
) -> tuple[int, list[str]]:
    """`steward_owner.research`'s order: a refusal, else the yes or the no recorded as Setup."""
    import steward_owner
    import steward_voice

    if _builder():
        return 2, [
            "refused: a builder session adds or reads no pack; the steward runs it on the"
            " person's yes (setting: AGK_AGENT)"
        ]
    code, refusal, words = steward_owner.yes_of(Path(root), Path(said), by)
    if refusal:
        return code, [refusal]
    yes = bool(words) and steward_voice.is_yes(words)
    choice = "yes" if yes else "no"
    code, lines = record(root, f'{what}: {choice} because the person said "{words}" at {at}')
    if code:
        return code, lines
    return (0, lines) if yes else (1, [*lines, NO_YES])


def record_note(root: Path, text: str) -> tuple[int, list[str]]:
    import steward

    return steward.record(Path(root), "Setup", text, steward.gh_api)


def fetch_source(source: str, tag: str | None, dest: Path) -> bool:
    """A folder is copied; a git URL is cloned at TAG, depth 1. False when it cannot be read."""
    if tag is None:
        if not Path(source).is_dir():
            return False
        shutil.copytree(source, dest, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        return True
    if not source.startswith("https://"):
        return False
    argv = ["git", "clone", "-q", "--depth", "1", "--branch", tag, "--", source, str(dest)]
    done = subprocess.run(argv, capture_output=True, check=False)  # nosec B603 - fixed argv, after the yes
    shutil.rmtree(dest / ".git", ignore_errors=True)
    return done.returncode == 0


def remote_tags(source: str) -> list[str] | None:
    """The tags at an `https` SOURCE; None for any other source or when it cannot be read."""
    if not source.startswith("https://"):
        return None
    argv = ["git", "ls-remote", "--tags", "--refs", "--", source]
    done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", check=False)  # nosec B603 - fixed argv, after the yes
    if done.returncode:
        return None
    return [
        line.rsplit("refs/tags/", 1)[-1]
        for line in done.stdout.splitlines()
        if "refs/tags/" in line
    ]


def _kind(source: str) -> str:
    return "git" if "://" in source else "folder"


def add(root, source, said, at, *, by=None, tag=None, fetch=fetch_source, record=record_note):
    """Rule 4: on a recorded yes, fetch SOURCE, check it, copy it and write the lock."""
    import check_packs

    root = Path(root)
    kind = _kind(source)
    if kind == "git" and (not source.startswith("https://") or not TAG.match(tag or "")):
        return 2, ["rule 4: a git source takes an exact tag (source: git)"]
    if kind == "folder" and tag is not None:
        return 2, ["rule 4: a folder source takes no tag (source: folder)"]
    entries = read_lock(root)
    if entries is None:
        return 2, [LOCK_CLASS]
    code, lines = _yes(root, said, at, by, "pack-add", record)
    if code:
        return code, lines
    folder = Path(source) if kind == "git" or Path(source).is_absolute() else root / source
    with tempfile.TemporaryDirectory() as tmp:
        got = Path(tmp) / "got"
        if not fetch(source if kind == "git" else str(folder), tag, got):
            return 4, [*lines, f"refused: the pack cannot be fetched (source: {kind})"]
        pid = (check_packs.load(got / check_packs.MANIFEST) or {}).get("id")
        if not isinstance(pid, str) or not check_packs.SLUG.match(pid) or pid == check_packs.CORE:
            return 1, [*lines, "rule 3: config/packs/: the pack's id is out of form (key: id)"]
        if any(
            p.is_symlink() or not NAME.match(p.relative_to(got).as_posix()) for p in got.rglob("*")
        ):
            return 1, [*lines, f"rule 4: {check_packs.FOLDER}/{pid}: the pack holds a symbolic"
                       " link or a file name out of form (key: files)"]  # fmt: skip
        stage = Path(tmp) / pid
        shutil.copytree(got, stage, symlinks=True)
        import pack_scan  # rule 6 (brief #2034, ADR-0841): the adoption scans, before any write

        if found := check_packs.problems(stage) + pack_scan.scan(root, stage):
            return 1, [*lines, *dict.fromkeys(found)]
        entry = lock_entry(stage)
        same = [e for e in entries if (e["id"], e["version"]) == (pid, entry["version"])]
        if same and (same[0]["sha256"], same[0]["files"]) != (entry["sha256"], entry["files"]):
            return 1, [
                *lines,
                f"rule 6: {check_packs.FOLDER}/{pid}: the pack changed at the locked version"
                " (key: version)",
            ]
        if same:
            return 1, [
                *lines,
                "refused: the pack is in the lock at that version; update --check"
                " lists newer ones (setting: packs.use)",
            ]
        dest = root / check_packs.FOLDER / pid
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(stage, dest)
    (root / LOCK).write_text(
        lock_text([*(e for e in entries if e["id"] != pid), entry]), encoding="utf-8"
    )
    use = f'{{ id = "{pid}", version = "{entry["version"]}", sha256 = "{entry["sha256"]}" }}'
    return 0, [
        *lines,
        f"added {check_packs.FOLDER}/{pid} and {LOCK}; add it with its ADR, in agk.toml",
        "protected: `config/` (name them in this change's ADR)",
        f"[packs] use: {use}",
        "gitleaks: not run",
    ]


def _version(text: str) -> tuple[int, ...] | None:
    found = TAG.match(text)
    return tuple(int(x) for x in found.groups()) if found else None


def update_check(root, said, at, *, by=None, tags=remote_tags, record=record_note):
    """Rules 4 and 8: on a recorded yes, the newer exact tags of each locked pack; no write."""
    import check_packs

    root = Path(root)
    entries = read_lock(root)
    if entries is None:
        return 2, [LOCK_CLASS]
    code, lines = _yes(root, said, at, by, "pack-update-check", record)
    if code:
        return code, lines
    code = 0
    for e in entries:
        manifest = root / check_packs.FOLDER / e["id"] / check_packs.MANIFEST
        source = (check_packs.load(manifest) or {}).get("source")
        if not isinstance(source, str) or not source.startswith("https://"):
            code = 2
            lines.append(f"{e['id']}: the source is not a public https URL (source: git)")
            continue
        found = tags(source)
        if found is None:
            code = 4
            lines.append(f"{e['id']}: the source cannot be read (source: git)")
            continue
        now = _version(e["version"]) or ()
        newer = sorted({v for t in found if (v := _version(t)) and v > now})
        names = ", ".join(".".join(map(str, v)) for v in newer)
        lines.append(
            f"{e['id']} {e['version']}: " + (f"newer {names}" if newer else "no newer tag")
        )
    return code, lines or ["no pack in the lock"]


def cmd_verify(root: Path) -> int:
    found = check(root)
    for line in found:
        print(f"FAIL packs: {line}")
    if found:
        return 1
    count = len(read_lock(root) or [])
    print(f"ok packs: {count} packs verified" if count else "ok packs: none in use")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="packs.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify").add_argument("--root", type=Path)
    for name in ("add", "update"):
        c = sub.add_parser(name)
        if name == "add":
            c.add_argument("source")
            c.add_argument("--tag")
        else:
            c.add_argument("--check", action="store_true")
        c.add_argument("--said", type=Path, required=True)
        c.add_argument("--at", required=True)
        c.add_argument("--by")
        c.add_argument("--root", type=Path)
    opts = parser.parse_args(argv)
    from common import repo_root

    root = opts.root or repo_root()
    if opts.command == "verify":
        return run("packs", lambda: cmd_verify(root))
    if opts.command == "update" and not opts.check:
        print(
            "refused: a real update is `add` of the new tag with its ADR (rule 8)", file=sys.stderr
        )
        return 2
    if opts.command == "add":
        code, lines = add(root, opts.source, opts.said, opts.at, by=opts.by, tag=opts.tag)
    else:
        code, lines = update_check(root, opts.said, opts.at, by=opts.by)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
