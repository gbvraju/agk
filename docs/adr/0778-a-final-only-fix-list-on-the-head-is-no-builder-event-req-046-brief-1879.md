# ADR-0778: A Final-only fix list on the head is no builder event (REQ-046)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1879, amendment 225 (SPEC-0039 rules 2 and 9, SPEC-0064 rule 4), ADR-0277, ADR-0265, ADR-0293,
  ADR-0589, ADR-0568, ADR-0329, ADR-0477, ADR-0713, ADR-0718, plan #661
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `kit/`, `.claude/`, `tests/kit/`, `agk.toml`

## Context

A covered fix list on exactly the head whose every `Final:` line is `docs/adr/<file> Proposed -> Accepted` clears that
head for the merger (SPEC-0021 rule 3a, `merge_cleared.accepted_adrs`), yet every waker read it as an owed verdict:
`autopilot.pick` and `conductor.builder_facts` started a `fix` job, `session.follow_up_owed` returned `fix list` and an
interactive `watch --pr` ended on it, so the builder posted `Report: <head> fix list applied: nothing to change`, which
nothing but the wake reads (ADR-0477), and in local mode that Report was in effect the merge trigger. Last night's run
had four such rounds (#1866 twice, #1867, #1870), 6 to 14 minutes from verdict to merge. The owner's word (2026-11-24,
the steward chat, quoted as data): "Yes, draft all four along with release".

## Decision

1. **One reading of "no event".** `merge_cleared.clears_head(verdict, sha)` is the merger's own test of rule 3
   (`Verdict: cleared <sha>`, or `accepted_adrs(verdict, sha) is not None`), and `judge` and `session.cleared_unmerged`
   call it. `merge_cleared.no_builder_event(comment, sha)` is what the wakers read: a `Verdict: cleared` (`Q-1391-1`) or
   `accepted_adrs` on exactly the full head; `merge_cleared.builder_owed` drops those and, when the newest verdict is
   one, every older verdict too, since only the newest counts. A fix list with a numbered item, any other `Final:` line
   (`docs/requirements.md`, a spec, a stack-options ADR), a mix, a short sha or another head stays an event as today.
2. **The builder is not woken.** `autopilot.pick` reads `builder_owed` as `owing`; `conductor.owed_of`, read by
   `builder_facts`, reads it for `owed`, so `job_gate` says `left (waits for an event)` (this also aligns the
   watchdog with `Q-1391-1` for a `Verdict: cleared`); `session.follow_up_owed` returns no `fix list` for it;
   `session.builder_verdicts` takes it out of the watch's `missed_verdict` and `verdict_line`, and every older listed
   verdict with it when it is the newest, so `watch --pr` waits on and ends at `merged` or `closed`. A `Verdict:
   cleared` still ends the watch (session rule 1). Labels stay events: `agk:conflict` and `agk:ci-red` start the job.
   `session.verdict_line` itself is unchanged, because the conductor and `session_plan` read it to tell whether a head
   has a verdict at all.
3. **The conductor merges in the same act.** `.claude/agents/conductor.md` ("The guarded merge"): with `auto_merge =
   true`, in the same act as posting `Verdict: cleared <sha>` or such a fix list on `<sha>`, run
   `python3 scripts/agk/merge_cleared.py --pr <n> --sha <sha>`, unchanged. `session.cleared_unmerged` reads
   `clears_head`, so `review-queue` lists a held one `cleared, not merged` for the next pass; with `auto_merge` off or
   absent it stays `skip: verdict on this head` and nothing merges.
4. **The builder's text.** `kit/templates/runtime/builder.txt` FINAL LINES: such a fix list on your head is no event; a
   job started on one anyway pushes nothing, posts `Report: <head> fix list applied: nothing to change` and ends, so a
   no-op job is never counted a failed job (`job_ended`).
5. **The specs.** Amendment 225 (`docs/runs/proposed-spec-amendments-225.md`) proposes SPEC-0039 rules 2 and 9 and
   SPEC-0064 rule 4; the reviewers approve it (principle 6).
6. **Path classes changed:** `scripts/agk/` (`merge_cleared.py`, `autopilot.py`, `conductor.py`, `session.py`), `kit/`
   (`templates/runtime/builder.txt`; `hashes.json` needed no change: `kit_hashes.py` reads `ok kit-hashes`), `.claude/` (`agents/conductor.md`), `tests/kit/` (the
   seven mapped test files) and `agk.toml` (`test_runtime_templates.py` joins the `builder.txt` map entry).

## Consequences

A Final-only round costs no builder job, no `nothing to change` comment and no second conductor review: CI's merger
merges on the verdict comment and a local conductor merges in the act of posting it, 2 to 14 minutes sooner. Every
guarantee stays where it was: the head pin (`--sha`, the exact-head test of `accepted_adrs`), the verdict's evidence
lines, the `Proposed` read of `acceptance_lines` and the hold list of rule 5. A push after the verdict moves the head,
so the predicate is false and the new head is reviewed.

## Residual

Session rule 1 still says the watch ends on any verdict naming the head; this build makes a Final-only fix list no
watch event as the brief asks and leaves the rule text to the maintainers (`Q-1879-5`). In solo mode a person's
`Confirmed:` of a Final-only head is still read as today (`Q-1879-4`).
