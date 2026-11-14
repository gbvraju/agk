# ADR-0535: Local governance runs call the kit's make target

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1264, plan #661, SPEC-0030 rule 6, SPEC-0039 rule 6, session rule 30
- Requirements: REQ-039

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

A project set up with `adopt.py` keeps its own `Makefile` (`kit/manifest.json` `adopt.skip`), so it has the kit's
`agk.mk` but may have no `governance` target. CI (`make -f agk.mk agk-lint|agk-test|agk-project-test` and the check
scripts), the builder's `prepush.py` (`make -f agk.mk agk-governance`) and `evidence.py check` already call `agk.mk`.
Two callers did not: the conductor's bounded local run, which its guard allowed only as `make -C <scratch>
test|governance`, and the guarded merge's governance run before and after the merge (`make -C <tree> governance`).
In such a project in local mode no pull request could be cleared or merged.

## Decision

1. `scripts/agk/merge_cleared.py` runs `make -C <tree> -f agk.mk agk-governance AGK_BASE=<base>`, both on the
   would-be merge and after the merge (one function builds both); every other argument, the lock, `env -i` and the
   step names in its output (`make governance`) are unchanged. This replaces the `make -C <worktree> governance`
   form that SPEC-0039 rule 6 names.
2. `.claude/hooks/conductor_guard.py` also allows exactly `make -C <scratch> -f agk.mk agk-governance` and
   `make -C <scratch> -f agk.mk agk-project-test`, under the same `env -i PATH="$PATH" HOME=<scratch>` prefix, the
   same optional `AGK_BASE=<sha>` and the same scratch rules. The two forms of SPEC-0030 rule 6 stay allowed, so a
   project set up with `init.py` that runs them is unchanged. Another `-f` file, another target, another option
   spelling or any extra argument is denied.
3. `.claude/agents/conductor.md` and `docs/guides/local-mode.md` name the `-f agk.mk agk-governance` form wherever
   they named `make -C <scratch> governance`, with the reason: `agk.mk` is the kit's own file, in every project.
4. CI mode and personal mode do not change; no workflow changes.

## Consequences

The conductor's local review and the guarded merge work in projects set up with init or adopt. A project whose own
`governance` target ran more than `agk.mk`'s recipe no longer has those extra steps run by the guarded merge; CI and
`prepush.py` already ran only the kit's recipe, so the gate is the same everywhere.

## Residual

- The text of SPEC-0030 rule 6 and SPEC-0039 rule 6 still names the old command; a reviewer's spec patch aligns it
  (Q-1264-1).
