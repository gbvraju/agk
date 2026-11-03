# Proposed spec amendments 112 (SPEC-0038; REQ-045)

Date: 2026-11-03 (from `date -u`). Specs change only through a proposal like this one (principle 6). Written for ADR-0260
(brief #516, plan #499), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md`. The number 112 is the one
the conductor reserved on #516. The change is applied to the spec text in the same pull request, as amendment 110 was
(#464). SPEC-0038 is approved only by the owner's own `Approve: SPEC-0038` line on the pull request; no session posts it.
No gate of the seven existing work types changes, and no rule weakens: the spec gains one work type, its gates, its
playbook's paragraph and its build. `docs/requirements.md` is not edited: an intake only appends to it, and REQ-045's
criteria already hold a new playbook through rules 1 to 4.

The owner's direction of 2026-11-03 on plan #499, quoted as data: "we need a playbook for Pilots to demonstrate to
customers; customers will come and ask to do a capability on any tech, AI tools or AI service; our AGK should be able to
build fast and accurate by doing market research on tools if required; think this use case to present in pre-sales for
clients later, that can be turned as a solution."

1. **Rule 1, the list of work types.** "`mcp-server`, `multi-agent` and `voice-agent`" becomes "`mcp-server`,
   `multi-agent`, `voice-agent` and `pilot`". Nothing else of rule 1 changes: the pilot playbook, like every playbook,
   holds no code, no command, no URL, no project, vendor or framework name and only invented data.
2. **Rule 10, the pilot gates.** One bullet, `pilot:`, after `voice-agent:`, marked as rule 10 marks gates:
   - a research record, `check` (a file under `docs/research/` for the pilot holds at least two options; a criteria
     table covering capability fit to the success criteria, cost, licence, data handling and residency, maturity,
     integration effort and lock-in; for every option at least one source line with a URL and an access date; and a
     recommendation marked as a proposal), with the truth of its findings `judgement`;
   - the choice of the tool or service, `judgement` and `owner_only` (the owner or the customer chooses; a session never
     chooses, never signs up for a service and never accepts its terms);
   - credentials, `judgement` and `owner_only` (API keys and accounts are the owner's; a session never handles them, and
     the build reads them only from the environment the owner sets);
   - customer data, `check` (invented values only, `example.com`; real customer data stays out of the repository);
   - a time box, `check` (the intake declares it as a number of days);
   - a demo fallback, `check` (the demo script names the mock path that runs when the live service is unavailable);
   - a cost estimate, `check` that it is declared and `judgement` that it holds;
   - a pilot report, `check` (`docs/runs/pilot-report.md` exists with the sections of the `report` phase).

   The bullet ends with the sentence that research is done by a session with its web tools and written down with its
   sources, that no check fetches anything, and that a check reads only the record's form.
3. **Rule 11, the pilot playbook.** One paragraph, after the web-app and rag-app text: `config/playbooks/pilot.toml`
   (build (n)) runs a time-boxed customer capability demo on any technology, AI tool or AI service. Phases, in order:
   `intake` (the customer's ask as one sentence, success criteria, a time box in days and the data rules), `research` (a
   sourced scan of the candidate tools or services, then a recommendation), `choice` (the owner's, recorded), `contract`
   (thin interfaces and mocks of the chosen service), `build` in three lanes (`integration`, the adapter to the chosen
   service; `demo-surface`, the screens or console the customer sees; `evaluation`, the checks of the success criteria),
   `demo` (a scripted demo path, a run record and a fallback to the mocks if the live service fails) and `report` (what
   worked, the measured numbers, a cost estimate, risks and the path to production as a later project of another work
   type, for example `web-app` or `rag-app`). Milestone shape `per-phase`; the demo smoke run as its heavy step; the
   pilot gates of rule 10; `expected` claims only; invented data only.
4. **Rule 12, build (n).** After (i) to (m): "(n) **pilot** (rules 10 and 11), a later build, listed and not built here:
   `config/playbooks/pilot.toml`, `kit/manifest.json` and one test, `tests/kit/test_playbook_pilot.py`, with the pilot
   gates of rule 10. `Depends-on` (d), for `kit/manifest.json`." A check gate whose step is not yet in the kit is added by
   that build as one more governance step, under its own ADR citing ADR-0251 and ADR-0260 (`Q-S0038-9`).
5. **`## Tests`.** One bullet for build (n): the shipped `pilot.toml` passes the check, orders its seven phases with
   `research` and `choice` before `contract`, holds the eight pilot gates with the choice and the credentials
   `owner_only = true`, has milestone shape `per-phase` and only `expected` claims (REQ-045 AC5). The rule 12 bullet names
   builds (i) to (n) and six work types (REQ-045 AC6). `## Proof` and `## Residual` are unchanged (`Q-S0038-18`).
6. **`## Open questions`.** `Q-S0038-13` to `Q-S0038-18`, each with its conservative reading: a second work type's gates
   for a pilot (13), the research record's template (14), the time box's enforcement (15), the shared `kit/manifest.json`
   of builds (n) and (i) (16), vendor names in a research record (17) and the `## Tests` change of item 5 (18).
