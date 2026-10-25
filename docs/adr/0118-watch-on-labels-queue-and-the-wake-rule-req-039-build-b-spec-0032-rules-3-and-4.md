# ADR-0118: watch on labels, queue and the wake rule (REQ-039 build (b), SPEC-0032 rules 3 and 4)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0115, ADR-0110
- Requirements: REQ-039

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0032 (Approved, #187) rule 3 makes `session.py watch` end on a change of the router's label and adds `queue`, so a conductor or builder that restarts resumes from GitHub with no memory; rule 4 is the wake rule of the
comment on #179. This is build (b) of rule 13, from the default branch after the router (#193). The number ADR-0118 was reserved on #179 by the conductor. The tests were written first (`tests/kit/test_session.py`,
`test_session_rules.py`, `tests/kit_dev/test_guide_loop.py`; on unchanged `main` the new cases failed: 9 failed in the first two files, then the guide cases).

## Decision

1. **`watch --pr N`** (`scripts/agk/session.py`) also ends with one line `label <name>`, or `label none`, when the `agk:` label of the pull request differs from the one read at its first poll (several labels read
   as their names joined by a comma). A label that is not `agk:`-prefixed is ignored. Verdict, merge, close and conflict come before it in the same poll; `--merged` ignores labels. It prints its event and exits, as before.
2. **`queue --role conductor|builder|person [--author LOGIN]`**: one GET of the open pull requests; it prints `#N <label>` for each whose label is the role's (conductor `agk:review`, `agk:ci-red`; builder `agk:fix`,
   `agk:conflict`, `agk:ci-red`; person `agk:approve`, `agk:ready`), or `empty`; the conductor's list skips drafts (amendment 56); `--author` keeps the pull requests by that login. An unreadable list fails naming rule 3
   (exit 2); an unknown role is usage (exit 2). It writes nothing.
3. **The wake rule**: `config/session-rules.md` rules 10 and 11 say how `watch` is started so its end wakes the session (Claude Code: a Bash command started with `run_in_background`; another runtime: the equivalent;
   never in the foreground, never detached with `&` or `nohup`), that each event is one wake, and that a session runs `queue` first when it starts or restarts. `docs/guides/getting-started.md` step 4 of "Running the
   loop" says the same and names the label end and `queue`.
4. **Readings taken where the spec leaves a point open** (questions in the pull request, the most conservative reading each): "the builder of that pull request" is the pull request's author login, given with `--author`
   (without it, every pull request of the role is listed, because sessions and people share one account until lane F); the baseline is the label at the first poll, so a label already set when `watch` starts is not
   an event; `queue` prints `empty` and exits 0 when nothing is the role's.
5. Amendment 57 (`docs/runs/proposed-spec-amendments-57.md`) is applied to SPEC-0030 rules 2 and 3. A flow-mode fragment `changelog.d/req-039-b-watch-queue.md` records the change. The manifest is unchanged (both files
   are already installed).

## Consequences

- A builder waiting on `watch` wakes when CI finishes (the label changes to `agk:review` or `agk:ci-red`) with no person and no polling of its own; the conductor keeps no state of its own.
- `watch` still polls GitHub once a minute without a runtime notification; it costs no model tokens.

## Residual

- 2026-10-25: the label end sees only the label at the polls; two changes between two polls read as the last (due 2026-12-31).
- 2026-10-25: `--author` cannot tell a session from a person while they share one account (lane F) (due 2026-12-31).
- 2026-10-25: `queue --role builder --author LOGIN` tells builders apart by the pull request's author, and until the identities are separated (lane F, ADR-0117) every session posts from one account, so a builder's queue lists every builder's work; the session takes the pull request whose branch is its own (due 2026-12-31).
