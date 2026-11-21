# Proposed spec amendments 198 (SPEC-0072; REQ-079)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0670 (brief #1590), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rules 2, 4 and 9 and the `## Tests`
section). Brief #1590 reserved amendment 198. This file proposes the lines and does not edit the spec. They are applied
word for word, on a person's `Approve: SPEC-0072`; no session posts it.

The sentence (brief #1590): "A product with a work type can no longer pass with no tests: the foundation writes a first
unit and integration test, and a change to product code without a test change is red."

## Why

`default.toml` holds `tests-first` as judgement and `project_tests` passes with no `tests` folder or no test collected, so a
work-type product with no tests passes (gap G17). Rule 4 lists no test of the product itself, and rule 9 keeps the test
settings unchanged with nothing that makes "no tests" red.

## Items

1. **Rule 2, one sentence added at the end of the enterprise gates item.** "`default.toml`'s `tests-first` is
   `kind = "check"` with the step `tests-floor`, which, in a project with a work type whose foundation has merged, fails
   when the `test_dirs` hold no test file of the stack, when the integration folder holds none, or when a change adds or
   changes a code file of an `[architecture]` layer and adds or changes no test file; a change that only deletes code
   needs no test change, and without a work type or before the foundation it is not run." (answers 1 and 2)
2. **Rule 4, one sentence added after "and the steps of rule 3 with their tests."** "It also writes one unit test and
   one integration test of the product that pass, in the stack's own layout (Python: `tests/unit/` and
   `tests/integration/` under the first `test_dirs` entry; another stack: `tests/integration/` until its pack names its
   own)." (answer 3, Q-1590-2)
3. **Rule 9, the `test_dirs`, `project_tests` row's impact replaced.** "unchanged; the foundation build's tests land in
   them; with a work type the `tests-floor` step makes no tests red before `project_tests` runs, and `mode = "adopt"`
   holds that until the person records today's behaviour as tests" (answer 4)
4. **The `## Tests` section, one line added after the rule 4 pins line.** "- Rule 4, the tests floor: an empty `tests/`
   in a work-type sample and a layer change with no test change are red, a docs-only change and a deletion only are
   green, the kit's own repository and a sample with no work type print `not run`, and an adopted sample is green on its
   first run; REQ-079 AC4, AC5 and AC7." (answer 6)
5. **Unchanged:** rules 1, 3 and 5 to 13, the Proof, the Residual, the Contexts and the Open questions.

## Questions (brief #1590), each with the reading this proposal takes

- Q-1590-1: does a change that only deletes code need a test change? Reading: no (the brief's recommendation).
- Q-1590-2: which layout marks an integration test for non-Python stacks? Reading: `tests/integration/` for every stack
  until its pack names one (the brief's recommendation).
- Q-1590-3: how does the step know the foundation has merged? Reading: the architecture record `docs/architecture.md`,
  which only the foundation build writes (rule 5), exists.
