# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `pins` step (brief #1592, ADR-0672; SPEC-0072 rule 4 as amendment 201 proposes; REQ-079).

    python3 scripts/agk/gates/pins.py [--root DIR]          # the check
    python3 scripts/agk/gates/pins.py write [--root DIR]    # the foundation's build file

The chosen option of the Accepted stack record selects `kit/templates/stacks/<stack>/` by the
`runtime` of its `stack.toml`, which names a part of that option. The check reads that stack's
build file and lock, offline, and fails on a direct dependency not pinned exactly or not in the
lock, on a missing lock, and on a part of the record whose version differs from the lock's; each
line names the rule and the component class, never a name or a version (principle 8). With no
`[delivery] work_type` or no Accepted record it prints `not run: no stack chosen`. `write` writes
the build file from the folder when the project has none (or holds the untouched file `init`
wrote, for the same name); any other build file is kept, never rewritten (adopted projects). The
lock is made by the stack's own tool on the builder's machine, never here. The runner's interface
(`RULE`, `check(root, playbook)`) is that of `scripts/agk/gates/` (brief #1586).
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import engines  # noqa: E402
from playbook_format import declaration  # noqa: E402

RULE = "SPEC-0072 rule 4: the stack's build file and lock are not pinned and in step"
STACKS = engines.TEMPLATES / "stacks"
NOT_RUN = "not run: no stack chosen"
PEP508 = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*?)\s*(;.*)?$")
EXACT_PY = re.compile(r"^==\s*([0-9][0-9A-Za-z.+!-]*)$")
EXACT_NPM = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LOCKED_PY = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")
NPM_GROUPS = ("dependencies", "devDependencies", "optionalDependencies")


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def line(rule: str, cls: str) -> str:
    return f"FAIL pins: {rule} (component class: {cls})"


def chosen(root: Path) -> tuple[dict[str, Any], Path, list[tuple[str, str, str]]] | None:
    """(stack.toml, its folder, the chosen option's parts) when a stack is chosen, else None."""
    if declaration(root)[0] is None:
        return None
    found = engines.accepted_stack(root)
    if found is None:
        return None
    _, text, letter = found
    lines = engines.section(text, "Decision") or []
    body = next(
        (m.group(2) for ln in lines if (m := engines.OPTION.match(ln)) and m.group(1) == letter), ""
    )
    parts = engines.option_parts(body) or []
    names = {p[0] for p in parts}
    for folder in sorted(p.parent for p in STACKS.glob("*/stack.toml")):
        meta = tomllib.loads((folder / "stack.toml").read_text(encoding="utf-8"))
        if meta.get("runtime") in names:
            return meta, folder, parts
    return None


def direct(meta: dict[str, Any], text: str) -> list[tuple[str, str | None]]:
    """(name, exact version or None) of each direct dependency of the build file."""
    out: list[tuple[str, str | None]] = []
    if meta["reader"] == "npm":
        data = json.loads(text)
        for group in NPM_GROUPS:
            for name, spec in (data.get(group) or {}).items():
                ok = isinstance(spec, str) and EXACT_NPM.match(spec)
                out.append((norm(name), spec if ok else None))
        return out
    project = tomllib.loads(text).get("project", {})
    specs = list(project.get("dependencies", []))
    for group in (project.get("optional-dependencies") or {}).values():
        specs += list(group)
    for spec in specs:
        m = PEP508.match(spec)
        if m:
            pin = EXACT_PY.match(m.group(3))
            out.append(
                (norm(m.group(1)), pin.group(1) if pin and "*" not in pin.group(1) else None)
            )
    return out


def locked(meta: dict[str, Any], text: str) -> dict[str, str]:
    """name -> version of each entry of the lock, line ends normalised."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if meta["reader"] == "npm":
        data = json.loads(text)
        out = {
            norm(key.rsplit("node_modules/", 1)[1]): str(v.get("version"))
            for key, v in (data.get("packages") or {}).items()
            if key.startswith("node_modules/") and isinstance(v, dict)
        }
        for name, v in (data.get("dependencies") or {}).items():  # lockfileVersion 1
            if isinstance(v, dict):
                out.setdefault(norm(name), str(v.get("version")))
        return out
    return {norm(m.group(1)): m.group(2) for ln in text.split("\n") if (m := LOCKED_PY.match(ln))}


def problems(root: Path) -> list[str] | None:
    """The failure lines, or None when no stack is chosen (the step is not run)."""
    found = chosen(Path(root))
    if found is None:
        return None
    meta, _, parts = found
    build, lock = Path(root) / meta["build_file"], Path(root) / meta["lock_file"]
    try:
        deps = direct(meta, build.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return [line(f"{RULE}: the build file is missing or unreadable", "build file")]
    try:
        have = locked(meta, lock.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [line(f"{RULE}: the lock file is missing", "lock file")]
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return [line(f"{RULE}: the lock file is unreadable", "lock file")]
    out: set[str] = set()
    for name, version in deps:
        if version is None:
            out.add(line(f"{RULE}: a direct dependency is not pinned exactly", "dependency"))
        elif name not in have:
            out.add(line(f"{RULE}: a direct dependency is not in the lock", "dependency"))
        elif have[name] != version:
            out.add(line(f"{RULE}: a direct dependency differs from the lock", "dependency"))
    for name, version, _ in parts:
        if norm(name) in have and have[norm(name)] != version:
            out.add(
                line(
                    f"{RULE}: a part of the Accepted stack record differs from the lock",
                    "stack part",
                )
            )
    return sorted(out)


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    """The runner's interface: the path classes that fail, none when the step passes."""
    found = problems(root)
    return ["build and lock files"] if found else []


def write(root: Path) -> int:
    found = chosen(root)
    if found is None:
        print(f"pins write: {NOT_RUN}")
        return 0
    meta, folder, _ = found
    from init import render, slug  # noqa: PLC0415 - the same rendering as init

    name = meta["build_file"]
    target = root / name
    variables = {"project": slug(root.resolve().name)}
    if target.exists():
        init_file = engines.TEMPLATES / name
        untouched = init_file.is_file() and target.read_text(encoding="utf-8") == render(
            init_file.read_text(encoding="utf-8"), variables, name
        )
        try:
            adopt = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8")).get("mode")
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            adopt = None
        if not untouched or adopt == "adopt":
            print(f"kept {name}")
            return 0
    target.write_text(
        render((folder / name).read_text(encoding="utf-8"), variables, name), encoding="utf-8"
    )
    print(f"wrote {name}; make {meta['lock_file']} with the stack's own tool and commit both")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[args.index("--root") + 1]) if "--root" in args else Path.cwd()
    if args[:1] == ["write"]:
        return write(root)
    found = problems(root)
    if found is None:
        print(f"pins: {NOT_RUN}")
        return 0
    for item in found:
        print(item)
    if found:
        return 1
    print("ok pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
