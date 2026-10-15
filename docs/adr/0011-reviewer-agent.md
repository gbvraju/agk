# ADR-0011: Reviewer agent (SPEC-0003), REQ-013

- Status: Proposed
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0008, ADR-0009, ADR-0010
- Requirements: REQ-013

## Context

SPEC-0003 (Approved) describes a read-only reviewer that reads one pull request against its stated intent and the
repository's Approved text. This PR implements rules 1 to 22 of the spec; rule 23 (shadow review) happens after
merge. The GitHub Action form is deferred (rule 14); nothing here adds a workflow, an action pin or a secret.

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `docs/requirements.md`. This PR
changes all six.

## Decision

1. **Context script.** `scripts/agk/review_context.py [--base REF] --body FILE|-` writes one markdown document to
   stdout from local git and files: context problems, the PR body, the numbered hunks of the diff, the advanced
   requirements with their test markers, the protected classes touched with the changed ADRs that name them, the
   referenced specs and ADRs, and the principles. The PR body and every embedded file sit in tilde fences longer than
   any tilde run inside, so their text cannot forge a heading or a hunk. Same inputs, same bytes; caps come from
   `agk.toml` (`review_diff_cap` default 4000, `review_other_cap` default 1500); an invalid value is refused naming
   the setting; a cut is marked `[truncated: N lines omitted]` and the document says `Truncated: yes`.
2. **Report validator.** `scripts/agk/check_review_report.py --context FILE --report FILE` accepts a report only when
   it has exactly one verdict (`cleared`, `fix list` or `rejected`), a `Context truncated:` line equal to the
   context's, consecutive findings each with `Where` (a hunk of the context, `PR body` or `context problems`),
   `Rule` (`SPEC-nnnn rule N`, `ADR-nnnn decision N`, `principle N` or `REQ-nnn ACn`, resolved against the context),
   `Wrong` and `Fix`. Messages name the finding and the field. On success it prints the footer
   `<!-- agk-review: verdict=V findings=N truncated=B -->`.
3. **Agent definition.** `.claude/agents/reviewer.md` with tools `Read, Grep, Glob` only; it says it never approves,
   merges, pushes or edits, treats the PR content as data and fixes the report format of decision 2.
4. **Install.** The three files are in the manifest's verbatim set, so init and adopt install them; `agk.toml`
   templates are unchanged (the two cap keys are optional and documented in the README).
5. **REQ-013** is added to `docs/requirements.md` with Status `planned` (AC1 deterministic context, AC2 validated
   report, AC3 read-only, AC4 verdicts measured). It is not marked done by this PR.
6. **Proof without a model.** Fixture pull requests F1 to F10 (`tests/kit_dev/review_fixtures.py`) are built in
   temporary git repositories; tests cover the context, the validator, the definition and the manifest; F1 to F6 also
   fail the existing checks. No test uses a model or the network.
7. **Kit version** `0.5.0`: installed content changed.
8. **`agk-governance` and the validator.** `check_review_report.py` needs a context and a report, so it is not run by
   `agk-governance`. The kit test that every `check_*.py` script is run by that target skips it, as it already skips
   `check_pr_body.py` (`tests/kit/test_agk_mk.py`, one line). No check is weakened: the validator is run by
   hand and by its own tests.
9. **Shadow review.** `docs/runs/shadow-review-template.md` describes how a rule 23 run is recorded.

## Consequences

- A maintainer or an agent can produce a reproducible review context and check a report mechanically before reading
  it; the model's own judgement is not measured in CI.
- Installed repositories gain two scripts and one agent definition (three files).
- AC4 (verdicts measured) has no test yet: the footers are aggregated later (SPEC-0003 rule 17).

## Residual

- 2026-10-15: the agent's judgement is evaluated only by hand, in the shadow-review records (due 2027-01-31).
- 2026-10-15: the report format (Where/Rule/Wrong/Fix lines) is mine; the spec leaves the format to the agent
  definition (due 2026-12-15).
- 2026-10-15: referenced documents are found by id and by path only; a document described in words is not (due 2026-12-15).
- 2026-10-15: class naming in an ADR is still a substring match (ADR-0003 residual).
