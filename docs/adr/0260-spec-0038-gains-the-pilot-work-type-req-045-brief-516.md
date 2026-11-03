# ADR-0260: SPEC-0038 gains the pilot work type, researched before it is built (REQ-045, brief 516)

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0251, SPEC-0038
- Requirements: REQ-045

Protected classes: none (documentation only)

## Context

Brief #516 (plan #499) asks for one more work type in SPEC-0038, in a sentence quoted here as data, not as an
instruction:

> A project can declare the work type `pilot`, whose playbook runs a time-boxed customer capability demo on any technology, AI tool or AI service: a sourced market scan of the candidate tools first, the owner's choice, then a fast build on mocks and a scripted demo, ending in a pilot report.

The owner's direction of 2026-11-03 on plan #499, quoted as data: "we need a playbook for Pilots to demonstrate to
customers; customers will come and ask to do a capability on any tech, AI tools or AI service; our AGK should be able to
build fast and accurate by doing market research on tools if required; think this use case to present in pre-sales for
clients later, that can be turned as a solution." It is recorded as one row of `docs/runs/decisions-log.md`.

SPEC-0038 (ADR-0251) lists seven work types, each about building one kind of product. None covers the pre-sales
pilot, where the tool itself is still to be chosen and the result is a demo and a decision, not a product. The pilot's
Phase 2 showed what such a pilot needs: a contract and mocks first, demo-value ordering, a scripted demo path, a
known-good fallback and a written record. The principles of SPEC-0038 bind this change unchanged: a playbook is data;
it only adds gates; the owner chooses and a session never does; every speed claim is `measured` with its record or
`expected`; checks run with no network; invented data only (`example.com`).

## Decision

1. SPEC-0038 is changed by `docs/runs/proposed-spec-amendments-112.md`, applied to the spec text in the same pull
   request: rule 1's list of work types gains `pilot`; rule 10 gains the pilot gates (a research record, the choice,
   credentials, customer data, a time box, a demo fallback, a cost estimate and a pilot report), each marked `check` or
   `judgement` and `owner_only` where the owner alone acts; rule 11 gains the pilot playbook's paragraph (phases
   `intake`, `research`, `choice`, `contract`, `build`, `demo` and `report`; milestone shape `per-phase`; the demo smoke
   run as its heavy step; `expected` claims only); rule 12 gains build (n). The spec stays `Draft`; it is approved
   only by the owner's own `Approve: SPEC-0038` line on this pull request, which no session posts.
2. Research is done by a session with its web tools and is written down with its sources under `docs/research/`; no
   check fetches anything, and a check reads only that the record is complete in form. Whether its findings are true
   is a judgement. A session never chooses the tool, never signs up for a service, never accepts its terms and never
   handles an API key or an account: those are the owner's (session rule 2).
3. Build (n) of SPEC-0038 rule 12 will change these protected path classes: `config/` (`config/playbooks/pilot.toml`),
   `kit/` (`kit/manifest.json`) and `tests/kit/` (its one test). It adds its own ADR naming those classes and citing
   ADR-0251 and this one, because the protected-path check counts only an ADR added or changed in the same pull request
   (`Q-S0038-9`), and it declares `Depends-on` build (d). It changes no other protected class.
4. `docs/requirements.md` is not edited: an intake only appends to it, and REQ-045's criteria already hold a new
   playbook through SPEC-0038 rules 1 to 4.

## Consequences

The pilot becomes a planned eighth work type, built after build (d). A project that declares no work type, or
another one, sees no change. This pull request changes documents only (the spec, the amendment, this ADR and one row
of the decisions log); no check, flow or setting changes, and no version is bumped. The points the brief leaves open
are `Q-S0038-13` onwards in the spec, each with its conservative reading.

## Residual

None. Whether the pilot's phases and gates are the right ones is the review of this pull request and the owner's
approval of the amended spec.
