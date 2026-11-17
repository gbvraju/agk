# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The one resolver of the kit's scripts (SPEC-0071 rules 2 and 3, brief #1453, ADR-0611).

`python3 kit_root.py` prints the folder of the kit's scripts for the project of the working
directory (its git top level): the plugin's `scripts/agk/` in a clean project (`[kit] layout =
"plugin"` in `agk.toml`), else the project's own `scripts/agk/`. `--form` prints the command prefix
the prompts name as `<kit>`: `scripts/agk` or `"${CLAUDE_PLUGIN_ROOT}/scripts/agk"`. `governance`
runs the gate: `make -f agk.mk agk-governance` in an installed project, as today, and in a clean
one the checks of `governance_map.CHECKS` from the plugin, in order, against the project's root,
stopping at the first that fails with its exit code. It never writes into the plugin's folder.

The plugin root is `CLAUDE_PLUGIN_ROOT` `(verify: the variable is set for every session, hook and
headless job the plugin serves)`, else the plugin this file sits in; either must hold
`.claude-plugin/plugin.json` and this script, and differ from the project. Otherwise, or with
another `layout`, it refuses with one line naming the setting, exit 1. Standard library; no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSTALLED_FORM = "scripts/agk"
PLUGIN_FORM = '"${CLAUDE_PLUGIN_ROOT}/scripts/agk"'
MAKE_GATE = ["make", "-f", "agk.mk", "agk-governance"]
LAYOUTS = ("installed", "plugin")
USAGE = "usage: kit_root.py [--form | governance]"


class Refused(Exception):
    """A refusal that names the setting, never its value (exit 1)."""


def project_root(cwd: Path | None = None) -> Path:
    here = Path.cwd() if cwd is None else cwd
    try:
        out = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True
        )
    except OSError:
        return here.resolve()
    top = out.stdout.strip()
    return Path(top).resolve() if out.returncode == 0 and top else here.resolve()


def layout(root: Path) -> str:
    path = root / "agk.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise Refused("kit_root: agk.toml cannot be read (setting: layout)") from exc
    kit = data.get("kit", {})
    value = kit.get("layout", "installed") if isinstance(kit, dict) else None
    if value not in LAYOUTS:
        raise Refused("kit_root: [kit] layout is neither installed nor plugin (setting: layout)")
    return value


def _plugin(candidate: Path, root: Path) -> bool:
    return (
        (candidate / ".claude-plugin" / "plugin.json").is_file()
        and (candidate / "scripts" / "agk" / "kit_root.py").is_file()
        and candidate.resolve() != root.resolve()
    )


def plugin_root(root: Path, env: dict | None = None) -> Path:
    named = (os.environ if env is None else env).get("CLAUDE_PLUGIN_ROOT", "")
    for candidate in ([Path(named)] if named else []) + [HERE.parent.parent]:
        if _plugin(candidate, root):
            return candidate.resolve()
    raise Refused("kit_root: no plugin root for this clean project (setting: CLAUDE_PLUGIN_ROOT)")


def kit_dir(root: Path, env: dict | None = None) -> Path:
    if layout(root) == "installed":
        return root / "scripts" / "agk"
    return plugin_root(root, env) / "scripts" / "agk"


def form(root: Path, env: dict | None = None) -> str:
    if layout(root) == "installed":
        return INSTALLED_FORM
    plugin_root(root, env)  # a clean project with no plugin learns it at once
    return PLUGIN_FORM


def gate(root: Path, env: dict | None = None) -> list[str] | None:
    """The governance command for `root`: today's make form (None when an installed project has no
    `agk.mk`), or this resolver from the plugin in a clean project."""
    if layout(root) == "installed":
        return list(MAKE_GATE) if (root / "agk.mk").is_file() else None
    return [sys.executable, str(kit_dir(root, env) / "kit_root.py"), "governance"]


def run_checks(root: Path, kit: Path) -> int:
    sys.path.insert(0, str(kit))
    import governance_map  # the plugin's own list, in the recipe's order

    for _name, command in governance_map.CHECKS:
        script, *args = command
        argv = [sys.executable, str(kit / Path(script).name), *args]
        print(" ".join(["python3", f"{PLUGIN_FORM}/{Path(script).name}", *args]), flush=True)
        code = subprocess.run(argv, cwd=root).returncode  # nosec B603 - the kit's own scripts
        if code != 0:
            return code
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 or (argv and argv[0] not in ("--form", "governance")):
        print(USAGE, file=sys.stderr)
        return 2
    root = project_root()
    try:
        if argv == ["--form"]:
            print(form(root))
        elif argv == ["governance"]:
            if layout(root) == "installed":
                return subprocess.run(MAKE_GATE, cwd=root).returncode  # nosec B603 B607 - fixed
            return run_checks(root, kit_dir(root))
        else:
            print(kit_dir(root))
    except Refused as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
