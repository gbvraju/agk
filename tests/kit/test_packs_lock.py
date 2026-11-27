"""Tests of the pack lock and its commands (SPEC-0077 rule 4; REQ-084 AC3; brief #2033, ADR-0840).

`packs.py verify` (offline) fails a locked file whose hash differs, a file the lock does not hold,
a lock entry whose folder is missing, a locked pack that `[packs] use` does not list and a use
entry the lock does not hold, each naming the rule, the pack and the key or setting, never a value;
`check_packs.findings` carries the lines into the `playbooks` step. `add` and `update --check` act
only on the person's recorded yes: with none they record the no, write nothing and read no source.
Fixtures in `tmp_path` only: invented data (`example.com`), stub fetchers, no network, no model.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import socket
import subprocess  # nosec B404 - runs the command itself with a fixed argument list
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_packs  # noqa: E402
import packs  # noqa: E402

PID = "zz-shop"
REL = f"config/packs/{PID}"
SKILL = "# An invented skill\n\nDraft the shop's terms.\n"
MANIFEST = """format = 1
id = "zz-shop"
version = "{version}"
publisher = "Example Org"
tier = "curated"
licence = "MIT"
source = "https://example.com/packs/zz-shop.git"
kit = ">=0.60.0,<1.0.0"
as_of = "2026-11-20"
reviewed = "2026-11-21 by maintainers"
kinds = ["skills"]

[permissions]

[files]
"skills/shop/SKILL.md" = "{sha}"
"""


def stub_pack(base: Path, version: str = "1.2.0", skill: str = SKILL) -> Path:
    """A well-formed pack folder at BASE (any name), one skill."""
    (base / "skills" / "shop").mkdir(parents=True, exist_ok=True)
    (base / "skills" / "shop" / "SKILL.md").write_text(skill, encoding="utf-8")
    sha = hashlib.sha256(skill.encode()).hexdigest()
    text = MANIFEST.format(version=version, sha=sha)
    (base / check_packs.MANIFEST).write_text(text, encoding="utf-8")
    return base


def use_line(root: Path, version: str = "1.2.0") -> str:
    digest = check_packs.digest(root / REL / check_packs.MANIFEST)
    return f'{{ id = "{PID}", version = "{version}", sha256 = "{digest}" }}'


def locked(tmp_path: Path, use: bool = True) -> Path:
    """A project with the stub pack in `[packs] use` and in the lock, as `add` leaves it."""
    stub_pack(tmp_path / REL)
    (tmp_path / packs.LOCK).write_text(packs.lock_text([packs.lock_entry(tmp_path / REL)]))
    table = f"[packs]\nuse = [{use_line(tmp_path)}]\n" if use else ""
    (tmp_path / "agk.toml").write_text(f'review_mode = "solo"\n{table}', encoding="utf-8")
    return tmp_path


def scannable(root: Path) -> None:
    """Rule 6 (brief #2034): the outbound guard fails closed without a neutrality list and git."""
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "neutrality.txt").write_text("# none\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - no network


def said(tmp_path: Path, words: str) -> Path:
    path = tmp_path / "said.txt"
    path.write_text(words, encoding="utf-8")
    return path


class Calls:
    """A stub fetcher, tag lister and recorder: each call is kept, nothing is read."""

    def __init__(self, source: Path | None = None, tags=()):
        self.fetched, self.listed, self.notes = [], [], []
        self.source, self.tags = source, list(tags)

    def fetch(self, source, tag, dest):
        self.fetched.append((source, tag))
        if self.source is None:
            return False
        shutil.copytree(self.source, dest)
        return True

    def list_tags(self, source):
        self.listed.append(source)
        return self.tags

    def record(self, root, text):
        self.notes.append(text)
        return 0, ["recorded"]


@pytest.fixture
def no_socket(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_ac3_a_locked_pack_in_use_verifies_offline(tmp_path, no_socket):
    """REQ-084 AC3: SPEC-0077 rule 4 (verify reads files only; the playbooks step passes)."""
    root = locked(tmp_path)
    assert packs.check(root) == []
    assert check_packs.findings(root) == []
    assert packs.main(["verify", "--root", str(root)]) == 0


def test_ac3_no_table_no_lock_prints_none_in_use(tmp_path, capsys):
    """REQ-084 AC3: SPEC-0077 rule 4 (with no `[packs]` table and no lock nothing is in use)."""
    assert packs.main(["verify", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "ok packs: none in use\n"


@pytest.mark.parametrize(
    ("change", "line"),
    [
        ("byte", f"rule 4: {REL}: a locked file's SHA-256 differs (key: files)"),
        ("extra", f"rule 4: {REL}: a file the lock does not hold (key: files)"),
        ("gone", f"rule 4: {REL}: a lock entry's pack folder is missing (key: pack)"),
        ("unused", f"rule 4: {REL}: a locked pack is not listed in use (setting: packs.use)"),
        ("unlocked", f"rule 4: {REL}: a use entry the lock does not hold (setting: packs.use)"),
        ("version", f"rule 4: {REL}: a use entry differs from the lock (setting: packs.use)"),
    ],
)
def test_ac3_each_verify_failure_names_the_rule_and_the_pack(tmp_path, change, line):
    """REQ-084 AC3: SPEC-0077 rule 4 (each failure of answer 1, never a value)."""
    root = locked(tmp_path)
    skill = root / REL / "skills" / "shop" / "SKILL.md"
    if change == "byte":
        skill.write_bytes(skill.read_bytes() + b"!")
    elif change == "extra":
        (root / REL / "skills" / "shop" / "notes.md").write_text("x\n", encoding="utf-8")
    elif change == "gone":
        shutil.rmtree(root / REL)
    elif change == "unused":
        (root / "agk.toml").write_text("[packs]\nuse = []\n", encoding="utf-8")
    elif change == "unlocked":
        (root / packs.LOCK).write_text("", encoding="utf-8")
    else:  # the folder and the use entry moved on, the lock did not
        stub_pack(root / REL, version="1.3.0")
        (root / "agk.toml").write_text(f"[packs]\nuse = [{use_line(root, '1.3.0')}]\n")
    assert line in packs.check(root) and line in check_packs.findings(root)
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(KIT_ROOT / "scripts/agk/packs.py"), "verify", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1 and f"FAIL packs: {line}" in proc.stdout
    assert hashlib.sha256(SKILL.encode()).hexdigest() not in proc.stdout
    step = subprocess.run(  # nosec B603 - the playbooks step: the resolver may stop it first
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_playbooks.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    fails = [x for x in step.stdout.splitlines() if x.startswith("FAIL playbooks: ")]
    assert step.returncode == 1 and fails and all("packs" in x for x in fails)


@pytest.mark.parametrize("text", ["[[pack]\n", 'pack = "zz"\n', '[[pack]]\nid = "Zz Bad"\n'])
def test_ac3_a_lock_out_of_form_is_named_by_its_path_class(tmp_path, text):
    """REQ-084 AC3: SPEC-0077 rule 4 (a lock that is not TOML, or out of form, never its text)."""
    root = locked(tmp_path)
    (root / packs.LOCK).write_text(text, encoding="utf-8")
    lines = packs.check(root)
    assert lines == [
        "rule 4: config/packs.lock: the lock is not readable or out of form (key: pack)"
    ]


def test_ac3_add_from_a_folder_on_a_yes_writes_the_folder_and_the_lock(tmp_path, capsys):
    """REQ-084 AC3: SPEC-0077 rule 4 (copied after its checks, the lock written, use printed)."""
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    scannable(tmp_path)
    calls = Calls(stub_pack(tmp_path / "outside" / "anything"))
    code, lines = packs.add(
        tmp_path,
        "outside/anything",
        said(tmp_path, "yes"),
        "2026-11-27T10:00Z",
        fetch=calls.fetch,
        record=calls.record,
    )
    assert code == 0 and calls.notes[0].startswith("pack-add: yes because the person said")
    assert (tmp_path / REL / "skills" / "shop" / "SKILL.md").read_text() == SKILL
    assert f"[packs] use: {use_line(tmp_path)}" in lines
    (tmp_path / "agk.toml").write_text(
        f'review_mode = "solo"\n[packs]\nuse = [{use_line(tmp_path)}]\n'
    )
    assert packs.check(tmp_path) == [] and check_packs.findings(tmp_path) == []
    code, lines = packs.add(
        tmp_path,
        "outside/anything",
        said(tmp_path, "yes"),
        "2026-11-27T10:01Z",
        fetch=calls.fetch,
        record=calls.record,
    )
    assert code == 1 and "(setting: packs.use)" in lines[-1]  # the same version: use update


@pytest.mark.parametrize("words", ["no", "yes, but not today", ""])
def test_ac3_add_and_update_check_without_a_yes_write_and_read_nothing(tmp_path, no_socket, words):
    """REQ-084 AC3: SPEC-0077 rule 4 (the no is recorded; no source is read, nothing written)."""
    root = locked(tmp_path)
    before = (root / packs.LOCK).read_bytes()
    calls = Calls(stub_pack(tmp_path / "outside" / "p"), tags=["1.9.0"])
    code, _ = packs.add(
        root,
        "https://example.com/zz.git",
        said(tmp_path, words),
        "T",
        tag="1.3.0",
        fetch=calls.fetch,
        record=calls.record,
    )
    assert code == 1 and calls.fetched == [] and calls.notes[0].startswith("pack-add: no because")
    code, _ = packs.update_check(
        root, said(tmp_path, words), "T", tags=calls.list_tags, record=calls.record
    )
    assert code == 1 and calls.listed == [] and (root / packs.LOCK).read_bytes() == before


def test_ac3_update_check_lists_newer_tags_and_changes_nothing(tmp_path):
    """REQ-084 AC3: SPEC-0077 rules 4 and 8 (only the newer exact tags; nothing written)."""
    root = locked(tmp_path)
    before = (root / packs.LOCK).read_bytes()
    calls = Calls(tags=["v1.1.0", "1.2.0", "main", "1.10.0", "v1.3.0"])
    code, lines = packs.update_check(
        root, said(tmp_path, "yes"), "T", tags=calls.list_tags, record=calls.record
    )
    assert code == 0 and lines[-1] == f"{PID} 1.2.0: newer 1.3.0, 1.10.0"
    assert calls.listed == ["https://example.com/packs/zz-shop.git"]
    assert (root / packs.LOCK).read_bytes() == before


@pytest.mark.parametrize(
    ("source", "tag", "code", "line"),
    [
        (
            "https://example.com/zz.git",
            None,
            2,
            "rule 4: a git source takes an exact tag (source: git)",
        ),
        (
            "https://example.com/zz.git",
            "main",
            2,
            "rule 4: a git source takes an exact tag (source: git)",
        ),
        (
            "https://example.com/zz.git",
            "1.2.0",
            4,
            "refused: the pack cannot be fetched (source: git)",
        ),
        ("missing/folder", None, 4, "refused: the pack cannot be fetched (source: folder)"),
    ],
)
def test_ac3_a_source_out_of_form_or_unreachable_writes_nothing(tmp_path, source, tag, code, line):
    """REQ-084 AC3: SPEC-0077 rule 4 (answer 5: a branch, a failed fetch; one line, no write)."""
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    calls = Calls()
    got, lines = packs.add(
        tmp_path,
        source,
        said(tmp_path, "yes"),
        "T",
        tag=tag,
        fetch=calls.fetch,
        record=calls.record,
    )
    assert (got, lines[-1]) == (code, line)
    assert not (tmp_path / "config").exists()


def test_ac3_a_pack_that_fails_its_check_is_never_copied(tmp_path):
    """REQ-084 AC3: SPEC-0077 rule 4 (answer 5: the copy happens only after every check passed)."""
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    bad = stub_pack(tmp_path / "outside" / "p")
    (bad / "skills" / "shop" / "SKILL.md").write_text("changed\n", encoding="utf-8")
    calls = Calls(bad)
    code, lines = packs.add(
        tmp_path, "outside/p", said(tmp_path, "yes"), "T", fetch=calls.fetch, record=calls.record
    )
    assert code == 1 and f"rule 3: {REL}: a listed file's SHA-256 differs (key: files)" in lines
    assert not (tmp_path / "config").exists()


def test_ac3_team_mode_counts_only_a_spec_approvers_yes(tmp_path, monkeypatch):
    """REQ-084 AC3: SPEC-0077 rule 4 (answer 4: `review_mode = "team"`, `--by` an approver)."""
    (tmp_path / "agk.toml").write_text('review_mode = "team"\n', encoding="utf-8")
    scannable(tmp_path)
    monkeypatch.setattr("reviewers.spec_approvers", lambda r: ["lead"])
    calls = Calls(stub_pack(tmp_path / "outside" / "p"))
    args = (tmp_path, "outside/p", said(tmp_path, "yes"), "T")
    code, lines = packs.add(*args, by="other", fetch=calls.fetch, record=calls.record)
    assert code == 2 and "spec_approvers" in lines[0] and calls.notes == []
    code, _ = packs.add(*args, by="lead", fetch=calls.fetch, record=calls.record)
    assert code == 0 and (tmp_path / packs.LOCK).is_file()


def test_ac3_a_builder_session_adds_no_pack(tmp_path, monkeypatch):
    """REQ-084 AC3: SPEC-0077 rule 4 (answer 4: the steward runs `add`, never a builder)."""
    monkeypatch.setenv("AGK_AGENT", "builder")
    calls = Calls(stub_pack(tmp_path / "outside" / "p"))
    code, lines = packs.add(
        tmp_path, "outside/p", said(tmp_path, "yes"), "T", fetch=calls.fetch, record=calls.record
    )
    assert code == 2 and "(setting: AGK_AGENT)" in lines[0] and calls.notes == []


def test_ac3_personal_mode_records_in_the_sidecar_and_posts_nothing(tmp_path):
    """REQ-084 AC3: SPEC-0077 rule 4 (answer 4: `[personal] forge = "files"`, nothing posted)."""
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n[personal]\nforge = "files"\n')
    scannable(tmp_path)
    calls = Calls(stub_pack(tmp_path / "outside" / "p"))
    code, _ = packs.add(tmp_path, "outside/p", said(tmp_path, "yes"), "T", fetch=calls.fetch)
    assert code == 0 and (tmp_path / packs.LOCK).is_file()
    assert "pack-add: yes" in (tmp_path / "docs/runs/steward/memory.md").read_text()


def test_ac3_the_class_stays_closed_only_packs_writes_the_lock():
    """REQ-084 AC3: SPEC-0077 rules 4 and 16 (answer 7: no other kit script writes a pack)."""
    writes = re.compile(r"copytree|write_text|write_bytes|\.rename\(|shutil\.move")
    named = re.compile(r"packs\.lock|check_packs\.FOLDER|config/packs")
    found = sorted(
        p.name
        for p in (KIT_ROOT / "scripts" / "agk").glob("*.py")
        if "packs.lock" in (text := p.read_text(encoding="utf-8"))
        or (named.search(text) and writes.search(text) and "copytree" in text)
    )
    assert found == ["packs.py"]


def test_ac3_update_check_reads_only_an_https_source(tmp_path):
    """REQ-084 AC3: SPEC-0077 rule 4 (a manifest `source` shaped as a git option runs nothing)."""
    root = locked(tmp_path)
    pwned = tmp_path / "pwned"
    manifest = root / REL / check_packs.MANIFEST
    hostile = f"--upload-pack=touch {pwned};"
    text = manifest.read_text(encoding="utf-8").replace(
        'source = "https://example.com/packs/zz-shop.git"', f'source = "{hostile}"'
    )
    manifest.write_text(text, encoding="utf-8")
    calls = Calls()
    code, lines = packs.update_check(root, said(tmp_path, "yes"), "T", record=calls.record)
    assert code == 2 and lines[-1] == f"{PID}: the source is not a public https URL (source: git)"
    assert packs.remote_tags(hostile) is None and not packs.fetch_source(
        hostile, "1.2.0", tmp_path / "x"
    )
    assert not pwned.exists() and hostile not in "\n".join(lines)


@pytest.mark.parametrize("shape", ["link", "name"])
def test_ac3_a_pack_with_a_symbolic_link_or_an_odd_name_is_never_copied(tmp_path, shape):
    """REQ-084 AC3: SPEC-0077 rule 4 (nothing outside the pack is read; the lock stays plain)."""
    (tmp_path / "agk.toml").write_text('review_mode = "solo"\n', encoding="utf-8")
    src = stub_pack(tmp_path / "outside" / "p")
    secret = tmp_path / "elsewhere.txt"
    secret.write_text("outside the pack\n", encoding="utf-8")
    if shape == "link":
        (src / "skills" / "shop" / "more.md").symlink_to(secret)
    else:
        (src / "skills" / "shop" / 'a "b".md').write_text("x\n", encoding="utf-8")
    calls = Calls()
    code, lines = packs.add(tmp_path, "outside/p", said(tmp_path, "yes"), "T", record=calls.record)
    want = f"rule 4: {REL}: the pack holds a symbolic link or a file name out of form (key: files)"
    assert (code, lines[-1]) == (1, want)
    assert not (tmp_path / "config").exists()
