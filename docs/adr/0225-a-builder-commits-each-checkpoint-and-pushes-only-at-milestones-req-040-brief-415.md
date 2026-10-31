# ADR-0225: a builder commits each checkpoint and pushes only at milestones (REQ-040, brief 415)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0116, ADR-0186, ADR-0221
- Requirements: REQ-040

Protected classes: `config/`, `tests/kit_dev/`, `tests/kit/`

## Context

Brief #415 (from #287 answer 6 and #286 part 6). Session rule 7 said a builder commits and pushes its branch at every step, and
every push of a draft starts CI; on a Free plan each such push costs at least two billed minutes, even after the router and
proof stop starting jobs for drafts. Brief #326 (ADR-0186) made a builder run `prepush.py` before each push but left rule 7 as
it was, and recorded the milestone push only as a proposal (`docs/runs/proposed-spec-amendments-101.md`, Q-326-4). The brief
gives the answers: rule 7 and rule 8 change, the getting-started guide says it in one line, and tests check it.

## Decision

1. **Rule 7 (answer 1).** A builder commits a `checkpoint:` at every step that leaves the tests it has written so far green or
   expected-red, as before, and pushes its branch only at these milestones: the first checkpoint, which opens the pull request
   as a draft (so ownership is visible at once); the tests written so far expected-red; the tests green; marking the pull
   request ready; and before any stop it can foresee (a usage limit near, a question it will wait on, the end of its turn).
   The rest of rule 7 (no `Final:` line in a checkpoint, the draft and ready routes) is unchanged.
2. **Rule 8 (answer 2).** The one `Progress:` comment is posted, or edited in place, at each push of rule 7, not at each
   checkpoint. Rule 23 (GitHub unreachable) is unchanged.
3. **The guide (answer 3).** Step 2 of `docs/guides/getting-started.md`, where it shows a builder's loop, says the same in one
   line.
4. **Tests first (answer 4).** `tests/kit_dev/test_session_rules_push.py` checks rule 7's milestones and their order, the parts
   of rule 7 that stay, rule 8 at each push, rule 23 unchanged, that no rule still says a builder pushes at every step or
   checkpoint (so rules 7, 8 and 31 agree), and the one line of the guide.
5. **The pinned rule 7 (Q-415-2).** `tests/kit/test_prepush.py` (brief #326) pinned the old first words of rule 7, "commits
   and pushes its branch at every step", as the record that the milestone push was then only proposed. That file is outside the
   brief's `Touches:` line, but the brief's own change makes it fail; the assertion now checks the new first words and the
   milestones, and its checks of rule 31 and of the proposal file stay as they were.

## Consequences

A draft costs a few CI runs (opened, red, green, ready, and one before each foreseeable stop) instead of one per step. A builder
that stops without warning keeps its unpushed checkpoints on its own machine only: rule 9's `resume` continues from the last
pushed checkpoint and its `Progress:` line, so the work since that push is redone, which is the price of fewer runs; a foreseen
stop pushes first and loses nothing.

## Residual

- 2026-10-31: Q-415-1: SPEC-0033 rule 1 and rule 3 (Approved) still say a builder commits and pushes at every step and posts
  the progress line after each checkpoint. An Approved spec is changed only by a proposal (principle 6), and the spec is outside
  the brief's `Touches:` line, so it is not edited here; proposed amendment 101, item 1, already states the matching change and
  waits for the maintainers.
- 2026-10-31: Q-415-3: `docs/guides/project-ci.md` still says a builder pushes a checkpoint to a draft at every step; it is
  outside `Touches:` and left for a later brief.
