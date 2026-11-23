"""REQ-063: brief #1835 (ADR-0764): an adopted project's whole git history is scanned for secrets
once, offline, each finding named by rule id and path class with the leaked-secret page, the run
recorded in `config/agk-baseline/history-scan.json` (or the sidecar's `records/`), and doctor's
line says when it never ran, ran incomplete or found something.

A stub `gitleaks` on PATH records its argument list and writes a fixed report whose `Secret`,
`Match`, `Message`, `Author` and `Email` carry markers that must never be printed or recorded.
Invented data only (example.com); no network.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import stat
import subprocess  # nosec B404 - fixed git argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import history_scan  # noqa: E402

MARKERS = ("MARKER-SECRET-0001", "MARKER-MATCH", "MARKER-MESSAGE", "MARKER-AUTHOR", "marker@")
REPORT = [
    {"RuleID": "aws-access-token", "File": "config/settings.py"},
    {"RuleID": "aws-access-token", "File": "config/old/keys.py"},
    {"RuleID": "generic-api-key", "File": "setup.cfg"},
]
MARKED = {
    "Secret": MARKERS[0],
    "Match": "key = MARKER-MATCH",
    "Message": "MARKER-MESSAGE add key",
    "Author": "MARKER-AUTHOR",
    "Email": "marker@example.com",
    "Commit": "0123456789abcdef0123456789abcdef01234567",
}
REPORT = [{**row, **MARKED} for row in REPORT]
STUB = """#!{python}
import json, os, sys, time
args = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
if args[:1] == ["version"]:
    print(os.environ.get("STUB_VERSION", "8.30.1"))
    sys.exit(0)
mode = os.environ.get("STUB_MODE", "findings")
path = args[args.index("--report-path") + 1]
print("MARKER-SECRET-0001 on stdout")
print("MARKER-MATCH on stderr", file=sys.stderr)
if mode == "sleep":
    time.sleep(30)
if mode == "exit2":
    sys.exit(2)
if mode == "badjson":
    open(path, "w").write("not json")
    sys.exit(1)
rows = json.loads(os.environ["STUB_REPORT"]) if mode == "findings" else []
open(path, "w").write(json.dumps(rows))
sys.exit(1 if rows else 0)
"""


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def project(path: Path, commit: bool = True) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.com"), ("user.name", "t")):
        git(path, "config", key, value)
    git(path, "config", "commit.gpgsign", "false")
    (path / "config").mkdir()
    (path / "config" / "protected-paths.txt").write_text("config/\n", encoding="utf-8")
    (path / "agk.toml").write_text('mode = "adopt"\n', encoding="utf-8")
    if commit:
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "initial")
    return path


@pytest.fixture
def stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stub gitleaks first on PATH; its log is returned."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe = bin_dir / "gitleaks"
    exe.write_text(STUB.format(python=sys.executable), encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "stub.log"
    log.write_text("", encoding="utf-8")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("STUB_LOG", str(log))
    monkeypatch.setenv("STUB_REPORT", json.dumps(REPORT))
    monkeypatch.delenv("STUB_MODE", raising=False)
    return log


def scans(log: Path) -> list[list[str]]:
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if r[:1] == ["git"]]


def record(root: Path) -> dict:
    return json.loads((root / history_scan.RECORD).read_text(encoding="utf-8"))


def test_req063_the_scan_reads_the_whole_history_never_a_range(tmp_path, stub):
    root = project(tmp_path / "svc")
    history_scan.run(root)
    (args,) = scans(stub)
    assert args[:2] == ["git", "--no-banner"] and "--redact" in args
    assert "--log-opts=--all" in args and not [a for a in args if ".." in a]
    report = Path(args[args.index("--report-path") + 1])
    assert root not in report.parents and not report.exists()  # made outside, removed after
    assert args[-1] == str(root)


def test_req063_findings_name_rule_and_class_with_the_runbook_never_a_value(tmp_path, stub):
    root = project(tmp_path / "svc")
    code, lines = history_scan.run(root, write=True)
    assert code == 1
    assert lines[:2] == [
        "history scan: aws-access-token 2 (path class: config/)",
        "history scan: generic-api-key 1 (path class: (repository root))",
    ]
    assert lines[-1] == history_scan.LEAK_RUNBOOK
    saved = record(root)
    text = (root / history_scan.RECORD).read_text(encoding="utf-8")
    for marker in (*MARKERS, "0123456789abcdef0123456789abcdef01234567", "settings.py"):
        assert marker not in "\n".join(lines) and marker not in text
    assert sorted(saved) == [
        "commits", "findings", "head", "note", "outcome", "reason", "scanned", "tool"
    ]  # fmt: skip
    assert saved["outcome"] == "findings" and saved["commits"] == 1
    assert (
        saved["tool"] == "gitleaks 8.30.1"
        and saved["head"] == git(root, "rev-parse", "HEAD").strip()
    )
    assert saved["findings"] == [
        {"class": "config/", "count": 2, "rule": "aws-access-token"},
        {"class": "(repository root)", "count": 1, "rule": "generic-api-key"},
    ]
    assert text.endswith("}\n") and "\r" not in text


def test_req063_a_complete_record_is_never_rewritten_and_nothing_scans_again(tmp_path, stub):
    root = project(tmp_path / "svc")
    history_scan.run(root, write=True)
    before = (root / history_scan.RECORD).read_bytes()
    code, lines = history_scan.run(root, write=True)
    assert code == 1 and len(scans(stub)) == 1
    assert lines == [f"history scan: recorded {record(root)['scanned']} (findings)"]
    assert (root / history_scan.RECORD).read_bytes() == before


def test_req063_clean_history_exit_0_and_an_incomplete_record_is_replaced(
    tmp_path, stub, monkeypatch
):
    root = project(tmp_path / "svc")
    monkeypatch.setenv("STUB_MODE", "sleep")
    monkeypatch.setattr(history_scan, "TIMEOUT", 1)
    code, lines = history_scan.run(root, write=True)
    assert code == 1 and lines[-1] == "history scan: incomplete (not finished within 1 s)"
    assert record(root)["outcome"] == "incomplete"
    monkeypatch.setenv("STUB_MODE", "clean")
    code, lines = history_scan.run(root, write=True)
    assert (code, lines) == (0, ["history scan: clean (1 commits, gitleaks 8.30.1)"])
    assert record(root)["outcome"] == "clean" and record(root)["findings"] == []


def test_req063_a_shallow_clone_is_scanned_and_recorded_incomplete(tmp_path, stub):
    origin = project(tmp_path / "origin")
    (origin / "app.py").write_text("print('example.com')\n", encoding="utf-8")
    git(origin, "add", "-A")
    git(origin, "commit", "-q", "-m", "second")
    shallow = tmp_path / "shallow"
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "clone", "-q", "--depth", "1", origin.as_uri(), str(shallow)], check=True
    )
    code, lines = history_scan.run(shallow, write=True)
    assert code == 1 and len(scans(stub)) == 1
    assert "history scan: aws-access-token 2 (path class: config/)" in lines
    assert record(shallow)["outcome"] == "incomplete"
    assert record(shallow)["reason"] == history_scan.SHALLOW


def test_req063_no_gitleaks_is_never_a_pass(tmp_path, monkeypatch):
    root = project(tmp_path / "svc")
    monkeypatch.setattr(history_scan.shutil, "which", lambda _name: None)
    code, lines = history_scan.run(root, write=True)
    assert code == 1
    assert lines == [
        "history scan: not run: gitleaks is not installed (tool: gitleaks); "
        + history_scan.GITLEAKS_INSTALL
        + "; run history_scan.py run --write again after"
    ]
    assert not (root / history_scan.RECORD).exists()


@pytest.mark.parametrize("mode", ["exit2", "badjson"])
def test_req063_a_failed_scanner_writes_no_record(tmp_path, stub, monkeypatch, mode):
    root = project(tmp_path / "svc")
    monkeypatch.setenv("STUB_MODE", mode)
    code, lines = history_scan.run(root, write=True)
    assert (code, lines) == (1, ["history scan: not run: the scanner failed (tool: gitleaks)"])
    assert not (root / history_scan.RECORD).exists()


def test_req063_no_commit_nothing_to_scan(tmp_path, stub):
    root = project(tmp_path / "svc", commit=False)
    assert history_scan.run(root, write=True) == (0, ["history scan: nothing to scan (no commit)"])
    assert not scans(stub) and not (root / history_scan.RECORD).exists()


def test_req063_another_version_and_an_ignore_file_are_named(tmp_path, stub, monkeypatch):
    root = project(tmp_path / "svc")
    (root / ".gitleaksignore").write_text("", encoding="utf-8")
    monkeypatch.setenv("STUB_VERSION", "v8.99.0")
    history_scan.run(root, write=True)
    assert record(root)["tool"] == "gitleaks 8.99.0"
    assert record(root)["note"] == "ignore file present"
    assert (root / ".gitleaksignore").read_text(encoding="utf-8") == ""


def test_req063_without_write_nothing_is_recorded_and_a_missing_folder_is_made(tmp_path, stub):
    root = project(tmp_path / "svc")
    history_scan.run(root)
    assert not (root / "config" / "agk-baseline").exists()
    history_scan.run(root, write=True)
    assert (root / history_scan.RECORD).is_file()


def test_req063_a_symlinked_record_folder_is_refused_never_followed(tmp_path, stub):
    root = project(tmp_path / "svc")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "config" / "agk-baseline").symlink_to(elsewhere, target_is_directory=True)
    code, lines = history_scan.run(root, write=True)
    assert code == 1 and lines[-1] == history_scan.SYMLINK
    assert not list(elsewhere.iterdir())


def test_req063_a_secret_shaped_rule_id_refuses_the_write_naming_the_kind(
    tmp_path, stub, monkeypatch
):
    root = project(tmp_path / "svc")
    fake = "AKIA" + "QYLPMN5HHHFPZAM2"  # built at run time, invented
    monkeypatch.setenv("STUB_REPORT", json.dumps([{"RuleID": fake, "File": "a.py"}]))
    code, lines = history_scan.run(root, write=True)
    assert code == 1 and fake not in "\n".join(lines)
    assert lines == ["history scan: record not written: it holds a secret shape (kind: SECRET)"]
    assert not (root / history_scan.RECORD).exists()


def test_req063_the_sidecar_holds_the_record_and_the_clone_none(tmp_path, stub):
    root = project(tmp_path / "svc")
    sidecar = tmp_path / "side"
    code, _ = history_scan.run(root, sidecar=sidecar, write=True)
    assert code == 1
    assert (sidecar / history_scan.PRIVATE).is_file()
    assert not (root / "config" / "agk-baseline").exists()
    assert stat.S_IMODE((sidecar / history_scan.PRIVATE).stat().st_mode) == 0o600


def test_req063_state_lines_for_doctor_and_status(tmp_path):
    path = tmp_path / "history-scan.json"
    assert history_scan.state(path) == ("warn", history_scan.NEVER)
    base = {"scanned": "2026-11-23", "commits": 4, "reason": "", "findings": []}
    path.write_text(json.dumps({**base, "outcome": "clean"}), encoding="utf-8")
    assert history_scan.state(path) == ("ok", "scanned 2026-11-23, 4 commits, no finding")
    path.write_text(
        json.dumps({**base, "outcome": "incomplete", "reason": "not finished within 600 s"}),
        encoding="utf-8",
    )
    assert history_scan.state(path) == (
        "warn",
        "incomplete (not finished within 600 s); run it again",
    )
    found = [
        {"rule": "aws-access-token", "class": "config/", "count": 2},
        {"rule": "generic-api-key", "class": "(repository root)", "count": 1},
    ]
    path.write_text(json.dumps({**base, "outcome": "findings", "findings": found}), "utf-8")
    level, text = history_scan.state(path)
    assert level == "warn" and text.startswith(
        "3 findings in history (aws-access-token, generic-api-key; "
        "path classes (repository root), config/); follow docs/runbooks/leaked-secret.md"
    )
    path.write_text("{not json", encoding="utf-8")
    assert history_scan.state(path) == ("warn", history_scan.UNREADABLE)


def test_req063_main_runs_with_root_and_write(tmp_path, stub, capsys):
    root = project(tmp_path / "svc")
    assert history_scan.main(["run", "--root", str(root), "--write"]) == 1
    out = capsys.readouterr().out
    assert "history scan: aws-access-token 2 (path class: config/)" in out
    assert not any(m in out for m in MARKERS)
    assert history_scan.main(["bogus"]) == 2


# Answer 10: the class stays closed. Each function under scripts/agk/ that builds a gitleaks
# argument list, with what it scans; a new one fails until it is named here.
GITLEAKS_CALLS = {
    ("prepush.py", "secret_scan"): "a range: merge base to head",
    ("history_scan.py", "scan"): "the whole history: --log-opts=--all",
    ("history_scan.py", "version"): "version only",
    ("doctor.py", "secret_scan_line"): "version only",
}


def gitleaks_calls() -> set[tuple[str, str]]:
    found = set()
    for path in sorted(SCRIPTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            for node in ast.walk(fn):
                if (
                    isinstance(node, ast.List)
                    and any(
                        isinstance(e, ast.Constant) and e.value in ("git", "version")
                        for e in node.elts
                    )
                    and any(isinstance(e, ast.Name) and e.id in ("tool", "exe") for e in node.elts)
                ):
                    found.add((path.relative_to(SCRIPTS).as_posix(), fn.name))
    return found


def test_req063_every_gitleaks_call_site_is_named():
    found = gitleaks_calls()
    unnamed = sorted(found - set(GITLEAKS_CALLS))
    assert not unnamed, f"a gitleaks call site not named in this test (file, function): {unnamed}"
    gone = sorted(set(GITLEAKS_CALLS) - found)
    assert not gone, f"a named gitleaks call site is gone (file, function): {gone}"
    scan = (SCRIPTS / "history_scan.py").read_text(encoding="utf-8")
    assert '"--log-opts=--all"' in scan


def real_gitleaks() -> str | None:
    named = os.environ.get("AGK_GITLEAKS")
    return named if named and Path(named).is_file() else shutil.which("gitleaks")


@pytest.mark.skipif(real_gitleaks() is None, reason="gitleaks is not installed here")
def test_req063_real_gitleaks_finds_a_key_removed_before_adoption_on_a_side_branch(
    tmp_path, monkeypatch
):
    exe = real_gitleaks()
    monkeypatch.setattr(history_scan.shutil, "which", lambda _name: exe)
    root = project(tmp_path / "svc")
    git(root, "checkout", "-q", "-b", "side")
    key = "AKIA" + "QYLPMN5HHHFPZAM2"  # invented, built at run time
    (root / "config" / "settings.py").write_text(f'KEY = "{key}"\n', encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "add")
    (root / "config" / "settings.py").write_text("KEY = ''\n", encoding="utf-8")
    git(root, "commit", "-q", "-am", "remove")
    git(root, "checkout", "-q", "main")
    code, lines = history_scan.run(root, write=True)
    assert code == 1, lines
    assert "history scan: aws-access-token 1 (path class: config/)" in lines
    assert key not in "\n".join(lines) and key not in (root / history_scan.RECORD).read_text()


def test_req063_the_runbook_sentence_is_prepush_s():
    import prepush  # noqa: PLC0415

    assert history_scan.LEAK_RUNBOOK == prepush.LEAK_RUNBOOK
