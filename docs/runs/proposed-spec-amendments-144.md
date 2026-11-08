# Proposed spec amendments 144 (SPEC-0039; REQ-046)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0373 (brief #797), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 144 is the one
brief #797 reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it
needs a person's `Approve: SPEC-0039`; no session posts it.

1. **Rule 2, the sweep.** In GitHub mode with `auto_merge = true`, `merger.yml` also runs on a schedule (every 15 minutes)
   and by hand. `merge_cleared.py --sweep` lists the open, non-draft pull requests labelled `agk:ready`, oldest first, and
   runs the one guarded command on each cleared head, at most five a run, printing one line per pull request. A gate job
   with no secret reads `--sweep-gate`, so a project with no auto-merge opens no `merge` environment.
2. **Rule 2, the report.** Each run prints `UNMERGED #<n> cleared <m> min <reason>` for a cleared pull request older than
   20 minutes it could not merge; in local mode `--sweep` merges nothing and prints only these lines.
3. **Rule 5, a new hold.** After `spec approval`: a pull request that adds or changes a spec a listed spec approver has
   approved, while the spec on the head reads `Draft`, is held with `an approved spec still reads Draft (rule 5)`. The
   router keeps such a pull request at `agk:approve` (SPEC-0032 rule 2).
4. **Not in this amendment.** The change to SPEC-0021 rule 1 that brief #797 reserved this number for is dropped: its cause
   did not reproduce, and the ruling of `Q-797-1` leaves `fix_items` unchanged.
