"""Fixtures: tiny git repositories built in tmp_path, and a runner for the check scripts."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

# Kit tests are collected only when run through agk.mk (agk-test sets AGK_KIT_TESTS=1), so a
# project's own `pytest .` never collects them.
if os.environ.get("AGK_KIT_TESTS") != "1":
    collect_ignore_glob = ["*"]
else:
    # A commit starts git's automatic maintenance, in the background on the runner's git, and
    # it writes under .git while a test lists the tree (brief #913). Off for every git here.
    _GIT_COUNT = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    for _n, (_key, _value) in enumerate((("maintenance.auto", "false"), ("gc.auto", "0"))):
        os.environ[f"GIT_CONFIG_KEY_{_GIT_COUNT + _n}"] = _key
        os.environ[f"GIT_CONFIG_VALUE_{_GIT_COUNT + _n}"] = _value
    os.environ["GIT_CONFIG_COUNT"] = str(_GIT_COUNT + 2)


PROTECTED = "constitution/\nconfig/\n.claude/\n.github/\ndocs/requirements.md\n"


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root

    def git(self, *args: str) -> str:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=True
        )
        return proc.stdout

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, files: dict[str, str | None], msg: str = "change") -> None:
        for rel, text in files.items():
            if text is None:
                (self.root / rel).unlink()
            else:
                self.write(rel, text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def branch(self, name: str = "feature") -> None:
        self.git("checkout", "-q", "-b", name)

    def run(self, script: str, *args: str, stdin: str | None = None, **env: str):
        full_env = {
            k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")
        }
        full_env.update(env)
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=self.root,
            input=stdin,
            capture_output=True,
            text=True,
            env=full_env,
        )


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path)
    r.git("init", "-q", "-b", "main")
    r.git("config", "user.email", "t@example.invalid")
    r.git("config", "user.name", "t")
    r.git("config", "commit.gpgsign", "false")
    return r
