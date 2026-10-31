"""Every proof run publishes a test manifest: what ran, what did not, and why (brief #425, ADR-0230).

`proof.py --manifest FILE` writes a Markdown manifest: each run with its area, command, files and the
seconds of the base run and the head run; "Not run" with each changed test file in no area, each
deleted test file and the reason of a `Behaviour: unchanged` skip or a draft; and "Excluded by the
project" with the `excluded` entries of the `[testing]` table, which proof never interprets.
`proof.yml` appends the manifest to the job summary on every outcome. No toolchain, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

import impact
import pytest
from common import CheckError
from test_proof_areas import TWO_AREAS, start

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "proof.yml"
EXCLUDED = (
    "[testing]\n"
    'excluded = ["@needs-renderer: no renderer on the CI runner", "@slow: run nightly"]\n'
)


def manifest(repo, *args: str, body: str | None = None) -> tuple[object, str]:
    out = repo.root.parent / "manifest.md"
    out.unlink(missing_ok=True)
    extra = ["--body", "-"] if body is not None else []
    proc = repo.run("proof.py", "--manifest", str(out), *extra, *args, stdin=body)
    text = out.read_text(encoding="utf-8") if out.is_file() else ""
    return proc, text


def section(text: str, title: str) -> str:
    """The lines under `### <title>` up to the next `###` heading."""
    found = re.search(rf"(?ms)^### {re.escape(title)}\n(.*?)(?=^### |\Z)", text)
    assert found, (title, text)
    return found.group(1)


def test_two_areas_each_list_command_files_and_base_and_head_seconds(repo):
    """REQ-016: brief #425 answers 1 and 4 (two areas with files)."""
    start(repo, TWO_AREAS)
    repo.commit(
        {
            "be.txt": "x\n",
            "fe.txt": "x\n",
            "backend/tests/test_new.py": "# new\n",
            "frontend/tests/new.test.ts": "// new\n",
        }
    )
    proc, text = manifest(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == "proof: proven"  # the output line is unchanged
    assert text.startswith("## Test manifest\n")
    assert "proof: proven" in text
    ran = section(text, "Ran")
    assert "#### backend\n" in ran and "#### frontend\n" in ran
    assert ran.index("#### backend") < ran.index("#### frontend")
    assert "- command: `test -f ../be.txt && ls tests/test_new.py`\n" in ran
    assert "- folder: `backend`\n" in ran
    assert "- files: 1\n  - `backend/tests/test_new.py`\n" in ran
    assert "- files: 1\n  - `frontend/tests/new.test.ts`\n" in ran
    assert len(re.findall(r"(?m)^- seconds: base \d+, head \d+$", ran)) == 2
    assert section(text, "Not run").strip() == "- nothing"
    assert section(text, "Excluded by the project").strip() == "- none"


def test_more_than_forty_files_show_the_first_forty_and_how_many_more(repo):
    """REQ-016: brief #425 answer 1 (the first 40, then "and n more")."""
    start(repo, TWO_AREAS)
    files = {f"backend/tests/test_{n:02d}.py": "# n\n" for n in range(43)}
    repo.commit({"be.txt": "x\n", **files})
    proc, text = manifest(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ran = section(text, "Ran")
    assert "- files: 43\n" in ran
    assert "`backend/tests/test_39.py`" in ran and "`backend/tests/test_40.py`" not in ran
    assert "  - and 3 more\n" in ran


def test_a_changed_test_file_in_no_area_is_listed_as_not_run(repo):
    """REQ-016: brief #425 answers 1 and 4 (a file in no area)."""
    start(repo, TWO_AREAS)
    repo.commit({"be.txt": "x\n", "backend/tests/test_new.py": "# n\n", "tests/test_x.py": "# x\n"})
    proc, text = manifest(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "- `tests/test_x.py`: in no [proof] area\n" in section(text, "Not run")


def test_a_deleted_test_file_is_listed_as_not_run(repo):
    """REQ-016: brief #425 answers 1 and 4 (a deletion)."""
    start(repo, TWO_AREAS)
    repo.commit(
        {"be.txt": "x\n", "backend/tests/test_new.py": "# n\n", "frontend/tests/old.test.ts": None}
    )
    proc, text = manifest(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "- `frontend/tests/old.test.ts`: deleted\n" in section(text, "Not run")


def test_a_deleted_test_file_without_a_proof_table_is_listed_too(repo):
    """REQ-016: brief #425 answer 1 (one `project_tests` run, no `[proof]` table)."""
    start(repo, "", project_tests="test -f be.txt", files={"tests/test_gone.py": "# g\n"})
    repo.commit({"be.txt": "x\n", "tests/test_new.py": "# n\n", "tests/test_gone.py": None})
    proc, text = manifest(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ran = section(text, "Ran")
    assert "#### project_tests\n" in ran and "- command: `test -f be.txt`\n" in ran
    assert "- files: 1\n  - `tests/test_new.py`\n" in ran
    assert re.search(r"(?m)^- seconds: base \d+, head \d+$", ran)
    assert "- `tests/test_gone.py`: deleted\n" in section(text, "Not run")


def test_behaviour_unchanged_lists_each_planned_run_with_the_reason(repo):
    """REQ-016: brief #425 answers 1 and 4 (`Behaviour: unchanged`)."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_new.py": "# n\n"})
    proc, text = manifest(repo, body="Behaviour: unchanged\n")
    assert proc.returncode == 0 and proc.stdout.strip() == "proof: skipped"
    assert section(text, "Ran").strip() == "- nothing"
    not_run = section(text, "Not run")
    assert (
        "- `backend` (1 test file): the pull request body says `Behaviour: unchanged`\n" in not_run
    )


def test_a_draft_or_status_only_commit_runs_nothing_and_says_why(repo):
    """REQ-016: brief #425 answers 1 and 3 (a draft, and the status-only skip of the workflow)."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_new.py": "# n\n"})
    proc, text = manifest(repo, "--not-run", "draft")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == "proof: skipped (draft)"
    assert section(text, "Ran").strip() == "- nothing"
    assert "- `backend` (1 test file): a draft pull request" in section(text, "Not run")
    proc, text = manifest(repo, "--not-run", "status-only")
    assert proc.returncode == 0
    assert "- `backend` (1 test file): a status-only final commit" in section(text, "Not run")
    proc, _ = manifest(repo, "--not-run", "other")
    assert proc.returncode == 2


def test_no_test_command_is_named_as_the_reason(repo):
    """REQ-016: brief #425 answer 1 (unknown: no test command)."""
    start(repo, "", project_tests=None)
    repo.commit({"tests/test_new.py": "# n\n"})
    proc, text = manifest(repo)
    assert proc.returncode == 4
    assert section(text, "Ran").strip() == "- nothing"
    assert "- `project_tests`: no test command (setting: project_tests)\n" in section(
        text, "Not run"
    )


def test_no_test_file_is_named_as_the_reason(repo):
    """REQ-016: brief #425 answer 1 (unknown: no added or changed test file)."""
    start(repo, TWO_AREAS)
    repo.commit({"src/code.txt": "changed\n"})
    proc, text = manifest(repo)
    assert proc.returncode == 4
    assert "- no added or changed test file\n" in section(text, "Not run")


def test_excluded_tags_are_listed_in_every_manifest(repo):
    """REQ-016: brief #425 answers 2 and 4 (an excluded tag is listed, never interpreted)."""
    start(repo, TWO_AREAS + EXCLUDED)
    repo.commit({"be.txt": "x\n", "backend/tests/test_new.py": "# n\n"})
    for args, body in (((), None), ((), "Behaviour: unchanged\n"), (("--not-run", "draft"), None)):
        proc, text = manifest(repo, *args, body=body)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        excluded = section(text, "Excluded by the project")
        assert "- `@needs-renderer`: no renderer on the CI runner\n" in excluded
        assert "- `@slow`: run nightly\n" in excluded
    assert impact.excluded_entries(repo.root) == [
        "@needs-renderer: no renderer on the CI runner",
        "@slow: run nightly",
    ]


@pytest.mark.parametrize(
    "value, setting",
    [
        ('"@x: y"', "testing.excluded"),
        ('["@needs-renderer"]', "testing.excluded[1]"),
        ('["@a: fine", "no reason:"]', "testing.excluded[2]"),
        ('["two words: x"]', "testing.excluded[1]"),
        ("[3]", "testing.excluded[1]"),
    ],
)
def test_a_malformed_excluded_entry_is_refused_naming_the_setting(repo, value, setting):
    """REQ-016: brief #425 answers 2 and 4 (a malformed entry)."""
    start(repo, TWO_AREAS + f"[testing]\nexcluded = {value}\n")
    repo.commit({"be.txt": "x\n", "backend/tests/test_new.py": "# n\n"})
    with pytest.raises(CheckError) as caught:
        impact.testing_table(repo.root)
    assert f"(setting: {setting})" in str(caught.value)
    proc, text = manifest(repo)
    assert proc.returncode == 2 and text == ""
    assert f"(setting: {setting})" in proc.stdout
    assert "renderer" not in proc.stdout and "fine" not in proc.stdout  # never the value


def test_the_testing_table_keeps_its_settings_and_accepts_excluded(repo):
    """REQ-016: brief #425 answer 2 (the other settings are read as before)."""
    start(repo, TWO_AREAS + EXCLUDED)
    assert impact.testing_table(repo.root)["profile"] == "balanced"
    start_none = repo.root.parent / "absent"
    assert impact.excluded_entries(start_none) == []


def test_without_manifest_the_output_is_unchanged(repo):
    """REQ-016: brief #425 (the manifest is written only when asked for)."""
    start(repo, TWO_AREAS)
    repo.commit({"be.txt": "x\n", "backend/tests/test_new.py": "# n\n"})
    proc = repo.run("proof.py")
    assert proc.returncode == 0 and proc.stdout.strip() == "proof: proven"
    assert not (repo.root.parent / "manifest.md").exists()


# --- the workflow (answer 3) ----------------------------------------------------------------------


def steps() -> dict[str, str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    out = {}
    for part in re.split(r"(?m)^      - ", text.split("    steps:\n", 1)[1])[1:]:
        named = re.match(r"name:\s*(.+)", part)
        if named:
            out[named.group(1).strip().strip('"')] = part
    return out


def test_the_run_step_writes_the_manifest():
    """REQ-016: brief #425 answer 3."""
    block = steps()["Red-then-green"]
    assert '--manifest "$RUNNER_TEMP/proof-manifest.md"' in block


def test_the_summary_step_appends_the_manifest_on_every_outcome_skipped_included():
    """REQ-016: brief #425 answers 3 and 4 (the summary step is present in the workflow)."""
    names = list(steps())
    assert "Test manifest" in names
    assert names.index("Test manifest") > names.index("Red-then-green")
    block = steps()["Test manifest"]
    cond = re.search(r"(?m)^        if: (.+)$", block).group(1)
    assert "!cancelled()" in cond  # also after a failed run step, and on a skip
    assert "steps.paused.outputs.paused != 'true'" in cond  # ADR-0196: paused skips every step
    assert '>> "$GITHUB_STEP_SUMMARY"' in block
    assert "--not-run" in block and "draft" in block and "status-only" in block
    assert "steps.status.outputs.skip" in block


def test_a_timed_out_run_and_a_command_with_backticks_read_right():
    """REQ-016: brief #425 answer 1 (the seconds of a run ended by proof_timeout)."""
    import proof

    run = proof.Run("api", ["t/test_a.py"], "echo `date`", ".", [900, None], "base")
    lines = proof.ran_lines(run)
    assert "- command: `` echo `date` ``" in lines  # a fence longer than the backticks inside
    assert "- seconds: base 900 (timed out, setting: proof_timeout), head not run" in lines
    run = proof.Run("api", ["t/test_a.py"], "true", ".", [2, 900], "head")
    assert "- seconds: base 2, head 900 (timed out, setting: proof_timeout)" in proof.ran_lines(run)
    assert proof.code("a`b") == "``a`b``" and proof.code("`x") == "`` `x ``"
