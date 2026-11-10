# Proposed spec amendments 160 (SPEC-0023, SPEC-0035; REQ-046, REQ-054)

Date: 2026-11-10 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0430 (brief #1012), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0023-the-architect-role-reviews-every-pull-request-by-one-written.md` and
`docs/specs/0035-a-second-reviewer-reviews-the-same-pull-request-heads-as-the.md`. The number 160 is the one brief #1012
reserved. This amendment is not applied to the spec texts in this pull request, which the brief limits to documents for
the owner's decision; the builds of this amendment (briefs #1013 and #1014) write it into both texts. The owner decides it with `Approve: <head> SPEC-0023` and
`Approve: <head> SPEC-0035` on this pull request; no session posts them.

The sentence (brief #1012): "The verdict that gates a merge comes from a fresh reviewer session that sees only the change,
its brief and the rulings on it (a goldfish), not from the conductor that planned and assigned the work; the conductor
routes, answers and merges; the shadow samples the reviewer's verdicts to measure them."

The owner's direction, quoted as data (brief #1012, 2026-11-10 21:30 IST): "Think through AGK, AGK shadow and goldfish,
best and easy adopt it our framework architecture, create brief for new milestone, don't combine with ongoing scope, need
best approach it should help us in any one or most of our nine checklist."

The source of the idea (brief #1012): the Elephant-Goldfish Model, Apache-2.0 `(verify: the licence and the repository
github.com/google/elephant-goldfish-model are the brief's, not read by this session)`. Its rule as the brief gives it: the
reviewer sees the work product and its sources, never the conversation that produced it, and the tool refuses to review
when it cannot start such a reviewer. No text or code of it is copied here.

Measured (brief #1012): on 2026-11-10, every gating verdict came from the conductor's long-context run; #965 waited 81
minutes for a verdict, and 6 red default branches followed cleared heads; the shadow issue #219 has 0 comments (read by
this session: `GET repos/gbvraju/agk/issues/219`, `comments` 0).

## What is on the default branch today

- SPEC-0023 rules 1 and 2: the read-only review agent `.claude/agents/architect-review.md`, with the guard
  `.claude/hooks/architect_guard.py --review`, "never in the session that built the change". No scheduled task starts it.
- `scripts/agk/review_context.py`: a deterministic, network-free review document for one head (the body, numbered hunks,
  the changed files, the advanced requirements, the protected classes, the cited specs and ADRs, the principles).
- SPEC-0035: the blind shadow on the `agk-shadow` issue, graded by `Marks:` and `scripts/agk/shadow_count.py`. It gates
  nothing.
- The conductor reviews every ready head itself, in the same run that files briefs, answers questions and posts `Assign:`.

## Items

1. **SPEC-0023, a new rule 2a "the gating review" (after rule 2).** "A gating verdict on a pull request, `Verdict: cleared
   <sha>` or `Verdict: fix list <sha>`, comes from a review session started for that one head, that:
   - runs the `architect-review` agent (rule 1) with its guard;
   - runs on the `strongest` tier (SPEC-0045);
   - holds a reviewer slot, `r1` or `r2` (item 4), by the same lease as a builder slot (SPEC-0034);
   - pushed no commit to the branch of that pull request, and is not the conductor's run.
   A session that cannot meet all four posts no verdict on that head. `Verdict: rejected <sha>` follows the same rule." The
   first two conditions are checked from the slot's lease line, the third from the branch's commits against the slot's
   holder, and the fourth from the lease name: a lease that starts `r` is never the conductor's
   `(verify: the conductor holds no slot lease today; the build reads the lease lines to confirm it)`.
2. **SPEC-0023, a new rule 2b "the goldfish bundle".** "The review session reads only:
   - the document `review_context.py` prints for the head;
   - the brief's body (the issue the `Brief: #n` line names);
   - the ruling lines on the brief and on the pull request, by a listed verdict author or a reviewer of
     `config/reviewers.yaml`: `Answer:`, `Correction:`, `Maintainer answer:`, `Approve:`, and the prior `Verdict:` lines
     on that pull request only;
   - the checks and statuses on the head.
   It never reads a `Progress:` comment, the narrative of a `Report:` (only its first line's head), a `Conductor report`,
   an `Assign:` or `Request:` line, the plan issue or any other issue, or a session transcript. The verdict's `Read:`
   line (rule 4) lists the bundle's parts by name; a verdict whose `Read:` line names a part outside the bundle is void."
   The build adds `python3 scripts/agk/review_context.py --bundle --pr <n> --sha <head>`, which prints the four parts and
   nothing else from saved or fetched GET responses, so the session needs no other read (build (a), brief #1013).
3. **SPEC-0023 rule 2c, the conductor (and the conductor role file).** "The conductor, when a head is ready and its checks
   reported, posts one comment `Review: <rN> #<pr> <40-hex head>` on the one open issue labelled `agk-conductor`, naming a
   live reviewer slot, never the same line twice for one head. It answers questions, posts `Assign:` lines and merges by
   SPEC-0039 as today. It posts no gating verdict itself, with one exception: while no reviewer slot is alive
   (`slot_seen_minutes`, the setting builders use), it posts `Verdict: <kind> <sha> (conductor fallback)`, which counts as
   gating, so the flow never stops. A fallback verdict is a verdict by a listed verdict author and is read by
   `session.py watch`, `merge_cleared.py` and the metrics exactly as a verdict; the words `(conductor fallback)` are the
   only difference." `session.py slot --next r<N>` prints `review #<pr> <head>` for the newest unanswered `Review:` line
   naming that slot, or `wait`.
4. **SPEC-0023 rule 2d, the reviewer slots.** "The `[flow]` key `reviewer_slots` (an integer from 0 to 9, default 0) names
   how many reviewer slots exist, `r1` to `r<n>`; anything else is refused naming `setting: flow.reviewer_slots`. With
   `0` the conductor's fallback of rule 2c is the only path, and nothing changes from today. A reviewer slot is a
   scheduled task of the person, as a builder slot is; no session creates or fires one." This repository's value is a
   question for the owner (`Q-S0023-1`).
5. **SPEC-0035 rule 1, the shadow samples the reviewer.** Rule 1 is changed: "For every head that a reviewer slot gave a
   gating verdict on, and whose head sha read as a number is `0` modulo the sample divisor, the shadow posts its one
   `Shadow:` comment as today. The divisor is the `[flow]` key `shadow_sample` (an integer from 1 to 20, default 5;
   anything else is refused naming `setting: flow.shadow_sample`); the number is the first eight hex characters of the
   head sha, so the choice is reproducible from the sha alone and needs no state." Rule 2 (blind) is unchanged: the
   shadow never reads the reviewer's verdict, nor the conductor's. A fallback verdict of SPEC-0023 rule 2c is sampled the
   same way. The shadow never gates: a `Shadow:` comment is not a verdict, and nothing reads it as one.
6. **SPEC-0035 rule 3 and 4, the marks name the reviewer.** In a `Marks:` line, `C` is renamed `R` (a finding of the gating
   reviewer, a slot or the conductor's fallback); `C` stays accepted as `R` for marks already posted. `shadow_count.py`
   prints the reviewer's catch rate by the formula of rule 4 with `R` for `C`, and the fallback verdicts in a separate
   column, so the conductor's rate and the slots' rate are never added together.
7. **SPEC-0023 rule 2e, local and personal modes.** "In local mode (`execution = "local"`) and personal mode
   (`forge = "files"`) a review is a new session of the runtime, started with the bundle of rule 2b only. Where the tool
   cannot start a second session, it prints `review: no fresh session; a person reviews` and exits 3, and posts nothing;
   the person reviews. It never falls back to the building session."
8. **SPEC-0023 rule 8a, the measures (for `scripts/agk/checklist.py`, REQ-054).** The amendment defines, each from saved
   GET responses and from the comments above, unknown never printed as zero:
   - under point 5 (auto-merge): review latency, the minutes from the ready event of a head to its gating verdict, as a
     median and a 90th percentile over the window; fix-list rounds per merged pull request; and the count of red default
     branches whose first red run follows the merge of a head that was cleared;
   - under point 9 (cost): tokens per review, from the `Usage:` line each review session ends its verdict with
     (`Usage: <n> tokens` or `Usage: not shown`, as a builder's `Report:`);
   - under point 2 (conductor starts): reviewer slots alive (`slot_seen_minutes`) and the conductor's share of gating
     verdicts, the fallback verdicts divided by all gating verdicts.
   Thresholds for `yes` go in the `[checklist]` table, defaults chosen by the build and recorded in its ADR.
9. **The builds that follow (rule 11 of SPEC-0023).** Tests first, each from the default branch, after this amendment's
   two `Approve:` lines:
   - (a) brief #1013: the bundle (item 2), the `Review:` line and the conductor's fallback (item 3), the reviewer slots
     and the setting (item 4), the local and personal refusal (item 7), the `architect-review.md` text for the bundle, and
     the conductor role file. Its ADR names the protected classes it changes.
   - (b) brief #1014: the shadow's sample (item 5), the `R` marks (item 6) and the measures (item 8) in `checklist.py`.
10. **Tests (for the builds).** Saved GitHub responses and a fake `gh` only, no network and no model:
    - a bundle from a fixture pull request contains the four parts and no `Progress:`, `Report:` narrative, `Assign:`,
      `Request:` or plan-issue text, and is the same bytes on two runs;
    - `slot --next r1` prints `review #<pr> <head>` for its `Review:` line, `wait` without one, and refuses a slot past
      `reviewer_slots`; a malformed `reviewer_slots` or `shadow_sample` is refused naming the setting;
    - a verdict by a session whose holder pushed to the branch is refused by the review helper;
    - with no reviewer slot alive the conductor's text and the fallback marker are read as gating by `watch` and
      `merge_cleared.py`;
    - the sample picks the same heads from the same shas, about one in five over a fixture of shas, and none of a head
      with no gating verdict;
    - `R` and `C` marks count the same; fallback findings are counted apart;
    - each measure of item 8 on a fixture window, and `unknown` for a window without its events;
    - in local mode with no second session the tool prints its line, exits 3 and posts nothing.
11. **Not in this amendment.** SPEC-0039 (the merge) is unchanged: `merge_cleared.py` merges on a gating verdict by a
    listed verdict author, as today. SPEC-0023 rules 3 to 6 (the nine steps, the verdict's shape, the checklist,
    discovery) and rule 8 (the first shadow record) are unchanged.
    No scheduled task is created or changed by any session.

## Contexts

- kit: the agents, `review_context.py` and `session.py` are installed, so every project gets the goldfish gate by the
  same settings; with `reviewer_slots = 0` a project behaves as today.
- github: reviewer slots are scheduled tasks of the person; verdicts stay pull request comments; `Review:` lines live on
  the `agk-conductor` issue.
- local: a review is a new local session started with the bundle only; with no second session, a person reviews.
- personal: the same as local.
- stacks: not applicable; the review reads code and runs no build step.

## Residual

- 2026-11-10: all sessions post from one account, so no check can tell a reviewer slot's verdict from the conductor's or a
  builder's; item 1's conditions rest on the lease lines and the branch's commits, and a session that ignores its role
  file is caught only by a person (due 2026-12-31).
- 2026-11-10: "reads only the bundle" is a written rule; the runtime can still read any file in the checkout, and the
  guard cannot tell a bundle read from another (due 2026-12-31).
- 2026-11-10: a fresh reviewer has no memory of earlier heads beyond the prior `Verdict:` lines; a finding the conductor
  would have remembered from the plan is missed unless the brief or a ruling states it (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-S0023-1: how many reviewer slots? Reading: the default is `0`, so nothing changes in any project until a person sets
  it; this repository is suggested `2` (`r1`, `r2`), set by the owner in `agk.toml` with the two scheduled tasks, after
  build (a) merges.
- Q-S0023-2: the sample rate of the shadow. Reading: one head in five (`shadow_sample = 5`), chosen by the sha; a lower
  divisor costs more shadow runs and is the owner's to set.
- Q-S0023-3: the fallback. Reading: the conductor gives a fallback verdict only while no reviewer slot is alive, never
  because a slot is slow; a `Review:` line unanswered for 60 minutes is shown by `doctor.py` as a warning and does not
  turn the conductor into the reviewer. Whether a slow slot should also fall back is the owner's ruling.
- Q-S0023-4: the brief names `Answer:` as a ruling line, which no rule defines today. Reading: an `Answer:` comment counts
  only when its author is a listed verdict author or a reviewer of `config/reviewers.yaml`; any other is outside the
  bundle.
- Q-S0023-5: `Verdict: rejected` is not named by the brief. Reading: it is gating in effect (it closes the work), so it
  follows the same rule as `cleared` and `fix list` (item 1).
