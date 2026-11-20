# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Personal mode's private state: `AGK_HOME`, the project id, the registry, attach and detach.

    python3 personal_state.py id [--clone DIR]
    python3 personal_state.py attach --person LOGIN [--share | --new] [--clone DIR]
    python3 personal_state.py detach [--delete-state] [--clone DIR]

SPEC-0041 build (c), rules 1 to 4 and parts of rules 27 to 29. The state lives under `AGK_HOME`
(default `~/.agk`, or `%USERPROFILE%\\.agk` on Windows): `registry.toml` maps the real path of a
clone's git common dir to its id, and `projects/<id>/` is the sidecar, a private git repository
with the kit's layout. Nothing is written in the clone: every git call on it is read-only and runs
with `--no-optional-locks` (rule 4). On POSIX the state is `0700` and its files `0600` (rule 28).
Standard library only; no network. Refusals name the rule or the setting, never a value.

Build (l), rules 19, 26 and 27 (brief #1506): `attach` records the plugin version as `[personal]
plugin_version` and never a script; `PLUGIN_SCHEMA` and `MIGRATIONS` are what `personal.py upgrade`
reads; `install_hook` and `remove_hook` write and remove the opt-in `pre-push` hook, the one write
under the clone's `.git/`, and `detach` removes that hook only when its bytes are what
`install_hook` wrote.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import PERSONAL_PINNED, CheckError  # noqa: E402
from local_mode import SESSION_SETTING  # noqa: E402

USAGE = (
    "usage: personal_state.py id|attach|detach [--clone DIR] [--person LOGIN] "
    "[--share|--new] [--delete-state]"
)
KIT = Path(__file__).resolve().parents[2]
TEMPLATE = KIT / "kit" / "templates" / "personal.toml"
DECISIONS_LOG = KIT / "kit" / "templates" / "decisions-log.md"
PLUGIN_JSON = KIT / ".claude-plugin" / "plugin.json"
LAW = PERSONAL_PINNED  # rule 26: the pinned copies, checked by `doctor.py`
# Rule 27: the schema this plugin writes, and the step from each older one: a function of the
# sidecar that changes its files and returns their paths (none yet: schema 1 is the first).
PLUGIN_SCHEMA = 1
MIGRATIONS: dict[int, Callable[[Path], list[str]]] = {}
HOOK_MARK = "# agk personal mode: written by `personal.py hook install` (SPEC-0041 rule 19)"
HOOK_GONE = (
    "agk pre-push: refused: the plugin path this hook records is gone; "
    "run `personal.py hook remove` and `hook install` again (rule 19)"
)
HOOK_EDITED = "the pre-push hook was changed by hand; left in place"
KEEP = ("docs/adr", "docs/briefs", "docs/specs", "forge", "metrics", "records")
HOME_SETTING = "AGK_HOME"
REGISTRY = "registry.toml"
PROJECTS = "projects"
READ_ONLY = ("config", "rev-parse", "rev-list")
LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,38}")  # a GitHub login, managed ones too (ADR-0563)
ATTACH_SUBJECT = "personal: attach"
EXPORT_LINE = (
    "detach: the records stay in the state folder; `personal.py export` takes them to team mode"
)
REQUIREMENTS = """# Requirements

The requirements of this project, kept in personal mode (SPEC-0041). Each is a `### REQ-nnn`
section with a `- Status:` line (planned | in-progress | done | retired). `REQ-001` to `REQ-099`
are AGK's own; this project's requirements start at `REQ-101`.

### REQ-001 — Nothing of AGK is written into the product repository

- Acceptance: AC1 no personal-mode command changes the product's work tree, `.git/`, refs or history
- Status: planned
"""
REVIEWERS = (
    "version: 1\n"
    "classes:\n"
    "  protected:     {paths: [constitution/, config/, docs/requirements.md, agk.toml], "
    "approvers: [maintainers]}\n"
    "  architecture:  {paths: [docs/adr/, docs/specs/], approvers: [maintainers]}\n"
    "teams:\n"
    '  maintainers: {github_team: "@PERSON"}\n'
    "verdict_authors: [PERSON]\n"
    "spec_approvers: [PERSON]\n"
)
TEST_MAP = "# REQ-n ACm -> test ids (path::name); no marker is written into the product's tests.\n"


def agk_home(env: Mapping[str, str] | None = None, osname: str | None = None) -> Path:
    """`AGK_HOME`, else `~/.agk` on POSIX and `%USERPROFILE%\\.agk` on Windows (rule 2)."""
    values: Mapping[str, str] = os.environ if env is None else env
    if values.get(HOME_SETTING):
        return Path(values[HOME_SETTING])
    base = values.get("USERPROFILE" if (osname or os.name) == "nt" else "HOME")
    if not base:
        raise CheckError(f"no home folder for the state (setting: {HOME_SETTING})")
    return Path(base) / ".agk"


def read(clone: Path, *args: str, check: bool = True) -> str | None:
    """A read-only git call on the clone (rule 4); None on failure when `check` is off."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(clone), "--no-optional-locks", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        if check:
            raise CheckError("the clone cannot be read as a git repository (rule 3)")
        return None
    return proc.stdout.strip()


def sidecar_git(sidecar: Path, *args: str) -> None:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=sidecar, capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        raise CheckError(f"git {args[-1] if args[0] == '-c' else args[0]} failed in the sidecar")


def normalise_url(url: str) -> str:
    """The URL with its scheme, credentials, a trailing `.git` and `/` removed, host lower-cased."""
    rest = url.strip()
    scheme = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://(.*)$", rest)
    if scheme:
        rest = scheme.group(1)
    elif scp := re.match(r"^([^/]+?):(.*)$", rest):
        rest = f"{scp.group(1)}/{scp.group(2)}"
    host, _, path = rest.partition("/")
    host = host.rpartition("@")[2].lower()
    rest = f"{host}/{path}".rstrip("/")
    if rest.endswith(".git"):
        rest = rest[: -len(".git")]
    return rest.rstrip("/")


def slug(text: str) -> str:
    """The last path part, lower-cased and reduced to `[a-z0-9-]`."""
    last = text.rstrip("/").rpartition("/")[2].lower()
    return re.sub(r"[^a-z0-9-]+", "-", last).strip("-") or "project"


def common_dir(clone: Path) -> str:
    """The real path of `git rev-parse --git-common-dir`: one for every worktree of a clone."""
    found = Path(read(clone, "rev-parse", "--git-common-dir") or "")
    return os.path.realpath(found if found.is_absolute() else Path(clone) / found)


def project_id(clone: Path) -> str:
    """`<slug>-<12 hex>` of rule 3: the root commits, or the normalised `origin` when shallow."""
    origin = read(clone, "config", "--get", "remote.origin.url", check=False)
    url = normalise_url(origin) if origin else None
    name = slug(url) if url else slug(Path(common_dir(clone)).parent.name)
    shallow = read(clone, "rev-parse", "--is-shallow-repository") == "true"
    roots = read(clone, "rev-list", "--max-parents=0", "HEAD", check=False)
    if roots and not shallow:
        data = "".join(f"{r}\n" for r in sorted(roots.split()))
    elif url:
        data = url
    else:
        raise CheckError("a clone with no commit and no origin has no project id (rule 3)")
    return f"{name}-{hashlib.sha256(data.encode('utf-8')).hexdigest()[:12]}"


def registry(home: Path) -> dict[str, str]:
    path = home / REGISTRY
    if not path.is_file():
        return {}
    try:
        clones = tomllib.loads(path.read_text(encoding="utf-8")).get("clones", {})
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise CheckError(f"the registry cannot be read (path: {HOME_SETTING}/{REGISTRY})") from exc
    return {str(k): str(v) for k, v in clones.items()}


def write_registry(home: Path, clones: dict[str, str]) -> None:
    """Atomic: a temporary file and a rename (keys and ids as TOML basic strings)."""
    lines = ["# Each clone's git common dir and its project id (SPEC-0041 rule 3).", "[clones]"]
    lines += [f"{json.dumps(k)} = {json.dumps(v)}" for k, v in sorted(clones.items())]
    tmp = home / f"{REGISTRY}.tmp"
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, home / REGISTRY)


@contextmanager
def private(home: Path):
    """On POSIX, `AGK_HOME` is `0700` and everything written under it `0600`/`0700` (rule 28)."""
    old = os.umask(0o077) if os.name != "nt" else None
    try:
        home.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            home.chmod(0o700)
        yield
    finally:
        if old is not None:
            os.umask(old)


def plugin_version() -> str | None:
    """The version of the plugin this script runs from (rule 26), None when it cannot be read."""
    try:
        found = json.loads(PLUGIN_JSON.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    return found if isinstance(found, str) and found else None


def settings_text(version: str | None) -> str:
    """The template's settings with the plugin version (rule 26) at the end of `[personal]`."""
    text = TEMPLATE.read_text(encoding="utf-8")
    return text + f"plugin_version = {json.dumps(version)}\n" if version else text


def make_sidecar(path: Path, person: str) -> None:
    """The kit's layout of rule 2, committed once to the sidecar's own repository."""
    path.mkdir(parents=True)
    sidecar_git(path, "init", "-q", "-b", "main")
    files = {
        "agk.toml": settings_text(plugin_version()),
        ".gitignore": "cache/\n",
        "config/reviewers.yaml": REVIEWERS.replace("PERSON", person),
        "docs/requirements.md": REQUIREMENTS,
        "docs/runs/decisions-log.md": DECISIONS_LOG.read_text(encoding="utf-8"),
        "test-map.toml": TEST_MAP,
        **{rel: (KIT / rel).read_text(encoding="utf-8") for rel in LAW},
        **{f"{rel}/.gitkeep": "" for rel in KEEP},
    }
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text, encoding="utf-8")
    (path / "cache").mkdir()
    sidecar_git(path, "add", "-A")
    sidecar_git(
        path,
        *("-c", f"user.name={person}", "-c", f"user.email={person}@personal.invalid"),
        *("-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "-m", ATTACH_SUBJECT),
    )


def installed(clone: Path) -> bool:
    """An `agk.toml` with a kit `version` in the clone's work tree (read only)."""
    top = read(clone, "rev-parse", "--show-toplevel", check=False)
    path = Path(top) / "agk.toml" if top else None
    if path is None or not path.is_file():
        return False
    try:
        return "version" in tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return True


ROOT_HINT = " (personal mode: pass --root <the sidecar's folder>)"


def root_hint(where: Path) -> str:
    """Brief #1452 answer 2: the refusal's tail when `where` is a clone with no `agk.toml` and a
    sidecar; it names the option, never the path. Any failure to read gives no tail."""
    try:
        clones = registry(agk_home())  # read first: no registry, no git process
        if not clones or installed(where):
            return ""
        if read(where, "rev-parse", "--git-dir", check=False) is None:
            return ""
        pid = clones.get(common_dir(where))
        return ROOT_HINT if pid and (agk_home() / PROJECTS / pid).is_dir() else ""
    except (CheckError, OSError):
        return ""


def attach(clone: Path, home: Path, person: str | None, choice: str | None) -> int:
    if not person or not LOGIN.fullmatch(person):
        raise CheckError("attach needs the one person's login (option: --person)")
    if installed(clone):
        raise CheckError("AGK is installed in this clone; use team mode there (rule 3)")
    cdir, pid = common_dir(clone), project_id(clone)
    clones = registry(home)
    if cdir in clones:
        print(f"attach: already attached as {clones[cdir]}")
        return 0
    if pid in clones.values() and choice is None:
        print(f"attach: the id {pid} is already the state of another clone; choose one:")
        print("  --share  this clone uses the same state")
        print("  --new    this clone gets a new state with a numbered suffix")
        print("refused: nothing written until the person chooses (rule 3)")
        return 1
    if pid in clones.values() and choice == "new":
        n = 2
        while f"{pid}-{n}" in clones.values() or (home / PROJECTS / f"{pid}-{n}").exists():
            n += 1
        pid = f"{pid}-{n}"
    with private(home):
        sidecar = home / PROJECTS / pid
        if not sidecar.is_dir():
            make_sidecar(sidecar, person)
        write_registry(home, {**clones, cdir: pid})
    print(f"attach: {pid}")
    return 0


def hook_path(clone: Path) -> Path:
    """`<git common dir>/hooks/pre-push`: one hook for every worktree of the clone (rule 19)."""
    return Path(common_dir(clone)) / "hooks" / "pre-push"


def hook_text(script: str) -> bytes:
    """The hook's bytes for the plugin's `personal.py` at SCRIPT: it fails closed, with one line,
    when that path is gone, and otherwise runs the gate with the person's approval (rule 19)."""
    lines = [
        "#!/bin/sh",
        HOOK_MARK,
        f"PLUGIN={shlex.quote(script)}",
        'if [ ! -f "$PLUGIN" ]; then',
        f"  echo {shlex.quote(HOOK_GONE)} >&2",
        "  exit 1",
        "fi",
        'exec python3 "$PLUGIN" gate --clone . --approve',
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def hook_state(path: Path) -> str | None:
    """None with no hook or one without the mark (not the kit's); `same` when its bytes are what
    `hook_text` writes for the plugin path it records, else `edited`."""
    if not path.is_file():
        return None
    data = path.read_bytes()
    text = data.decode("utf-8", "replace")
    if HOOK_MARK not in text:
        return None
    found = re.search(r"^PLUGIN=(.*)$", text, re.MULTILINE)
    try:
        script = shlex.split(found.group(1)) if found else []
    except ValueError:
        script = []
    return "same" if len(script) == 1 and data == hook_text(script[0]) else "edited"


def install_hook(clone: Path, script: str) -> str:
    """Rule 19: write the untracked `pre-push`; refused with `core.hooksPath` set or a hook in
    place."""
    if read(clone, "config", "--get", "core.hooksPath", check=False):
        raise CheckError(
            "the kit writes no hook while core.hooksPath is set (setting: core.hooksPath)"
        )
    path = hook_path(clone)
    if path.exists():
        raise CheckError("a pre-push hook exists; it is left as it is (rule 19)")
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(hook_text(script))
    if os.name != "nt":
        path.chmod(0o755)
    return "hook: installed the pre-push hook; it runs the gate before each push"


def remove_hook(clone: Path) -> str:
    """Rule 19: remove the hook only when its bytes are what `install_hook` wrote."""
    path = hook_path(clone)
    found = hook_state(path)
    if found is None:
        raise CheckError("there is no pre-push hook of the kit here (rule 19)")
    if found == "edited":
        raise CheckError(f"{HOOK_EDITED} (rule 19)")
    path.unlink()
    return "hook: removed the pre-push hook"


def detach(clone: Path, home: Path, delete: bool, stdin) -> int:
    cdir = common_dir(clone)
    clones = registry(home)
    if cdir not in clones:
        raise CheckError("this clone is not attached (rule 27)")
    pid = clones[cdir]
    rest = {k: v for k, v in clones.items() if k != cdir}
    if delete:
        if os.environ.get(SESSION_SETTING):
            raise CheckError(f"--delete-state is refused in an agent session ({SESSION_SETTING})")
        if not stdin.isatty():
            raise CheckError("--delete-state needs the person at a terminal (rule 27)")
        if pid in rest.values():
            raise CheckError("another clone shares this state; detach it first (rule 27)")
    print(EXPORT_LINE)
    if delete:
        print(f"detach: type the id {pid} to delete its state: ", end="", flush=True)
        if stdin.readline().strip() != pid:
            raise CheckError("the typed id differs; nothing deleted (rule 27)")
    with private(home):
        write_registry(home, rest)
        if delete:
            shutil.rmtree(home / PROJECTS / pid)
    print(f"detach: {pid} {'deleted' if delete else 'detached; the state is kept'}")
    hook = hook_path(clone)
    found = hook_state(hook)
    if found == "same":
        hook.unlink()
        print("detach: removed the pre-push hook")
    elif found == "edited":
        print(f"detach: {HOOK_EDITED}")
    return 0


def parse(args: list[str]) -> dict | None:
    if not args or args[0] not in ("id", "attach", "detach"):
        return None
    out: dict = {"command": args[0], "clone": ".", "person": None, "choice": None, "delete": False}
    rest = args[1:]
    while rest:
        flag = rest.pop(0)
        if flag in ("--clone", "--person") and rest:
            out[flag[2:]] = rest.pop(0)
        elif flag in ("--share", "--new") and out["choice"] is None:
            out["choice"] = flag[2:]
        elif flag == "--delete-state":
            out["delete"] = True
        else:
            return None
    return out


def main(argv: list[str] | None = None, stdin=None) -> int:
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    clone = Path(options["clone"])
    try:
        if options["command"] == "id":
            print(project_id(clone))
            return 0
        home = agk_home()
        if options["command"] == "attach":
            return attach(clone, home, options["person"], options["choice"])
        return detach(clone, home, options["delete"], stdin or sys.stdin)
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
