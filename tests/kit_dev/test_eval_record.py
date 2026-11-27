"""Tests of the eval record and the promotion it gates (SPEC-0077 rules 10, 15 and 16; REQ-084 AC7,
AC8; brief #2043 build (h), ADR-0847).

`eval_record.py write` turns build (g)'s saved runs into `docs/runs/evals/<date>.md`, naming each
regression beyond `tolerance`; `accept` sets it accepted only on the person's recorded yes; a kit
release and a curated pack need the last accepted record. Saved invented trees, no network, no
model.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_packs  # noqa: E402
import eval_record  # noqa: E402
import steward_owner  # noqa: E402

LAYERS = eval_record.LAYERS
DAY, LAST = "2026-11-27", "2026-11-20"
SAID_AT = "2026-11-27T19:30:00Z"


@pytest.fixture(autouse=True)
def no_socket(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.delenv("AGK_STEWARD_START", raising=False)


def put(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def kit(tmp_path: Path) -> Path:
    """A saved kit tree: the shipped rubric, a solo files-forge sidecar's settings."""
    root = tmp_path / "kit"
    put(root, "evals/rubric.toml", (KIT_ROOT / "evals" / "rubric.toml").read_text("utf-8"))
    put(root, "agk.toml", 'version = "0.66.0"\nreview_mode = "solo"\n\n[personal]\nforge = "files"\n')
    return root


def record(n: int, product: str = "booking-web", score: int | None = None, **over) -> dict:
    data = {
        "product": product,
        "run": n,
        "kit": {"version": "0.66.0", "sha": "a" * 40},
        "tier": "strongest",
        "models": ["model-a"],
        "status": "complete",
        "objective": {"tests_passed": 10 + n, "tests_failed": 0, "accessibility": "not-run"},
        "process": {"questions": 2, "records": 5, "rounds": 1, "minutes": 90},
        "cost": {
            "input": 1000,
            "cache_write": 10,
            "cache_read": 100,
            "output": 50,
            "other": 0,
            "total": 1160,
            "usd": 3.0 * n,
        },
        "review": {layer: (n + 2 if score is None else score) for layer in LAYERS},
        "accepted": ["AC1", "AC2", "AC3"],
    }
    data.update(over)
    return data


def runs(root: Path, records: list[dict]) -> Path:
    folder = root / "runs"
    for rec in records:
        put(folder, f"{rec['product']}/run-{rec['run']}.json", json.dumps(rec))
    return folder


def three(product: str = "booking-web", score: int | None = None) -> list[dict]:
    return [record(n, product, score) for n in (1, 2, 3)]


def accepted_record(root: Path, day: str, score: int) -> Path:
    """A record written from saved runs and set accepted on a yes, as `accept` does."""
    folder = runs(root / day, three("booking-web", score) + three("payments-api", score))
    assert eval_record.write(root, folder, day)[0] == 0
    said = put(root, f"said-{day}.txt", "Yes\n")
    assert eval_record.accept(root, day, said, SAID_AT, None, gh_never)[0] == 0
    return root / eval_record.FOLDER / f"{day}.md"


def gh_never(*a, **k):
    raise AssertionError("a GitHub call was made")


def lines_of(root: Path, day: str = DAY) -> list[str]:
    return (root / eval_record.FOLDER / f"{day}.md").read_text("utf-8").splitlines()


def test_ac7_write_gives_every_line_of_the_record(kit):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 1: the form of the record)."""
    folder = runs(kit, three() + three("payments-api"))
    code, said = eval_record.write(kit, folder, DAY)
    assert code == 0, said
    text = lines_of(kit)
    digest = hashlib.sha256((kit / "evals" / "rubric.toml").read_bytes()).hexdigest()
    assert text[0] == f"# Eval record {DAY}"
    for line in (
        "- Status: proposed",
        f"- Kit: 0.66.0 at {'a' * 40}",
        f"- Rubric: {digest}",
        "- Tolerance: 0",
        "- Cost per accepted feature: 2.00 usd",
        "- Compared with: none (first record)",
        "- Regressions: none",
        "| product | layer | run 1 | run 2 | run 3 | median |",
        "| booking-web | problem | 3 | 4 | 5 | 4 |",
        "| payments-api | code | 3 | 4 | 5 | 4 |",
        "| booking-web | objective.tests_passed | 11 | 12 | 13 | 12 |",
        "| booking-web | process.questions | 2 | 2 | 2 | 2 |",
        "| booking-web | cost.usd | 3 | 6 | 9 | 6 |",
        "| booking-web | objective.accessibility | not-run | not-run | not-run | - |",
    ):
        assert line in text, line


def test_ac7_an_incomplete_run_is_shown_with_its_stage_never_0(kit):
    """REQ-084 AC7: SPEC-0077 rules 9 and 10 (answer 1, `Q-PH-2`)."""
    broken = record(2, status="incomplete", stage="review", review={}, accepted=[])
    folder = runs(kit, [record(1), broken, record(3)])
    assert eval_record.write(kit, folder, DAY)[0] == 0
    text = lines_of(kit)
    assert "| booking-web | problem | 3 | incomplete (review) | 5 | 4 |" in text
    assert "- Regressions:" in text and "- booking-web incomplete review" in text
    assert not any("| 0 |" in line for line in text)


def test_ac7_compare_names_the_product_the_layer_and_the_score_past_tolerance():
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 2)."""
    last = {"booking-web": {"problem": 5.0, "code": 4.0}, "payments-api": {"data": 3.0}}
    new = {"booking-web": {"problem": 3.0, "code": 4.0}, "web-new": {"problem": 1.0}}
    assert eval_record.compare(new, last, 1) == [
        "booking-web problem 3 (was 5, tolerance 1)",
        "payments-api data missing",
    ]
    assert eval_record.compare(new, last, 2) == ["payments-api data missing"]
    assert eval_record.compare(new, None, 0) == []


def test_ac7_three_runs_within_tolerance_give_no_regression(kit):
    """REQ-084 AC7: SPEC-0077 rule 15 (three runs differ by at most `tolerance`)."""
    accepted_record(kit, LAST, 5)
    rubric = kit / "evals" / "rubric.toml"
    rubric.write_text(rubric.read_text("utf-8").replace("tolerance = 0", "tolerance = 1"), "utf-8")
    folder = runs(kit, three(score=4) + three("payments-api", 4))
    # a changed rubric is refused at accept, never at write; the comparison reads `tolerance` today
    assert eval_record.write(kit, folder, DAY)[0] == 0
    assert "- Regressions: none" in lines_of(kit)
    assert f"- Compared with: {LAST}" in lines_of(kit)


def test_ac7_a_median_below_the_last_beyond_tolerance_is_a_regression(kit):
    """REQ-084 AC7: SPEC-0077 rule 10 (`Measured:` after: product, layer, score)."""
    accepted_record(kit, LAST, 5)
    folder = runs(kit, three(score=4) + three("payments-api", 5))
    assert eval_record.write(kit, folder, DAY)[0] == 0
    text = lines_of(kit)
    assert "- booking-web problem 4 (was 5, tolerance 0)" in text
    assert "- Regressions: none" not in text


@pytest.mark.parametrize("value", ["-1", "7", "true", '"1"', None])
def test_ac8_a_bad_tolerance_is_refused_naming_tolerance(kit, value):
    """REQ-084 AC8: SPEC-0077 rule 10 (answer 6: `tolerance`, never the value)."""
    rubric = kit / "evals" / "rubric.toml"
    text = rubric.read_text("utf-8")
    new = "" if value is None else f"tolerance = {value}"
    rubric.write_text(text.replace("tolerance = 0", new), "utf-8")
    code, said = eval_record.write(kit, runs(kit, three()), DAY)
    assert code == 1
    assert said == ["refused: evals/rubric.toml (setting: tolerance)"]
    assert not (kit / eval_record.FOLDER).exists()


def test_ac7_write_never_overwrites_and_refuses_another_rubric(kit):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 7)."""
    folder = runs(kit, three())
    assert eval_record.write(kit, folder, DAY)[0] == 0
    code, said = eval_record.write(kit, folder, DAY)
    assert code == 1 and said == ["refused: a record exists for the date (path class: docs/runs/evals/)"]
    old = record(1, review={layer: 3 for layer in LAYERS[:-1]})
    other = runs(kit / "old", [old, record(2), record(3)])
    code, said = eval_record.write(kit, other, "2026-11-28")
    assert code == 1 and said[-1].endswith("(path class: evals/)")


def test_ac8_accept_on_a_yes_writes_the_status_the_line_and_one_setup_entry(kit):
    """REQ-084 AC8: SPEC-0077 rules 10 and 12 (answer 3; `forge = "files"` posts nothing)."""
    assert eval_record.write(kit, runs(kit, three()), DAY)[0] == 0
    said = put(kit, "said.txt", "Yes\n")
    code, out = eval_record.accept(kit, DAY, said, SAID_AT, "someone", gh_never)
    assert code == 0, out
    text = lines_of(kit)
    assert "- Status: accepted" in text
    assert f'- Accepted: the person said "Yes" at {SAID_AT}' in text
    memory = (kit / "docs" / "runs" / "steward" / "memory.md").read_text("utf-8")
    assert memory.count("Setup: eval-record") == 1
    assert f'Setup: eval-record {DAY}: accepted because the person said "Yes" at {SAID_AT}' in memory
    assert eval_record.accepted(kit)[0] == DAY


@pytest.mark.parametrize("words", ["maybe later", "", "Yes, but change the rubric first"])
def test_ac8_any_other_reply_writes_nothing(kit, words):
    """REQ-084 AC8: SPEC-0077 rule 10 (answer 3: any other reply changes no file)."""
    assert eval_record.write(kit, runs(kit, three()), DAY)[0] == 0
    before = lines_of(kit)
    code, out = eval_record.accept(kit, DAY, put(kit, "said.txt", words), SAID_AT, None, gh_never)
    assert code == 1 and out == [f"eval-record {DAY}: not accepted"]
    assert lines_of(kit) == before
    assert not (kit / "docs" / "runs" / "steward").exists()
    assert eval_record.accepted(kit) is None


def test_ac8_a_session_the_conductor_started_accepts_nothing(kit, monkeypatch):
    """REQ-084 AC8: SPEC-0077 rule 10 (principle 2: `AGK_STEWARD_START`)."""
    assert eval_record.write(kit, runs(kit, three()), DAY)[0] == 0
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    code, out = eval_record.accept(kit, DAY, put(kit, "s.txt", "Yes"), SAID_AT, None, gh_never)
    assert code == 2 and "(setting: AGK_STEWARD_START)" in out[0]
    assert "- Status: proposed" in lines_of(kit)


def test_ac8_in_team_mode_only_a_spec_approver_accepts(kit, monkeypatch):
    """REQ-084 AC8: SPEC-0077 rules 10 and 12 (answer 6: `review_mode = "team"`)."""
    monkeypatch.setattr(steward_owner, "review_mode", lambda root: "team")
    monkeypatch.setattr(eval_record, "review_mode", lambda root: "team")
    monkeypatch.setattr("reviewers.spec_approvers", lambda root: ["approver-a"])
    assert eval_record.write(kit, runs(kit, three()), DAY)[0] == 0
    said = put(kit, "said.txt", "Yes")
    code, out = eval_record.accept(kit, DAY, said, SAID_AT, "someone-else", gh_never)
    assert code == 2 and "(setting: spec_approvers)" in out[0]
    assert eval_record.accept(kit, DAY, said, SAID_AT, "approver-a", gh_never)[0] == 0
    assert f'- Accepted: the person said "Yes" at {SAID_AT} (by approver-a)' in lines_of(kit)


def test_ac8_accept_refuses_a_regressed_an_accepted_or_a_rerubricked_record(kit):
    """REQ-084 AC8: SPEC-0077 rule 10 (answer 3, `Q-PH-4`)."""
    accepted_record(kit, LAST, 5)
    said = put(kit, "said.txt", "Yes")
    code, out = eval_record.accept(kit, LAST, said, SAID_AT, None, gh_never)
    assert code == 1 and out == ["refused: the record is already accepted (SPEC-0077 rule 10)"]
    assert eval_record.write(kit, runs(kit, three(score=4) + three("payments-api", 5)), DAY)[0] == 0
    code, out = eval_record.accept(kit, DAY, said, SAID_AT, None, gh_never)
    assert code == 1 and out == ["refused: a record with a regression is never accepted (SPEC-0077 rule 10)"]
    day = "2026-11-28"
    assert eval_record.write(kit, runs(kit / day, three(score=5) + three("payments-api", 5)), day)[0] == 0
    rubric = kit / "evals" / "rubric.toml"
    rubric.write_text(rubric.read_text("utf-8") + "\n", "utf-8")
    code, out = eval_record.accept(kit, day, said, SAID_AT, None, gh_never)
    assert code == 1 and out == ["refused: the record was scored on another rubric (path class: evals/)"]
    assert eval_record.accepted(kit)[0] == LAST


def test_ac7_accepted_is_the_newest_well_formed_accepted_record(kit):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 7: two records, a record out of form)."""
    accepted_record(kit, LAST, 5)
    accepted_record(kit, DAY, 5)
    assert eval_record.accepted(kit)[0] == DAY
    path = kit / eval_record.FOLDER / f"{DAY}.md"
    path.write_text(path.read_text("utf-8").replace("| 5 |\n", "| 9 |\n", 1), "utf-8")
    assert eval_record.accepted(kit)[0] == LAST
    assert eval_record.accepted(kit / "nowhere") is None


# --- the release (answer 4 (a)) -----------------------------------------------------------------

RELEASE = KIT_ROOT / "scripts" / "agk" / "check_release.py"
OLD_LOG = "# Changelog\n\n## Unreleased\n\n- #5 a change\n\n## 1.0.0 (2026-11-01)\n\n- #1 the start\n"
NEW_LOG = (
    "# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-11-28)\n\n- #5 a change\n\n"
    "## 1.0.0 (2026-11-01)\n\n- #1 the start\n"
)


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def versions(root: Path, version: str, mode: str = "flow") -> None:
    put(root, "agk.toml", f'version = "{version}"\npr_mode = "{mode}"\nreview_mode = "solo"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": version}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": version}))


def release_tree(tmp_path: Path, evals: bool, record_day: str | None, mode: str = "flow") -> Path:
    root = tmp_path / "rel"
    root.mkdir()
    for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@example.invalid")):
        git(root, *args)
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    versions(root, "1.0.0")
    put(root, "CHANGELOG.md", OLD_LOG)
    put(root, "kit/hashes.json", "{}\n")
    put(root, "scripts/agk/check_release.py", "# on the base\n")
    if evals:
        put(root, "evals/rubric.toml", (KIT_ROOT / "evals" / "rubric.toml").read_text("utf-8"))
    if record_day:
        put(root, "agk.toml", 'version = "1.0.0"\nreview_mode = "solo"\n\n[personal]\nforge = "files"\n')
        accepted_record(root, record_day, 5)
        shutil.rmtree(root / record_day)
        versions(root, "1.0.0")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "release")
    versions(root, "1.1.0", mode)
    put(root, "CHANGELOG.md", NEW_LOG)
    put(root, "kit/hashes.json", '{"new": 1}\n')
    return root


def check_release(root: Path) -> subprocess.CompletedProcess:
    base = subprocess.run(
        ["git", "rev-parse", "main"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(root), "AGK_BASE": base}
    return subprocess.run(
        [sys.executable, str(RELEASE)], cwd=root, capture_output=True, text=True, env=env
    )


def test_ac7_a_release_with_evals_and_no_accepted_record_fails(tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 10 (`Measured:` after: one FAIL naming rule 10)."""
    proc = check_release(release_tree(tmp_path, True, None))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout.strip() == (
        "FAIL release: SPEC-0077 rule 10: a release pull request needs an accepted eval record"
        " (path class docs/runs/evals/)"
    )


def test_ac7_a_release_with_an_accepted_record_after_the_last_release_passes(tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 4 (a))."""
    proc = check_release(release_tree(tmp_path, True, "2026-11-02"))
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout + proc.stderr


def test_ac7_a_record_older_than_the_last_release_does_not_count(tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 4 (a): on or after the newest release heading)."""
    proc = check_release(release_tree(tmp_path, True, "2026-10-30"))
    assert proc.returncode == 1 and "SPEC-0077 rule 10" in proc.stdout


@pytest.mark.parametrize(("evals", "mode"), [(False, "flow"), (True, "strict")])
def test_ac8_no_evals_or_strict_mode_checks_as_today(tmp_path, evals, mode):
    """REQ-084 AC8: SPEC-0077 rule 12 (`Q-PH-1`: no `evals/` on the base, or strict mode)."""
    proc = check_release(release_tree(tmp_path, evals, None, mode))
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout + proc.stderr


# --- the curated pack (answer 4 (b)) --------------------------------------------------------------


def pack(root: Path, tier: str, evals: str | None) -> Path:
    folder = root / "config" / "packs" / "pack-a"
    body = put(folder, "playbooks/a.md", "# A\n\n- basis = \"expected\"\n")
    digest = hashlib.sha256(body.read_bytes()).hexdigest()
    manifest = (
        'format = 1\nid = "pack-a"\nversion = "1.0.0"\npublisher = "Example"\n'
        f'tier = "{tier}"\nlicence = "MIT"\nsource = "https://example.com/pack-a"\nkit = ">=0.1.0"\n'
        'as_of = "2026-11-01"\nreviewed = "2026-11-01 by the maintainers"\nkinds = ["playbooks"]\n'
        + (f'evals = "{evals}"\n' if evals else "")
        + f'[files]\n"playbooks/a.md" = "{digest}"\n[permissions]\n'
    )
    put(folder, "agk-pack.toml", manifest)
    return folder


CURATED = "rule 10: config/packs/pack-a: a curated pack needs an accepted eval record (key: evals)"


def test_ac7_a_curated_pack_needs_an_accepted_record_only_where_evals_exist(kit, tmp_path):
    """REQ-084 AC7: SPEC-0077 rule 10 (answer 4 (b), `Q-PH-5`)."""
    folder = pack(kit, "curated", None)
    assert f"{CURATED}" in check_packs.problems(folder, kit)
    day = accepted_record(kit, LAST, 5).name
    named = pack(kit, "curated", f"docs/runs/evals/{day}")
    assert CURATED not in check_packs.problems(named, kit)
    assert CURATED not in check_packs.problems(pack(kit, "community", None), kit)
    project = tmp_path / "project"
    assert CURATED not in check_packs.problems(pack(project, "curated", None), project)


# --- the class stays closed (answer 9) ------------------------------------------------------------


def test_ac8_only_eval_record_writes_or_reads_the_records():
    """REQ-084 AC8: SPEC-0077 rule 16 (answer 9: one writer, one reader)."""
    folder = re.compile(r"docs/runs/evals|Status: accepted")
    for path in (KIT_ROOT / "scripts" / "agk").rglob("*.py"):
        if path.name != "eval_record.py":
            assert not folder.search(path.read_text("utf-8")), path.name
    for name in ("check_release.py", "check_packs.py", "scorecard.py"):
        text = (KIT_ROOT / "scripts" / "agk" / name).read_text("utf-8")
        assert "eval_record.accepted(" in text, name


def test_ac8_the_script_is_kit_only_and_refuses_outside_the_kit(tmp_path):
    """REQ-084 AC8: SPEC-0077 rule 12 (answer 6: `[kit] layout`, never installed)."""
    copy = tmp_path / "scripts" / "agk"
    copy.mkdir(parents=True)
    shutil.copy(KIT_ROOT / "scripts" / "agk" / "eval_record.py", copy)
    proc = subprocess.run(
        [sys.executable, str(copy / "eval_record.py"), "write", "--runs", str(tmp_path)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 2 and "(path class: evals/)" in proc.stderr
