# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""/agk:setup's helper, build (a): read, size and print (SPEC-0065 rules 2, 3, 5, 6, 12; ADR-0618).

    python3 setup.py plan|status [--json] [--builders N] [--machine FILE] [--github FILE]
                                 [--root DIR]

Run from the plugin root, never installed into a project. It reads the machine (OS, memory,
cores, disk, administrator right, WSL, the tools and their versions, winget's policy, a proxy,
the clone's remote) and the repository (`execution`, `review_mode`, `[flow]`, `[capacity]`,
`[autopilot]`, `config/reviewers.yaml`, `[team] members`; the conductor's lease and the running
builders through `conductor.py lease --show` and one `session.py plan --json`; a live steward from
the steward's own cache, no call). It asks nothing. `plan` prints the plan (eight lines or fewer)
and the table; `status` the table only. Each check row is `skipped` when it is already met and
`waiting` when it is not: this build installs nothing and writes no file. The proof rows run the
doctor, one small kit test, one container start when the project uses containers, and the dry
plan. `--json` prints `steps` (`step`, `result`, `note`), `pending`, `roles` (chosen by build (h),
empty here) and `builders`. `--builders N` lowers the figure; above the cap it is refused. A
remote's or a proxy's credentials are never read back. `--machine` and `--github` take a saved
read (the tests' doubles). Exit 0, 1 on a refusal, 2 on a usage error.
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
import tomllib
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import common  # noqa: E402
import reviewers  # noqa: E402
import session_plan  # noqa: E402
import wsl  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[2]
GIB = 1024**3
MINIMUM = {  # rule 7's one table; None until build (c) records it (verify)
    "python": "3.11", "git": None, "gh": None, "claude": None, "node": "20",
    "podman": None, "docker": None, "pwsh": None,
}  # fmt: skip
CHECKED = ("python", "git", "gh", "claude", "node")
PROOF = ("doctor", "kit_test", "container", "dry_plan")
RESULTS = ("done", "skipped", "waiting", "failed")
MAX_BUILDERS = 3  # the default of `[flow] max_builders`, as `session.py` reads it
DEFAULT_RESERVE = 0.25
BROWSER_FILES = ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs")
SMALL_IMAGE = "hello-world"  # (verify) the image of rule 12's container start
WINGET_POLICY = r"SOFTWARE\Policies\Microsoft\Windows\AppInstaller"
VERSION = re.compile(r"(\d+(?:\.\d+)+)")


def run_cmd(args: list[str], cwd: Path) -> int:
    """One proof command's exit code; the tests replace it."""
    try:
        proc = subprocess.run(  # nosec B603 - fixed argument lists only, no shell
            args, cwd=cwd, capture_output=True, timeout=600
        )
        return proc.returncode
    except (OSError, subprocess.SubprocessError):
        return 127


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
        "proxy": proxy_state(os.environ),
        "remote": remote_name(capture(["git", "-C", str(root), "remote", "get-url", "origin"])),
    }  # fmt: skip


def read_github(root: Path) -> dict:
    """The lease and the running builders: one `lease --show` and one plan pass, GET only."""
    py, scripts = sys.executable, PLUGIN / "scripts" / "agk"
    lease = capture([py, str(scripts / "conductor.py"), "lease", "--show"], root)
    plan = capture([py, str(scripts / "session.py"), "plan", "--json"], root)
    try:
        running = json.loads(plan)["capacity"]["running"] if plan else None
    except (ValueError, KeyError, TypeError):
        running = None
    return {"lease": (lease or "").strip().removeprefix("lease: ") or None, "running": running}


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
        "steward": github.get("steward"),
    }  # fmt: skip


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
    if least is None or not VERSION.fullmatch(found):
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


def proof_rows(root: Path, machine: dict, repo: dict) -> list[dict]:
    """Rule 12: the doctor, one small kit test, one container start, the dry plan."""
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


def plan_lines(machine: dict, repo: dict, builders: dict, rows: list[dict]) -> list[str]:
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
        "  This run installs and changes nothing; /agk:setup status shows the table again.",
    ]


def table_lines(rows: list[dict]) -> list[str]:
    return [f"{r['step']:<10} {r['result']:<8} {r['note']}" for r in rows]


def load(path: str | None):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def main(argv: list[str] | None = None) -> int:
    common.utf8_output()
    parser = argparse.ArgumentParser(prog="setup.py", add_help=True)
    parser.add_argument("form", choices=("plan", "status"))
    for flag in ("--machine", "--github", "--root"):
        parser.add_argument(flag)
    parser.add_argument("--builders", type=int)
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    root = Path(args.root or ".").resolve()
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
    rows = check_rows(machine, repo) + proof_rows(root, machine, repo)
    pending = [r["step"] for r in rows if r["result"] == "waiting"]
    if args.json:
        table = {"steps": rows, "pending": pending, "roles": [], "builders": builders}
        print(json.dumps(table, indent=2))
        return 0
    lines = plan_lines(machine, repo, builders, rows) + [""] if args.form == "plan" else []
    print("\n".join(lines + table_lines(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
