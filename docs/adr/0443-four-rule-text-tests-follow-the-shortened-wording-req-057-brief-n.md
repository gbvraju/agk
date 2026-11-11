# ADR-0443: Four rule-text tests follow the shortened wording of the same rules

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1048, issue #1049, issue #1047 (closed as a duplicate of #1049), brief #1023, pull request #1040, plan #661, Q-1023-1, Q-1023-2, Q-1023-3
- Requirements: REQ-057

Protected classes: `tests/kit/`, `tests/kit_dev/`

## Context

Pull request #1040 (brief #1023) shortened sentences of `.claude/agents/conductor.md` and `config/session-rules.md`
with no change of meaning (Q-1023-2, Q-1023-3). Four tests of `governance` still looked for the old words, were not in
the builder's selected run, and failed on the merged tree: `4 failed` in the step `Tests of the checks` on 27d24bb
and again on abb72b3, so the default branch is red.

## Decision

Each of the four tests asserts the wording its rule now has for the same requirement; no requirement is dropped:

1. `test_the_conductor_report_ends_with_the_nine_lines` reads `every hourly report ends with` without case.
2. `test_ac7_the_conductor_reads_question_and_report_comments_and_answers_each_by_a_verdict` reads
   ``answer each by a `Verdict:` comment that names the head``.
3. `test_ac3_the_rules_file_states_the_progress_line` reads `posts, or edits in place, one comment`, the first
   sentence of session rule 8, which now says what `edits it in place` and `never repeats it` said.
4. `test_ac_rule_7_keeps_its_draft_and_ready_parts` reads `opens the pull request as a draft`.

The rule files and `config/rule-budget.txt` do not change.

## Consequences

The change is a test of text following the text, not a weaker check (principle 11): each test still fails when its
rule loses the requirement. The default branch turns green when this merges.

## Residual

- 2026-11-11: none.
