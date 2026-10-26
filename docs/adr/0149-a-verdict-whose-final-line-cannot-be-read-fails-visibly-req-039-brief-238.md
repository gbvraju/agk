# ADR-0149: a verdict whose Final line cannot be read fails visibly (REQ-039, brief #238)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0094, ADR-0105, ADR-0121
- Requirements: REQ-039

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #238, seen on 2026-10-26 on three pull requests: the reviewer approved the commit before a status-only final commit with `Verdict: cleared <sha>` and a `Final:` line in plain words. The router reads a final commit as covered only from `Verdict: fix list <sha>` followed by `Final: <path> [REQ-n] <old> -> <new>` (`covered_fix_list`, SPEC-0021), so each final commit went to `agk:review` instead of `agk:ready`, and nothing said why. The conductor assigned the brief to `builder-b` on #204 with this ADR number reserved and amendment 84 only if a spec rule changes. The tests were written first (`tests/kit/test_verdict_problem.py`, `test_route_correction.py`, `test_conductor_guard_verdict.py`: 25 failed on the unchanged tree).

## Decision

1. **One reading, shared** (`scripts/agk/common.py`, `verdict_problem`, next to `covered_fix_list`): it returns the problem of a `Verdict:` comment, or None. The problems: a `Final:` line under a verdict that is not `fix list`; a `Final:` line that does not match `Final: <path> [REQ-n] <old> -> <new>`; a `Final:` line for `docs/requirements.md` without its requirement id, or a requirement id on any other path; and a `Final:` line in a fix list that also has numbered items, which `covered_fix_list` ignores without a word (the verdict on 90e5749: the message says to post the `Final:` line in its own verdict once the items are met). Each message names the rule (SPEC-0021 rule 1 or 2) and shows the expected shape, never the body. A numbered list of items with no `Final:` line is not a problem.
2. **The router tells the reviewer** (`scripts/agk/route.py`, `correct_verdicts`): on a `Verdict:` comment of a listed author with a problem, the router posts one reply on the pull request that begins `Correction needed:`, gives the message and ends `(verdict comment <id>)`. A reply already there for that comment means nothing new is posted, so a rerun posts nothing. The label stays as the router decides it today; the reply is the last write of a routing; a dry run and a read-only token post nothing. It uses the router's existing write path and the five permissions it already has (`issues: write` covers a comment), and adds none. A comment of an unlisted author is no verdict, so no one else can make the router post. This is the one comment the router posts (Q-K4-326).
3. **The conductor's guard refuses it before it is posted** (`.claude/hooks/conductor_guard.py`): a comment `POST` whose body starts with `Verdict:` and has a problem is denied with the same message, from `-f body=...` or from `-F body=@<file>`. A verdict has several lines, which a command line cannot carry, so the guard now also allows the conductor's own comment `POST` of one `-F body=@<file>` where the file is a regular file of a scratch directory (the rule the shadow reviewer's guard already has), on the origin repository's issue-comment endpoint only; the conductor's role file says to write the verdict into a scratch file and post it so (Q-K4-327).
4. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sm.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 84 (`docs/runs/proposed-spec-amendments-84.md`) is for SPEC-0032 rule 8, SPEC-0036 rule 5 and SPEC-0030 rule 6, because a spec says the router posts no comment.

## Consequences

- A reviewer who writes a `Final:` line the router cannot read is told at once, in plain words, how to write it; the pull request no longer sits at `agk:review` without a reason.
- The router is no longer silent: it posts one comment, only for a verdict of a listed author with a problem.

## Residual

- 2026-10-26: the guard sees a verdict only when it goes through `gh api`; a verdict posted with a runtime's own comment tool, which the hook's matcher does not cover, is caught by the router's reply instead (due 2026-12-31).
- 2026-10-26: the router answers the `Verdict:` comments it sees at a routing; a malformed verdict is answered at the next routing after it (a comment event starts one), not before it is posted (due 2026-12-31).
