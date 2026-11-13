# ADR-0495: A shared-index change re-proves on the checks alone

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0325, ADR-0339, SPEC-0050 amendment 171, brief #1163, plan #661
- Requirements: REQ-057

## Context

SPEC-0050 rule 6 puts a pull request in the re-prove state when a file it changes, shared indexes included, changed on the
default branch after its merge base (`Q-S0050-7`), and rule 7 sends it back to its builder: merge the default branch, run
`prepush.py`, push, and a new review. Rule 3's shared indexes (`agk.toml`, `kit/manifest.json`, `config/rule-budget.txt`,
`docs/requirements.md`, `docs/build-state.md`) change in almost every brief, because each new test file adds a
`[[testing.map]]` line to `agk.toml`. On 2026-11-12/13 #1147 went from `agk:merge-ready` back to review three times only
for that, about 20 to 30 minutes and one builder wake each (brief #1163's `Measured:` line).

## Decision

1. `session_plan.reprove_state` returns the re-prove files and whether every one is a shared index; `reprove_kind` says
   `light` when they all are and the merge with the default branch is clean (`git merge-tree --write-tree` with no
   conflict), `conflict` when it is not, `full` when any other file is in the state, `none` when no file is, and nothing
   (unknown) when git cannot read it.
2. `conductor.py sweep` ends such a pull request's line with ` light`: `re-prove: #<n> <file> (changed by #<m>) light`.
3. `conductor.py reprove --pr <n> [--apply]` reads the pull request, fetches its base branch and `refs/pull/<n>/head`,
   and goes on only for `light`: it prints `PUT repos/<repo>/pulls/<n>/update-branch expected_head_sha=<head>` and, with
   `--apply`, makes that one call (a merge commit by GitHub, never a rebase or a force-push), reads the new head and posts
   `Report: <new head> merge of main (light re-prove, SPEC-0050 amendment 171)`. A full re-prove or a conflict prints
   `full re-prove (<file> is not a shared index|conflict)`, exits 3 and writes nothing.
4. `merge_cleared.py` (`judge_head`, used by the merge, `--status`, `--sweep` and the merger's event) carries the latest
   `Verdict: cleared <old>` to the head when the head is a commit with exactly two parents, the first `<old>`, the second
   on the default branch as last fetched; `<old>` is in the light state against that parent with the default branch's
   `[flow] shared_indexes`; and the head's tree is exactly the clean merge of the two, so it adds nothing beyond the
   default branch's change. A fix list with `Final:` lines never carries. The required checks of the new head, every
   hold, the re-prove hold of rule 8 and the pre-merge governance run (SPEC-0039 rule 6) are unchanged.
5. The conductor's instructions are not edited (the owner's file); `docs/guides/getting-started.md` names the command.

Protected path classes changed: `scripts/agk/` (`session_plan.py`, `conductor.py`, `merge_cleared.py`), `tests/kit/`
(`test_light_reprove.py`, and three expected `re-prove:` lines of `test_conductor_commands.py` that now end ` light`),
`agk.toml` (the `[[testing.map]]` entries of the three scripts) and `kit/` (`kit/hashes.json`, regenerated).

## Consequences

A pull request held only by another change's shared-index line returns to `agk:merge-ready` on the checks alone, with no
builder wake and no second review. The conductor's guard (`.claude/hooks/conductor_guard.py`) does not yet allow the new
command, so a conductor running under it cannot run it until the guard admits the form (`Q-1163-1`). A local conductor,
or one with `auto_merge = false`, runs the same command; a person still merges, and rule 7's sweep line stays the guard.

## Residual

- 2026-11-12: the guard form of `conductor.py reprove --pr <n> [--apply]` and its `PUT` is the maintainers' (`Q-1163-1`,
  due 2027-01-31).
