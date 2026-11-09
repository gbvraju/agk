# ADR-0397: One record interface for personal mode, its api view and the agent mark

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0267, ADR-0179, SPEC-0041, SPEC-0007, brief #894
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0041 (Approved) puts one developer's records in a private sidecar and names, in rules 6 to 8, a forge interface,
a view that the existing `--api-dir` readers can read and a mark that keeps an agent's comment from counting as an
approval. ADR-0267 decision 10 asks each build for its own ADR naming the protected classes it changes and citing it.
This is the first part of build (d) of rule 30; rule 9's "not used in personal mode" lines change files that open pull
requests hold and come in the second part.

## Decision

1. `scripts/agk/forge.py` (new, installed) gives one interface: `get(name, endpoint)` with the names of SPEC-0007 rule
   20, and the writes `create_issue`, `comment` and `record_pull`. `GithubForge` wraps `metrics.Gh` and `metrics.ApiDir`
   unchanged; its writes are refused naming the setting `forge`, because personal mode never writes to GitHub (rule 1).
2. `FilesForge` keeps GitHub-shaped JSON under `forge/` of the sidecar, with one number sequence for issues and pulls,
   each write a temporary file and a rename, committed to the sidecar with only that file. It runs `git` and never `gh`.
3. `scripts/agk/personal.py api-view DIR` (new, installed) renders the records and the product's git, read-only, into
   a new or empty folder outside the clone. A name no record can answer writes no file, so a reader prints `unknown`
   as it does for a saved response that is absent.
4. A comment written while `CLAUDECODE` is set carries `performed_via_github_app: {"slug": "claude"}`; a sidecar whose
   `agent_apps` lacks `claude` is refused naming the setting. `reviewers.py` does not change. `personal.py confirm`
   exists only as its refusal in an agent session, and otherwise says it comes in build (g) and writes nothing.

## Consequences

`metrics.py`, `facts.py` and `check_final_clearance.py` read personal state with no change to their code. A project that
never attaches personal mode sees two more installed scripts that it never runs, and every reader as before.

## Residual

The agent mark is written by the kit and not by GitHub, so it is a label and not proof (`Q-S0041-16`). A pull request's
files and commits in the api view come from the clone, so a record whose head the clone no longer has reads as
`unknown`. `personal.py` needs `personal_state.py`, which `tests/kit_dev/test_kit_manifest.py` keeps out of the
installed set: in an installed team-mode project `api-view` refuses, naming the path class, until the user-scope
packaging of build (l) (`Q-894-1`).
