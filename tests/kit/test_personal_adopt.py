"""SPEC-0041 build (g), part 2: `/agk:personal-adopt` drafts records with citations that exist (brief #1504).

Advances REQ-048 (AC2: the model's reading of the code becomes cited Draft and Proposed records in
the sidecar for the person to confirm, and every uncited claim is refused with its position).

Rule 13: `personal_adopt.py check|render` refuses each claim whose citation `path:start-end@blob`
does not exist in the product clone, printing the rule and the claim's position, never its text.
Rule 14: the claims left are rendered as `planned` requirements with a `Source:` line, `Draft` specs
and `Proposed` ADRs with `- Kind: recorded`, numbered from `common.next_free_ids`, in one sidecar
commit. Rules 4 and 28: nothing is written in the clone, nothing is quoted past `quote_lines` and
the data guard scans each rendered file. Invented repositories and sidecars only; no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import personal_adopt as pa  # noqa: E402
import personal_state as ps  # noqa: E402

PERSON = "member-example-1"
TODAY = "2026-11-18"
CART = "".join(f"line {n} of the cart\n" for n in range(1, 21))
CART = CART.replace("line 12 of the cart", "def empty_cart(cart): cart.items.clear()")
STATEMENT = "A customer can empty the cart in one step"
FAKE_BLOB = "0" * 39 + "1"
SECRET = "AKIA" + "Z7Q3XK2M5NWP4R6T"  # an invented access key id, the shape gitleaks finds


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(root: Path, subject: str = "change") -> str:
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", subject)  # fmt: skip
    return git(root, "rev-parse", "HEAD")


def product(tmp_path: Path) -> Path:
    """An invented product clone: one tracked file of 20 lines, committed, and one untracked file."""
    root = tmp_path / "clone"
    (root / "src").mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    (root / "src" / "cart.py").write_text(CART, encoding="utf-8")
    commit(root)
    (root / "notes.txt").write_text("untracked\n", encoding="utf-8")
    return root


def blob(root: Path, rel: str = "src/cart.py") -> str:
    return git(root, "rev-parse", f"HEAD:{rel}")


def sidecar_of(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "home" / "projects" / "clone-000000000000"
    ps.make_sidecar(path, PERSON)
    if extra:
        (path / "agk.toml").write_text((path / "agk.toml").read_text("utf-8") + extra, "utf-8")
        commit(path, "settings")
    return path


def cite(root: Path, start: int = 10, end: int = 14, rel: str = "src/cart.py", sha: str = "") -> str:
    return f"{rel}:{start}-{end}@{sha or blob(root, rel)}"


def claim(citation: str, statement: str = STATEMENT, **more) -> dict:
    return {"statement": statement, "citations": [citation], **more}


def proposals(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "proposals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def run(*args: str | Path) -> tuple[int, list[str]]:
    lines: list[str] = []
    code = pa.main([str(a) for a in args], out=lines.append)
    return code, lines


def snapshot(root: Path) -> dict[str, str]:
    """Every file of the clone's work tree and of its `.git/`, by content hash."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def full(root: Path) -> dict:
    good = cite(root)
    return {
        "requirements": [{"title": "A customer can empty the cart", "claims": [claim(good)]}],
        "specs": [{"title": "Emptying the cart", "requirements": [0], "claims": [claim(good)]}],
        "adrs": [
            {"title": "The cart empties in one step", "specs": [0], "requirements": [0],
             "claims": [claim(good, "The cart is emptied by clearing its items", verify=True)]},
        ],
    }  # fmt: skip


@pytest.mark.parametrize(
    ("make", "why"),
    [
        (lambda r: cite(r, rel="notes.txt", sha=FAKE_BLOB), "the path is not tracked"),
        (lambda r: cite(r, sha=FAKE_BLOB), "the blob is not that path's blob at a commit"),
        (lambda r: cite(r, 18, 21), "the range lies outside the blob"),
        (lambda r: cite(r, 0, 3), "the range lies outside the blob"),
        (lambda r: "src/cart.py:10-14", "not a citation of the form path:start-end@blob"),
    ],
)
def test_a_citation_that_does_not_exist_is_refused_by_its_position(tmp_path, make, why):
    """REQ-048 AC2: SPEC-0041 rule 13 (each refusal names the rule and the position, never the text)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    data = {"requirements": [{"title": "A cart", "claims": [claim(cite(root)), claim(make(root))]}]}
    code, out = run("check", proposals(tmp_path, data), "--clone", root, "--sidecar", side)
    assert code == 1
    assert out[0] == f"refused: requirements[0].claims[1]: SPEC-0041 rule 13: {why}"
    assert not any(STATEMENT in line or "notes.txt" in line for line in out)
    assert out[-1] == "check: 1 of 2 claims refused"


def test_a_blob_of_an_older_commit_is_accepted(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 13 (the blob is that path's blob at a commit of the product)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    old = blob(root)
    (root / "src" / "cart.py").write_text(CART + "line 21\n", encoding="utf-8")
    commit(root)
    data = {"requirements": [{"title": "A cart", "claims": [claim(cite(root, sha=old))]}]}
    assert run("check", proposals(tmp_path, data), "--clone", root, "--sidecar", side) == (
        0, ["check: 0 of 1 claims refused"]
    )  # fmt: skip


def test_render_writes_cited_records_in_one_sidecar_commit_and_lists_confirm(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 14 (planned with Source, Draft, Proposed with Kind: recorded)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    status, head = git(root, "status", "--porcelain"), git(side, "rev-parse", "HEAD")
    before = snapshot(root)
    code, out = run("render", proposals(tmp_path, full(root)), "--clone", root, "--sidecar", side,
                    "--today", TODAY)  # fmt: skip
    assert code == 0, out
    assert "rendered: REQ-101, SPEC-0001, ADR-0001" in out
    assert any(line.endswith(f"personal.py confirm REQ-101 --sidecar {side}") for line in out)
    assert git(side, "rev-parse", "HEAD~1") == head and not git(side, "status", "--porcelain")
    reqs = (side / "docs" / "requirements.md").read_text(encoding="utf-8")
    assert f"### REQ-101 — A customer can empty the cart\n\n- Acceptance: AC1 {STATEMENT}\n" in reqs
    assert f"- Source: observed in code at {cite(root)}\n- Status: planned\n" in reqs
    spec = (side / "docs" / "specs" / "0001-emptying-the-cart.md").read_text(encoding="utf-8")
    assert "- Status: Draft\n" in spec and "- Requirements: REQ-101\n" in spec
    adr = (side / "docs" / "adr" / "0001-the-cart-empties-in-one-step.md").read_text("utf-8")
    assert "- Status: Proposed\n" in adr and "- Kind: recorded\n" in adr
    assert f"- Date: {TODAY}\n" in adr and "- Related: SPEC-0001\n" in adr
    assert "clearing its items (verify) (observed in code at" in adr
    assert snapshot(root) == before and git(root, "status", "--porcelain") == status


def test_rendered_records_pass_the_sidecar_checks(tmp_path):
    """REQ-048 AC2: SPEC-0041 rules 2 and 14 (the sidecar's file checks run unchanged on them)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    assert run("render", proposals(tmp_path, full(root)), "--clone", root, "--sidecar", side)[0] == 0
    for check in ("check_adrs", "check_requirements", "check_specs"):
        done = subprocess.run(  # nosec B603 - the kit's own check, fixed argument list
            [sys.executable, str(SCRIPTS / f"{check}.py")], cwd=side, capture_output=True,
            text=True, check=False, env={**os.environ, "CLAUDECODE": ""},
        )  # fmt: skip
        assert done.returncode == 0, (check, done.stdout, done.stderr)


def test_a_proposal_whose_every_claim_is_refused_renders_nothing(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 13 (nothing of a proposal whose every claim is refused)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    head = git(side, "rev-parse", "HEAD")
    data = {"requirements": [{"title": "A cart", "claims": [claim(cite(root, sha=FAKE_BLOB))]}]}
    code, out = run("render", proposals(tmp_path, data), "--clone", root, "--sidecar", side)
    assert code == 1 and out[-1] == "render: nothing rendered; 1 of 1 claims refused"
    assert git(side, "rev-parse", "HEAD") == head and not git(side, "status", "--porcelain")


def test_a_mix_renders_only_the_good_claims(tmp_path):
    """REQ-048 AC2: SPEC-0041 rules 13 and 14 (a refused claim is left out, the rest rendered)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    data = full(root)
    data["requirements"][0]["claims"].append(claim(cite(root, 30, 31), "A refused point"))
    code, out = run("render", proposals(tmp_path, data), "--clone", root, "--sidecar", side)
    assert code == 0 and out[0].startswith("refused: requirements[0].claims[1]: SPEC-0041 rule 13")
    assert "render: 1 of 4 claims refused" in out
    assert "A refused point" not in (side / "docs" / "requirements.md").read_text(encoding="utf-8")


def test_a_code_excerpt_is_refused_unless_quote_lines_allows_it(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 28 (`[personal] quote_lines`, 0 by default)."""
    root = product(tmp_path)
    quoted = "It runs def empty_cart(cart): cart.items.clear() to empty the cart"
    data = {"requirements": [{"title": "A cart", "claims": [claim(cite(root), quoted)]}]}
    side = sidecar_of(tmp_path)
    code, out = run("check", proposals(tmp_path, data), "--clone", root, "--sidecar", side)
    assert code == 1 and out[0] == (
        "refused: requirements[0].claims[0]: SPEC-0041 rule 28: a code excerpt beyond the "
        "setting personal.quote_lines"
    )
    allowed = sidecar_of(tmp_path / "two", "quote_lines = 1\n")
    assert run("check", proposals(tmp_path, data), "--clone", root, "--sidecar", allowed)[0] == 0


def test_a_secret_shaped_string_is_refused_naming_the_path_class(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 28 (the data guard scans every rendered text first)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    data = {"adrs": [{"title": "Keys", "claims": [claim(cite(root), f"The key is {SECRET}")]}]}
    code, out = run("render", proposals(tmp_path, data), "--clone", root, "--sidecar", side)
    assert code == 1 and out[0] == (
        "refused: adrs[0].claims[0]: SPEC-0041 rule 28: the data guard finds a secret or "
        "personal value (path class docs/adr/)"
    )
    assert not any(SECRET in line for line in out)
    assert SECRET not in json.dumps(snapshot(side))


def test_a_second_run_continues_the_numbers_and_duplicates_nothing(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 14 (numbers from `common.next_free_ids` on the sidecar)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    first = proposals(tmp_path, full(root))
    assert run("render", first, "--clone", root, "--sidecar", side)[0] == 0
    code, out = run("render", first, "--clone", root, "--sidecar", side)
    assert code == 0 and "render: nothing new; every record is already in the sidecar" in out
    more = full(root)
    more["requirements"][0]["title"] = "A customer sees the cart"
    code, out = run("render", proposals(tmp_path, more), "--clone", root, "--sidecar", side)
    assert code == 0 and "rendered: REQ-102" in out
    reqs = (side / "docs" / "requirements.md").read_text(encoding="utf-8")
    assert reqs.count("### REQ-101 ") == 1 and reqs.count("### REQ-102 ") == 1
    assert len(list((side / "docs" / "specs").glob("*.md"))) == 1


@pytest.mark.parametrize(
    "data",
    ["[]", '{"requirements": [{"title": "", "claims": []}]}', '{"other": []}', "{nope"],
)
def test_a_proposals_file_of_another_shape_is_refused_whole(tmp_path, data):
    """REQ-048 AC2: SPEC-0041 rule 13 (the proposals are JSON of one shape)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    path = tmp_path / "proposals.json"
    path.write_text(data, encoding="utf-8")
    code, out = run("check", path, "--clone", root, "--sidecar", side)
    assert code == 1 and out == ["refused: the proposals file is not of the shape of SPEC-0041 rule 13"]


def test_render_refuses_a_dirty_sidecar_and_usage_errors(tmp_path):
    """REQ-048 AC2: SPEC-0041 rule 14 (one sidecar commit from a clean sidecar)."""
    root, side = product(tmp_path), sidecar_of(tmp_path)
    (side / "docs" / "adr" / "stray.md").write_text("x\n", encoding="utf-8")
    code, out = run("render", proposals(tmp_path, full(root)), "--clone", root, "--sidecar", side)
    assert code == 1 and out == ["refused: render needs a clean sidecar work tree (SPEC-0041 rule 14)"]
    assert run("nothing")[0] == 2 and run("check")[0] == 2


def test_the_script_is_standard_library_only_and_shipped():
    """REQ-048 AC2: SPEC-0041 rule 28 (no network library) and rule 26 (shipped in the plugin)."""
    text = (SCRIPTS / "personal_adopt.py").read_text(encoding="utf-8")
    for name in ("socket", "http", "urllib", "ssl", "ftplib", "smtplib"):
        assert f"import {name}" not in text and f"from {name}" not in text
    root = SCRIPTS.parents[1]
    manifest = json.loads((root / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/personal_adopt.py" in manifest["verbatim"]
    skill = (root / "skills" / "personal-adopt" / "SKILL.md").read_text(encoding="utf-8")
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/agk/personal_adopt.py" in skill
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/agk/survey.py" in skill
    assert "Never run `personal.py confirm`" in skill
