# Proposed spec amendments 249 (SPEC-0072; REQ-082)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0807 (brief #1948, SPEC-0075 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 2). This file proposes the lines and does not edit the spec. SPEC-0075's build (f), after (d), applies it word for
word, on the owner's `Maintainer answer: amendment 249 approved`; no session posts it.

The sentence (brief #1948), quoted as data: "Intake for the data model on the Day-1 quality path: every project with stored data gets an expert, engine-aware database design from its domain model, curated and cited patterns and its main queries, confirmed by a person on business choices, checked offline and kept in step with each migration."

## Items

1. **SPEC-0072 rule 2, the migrations gate as a check.** At the end of the **Enterprise gates** bullet, after "so every
   work type inherits them." add: "One exception reads a setting: while `[data] migrations` (SPEC-0075 rule 10) names
   the project's migration globs, `run_gates.py` reads the `migrations` gate as `kind = "check"` with
   `step = "migrations"` (`scripts/agk/gates/migrations.py`), which fails an added migration with no way back or no
   test that names it, a merged migration changed later, and a table, column or index that `docs/data-model.md` does
   not name, naming the rule and the path class; with the setting unset the gate stays `judgement` with its reason.
   The playbook files are unchanged, so the no-weakening rule below reads them as today (amendment 249)."

No other rule changes.
