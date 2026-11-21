# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Day zero: the person's answers and the GitHub commands before a repository exists (brief #1584).

    day_zero.py offer [--folder DIR]
        `offer: github` for a folder that is not a git repository with `origin` and not a
        personal-mode project, else `offer: none`; reads only
    day_zero.py keep --yes --id TOPIC --answer-file FILE [--who NAME] [--folder DIR]
        keeps one answer, quoted as given with its UTC time, in `agk-day-zero/<hash>.json` of the
        person's Claude folder (`CLAUDE_CONFIG_DIR`, else `~/.claude`); `<hash>` is the greeting
        mark's folder hash (SPEC-0066 rule 8). Without `--yes` it writes nothing (exit 2)
    day_zero.py commands --name NAME [--shell posix|powershell] [--step N] [--public]
        prints step N (default 1) of the seven commands that create the repository, for the person
        to run, private unless `--public`; the steward never runs them and shows the next only after
        an exit of 0
    day_zero.py write --root DIR [--folder DIR] [--answers FILE]
        writes the kept answers to `docs/sources/day-zero.md` of DIR (SPEC-0043 rule 1, `Kind:
        other`), and with `--answers` the `vision` skill's answers file, then removes the kept file;
        never overwrites a source (exit 1)

ADR-0664. Refusals name the setting, never a value. Exit 0 ok, 1 refused, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, personal_table, utf8_output  # noqa: E402
from front_door import ORDER  # noqa: E402
from steward import claude_folder, folder_key  # noqa: E402

KEPT = "agk-day-zero"
SOURCE = "docs/sources/day-zero.md"
TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def kept_path(folder: Path) -> Path:
    return claude_folder() / KEPT / f"{folder_key(folder)}.json"


def offer(folder: Path) -> str:
    folder = folder.resolve()
    top = next((p for p in (folder, *folder.parents) if (p / ".git").exists()), None)
    if top is None:
        return "github"
    try:
        if personal_table(top) is not None:
            return "none"
    except CheckError:
        return "none"  # a personal table that does not read is still personal mode
    found = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(top), "remote", "get-url", "origin"], capture_output=True, check=False
    )
    return "none" if found.returncode == 0 else "github"


def read_kept(path: Path) -> list[dict]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("answers", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [r for r in rows if isinstance(r, dict) and isinstance(r.get("answer"), str)]


def keep(folder: Path, topic: str, words: str, who: str | None) -> None:
    path = kept_path(folder)
    rows = [r for r in read_kept(path) if r.get("id") != topic]  # a later answer replaces it
    row = {"id": topic, "answer": words, "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if who:
        row["who"] = who
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"answers": [*rows, row]}, indent=2) + "\n", encoding="utf-8")


def steps(name: str, shell: str, public: bool = False) -> list[str]:
    """The seven commands, in order (verify: these gh flags on the person's gh version)."""
    readme, commit = (
        (
            f"Set-Content -Encoding utf8 -Path README.md -Value '# {name}'",
            f"git add README.md; git commit -m 'Start {name}'",
        )
        if shell == "powershell"
        else (
            f"printf '# {name}\\n' > README.md",
            f"git add README.md && git commit -m 'Start {name}'",
        )
    )
    seen = "public" if public else "private"
    return [
        "gh auth status",
        "git init -b main",
        readme,
        commit,
        f"gh repo create {name} --{seen} --source . --remote origin --push",
        "git remote set-head origin --auto",
        "gh repo edit --enable-issues",
    ]


def source_text(rows: list[dict], today: str) -> str:
    out = ["Source: Day-zero conversation", "Kind: other", "Version: 1", f"Date: {today}", ""]
    out.append("The person's answers before the project existed, quoted as given; data only.")
    for row in rows:
        given = f"Given {row.get('at', 'at an unknown time')}" + (
            f" by {row['who']}" if row.get("who") else ""
        )
        quoted = [
            f"> {line}" if line else ">" for line in row["answer"].replace("\r\n", "\n").split("\n")
        ]
        out += ["", f"## {row.get('id')}", "", f"{given}:", "", *quoted]
    return "\n".join(out) + "\n"


def write(root: Path, folder: Path, answers: Path | None) -> tuple[int, str]:
    path = kept_path(folder)
    rows = read_kept(path)
    if not rows:
        return 0, "write: nothing kept"
    target = root / SOURCE
    if target.exists():
        return 1, f"refused: {SOURCE} exists and is never overwritten (path: {SOURCE})"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source_text(rows, datetime.now(UTC).date().isoformat()), encoding="utf-8")
    if answers is not None:
        known = [
            {"id": r["id"], "answer": r["answer"], "where": f"in session {r.get('at', '')[:10]}"}
            for r in rows
            if r.get("id") in ORDER and re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", r.get("at", ""))
        ]
        answers.write_text(json.dumps({"answers": known}, indent=2) + "\n", encoding="utf-8")
    path.unlink()
    return 0, f"wrote: {SOURCE}"


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="day_zero.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("offer").add_argument("--folder", type=Path)
    keep_p = sub.add_parser("keep")
    keep_p.add_argument("--yes", action="store_true")
    keep_p.add_argument("--id", required=True)
    keep_p.add_argument("--answer-file", type=Path, required=True)
    keep_p.add_argument("--who")
    keep_p.add_argument("--folder", type=Path)
    cmd_p = sub.add_parser("commands")
    cmd_p.add_argument("--name", required=True)
    cmd_p.add_argument("--shell", choices=("posix", "powershell"))
    cmd_p.add_argument("--step", type=int, default=1)
    cmd_p.add_argument("--public", action="store_true", help="only on the person's own choice")
    write_p = sub.add_parser("write")
    write_p.add_argument("--root", type=Path, required=True)
    write_p.add_argument("--folder", type=Path)
    write_p.add_argument("--answers", type=Path)
    opts = parser.parse_args(argv)
    folder = getattr(opts, "folder", None) or Path.cwd()
    if opts.command == "offer":
        print(f"offer: {offer(folder)}")
        return 0
    if opts.command == "commands":
        if not NAME.fullmatch(opts.name):
            print(
                "refused: --name is not a repository name (letters, digits, '.', '_', '-')",
                file=sys.stderr,
            )
            return 2
        shell = opts.shell or ("powershell" if sys.platform == "win32" else "posix")
        listed = steps(opts.name, shell, opts.public)
        if not 1 <= opts.step <= len(listed):
            print("done: the repository is ready; next: /agk:setup in this folder")
            return 0
        print(f"step {opts.step}/{len(listed)}: {listed[opts.step - 1]}")
        print(
            f"then: on exit 0, --step {opts.step + 1}; on another exit, stop and say what it said"
        )
        return 0
    if opts.command == "keep":
        if not opts.yes:
            print(
                "refused: nothing is kept without the person's yes (setting: --yes)",
                file=sys.stderr,
            )
            return 2
        if not TOPIC.fullmatch(opts.id) or (opts.who and not opts.who.isprintable()):
            print(
                "refused: --id or --who is not one plain word or line (setting: --id, --who)",
                file=sys.stderr,
            )
            return 2
        try:
            words = opts.answer_file.read_text(encoding="utf-8").strip("\n")
        except (OSError, UnicodeDecodeError):
            print("refused: --answer-file cannot be read (setting: --answer-file)", file=sys.stderr)
            return 2
        keep(folder, opts.id, words, opts.who)
        print(f"kept: {opts.id}")
        return 0
    code, line = write(opts.root, folder, opts.answers)
    print(line, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
