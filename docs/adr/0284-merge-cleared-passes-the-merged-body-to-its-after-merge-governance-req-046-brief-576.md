# ADR-0284: merge_cleared.py passes the merged pull request's body to its after-merge governance (REQ-046, brief 576)

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0273, ADR-0271, ADR-0261, SPEC-0039
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

ADR-0273 (build (c) of SPEC-0039) runs `make governance` on each merge commit with `env -i`
leaving only `PATH` and `HOME`. ADR-0271 (session rule 36) lets a build of an Approved spec cover
its protected change with a `Covered-by:` line in its pull request body, which
`check_protected_changes.py` reads only from `--body FILE` or the file `AGK_PR_BODY` names. With
no body the after-merge run of a `Covered-by:` merge fails `protected-changes`: after #567 merged
(45675f0) it reported the branch red and opened the red-branch issue (#574), which holds every
later merge. The ADR number was reserved for brief #576 by the conductor.

## Decision

1. Before the governance run, the command writes the pull request body it already read before the
   merge (an empty file when the body is empty) to `pr-body.md` in the run's temporary home, the
   scratch folder outside the checkout that is removed with the worktree in every case.
2. The `env -i` list of the governance run holds exactly `PATH`, `HOME` and
   `AGK_PR_BODY=<that file>`. No token and no other variable is passed; the body is not read
   again, and nothing else of the run changes.
3. This amends ADR-0273 decision 3, which names only `PATH` and `HOME`. SPEC-0039 rule 6 changes by
   amendment 120 (`docs/runs/proposed-spec-amendments-120.md`, the number the conductor reserved
   in its fix list on #577, answering Q-576-1), applied to the spec in this pull request: its
   command `env -i PATH="$PATH" HOME=<scratch>` gains `AGK_PR_BODY=<scratch>/home/pr-body.md`.
   It needs a person's `Approve: SPEC-0039` on the pull request.

## Consequences

A `Covered-by:` merge whose body names an Accepted ADR covering its classes is checked as CI
checked it, and is no longer reported red. A body without the line is still red, as it would be
in CI. The body is the author's text, which the merged code already reads in CI; it carries no
token.

## Residual

None.
