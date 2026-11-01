# ADR-0247: one page of core rules that a session reads first, with CLAUDE.md pointing at it (REQ-039, brief 388)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0212
- Requirements: REQ-039

Protected classes: `config/` (`config/core-rules.md`), `CLAUDE.md`, `tests/kit/`, `tests/kit_dev/`, `kit/`
(`kit/manifest.json`)

## Context

Plan #278 answer 4 asks for one page that a session reads first, with everything else as reference. `CLAUDE.md` restated
parts of the constitution and of the session rules (never merge, never post `Confirmed:`, protected paths, the pull request
body), so one rule lived in two or three places and could drift. The person accepted rows 3 to 13 of the decision table of
the split of plan #278 on 2026-11-01 (the conductor's field note on #278, which closed the plan as decided). Row 13 chose
the core: the constitution; the safety rules, session rules 2, 14, 15, 22, 29, 30 and 33 and `CLAUDE.md` items 3, 5 and 8;
and session rules 1, 3, 7, 17, 18, 21 and 31. The rule for every merge of that decision: never renumber. Brief #388 gives
the answers; this ADR number was reserved for it by the conductor (the field note on #388).

## Decision

1. **The page (answer 1).** A new file, `config/core-rules.md`, names the core of row 13 by number and file. Each safety
   rule and each working rule is one line: its reference and a plain summary of at most one sentence that adds nothing.
   The constitution is named whole (principles 1 to 12, already one sentence each) and is not summarised. The page says at
   its top that the numbered rules win over the summaries. It is listed in `kit/manifest.json` (verbatim), beside
   `config/session-rules.md`, so an installed project that receives the new `CLAUDE.md` receives the page it points at.
2. **CLAUDE.md (answer 2).** `CLAUDE.md` keeps its title, its first sentence (the constitution is authoritative, twelve
   numbered rules), its pointer to `config/session-rules.md` and its compaction-recovery section word for word, and
   replaces its numbered list with a pointer to `config/core-rules.md`. Every item of that list carries some text found
   nowhere else, so all ten move to the last section of the page, `CLAUDE.md items`, with their exact text and their
   numbers, and are cited as `CLAUDE.md item N` as before; none is dropped and none is renumbered.
3. **No rule changes (answer 3).** Nothing in `constitution/principles.md`, `config/session-rules.md` or a spec changes.
4. **Tests first (answer 4).** `tests/kit/test_core_rules_page.py` checks that every rule the page names exists; that the
   page names exactly the core of row 13; that each summary is at most one sentence; that every item of `CLAUDE.md` before
   the change is on the page with its number and exact text; that the page has at most 60 lines; and that `CLAUDE.md`
   points at the page, carries no numbered list, keeps its compaction-recovery section and still points at
   `config/session-rules.md` (the existing test of REQ-037 AC1 is unchanged and passes).
5. **Existing tests that read the moved text.** Four existing tests asserted phrases of the old list in `CLAUDE.md`
   (`tests/kit/test_session_rules.py`, `tests/kit/test_solo_mode.py`, `tests/kit_dev/test_flow_texts.py`,
   `tests/kit_dev/test_playbook.py`). Each now reads `CLAUDE.md` together with the page it points at; every asserted phrase
   and count is unchanged, so no check is weakened (principle 11). `tests/kit_dev/test_kit_manifest.py` lists the page
   among the single verbatim files.

## Consequences

- A session reads one page of at most 60 lines first; the numbered rules stay the source, cited by number.
- A rule now lives once: the page holds the former `CLAUDE.md` items and only cites the constitution and the session rules.
- When a session rule named on the page is merged into another by a later brief, its number stays as a pointer line, so the
  page's citations stay valid; a later change of the core is a change of this page with its own ADR.

## Residual

- Q-388-1: the review context's `Operating rules` section is the text of `CLAUDE.md` (SPEC-0003 rule 5 (h)), so after this
  change it holds the pointer rather than the ten items. Brief #388 answer 3 changes no spec, so `review_context.py` is not
  changed; adding the page to that section is a spec amendment for a later brief (conservative reading: no spec change).
- Q-388-2: the compaction-recovery section is kept word for word (answer 2), so it does not add the page to its list of
  files to re-read; the pointer at the top of `CLAUDE.md`, which is re-read, names the page (conservative reading).
- Q-388-3: row 13 names `CLAUDE.md` items 3, 5 and 8 as safety rules; the page lists them under the safety rules with a
  one-sentence summary and keeps their exact text, with the other seven items, in its `CLAUDE.md items` section, so the
  exact text is held once (conservative reading: nothing dropped, nothing renumbered).
- Q-388-4: brief #388's `Touches:` line names four files; the manifest entry, the four existing tests of decision 5 and
  this ADR are outside it and are needed for the kit to install the page and for the suite to read the moved text.
