"""The release pull request check (SPEC-0028 rules 4 and 5). Kit-only: never installed.

In flow mode a pull request that raises `version` in `agk.toml` is a release pull request. It may
change only `CHANGELOG.md`, `agk.toml`, `kit/manifest.json`, `.claude-plugin/plugin.json` and
`kit/hashes.json`; the three versions are raised together to one greater number; and the lines under
`## Unreleased` are moved unchanged and in order under `## <new version> (<date>)`, leaving
`## Unreleased` empty and the older sections as they were. The fragments under `changelog.d/` are
gathered into those lines in pull request order (SPEC-0031 rules 3 and 4): their deletion is part of
the release, a fragment left, added or edited fails it. Each ADR that a Final line accepted
(a record on the base that its Final comment, given with `--comments FILE` as
`gh api repos/{repo}/issues/comments/<id>` answers, verifies: `check_adrs.verified_records`,
SPEC-0021 rule 3a) has its Status line flipped from `Proposed` to `Accepted` by the release and
nothing else changed; one left `Proposed` fails it. An unverified record asks no flip, and a
release without FILE fails closed while the base holds a record. In
strict mode, when no version is raised and when the base does not have this script yet (the pull
request that adds it is the last build that bumps itself, SPEC-0028 rule 9) it prints `ok release`
and checks nothing. Git and files only: no network, no model. Messages name the rule and the
path, never a version.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_adrs
from changelog_fragments import FRAG_DIR, gathered_lines, tree_fragments
from check_adrs import status_of
from common import (
    CheckError,
    changed_files,
    changed_lines,
    git,
    merge_base,
    pr_mode,
    repo_root,
    resolve_base,
    run,
    show,
)

NAME = "release"
ALLOWED = (
    "CHANGELOG.md",
    "agk.toml",
    "kit/manifest.json",
    ".claude-plugin/plugin.json",
    "kit/hashes.json",
)
DOTTED = re.compile(r"\d+(?:\.\d+)*")
HEADING = "## "


def toml_version(text: str | None) -> str | None:
    try:
        value = tomllib.loads(text or "").get("version")
    except tomllib.TOMLDecodeError:
        return None
    return value if isinstance(value, str) else None


def json_version(text: str | None, key: str) -> str | None:
    try:
        value = json.loads(text or "").get(key)
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def numbers(version: str | None) -> tuple[int, ...] | None:
    return tuple(map(int, version.split("."))) if version and DOTTED.fullmatch(version) else None


def sections(text: str) -> list[tuple[str, list[str]]]:
    """(heading, non-empty lines) of each `## ` section, with the text before the first as ''."""
    found: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        if line.startswith(HEADING):
            found.append((line.strip(), []))
        elif line.strip():
            found[-1][1].append(line.rstrip())
    return found


def moved_unchanged(old: str, new: str, version: str, gathered: list[str] | None = None) -> bool:
    """Unreleased became empty, its lines (then the gathered fragment lines) are the new version's,
    the rest is as it was."""
    before, after = sections(old), sections(new)
    if len(before) < 2 or len(after) != len(before) + 1:
        return False
    heading = re.fullmatch(rf"## {re.escape(version)} \(\d{{4}}-\d{{2}}-\d{{2}}\)", after[2][0])
    return (
        before[0] == after[0]
        and before[1][0] == after[1][0] == "## Unreleased"
        and after[1][1] == []
        and heading is not None
        and after[2][1] == before[1][1] + (gathered or [])
        and after[3:] == before[2:]
    )


# The opt-in marker of a changelog entry (brief #320 answer 2): one `(opt-in: <settings>)` at the
# end of the line, for a feature a project switches on by a setting of `agk.toml`; a dotted setting
# names a key of a table. The marker may name several settings separated by `, ` (brief #340
# answer 1), each once. The release moves the line unchanged, so the marker stays with it.
SETTING = r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*"
OPT_IN = re.compile(rf"(?P<text>.*\S) \(opt-in: (?P<settings>{SETTING}(?:, {SETTING})*)\)")
ENTRY = re.compile(r"- (?:#\d+ )?(?P<rest>.*)")
SUMMARY_LIMIT = 120
RELEASED = re.compile(r"## (\d+(?:\.\d+)*) \(\d{4}-\d{2}-\d{2}\)")
# An entry whose change starts with `<version> added ` speaks for that earlier release (brief #340
# answer 3): a later release may list what an older one shipped before the marker existed.
NAMED = re.compile(r"(?P<version>\d+(?:\.\d+)*) added ")


def opt_in(line: str) -> tuple[tuple[str, ...], str] | None:
    """(settings, one-line summary) of a changelog line `- [#n ]<change> (opt-in: <settings>)`,
    else None (no marker, a marker not at the end, more than one, or a malformed list). The
    summary is the change up to its first `: `, cut to SUMMARY_LIMIT characters at a word
    boundary."""
    entry = ENTRY.fullmatch(line.strip())
    found = OPT_IN.fullmatch(entry.group("rest")) if entry else None
    if found is None or "(opt-in:" in found.group("text"):
        return None
    settings = tuple(found.group("settings").split(", "))
    if len(set(settings)) != len(settings):
        return None
    summary = found.group("text").split(": ", 1)[0].strip()
    if len(summary) > SUMMARY_LIMIT:
        summary = summary[: SUMMARY_LIMIT + 1].rsplit(" ", 1)[0].rstrip(" ,;")
    return settings, summary


def release_named(line: str) -> str | None:
    """The version an entry speaks for when its change starts with `<version> added `, else None."""
    entry = ENTRY.fullmatch(line.strip())
    named = NAMED.match(entry.group("rest")) if entry else None
    return named.group("version") if named else None


def opt_ins(changelog: str, old: str, new: str) -> list[tuple[str, str]]:
    """One (setting, summary) per setting of every opt-in entry of the released sections
    `## V (<date>)` with V <= new, newest section first, in the changelog's order. An entry counts
    when old < V, or, when it speaks for an earlier release R < V, when old < R instead.
    `## Unreleased` is not read."""
    low, high = numbers(old), numbers(new)
    if low is None or high is None:
        return []
    found: list[tuple[str, str]] = []
    section = None
    for line in changelog.splitlines():
        if line.startswith(HEADING):
            heading = RELEASED.fullmatch(line.strip())
            version = numbers(heading.group(1)) if heading else None
            section = version if version is not None and version <= high else None
            continue
        if section is None or (item := opt_in(line)) is None:
            continue
        named = release_named(line)
        speaks = numbers(named) if named else None
        since = speaks if speaks is not None and speaks < section else section
        if low < since:
            found.extend((setting, item[1]) for setting in item[0])
    return found


UNFLIPPED = (
    "rule 5: an ADR of docs/adr/ that a Final line accepted still says Proposed; "
    "set its Status line to Accepted (check_adrs.py --pending lists them)"
)


def recorded_adrs(root: Path, mb: str, comments: list[dict] | None = None) -> set[str]:
    """The ADR paths that a squash commit of merge_cleared.py on the base records as accepted by a
    Final line that COMMENTS verifies (SPEC-0021 rule 3a): the release flips each one's Status
    line. Without COMMENTS while a record exists: a CheckError (fail closed)."""
    try:
        numbers = check_adrs.verified_records(root, mb, comments)
    except CheckError as err:
        raise CheckError(f"rule 5: {err}") from None
    names = git(root, "ls-tree", "-z", "--name-only", f"{mb}:docs/adr", check=False).split("\0")
    return {
        f"docs/adr/{name}"
        for name in names
        if (m := check_adrs.FILE_RE.match(name)) and m.group(1) in numbers
    }


def status_flip(root: Path, mb: str, path: str) -> bool:
    """Whether PATH changes only its Status line, from Proposed to Accepted."""
    lines = changed_lines(root, mb, path)
    return sorted(ln.strip() for ln in lines) == ["+- Status: Accepted", "-- Status: Proposed"]


def read_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def check(root: Path, comments: list[dict] | None = None) -> int:
    if pr_mode(root) != "flow":
        print(f"ok {NAME}")
        return 0
    base = resolve_base(root, None)
    mb = merge_base(root, base) if base else "HEAD"
    if show(root, mb, "scripts/agk/check_release.py") is None:
        print(f"ok {NAME}")  # the pull request that adds this check is the last build that bumps
        return 0
    old = toml_version(show(root, mb, "agk.toml"))
    new = toml_version((root / "agk.toml").read_text(encoding="utf-8"))
    if new is None or old is None or new == old:
        print(f"ok {NAME}")
        return 0
    changes = changed_files(root, mb)
    fragments = set(tree_fragments(root, mb))
    flips = recorded_adrs(root, mb, comments)
    for path in sorted(set(changes) - set(ALLOWED)):
        if path in fragments and changes[path] == "D":
            continue
        if path in flips and changes[path] == "M" and status_flip(root, mb, path):
            continue
        if path.startswith(FRAG_DIR):
            raise CheckError(f"rule 4: a release pull request adds or edits a file of {FRAG_DIR}")
        raise CheckError(f"rule 5: a release pull request changes {path}, outside its five files")
    if any((root / path).exists() for path in fragments):
        raise CheckError(f"rule 4: a fragment is left under {FRAG_DIR}")
    if any(status_of(read_or_empty(root / path)) == "Proposed" for path in flips):
        raise CheckError(UNFLIPPED)
    manifest = json_version((root / "kit/manifest.json").read_text(encoding="utf-8"), "kit_version")
    plugin = json_version(
        (root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"), "version"
    )
    if not (new == manifest == plugin):
        raise CheckError("rule 5: the three versions differ")
    if numbers(new) is None or numbers(old) is None or numbers(new) <= numbers(old):
        raise CheckError("rule 5: the three versions do not rise")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    gathered = gathered_lines(root, mb, "rule 4")[1]
    if not moved_unchanged(show(root, mb, "CHANGELOG.md") or "", changelog, new, gathered):
        problem = (
            "rule 5: Unreleased is not empty after the move"
            if sections(changelog)[1:2] and sections(changelog)[1][1]
            else "rule 5: the lines of Unreleased were not moved unchanged under the new version"
        )
        raise CheckError(problem)
    print(f"ok {NAME}")
    return 0


def valid_release(root: Path, mb: str, comments: list[dict] | None = None) -> bool:
    """Whether the change set from `mb` is a valid release pull request: flow mode, a raised
    version, nothing changed outside the release files (a deleted fragment is part of it) and
    every rule of `check` met, with the Final COMMENTS of the base's records (SPEC-0021 rule 3a;
    without them while a record exists, not a release). `check_protected_changes.py` asks, so
    that a release needs no ADR for the protected files it must change (brief #212)."""
    if pr_mode(root) != "flow" or show(root, mb, "scripts/agk/check_release.py") is None:
        return False
    old = toml_version(show(root, mb, "agk.toml"))
    new = toml_version((root / "agk.toml").read_text(encoding="utf-8"))
    if old is None or new is None or old == new:
        return False
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return check(root, comments) == 0
    except CheckError:
        return False


USAGE = "usage: check_release.py [--comments FILE]"


def main() -> int:
    args = sys.argv[1:]
    if args and (len(args) != 2 or args[0] != "--comments"):
        raise CheckError(USAGE)
    root = repo_root()
    return check(root, check_adrs.read_comments(args[1] if args else None))


if __name__ == "__main__":
    sys.exit(run(NAME, main))
