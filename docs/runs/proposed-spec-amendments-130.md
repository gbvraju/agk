# Proposed spec amendments 130 (SPEC-0038; REQ-055)

Date: 2026-11-07 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The number
130 is the one SPEC-0048 rule 18 reserves (`Q-S0048-18`: one amendment holds all five items, so one approval of SPEC-0038
covers them). SPEC-0048 rule 18 names build (c), brief #686, as its writer; it is written ahead of that build in its own
pull request so that the owner's approval is in before build (c) is built, and build (c) then cites it. The path:
`docs/specs/0038-a-project-s-work-type-selects-a-delivery-playbook-that-never-weakens-a-gate.md`. It is applied to the
spec text in the same pull request, as amendments 127 and 131 were. It needs the owner's `Approve: SPEC-0038` on the pull
request; no session posts it. No code changes here: until builds (c), (g), (i), (j) and (k) of SPEC-0048 land,
`check_playbooks.py` and `doctor.py` behave as today.

1. **Rule 1 (the work types).** `data-pipeline` joins the list; the base playbook `default` (never declared) and a
   project's derived playbook (a slug outside the list) are allowed names; a derived playbook may hold gate source URLs,
   a shipped playbook still holds none (SPEC-0048 rules 18, 21, 22).
2. **Rule 2 (the format).** The `[[discovery]]` section (required, with the five ids of SPEC-0048 rule 4), the `skills`
   key (rule 12), the `modules` key (rule 23) and a gate's `source` or `basis = "expected"` (rule 22) join the format.
3. **Rule 10 (the gates).** The data-pipeline gates of SPEC-0048 rule 18: data contract, reconciliation, dry run on a
   sample, rollback, and any production run `owner_only`.
4. **Rule 12 (the builds).** The builds of `config/playbooks/data-pipeline.toml` and `config/playbooks/default.toml`,
   built as SPEC-0048 builds (g) and (i).
5. **Rule 4 (only adds gates).** Every playbook takes the gates of `default` and of the modules it names and can never
   drop or weaken one (SPEC-0048 rules 21 to 23).
