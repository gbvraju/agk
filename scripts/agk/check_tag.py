"""The check of a pushed tag: the tagged commit is a release (brief #212, build (b)). Kit-only.

    python3 check_tag.py --tag vN.N.N [--issue-json FILE]

Run on the tagged commit by the workflow `agk-tag.yml`. It checks, in this order, that the tag is
`vN.N.N`; that `agk.toml`, `kit/manifest.json` and `.claude-plugin/plugin.json` state the tag's
version; that `CHANGELOG.md` has a section `## <version> (` ; that no fragment is left under
`changelog.d/`; and that `kit/hashes.json` matches the kit files (`kit_hashes.problems`, against
the first parent, so the row of the new version is compared). It prints `ok tag`, or `FAIL tag:`
and the first check that failed and exits 1. With `--issue-json` and a failure it writes the one
issue `The tag <tag> is not a release` as JSON (title, label `agk-release`, body: the commit, the
failing check with its output and the fix; a plain issue, not a brief, because only a person can
fix a tag). It deletes and moves no tag, makes no
release and no commit, and reads git and files only: no network, no model.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

import kit_hashes
from changelog_fragments import FRAG_DIR, tree_fragments
from common import CheckError, git, repo_root, run

NAME = "tag"
USAGE = "usage: check_tag.py --tag vN.N.N [--issue-json FILE]"
TAG = re.compile(r"v(\d+\.\d+\.\d+)")
LABEL = "agk-release"
FIX = (
    "delete the tag and its release, and tag the merge commit of the release pull request "
    "(this check deletes nothing and never moves a tag)"
)


def stated(root: Path) -> list[tuple[str, str | None]]:
    """(path, version) of each file that states the kit's version; None when unreadable."""

    def read(rel: str, key: str, loader) -> str | None:
        try:
            value = loader((root / rel).read_text(encoding="utf-8")).get(key)
        except (OSError, ValueError):
            return None
        return value if isinstance(value, str) else None

    return [
        ("agk.toml", read("agk.toml", "version", tomllib.loads)),
        ("kit/manifest.json", read("kit/manifest.json", "kit_version", json.loads)),
        (".claude-plugin/plugin.json", read(".claude-plugin/plugin.json", "version", json.loads)),
    ]


def failure(root: Path, tag: str) -> str | None:
    """The first check the tagged commit fails, or None."""
    found = TAG.fullmatch(tag)
    if not found:
        return "the tag is not of the form vN.N.N"
    version = found.group(1)
    for path, have in stated(root):
        if have != version:
            return f"{path} states a version other than the tag"
    changelog = root / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8") if changelog.is_file() else ""
    if not re.search(rf"(?m)^## {re.escape(version)} \(", text):
        return "CHANGELOG.md has no section for the tag"
    if tree_fragments(root, "HEAD"):
        return f"a fragment is left under {FRAG_DIR}"
    parents = git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
    if kit_hashes.problems(root, parents[0] if parents else "HEAD"):
        return "kit/hashes.json does not match the kit files"
    return None


def issue(tag: str, commit: str, message: str) -> dict:
    """The one issue, a plain issue for a person: only a person can fix a tag, so it is not a
    brief and carries no priority. It says which check failed, with its output, and the fix."""
    command = f"python3 scripts/agk/check_tag.py --tag {tag}"
    body = (
        f"The tag {tag} is not a release.\n\n"
        f"- Commit: {commit}\n"
        f"- Failing check: {message}\n"
        f"- Output of `{command}`: FAIL {NAME}: {message}\n"
        f"- Fix: {FIX}\n"
    )
    return {"title": f"The tag {tag} is not a release", "labels": [LABEL], "body": body}


def check(root: Path, tag: str, out: Path | None) -> int:
    message = failure(root, tag)
    if message is None:
        print(f"ok {NAME}")
        return 0
    if out is not None:
        commit = git(root, "rev-parse", "HEAD").strip()
        try:
            out.write_text(json.dumps(issue(tag, commit, message)) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CheckError("the issue file cannot be written") from exc
    print(f"FAIL {NAME}: {message}")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    opts = dict(zip(args[::2], args[1::2], strict=False))
    if len(args) % 2 or "--tag" not in opts or not set(opts) <= {"--tag", "--issue-json"}:
        print(USAGE)
        return 2
    out = Path(opts["--issue-json"]) if "--issue-json" in opts else None
    return check(repo_root(), opts["--tag"], out)


if __name__ == "__main__":
    sys.exit(run(NAME, main))
