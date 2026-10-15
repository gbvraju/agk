"""Fixture repositories with known drift for the drift audit (SPEC-0004 rule 18).

Every commit gets an author and committer date, so the audit's window is reproducible with --today.
"""

from __future__ import annotations

import hashlib
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import reviewers

ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 10, 15)

REVIEWERS = (
    "version: 1\n"
    "classes:\n"
    "  protected: {paths: [.claude/, docs/requirements.md, scripts/agk/],"
    " approvers: [maintainers]}\n"
    "teams:\n"
    '  maintainers: {github_team: "@demo-org/maintainers"}\n'
)

BASE_FILES = {
    "agk.toml": 'default_branch = "main"\ntest_dirs = ["tests"]\n',
    "config/protected-paths.txt": ".claude/\ndocs/requirements.md\nscripts/agk/\n",
    "config/reviewers.yaml": REVIEWERS,
    ".github/CODEOWNERS": reviewers.render_codeowners(reviewers.parse(REVIEWERS)),
    "constitution/principles.md": "# Principles\n\n1. A protected change requires an ADR.\n",
    "docs/requirements.md": (
        "# Requirements\n\n"
        "### REQ-001 — Demo one\n\n- Acceptance: AC1 a thing\n- Status: done\n\n"
        "### REQ-002 — Demo two\n\n- Acceptance: AC1 another\n- Status: planned\n"
    ),
    "docs/specs/0001-demo.md": (
        "# SPEC-0001: Demo\n\n- Status: Approved\n- Owner: maintainers\n- Requirements: REQ-001\n\n"
        "## Rules\n\n1. **First.** Do it.\n\n"
        "## Residual\n\n- 2026-10-01: nothing (due 2027-01-01)\n"
    ),
    "docs/adr/0001-demo.md": (
        "# ADR-0001: Demo\n\n- Status: Accepted\n- Date: 2026-09-01\n- Deciders: maintainers\n"
        "- Related: none\n- Requirements: REQ-001\n\n## Context\n\nWhy.\n\n## Decision\n\n"
        "1. **Keep it.** Yes.\n\n## Consequences\n\nNone.\n\n"
        "## Residual\n\n- 2026-09-01: open item\n"
    ),
    "docs/runs/residuals.md": "# Residuals register\n\n## Open\n\n## Closed\n\n| a | b |\n",
    "tests/test_demo.py": '"""REQ-001 AC1"""\n',
    ".claude/settings.json": "{}\n",
    "scripts/agk/tool.py": "x = 1\n",
}


def stamp(days_ago: int) -> str:
    moment = datetime(TODAY.year, TODAY.month, TODAY.day, 12, tzinfo=UTC) - timedelta(days=days_ago)
    return moment.strftime("%Y-%m-%dT%H:%M:%S+0000")


def clean_env() -> dict[str, str]:
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "AGK_KIT_TESTS")
    return {k: v for k, v in os.environ.items() if k not in drop}


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            rel = path.relative_to(root).as_posix()
            out[rel] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
    return out


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str, days_ago: int | None = None) -> str:
        env = clean_env()
        if days_ago is not None:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = stamp(days_ago)
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=True, env=env
        )
        return proc.stdout

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def edit(self, rel: str, old: str, new: str) -> None:
        text = (self.root / rel).read_text(encoding="utf-8")
        assert old in text, (rel, old)
        self.write(rel, text.replace(old, new, 1))

    def commit(self, days_ago: int, message: str = "change") -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, days_ago=days_ago)
        return self.git("rev-parse", "HEAD").strip()


def base(root: Path) -> Repo:
    repo = Repo(root)
    for rel, text in BASE_FILES.items():
        repo.write(rel, text)
    repo.commit(60, "base")
    return repo


def add_protected_change(repo: Repo, days_ago: int, covered: bool = False) -> str:
    repo.write(".claude/settings.json", f'{{"n": {days_ago}}}\n')
    if covered:
        repo.write(
            f"docs/adr/00{90 + days_ago % 9}-cover.md",
            "# ADR-0090: Cover\n\n- Status: Accepted\n- Date: 2026-10-10\n\n"
            "Protected classes: `.claude/`\n",
        )
    return repo.commit(days_ago, "protected change")


def draft_spec(repo: Repo, days_ago: int) -> None:
    repo.write(
        "docs/specs/0002-draft.md",
        "# SPEC-0002: Draft\n\n- Status: Draft\n- Owner: maintainers\n- Requirements: REQ-002\n",
    )
    repo.commit(days_ago, "add a draft spec")


def proposed_adr(repo: Repo, date_text: str) -> None:
    repo.write(
        "docs/adr/0002-proposed.md",
        f"# ADR-0002: Proposed\n\n- Status: Proposed\n- Date: {date_text}\n"
        "- Deciders: maintainers\n",
    )
    repo.commit(1, "add a proposed adr")


def overdue_adr_residual(repo: Repo) -> None:
    repo.edit(
        "docs/adr/0001-demo.md",
        "- 2026-09-01: open item",
        "- 2026-09-01: open item (due 2026-01-01)",
    )
    repo.commit(1, "residual with a date")


def register(repo: Repo, lines: list[str]) -> None:
    repo.edit("docs/runs/residuals.md", "## Open\n", "## Open\n\n" + "\n".join(lines) + "\n")
    repo.commit(1, "register lines")


def clean(root: Path) -> Path:
    base(root)
    return root
