# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""/agk:setup's helper: read, size and print (build (a), SPEC-0065 rules 2, 3, 5, 6, 12; ADR-0618),
ask and propose the project settings (build (b), rules 4 and 9; ADR-0619).

    python3 setup.py plan|status|ask|settings|install|ci|wsl|back [--json] [--builders N]
                     [--answer ID=CHOICE ...] [--yes] [--date YYYY-MM-DD] [--machine FILE]
                     [--github FILE] [--root DIR]

Run from the plugin root, never installed into a project. It reads the machine (OS, memory,
cores, disk, administrator right, WSL, the tools and their versions, winget's policy, a proxy,
the clone's remote) and the repository (`execution`, `review_mode`, `[flow]`, `[capacity]`,
`[autopilot]`, `config/reviewers.yaml`, `[team] members`; the conductor's lease and the running
builders through `conductor.py lease --show` and one `session.py plan --json`; a live steward from
the steward's own cache, no call). It asks nothing. `plan` prints the plan (eight lines or fewer)
and the table; `status` the table only. Each check row is `skipped` when it is already met and
`waiting` when it is not: this build installs nothing and writes no file. The proof rows (the
doctor, one small kit test, one container start when the project uses containers, and the dry plan)
are the last steps, after the person's yes: `status` runs them; `plan` lists them as not yet run and
runs none. `--json` prints `steps` (`step`, `result`, `note`), `pending`, `roles`, `roles_why` and
`builders`. `roles` (build (h), rule 14; ADR-0625) are this machine's, from `review_mode`, the
signed-in login (one `gh api user`, compared and never printed) against `verdict_authors` and
`spec_approvers`, the lease and the live steward; `--roles A,B` lowers them, never raises them.
`restart` (rule 15) restarts exactly those roles after `--yes`: the conductor by one
`conductor.py watchdog`, the builders by `/agk:launch`'s line, the steward by its open command.
`status` adds the team as the repository records it (`--json`: `team`), read-only.
`--builders N` lowers the figure; above the cap it is refused. A remote's or a proxy's
credentials are never read back. `--machine` and `--github` take a saved read (the tests'
doubles). `ask` prints at most five plain questions, each only when the machine and the project
leave it unset, with a recommendation (`--json`: `questions`); `--answer` gives the person's
choices back, and `plan` then names the settings in its last line. `settings --yes` writes the
settings the project does not already hold to `agk.toml` with the project's next ADR on a new
branch, and commits, pushes and merges nothing; all equal, or "for me only", writes nothing.
`ci` (build (f), rule 10; ADR-0623) is CI mode's form, for `execution = "hosted"` only: it installs
nothing and checks the repository with `gh api -X GET` calls only (Actions, the kit's workflows, a
ruleset or branch rule, the merge secret's presence with `auto_merge = true`, never its value),
one `missing:` line per missing item naming its setting (`--json`: `missing`).
`wsl` (build (d), rules 7 and 17; ADR-0621) is the WSL path on the Windows host, with WSL 2 chosen:
it runs `/agk:wsl`'s `wsl_setup.ps1 -Status -Json` and `wsl.py plan`, and after the yes one
`wsl_setup.ps1 -Json` pass and `wsl.py status`, both from this plugin and unchanged; the pass
carries `-InstallWatchdog` only when `wsl.py plan` says the WSL task goes on (that script then
hands the scheduler to `autopilot.py on` inside WSL when `[autopilot]` is set), never in personal
mode.
`back` (build (g), rule 13; ADR-0624) undoes what this command added on this machine, as kept in
`<git dir>/agk/setup.json`: with `--yes` it deletes each recorded scheduler task by its name and
prepares the reverse of each proposed setting the default branch still holds, on a new branch with
the project's next ADR; it uninstalls nothing, deletes no file and commits or pushes nothing.
`install` (rule 7) installs, after `--yes`, each tool missing or below the one `MINIMUM` table:
native Windows through winget (build (c), ADR-0620); Linux and cloud virtual machines (build (e),
ADR-0622) through apt or dnf, with Node.js, gitleaks and Claude Code by `setup_linux.sh`'s steps;
on macOS it prints one line and changes nothing.
Exit 0, 1 on a refusal, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import common  # noqa: E402
import merge_cleared  # noqa: E402
import reviewers  # noqa: E402
import session_plan  # noqa: E402
import wsl  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[2]
GIB = 1024**3
MINIMUM = {  # rule 7's one table, read by every platform script and the tests (ADR-0620, verify)
    "python": "3.11", "git": "2.43", "gh": "2.45", "claude": "2.0", "node": "20",
    "podman": "4.9", "docker": None, "pwsh": "7.6", "wt": "1.23", "gitleaks": "8.30.1",
}  # fmt: skip
WINGET = {  # build (c): each tool's winget package, in the order installed (verify)
    "python": "Python.Python.3.13", "git": "Git.Git", "gh": "GitHub.cli",
    "node": "OpenJS.NodeJS.LTS", "pwsh": "Microsoft.PowerShell", "wt": "Microsoft.WindowsTerminal",
    "gitleaks": "Gitleaks.Gitleaks", "podman": "RedHat.Podman",
}  # fmt: skip
CLAUDE_INSTALL = [  # Claude Code by its own installer (verify: the Windows installer command)
    "powershell", "-NoProfile", "-Command", "irm https://claude.ai/install.ps1 | iex",
]  # fmt: skip
LINUX_PACKAGES = {  # build (e): each tool's distribution package, per package manager (verify)
    "apt": {"git": "git", "gh": "gh", "podman": "podman"},
    "dnf": {"git": "git", "gh": "gh", "podman": "podman"},
}  # fmt: skip
LINUX_INSTALL = {"apt": ["apt-get", "install", "-y", "-q"], "dnf": ["dnf", "install", "-y", "-q"]}
LINUX_REFRESH = {"apt": ["apt-get", "update", "-q"], "dnf": ["dnf", "makecache", "-q"]}
NODE_SETUP = {  # Node.js by wsl_setup.ps1's path: NodeSource's script, then its package (verify)
    "apt": "https://deb.nodesource.com/setup_22.x", "dnf": "https://rpm.nodesource.com/setup_22.x",
}  # fmt: skip
CLAUDE_LINUX = "https://claude.ai/install.sh"  # Claude Code's own installer (wsl_setup.ps1's)
SETUP_SH = Path(__file__).resolve().parent / "setup_linux.sh"
MAC_LINE = (
    "stop: macOS is not covered by /agk:setup yet (setting: the platform); nothing was changed"
)
MACHINE_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
WINGET_FLAGS = ["--exact", "--source", "winget", "--accept-package-agreements",
                "--accept-source-agreements", "--disable-interactivity", "--silent"]  # fmt: skip
CHECKED = ("python", "git", "gh", "claude", "node")
PROOF = ("doctor", "kit_test", "container", "dry_plan")
RESULTS = ("done", "skipped", "waiting", "failed")
NOT_YET = "runs after your yes, and in /agk:setup status"  # rules 5 and 12: never in `plan`
MAX_BUILDERS = 3  # the default of `[flow] max_builders`, as `session.py` reads it
DEFAULT_RESERVE = 0.25
BROWSER_FILES = ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs")
SMALL_IMAGE = "hello-world"  # (verify) the image of rule 12's container start
WINGET_POLICY = r"SOFTWARE\Policies\Microsoft\Windows\AppInstaller"
VERSION = re.compile(r"(\d+(?:\.\d+)+)")
NUMBER = re.compile(r"\d+(?:\.\d+)*")  # a version as the table and a read hold it: "20", "2.43.0"
ANSWERS = {  # rule 4's five questions and their choices, in the order asked
    "where": ("hosted", "local", "personal"), "team": ("solo", "team"),
    "autopilot": ("off", "assist", "on"), "engine": ("podman", "docker"),
    "windows": ("wsl", "native"),
}  # fmt: skip
WHERE = {"hosted": "on GitHub's machines", "local": "on this machine", "personal": "for me only"}
BRANCH = "agk/setup-settings"
BACK_BRANCH = "agk/setup-back"
RECORD = ("agk", "setup.json")  # <git dir>/agk/setup.json: what this command added (rule 13)
WSL_TASKS = {False: "AGK conductor watchdog (WSL)", True: "agk-autopilot (WSL)"}  # the WSL script's
KEPT = "back uninstalled nothing, removed no worktree and deleted no file"
NAMES_PLACEHOLDER = (
    "\n# The model names (/agk:setup's placeholder): name each tier's model, then remove the #"
    " signs."
    '\n# [models.names]\n# strongest = "<your strongest model>"\n# mid = "<your mid model>"\n'
)


def run_cmd(args: list[str], cwd: Path) -> int:
    """One proof command's exit code; the tests replace it."""
    try:
        proc = subprocess.run(  # nosec B603 - fixed argument lists only, no shell
            args, cwd=cwd, capture_output=True, timeout=600
        )
        return proc.returncode
    except (OSError, subprocess.SubprocessError):
        return 127


def run_out(args: list[str], cwd: Path) -> tuple[int, str]:
    """A command's exit code and output, for the WSL path's kit scripts; the tests replace it."""
    try:
        proc = subprocess.run(  # nosec B603 - fixed argument lists only, no shell
            args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=3600
        )
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return proc.returncode, proc.stdout or ""


def capture(args: list[str], cwd: Path | None = None) -> str | None:
    try:
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=120
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def remote_name(url: str | None) -> str | None:
    """`owner/name` of a GitHub remote; whatever stands before the host is never kept."""
    found = wsl.ORIGIN.search((url or "").strip())
    return found[1] if found else None


def proxy_state(env) -> str:
    """`configured` or `none`: the proxy's address may hold a credential and is never shown."""
    names = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")
    return "configured" if any(env.get(n) for n in names) else "none"


def tool_version(name: str) -> str | None:
    if name == "python":
        return platform.python_version()
    if name == "wt":  # `wt` opens a window: presence only (verify)
        return "present" if shutil.which("wt") else None
    if not shutil.which(name):
        return None
    found = VERSION.search(capture([name, "--version"]) or "")
    return found[1] if found else "present"


def winget_state() -> str:
    if not shutil.which("winget"):
        return "absent"
    try:  # (verify) the App Installer policy key that turns winget off
        reg = vars(importlib.import_module("winreg"))  # winreg exists on Windows only
        key = reg["OpenKey"](reg["HKEY_LOCAL_MACHINE"], WINGET_POLICY)
        if reg["QueryValueEx"](key, "EnableAppInstaller")[0] == 0:
            return "refused by policy"
    except (ImportError, OSError, KeyError):
        pass
    return "allowed"


def is_admin() -> bool:
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0
    try:
        import ctypes

        return bool(vars(ctypes)["windll"].shell32.IsUserAnAdmin())  # windll on Windows only
    except (AttributeError, KeyError, OSError):
        return False


def sudo_ready() -> bool:
    """sudo present and usable here without a prompt (`sudo -n true`): with no terminal, or an
    account sudo refuses, a later install would fail; `sudo -v` in a terminal makes it ready."""
    return bool(shutil.which("sudo")) and capture(["sudo", "-n", "true"]) is not None


def wsl_state() -> str:
    if sys.platform.startswith("linux"):
        try:
            text = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
        except OSError:
            return "absent"
        return (
            "inside WSL 2" if "wsl2" in text else "inside WSL" if "microsoft" in text else "absent"
        )
    return "present" if shutil.which("wsl") else "absent"


def read_machine(root: Path) -> dict:
    """Rule 3: what the machine tells; a figure that cannot be read is None (unknown)."""
    avail, total = common.available_memory(), session_plan.total_memory()
    disk = session_plan.disk_figures(root)
    return {
        "os": platform.system() or "unknown", "os_version": platform.release() or "unknown",
        "wsl": wsl_state(), "memory_total_gb": total / GIB if total else None,
        "memory_available_gb": avail / GIB if avail else None, "cores": os.cpu_count(),
        "disk_free_gb": disk[0] / GIB if disk else None, "admin": is_admin(),
        "tools": {n: tool_version(n) for n in MINIMUM}, "winget": winget_state(),
        "package_manager": next((k for k, v in LINUX_INSTALL.items() if shutil.which(v[0])),
                                "absent"), "sudo": sudo_ready(),
        "proxy": proxy_state(os.environ),
        "remote": remote_name(capture(["git", "-C", str(root), "remote", "get-url", "origin"])),
    }  # fmt: skip


def read_github(root: Path) -> dict:
    """The lease and the running builders: one `lease --show` and one plan pass, GET only."""
    py, scripts = sys.executable, PLUGIN / "scripts" / "agk"
    lease = capture([py, str(scripts / "conductor.py"), "lease", "--show"], root)
    plan = capture([py, str(scripts / "session.py"), "plan", "--json"], root)
    try:
        found = json.loads(plan) if plan else {}
        running, waiting = found["capacity"]["running"], found["capacity"]["waiting_for_verdict"]
        sessions = [{"session": r["session"], "brief": r["brief"]} for r in found["running"]]
    except (ValueError, KeyError, TypeError):
        running, waiting, sessions = None, None, []
    return {
        "lease": (lease or "").strip().removeprefix("lease: ") or None,
        "running": running,
        "sessions": sessions,
        "waiting": waiting,
        "login": common.signed_in_login(root),  # compared by login_state, never printed
    }


def live_steward(root: Path) -> str | None:
    """A live steward from the steward's own cache (no call), None when it holds none."""
    try:
        import steward

        found = steward.live_start(
            steward.load_cache(root).get("comments", []), "", datetime.now(UTC)
        )
    except (ImportError, OSError, ValueError, KeyError, AttributeError):
        return None
    return found


def read_repository(root: Path, github: dict) -> dict:
    """Rule 3's repository read: the settings of `agk.toml`, the reviewers and the team."""
    try:
        toml = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
        kit = True
    except (OSError, tomllib.TOMLDecodeError):
        toml, kit = {}, False
    flow, cap = toml.get("flow", {}), toml.get("capacity", {})

    def least(key):
        values = [t[key] for t in (flow, cap) if isinstance(t.get(key), int | float)]
        return min(values) if values else None

    heavy = any((root / n).is_file() for n in BROWSER_FILES) or bool(wsl.project_engines(root))
    return {
        "kit": kit, "execution": toml.get("execution", "hosted"),
        "review_mode": toml.get("review_mode"), "autopilot": "autopilot" in toml,
        "profile": cap.get("profile"), "max_builders": least("max_builders") or MAX_BUILDERS,
        "builder_memory_gb": least("builder_memory_gb"), "heavy": heavy,
        "engines": sorted(wsl.project_engines(root)),
        "verdict_authors": len(reviewers.verdict_authors(root)),
        "spec_approvers": len(reviewers.spec_approvers(root)),
        "members": len(toml.get("team", {}).get("members", [])),
        "lease": github.get("lease"), "running": github.get("running"),
        "steward": github.get("steward"), "sessions": github.get("sessions") or [],
        "waiting": github.get("waiting"), "login": login_state(root, github.get("login")),
    }  # fmt: skip


def login_state(root: Path, login) -> str:
    """Rule 14: the signed-in login compared with the reviewer lists, never kept or printed:
    `author` (in `verdict_authors`), `reviewer` (a spec approver only), `other` or `unknown`."""
    if not isinstance(login, str) or not login:
        return "unknown"
    key = str(Path(root).resolve())  # a saved login stands in for the one `gh api user` read
    common.SIGNED_IN[key] = login.lower() if common.GH_LOGIN.fullmatch(login) else None
    if common.conductor_refusal(root) is None:  # the conductor's own check (#1449, ADR-0607)
        return "author"
    return "reviewer" if login.lstrip("@").lower() in reviewers.spec_approvers(root) else "other"


ROLES = ("steward", "conductor", "builders")
WAITS = "the conductor waits for a verdict author's machine"
LISTS = "(setting: verdict_authors and spec_approvers in config/reviewers.yaml)"
STEWARD_OPEN = "claude --agent steward"


def machine_roles(repo: dict, answers: dict) -> tuple[list[str], str]:
    """Rule 14: this machine's roles and the one line that says why; rule 16: none for me only
    or on GitHub's machines. A lease that is not read `free` starts no conductor here."""
    where = answers.get("where") or ("hosted" if repo["execution"] == "hosted" else "local")
    if where != "local":
        return [], ("for me only: no roles, nothing is posted" if where == "personal"
                    else "the AI work runs on GitHub's machines: no role here")  # fmt: skip
    team = f"the team's builders stay within max_builders {repo['max_builders']}"
    team += f" ({repo['running'] or 0} live)"
    if (repo["review_mode"] or answers.get("team") or "team") == "solo":  # the answer only if unset
        return list(ROLES), "one person: this machine runs every role"
    state, lease = repo["login"], repo["lease"] or ""
    said = {"author": "this login is a verdict author", "reviewer": "this login is a listed "
            "reviewer, not a verdict author", "other": "this login is not a listed reviewer",
            "unknown": "this login is unknown"}[state]  # fmt: skip
    steward = state in ("author", "reviewer") and not repo["steward"]
    why: str | None
    if lease.startswith("held by"):
        why = "another machine holds the conductor's lease"
    elif lease != "free":
        why = "the conductor's lease cannot be read as free"
    else:
        why = None if state == "author" else WAITS
    if state in ("author", "reviewer") and repo["steward"]:
        said += ", and a steward is already live"
    roles = [r for r, ok in zip(ROLES, (steward, why is None, True), strict=True) if ok]
    return roles, "; ".join(x for x in (said, why, team) if x)


def restart(root: Path, roles: list[str], yes: bool) -> tuple[int, dict, list[str]]:
    """Rule 15: restart exactly the roles of rule 14: the conductor through the watchdog's start,
    the builders through /agk:launch's plan and yes, the steward by the command that opens it."""
    if not roles:
        return 0, {"steps": [], "pending": []}, ["nothing to restart: this machine runs no role"]
    if not yes:
        named = ", ".join(roles)
        return 1, {"steps": [], "pending": []}, [
            f"restart would start: {named}; nothing started before the person's yes "
            "(setting: --yes)"]  # fmt: skip
    steps, lines = [], []
    for role in roles:
        if role == "conductor":
            watchdog = [sys.executable, str(PLUGIN / "scripts" / "agk" / "conductor.py"),
                        "watchdog", "--conductor-only"]  # fmt: skip  (no builder pass: rule 15)
            code, out = run_out(watchdog, root)
            said = out.strip().splitlines()
            lines += said
            started = [x for x in said if x.startswith("watchdog: started ")]
            last = said[-1] if said else "the watchdog printed nothing"
            result = "failed" if code else "done" if started else "waiting"
            steps.append(row(role, result, f"conductor.py watchdog: exit {code}: {last}" if code
                             else started[0] if started else last))  # fmt: skip
        elif role == "steward":
            steps.append(row(role, "waiting", f"open it in a new terminal: {STEWARD_OPEN}"))
        else:
            steps.append(
                row(role, "waiting", "run /agk:launch: it shows its plan and asks your yes")
            )
    pending = [r["step"] for r in steps if r["result"] != "done"]
    return 0, {"steps": steps, "pending": pending}, lines


def team_view(repo: dict, roles: list[str]) -> dict:
    """Rule 15: the team as the repository records it, read-only; logins are never shown."""
    return {"lease": repo["lease"] or "unknown", "steward": repo["steward"],
            "builders": repo["sessions"], "members": repo["members"],
            "waiting": repo["waiting"], "here": roles}  # fmt: skip


def team_lines(team: dict) -> list[str]:
    built = ", ".join(f"{b['session']} #{b['brief']}" for b in team["builders"]) or "none running"
    waiting = team["waiting"]
    waits = "unknown" if waiting is None else (
        f"{waiting} pull request{'' if waiting == 1 else 's'} wait{'s' if waiting == 1 else ''} "
        "for a verdict")  # fmt: skip
    one = "member" if team["members"] == 1 else "members"
    return [
        "Team (read only, nothing posted):",
        f"  conductor lease: {team['lease']}",
        f"  steward: {team['steward'] + ' live' if team['steward'] else 'none live seen'}",
        f"  builders: {built}",
        f"  {team['members']} {one} listed; on the owner: {waits}",
        f"  this machine: {', '.join(team['here']) or 'no role'}",
    ]


def size(available, total, cores, per_gb, reserve, max_builders, live=0) -> dict:
    """Rule 6: (available less the reserve) / per builder, rounded down, then the caps; the
    first of memory, cores, max_builders and team wins a tie."""
    if available is None:
        limits = [("memory", 1, "memory unknown: 1 builder")]
    else:
        kept = reserve * (total if total else available)
        got = max(0, int((available - kept) // per_gb))
        note = (
            f"memory: {available:.0f} GB available less a {reserve:.0%} reserve, {per_gb:g} GB each"
        )
        limits = [("memory", got, note)]
    if cores:
        limits.append(("cores", cores // 2, f"cores: one builder per two of {cores}"))
    limits.append(("max_builders", max_builders, f"max_builders is {max_builders}"))
    if live:
        team = max(0, max_builders - live)
        limits.append(("team", team, f"team: max_builders {max_builders} less {live} live"))
    name, figure, reason = min(limits, key=lambda item: item[1])
    return {"figure": figure, "limit": name, "reason": reason, "per_builder_gb": per_gb}


def older(found: str, least: str | None) -> bool:
    if least is None or not NUMBER.fullmatch(found):
        return False
    return tuple(map(int, found.split("."))) < tuple(map(int, least.split(".")))


def either(step: str, met, note: str, missing: str) -> dict:
    return row(step, "skipped", note) if met else row(step, "waiting", missing)


def check_rows(machine: dict, repo: dict) -> list[dict]:
    rows, tools = [], machine.get("tools", {})
    for name in CHECKED:
        found, least = tools.get(name), MINIMUM[name]
        want = f"{least} or newer" if least else "any version"
        if found and older(found, least):
            rows.append(row(name, "waiting", f"{found} is older than {least}: update {name}"))
        else:
            rows.append(
                either(name, found, f"{found} ({want})", f"missing: install {name} ({want})")
            )
    have = [f"{e} {tools[e]}" for e in ("podman", "docker") if tools.get(e)]
    if repo["engines"]:
        rows.append(either("engine", have, (have or [""])[0], "missing: a container engine"))
    remote = machine.get("remote")
    rows.append(either("clone", remote, str(remote), "this folder is not a GitHub clone"))
    no_kit = "no agk.toml: /agk:init or /agk:adopt sets it up"
    return [*rows, either("kit", repo["kit"], "agk.toml present", no_kit)]


def proof_rows(root: Path, machine: dict, repo: dict, run: bool = True) -> list[dict]:
    """Rule 12: the doctor, one small kit test, one container start, the dry plan; with RUN
    false (`plan`, before the yes of rule 5) each is listed as not yet run and none runs."""
    if not run:
        return [row(name, "skipped", NOT_YET) for name in PROOF]
    py, scripts = sys.executable, str(PLUGIN / "scripts" / "agk")

    def proof(name: str, args: list[str], what: str, skip: str | None = None) -> dict:
        if skip:
            return row(name, "skipped", skip)
        code = run_cmd(args, root)
        return row(name, "failed" if code else "done", f"{what}: exit {code}" if code else what)

    test = root / "tests" / "kit" / "test_doctor.py"
    engine = next((e for e in ("podman", "docker") if machine["tools"].get(e)), "")
    no_engine = "the project uses no containers" if not repo["engines"] else "no engine yet"
    pytest = [py, "-m", "pytest", "-q", "-c", "tests/kit/pytest.ini", str(test)]
    return [
        proof("doctor", [py, f"{scripts}/doctor.py"], "doctor.py"),
        proof("kit_test", pytest, "test_doctor.py", None if test.is_file() else "the doctor alone"),
        proof("container", [engine, "run", "--rm", SMALL_IMAGE], f"{engine} run",
              None if repo["engines"] and engine else no_engine),
        proof("dry_plan", [py, f"{scripts}/session.py", "plan"], "session.py plan",
              None if repo["kit"] else "no agk.toml in this folder"),
    ]  # fmt: skip


def row(step: str, result: str, note: str) -> dict:
    return {"step": step, "result": result, "note": note}


def gb(value) -> str:
    return "unknown" if value is None else f"{value:.0f} GB"


def plan_lines(machine: dict, repo: dict, builders: dict, rows: list[dict], roles) -> list[str]:
    """Rule 5: one plan of at most eight lines; nothing is asked."""
    m, tools = machine, machine.get("tools", {})
    total, avail = m.get("memory_total_gb"), m.get("memory_available_gb")
    memory = "memory unknown" if total is None and avail is None else f"{gb(total)} memory"
    memory += f" ({gb(avail)} available)" if avail is not None else ""
    have = ", ".join(f"{n} {tools[n]}" for n in (*CHECKED, "podman", "docker") if tools.get(n))
    missing = ", ".join(r["step"] for r in rows if r["result"] == "waiting") or "nothing"
    admin, kit = "yes" if m.get("admin") else "no", "installed" if repo["kit"] else "not installed"
    running = "unknown" if repo["running"] is None else repo["running"]
    one = "builder" if builders["figure"] == 1 else "builders"
    return [
        "Plan:",
        f"  This machine: {m['os']} {m['os_version']}, {memory}, {m.get('cores') or 'unknown'}"
        f" cores, {gb(m.get('disk_free_gb'))} free disk, administrator {admin}.",
        f"  Also: WSL {m.get('wsl')}, winget {m.get('winget')}, proxy {m.get('proxy')}.",
        f"  Tools: {have or 'none'}; to install: {missing}.",
        f"  Project: {m.get('remote') or 'not a GitHub clone'}; kit {kit}, execution "
        f"{repo['execution']}, review mode {repo['review_mode'] or 'unset'}.",
        f"  Team: {repo['verdict_authors']} verdict authors, {repo['members']} members; lease "
        f"{repo['lease'] or 'unknown'}; running builders {running}; live steward "
        f"{repo['steward'] or 'none seen'}.",
        f"  Builders: {builders['figure']} {one} of {builders['per_builder_gb']:g} GB "
        f"(limit {builders['limit']}; {builders['reason']}).",
        f"  Roles here: {', '.join(roles[0]) or 'none'} ({roles[1]}). This run changes "
        "nothing; /agk:setup status runs the proofs.",
    ]


def table_lines(rows: list[dict]) -> list[str]:
    return [f"{r['step']:<10} {r['result']:<8} {r['note']}" for r in rows]


def config_of(root: Path) -> tuple[str | None, dict]:
    try:
        text = (root / "agk.toml").read_text(encoding="utf-8")
        return text, tomllib.loads(text)
    except (OSError, tomllib.TOMLDecodeError):
        return None, {}


def questions(machine: dict, repo: dict, config: dict, builders: dict) -> list[dict]:
    """Rule 4: at most five, each only when unset, in plain words with a recommendation."""
    found: list[dict] = []

    def ask(qid: str, text: str, pick: str, reason: str) -> None:
        said = WHERE.get(pick, pick) if qid == "where" else LABELS.get(pick, pick)
        text = f"{text}? I recommend {said}: {reason}."
        found.append({"id": qid, "text": text, "choices": list(ANSWERS[qid]), "recommend": pick})

    room, known = builders["figure"], machine.get("memory_available_gb") is not None
    if "execution" not in config:
        why = f"it has room for {room} AI workers at once" if room else "its memory is too small"
        ask("where", "Where should the AI work run: on GitHub's machines, on this machine, or for "
            "me only, nothing in the project", "local" if known and room else "hosted",
            why if known else "this machine's memory could not be read")  # fmt: skip
    if repo["review_mode"] is None:
        many = repo["verdict_authors"] > 1 or repo["members"] > 0
        ask("team", "Will one person approve the AI's work, or a team", "team" if many else "solo",
            "the project lists several people" if many else "no one else is listed yet",
        )  # fmt: skip
    if "autopilot" not in config:
        ask("autopilot", "Should the AI start its work by itself: off, assist (it asks you before "
            "each new task) or on", "assist", "you keep the say before new work starts",
        )  # fmt: skip
    tools = machine.get("tools", {})
    if repo["engines"] and not (tools.get("podman") or tools.get("docker")):
        ask("engine", "The project uses containers and this machine has no container engine: "
            "Podman or Docker", "podman", "it runs without a background service")  # fmt: skip
    if machine.get("os") == "Windows" and wsl.adapter_kind(config) == "unset":
        can = machine.get("wsl") == "present" or machine.get("admin")
        ask("windows", "Should the AI work run in Windows itself or in WSL 2, a Linux system "
            "inside Windows", "wsl" if can else "native",
            "it avoids failures that happen only on Windows" if can
            else "turning WSL 2 on needs an administrator, and this account is not one",
        )  # fmt: skip
    return found


LABELS = {"solo": "one person", "team": "a team", "podman": "Podman", "docker": "Docker",
          "wsl": "WSL 2", "native": "Windows itself"}  # fmt: skip


def proposals(config: dict, answers: dict, builders: dict, machine: dict) -> list[tuple]:
    """Rule 9: each `(table, key, value)` the project does not already hold."""
    out: list[tuple] = []
    flow, cap = config.get("flow", {}), config.get("capacity", {})

    def want(table: str | None, key: str, value) -> None:
        if (config.get(table, {}) if table else config).get(key) != value:
            out.append((table, key, value))

    where = answers.get("where")
    if where == "personal":
        return out  # rule 16: personal mode proposes nothing to the project
    if where in ("hosted", "local") and config.get("execution") not in ("hybrid", "pool"):
        want(None, "execution", where)
    if (where or config.get("execution", "hosted")) == "hosted":
        return out  # rule 16: CI mode changes `execution` only, nothing sized from this machine
    if "team" in answers:
        want(None, "review_mode", answers["team"])
    if builders["figure"] > 1:  # more than one builder under one login (brief #1461 answer 1)
        want(None, "pr_mode", "flow")
    solo = answers.get("team", config.get("review_mode")) == "solo"
    if solo and builders["figure"] >= 1 and "max_builders" not in flow | cap:
        want("flow", "max_builders", builders["figure"])
    if "builder_memory_gb" not in flow | cap:
        want("flow", "builder_memory_gb", builders["per_builder_gb"])
    pick = {"wsl": "wsl", "native": "windows"}.get(answers.get("windows", ""))
    local = (where or config.get("execution")) == "local"
    if pick is None and machine.get("os") == "Linux" and local and not flow.get("launch_adapter"):
        pick = "wsl"  # the background adapter (rule 10)
    if pick:
        want("flow", "launch_adapter", wsl.ADAPTERS[pick])
    if "autopilot" in answers and "autopilot" not in config:
        want("autopilot", "mode", answers["autopilot"])
    return out


def shown(item: tuple) -> str:
    table, key, value = item
    said = "removed" if value is None else f"= {json.dumps(value)}"
    return f"{f'[{table}] ' if table else ''}{key} {said}"


def set_key(text: str, table: str | None, key: str, value) -> str:
    """TEXT with KEY of TABLE (None: the top level) set to VALUE (None: removed); the rest
    unchanged."""
    lines, line = text.splitlines(keepends=True), f"{key} = {json.dumps(value)}\n"
    heads = [i for i, ln in enumerate(lines) if re.match(r"\s*\[", ln)]
    if table is None:
        start, end = -1, heads[0] if heads else len(lines)
    else:
        found = next((i for i in heads if lines[i].split("#")[0].strip() == f"[{table}]"), None)
        if found is None and value is None:
            return text
        if found is None:
            lead = "" if not text or text.endswith("\n") else "\n"
            return f"{text}{lead}\n[{table}]\n{line}"
        start = found
        end = next((i for i in heads if i > start), len(lines))
    for i in range(start + 1, end):
        if re.match(rf"\s*{key}\s*=", lines[i]):
            lines[i : i + 1] = [] if value is None else [line]
            rest = [ln for ln in lines[start + 1 : end - 1] if ln.split("#")[0].strip()]
            if value is None and table is not None and not rest:
                del lines[start]  # a table left with no key goes too: `[autopilot]` alone is set
            return "".join(lines)
    if value is None:
        return text
    at = end if table is None else max(i + 1 for i in range(start, end) if lines[i].strip())
    while table is None and at > 0 and lines[at - 1].lstrip().startswith("#"):
        at -= 1  # a top-level key goes above the comment that opens the first table
    if at and not lines[at - 1].endswith("\n"):
        lines[at - 1] += "\n"
    lines.insert(at, line)
    return "".join(lines)


def project_adr(number: int, items: list[tuple], today: str, back: bool = False) -> str:
    listed = [f"- `{shown(i)}`" for i in items]
    title = "reversed by /agk:setup back" if back else "chosen in /agk:setup"
    why = ("The person ran `/agk:setup back`, which reverses the settings `/agk:setup` proposed "
           "and the default branch still holds; ") if back else (
           "The person ran `/agk:setup` and answered its questions; ")  # fmt: skip
    return "\n".join([
        f"# ADR-{number:04d}: The project settings {title}", "",
        "- Status: Proposed", f"- Date: {today}", "- Deciders: maintainers", "- Related: none",
        f"- Requirements: {wsl.REQUIREMENT}", "", "Protected classes: `agk.toml`", "",
        "## Context", "",
        f"{why}these settings live in `agk.toml`, a protected path, so they come by pull request "
        "with this ADR.", "",
        "## Decision", "", "Set in `agk.toml`, and nothing else:", "", *listed, "",
        "## Consequences", "",
        "- The sessions of this project read the new values after the merge.", "",
        "## Residual", "",
        f"- {today}: none; the maintainers review the change before the merge.",
        "",
    ])  # fmt: skip


def write_settings(root: Path, find, today: str, back: bool = False) -> list[str]:
    """Rule 9: one change and its ADR on a new branch from the default branch; FIND gives the
    settings the default branch's `agk.toml` lacks (BACK: rule 13's reverse, each recorded on the
    proposal). The text is built and parsed first."""
    load_record(root)  # an unreadable record is refused before any branch is made
    ref = f"origin/{wsl.default_branch(config_of(root)[1])}"
    unread = wsl.Refusal("the default branch's agk.toml cannot be read (path class: agk.toml)")
    if not wsl.git(root, "rev-parse", "--verify", "--quiet", f"{ref}:agk.toml"):
        raise unread
    text = wsl.git(root, "show", f"{ref}:agk.toml")
    text += "\n" if text else ""
    try:
        base = tomllib.loads(text)
        items = find(base)
    except tomllib.TOMLDecodeError:
        raise unread from None
    if not items and back:
        return ["nothing to reverse: the default branch holds none of the settings setup proposed"]
    if not items:
        return ["every setting already matches: nothing written and no pull request is needed"]
    for item in items:
        text = set_key(text, *item)
    try:
        names = tomllib.loads(text).get("models", {}).get("names")
    except tomllib.TOMLDecodeError:
        bad = "the change would not parse; nothing written (path class: agk.toml)"
        raise wsl.Refusal(bad) from None
    text += "" if back or names or "# [models.names]" in text else NAMES_PLACEHOLDER
    if wsl.git(root, "status", "--porcelain", "--untracked-files=no"):
        raise wsl.Refusal("uncommitted changes in this folder (path class: the working tree)")
    branch = f"{BACK_BRANCH if back else BRANCH}-{today}"
    if wsl.git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        raise wsl.Refusal("that branch already exists (path class: the settings branch)")
    wsl.git(root, "checkout", "-q", "-b", branch, ref)
    if wsl.git(root, "branch", "--show-current") != branch:
        raise wsl.Refusal("the new branch was not made (path class: the settings branch)")
    what = "reversed by setup back" if back else "chosen in setup"
    number, adr = wsl.next_adr(root, f"the-project-settings-{what.replace(' ', '-')}")
    (root / "agk.toml").write_text(text, encoding="utf-8")
    adr.write_text(project_adr(number, items, today, back), encoding="utf-8")
    if not back:
        remember(root, "settings", [{"table": t, "key": k, "value": v, "before": lookup(base, t, k)}
                                    for t, k, v in items])  # fmt: skip
    req, rel = wsl.REQUIREMENT, adr.relative_to(root).as_posix()
    summary = "Returns" if back else "Sets"
    body = "\n".join([
        f"Advances: {req}", f"Summary: {summary} the project's AI workforce settings {what}.",
        f"Build-state row: {today} {req} unchanged, the settings {what}",
        f"Decisions taken: ADR-{number:04d} (Proposed) names the protected class `agk.toml`",
        "Questions: none",
        "Verified: `python3 scripts/agk/prepush.py --record` in this checkout", "",
    ])  # fmt: skip
    path = wsl.body_path(root).with_name("pr-body-setup.md")
    path.write_text(body, encoding="utf-8")
    message, opener = f"agk: the project settings {what}", wsl.__file__
    return [
        f"changed: agk.toml ({', '.join(shown(i) for i in items)})",
        f"adr: wrote {rel} (ADR-{number:04d}, Proposed)", f"branch: {branch}", f"body: {path}", "",
        "then you run, in this folder (setup commits, pushes and merges nothing):",
        f'  git add agk.toml {rel} && git commit -m "{message}"',
        f"  python3 scripts/agk/prepush.py --record --body {path}",
        f"  git push -u origin {branch}",
        f'  python3 {Path(opener).resolve().as_posix()} open --body {path} --branch {branch} '
        f'--title "The project settings {what}"',
    ]  # fmt: skip


def lookup(config: dict, table: str | None, key: str):
    found = config.get(table, {}) if table else config
    return found.get(key) if isinstance(found, dict) else None


def record_path(root: Path) -> Path | None:
    found = wsl.git(root, "rev-parse", "--absolute-git-dir")
    return Path(found).joinpath(*RECORD) if found else None


def load_record(root: Path) -> dict:
    """Rule 13's record; a folder that is not a clone has none. Unreadable: refused."""
    path = record_path(root)
    if path is None or not path.is_file():
        return {}
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = None
    tasks = found.get("tasks", []) if isinstance(found, dict) else None
    settings = found.get("settings", []) if isinstance(found, dict) else None
    if not (isinstance(tasks, list) and all(isinstance(t, str) for t in tasks)
            and isinstance(settings, list) and all(isinstance(s, dict) for s in settings)):
        raise wsl.Refusal("the record cannot be read; nothing done (setting: setup.json)")
    return found


def remember(root: Path, key: str, items: list) -> None:
    """Add ITEMS to the record's KEY, none twice; a folder that is not a clone keeps nothing."""
    if record_path(root) is None or not items:
        return
    record = load_record(root)
    record[key] = record.get(key, []) + [i for i in items if i not in record.get(key, [])]
    save_record(root, record)


def save_record(root: Path, record: dict) -> None:
    path = record_path(root)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def reverse(recorded: list[dict]):
    """Rule 13: each recorded setting the default branch still holds goes back to its before."""

    def find(base: dict) -> list[tuple]:
        out: list[tuple] = []
        for s in recorded:
            item = (s.get("table"), s.get("key"), s.get("before"))
            if isinstance(item[1], str) and lookup(base, item[0], item[1]) == s.get("value"):
                out += [] if item in out else [item]
        return out

    return find


def back(root: Path, today: str, yes: bool) -> tuple[int, dict, list[str]]:
    """Build (g), rule 13: remove the recorded scheduler tasks by name, then prepare the reverse
    settings change; nothing uninstalled, no worktree removed, no file deleted."""
    record = load_record(root)
    tasks, settings = record.get("tasks", []), record.get("settings", [])
    table: dict = {"steps": [], "pending": [], "roles": [], "builders": None}
    if not tasks and not settings:
        return 0, table, ["nothing to undo: /agk:setup recorded nothing on this machine"]
    if not yes:
        table["steps"] = [
            row("tasks", "waiting", f"would remove {', '.join(tasks)}") if tasks
            else row("tasks", "skipped", "no scheduler task to remove"),
            row("settings", "waiting", "would prepare the reverse of the settings setup proposed")
            if settings else row("settings", "skipped", "no setting to reverse"),
        ]  # fmt: skip
        table["pending"] = [r["step"] for r in table["steps"] if r["result"] == "waiting"]
        return 1, table, ["stop: nothing changed: back runs only after your yes (setting: --yes)"]
    kept = [n for n in tasks if run_cmd(["schtasks", "/Delete", "/TN", n, "/F"], root) != 0]
    gone = [n for n in tasks if n not in kept]
    if tasks:
        save_record(root, record | {"tasks": kept})
    if kept:
        again = f"not removed: {', '.join(kept)}; run /agk:setup back again"
        steps = [row("tasks", "failed", again)]
    elif gone:
        steps = [row("tasks", "done", f"removed: {', '.join(gone)}")]
    else:
        steps = [row("tasks", "skipped", "setup added no scheduler task on this machine")]
    lines: list[str] = []
    branch = f"{BACK_BRANCH}-{today}"
    if not settings:
        steps.append(row("settings", "skipped", "setup proposed no setting from this machine"))
    elif wsl.git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        steps.append(row("settings", "skipped", f"the reverse change is already on {branch}"))
    else:
        try:
            lines = write_settings(root, reverse(settings), today, back=True)
            done = "skipped" if lines[0].startswith("nothing to reverse") else "done"
            steps.append(row("settings", done, lines[0]))
        except wsl.Refusal as exc:
            steps.append(row("settings", "failed", str(exc)))
    pending = [r["step"] for r in steps if r["result"] in ("waiting", "failed")]
    return (1 if pending else 0), table | {"steps": steps, "pending": pending}, lines + [KEPT]


def tool_of(args: list[str]) -> str | None:
    """The tool an install call is for: its winget package, or Claude Code's own installer."""
    if args == CLAUDE_INSTALL:
        return "claude"
    ids = {v: k for k, v in WINGET.items()}
    return ids.get(args[3]) if args[:3] == ["winget", "install", "--id"] else None


def needs(found: str | None, least: str | None) -> bool:
    """To install: missing, older than the floor, or with a floor and no version read."""
    return not found or older(found, least) or bool(least and not NUMBER.fullmatch(found))


def install_order(tools: dict, engines: bool) -> list[str]:
    """Rule 7: the tools to install on native Windows, missing or older than the minimum."""
    names = [n for n in WINGET if n != "podman"]
    if engines and not tools.get("docker"):
        names.append("podman")
    return [n for n in [*names, "claude"] if needs(tools.get(n), MINIMUM[n])]


def fresh_path() -> str:
    """The machine's and the user's PATH as an install leaves them; this process keeps its own."""
    try:  # winreg exists on Windows only
        reg = vars(importlib.import_module("winreg"))
        keys = [(reg["HKEY_LOCAL_MACHINE"], MACHINE_PATH),
                (reg["HKEY_CURRENT_USER"], "Environment")]  # fmt: skip
        parts = [reg["QueryValueEx"](reg["OpenKey"](h, k), "Path")[0] for h, k in keys]
    except (ImportError, OSError, KeyError):
        return os.environ.get("PATH", "")
    return os.pathsep.join(os.path.expandvars(p) for p in parts)


def installed_version(name: str) -> str | None:
    """Read after an install, or when a version is unread: winget's own list for its packages,
    else the tool on the PATH read again (an install does not refresh this process's PATH)."""
    if name not in WINGET:
        where = shutil.which(name, path=fresh_path())
        out = capture([where, "--version"]) if where else None
        version = VERSION.search(out or "")
        return version[1] if version else ("present" if where else None)
    out = capture(["winget", "list", "--id", WINGET[name], *WINGET_FLAGS[:3]]) or ""
    line = next((ln for ln in out.splitlines() if WINGET[name] in ln), "")
    found = VERSION.search(line.split(WINGET[name], 1)[-1])
    return found[1] if found else None


def stop_line(machine: dict, todo: list[str], root: Path) -> str | None:
    """Rule 7: what IT must allow, read before the first install; None when nothing stops it."""
    hand = f"or install {', '.join(todo)} by hand, then run /agk:setup again"
    if not [t for t in todo if t in WINGET]:
        return None
    winget = machine.get("winget")
    if winget != "allowed":
        why = "winget is missing" if winget == "absent" else "winget is refused by policy"
        return f"stop: {why}: allow winget (the App Installer), {hand}"
    if not machine.get("admin"):
        return f"stop: this account is not an administrator: ask IT for that right, {hand}"
    first = WINGET[next(t for t in todo if t in WINGET)]
    if run_cmd(["winget", "show", "--id", first, *WINGET_FLAGS[:3]], root):
        return f"stop: the test download was refused: allow downloads from winget's source, {hand}"
    return None


def windows_install(root: Path, machine: dict, repo: dict, yes: bool) -> tuple[int, dict]:
    """Rule 7's native Windows path: checked before, a stop before the first install, one winget
    install per missing tool, checked after; a failure stops the run with the tool as it was."""
    tools, engines = machine.get("tools", {}), bool(repo["engines"])
    names = [n for n in WINGET if n != "podman"] + (["podman"] if engines else []) + ["claude"]
    tools = {
        n: v if not v or NUMBER.fullmatch(v) or n not in WINGET else installed_version(n) or v
        for n, v in tools.items()
    }  # a tool read only as present: winget's list names it
    todo = install_order(tools, engines)
    rows, stop = first_rows(names, tools, todo), None
    if machine.get("os") != "Windows":
        stop = "stop: this form is the native Windows path only (setting: the platform)"
    elif todo and not yes:
        stop = "stop: nothing installed: installs run only after the person's yes (setting: --yes)"
    elif todo:
        stop = stop_line(machine, todo, root)
    for name in [] if stop else todo:
        least = MINIMUM[name]
        args = CLAUDE_INSTALL if name == "claude" else ["winget", "install", "--id", WINGET[name],
                                                         *WINGET_FLAGS]  # fmt: skip
        code = run_cmd(args, root)
        found = None if code else installed_version(name)
        if found and not older(found, least):
            rows[name] = row(name, "done", f"{found} (at least {least or 'any version'})")
            continue
        why = f"exit {code}" if code else f"reads {found or 'nothing'} after, below {least}"
        rows[name] = row(name, "failed", f"{why}: left as it was (winget's own transaction)")
        stop = f"stop: {name} did not install and nothing after it ran; then run /agk:setup again"
        break
    return last_table(names, rows, stop)


def first_rows(names: list[str], tools: dict, todo: list[str]) -> dict:
    """Each tool's row before any install: `skipped` with what is there, or `waiting`."""
    have = {n: tools.get(n) or (f"docker {tools.get('docker')}" if n == "podman" else "present")
            for n in names}  # fmt: skip
    rows = {n: row(n, "skipped", f"{have[n]} (at least {MINIMUM[n] or 'any version'})")
            for n in names if n not in todo}  # fmt: skip
    return rows | {n: row(n, "waiting", f"to install, at least {MINIMUM[n] or 'any version'}")
                   for n in todo}  # fmt: skip


def last_table(names: list[str], rows: dict, stop: str | None) -> tuple[int, dict]:
    steps = [rows[n] for n in names]
    pending = [r["step"] for r in steps if r["result"] in ("waiting", "failed")]
    return (1 if stop else 0), {"steps": steps, "pending": pending, "stop": stop}


def unsudo(args: list[str]) -> list[str]:
    return args[1:] if args[:1] == ["sudo"] else args


def is_refresh(args: list[str]) -> bool:
    """The package lists' refresh: the test download before the first Linux install."""
    return unsudo(args) in LINUX_REFRESH.values()


def linux_tool_of(args: list[str]) -> str | None:
    """The tool a Linux install call is for: its distribution package, or a setup_linux.sh step."""
    rest = unsudo(args)
    if rest[:2] == ["bash", str(SETUP_SH)] and len(rest) > 2:
        return rest[2]
    for manager, verb in LINUX_INSTALL.items():
        if rest[:-1] == verb and rest:
            return {v: k for k, v in LINUX_PACKAGES[manager].items()}.get(rest[-1])
    return None


def linux_version(name: str) -> str | None:
    """Read after an install: the PATH with the installers' own folders (this process keeps its
    PATH); gitleaks tells its version by `gitleaks version`."""
    extra = [os.environ.get("PATH", ""), str(Path.home() / ".local" / "bin"), "/usr/local/bin"]
    where = shutil.which(name, path=os.pathsep.join(extra))
    if not where:
        return None
    found = VERSION.search(capture([where, "version" if name == "gitleaks" else "--version"]) or "")
    return found[1] if found else "present"


def linux_install(root: Path, machine: dict, repo: dict, yes: bool) -> tuple[int, dict]:
    """Rule 7's Linux and cloud path (build (e)): the distribution's packages through apt or dnf,
    Node.js, gitleaks and Claude Code by setup_linux.sh's steps (wsl_setup.ps1's path), checked
    before and after; a stop before the first install; a failure stops the run there."""
    tools, engines = machine.get("tools", {}), bool(repo["engines"])
    engine = ["podman"] if engines and not tools.get("docker") else []
    names = ["python", "git", "gh", *engine, "node", "gitleaks", "claude"]
    todo = [n for n in names[1:] if needs(tools.get(n), MINIMUM[n])]
    rows, stop = first_rows(names, tools, todo), None
    manager = str(machine.get("package_manager") or "absent")
    sudo = [] if machine.get("admin") else ["sudo"]
    hand = f"or install {', '.join(todo)} by hand, then run /agk:setup again"
    as_root = [n for n in todo if n != "claude"]  # Claude Code installs as the user
    packaged = [n for n in as_root if n != "gitleaks"]  # the package manager's own steps
    if todo and not yes:
        stop = "stop: nothing installed: installs run only after the person's yes (setting: --yes)"
    elif packaged and manager not in LINUX_INSTALL:
        stop = f"stop: no package manager this command knows (apt or dnf) is here: {hand}"
    elif as_root and sudo and not machine.get("sudo"):
        stop = ("stop: this account is not root and cannot use sudo here without a prompt: run "
                f"`sudo -v` in a terminal first, or ask for sudo, {hand}")  # fmt: skip
    elif packaged and run_cmd([*sudo, *LINUX_REFRESH[manager]], root):
        stop = ("stop: the test download was refused: allow the distribution's package mirrors "
                f"(a company proxy or certificate is the usual cause), {hand}")  # fmt: skip
    steps: dict[str, list[str]] = {
        "node": [manager, NODE_SETUP.get(manager, "")], "claude": [CLAUDE_LINUX],
        "gitleaks": [str(MINIMUM["gitleaks"])],
    }  # fmt: skip
    for name in [] if stop else todo:
        package = LINUX_PACKAGES.get(manager, {}).get(name)
        args = ([*sudo, *LINUX_INSTALL[manager], package] if package
                else ["bash", str(SETUP_SH), name, *steps[name]])  # fmt: skip
        code = run_cmd(args, root)
        found = None if code else linux_version(name)
        if found and not older(found, MINIMUM[name]):
            rows[name] = row(name, "done", f"{found} (at least {MINIMUM[name]})")
            continue
        why = f"exit {code}" if code else f"reads {found or 'nothing'} after, below {MINIMUM[name]}"
        kept = "; NodeSource's package source it added stays" if name == "node" else ""
        note = f"{why}: left as it was (the installer's own transaction){kept}"
        rows[name] = row(name, "failed", note)
        stop = f"stop: {name} did not install and nothing after it ran; then run /agk:setup again"
        break
    return last_table(names, rows, stop)


CI_CHECKS = {  # build (f), rule 10: each repository check of CI mode and the setting it names
    "actions": "Actions permissions", "workflows": "the kit's workflows",
    "rules": "kit/templates/ruleset.json", "secrets": "auto_merge",
}  # fmt: skip


PAGE = 100  # GitHub's largest page of a listing


def gh_get(path: str):
    """One GET of the GitHub API through `gh`; None when GitHub gives this sign-in no answer."""
    out = capture(["gh", "api", "-X", "GET", path])
    try:
        return json.loads(out) if out else None
    except ValueError:
        return None


def kit_workflows() -> list[str]:
    """The kit's workflows: `kit/manifest.json`'s verbatim files under `.github/workflows/`."""
    try:
        manifest = json.loads((PLUGIN / "kit" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [f for f in manifest.get("verbatim", []) if f.startswith(".github/workflows/")]


def workflow_pages(repo: str) -> list[dict] | None:
    """Every page of the repository's workflows, 100 a page; None when a page goes unanswered."""
    found: list[dict] = []
    for page in range(1, 101):
        listed = gh_get(f"{repo}/actions/workflows?per_page={PAGE}&page={page}")
        if listed is None:
            return None
        batch = listed.get("workflows") or []
        found += batch
        if len(batch) < PAGE or len(found) >= (listed.get("total_count") or 0):
            return found
    return found


def ci_checks(remote: str, config: dict) -> list[tuple[str, bool | None, str]]:
    """Rule 10: (step, met or None when unknown, what is missing); GET only, no secret read."""
    repo = f"repos/{remote}"
    actions = gh_get(f"{repo}/actions/permissions")
    enabled = None if actions is None else actions.get("enabled") is True
    checks = [("actions", enabled, "GitHub Actions is off for this repository: turn it on")]
    listed, lacking = workflow_pages(repo), []
    if listed is not None:
        active = {w.get("path") for w in listed if w.get("state") == "active"}
        lacking = [Path(f).name for f in kit_workflows() if f not in active]
    what = f"the kit's workflows absent or disabled: {', '.join(lacking)}; run /agk:upgrade"
    checks.append(("workflows", None if listed is None else not lacking, what))
    sets, branch = gh_get(f"{repo}/rulesets"), (gh_get(repo) or {}).get("default_branch")
    shield = gh_get(f"{repo}/branches/{branch}") if branch else None
    known = [bool(sets)] if sets is not None else []
    known += [shield.get("protected") is True] if shield is not None else []
    rules = any(known) if known else None
    checks.append(("rules", rules, "no ruleset and no branch rule on the default branch"))
    flow = config.get("flow")  # a `flow` that is not a table counts as unset
    if isinstance(flow, dict) and flow.get("auto_merge") is True:
        held = gh_get(f"{repo}/environments/merge/secrets")
        met = None if held is None else bool(held.get("secrets"))  # counted, never kept
        checks.append(("secrets", met, "the merge environment holds no secret for the merger"))
    return checks


def ci_mode(root: Path, remote: str | None) -> tuple[int, dict, list[str]]:
    """Build (f): CI mode installs nothing and checks the repository, one line per missing item."""
    _, config = config_of(root)
    if not config or config.get("execution", "hosted") != "hosted":
        return 1, {}, ["refused: the repository checks are CI mode's (setting: execution)"]
    if not remote:
        return 1, {}, ["stop: this folder has no GitHub remote to check (setting: the clone)"]
    steps, missing = [], []
    for step, met, what in ci_checks(remote, config):
        if met is None:
            steps.append(row(step, "waiting", "unknown: GitHub gave this sign-in no answer"))
            continue
        steps.append(row(step, "skipped" if met else "waiting", "present" if met else what))
        missing += [] if met else [f"missing: {what} (setting: {CI_CHECKS[step]})"]
    pending = [r["step"] for r in steps if r["result"] == "waiting"]
    table = {"steps": steps, "pending": pending, "roles": [], "builders": None,
             "missing": missing}  # fmt: skip
    lines = table_lines(steps) + missing + merger_note(root, remote, config)
    return (1 if pending else 0), table, lines


def merger_note(root: Path, remote: str, config: dict) -> list[str]:
    """Brief #1554 answer 4 (ADR-0654): the doctor's `merger-variable` line, printed once in the
    merge step and never run; nothing when the merger is not installed or nothing is to change."""
    try:
        text = (root / ".github" / "workflows" / "merger.yml").read_text(encoding="utf-8")
    except OSError:
        return []
    held = gh_get(f"repos/{remote}/actions/variables/{merge_cleared.MERGER_VARIABLE}")
    value = held.get("value") if isinstance(held, dict) else None
    found = re.search(r'cron: "\*/([1-9][0-9]?) \* \* \* \*"', text)
    per_day = 1440 // int(found.group(1)) if found else None
    line = merge_cleared.merger_variable_line(config, value, per_day)
    return [f"note: {line[1]}"] if line else []


WSL_SCRIPT = PLUGIN / "scripts" / "agk" / "wsl_setup.ps1"  # /agk:wsl's, called and never copied
WSL_HELPER = PLUGIN / "scripts" / "agk" / "wsl.py"
WATCHDOG_ON = "the WSL task on"  # `wsl.py plan`'s watchdog line when the adapter is merged


def wsl_pass(root: Path, flags: list[str], state: Path) -> dict | None:
    """One `wsl_setup.ps1 ... -Json` pass, its table saved to STATE for `wsl.py`; None: no table."""
    _, out = run_out(["pwsh", "-NoProfile", "-File", str(WSL_SCRIPT), *flags, "-Json"], root)
    try:
        table = json.loads(out) if out.strip() else None
    except ValueError:
        table = None
    if not isinstance(table, dict) or not isinstance(table.get("steps"), list):
        return None
    state.write_text(json.dumps(table), encoding="utf-8")
    return table  # its exit is in its rows: a failed step is `failed`


def wsl_helper(root: Path, form: str, state: Path) -> list[str]:
    args = [sys.executable, str(WSL_HELPER), form, "--state", str(state), "--root", str(root)]
    return [ln for ln in run_out(args, root)[1].splitlines() if ln.strip()]


def wsl_steps(table: dict) -> list[dict]:
    """The script's own rows, each `step`, `result` (one of RESULTS, else failed) and `note`."""
    found = [s for s in table.get("steps", []) if isinstance(s, dict)]
    said = [(s, str(s.get("result"))) for s in found]
    return [row(str(s.get("step")), got if got in RESULTS else "failed", str(s.get("note") or ""))
            for s, got in said]  # fmt: skip


def wsl_path(root: Path, machine: dict, config: dict, answers: dict, yes: bool) -> dict:
    """Build (d): the WSL path of rule 7, `/agk:wsl` called unchanged (rule 17), then the one
    scheduler task through that script's watchdog step (brief #1463 answer 1)."""
    table: dict = {"steps": [], "pending": [], "plan": [], "status": [], "roles": [],
                   "builders": None}  # fmt: skip
    where = answers.get("where") or config.get("execution", "hosted")
    if machine.get("os") != "Windows":
        stop = "stop: the WSL path runs on the Windows host (setting: the platform)"
    elif answers.get("windows") != "wsl":
        stop = "refused: the WSL path is for WSL 2 chosen (setting: windows)"
    elif where == "hosted":
        stop = "refused: CI mode installs nothing on this machine (setting: execution)"
    else:
        stop = None
    if stop:
        return table | {"stop": stop}
    engine, personal = answers.get("engine", "podman"), where == "personal"
    with tempfile.TemporaryDirectory() as folder:
        state = Path(folder) / "wsl-state.json"
        flags = ["-Engine", engine]
        checked = wsl_pass(root, ["-Status", *flags], state)
        if checked is None:
            no = "stop: wsl_setup.ps1 gave no table: install PowerShell 7, then run /agk:setup"
            return table | {"stop": no}
        table["plan"] = wsl_helper(root, "plan", state)
        line = next((ln for ln in table["plan"] if ln.startswith("watchdog:")), "watchdog: none")
        task = WATCHDOG_ON in line and not personal
        done = checked
        if yes:
            ran = wsl_pass(root, flags + (["-InstallWatchdog"] if task else []), state)
            if ran is None:
                return table | {"stop": "stop: wsl_setup.ps1 gave no table; run /agk:setup again"}
            done, table["status"] = ran, wsl_helper(root, "status", state)
            if task and any(s.get("step") == "watchdog" and s.get("result") == "done"
                            for s in wsl_steps(ran)):  # fmt: skip
                remember(root, "tasks", [WSL_TASKS["autopilot" in config]])  # rule 13
    steps = wsl_steps(done)
    if personal:
        steps.append(row("scheduler", "skipped", "for me only: no scheduler task (personal mode)"))
    elif not task:
        steps.append(row("scheduler", "waiting", line.removeprefix("watchdog: ")))
    failed = next((r["step"] for r in steps if r["result"] == "failed"), None)
    if not yes:
        stop = "stop: nothing set up: the WSL setup runs only after your yes (setting: --yes)"
    elif failed:
        stop = f"stop: {failed} did not finish; run /agk:setup again to resume from it"
    pending = [r["step"] for r in steps if r["result"] in ("waiting", "failed")]
    return table | {"steps": steps, "pending": pending, "stop": stop}


def load(path: str | None):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def main(argv: list[str] | None = None) -> int:
    common.utf8_output()
    parser = argparse.ArgumentParser(prog="setup.py", add_help=True)
    forms = ("plan", "status", "ask", "settings", "install", "ci", "wsl", "back", "restart")
    parser.add_argument("form", choices=forms)
    for flag in ("--machine", "--github", "--root", "--date", "--roles"):
        parser.add_argument(flag)
    parser.add_argument("--builders", type=int)
    parser.add_argument("--answer", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--yes", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    answers = dict(a.split("=", 1) for a in args.answer if "=" in a)
    today = args.date or datetime.now(UTC).date().isoformat()
    bad = len(answers) != len(args.answer) or not wsl.DATE_RE.match(today)
    if bad or any(v not in ANSWERS.get(k, ()) for k, v in answers.items()):
        print("usage: --answer ID=CHOICE with an ID and a choice of setup.py ask", file=sys.stderr)
        return 2
    root = Path(args.root or ".").resolve()
    if args.form == "back":  # build (g): nothing of the machine is read
        try:
            code, undone, notes = back(root, today, args.yes)
        except wsl.Refusal as exc:
            print(f"setup: {exc}")
            return 1
        print(json.dumps(undone | {"lines": notes}, indent=2) if args.json
              else "\n".join(table_lines(undone["steps"]) + notes))  # fmt: skip
        return code
    if args.form == "ci":  # build (f): nothing of the machine but its remote is read
        saved = load(args.machine)
        remote = saved.get("remote") if saved else remote_name(
            capture(["git", "-C", str(root), "remote", "get-url", "origin"]))  # fmt: skip
        code, table, shown_lines = ci_mode(root, remote)
        print(json.dumps(table, indent=2) if args.json and table else "\n".join(shown_lines))
        return code
    machine = load(args.machine) or read_machine(root)
    github = load(args.github)
    if github is None:
        github = read_github(root) | {"steward": live_steward(root)}
    repo = read_repository(root, github)
    per = repo["builder_memory_gb"] or (4 if repo["heavy"] else 3)
    reserve = session_plan.RESERVES.get(repo["profile"], DEFAULT_RESERVE)
    live = (repo["running"] or 0) if repo["review_mode"] == "team" else 0
    builders = size(
        machine.get("memory_available_gb"), machine.get("memory_total_gb"), machine.get("cores"),
        per, reserve, repo["max_builders"], live,
    )  # fmt: skip
    if args.builders is not None:
        if not 0 <= args.builders <= builders["figure"]:
            cap = f"{builders['figure']} ({builders['limit']})"
            print(f"refused: --builders above the cap of {cap}")
            return 1
        builders |= {"figure": args.builders, "limit": "person", "reason": "lowered by the person"}
    roles = machine_roles(repo, answers)
    if args.roles is not None:  # rule 14: fewer roles, never more than the repository allows
        chosen = [r for r in ROLES if r in args.roles.split(",")]
        if set(args.roles.split(",")) - set(roles[0]) or not chosen:
            print(f"refused: --roles names a role this machine may not run here {LISTS}")
            return 1
        roles = (chosen, f"{roles[1]}; lowered by the person")
    if args.form == "restart":
        code, table, notes = restart(root, roles[0], args.yes)
        table |= {"roles": roles[0], "roles_why": roles[1], "builders": builders}
        print(json.dumps(table, indent=2) if args.json else
              "\n".join(notes + table_lines(table["steps"])))  # fmt: skip
        return code
    _, config = config_of(root)
    if args.form == "wsl":
        table = wsl_path(root, machine, config, answers, args.yes)
        lines = table["plan"] + table_lines(table["steps"]) + table["status"]
        said = "\n".join(lines + ([table["stop"]] if table["stop"] else []))
        print(json.dumps(table, indent=2) if args.json else said)
        return 1 if table["stop"] else 0
    if args.form == "install":
        if machine.get("os") == "Darwin":  # rule 7, Q-S0065-3: one line, nothing changed
            mac = {"steps": [], "pending": [], "stop": MAC_LINE}
            print(json.dumps(mac) if args.json else MAC_LINE)
            return 1
        install = linux_install if machine.get("os") == "Linux" else windows_install
        code, table = install(root, machine, repo, args.yes)
        said = "\n".join(table_lines(table["steps"]) + ([table["stop"]] if table["stop"] else []))
        print(json.dumps(table, indent=2) if args.json else said)
        return code
    if args.form == "ask":
        found = questions(machine, repo, config, builders)
        text = [f"  {n}. {q['text']}" for n, q in enumerate(found, 1)]
        none = ["No question: this machine and the project answer them all."]
        listed = "\n".join(["Questions:", *text] if text else none)
        out = {"questions": found} if args.json else listed
        print(json.dumps(out, indent=2) if args.json else out)
        return 0
    items = proposals(config, answers, builders, machine)
    if args.form == "settings":
        if not args.yes:
            print("setup: nothing written: the settings are written only after the person's yes "
                  "(setting: --yes)")  # fmt: skip
            return 1
        if answers.get("where") == "personal":
            print("for me only: nothing is proposed to the project (personal mode, no pull "
                  "request)")  # fmt: skip
            return 0
        try:
            find = lambda base: proposals(base, answers, builders, machine)  # noqa: E731
            print("\n".join(write_settings(root, find, today)))
        except wsl.Refusal as exc:
            print(f"setup: {exc}")
            return 1
        return 0
    rows = check_rows(machine, repo) + proof_rows(root, machine, repo, args.form == "status")
    pending = [r["step"] for r in rows if r["result"] == "waiting"]
    team = team_view(repo, roles[0])
    if args.json:
        table = {
            "steps": rows,
            "pending": pending,
            "roles": roles[0],
            "roles_why": roles[1],
            "builders": builders,
        } | ({"team": team} if args.form == "status" else {})
        print(json.dumps(table, indent=2))
        return 0
    lines = plan_lines(machine, repo, builders, rows, roles) if args.form == "plan" else []
    if lines and answers.get("where") == "personal":  # rule 16
        lines.append("  For the developer: for me only, nothing is proposed to the project.")
    elif lines and items:  # rule 4: the settings only in the plan's last line, for the developer
        lines.append(f"  For the developer: {'; '.join(shown(i) for i in items)}.")
    lines += [""] if lines else []
    shown_team = ["", *team_lines(team)] if args.form == "status" else []
    print("\n".join(lines + table_lines(rows) + shown_team))
    return 0


if __name__ == "__main__":
    sys.exit(main())
