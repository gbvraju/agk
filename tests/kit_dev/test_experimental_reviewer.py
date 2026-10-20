"""Kit-only tests of the experimental reviewer opt-in (ADR-0020)."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, expected_files, make_repo, manifest, run_init, snapshot

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import adopt  # noqa: E402
import common  # noqa: E402
import doctor  # noqa: E402
import init  # noqa: E402

EXPERIMENTAL = [
    ".claude/agents/reviewer.md",
    "scripts/agk/check_review_report.py",
    "scripts/agk/review_context.py",
]
# the reviewer's tests (tests/kit/test_review_*.py) stay in the kit repository (ADR-0052)


def upgrade(root):
    return subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "upgrade.py"), str(root), "--dry-run"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def run_upgrade(root, *args):
    return subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "upgrade.py"), str(root), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def opt_in(root):
    with open(root / "agk.toml", "a", encoding="utf-8") as fh:
        fh.write("experimental_reviewer = true\n")


def test_ac3_manifest_lists_the_three_experimental_paths_outside_the_verbatim_set():
    """REQ-013 AC3: ADR-0020 decision 2."""
    m = manifest()
    assert m["experimental"] == EXPERIMENTAL
    assert not set(EXPERIMENTAL) & set(m["verbatim"])
    assert not set(EXPERIMENTAL) & expected_files()


def test_ac3_the_release_row_hashes_the_experimental_files():
    """REQ-013 AC3: ADR-0020 decision 2 (a later upgrade can tell an old copy from an edit)."""
    table = json.loads((KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))
    row = table["releases"][manifest()["kit_version"]]
    assert set(EXPERIMENTAL) <= set(row["verbatim"])


def test_ac3_init_writes_none_of_them_by_default(tmp_path):
    """REQ-013 AC3: ADR-0020 decision 2."""
    repo = make_repo(tmp_path / "proj")
    assert run_init(repo).returncode == 0
    for rel in EXPERIMENTAL:
        assert not (repo / rel).exists(), rel
    assert common.experimental_enabled(repo) is False


def test_ac3_adopt_writes_none_of_them_by_default(tmp_path):
    """REQ-013 AC3: ADR-0020 decision 2."""
    repo = make_repo(tmp_path / "proj")
    proc = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "adopt.py"), str(repo)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout
    for rel in EXPERIMENTAL:
        assert not (repo / rel).exists(), rel


def test_ac3_installers_plan_the_three_files_when_agk_toml_sets_the_key(tmp_path):
    """REQ-013 AC3: ADR-0020 decision 3 (the key is read from the target's agk.toml)."""
    repo = make_repo(tmp_path / "proj")
    (repo / "agk.toml").write_text("experimental_reviewer = true\n", encoding="utf-8")
    items, _, _ = init.build_items(repo, "2026-01-02")
    assert set(EXPERIMENTAL) <= {rel for rel, _ in items}
    plan, _, _ = adopt.build_plan(repo, "2026-01-02")
    assert set(EXPERIMENTAL) <= {entry[0] for entry in plan}
    (repo / "agk.toml").write_text("experimental_reviewer = false\n", encoding="utf-8")
    items, _, _ = init.build_items(repo, "2026-01-02")
    assert not set(EXPERIMENTAL) & {rel for rel, _ in items}


@pytest.mark.parametrize(
    "text", ['experimental_reviewer = "true"', "experimental_reviewer = 1", "x ="]
)
def test_ac3_only_the_boolean_true_opts_in(tmp_path, text):
    """REQ-013 AC3: ADR-0020 decision 3."""
    (tmp_path / "agk.toml").write_text(text + "\n", encoding="utf-8")
    assert common.experimental_enabled(tmp_path) is False


def test_ac3_upgrade_creates_the_files_on_opt_in_and_is_then_idempotent(tmp_path):
    """REQ-013 AC3: ADR-0020 decision 3 (not reported as deleted: they were never installed)."""
    repo = make_repo(tmp_path / "proj")
    assert run_init(repo).returncode == 0
    opt_in(repo)
    dry = upgrade(repo)
    assert dry.returncode == 0, dry.stdout
    for rel in EXPERIMENTAL:
        assert f"create {rel}" in dry.stdout and "deleted-locally" not in dry.stdout
        assert not (repo / rel).exists()
    assert run_upgrade(repo).returncode == 0
    for rel in EXPERIMENTAL:
        assert (repo / rel).read_bytes() == (KIT_ROOT / rel).read_bytes()
    before = snapshot(repo)
    again = run_upgrade(repo)
    assert again.returncode == 0 and "nothing to do" in again.stdout
    assert snapshot(repo) == before


def test_ac3_upgrade_reports_but_never_deletes_files_when_the_key_is_off(tmp_path):
    """REQ-013 AC3: ADR-0020 decision 3 (removed-in-kit)."""
    repo = make_repo(tmp_path / "proj")
    assert run_init(repo).returncode == 0
    opt_in(repo)
    assert run_upgrade(repo).returncode == 0
    text = (
        (repo / "agk.toml")
        .read_text(encoding="utf-8")
        .replace("experimental_reviewer = true\n", "")
    )
    (repo / "agk.toml").write_text(text, encoding="utf-8")
    proc = run_upgrade(repo, "--dry-run")
    assert proc.returncode == 0, proc.stdout
    for rel in EXPERIMENTAL:
        assert f"removed-in-kit {rel}" in proc.stdout
        assert (repo / rel).exists()


def test_ac3_doctor_checks_the_three_files_only_when_the_key_is_set():
    """REQ-013 AC3: ADR-0020 decision 3."""
    m = manifest()
    off, _ = doctor.installed_files(m, "init")
    on, _ = doctor.installed_files(m, "init", True)
    assert not set(EXPERIMENTAL) & set(off)
    assert set(EXPERIMENTAL) <= set(on)
    on_adopt, _ = doctor.installed_files(m, "adopt", True)
    assert set(EXPERIMENTAL) - {"tests/kit/review_fixtures.py"} <= set(on_adopt) | set(off)


def test_ac3_review_skill_says_experimental_and_stops_when_the_agent_is_absent():
    """REQ-013 AC3: ADR-0020 decision 4."""
    text = (KIT_ROOT / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")
    assert "experimental" in text.lower() and "never a gate" in text
    assert ".claude/agents/reviewer.md" in text and "experimental_reviewer = true" in text
    body = text.split("---\n", 2)[2]
    assert body.index("check that the project has") < body.index("review_context.py")


def test_ac3_readme_has_the_experimental_heading_the_result_and_the_link():
    """REQ-013 AC3: ADR-0020 decision 6."""
    readme = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "## Experimental: reviewer agent" in readme
    assert "\n## Reviewer agent" not in readme
    section = readme.split("## Experimental: reviewer agent", 1)[1].split("\n## ", 1)[0]
    assert "0 of 5" in section and "docs/runs/shadow-review-4.md" in section
    assert "never a gate" in section and "human review stays required" in section


def test_ac3_this_repository_keeps_its_copies_and_says_so():
    """REQ-013 AC3: ADR-0020 decision 5."""
    assert common.experimental_enabled(KIT_ROOT) is True
    for rel in EXPERIMENTAL:
        assert (KIT_ROOT / rel).is_file(), rel


def test_ac3_adr_amends_adr_0011_names_the_classes_and_records_the_rulings():
    """REQ-013 AC3: ADR-0020 decisions 1 and 7."""
    text = (KIT_ROOT / "docs" / "adr" / "0020-reviewer-agent-experimental.md").read_text(
        encoding="utf-8"
    )
    assert "- Amends: ADR-0011" in text and "Q-SR4-1" in text and "Q-SR4-2" in text
    line = next(ln for ln in text.splitlines() if ln.startswith("Protected classes:"))
    for cls in (".claude/", "scripts/agk/", "tests/kit/", "tests/kit_dev/", "kit/", "agk.toml"):
        assert f"`{cls}`" in line, cls
    assert "2026-12-31" in text.split("## Residual", 1)[1]
