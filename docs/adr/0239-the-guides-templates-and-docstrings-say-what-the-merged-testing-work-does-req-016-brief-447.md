# ADR-0239: the guides, templates and docstrings say what the merged testing work does (REQ-016, brief 447)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0185, ADR-0220, ADR-0227, ADR-0230, ADR-0232, ADR-0238
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `kit/`

## Context

Five residuals recorded on merged pull requests were each left alone because they lay outside that brief's `Touches`:
Q-415-3 (#415), Q-417-5 (#417), the `excluded` residual of #429 and Q-427-5 (#430). Each is a text that now says less than,
or the opposite of, what the code does: the CI guide still has a builder push at every step, the reference omits
`prepush.py --no-lock`, the docstrings of `impact.py` and `test_plan.py` still say that nothing runs the selection, the testing
guide and the commented `[testing]` tables do not name `excluded`, and SPEC-0007 rules 14 and 20 do not name what `metrics.py`
gained in brief #427. Brief #447 gives the answers. It changes text only, never code.

## Decision

1. **The CI guide (answer 1).** The first sentence of section 1 of `docs/guides/project-ci.md` says that a builder pushes its
   draft only at its milestones (session rule 7), not at every step. The rest of the section is unchanged.
2. **The reference (answer 2).** The `prepush.py` usage line of `docs/guides/reference.md` gains `[--no-lock]`, with one
   sentence taken from `prepush.py`'s own docstring: `--no-lock` leaves the heavy-step lock out, for CI. Nothing else in that
   file changes.
3. **The docstrings (answer 3).** The module docstrings of `scripts/agk/impact.py` and `scripts/agk/test_plan.py` name what runs
   the selection on main: `prepush.py` runs the selected regression tests (brief #417), and `proof.py` runs them only with
   `proof_regression = true` (brief #442, off by default). No code changes.
4. **`excluded` (answer 4).** `docs/guides/testing.md` and the commented `[testing]` tables of `kit/templates/agk.toml` and
   `kit/templates/agk.adopt.toml` name the `excluded` key, in the words of `impact.py`'s docstring: a list of
   `"<tag>: <reason>"` texts, the tests that the project's own command leaves out, which proof lists in its manifest
   (brief #425, ADR-0230). The templates' example value is invented.
5. **SPEC-0007 (answer 5).** `docs/runs/proposed-spec-amendments-105.md` proposes, in the form of amendment 104, that rule 14
   name the columns `project_test_seconds` and `proof_seconds` and the lines `backstop escapes: ...` and
   `over budget (budget_seconds <b>): ...`, and that rule 20 name their cases. It is a proposal only; no rule of the spec changes.
6. **Tests (answer 6).** The kit tests that read the changed files were run before and after the change. No assertion pins a
   sentence this brief changes, so no test changes. `tests/kit/test_prepush_regression.py` asserts that the testing guide does
   not say "Nothing runs the selection yet", which stays true. The manifest and hashes are regenerated with the kit's own
   scripts.

## Consequences

A reader of the guides, the templates and the docstrings learns what the testing work does today. Nothing a check or a script
does changes.

## Residual

- 2026-11-01: Q-447-1: the commented `[testing]` tables of both templates also say "nothing runs the selection yet", which the
  brief's sentence contradicts but its answer 4 does not name. The conservative reading changes only what answer 4 names and
  asks.
- 2026-11-01: Q-447-2: the testing guide's opening paragraph says proof is unchanged by the selection, which `proof_regression`
  (brief #442) now qualifies; answer 4 names only `excluded`, so the paragraph stays and the question is asked.
