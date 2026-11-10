# Proposed spec amendments 150 (SPEC-0032, SPEC-0036, SPEC-0006; REQ-039)

Date: 2026-11-10 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for brief #846, answer 6 (spec first). The paths:
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md` (rules 2, 3, 8 and 13),
`docs/specs/0036-whenever-a-pull-request-changes-state-the-project-publishes.md` (rule 2) and `docs/specs/0006-doctor.md`
(rule 5, one row only). The number 150 is the one brief #846 reserved. This amendment is not applied to the spec text in
this pull request; the owner decides it, and it needs a person's `Approve: SPEC-0032`, `Approve: SPEC-0036` and
`Approve: SPEC-0006`; no session posts them, and no build starts before them.

What the code does today (main 0164281): `route.py` `decide` sets one of seven labels in the order conflict, ci-running,
ci-red, approve, fix, ready, review (the code puts approve before fix; SPEC-0032 rule 2 says fix before approve). It
reads no draft flag: `decide` on a draft with green checks and no verdict returns `agk:review`, although SPEC-0033 rule
11 records that "the router gives a draft pull request no review label". Every state label has the one description "AGK:
the state of a pull request". `agk:parked` already exists, as a label of a brief that `next` does not offer, and
`merge_cleared.py` already holds a pull request labelled `agk:hold`. No "AGK status comment" exists: SPEC-0032 rule 8
says the router posts no comment, apart from the narrow replies its later amendments name.

1. **SPEC-0032 rule 2, the states and their actors.** Replace the seven labels with eleven, each set by `route.py` from
   facts it reads with GET, exactly one at a time, and each with a GitHub description that names its actor in the form
   `AGK: <actor> acts next: <what>`:
   - `agk:build` (builder): the pull request is a draft, or the body has a `Brief: #n` line and no `Report:` by the
     pull request's author on the head says `ready for review`, `fix list applied` or `merge of main` (`Q-846-3`);
   - `agk:ci-running` (checks): a required check of the head has not completed, as today;
   - `agk:ci-red` (builder): a required check of the head failed, as today;
   - `agk:conflict` (builder): `mergeable_state` is dirty, as today (`Q-846-5`);
   - `agk:review` (conductor): a `Report:` of the first item on the head, checks green, no verdict by a listed author
     names the head, and the other cases where `decide` returns `agk:review` today (an unreadable conductor line,
     brief #854);
   - `agk:fix` (builder): the latest verdict names the head and is a fix list or a rejection, as today;
   - `agk:question` (owner): the newest `Owner needed:` comment by a listed verdict author on the pull request has no
     later `Maintainer answer:` or `Approve:` by an account in `spec_approvers` and no later head (`Q-846-4`);
   - `agk:approve` (owner): a spec approval the head needs is not posted, as today;
   - `agk:owner-merge` (owner): cleared or covered on the head, checks green, approvals in, and the pull request changes
     a path of the list `merge_cleared.py` refuses to merge (SPEC-0039 rule 5: `constitution/`, `config/reviewers.yaml`,
     the ruleset class, `scripts/agk/ruleset.py`, `.github/workflows/`), one list read by both;
   - `agk:merge-ready` (merger): cleared or covered on the head, checks green, approvals in, no such path;
   - `agk:parked` (owner): a person put the label on the pull request (`Q-846-1`).
   When more than one holds, the first of this order wins: `agk:parked`, `agk:build`, `agk:ci-running`, `agk:ci-red`,
   `agk:conflict`, `agk:review`, `agk:fix`, `agk:question`, `agk:approve`, `agk:owner-merge`, `agk:merge-ready`. This is
   the brief's order, except that `agk:parked` comes first, because the router never sets or removes it and a hold the
   router overrode would not hold (`Q-846-1`). A merged or closed pull request keeps its last label, as today.
2. **SPEC-0032 rule 2, the rename without a gap.** `agk:ready` is replaced by `agk:merge-ready` or `agk:owner-merge`.
   `session.py queue`, `session_plan.py`, `merge_cleared.py --sweep`, `conductor.py sweep` and `uninstall.py` read
   `agk:ready` as `agk:merge-ready` until the first kit release after the build that makes the change, and the build
   after that release removes the old name. The router never sets `agk:ready` again; it removes it as one of the other
   labels.
3. **SPEC-0032 rule 2, one reader.** `route.py` has one function `pr_state(facts) -> (label, actor)`, the present
   `decide` extended by item 1. `session_plan.py`, `merge_cleared.py --sweep` and `conductor.py sweep` call it on facts
   they read with GET, or read the label the router set, and none counts a label by a rule of its own. The plan's
   verdict wait (ADR-0384, `waiting_for_verdict`) counts `agk:review` only, which by item 1 never holds a draft.
4. **SPEC-0032 rule 3, the queues.** `queue --role builder` lists `agk:build`, `agk:ci-red`, `agk:conflict` and
   `agk:fix` of its author; `--role conductor` lists `agk:review` and `agk:ci-red` (not drafts), as today; `--role
   person` lists `agk:question`, `agk:approve`, `agk:owner-merge` and `agk:parked`; a new `--role merger` lists
   `agk:merge-ready`. `watch` ends on a change between any two of the eleven labels, as today.
5. **SPEC-0032 rule 2, the age of a state (answer 4).** The state's start is the `created_at` of the newest `labeled`
   event of the current state label in the pull request's events (one GET), or `unknown` when it cannot be read, never
   the time of the run. `route.py --pr N --dry-run` prints `State: agk:<state> (<actor>) since <UTC time>, <m> min`.
   `conductor.py sweep` prints `STUCK #<n> agk:<state> <actor> <m> min` for each state older than `stall_minutes` of
   `[flow]`, owner rows first, then builder, conductor, merger and checks; an `unknown` age is printed as `unknown` and
   is never listed as stuck. Where the line lives on GitHub is `Q-846-2`: until the owner rules, the router posts no new
   comment (rule 8 stands) and the line is in the pipeline document (item 7).
6. **SPEC-0032 rule 8, every mode (answer 5).** GitHub projects get the labels and descriptions through the kit's
   `route.py`, which creates a missing state label with its description, as it creates the seven today. Local and
   personal modes have no router and no labels: `session.py plan` and `route.py --pr N --dry-run` print the same
   state, actor and age lines from the same function.
7. **SPEC-0036 rule 2, the pipeline document.** Schema 2 of `kit/pipeline-schema.json`: `ready` holds the pull requests
   labelled `agk:merge-ready` or `agk:owner-merge`, each with a new field `actor`; each item of `ready` and `approve`
   gains `state`, `actor` and `since` (`unknown` when it cannot be read); `counts` holds exactly `build`, `review`,
   `fix`, `ci-red`, `conflict`, `question`, `approve`, `owner-merge`, `merge-ready` and `parked` (`agk:ci-running` is
   still not counted). The raised schema number carries a `Readers:` line, as rule 7 asks; no reader exists yet.
8. **SPEC-0006 rule 5, one doctor row (a consequence of items 1 and 2).** `doctor.py` has one row `state-labels`,
   severity `warn`, when a state label of item 1 is missing in the repository or its description does not name its
   actor, reading the labels with one GET; a local or personal project prints `not applicable`. It never fails the run.
9. **SPEC-0032 rule 13, the builds.** Two builds, tests first with saved pull request payloads, each about 300 changed
   lines or fewer, from the default branch: (a) items 1 to 4 and 8, in `tests/kit/test_pr_state_lifecycle.py`, with
   ADR-0385 or a `Covered-by:` line; (b) items 5 to 7, in `tests/kit/test_pr_state_age.py`, with an ADR the conductor
   reserves. Build (a) waits for brief #842's open builds where both change `session_plan.py` (`Depends-on`).
10. **Not in this amendment: the two co-owner comments of 2026-11-09.** The cost rules (no new job or trigger; the router
    and the merger as one job; a sparse checkout; `metrics.py` reporting the router's and merger's minutes) and answers
    7 to 10 (the conductor running `route.py --all` between events, the action for each stuck state, the live board on
    the plan issue, the weekly minutes by state) change a workflow, the conductor's guard and `merge_cleared.py`'s
    callers, which neither build of item 9 touches. They are proposed as a later amendment for builds (c) and (d)
    (`Q-846-6`); nothing in items 1 to 9 adds a job, a trigger or a step to a workflow.
11. **Unchanged.** `constitution/`, the ruleset, the required checks and the workflows are not touched. The router
    still runs no agent, merges nothing and reviews nothing. A state label set with the job's token starts no
    workflow, as today.

## Questions

Each is open until a person rules; the reading after it is the conservative one the items apply.

- **Q-846-1, for the owner:** `agk:parked` already names a brief that `next` does not offer, and `merge_cleared.py`
  already holds a pull request labelled `agk:hold`. The brief lists `agk:parked` last, so it would never win over
  another state. Reading: one label, `agk:parked`, means "a person holds it" on a brief and on a pull request alike; the
  router never sets or removes it, it wins over every state, and `merge_cleared.py` reads it as it reads `agk:hold`,
  which stays as it is.
- **Q-846-2, for the owner:** answer 4 puts the age in "the pull request's AGK status comment (SPEC-0036)". No such
  comment exists, and SPEC-0032 rule 8 says the router posts no comment. Reading: no new comment; the line is printed by
  `route.py --dry-run` and `conductor.py sweep` and stored in the pipeline document. A comment edited in place by the
  router needs the owner's yes and a further amendment to rule 8.
- **Q-846-3:** a pull request a person opens has no `Report:`, so "no ready `Report:` yet on the head" would hold it at
  `agk:build` for ever. Reading: the `Report:` test applies only to a body with a `Brief: #n` line; a draft is
  `agk:build` whatever its body.
- **Q-846-4:** "an open `Owner needed:` or maintainer question" is not defined, and a `Question:` asks the conductor,
  not the owner (session rule 17). Reading: as item 1, an `Owner needed:` comment by a listed verdict author on the pull
  request, closed by a later `Maintainer answer:` or `Approve:` by an account in `spec_approvers`, or by a new head.
- **Q-846-5:** answer 1 also gives `agk:conflict` for "its merge of main is due", which no fact the router reads
  defines. Reading: `mergeable_state` dirty only, as today; a due merge of main stays the merger's `behind` line.
- **Q-846-6, for the owner:** answer 6 names two builds; the two co-owner comments add work that changes a workflow
  (which a build changes only with the owner's yes quoted in its brief) and the conductor's guard. Reading: they are
  not in builds (a) and (b); they wait for their own amendment and builds, and this brief is not finished by them.
