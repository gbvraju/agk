# ADR-0117: K5 opens for the conductor plan, and the record names exactly what it opens (brief #194)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Amends: ADR-0053
- Related: ADR-0060, ADR-0025, ADR-0105
- Requirements: REQ-036, REQ-037, REQ-038, REQ-039, REQ-040, REQ-041

Protected classes: none (documentation only)

## Context

The decision recorded here is the maintainers', taken on 2026-10-24; this text was written on 2026-10-25 from their brief #194, which is its only source. ADR-0053 decision 2 says "Everything else in the register still waits for the K5-opening ADR proper", and ADR-0060 decision 4 says "every other candidate in the residual register still waits for the K5-opening ADR proper"; the
proper ADR is due after criterion a and the first outside developer's run (ADR-0053 residual, 2026-11-30). Since 2026-10-24 the maintainers have run the conductor plan, by intake and review, and a part of it is built. No ADR records that decision, so the repository's own record says less was opened than was built. Builder A met the gap on #191 (Q-K4-271) and the conductor
sent it to the maintainers.

## Decision

1. **This ADR is the record.** It records that the maintainers opened K5 for the conductor plan on 2026-10-24, and it amends ADR-0053 decision 2 by naming what is opened. ADR-0060 decision 4 carries the same sentence and is amended in this text only, because `check_adrs` accepts one ADR in `Amends` (the reading ruled for Q-K4-215, as ADR-0060 itself did); neither ADR is edited.
2. **What it opens, exactly:**
   - the conductor plan's lane A, the conductor protocol (brief #163); lane C, the engines, vision, stack and design (brief #164); lane E, parallel builds; and lane F, the separation of identities (lanes E and F are named in brief #194; no brief of them was readable to the author, see the question);
   - the changelog fragments of flow mode (REQ-038);
   - the briefs that came out of the run: #176 (REQ-041, work management for parallel sessions), #179 (REQ-039, GitHub events label each pull request, people approve specs, a red default branch stops new work), #180 (the governance base is the first parent of the merge ref), #182 (REQ-040, work survives a session that stops mid-task), #183 (an optional merger role, off by default, built after lane F), #185 (the red default branch of 2026-10-25), and the `Flow` section of the weekly report (build (d) of SPEC-0034), which is built once this ADR is Accepted.
3. **The requirements already built under it**, so that the record matches the history: REQ-036 (lane C; intake #166; builds #168, #170, #173, #174, #178), REQ-037 (lane A; intake #167; builds #169, #172, #175, #184) and REQ-038 (fragments; intake #177; build #181). Also merged under the opened briefs: #186 (brief #185) and #188 (brief #180). Opened and in progress: REQ-039 (intake #187, build #193), REQ-040 (intake #189, part a #192) and REQ-041 (intake #191).
4. **What stays closed.** Every other candidate in `docs/runs/residuals.md` still waits for the K5-opening ADR proper. No new kind of report section and no portal action is opened beyond the ones named above.
5. **What stays the proof.** The friends launch (the guide's hosted steps 8 to 12 on a tagged release, on 2026-11-27 as ADR-0053 records it) and the phase 2 dogfood run of ten pull requests. Nothing is called autonomous until the shadow review measures the conductor's catch rate (SPEC-0023 rule 8 sets the shadow measure for the review agent; ten pull requests are a small sample, as its residual says).
6. **The register is not edited by this ADR.** `docs/runs/residuals.md` keeps every line as it is, including the K5-opening ADR proper (due 2026-11-30). Two lines name candidates whose substance the opened work builds, "collision-proof parallel agents" (REQ-041) and "session continuity from the repository" (REQ-040); whether they move to `in progress, ADR-0117` is the maintainers' ruling (Q-K4-272).
7. **Approval.** The status is Proposed. It becomes Accepted on the maintainers' word, as the `Final:` line of a verdict.

## Consequences

- The record and the history agree: what was built under the conductor plan is named as opened, with the requirements and the pull requests.
- Build (d) of SPEC-0034 (the `Flow` section) no longer waits for an ADR once this one is Accepted; the rest of K5 keeps waiting.
- Nothing is built by this pull request: it is documentation only.

## Residual

- 2026-10-25: lanes E and F are named in the brief and their briefs were not readable to the author; if either has a scope that differs from "parallel builds" or "the separation of identities", this record is corrected before it is Accepted (due 2026-11-30).
- 2026-10-25: the phase 2 dogfood run of ten pull requests and the conductor's catch rate are named in the brief; no earlier document in this repository defines the run, and SPEC-0023 rule 8 measures the review agent, not the conductor (due 2026-12-31).
- 2026-10-25: the K5-opening ADR proper, for every other candidate, stays due as ADR-0053 records it (due 2026-11-30).
