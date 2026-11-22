# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The one resolver of the kit's scripts (SPEC-0071 rules 2 and 3, brief #1453, ADR-0611).

`python3 kit_root.py` prints the folder of the kit's scripts for the project of the working
directory (its git top level): the plugin's `scripts/agk/` in a clean project (`[kit] layout =
"plugin"` in `agk.toml`), else the project's own `scripts/agk/`. `--form` prints the command prefix
the prompts name as `<kit>`: `scripts/agk`, or `"${CLAUDE_PLUGIN_ROOT}/scripts/agk"`, or with that
variable unset the plugin's folder itself, quoted. `governance` runs the gate: `make -f agk.mk
agk-governance` in an installed project, as today, and in a clean one the checks of
`governance_map.CHECKS` from the plugin, in order, against the project's root, stopping at the
first that fails with its exit code. It never writes into the plugin's folder.

The plugin root is `CLAUDE_PLUGIN_ROOT` `(verify: the variable is set for every session, hook and
headless job the plugin serves)`, else the plugin this file sits in; either must hold
`.claude-plugin/plugin.json` and this script, and differ from the project. Otherwise, or with
another `layout` in a readable `[kit]` table, it refuses with one line naming the setting
(exit 1). An `agk.toml` that cannot be read keeps the installed layout, as before. Standard
library; no network.

`pin_refusal(root, plugin)` is the start check of SPEC-0071 rule 6 (brief #1455, ADR-0613): in a
clean project `[kit] plugin_version` must be set, equal `version` (Q-S0071-7) and equal the
`version` in `plugin`'s `.claude-plugin/plugin.json`; else it returns one line naming
`plugin_version`, never a value, and with no plugin also the install command `INSTALL`. `main`
runs it after finding the plugin, and `common` on import, so every kit script stops, exit 1,
before any work.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

HERE = Path(__file__).resolve().parent
INSTALLED_FORM = "scripts/agk"
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"  # the plugin root as a command names it (brief #1696)
PLUGIN_FORM = f'"{PLUGIN_ROOT}/scripts/agk"'
MAKE_GATE = ["make", "-f", "agk.mk", "agk-governance"]
LAYOUTS = ("installed", "plugin")
USAGE = "usage: kit_root.py [--form | governance]"
PIN = "plugin_version"
# The one install command a teammate without the plugin is told (Q-S0071-4), from
# docs/guides/getting-started.md (verify: the install command for a private source).
INSTALL = "claude plugin install agk@agk"


class Refused(Exception):
    """A refusal that names the setting, never its value (exit 1)."""


def project_root(cwd: Path | None = None) -> Path:
    here = Path.cwd() if cwd is None else cwd
    try:
        out = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "rev-parse", "--show-toplevel"],
            cwd=here,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return here.resolve()
    top = out.stdout.strip()
    return Path(top).resolve() if out.returncode == 0 and top else here.resolve()


def layout(root: Path) -> str:
    path = root / "agk.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return "installed"  # an unreadable agk.toml keeps today's path (verdict item 3)
    kit = data.get("kit", {})
    if not isinstance(kit, dict):
        return "installed"
    value = kit.get("layout", "installed")
    if value not in LAYOUTS:
        raise Refused("kit_root: [kit] layout is neither installed nor plugin (setting: layout)")
    return value


def _toml(root: Path) -> dict:
    try:
        return tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}


def plugin_version(candidate: Path) -> str | None:
    """The `version` of `candidate`'s `.claude-plugin/plugin.json`, None when it has none."""
    try:
        data = json.loads((candidate / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    value = data.get("version") if isinstance(data, dict) else None
    return value if isinstance(value, str) and value else None


def pin_refusal(root: Path, plugin: Path | None) -> str | None:
    """None outside a clean project or when `plugin` is the pinned version; else the one refusal
    line (SPEC-0071 rule 6). It names the setting, never the pin or the plugin's version."""
    data = _toml(root)
    kit = data.get("kit")
    if not isinstance(kit, dict) or kit.get("layout") != "plugin":
        return None
    pin = kit.get(PIN)
    if not isinstance(pin, str) or not pin:
        return f"agk: this clean project pins no plugin version (setting: {PIN})"
    if data.get("version") != pin:
        return f"agk: the pinned plugin version is not the project's version (setting: {PIN})"
    found = None
    if plugin is not None and plugin.resolve() != root.resolve():
        found = plugin_version(plugin)
    if found is None:
        return f"agk: no AGK plugin runs this clean project; install it: {INSTALL} (setting: {PIN})"
    if found != pin:
        return f"agk: the running AGK plugin is not the pinned version (setting: {PIN})"
    return None


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
    """The prompts' `<kit>`: the variable's form only when the variable names the plugin found,
    else that plugin's folder, quoted (verdict item 1)."""
    if layout(root) == "installed":
        return INSTALLED_FORM
    found = plugin_root(root, env)  # a clean project with no plugin learns it at once
    named = (os.environ if env is None else env).get("CLAUDE_PLUGIN_ROOT", "")
    if named and Path(named).resolve() == found:
        return PLUGIN_FORM
    return f'"{found / "scripts" / "agk"}"'


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


def utf8_output() -> None:
    """`common.utf8_output` (brief #1233, ADR-0524), kept here: a stub plugin holds this resolver
    alone, so it runs copied without `common` (brief #1488). Reconfigures stdout and stderr to
    UTF-8 when they are text streams in another encoding."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        encoding = str(getattr(stream, "encoding", "") or "").lower().replace("_", "-")
        if reconfigure is None or encoding in ("utf-8", "utf8"):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def main(argv: list[str]) -> int:
    utf8_output()
    if len(argv) > 1 or (argv and argv[0] not in ("--form", "governance")):
        print(USAGE, file=sys.stderr)
        return 2
    root = project_root()
    try:
        if layout(root) == "plugin":
            try:
                found: Path | None = plugin_root(root)
            except Refused:
                found = None  # no plugin: the pin's line names the install command (rule 10)
            line = pin_refusal(root, found)
            if line:
                raise Refused(line)
        if argv == ["--form"]:
            print(form(root))
        elif argv == ["governance"]:
            if layout(root) == "installed":
                return subprocess.run(MAKE_GATE, cwd=root).returncode  # nosec B603 - fixed argv
            return run_checks(root, kit_dir(root))
        else:
            print(kit_dir(root))
    except Refused as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
