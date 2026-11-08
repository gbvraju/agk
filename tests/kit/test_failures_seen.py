"""Seen before: a new failure names the earlier fixed failures it matches (SPEC-0046 rule 9).

REQ-053 AC6, brief #756 (build (d) of SPEC-0046, ADR-0303). `failures.py seen --signature SIG
--test ID` reads the closed `found-bug` issues of the project's own repository that hold a fix
record and the merged pull requests that name them with `Fixes-failure:`, through a `gh` stub on
`PATH` serving saved responses, and prints at most three lines, exact signature first, then the
same test id, newest first within each; never by text similarity. GET only, no file written,
invented data (`example.com`), no network. The tests were written first (answer 3)."""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import failures
import pytest

REPO = "acme/widgets"
SIG = "0123456789ab"
NEAR = "0123456789ac"  # one character away from SIG: similar, but a different signature
OTHER = "fedcba987654"
TEST = "tests/test_shop.py::test_cart"
STUB = '''#!/usr/bin/env python3
"""A gh stub: serves GET fixtures by endpoint (query ignored), logs every call."""
import json, os, sys
args = sys.argv[1:]
root = os.environ["GH_STUB_DIR"]
with open(os.path.join(root, "calls.log"), "a") as log:
    log.write(json.dumps(args) + "\\n")
method = args[args.index("--method") + 1] if "--method" in args else "GET"
endpoint = next(a for a in args[1:] if a.startswith("repos/"))
if method != "GET":
    sys.exit(1)
fixtures = json.load(open(os.path.join(root, "fixtures.json")))
value = fixtures.get(endpoint.split("?")[0])
if value is None:
    sys.stderr.write("gh: Not Found (HTTP 404)\\n")
    sys.exit(1)
print(json.dumps(value))
'''


def issue(number: int, sig: str, test: str = TEST, record: bool = True, **extra) -> dict:
    lines = [f"Failure-signature: {sig}", f"Test: {test}"]
    if record:
        lines += [
            f"Symptom: the cart total is off by one on issue {number}",
            "Cause: the discount was applied twice",
            "Reproduce: pytest tests/test_shop.py -k cart",
            "Fixed-by: apply the discount once, in the order step",
        ]
    item = {
        "number": number,
        "state": "closed",
        "labels": [{"name": "found-bug"}],
        "body": "\n".join(lines),
        "html_url": f"https://example.com/{REPO}/issues/{number}",
    }
    item.update(extra)
    return item


def pull(number: int, fixes: int, merged: str | None = "2026-11-01T10:00:00Z") -> dict:
    body = f"Summary: fixes the cart\nFixes-failure: #{fixes}\nSymptom: the cart total is off"
    return {"number": number, "state": "closed", "merged_at": merged, "body": body}


@pytest.fixture
def gh(tmp_path: Path, monkeypatch):
    stub = tmp_path / "stub"
    stub.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe = bin_dir / "gh"
    exe.write_text(STUB, encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    proj = tmp_path / "proj"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=True)  # nosec B603 B607
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(proj), "remote", "add", "origin", f"https://github.com/{REPO}.git"],
        check=True,
    )
    monkeypatch.chdir(proj)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_STUB_DIR", str(stub))
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    class Gh:
        dir = stub
        root = proj

        def serve(self, issues: list, pulls: list) -> None:
            fixtures = {}
            if issues is not None:
                fixtures[f"repos/{REPO}/issues"] = issues
            if pulls is not None:
                fixtures[f"repos/{REPO}/pulls"] = pulls
            (stub / "fixtures.json").write_text(json.dumps(fixtures), encoding="utf-8")

        def calls(self) -> list[list[str]]:
            log = stub / "calls.log"
            return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    return Gh()


def seen(capsys, sig: str = SIG, test: str = TEST) -> tuple[int, list[str]]:
    code = failures.main(["seen", "--signature", sig, "--test", test])
    return code, [ln for ln in capsys.readouterr().out.splitlines() if ln]


def test_req_053_ac6_exact_signature_before_same_test_newest_first(gh, capsys):
    gh.serve(
        [issue(30, OTHER), issue(12, SIG), issue(20, SIG), issue(40, OTHER, test="t::other")],
        [pull(31, 30), pull(13, 12), pull(21, 20), pull(41, 40)],
    )
    code, lines = seen(capsys)
    assert code == 0
    assert lines == [
        "seen before: #20 the cart total is off by one on issue 20; fixed by #21",
        "seen before: #12 the cart total is off by one on issue 12; fixed by #13",
        "seen before: #30 the cart total is off by one on issue 30; fixed by #31",
    ]


def test_req_053_ac6_at_most_three_lines(gh, capsys):
    numbers = [10, 11, 12, 13, 14]
    gh.serve([issue(n, SIG) for n in numbers], [pull(n + 100, n) for n in numbers])
    _, lines = seen(capsys)
    assert [ln.split()[2] for ln in lines] == ["#14", "#13", "#12"]


def test_req_053_ac6_an_issue_without_a_fix_record_is_skipped(gh, capsys):
    gh.serve(
        [issue(12, SIG), issue(20, SIG, record=False), issue(25, SIG)],
        [pull(13, 12), pull(21, 20)],  # 25 has a record but no merged pull request names it
    )
    _, lines = seen(capsys)
    assert lines == ["seen before: #12 the cart total is off by one on issue 12; fixed by #13"]


def test_req_053_ac6_a_similar_but_different_signature_is_not_matched(gh, capsys):
    gh.serve(
        [issue(12, NEAR, test="tests/test_shop.py::test_cart_total"), issue(14, SIG[:-1], test="tests/test_shop.py::test_cart[2]")],
        [pull(13, 12), pull(15, 14)],
    )
    code, lines = seen(capsys)
    assert (code, lines) == (0, [])


def test_req_053_ac6_open_issues_other_labels_and_unmerged_pulls_do_not_count(gh, capsys):
    gh.serve(
        [
            issue(12, SIG, state="open"),
            issue(14, SIG, labels=[{"name": "agk-brief"}]),
            issue(16, SIG, pull_request={"url": "https://example.com/pr/16"}),
            issue(18, SIG),
        ],
        [pull(13, 12), pull(15, 14), pull(17, 16), pull(19, 18, merged=None)],
    )
    assert seen(capsys)[1] == []


def test_req_053_ac6_get_only_on_the_own_repository_and_no_file_written(gh, capsys):
    gh.serve([issue(12, SIG)], [pull(13, 12)])
    before = sorted(p.name for p in gh.root.iterdir())
    seen(capsys)
    calls = gh.calls()
    assert calls
    for call in calls:
        assert call[call.index("--method") + 1] == "GET"
        assert next(a for a in call if a.startswith("repos/")).startswith(f"repos/{REPO}/")
    assert sorted(p.name for p in gh.root.iterdir()) == before


@pytest.mark.parametrize("missing", ["issues", "pulls"])
def test_req_053_ac6_a_failed_read_is_said_never_printed_as_no_match(gh, capsys, missing):
    gh.serve(
        None if missing == "issues" else [issue(12, SIG)],
        None if missing == "pulls" else [pull(13, 12)],
    )
    code, lines = seen(capsys)
    assert code == 4
    assert len(lines) == 1
    assert "cannot be read" in lines[0]
    assert not any(ln.startswith("seen before") for ln in lines)


def test_req_053_ac6_a_bad_signature_is_a_usage_error(gh, capsys):
    gh.serve([], [])
    code, lines = seen(capsys, sig="not-a-sig")
    assert code == 2
    assert "not-a-sig" not in "\n".join(lines)
    assert gh.calls() == []
