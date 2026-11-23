"""A test that reads a file by a literal join runs when that file changes (brief #1792; REQ-062).

The measure of brief #1792 run on the kit's own tree: for every tracked file that a kit test reads
by a join of quoted literals (`ROOT / "skills" / "upgrade" / "SKILL.md"`, `Path("a", "b")`,
`os.path.join("a", "b")`) and that is not documentation, `impact.select` on a change of that file
alone selects that test, or runs the full suite. The class closes here: a new test that reads a
file the selection cannot see fails this test, naming the file, the test and SPEC-0055 rule 6.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import impact
from common import load_config

ROOT = Path(__file__).resolve().parents[2]
REAL_INDEX = impact.name_index
RULE = "SPEC-0055 rule 6 (brief #1792): a change of {file} alone does not select {test}"


def pairs(root: Path) -> dict[str, set[str]]:
    """Each tracked, non-documentation file that a test reads by a literal join, with its tests."""
    cfg = load_config(root)
    dirs, patterns = list(cfg["test_dirs"]), list(cfg["test_patterns"])
    files = impact.head_files(root, "HEAD")
    tracked = set(files)
    is_doc = impact.doc_reader(root, "HEAD")
    found: dict[str, set[str]] = {}
    tests = [p for p in files if impact.is_test_file(p, dirs, patterns)]
    for test, source in impact._blobs(root, "HEAD", tests):
        for path in impact.joined_paths(source):
            if path in tracked and path != test and not is_doc(path):
                if not impact.is_test_file(path, dirs, patterns):
                    found.setdefault(path, set()).add(test)
    return found


def test_every_file_a_test_reads_by_a_join_selects_that_test(monkeypatch):
    """REQ-062: brief #1792 answer 3 (the class stays closed)."""
    found = pairs(ROOT)
    assert found, "no test reads a file by a literal join: the measure reads nothing"
    # One tree, so one index and one config for every selection; the importer step only adds
    # tests, so leaving it out keeps the check strict: each test must be named.
    monkeypatch.setattr(impact, "name_index", lambda r, h, t: index(r, h, tuple(t)))
    monkeypatch.setattr(impact, "config_source", cache(impact.config_source))
    monkeypatch.setattr(impact, "add_importers", lambda *args: {})
    missed = []
    for path in sorted(found):
        monkeypatch.setattr(impact, "changed_files", lambda r, b, h, p=path: [p])
        picked = impact.select(ROOT, "HEAD", "HEAD")
        chosen = {s.test for s in picked.selected}
        if not picked.full:
            missed += [RULE.format(file=path, test=t) for t in sorted(found[path] - chosen)]
    assert missed == [], "\n".join(missed)


@cache
def index(root: Path, head: str, tests: tuple[str, ...]) -> dict[str, set[str]]:
    """One name index for every selection of this test (each reads the same tree)."""
    return REAL_INDEX(root, head, list(tests))
