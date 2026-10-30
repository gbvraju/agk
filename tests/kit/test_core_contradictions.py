"""One test for each contradiction a project pilot found in the kit's rules (brief #383, ADR-0211).

Each test runs both rules of a contradiction together, so that a smaller core cannot bring one back
quietly: (a) a stack ADR is accepted by one ordinary commit, and both `engines.py stack-check` and
`check_final_clearance.py` pass it (brief #274, ADR-0163); (b) every kit script that imports another
starts under `python3 -I`, the only Python form the conductor's guard allows (brief #270,
ADR-0161). (c), a check that fails once the charter is accepted, has no test: `playbook.py
check-start` rule 5 refuses a charter that is not Proposed, a decided rule on the default branch
that `tests/kit_dev/test_playbook.py` asserts; ADR-0211 records it as a residual (Q-383-1).
Git and files only: no network, no model.
"""

from __future__ import annotations

import ast
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
NAMES = {p.stem for p in SCRIPTS.glob("*.py")}
CONFIG = "version: 1\nverdict_authors: [reviewer]\n"
STACK = "docs/adr/0002-stack-options.md"


def stack_adr(status: str, chosen: str) -> str:
    return f"""# ADR-0002: stack options

- Status: {status}
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

## Context

A reading list that runs on a laptop.

## Decision

1. **Options**
   - Option A — plain scripts. Trade-offs: nothing to host. Practices: pinned actions.
   - Option B — a web framework. Trade-offs: a host to run. Practices: security headers.
2. **Practices**
   - pinned actions: check (step: the workflow lint of the adopting build)
   - security headers: check (step: a header test of the adopting build)
3. **Chosen**: {chosen}

## Consequences

The architect accepts one option; the ADR then locks it.

## Residual

None.
"""


def comments(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "comments.json"
    found = [{"body": body, "created_at": "2026-10-30T10:00:00Z", "user": {"login": "reviewer"}}]
    path.write_text(json.dumps(found), encoding="utf-8")
    return path


def stack_check(root: Path):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "engines.py"), "stack-check", "--root", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_a_stack_adr_is_accepted_by_one_ordinary_commit_that_both_checks_pass(repo, tmp_path):
    """Contradiction (a), brief #383 answer 1a (REQ-039): `stack-check` refuses `Chosen` while the
    ADR is Proposed and a `Final:` commit may change only status lines, so the one way through is
    an ordinary commit that sets both lines; both checks pass that commit, and the Final route
    still fails naming the ordinary commit, so a session is never left with no way to accept."""
    repo.commit({"config/reviewers.yaml": CONFIG, STACK: stack_adr("Proposed", "none yet")}, "x")
    reviewed = repo.git("rev-parse", "HEAD").strip()
    assert stack_check(repo.root).returncode == 0

    repo.commit({STACK: stack_adr("Accepted", "Option A — nothing to host suits a laptop.")}, "y")
    head = repo.git("rev-parse", "HEAD").strip()
    proc = stack_check(repo.root)
    assert proc.returncode == 0 and proc.stdout.startswith("ok engines-stack\n"), proc.stdout
    cleared = comments(tmp_path, f"Verdict: cleared {head[:7]}\n\nreviewed.\n")
    proc = repo.run("check_final_clearance.py", "--comments", str(cleared))
    assert proc.returncode == 0, proc.stdout + proc.stderr

    final = f"Verdict: fix list {reviewed[:7]}\n\nreviewed.\n\nFinal: {STACK} Proposed -> Accepted"
    proc = repo.run("check_final_clearance.py", "--comments", str(comments(tmp_path, final)))
    assert proc.returncode == 1 and "set by an ordinary commit" in proc.stdout, proc.stdout


def importing_scripts() -> list[str]:
    """The kit scripts that import another kit script, at any depth."""
    found = []
    for path in sorted(SCRIPTS.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            module = ""
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                module = next((a.name for a in node.names if a.name.split(".")[0] in NAMES), "")
            if module and module.split(".")[0] in NAMES:
                found.append(path.name)
                break
    return found


def test_the_set_of_importing_scripts_is_not_empty():
    """Contradiction (b): the parametrized test below covers something (REQ-039)."""
    assert len(importing_scripts()) > 30


@pytest.mark.parametrize("name", importing_scripts())
def test_b_every_importing_kit_script_starts_under_the_guards_isolated_python(tmp_path, name):
    """Contradiction (b), brief #383 answer 1b (REQ-039): the conductor's guard allows Python only
    as `python3 -I`, which leaves the script's folder off the import path; every kit script that
    imports another still starts from an unrelated folder and ends in its own code (its usage, its
    own refusal, or nothing for a module without a main), never an import error or a traceback;
    exit 1 is allowed for a script's own refusal of `--help` (Q-383-2)."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / name), "--help"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert "Traceback" not in proc.stderr, proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr and "ImportError" not in proc.stderr
    assert proc.returncode in (0, 1, 2), (proc.returncode, proc.stdout, proc.stderr)
