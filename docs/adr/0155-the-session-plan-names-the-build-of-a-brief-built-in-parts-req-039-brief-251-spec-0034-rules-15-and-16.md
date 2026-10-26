# ADR-0155: the session plan names the build of a brief built in parts (REQ-039, brief 251, SPEC-0034 rules 15 and 16)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0153, ADR-0154
- Requirements: REQ-039

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #251 (priority 2, seen in the review of #250): `session.py plan` names a brief but not a build, and `launch.py` prompts `session.py claim --brief <n>` with no `--build`. A session launched on a brief with several builds (such as #244 and #247) could claim the whole brief, repeat a build already merged, or take a build that waits for another. The tests were written first.

## Decision

1. **The `Builds:` line.** A brief built in parts may carry `Builds: (a) the first part; (b) the second part`. `session_plan.builds_of` reads it; a brief with no such line is planned as before (no `build` in the plan, the prompt unchanged).
2. **The next free build.** The plan names the first build that is not merged, has no live take and has no open pull request. A merged build is a merged pull request whose **title** says `brief #<n> build (<x>)`, as every builder title does (the verdict on 6ef8389: a body that says "build (b) is not in this pull request" must not mark build (b) done, so free text is never read); an open one keeps the build from being named again. A take of the whole brief names no build (the brief stays taken, as before). A taken brief with builds is still read, so that an independent build can start while another is in progress.
3. **The order.** A build waits for the nearest unmerged build before it unless the text of its `Builds:` item starts with `independent:`. The plan says so in words (`#244 build (b) waits for build (a)`) and in the data (`waits`: `brief`, `build`, `waits_for_build`, `why`). A brief whose builds are all merged starts nothing and is listed as skipped (`every build is merged; the conductor closes it`).
   **A brief never disappears from the plan without a word:** every open brief that the plan does not start is in `waits` or `skipped` with its reason (`no free slot`, `the merge queue is above your merge rate`, `every build is taken or in progress`, or the reasons above).
4. **The plan and the prompts.** `start` carries `build` for a brief with builds; the words say `builder-a takes #5 build (a)`. `launch.py` prompts `session.py claim --session <s> --brief <n> --build <x>` and says `build (<x>) of brief #<n>`; a build that is not a name is refused naming the field; the adapter gets `AGK_BUILD`. A brief without builds gets today's prompt.
5. **A take whose session moved on** (the verdict on 39b7f9a). For a brief built in parts, a live take stops holding the brief when its session has a later `taken:` on a different brief: its work there is finished and the hold has no purpose, so the plan offers the next build at once. A take whose session has not moved on still holds the brief, and the plan says so in words with the hour it ends: `#244 build (b) is held for builder-a until 18:02 UTC` (the later of the take and the merge of the brief's pull request, plus `claim_hours`), or `while its pull request is open`. Every skip `taken by X` says the same (`taken by X until 18:02 UTC`). A brief without a `Builds:` line keeps its take as SPEC-0034 rule 5 says: this is a reading of the plan, not a change of `next` (Q-251-4).
6. **Another build of the same brief is not a rival.** The overlap of `Touches:` between a brief and its own running build (a take or an open pull request of the same brief) is not counted, since the build rule orders them.
7. **Readings taken where the brief leaves a point open** (the most conservative each, as questions on the pull request): the marker of an independent build is the text `independent:` at the start of its item (the brief names no form); an open pull request that names a build counts as that build in progress; the nearest unmerged build before it is the one a build waits for. No spec rule changes, so no amendment: the rules 15 and 16 of SPEC-0034 are read as they are. Flow mode: fragment `changelog.d/plan-names-the-build.md`; no version bump.

## Consequences

- A session launched on a brief built in parts claims exactly the build the plan named.
- An independent build can run beside another build of the same brief.

## Residual

- 2026-10-26: `next` still takes a whole brief, not a build; only a conductor assignment or `/agk:launch` claims a build (due 2026-12-31).
