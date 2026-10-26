"""A new project names its spec approver at install (brief #254; REQ-039; SPEC-0032 rule 5).

The installed `config/reviewers.yaml` (init and adopt templates) carries `spec_approvers` with the
placeholder next to `maintainers`; `reviewers.py --check` fails while it lists nobody but the
placeholder, naming the setting; the doctor reports it; an upgrade of a project without the line
only notes it. Fixtures in `tmp_path` with git. No network, no model.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
import reviewers
import upgrade
from test_doctor import checks_of, doctor, prepare, stub_gh

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ("kit/templates/reviewers.yaml", "kit/templates/reviewers.adopt.yaml")
PROTECTED = {
    "kit/templates/reviewers.yaml": "kit/templates/protected-paths.txt",
    "kit/templates/reviewers.adopt.yaml": "kit/templates/protected-paths.adopt.txt",
}
GUIDES = {  # the guide and where its step that puts in the handle starts and ends
    "docs/guides/getting-started.md": ("## Step 4.", "## Step 5."),
    "docs/guides/existing-codebase.md": ("Put your GitHub handle", "## Step 2."),
}


def template(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def install(repo, rel: str) -> None:
    """The two files `reviewers.py --check` reads, as a fresh install writes them."""
    repo.write("config/reviewers.yaml", template(rel))
    repo.write("config/protected-paths.txt", template(PROTECTED[rel]))


def check(repo):
    return repo.run("reviewers.py", "--check")


# --- answer 1: the templates ---------------------------------------------------------------------


@pytest.mark.parametrize("rel", TEMPLATES)
def test_ac4_each_template_lists_the_placeholder_approver_next_to_maintainers(rel):
    """REQ-039 AC4: brief #254 answer 1 (one line with a comment, after the `maintainers` line)."""
    lines = template(rel).splitlines()
    at = next(i for i, ln in enumerate(lines) if ln.strip().startswith("maintainers:"))
    line = lines[at + 1]
    assert line.startswith('spec_approvers: ["@REPLACE-ME"]')
    assert re.search(r"#\s*\S", line), "the line carries a one-line comment"
    assert sum(ln.startswith("spec_approvers:") for ln in lines) == 1
    data = reviewers.parse(template(rel))
    assert data["spec_approvers"] == ["@REPLACE-ME"] and reviewers.approvers_of(data) == []


# --- answers 3 and 4: the check ------------------------------------------------------------------


@pytest.mark.parametrize("rel", TEMPLATES)
def test_ac4_a_fresh_install_fails_the_check_until_both_handles_are_set(repo, rel):
    """REQ-039 AC4: brief #254 answers 3 and 4 (fails naming each setting, never a value)."""
    install(repo, rel)
    proc = check(repo)
    assert proc.returncode == 1
    assert "verdict_authors" in proc.stdout and "spec_approvers" in proc.stdout
    assert "REPLACE-ME" not in proc.stdout

    text = template(rel).replace(
        'maintainers: {github_team: "@REPLACE-ME"}', 'maintainers: {github_team: "@ada"}'
    )
    repo.write("config/reviewers.yaml", text)
    proc = check(repo)
    assert proc.returncode == 1 and "spec_approvers" in proc.stdout
    assert "verdict_authors" not in proc.stdout and "REPLACE-ME" not in proc.stdout

    repo.write("config/reviewers.yaml", template(rel).replace("@REPLACE-ME", "@ada"))
    proc = check(repo)
    assert proc.returncode == 0, proc.stdout
    assert reviewers.spec_approvers(repo.root) == ["ada"]


@pytest.mark.parametrize(
    "listed", ['["@REPLACE-ME"]', "[@replace-me]", "[REPLACE-ME]", "['@REPLACE-ME', REPLACE-ME]"]
)
def test_ac4_a_list_of_only_the_placeholder_fails_naming_the_setting(repo, listed):
    """REQ-039 AC4: brief #254 answer 3 (the placeholder in any spelling lists nobody)."""
    install(repo, TEMPLATES[0])
    base = template(TEMPLATES[0]).replace("@REPLACE-ME", "@ada")
    repo.write("config/reviewers.yaml", base.replace('["@ada"]', listed, 1))
    proc = check(repo)
    assert proc.returncode == 1
    assert [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL")] == [
        f"FAIL reviewers: {reviewers.APPROVERS} lists only the placeholder: "
        "put the handle of the person who approves specs there (SPEC-0032)"
    ]


@pytest.mark.parametrize("listed", [None, "[]", "['@REPLACE-ME', ada]", "[ada]"])
def test_ac4_absent_empty_or_a_real_person_beside_the_placeholder_passes(repo, listed):
    """REQ-039 AC4: SPEC-0032 rule 5 (absent or empty is still allowed; reading Q-254-1)."""
    install(repo, TEMPLATES[0])
    lines = template(TEMPLATES[0]).replace("@REPLACE-ME", "@ada").splitlines(keepends=True)
    lines = [ln for ln in lines if not ln.startswith("spec_approvers:")]
    if listed is not None:
        lines.append(f"spec_approvers: {listed}\n")
    repo.write("config/reviewers.yaml", "".join(lines))
    proc = check(repo)
    assert proc.returncode == 0, proc.stdout


def test_ac4_the_problem_function_names_the_setting_only():
    """REQ-039 AC4: brief #254 answer 3 (`approver_problems`, the unit the check prints)."""
    data = reviewers.parse('version: 1\nspec_approvers: ["@REPLACE-ME"]\n')
    problems = reviewers.approver_problems(data)
    assert len(problems) == 1 and "spec_approvers" in problems[0]
    assert "REPLACE" not in problems[0].upper().replace("SPEC_APPROVERS", "")


# --- answer 3: the doctor ------------------------------------------------------------------------


def run_doctor(tmp_path: Path, text: str) -> dict[str, dict]:
    dirs = prepare("ok", tmp_path)
    (dirs["root"] / "config" / "reviewers.yaml").write_text(text, encoding="utf-8")
    stub = tmp_path / "bin"
    stub_gh(stub)
    proc = doctor(
        "--api-dir",
        str(dirs["api"]),
        "--repo",
        "example-owner/example-repo",
        "--kit-root",
        str(dirs["kit"]),
        "--json",
        str(dirs["root"]),
        path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )
    return checks_of(proc.stdout)


def test_ac4_the_doctor_reports_the_placeholder_approver_naming_the_setting(tmp_path):
    """REQ-039 AC4: brief #254 answer 3 (`placeholder-team-reviewers`, SPEC-0006)."""
    text = (
        'version: 1\nteams:\n  maintainers: {github_team: "@example-owner/maintainers"}\n'
        'spec_approvers: ["@REPLACE-ME"]   # who approves a spec\n'
    )
    report = run_doctor(tmp_path / "a", text)
    found = report["placeholder-team-reviewers"]
    assert found["status"] == "fail" and found["severity"] == "error"
    assert "spec_approvers" in found["message"] and "REPLACE" not in found["message"]
    fixed = run_doctor(tmp_path / "b", text.replace("@REPLACE-ME", "@ada"))
    assert fixed["placeholder-team-reviewers"]["status"] == "ok"


# --- answer 4: an upgrade ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "src"),
    [("config/reviewers.yaml", TEMPLATES[0]), ("config/reviewers.yaml", TEMPLATES[1])],
)
def test_ac4_an_upgrade_without_the_line_notes_it_and_writes_nothing(tmp_path, rel, src):
    """REQ-039 AC4: brief #254 answer 4 (a template: a note, never a write)."""
    table = json.loads((ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))
    row = table["releases"]["0.56.0"]  # the last release whose templates had no such line
    old = (
        "\n".join(
            ln
            for ln in template(src).replace("@REPLACE-ME", "@ada").splitlines()
            if not ln.startswith("spec_approvers:")
        )
        + "\n"
    )
    target = tmp_path / "target"
    (target / "config").mkdir(parents=True)
    (target / rel).write_text(old, encoding="utf-8")
    notes = upgrade.template_notes(target, ROOT, {rel: src}, row)
    assert f"template-changed {rel} ({src})" in notes
    assert rel not in upgrade.CREATE_ONLY  # a template the upgrade prints and never writes
    assert (target / rel).read_text(encoding="utf-8") == old
    assert sorted(p.name for p in (target / "config").iterdir()) == ["reviewers.yaml"]


# --- answer 2: the guides ------------------------------------------------------------------------


@pytest.mark.parametrize("rel", GUIDES)
def test_ac4_step_4_of_each_guide_says_to_replace_both_placeholders(rel):
    """REQ-039 AC4: brief #254 answer 2 (both settings named where the handle is put in)."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    start, end = GUIDES[rel]
    step = text[text.index(start) : text.index(end)]
    assert "maintainers" in step and "spec_approvers" in step and "@REPLACE-ME" in step
