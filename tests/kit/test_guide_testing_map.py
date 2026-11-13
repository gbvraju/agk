"""The testing guide's worked map per module (brief #1156, ADR-0492; REQ-062).

`docs/guides/testing.md` has a section "A map per module": a `[testing]` table for an invented
project with `backend/orders/`, `backend/users/` and `frontend/src/`, one `[[testing.map]]` entry
per module naming its own tests and the shared `backend/common/**` in `always_full`. The tests
read the example from the guide, parse it as TOML, check the keys the selection reads (`code` and
`tests`), and run the test plan on a fixture repository that uses it: a change in one module
selects only that module's tests, and a change in the shared code selects the full suite.
Invented data, no network.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import impact

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "testing.md"
HEADER = "## A map per module"

BASE_TOML = (
    'default_branch = "main"\n'
    'test_dirs = ["tests"]\n'
    'test_patterns = ["test_*.py", "*.test.ts"]\n'
    "project_tests = 'exit 0'\n"
)
FILES = {
    "backend/orders/x.py": "# orders\n",
    "backend/users/x.py": "# users\n",
    "backend/common/x.py": "# shared\n",
    "frontend/src/x.ts": "// app\n",
    "tests/backend/orders/test_orders.py": "# orders tests\n",
    "tests/backend/users/test_users.py": "# users tests\n",
    "tests/frontend/x.test.ts": "// app tests\n",
}


def section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.find(HEADER)
    assert start != -1, "the testing guide has no section 'A map per module'"
    end = text.find("\n## ", start + len(HEADER))
    return text[start : end if end != -1 else len(text)]


def example() -> str:
    found = re.search(r"```toml\n(.*?)```", section(), re.S)
    assert found, "the section shows no toml block"
    return found.group(1)


def table() -> dict:
    return tomllib.loads(example())["testing"]


def test_the_section_exists_and_says_why_one_broad_entry_is_wrong():
    """REQ-062: brief #1156 answer 2 (a)."""
    body = section()
    assert "backend/**" in body
    assert "every back-end test" in body
    assert "default branch" in body and "merge wave" in body


def test_the_example_parses_and_each_entry_has_code_and_tests():
    """REQ-062: brief #1156 answer 2 (b) (the keys impact.py reads)."""
    found = table()
    entries = found["map"]
    codes = [e["code"] for e in entries]
    assert codes == ["backend/orders/**", "backend/users/**", "frontend/src/**"]
    for entry in entries:
        assert set(entry) == {"code", "tests"}
        assert isinstance(entry["tests"], list) and entry["tests"]
    assert "backend/common/**" in found["always_full"]
    assert not any(e["code"] == "backend/**" for e in entries)


def test_the_example_passes_the_always_full_rule(tmp_path):
    """REQ-062: brief #1156 answer 1 (the shared code carries its `# full:` reason)."""
    (tmp_path / "agk.toml").write_text(BASE_TOML + example(), encoding="utf-8")
    assert impact.always_full_problems(tmp_path) == []


def selection(repo, changed: str) -> dict:
    repo.commit({"agk.toml": BASE_TOML + example(), **FILES}, "base")
    repo.branch("feature")
    repo.commit({changed: "# changed\n"}, "change")
    proc = repo.run("test_plan.py", "--base", "main", "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)["regression"]


def test_a_module_change_selects_only_that_modules_tests(repo):
    """REQ-062: brief #1156 answer 2 (c) (one module, not the full suite)."""
    found = selection(repo, "backend/orders/x.py")
    assert found["full"] is False
    assert [s["file"] for s in found["selected"]] == ["tests/backend/orders/test_orders.py"]
    assert found["unmapped"] == []


def test_a_shared_change_selects_the_full_suite(repo):
    """REQ-062: brief #1156 answer 2 (c) (always_full)."""
    found = selection(repo, "backend/common/x.py")
    assert found["full"] is True
    assert "always_full" in found["reason"]
