# Proposed spec amendments 158 (SPEC-0039; REQ-046, REQ-057)

Date: 2026-11-10 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0416 (brief #971), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 158 is the one
brief #971 reserved. This amendment is not applied to the spec text in this pull request: amendments 139, 144, 148 and 151
to SPEC-0039 are not in its text yet either, and their apply step, like brief #798's for amendment 145, writes them in
order. The owner decides it with `Approve: <head> SPEC-0039` on this pull request; no session posts it. It reads with
amendment 151 and replaces its item 4 and the strict ruleset of its item 3.

The sentence (brief #971): "In GitHub mode a cleared pull request joins GitHub's merge queue, which tests it on top of main
and the pull requests ahead of it in batches, so no pull request re-runs its checks after every merge to main, and main
still never merges an untested combination."

The owner's yes, quoted as data (#661, 2026-11-10T07:54Z): "Approve: merge queue — ruleset requires the merge queue (batch
5, no up-to-date rule); governance and proof run on merge_group; the merger enqueues cleared heads; local and personal modes
re-prove only on overlap".

Measured (brief #971): on 2026-11-10, 00:00 to 13:20 IST, 30 of 76 pull-request `governance` runs (203 of 443 minutes, 46%)
ran only because the branch had merged the default branch, which the ruleset's up-to-date rule forces after every merge.

## Items

1. **Rule 1, the setting (a new rule "the merge queue").** The `[flow]` key `merge_queue = false | true` already exists
   (default `false`; anything but a boolean is refused naming `setting: flow.merge_queue`; brief #853, ADR-0387). Its
   meaning changes. Rule 1 gains: "With `merge_queue = true`, GitHub mode (`execution` not `local`, `forge` not `files`)
   and `auto_merge = true`, a cleared pull request joins GitHub's merge queue, by rule 2a. With `merge_queue = false`, or
   in local or personal mode, nothing changes: SPEC-0050 rule 6 re-proves only on overlap and rule 6 runs governance and
   `[testing] pre_merge_tests` on the would-be merge." Amendment 151 item 4 (`agk/verdict` a required status of the queue,
   the command holding naming the setting) is replaced by this item and item 3.
2. **Rule 2a, the command queues instead of merging (new, after rule 2).** "With the merge queue on (rule 1),
   `merge_cleared.py --pr <n> --sha <head>` does not merge a cleared, green, approved head. Every hold it has today still
   applies first, in the same order: the verdict (rule 3), the evidence (rule 4), the hold list (rule 5: approvals, a red
   default branch, workflow changes left for the owner and the rest), the re-prove state of SPEC-0050 rule 6, and the
   pinned run of governance and `pre_merge_tests` on the would-be merge (rule 6). Then it adds that exact head to the merge
   queue, pinned to the cleared sha (`expectedHeadOid`), prints `merge-cleared #<n> <sha12>: queued` and exits 0, and
   records the queue entry by rule 7 as it records a merge, with the word `queued` in place of the merge sha. A head that
   moved is refused by GitHub and prints `refused: head moved`, exit 3. A head already in the queue prints `queued` again
   and adds nothing. After the queue merges it, the next review pass or merger run records the merge by rule 7 and runs
   nothing of rule 6's after-merge governance: the push to the default branch runs the full suite." The pinned run of
   rule 6 before queueing stays, so the queue never receives a head that fails on today's default branch (`Q-S0039-18`).
3. **Rule 2b, the queue's run is the merge gate (new).** "The workflows `governance` and `proof` run on the `merge_group`
   event, on the queue's commit. They run the tests that `test_plan.py` selects for the files the batch changes against
   the default branch, plus `[testing] pre_merge_tests`, and the full suite when a changed file matches `always_full`. A
   push to the default branch still runs the full suite. The queue's required checks are `governance` and `proof` only. No
   status that is set only on a pull request's head, such as `agk/verdict`, is required by the queue: the queue's commit
   never carries it, so the queue would wait for it forever. `agk/verdict` stays a status that starts the merger job
   (amendment 151 item 2) and is required by nothing."
4. **Rule 2c, a failed batch (new).** "When a check of the queue fails, GitHub removes the failing pull request and merges
   the rest of the batch. The merger job, on the event that the pull request left the queue without merging
   `(verify: the event and action GitHub sends, read as pull_request dequeued)`, posts one comment on it,
   `Removed from the merge queue: <check> failed on <queue sha12>`, never the same line twice for one queue sha, and the
   router labels it `agk:ci-red` (SPEC-0032). The pull request then needs a new head and a new verdict, as any red head
   does."
5. **Rule 5, the up-to-date rule.** Amendment 151 item 3 is replaced: "The ruleset's rule `Require branches to be up to
   date before merging` is off in every mode. It is not needed: SPEC-0050 rule 6 holds a pull request whose files the
   default branch changed since its merge base, rule 6 runs governance and the pre-merge tests on the would-be merge, and
   with the queue on GitHub tests the batch on top of the default branch. Forcing every open pull request to merge the
   default branch after every merge is what ran 30 of 76 governance runs on 2026-11-10." `doctor.py`'s
   `ruleset-up-to-date` warning (brief #853) is retired in the build (`Q-S0039-17`).
6. **Rule 11, the guide.** `docs/guides/auto-merge.md` gains a section for the owner, who sets the ruleset; no session
   sets or reads it: "require the merge queue, with squash; build at most 5 and at least 1 pull request per batch, waiting
   at most 5 minutes; only non-failing pull requests merge; the rule `Require branches to be up to date before merging` is
   off (also with the queue off, item 5); the queue's required checks are `governance` and `proof`, never `agk/verdict`;
   and the merge queue is offered only where GitHub offers it to the repository `(verify: GitHub offers it to
   organization-owned public repositories and to Enterprise Cloud, not to a repository owned by a personal account, as
   ADR-0387 recorded)`." It also says that GitHub's merge queue is not the conductor's local `conductor.py merge-queue`
   (brief #643, ADR-0329) nor its key `merge_queue_wait_minutes`, which stay as they are.
7. **Rule 1, the doctor line.** `doctor.py` prints one line `merge queue: on` or `merge queue: off`, read from the
   setting on the default branch only, never from the ruleset; a malformed value fails naming the setting.
8. **Rule 12, the build that follows.** One build, brief #972, tests first, from the default branch, after this
   amendment's `Approve:`: `scripts/agk/merge_cleared.py` (rule 2a; the hold `merge queue (setting flow.merge_queue)`
   becomes the queueing), `.github/workflows/governance.yml` and `.github/workflows/proof.yml` (`merge_group`, rule 2b),
   `.github/workflows/merger.yml` (rule 2c), `scripts/agk/route.py` (the `agk:ci-red` label of rule 2c),
   `scripts/agk/doctor.py` (items 5 and 7), `docs/guides/auto-merge.md` (item 6), and the tests of item 9. Its workflow
   changes are the owner's yes on #661, quoted in its brief; its ADR names the protected classes it changes
   (`scripts/agk/`, `.github/`, `tests/kit/`). Contexts: stacks run the selection on `merge_group` by each stack's test
   step; the full suite stays on the default branch.
9. **Tests.** The tests of rules 1, 2, 5 and 10 gain, with saved GitHub responses and a fake `gh` only: with
   `merge_queue = true` in GitHub mode a cleared, green head is queued pinned to its sha and prints `queued`; each hold of
   rules 3 to 6 and the re-prove state still holds first and queues nothing; a moved head prints `refused: head moved`; a
   queued head is not queued twice; in local and personal mode and with `merge_queue = false` the command merges as
   today; the workflows' `on:` lists `merge_group` for `governance` and `proof` and not for any other workflow; no
   workflow or guide names `agk/verdict` as a required check of the queue; a saved removal event posts one `Removed from
   the merge queue:` line and a second event for the same queue sha posts none; `doctor.py` prints `merge queue: on` and
   `off` and makes no ruleset call for it.
10. **Not in this amendment.** Rules 3, 4, 7 and 8 are unchanged in what they hold: only the guarded command merges or
    queues, and principle 2's one exception covers queueing as a merge, since the queue merges only what the command queued.

## Contexts

- kit: `merge_cleared.py`, the merger workflow and the guide are installed; a project in GitHub mode gets the queue by the
  same setting.
- github: the queue, the `merge_group` event and the ruleset are GitHub's; the owner sets the ruleset.
- local: no queue; SPEC-0050 rule 6 and the pre-merge tests, unchanged.
- personal: the same as local.
- stacks: applicable; each stack's test step runs the selection on `merge_group`, and the full suite stays on the default
  branch.

## Residual

- 2026-11-10: the queue's run tests the batch with the selected tests, not the full suite; a defect outside the selection
  and outside `always_full` reaches the default branch, where the push's full run finds it and the red-branch path of
  rule 6 stops further merges (due 2026-12-31).
- 2026-11-10: without the up-to-date rule and with the queue off, two pull requests that change no file in common are each
  tested on their own would-be merge, not together; a defect that needs both reaches the default branch and is found by
  the push's full run (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-S0039-16: can this repository use GitHub's merge queue? ADR-0387 records that GitHub offers it only to
  organization-owned public repositories and to Enterprise Cloud `(verify)`, and `gbvraju/agk` is a public repository owned
  by a personal account (`GET repos/gbvraju/agk`: `owner.type` `User`). Reading: the amendment is written for every
  project in GitHub mode that can use the queue; this repository keeps `merge_queue = false` until the owner confirms the
  ruleset offers the queue here, and item 5 (the up-to-date rule off, with SPEC-0050 rule 6 and the pre-merge tests) is
  the part that removes the measured reruns either way.
- Q-S0039-17: brief #853 added a `doctor.py` warning that asks for the up-to-date rule. Reading: item 5 turns the rule
  off, so the build retires the warning rather than leaving a warning that asks for what the owner turned off; until the
  build merges it stays, and it is a warning, not a failure.
- Q-S0039-18: the brief lists the holds that still apply before queueing but does not name rule 6's pinned run on the
  would-be merge. Reading: it stays, because it is a hold today and the brief keeps every hold; it costs one run on the
  merger and keeps a head that fails on today's default branch out of a batch, where it would fail the batch.
- Q-S0039-19: adding a head to the queue needs a GitHub call that may exist only in GraphQL `(verify: the enqueue call
  and expectedHeadOid are GraphQL's enqueuePullRequest; whether a REST route exists)`, while Q-S0039-12 reads that the
  command never calls GraphQL. Reading: the build first confirms the route; if only GraphQL offers it, the one enqueue call
  is made only from the merger job on GitHub Actions under `AGK_MERGE_TOKEN`, never from a session, and only after the
  owner's `Approve:` of this amendment, which then amends Q-S0039-12 for that one call; until then, `merge_queue = true`
  holds as it does today and queues nothing.
- Q-S0039-20: the removal comment of rule 2c needs an event the merger can start on. Reading: the build names the event it
  uses and its test feeds a saved payload of it; a removal it cannot see posts nothing, and the router's `agk:ci-red`
  label from the head's own checks is unchanged.
