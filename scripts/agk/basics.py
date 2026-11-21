# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The foundation's basics (SPEC-0072 rule 4 as amendment 202 proposes; REQ-079; brief #1594,
ADR-0674).

    python3 scripts/agk/basics.py write [--root DIR]

The foundation build runs `write` once. By `[delivery] work_type` it picks the shape (a web app
and an API service are servers, a data pipeline is a report job) and, for a chosen Python stack,
writes from `kit/templates/`: the `.env` ignore line, `.env.example` (names and placeholders
only), the startup settings check, the safe log, the health address (servers only), `README.md`
and `docs/deploy.md` ("local only" until a hosting option is chosen). It never writes over an
existing file. With `mode = "adopt"` it writes nothing and proposes each missing part as one plain
question. A tracked environment file is named and never removed. Other work types and stacks are
said plainly and get theirs with their pack.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

from common import load_config, utf8_output
from gates.pins import chosen
from init import render, slug
from playbook_format import declaration

TEMPLATES = Path(__file__).resolve().parents[2] / "kit" / "templates"
SKELETON = TEMPLATES / "skeleton" / "python"
USAGE = "usage: python3 scripts/agk/basics.py write [--root DIR]"
IGNORE = (
    "# A product's own environment file, never committed; `.env.example` holds its names "
    "(brief #1594, ADR-0674).\n.env\n"
)
ASK = "Your project has no {}. Shall I add one? Yes (recommended) · later"
SETTING = {
    "APP_ENV": ("Where the product runs: local or production.", "local or production"),
    "DATABASE_PATH": ("The database file, for example local.db on this machine.", "file path"),
    "PORT": ("The port the server listens on, for example 8000.", "port number"),
}
LOCAL = {"APP_ENV": "local", "DATABASE_PATH": "local.db", "PORT": "8000"}
# work type -> (shape, package folder, what it is); `[architecture] layers` name the folders.
SHAPES = {
    "web-app": ("server", "backend", "A web app"),
    "api-service": ("server", "api", "An API service"),
    "data-pipeline": ("job", "job", "A data and report tool"),
}
SERVER = ("APP_ENV", "DATABASE_PATH", "PORT")
# (part, source under SKELETON, target with {pkg}, the part's name in the adopt question)
PARTS = [
    ("all", "common/settings.py", "{pkg}/settings.py", "startup settings check"),
    ("all", "common/logs.py", "{pkg}/logs.py", "safe request log"),
    ("server", "server/__init__.py", "{pkg}/__init__.py", ""),
    ("server", "server/app.py", "{pkg}/app.py", "health check"),
    ("server", "server/__main__.py", "{pkg}/__main__.py", ""),
    ("job", "job/__init__.py", "{pkg}/__init__.py", ""),
    ("job", "job/__main__.py", "{pkg}/__main__.py", "run log"),
    ("job", "job/samples/example.csv", "samples/example.csv", "sample input file"),
]


def rendered(root: Path, shape: str, pkg: str, what: str) -> dict[str, tuple[str, str]]:
    """Each file the shape writes: target -> (its text, the adopt question's part name)."""
    names = SERVER if shape == "server" else ("APP_ENV",)
    run = f"-m {pkg}" + ("" if shape == "server" else " samples/example.csv")
    check = f"Check it: `python3 -m {pkg} --check` (asks the health address once)\n"
    variables = {
        "project": slug(root.resolve().name),
        "settings": "\n".join(f"# {SETTING[n][0]}\n{n}=<{SETTING[n][1]}>" for n in names),
        "what": f"{what}. The foundation wrote its settings check, its safe log"
        + (" and its health address." if shape == "server" else " and its run line."),
        "local": ", ".join(f"`{n}={LOCAL[n]}`" for n in names),
        "run": f"python3 {run}",
        "run_windows": f"py {run}",
        "check": check if shape == "server" else "",
        "hosting": "local only",
        "health": ", then check that `/health` answers ok" if shape == "server" else "",
    }
    out: dict[str, tuple[str, str]] = {}
    for name, target, part in (
        ("project-settings-example.txt", ".env.example", "example settings file"),
        ("project-readme.md", "README.md", "README"),
        ("deploy.md", "docs/deploy.md", "written deploy step"),
    ):
        source = (TEMPLATES / name).read_text(encoding="utf-8")
        out[target] = (render(source, variables, name), part)
    for kind, source, target, part in PARTS:
        if kind in ("all", shape):
            text = (SKELETON / source).read_text(encoding="utf-8")
            out[target.format(pkg=pkg)] = (text, part)
    return out


def tracked_env(root: Path) -> bool:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "ls-files", "--", ".env"], cwd=root, capture_output=True, text=True, check=False
    )
    return bool(done.stdout.strip())


def write(root: Path) -> list[str]:
    """The lines `write` prints; each names a path or a setting, never a value."""
    work_type = declaration(root)[0]
    if work_type is None:
        return ["basics: not run: no work type (setting: work_type)"]
    adopt = load_config(root)["mode"] == "adopt"
    out = ["warning: a tracked environment file (path class: .env); remove it from git yourself"]
    out = out if tracked_env(root) else []
    ignore = root / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []
    if ".env" not in lines:
        if adopt:
            out.append(f"proposed: .gitignore: {ASK.format('ignore line for its .env file')}")
        else:
            old = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
            ignore.write_text(old + ("\n" if old and not old.endswith("\n") else "") + IGNORE)
            out.append("wrote .gitignore: the .env line")
    if work_type not in SHAPES:
        return [
            *out,
            "not written: basics: no skeleton for this work type yet (setting: work_type)",
        ]
    stack = chosen(root)
    if stack is None or stack[0][0] != "python-pyproject":
        why = "no stack chosen" if stack is None else "no skeleton for this stack yet"
        return [*out, f"not written: basics: {why} (setting: stack record)"]
    asked: set[str] = set()
    for target, (text, part) in rendered(root, *SHAPES[work_type]).items():
        path = root / target
        if path.exists():
            out.append(f"kept {target}")
        elif adopt:
            if part and part not in asked:
                asked.add(part)
                out.append(f"proposed: {target}: {ASK.format(part)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
            out.append(f"wrote {target}")
    return out


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] != ["write"] or len(args) not in (1, 3) or (len(args) == 3 and args[1] != "--root"):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(args[2]) if len(args) == 3 else Path.cwd()
    print("\n".join(write(root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
