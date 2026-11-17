# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""One licensed plugin snapshot per release, for the private release repository (brief #1476,
ADR-0627, REQ-014). Kit-only: never installed.

    python3 scripts/agk/plugin_snapshot.py build --tag vX.Y.Z --out DIR
    python3 scripts/agk/plugin_snapshot.py publish --tag vX.Y.Z --dir DIR
    python3 scripts/agk/plugin_snapshot.py verify --tag vX.Y.Z --clone DIR

`build` reads the tag only (`git archive`) and writes exactly the paths of the allow list
`snapshot` of the tag's own `kit/manifest.json` (a tag without one, or a `--tag` that is not a tag,
is refused): a list entry ending in `/` is a folder, any other is one file. It writes
`.claude-plugin/marketplace.json` with one plugin, `"source": "."`, at the tag's version, and
prints `digest <sha256>` of the tree (each path, mode and file digest, sorted), so two builds of
one tag give one digest. It fails, naming the path class and writing nothing, on a kit file
(`check_licence_notice`'s kit files) without the owner and licence header, on a secret or
personal-data shape (`guard.scan_text`) and when the tag's `scripts/agk/kit_hashes.py --check`
fails in a throwaway clone of the tag; the tag's `kit/hashes.json` is copied as it is, every row
kept.

`publish` prints, and never runs, the owner's commands that commit DIR to the release repository
(`[release] repository` in `agk.toml`) as one commit `Release vX.Y.Z` on top of the last, tag it,
and grant or revoke one person's read access. `verify` compares a clone of the release repository
at the tag with a fresh build, byte for byte, and fails naming the first path that differs. Git
and files only: no network, no push, no tag. Refusals name the setting or path class, never a value.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_licence_notice as notice
import guard
from common import CheckError, git, repo_root, run, utf8_output

NAME = "plugin-snapshot"
USAGE = (
    "usage: plugin_snapshot.py build --tag vX.Y.Z --out DIR | publish --tag vX.Y.Z --dir DIR"
    " | verify --tag vX.Y.Z --clone DIR"
)
MANIFEST = "kit/manifest.json"
MARKETPLACE = ".claude-plugin/marketplace.json"
SETTING = "[release] repository"
HASH_CHECK = "scripts/agk/kit_hashes.py"


def tag_ref(root: Path, tag: str) -> str:
    """`refs/tags/<tag>`; a value that is not a tag (a branch moves) is refused."""
    ref = f"refs/tags/{tag}"
    if not git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}", check=False).strip():
        raise CheckError("the --tag value is not a tag of this repository (setting: --tag)")
    return ref


def allow_list(root: Path, ref: str) -> list[str]:
    """The `snapshot` list of the tag's own manifest; a tag without one is refused."""
    text = git(root, "show", f"{ref}:{MANIFEST}", check=False)
    listed = json.loads(text).get("snapshot") if text.strip() else None
    if not isinstance(listed, list) or not listed:
        raise CheckError(f"the tag's {MANIFEST} has no list (setting: snapshot)")
    return [str(p) for p in listed]


def allowed(rel: str, listed: list[str]) -> bool:
    return any(rel.startswith(p) if p.endswith("/") else rel == p for p in listed)


def tag_files(root: Path, ref: str, listed: list[str]) -> dict[str, tuple[int, bytes]]:
    """path -> (mode, bytes) of the tag's files in the allow list; nothing else is read."""
    proc = subprocess.run(  # nosec B603 B607 - git with a fixed argument list
        ["git", "-C", str(root), "archive", "--format=tar", f"{ref}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        raise CheckError("the tag does not resolve (path class tag)")
    files: dict[str, tuple[int, bytes]] = {}
    with tarfile.TarFile(fileobj=io.BytesIO(proc.stdout)) as tar:  # a plain tar of `git archive`
        for member in tar.getmembers():
            if member.isfile() and allowed(member.name, listed):
                data = tar.extractfile(member)
                mode = 0o755 if member.mode & 0o111 else 0o644
                files[member.name] = (mode, data.read() if data else b"")
    return files


def marketplace(tag: str) -> bytes:
    plugin = {
        "name": "agk",
        "source": ".",
        "description": "Workflow commands for repositories governed by agk.",
        "version": tag.removeprefix("v"),
    }
    body = {"name": "agk", "owner": {"name": "agk maintainers"}, "plugins": [plugin]}
    return (json.dumps(body, indent=2) + "\n").encode("utf-8")


def licence_problems(files: dict[str, tuple[int, bytes]], place: Path) -> list[str]:
    """check_licence_notice's rule on the snapshot's kit files (its manifest and REUSE.toml)."""
    globs = notice.annotated(place)
    found: list[str] = []
    for rel in notice.kit_files(place, sorted(files)):
        data = files[rel][1]
        if any(g.match(rel) for g in globs):
            continue
        style = notice.style_of(rel)
        if style is None or not notice.has_header(data.decode("utf-8", "replace"), style):
            found.append(f"{rel} has no owner and licence header (path class {top(rel)})")
    return found


def secret_problems(files: dict[str, tuple[int, bytes]]) -> list[str]:
    found: list[str] = []
    for rel, (_, data) in sorted(files.items()):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        kinds = sorted({f.kind for f in guard.scan_text(text)})
        if kinds:
            found.append(f"{rel} holds a {', '.join(kinds)} shape (path class {top(rel)})")
    return found


def hashes_problem(root: Path, commit: str) -> str | None:
    """The tag's own `kit_hashes.py --check`, run in a throwaway clone at the tag."""
    with tempfile.TemporaryDirectory(prefix="agk-snapshot-") as place:
        tree = Path(place) / "tree"
        git(root, "clone", "-q", "--shared", "--no-checkout", "--", ".", str(tree))
        git(tree, "checkout", "-q", "--detach", commit)
        if not (tree / HASH_CHECK).is_file():
            return f"{HASH_CHECK} is missing at the tag (path class scripts/agk/)"
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "AGK_"))}
        env["AGK_BASE"] = git(tree, "rev-parse", "HEAD").strip()
        proc = subprocess.run(  # nosec B603 - the tag's own check, a fixed argument list
            [sys.executable, HASH_CHECK, "--check"],
            cwd=tree,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    return None if proc.returncode == 0 else "kit/hashes.json fails its check (path class kit/)"


def top(rel: str) -> str:
    return rel.split("/", 1)[0] + "/" if "/" in rel else rel


def digest(files: dict[str, tuple[int, bytes]]) -> str:
    lines = [
        f"{rel}\0{mode:o}\0{hashlib.sha256(data).hexdigest()}\n"
        for rel, (mode, data) in sorted(files.items())
    ]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def snapshot(root: Path, tag: str) -> tuple[dict[str, tuple[int, bytes]], list[str]]:
    """The snapshot's files and its problems (empty: it may be written)."""
    ref = tag_ref(root, tag)
    files = tag_files(root, ref, allow_list(root, ref))
    files[MARKETPLACE] = (0o644, marketplace(tag))
    with tempfile.TemporaryDirectory(prefix="agk-snapshot-") as place:
        write(files, Path(place))
        problems = licence_problems(files, Path(place))
    problems += secret_problems(files)
    found = hashes_problem(root, git(root, "rev-parse", f"{ref}^{{commit}}").strip())
    return files, problems + ([found] if found else [])


def write(files: dict[str, tuple[int, bytes]], out: Path) -> None:
    for rel, (mode, data) in sorted(files.items()):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)


def build(root: Path, tag: str, out: Path) -> int:
    if out.exists() and any(out.iterdir()):
        raise CheckError("the out folder is not empty (path class out)")
    files, problems = snapshot(root, tag)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if problems:
        print(f"{NAME}: nothing written")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agk-snapshot-", dir=out.parent) as place:
        write(files, Path(place) / "tree")
        out.rmdir() if out.exists() else None
        shutil.move(str(Path(place) / "tree"), str(out))
    print(f"wrote {len(files)} files")
    print(f"digest {digest(files)}")
    return 0


def release_repository(root: Path) -> str:
    path = root / "agk.toml"
    data = tomllib.loads(path.read_text("utf-8")) if path.is_file() else {}
    repo = (data.get("release") or {}).get("repository")
    if not isinstance(repo, str) or repo.count("/") != 1:
        raise CheckError(f"the setting {SETTING} is unset")
    return repo


def publish(root: Path, tag: str, folder: Path) -> int:
    """Prints the owner's commands; runs none of them."""
    tag_ref(root, tag)
    repo = release_repository(root)
    q = shlex.quote
    work, src, name, tagq = q(f"{folder}.release"), q(f"{folder}/."), q(repo), q(tag)
    for line in (
        f"gh repo clone {name} {work}",
        f"git -C {work} rm -rq --ignore-unmatch .",
        f"cp -a {src} {work}/",
        f"git -C {work} add -A",
        f"git -C {work} commit -m {q(f'Release {tag}')}",
        f"git -C {work} tag {tagq}",
        f"git -C {work} push origin HEAD {tagq}",
        f"gh api --method PUT {q(f'repos/{repo}/collaborators')}/<login> -f permission=pull",
        f"gh api --method DELETE {q(f'repos/{repo}/collaborators')}/<login>",
    ):
        print(line)
    return 0


def verify(root: Path, tag: str, clone: Path) -> int:
    files, problems = snapshot(root, tag)
    if problems:
        print(f"FAIL {NAME}: the build fails; run build for its lines")
        return 1
    have = {
        p.relative_to(clone).as_posix()
        for p in clone.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(clone).parts
    }
    for rel in sorted(have | set(files)):
        path = clone / rel
        if rel not in files or rel not in have or path.read_bytes() != files[rel][1]:
            print(f"FAIL {NAME}: {rel} differs from the build (path class {top(rel)})")
            return 1
    print(f"ok {NAME}: {len(files)} files match, digest {digest(files)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    flags = {"build": "--out", "publish": "--dir", "verify": "--clone"}
    if len(args) != 5 or args[0] not in flags or args[1] != "--tag" or args[3] != flags[args[0]]:
        print(USAGE, file=sys.stderr)
        return 2
    command, tag, place = args[0], args[2], Path(args[4]).resolve()
    root = repo_root()
    if command == "build":
        return build(root, tag, place)
    if command == "publish":
        return publish(root, tag, place)
    return verify(root, tag, place)


if __name__ == "__main__":
    sys.exit(run(NAME, main))
