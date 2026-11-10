# ADR-0431: Reviewer slots take `Review:` lines and post the gating verdict from the bundle only (REQ-046)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0020, ADR-0430, ADR-0362, ADR-0425, SPEC-0023, SPEC-0034, amendment 160, brief #1012, brief #1013, plan #661
- Requirements: REQ-046, REQ-054

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `.claude/`, `kit/`, `agk.toml`

## Context

ADR-0430 (Proposed, brief #1012) decides that a gating verdict comes from a review session started for one head that
reads only the bundle, and leaves the build to briefs #1013 and #1014. Brief #1013 is build (a): the bundle, the
`Review:` line, the reviewer slot's next step and the conductor's fallback marker. No Accepted ADR covers these
protected classes, so the build writes its own (session rule 36); 0431 is the brief's `Reserved:` number.

## Decision

1. `scripts/agk/review_bundle.py --pr <n> --sha <40-hex> [--base REF]` prints one document: the output of
   `review_context.py` for that head, the brief's body (the pull request's `Brief: #n`), the ruling comments of the brief
   and the pull request (first line `Answer:`, `Correction:`, `Maintainer answer:` or `Approve:`, and `Verdict:` on the
   pull request), each with its author and time, oldest first, and the conclusions of the head's check runs by name. It
   reads REST with GET only, and of the issues only the brief and the two comment lists. It refuses a sha that is not
   the pull request's head, and a checkout whose `HEAD` is not that sha, naming this ADR. The same replies and the same
   checkout give the same bytes. It is installed with the kit as a fourth path of the `experimental` list of
   `kit/manifest.json` that ADR-0020 decision 2 set, beside `review_context.py`.
2. `session.py` reads `Review: r<N> #<pr> <40-hex>` on the one open `agk-conductor` issue by a listed verdict author.
   `slot --take|--renew|--release|--next r<N>` use the builder slots' lease (ADR-0362, ADR-0425). `slot --next r<N>`
   prints `review pr #<n> <sha>` for the newest of its lines with no `Verdict:` on that head by a listed verdict author,
   and `wait` otherwise; `Pool: stop` by an approver stops it as it stops a builder slot. It prints `stop: reviewer
   pushed this branch`, and releases the lease, when a commit of that pull request names the slot or this run's name as
   a word in its message (body or trailer).
3. A verdict's first line may end ` (conductor fallback)`. `conductor.py check-verdict`, `session.py` (its `watch` and
   slot readers), `merge_cleared.py` and the router (`metrics.VERDICT`, read by `metrics.verdicts`, and
   `common.FIX_LIST`, read by `common.verdict_problem`) read such a line exactly as the same line without it.
4. `.claude/agents/architect-review.md` gains one paragraph for the slot run, with no rise in its rule budget, and the
   review guard's read-only scripts gain `review_bundle`.

## Consequences

- A reviewer slot can be scheduled (operations, after merge) and reviews a head within one run of its `Review:` line.
- The fallback leaves the conductor's verdicts gating while no reviewer slot runs.
- The bundle runs `review_context.py` on the checkout, so a reviewer run checks out the head first.

## Residual

- 2026-11-30: the `[flow] reviewer_slots` count, the marker's `agent:`, `tier:` and `session:` lines and the local and
  personal refusal of amendment 160 items 1, 4 and 7 are not in brief #1013's answers and are not built here (Q-1013-1).
- 2026-11-30: `shadow_rate.py`, `core_audit.py` and `reviewers.py` still read a verdict's first line without the
  fallback ending; brief #1014 owns them, and a shared constant for the first-line grammar (Q-1013-2).
- 2026-11-30: under the review guard the slot run of decision 4 cannot save the bundle file, write `v.md` or run
  `conductor.py check-verdict`, since the guard refuses every write and redirect; reviewer slots wait for the
  maintainers' guard decision before they are scheduled (Q-1013-3, asked of the owner on #661).
- 2026-12-31: "the bundle only" is a written rule; the runtime can read the checkout (ADR-0430 residual).
