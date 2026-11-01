# ADR-0243: session rules that say the same thing are merged, keeping every rule number (REQ-039, brief 384)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0212, ADR-0196, ADR-0225
- Requirements: REQ-039

Protected classes: `config/` (`config/session-rules.md`), `.claude/` (`.claude/agents/shadow.md`), `tests/kit/`
(`tests/kit/test_session_rules.py`, `tests/kit/test_shadow_rules.py`, `tests/kit/test_usage_figures.py`), `tests/kit_dev/`
(`tests/kit_dev/test_session_rules_push.py`)

## Context

The session rules had grown to 35, and several pairs stated one duty twice. The core audit and the overlap table
(`docs/runs/core-overlap-1.md`, ADR-0212) listed them. On 2026-11-01 the person accepted rows 3 to 8 of the decision
table of the split of plan #278, as proposed (the conductor's field note on #278): session rules 13 into 31; 6 and 23
into 21; 16 into 17; 5 into 18; 20 and 24 into 1; 12, 25 and 26 out of the core with a pointer kept. The rule for every
merge: never renumber; a merged number stays as a pointer line. Brief #384 gives six answers; no safety rule weakens.

## Decision

1. **The merges (answer 1).** Each surviving rule takes the other rules' text word for word, appended in the order
   below. The only rewordings are citations of a rule that is now the same rule: rule 1 drops "(rule 20)"; the text of
   rule 23 in rule 21 says "follows the five polls above" for "follows the five polls of rule 21" and drops "(rule 21)".
   Every command, option and comment shape stays word for word.

   | Row | Merged number | Now in | Order in the surviving rule |
   | --- | --- | --- | --- |
   | 3 | 13 (`push-check` before every push) | rule 31 | rule 13, then rule 31 |
   | 4 | 6 (stop and ask) and 23 (GitHub unreachable) | rule 21 | rule 6, rule 21, then rule 23 |
   | 5 | 16 (questions and reports on the pull request) | rule 17 | rule 17, then rule 16 |
   | 6 | 5 (`next` and `claim`) | rule 18 | rule 5, then rule 18 |
   | 7 | 20 (`Correction:`) and 24 (when `watch --pr` ends) | rule 1 | rule 1, rule 20, then rule 24 |

2. **The pointer lines (answer 2).** Each merged number stays as one line, `N. Merged into rule M (ADR-0243).`, so the
   numbering has no gap, `session.py ids` still prints 36 as the next rule number, and every citation in scripts, role
   files, guides, ADRs and verdicts still names a rule that exists. No surviving rule cites a pointer number.
3. **Row 8, out of the core (answer 3).** Rule 25 (the `Shadow:` comment) and rule 26 (the `Marks:` comment) move word for
   word into a section "Moved from the session rules" of `.claude/agents/shadow.md`, as M1 and M2; rule 12 (the usage
   figure on a `Report:` line) moves word for word into step 6 of "Running the loop" of
   `docs/guides/getting-started.md`, after the guide's own sentence, which is kept. Each number stays as one line,
   `N. Moved to `<file>` (ADR-0243).`. SPEC-0035 rules 1, 3 and 7 and SPEC-0033 rule 8 stay their decided sources and are
   not edited (Q-384-1, Q-384-2, Q-384-4).
4. **The safety rules (answer 4).** Rules 2, 14, 15, 22, 29, 30 and 33 are unchanged byte for byte; rules 7 to 11, 19,
   27, 28, 32, 34 and 35 are unchanged too.
5. **Tests (answer 5).** `tests/kit/test_session_rules.py` holds the text of each merged and moved rule before the change
   and of each safety rule, and checks: the numbers 1 to 35 without a gap; each pointer line and that its target exists
   and is not a pointer; each surviving rule or destination file holds the moved text; each backticked command and shape
   of a moved rule is still named; no rule cites a pointer number; the safety rules byte for byte. The tests that read
   the moved text (`test_shadow_rules.py`, `test_usage_figures.py`, `tests/kit_dev/test_session_rules_push.py`) read it
   where it now lives and check the pointer line.
6. **Path classes (answer 6).** `config/`, `.claude/`, `tests/kit/` and `tests/kit_dev/`, as listed above.

## Consequences

- A newcomer reads 25 rules and 10 pointer lines instead of 35 rules; nothing a session must do is dropped.
- A citation of a merged number (for example "session rule 13" in a guide or a verdict) still resolves, through one
  pointer line; the core audit keeps counting citations by number.
- A later change to a safety rule must also change the byte-for-byte text in the test, which makes it visible.

## Residual

- 2026-11-01: SPEC-0035 rule 7 says the session rules give the shapes of `Shadow:` and `Marks:`; after row 8 the session
  rules point at the shadow role file, which gives them. Amending the sentence of the Approved spec is for a person
  (Q-384-2).
- 2026-11-01: brief #384 answer 3 names "the reporting guide" for rule 12; no file has that name. Conservative reading: the
  guide section that already states the usage figure for a builder, step 6 of "Running the loop" of
  `docs/guides/getting-started.md`, keeping its own sentence and adding the rule word for word (Q-384-1).
- 2026-11-01: brief #384 answer 3 also names SPEC-0035 as a destination; SPEC-0035 is Approved and already holds the
  shapes in rules 1 and 3, so it is not edited and rules 25 and 26 move whole to the shadow role file, its reader's file
  (Q-384-4).
- 2026-11-01: three tests outside the brief's `Touches:` line read the moved text and now read it where it lives
  (`tests/kit/test_shadow_rules.py`, `tests/kit/test_usage_figures.py`, `tests/kit_dev/test_session_rules_push.py`), and
  the shadow role file and the getting-started guide receive rules 25, 26 and 12, as answer 3 requires (Q-384-3).
