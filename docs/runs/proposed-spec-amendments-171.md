# Proposed spec amendments 171 (SPEC-0050; REQ-057)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0495 (brief #1163), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0050-overlapping-work-never-runs-at-once-and-a-second-change-re-proves.md` (rules 6 and 7, and the answer
`Q-S0050-7` re-read). The number 171 is the one brief #1163 reserved. The brief asks for the amendment and its build in
one pull request, so this amendment is applied to the spec text in the same pull request: a new rule 7a, one clause in
rule 6, one in rule 7 and one in `Q-S0050-7`, and the new answer `Q-S0050-16`. The spec's `- Status:` line is left as
it is; the owner decides the amendment with `Approve: <head> SPEC-0050` on this pull request; no session posts it.

The sentence (brief #1163): "When a pull request's only re-prove files are shared indexes and its merge is clean, the
conductor updates the branch itself and its last clearing verdict carries over once the checks pass, with no builder
round trip and no second review."

## What is on the default branch today

Read in the code by this session (main 40ca3ff):

- `session_plan.reprove_files` applies rule 6 with no exemption: a shared index both sides changed puts a pull request in
  the re-prove state, and `merge_cleared.reprove_check` holds it with `held: re-prove (rule 6 of SPEC-0050)`.
- `merge_cleared.judge` clears only `Verdict: cleared <the head>`; a merge of the default branch makes a new head, so the
  conductor reviews again (rule 7).
- On 2026-11-12/13 #1147 went from `agk:merge-ready` back to review three times only because #1152 and #1153 added lines
  to `agk.toml` (the brief's `Measured:` line).

## Items

1. **The light re-prove (new rule 7a).** A pull request whose re-prove files of rule 6 are all shared indexes (rule 3, as
   `[flow] shared_indexes` sets them) and whose merge with the default branch is clean (`git merge-tree --write-tree`
   with no conflict) takes the light re-prove: the conductor brings the branch up to date (`PUT
   /repos/{owner}/{repo}/pulls/{n}/update-branch` with the head it read as `expected_head_sha`: a merge commit, never a
   rebase or a force-push), the required checks run on the new head as for any push, and the clearing verdict on the
   old head carries over to the new head when they pass, because the diff between the two heads is only the default
   branch's commits. `conductor.py reprove --pr <n> [--apply]` does it and posts `Report: <new head> merge of main (light
   re-prove, SPEC-0050 amendment 171)`; `conductor.py sweep` marks the line `light`.
2. **What the merger accepts.** `merge_cleared.py` accepts a clearing verdict on the first parent of the head when the
   head is a merge commit whose second parent is on the default branch as last fetched, the first parent is in the light
   state against it, and the head's tree is exactly the clean merge of the two (no extra content). A fix list with
   `Final:` lines never carries.
3. **What stays.** Any other re-prove file, a conflict or a failed check keeps today's full re-prove with the builder and
   a new review. `merge_cleared.py`'s own merge-tree governance run before merging (SPEC-0039 rule 6) and the re-prove
   hold of rule 8 stay unchanged.

## Text applied to SPEC-0050

- Rule 6, after "Two builds of one brief re-prove like any two pull requests (`Q-S0050-12`).": " A re-prove whose files
  are all shared indexes and whose merge is clean is the light re-prove of rule 7a (amendment 171)."
- Rule 7, after "The conductor gives no clearing verdict on a head in the re-prove state": ", except by rule 7a's carried
  verdict".
- New rule 7a, the text of item 1 and item 2 above, with item 3's last sentence (`Q-S0050-16`).
- `Q-S0050-7`, at its end: "; amendment 171 (rule 7a) lets a re-prove whose files are all shared indexes and whose merge
  is clean carry the verdict over on the checks alone."
- A `## Contexts` section, which the amended Approved spec must state (amendment 142, `check_specs.py`), from the brief's
  `Contexts:` line.
- New answer `Q-S0050-16`: the brief reserved `Q-S0050-14`, which the spec already holds (the rule budget, ruled
  2026-11-06), so the answer takes the next free number.

## Tests

`tests/kit/test_light_reprove.py` (brief #1163 tests (a) to (e)), on git repositories in a temporary folder and stubbed
REST: a lone `agk.toml` re-prove with a clean merge is `light`; a script both sides changed makes it `full`; a conflicting
merge is `conflict`; `reprove --apply` calls update-branch with `expected_head_sha` and posts the report, and a full one
writes nothing; the merger carries the verdict only to a merge that adds nothing beyond the default branch's change.
Test (f): the existing SPEC-0050 tests stay green, three expected `re-prove:` lines now ending ` light`.

## Contexts

- kit: the installed `conductor.py`, `session_plan.py` and `merge_cleared.py`, so every project with a conductor skips the
  round trip for a shared-index line
- github: no workflow change; update-branch is one REST call by the conductor's own token, so the checks run as for a push
- local: a local conductor runs the same command; with `auto_merge = false` a person still merges and rule 7's sweep line
  stays the guard
- personal: not applicable: no conductor; nothing changes
- stacks: not applicable: no test or build step of a stack changes

## Residual

- 2026-11-12: the conductor's guard does not yet allow `conductor.py reprove` and its `PUT` (`Q-1163-1`, due 2027-01-31).

## Questions

- **Q-1163-1:** see the pull request: the conductor's guard (`.claude/hooks/conductor_guard.py`, outside the brief's
  `Touches:`) denies the new command; the reading is to leave the guard as it is until a person rules.
