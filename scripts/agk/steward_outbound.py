"""The outbound data guard (SPEC-0059 rule 6, build (e); brief #1324, ADR-0561).

Usage: python3 scripts/agk/steward_outbound.py check (--text TEXT | --file FILE) [--root DIR]

Before any text leaves a project for the kit repository (an issue, a comment, a correction) it is
checked, fail closed, against: the tokens of the project's `config/neutrality.txt` and of the kit's
list (`kit/templates/neutrality.txt`, where the project holds it); the detectors of
`guard.scan_text` with the `[guard] patterns` (SPEC-0042 rule 10); URLs and names of the hosts of
the project's git remotes; and repository names other than the kit's. A match prints one line per
class naming the setting, never the value, and exits 2; a list or the remotes that cannot be read
refuse the same way. A clean text prints `ok outbound` and exits 0. No network; git is read only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import utf8_output  # noqa: E402

KIT_HOST = "github.com"
FORGES = frozenset({"github.com", "gitlab.com", "bitbucket.org"})
LISTS = ("config/neutrality.txt", "kit/templates/neutrality.txt")  # the second only where present
RULE = "SPEC-0059 rule 6"
REWRITE = "; rewrite it with invented names (example.com)"
URL = re.compile(r"(?i)\b(?:https?|ssh|git)://(?:[^@/\s]+@)?([a-z0-9.-]+)(?::\d+)?(/[^\s)>\]\"'`]*)?")
SCP = re.compile(r"(?i)\b[\w.-]+@([a-z0-9.-]+\.[a-z]{2,}):([\w.-]+/[\w.-]+)")
REPO_REFS = (
    re.compile(r"\brepos/([\w.-]+/[\w.-]+)"),
    re.compile(r"(?<![\w./-])([A-Za-z0-9][\w.-]*/[\w.-]+)#\d+"),
)


def refusal(what: str, setting: str) -> str:
    return f"outbound guard: {RULE} refuses {what} (setting: {setting})"


def cannot(setting: str) -> list[str]:
    return [refusal("a text it cannot check", setting)]


def repo_name(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p]
    return "/".join(parts[:2]).lower().removesuffix(".git") if len(parts) >= 2 else ""


def parse_remote(url: str) -> tuple[str, str] | None:
    """(host, owner/repo) of a remote URL, lower case; None for a local path."""
    found = URL.match(url.strip())
    if found:
        return found[1].lower(), repo_name(found[2] or "")
    found = SCP.match(url.strip())
    return (found[1].lower(), repo_name(found[2])) if found else None


def remotes(root: Path) -> list[tuple[str, str]] | None:
    """The project's git remotes as (host, owner/repo); None when git cannot read them."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell, no network
            ["git", "-C", str(root), "config", "--local", "--get-regexp", r"^remote\..*\.url$"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return None
    if proc.returncode not in (0, 1):  # 1: no remote is set
        return None
    urls = [line.split(None, 1)[1] for line in proc.stdout.splitlines() if " " in line]
    return [r for r in map(parse_remote, urls) if r is not None]


def tokens(root: Path) -> list[tuple[str, list[str]]] | str:
    """(setting, tokens) of each list; the setting of the first list that cannot be read."""
    from common import read_list

    out = []
    for i, rel in enumerate(LISTS):
        path = root / rel
        if i and not path.exists():
            continue
        try:
            out.append((rel, [t.lower() for t in read_list(path.read_text(encoding="utf-8"))]))
        except (OSError, UnicodeDecodeError):
            return rel
    return out


def kit_repo(root: Path) -> str | None:
    """The kit's `owner/repo`: the `repository` of `.claude-plugin/plugin.json` (the kit itself,
    or the kit checkout holding this file), else the `agk` marketplace of `.claude/settings.json`
    (`kit/templates/plugin-settings.txt`); None when neither names one (every repository is then
    another's, fail closed)."""
    for base in (root, Path(__file__).resolve().parents[2]):
        try:
            data = json.loads((base / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            url = data.get("repository")
            url = url.get("url") if isinstance(url, dict) else url
            found = parse_remote(str(url)) if isinstance(url, str) else None
            if found and found[0] == KIT_HOST and found[1]:
                return found[1]
        except (OSError, ValueError, AttributeError):
            pass
    try:
        settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        source = settings["extraKnownMarketplaces"]["agk"]["source"]
        if source.get("source") == "github" and repo_name(str(source.get("repo") or "")):
            return repo_name(str(source["repo"]))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def is_kit(found: list[tuple[str, str]] | None, kit: str | None) -> bool:
    return bool(found and kit and (KIT_HOST, kit) in found)


def check(
    text: str, root: Path, found: list[tuple[str, str]] | None = None, kit: str | None = None
) -> list[str]:
    """The refusal lines for TEXT bound for the kit repository; [] when it may be posted. KIT is
    looked up when None; "" means no kit is named."""
    kit = kit_repo(root) if kit is None else (kit or None)
    lists = tokens(root)
    if isinstance(lists, str):
        return cannot(lists)
    found = remotes(root) if found is None else found
    if found is None:
        return cannot("git remotes")
    from guard import scan_text

    from config import guard_patterns

    try:
        patterns = guard_patterns(root)
    except Exception:  # noqa: BLE001 - a refused [guard] table cannot be checked: fail closed
        return cannot("[guard]")
    low, classes = text.lower(), {}
    for setting, words in lists:
        if any(w in low for w in words):
            classes["neutrality token"] = setting
    for finding in scan_text(text, patterns):
        classes.setdefault(finding.kind, "[guard]; data guard, SPEC-0042")
    hosts = {h for h, _ in found}
    own = {r for _, r in found if r and r != kit}
    repos: set[str] = set()
    for match in URL.finditer(text):
        host, repo = match[1].lower(), repo_name(match[2] or "")
        if host in hosts and (host, repo) != (KIT_HOST, kit):
            classes.setdefault("project host URL", "git remotes")
        if host in FORGES or host in hosts:
            repos.add(repo)
    for host in hosts - {KIT_HOST}:
        if re.search(rf"(?<![\w.-]){re.escape(host)}(?![\w-])", low):
            classes.setdefault("project host URL", "git remotes")
    for pattern in REPO_REFS:
        repos.update(m[1].lower().removesuffix(".git") for m in pattern.finditer(text))
    repos.update(r for r in own if re.search(rf"(?<![\w.-]){re.escape(r)}(?![\w-])", low))
    if any(r and r != kit for r in repos):
        classes.setdefault("another repository name", "kit repository")
    return [refusal(kind, setting) + REWRITE for kind, setting in sorted(classes.items())]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="steward_outbound.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("check")
    group = cmd.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file", type=Path)
    cmd.add_argument("--root", type=Path, default=Path.cwd())
    opts = parser.parse_args(argv)
    try:
        text = opts.text if opts.text is not None else opts.file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print("\n".join(cannot("--file")))
        return 2
    lines = check(text, opts.root)
    print("\n".join(lines) if lines else "ok outbound")
    return 2 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
