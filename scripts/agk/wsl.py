"""/agk:wsl's helper: the plan, the status lines and the adapter pull request (brief #1376, ADR-0577).

    python3 wsl.py plan [--state FILE] [--back] [--root DIR]
    python3 wsl.py status [--state FILE] [--root DIR]
    python3 wsl.py pr --to wsl|windows [--brief N|none] [--date YYYY-MM-DD] [--root DIR]
    python3 wsl.py open --body FILE --branch NAME [--title TEXT] [--root DIR]

Run from the plugin root, never installed into a project. FILE is the `-Json` table of
`wsl_setup.ps1`. `plan` prints five lines or fewer and `status` one line per part; both read the
default branch's `agk.toml` with one GET through `gh`. `pr` changes `launch_adapter` in the
`[flow]` table of the project's `agk.toml`, writes the project's own ADR (Proposed) and prints the
pull request body; it commits nothing. `open` posts the one draft pull request by REST and never
merges. Exit 0, 1 on a refusal, 2 on a usage error.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import utf8_output

USAGE = (
    "usage: wsl.py plan [--state FILE] [--back] | status [--state FILE] | "
    "pr --to wsl|windows [--brief N|none] [--date YYYY-MM-DD] | "
    "open --body FILE --branch NAME [--title TEXT]  [--root DIR]"
)
SETTING = "(setting: launch_adapter in the flow table of agk.toml)"
ADAPTERS = {  # the kit's two adapter commands, as doctor.ADAPTERS sets them
    "windows": "pwsh -NoProfile -File scripts/start-session-windows.ps1",
    "wsl": "bash scripts/start-session-local.sh",
}
NAMES = {"windows": "Windows", "wsl": "WSL"}
STATE_KEYS = ("steps", "pending", "project_dir", "distro", "memory_gb", "watchdog", "doctor")
RESULTS = ("done", "skipped", "waiting", "failed")
MACHINE = (
    "windows", "wsl", "distro", "wsl2", "linux_user", "wslconfig", "wsl_conf", "company_ca",
    "packages", "gh_cli", "nodejs", "podman", "restart",
)  # fmt: skip
PROJECT = (
    "git_config", "claude_code", "clone", "worktrees", "kit_tools", "trust", "plugin",
    "playwright", "podman_check", "playwright_libs", "terminal",
)  # fmt: skip
SIGN_INS = ("github_signin", "claude_signin")
STEP_IDS = MACHINE + SIGN_INS + PROJECT + ("watchdog", "watchdog_back")
WATCHDOGS = {
    "wsl": "the WSL task",
    "windows": "the Windows task",
    "both": "both tasks are on; run /agk:wsl again to disable one",
    "none": "none",
}
ORIGIN = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$")
ADR_FILE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIREMENT = "REQ-001"  # protected paths change only with an ADR (every install's list)


class Refusal(Exception):
    pass


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def repo_of(root: Path) -> str:
    match = ORIGIN.search(git(root, "remote", "get-url", "origin"))
    if not match:
        raise Refusal("the remote origin is not a GitHub repository (path class: the target root)")
    return match.group(1)


def read_toml(text: str) -> dict | None:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None


def local_toml(root: Path) -> str:
    try:
        return (root / "agk.toml").read_text(encoding="utf-8")
    except OSError:
        raise Refusal("agk.toml cannot be read (path class: agk.toml)") from None


def default_branch(config: dict | None) -> str:
    value = (config or {}).get("default_branch")
    return value if isinstance(value, str) and value else "main"


def default_toml(repo: str, branch: str) -> str | None:
    """The default branch's `agk.toml`, by one GET through `gh`; None when it cannot be read."""
    exe = shutil.which("gh")
    if exe is None:
        return None
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [exe, "api", "-H", "Accept: application/vnd.github.raw",
         f"repos/{repo}/contents/agk.toml?ref={branch}"],
        capture_output=True, text=True, encoding="utf-8",
    )  # fmt: skip
    return done.stdout if done.returncode == 0 else None


def flow(config: dict | None) -> dict:
    table = (config or {}).get("flow")
    return table if isinstance(table, dict) else {}


def adapter_kind(config: dict | None) -> str:
    """`wsl`, `windows`, `unset`, `other`, or `unknown` when the file was not read."""
    if config is None:
        return "unknown"
    value = flow(config).get("launch_adapter")
    if not isinstance(value, str) or not value.strip():
        return "unset"
    return next((k for k, v in ADAPTERS.items() if v == value.strip()), "other")


def load_state(path: str | None) -> dict | None:
    if path is None:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise Refusal("the state file cannot be read (option --state)") from None
    return data if isinstance(data, dict) else None


def results(state: dict | None) -> dict[str, str]:
    steps = (state or {}).get("steps") or []
    return {s.get("step"): s.get("result") for s in steps if isinstance(s, dict)}


def word(found: dict[str, str], step: str) -> str:
    value = found.get(step)
    return "done" if value in ("done", "skipped") else value or "not read"


def all_done(found: dict[str, str], steps: tuple[str, ...]) -> bool:
    return bool(found) and all(word(found, s) == "done" for s in steps if s in found)


def facts(root: Path) -> tuple[str, str, str, bool]:
    """(repository, default branch, the adapter on it, auto_start on the default branch)."""
    repo = repo_of(root)
    here = read_toml(local_toml(root))
    branch = default_branch(here)
    text = default_toml(repo, branch)
    config = read_toml(text) if text is not None else None
    auto = flow(config if config is not None else here).get("auto_start") is True
    return repo, branch, adapter_kind(config), auto


def plan(root: Path, state: dict | None, back: bool) -> list[str]:
    """Brief #1376 answer 1: what `/agk:wsl` will do, in five lines or fewer."""
    repo, branch, kind, auto = facts(root)
    found = results(state)
    never = "you review and merge it, the kit never merges"
    if back:
        lines = [
            f"adapter: already the Windows adapter on {branch}"
            if kind == "windows"
            else f"pull request: sets launch_adapter to the Windows adapter with its ADR; {never}"
        ]
        if not auto:
            lines.append("watchdog: none (auto_start is off, so no conductor runs here)")
        elif kind == "windows":
            lines.append("watchdog: the Windows task re-enabled, the WSL task disabled (never deleted)")
        else:
            lines.append("watchdog: the Windows task is re-enabled after that pull request merges")
        lines.append("clone: the clone inside WSL stays; nothing is deleted")
        return lines
    distro = (state or {}).get("distro") or "Ubuntu-24.04"
    memory = (state or {}).get("memory_gb")
    sized = f"{memory} GB" if memory else "the machine's memory less 5 GB"
    lines = [
        "machine: already set up"
        if all_done(found, MACHINE)
        else f"machine: WSL 2 with {distro}, {sized} for WSL (.wslconfig, a backup kept), then git, "
        "Python, the GitHub CLI, Node.js and Podman inside it",
        "sign-ins: done"
        if all_done(found, SIGN_INS) and all(s in found for s in SIGN_INS)
        else "sign-ins: GitHub and Claude, each the normal sign-in in your browser",
        f"project: {repo} cloned inside WSL with its worktrees, the plugin, Playwright and the "
        "doctor" + (" (already done)" if all_done(found, PROJECT) else ""),
    ]
    if kind == "wsl":
        lines.append(f"adapter: already the WSL adapter on {branch}")
    else:
        lines.append(f"pull request: sets launch_adapter to the WSL adapter with its ADR; {never}")
    if not auto:
        lines.append("watchdog: none (auto_start is off, so no conductor runs here)")
    elif kind == "wsl":
        lines.append("watchdog: the WSL task on, the Windows task disabled (never deleted)")
    else:
        lines.append("watchdog: moved on the next /agk:wsl after that pull request merges")
    return lines


def status(root: Path, state: dict | None) -> list[str]:
    """Brief #1376 answer 4: one plain line per part."""
    _repo, branch, kind, _auto = facts(root)
    found = results(state)
    if state is None:
        lines = [f"{part}: not read (run /agk:wsl status)" for part in ("wsl", "sign-ins", "clone")]
    else:
        memory = state.get("memory_gb")
        lines = [
            f"wsl: {state.get('distro') or 'not read'} {word(found, 'wsl2')}, "
            f"{memory if memory else '?'} GB for WSL",
            f"sign-ins: GitHub {word(found, 'github_signin')}, Claude {word(found, 'claude_signin')}",
            f"clone: {state.get('project_dir') or 'not read'} {word(found, 'clone')}, "
            f"worktrees {word(found, 'worktrees')}",
        ]
    adapter = {
        "unknown": "adapter: not read from the default branch",
        "unset": f"adapter: unset on {branch}",
        "other": f"adapter: another command on {branch}",
    }.get(kind, f"adapter: the {NAMES.get(kind, kind)} adapter on {branch}")
    lines.append(adapter)
    if state is None:
        lines += [f"{part}: not read" for part in ("watchdog", "podman", "playwright", "doctor")]
        return lines
    lines += [
        f"watchdog: {WATCHDOGS.get(str(state.get('watchdog')), 'not read')}",
        f"podman: {word(found, 'podman')}, rootless check {word(found, 'podman_check')}",
        f"playwright: {word(found, 'playwright')}, libraries {word(found, 'playwright_libs')}",
        f"doctor: {state.get('doctor') or 'not read'}",
    ]
    return lines


def flow_bounds(lines: list[str]) -> tuple[int, int] | None:
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "[flow]"), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), None)
    return start, len(lines) if end is None else end


def set_adapter(text: str, value: str) -> str:
    """The text with `launch_adapter` of the `[flow]` table set to `value`; the rest unchanged."""
    lines = text.splitlines(keepends=True)
    line = f'launch_adapter = "{value}"\n'
    bounds = flow_bounds(lines)
    if bounds is None:
        return text + ("" if text.endswith("\n") or not text else "\n") + "\n[flow]\n" + line
    start, end = bounds
    for i in range(start + 1, end):
        if re.match(r"\s*launch_adapter\s*=", lines[i]):
            lines[i] = line
            return "".join(lines)
    last = max((i for i in range(start, end) if lines[i].strip()), default=start)
    if not lines[last].endswith("\n"):
        lines[last] += "\n"
    lines.insert(last + 1, line)
    return "".join(lines)


def next_adr(root: Path, slug: str) -> tuple[int, Path]:
    folder = root / "docs" / "adr"
    numbers = [int(m.group(1)) for p in folder.glob("*.md") if (m := ADR_FILE.match(p.name))]
    number = max(numbers, default=0) + 1
    if number > 9999:
        raise Refusal("no ADR number is left (path class docs/adr/)")
    return number, folder / f"{number:04d}-{slug}.md"


def adr_text(number: int, to: str, today: str) -> str:
    where = "in WSL 2" if to == "wsl" else "on Windows again"
    why = (
        "The person ran `/agk:wsl`: the sessions of this machine now run inside WSL 2, on the "
        "Linux disk, where the Windows-only failures (console encoding, CRLF line endings, "
        "PowerShell lines) do not arise."
        if to == "wsl"
        else "The person ran `/agk:wsl back`: the sessions of this machine run on Windows again."
    )
    return "\n".join(
        [
            f"# ADR-{number:04d}: The workforce runs {where}",
            "",
            "- Status: Proposed",
            f"- Date: {today}",
            "- Deciders: maintainers",
            "- Related: none",
            f"- Requirements: {REQUIREMENT}",
            "",
            "Protected classes: `agk.toml`",
            "",
            "## Context",
            "",
            f"{why} `launch_adapter` is read from `agk.toml` in the checkout and on the default "
            "branch alike, so the change comes by pull request with this ADR.",
            "",
            "## Decision",
            "",
            f'Set `launch_adapter = "{ADAPTERS[to]}"` in the `[flow]` table of `agk.toml`, the '
            f"kit's {NAMES[to]} adapter. Nothing else changes.",
            "",
            "## Consequences",
            "",
            f"- The conductor and the watchdog start sessions through the {NAMES[to]} adapter.",
            "- After the merge, `/agk:wsl` moves the watchdog task; the other task is disabled, "
            "never deleted.",
            "",
            "## Residual",
            "",
            f"- {today}: none; the maintainers review the change before the merge.",
            "",
        ]
    )


def body_path(root: Path) -> Path:
    found = git(root, "rev-parse", "--absolute-git-dir")
    folder = (Path(found) if found else root / ".git") / "agk"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "pr-body-wsl.md"


def make_pr(root: Path, to: str, brief: str | None, today: str) -> list[str]:
    """Brief #1376 answer 3: the adapter change, the project's ADR and the body; nothing committed."""
    text = local_toml(root)
    if adapter_kind(read_toml(text)) == to:
        raise Refusal(f"launch_adapter is already the {NAMES[to]} adapter; nothing written {SETTING}")
    slug = "the-workforce-runs-in-wsl-2" if to == "wsl" else "the-workforce-runs-on-windows-again"
    number, adr = next_adr(root, slug)
    adr.parent.mkdir(parents=True, exist_ok=True)
    (root / "agk.toml").write_text(set_adapter(text, ADAPTERS[to]), encoding="utf-8")
    adr.write_text(adr_text(number, to, today), encoding="utf-8")
    where = "into WSL 2" if to == "wsl" else "back to Windows"
    lines = [f"Brief: {brief}"] if brief and brief.startswith("#") else []
    lines += [
        f"Advances: {REQUIREMENT}",
        f"Summary: Moves this machine's AI workforce {where}.",
        f"Build-state row: {today} {REQUIREMENT} unchanged, launch_adapter set to the kit's "
        f"{NAMES[to]} adapter",
        f"Decisions taken: ADR-{number:04d} (Proposed) names the protected class `agk.toml`",
        "Questions: none",
        f"Verified: `python3 scripts/agk/prepush.py --record` in the {NAMES[to]} checkout",
    ]
    body = "\n".join(lines) + "\n"
    path = body_path(root)
    path.write_text(body, encoding="utf-8")
    rel = adr.relative_to(root).as_posix()
    return [
        "changed: agk.toml (launch_adapter in the flow table)",
        f"adr: wrote {rel} (ADR-{number:04d}, Proposed)",
        f"commit: agk: the workforce runs {'in WSL 2' if to == 'wsl' else 'on Windows again'}",
        f"body: {path}",
        "",
        body.rstrip("\n"),
    ]


def open_pr(root: Path, body: str, branch: str, title: str) -> list[str]:
    """Brief #1376 answer 3: one REST POST of a draft pull request; never a merge."""
    repo = repo_of(root)
    base = default_branch(read_toml(local_toml(root)))
    exe = shutil.which("gh")
    if exe is None:
        raise Refusal("gh is not installed (path class: the person's tools)")
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [exe, "api", "-X", "POST", f"repos/{repo}/pulls", "-f", f"title={title}",
         "-f", f"head={branch}", "-f", f"base={base}", "-F", "draft=true", "-F", f"body=@{body}"],
        capture_output=True, text=True, encoding="utf-8",
    )  # fmt: skip
    if done.returncode != 0:
        raise Refusal("the pull request was not opened; gh refused it (path class: the remote)")
    try:
        url = json.loads(done.stdout).get("html_url", "")
    except ValueError:
        url = ""
    return [f"opened: {url}".rstrip(), "the pull request waits for review; the kit never merges it"]


def options(args: list[str], flags: set[str], switches: set[str]) -> dict | None:
    found: dict = {}
    i = 0
    while i < len(args):
        if args[i] in switches:
            found[args[i]] = True
            i += 1
        elif args[i] in flags and i + 1 < len(args):
            found[args[i]] = args[i + 1]
            i += 2
        else:
            return None
    return found


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    command, rest = (args[0], args[1:]) if args else ("", [])
    spec = {
        "plan": ({"--state", "--root"}, {"--back"}),
        "status": ({"--state", "--root"}, set()),
        "pr": ({"--to", "--brief", "--date", "--root"}, set()),
        "open": ({"--body", "--branch", "--title", "--root"}, set()),
    }
    if command not in spec:
        print(USAGE, file=sys.stderr)
        return 2
    opts = options(rest, *spec[command])
    if opts is None:
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(opts.get("--root", ".")).resolve()
    try:
        if command == "plan":
            out = plan(root, load_state(opts.get("--state")), bool(opts.get("--back")))
        elif command == "status":
            out = status(root, load_state(opts.get("--state")))
        elif command == "pr":
            to = opts.get("--to")
            today = opts.get("--date") or datetime.now(UTC).date().isoformat()
            if to not in ADAPTERS or not DATE_RE.match(today):
                print(USAGE, file=sys.stderr)
                return 2
            brief = opts.get("--brief")
            if brief is not None and not re.fullmatch(r"none|#?\d+", brief):
                print(USAGE, file=sys.stderr)
                return 2
            brief = None if brief in (None, "none") else f"#{brief.lstrip('#')}"
            out = make_pr(root, to, brief, today)
        else:
            if "--body" not in opts or "--branch" not in opts:
                print(USAGE, file=sys.stderr)
                return 2
            title = opts.get("--title") or "The AI workforce of this machine runs in WSL 2"
            out = open_pr(root, opts["--body"], opts["--branch"], title)
    except Refusal as exc:
        print(f"wsl: {exc}")
        return 1
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
