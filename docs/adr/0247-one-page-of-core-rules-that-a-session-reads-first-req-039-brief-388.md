# ADR-0247: one page of core rules that a session reads first, with CLAUDE.md pointing at it (REQ-039, brief 388)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0212
- Requirements: REQ-039

Protected classes: `config/` (`config/core-rules.md`), `CLAUDE.md`, `tests/kit/`, `tests/kit_dev/`, `kit/`
(`kit/manifest.json`, `kit/templates/gitattributes`)

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
   `config/session-rules.md`, so an installed project that receives the new `CLAUDE.md` receives the page it points at,
   and the installed `.gitattributes` template (`kit/templates/gitattributes`) pins it to LF like every installed file.
2. **CLAUDE.md (answer 2).** `CLAUDE.md` keeps its title, its first sentence (the constitution is authoritative, twelve
   numbered rules), its pointer to `config/session-rules.md` and its compaction-recovery section word for word, and
   replaces its numbered list with a pointer to `config/core-rules.md`. Every item of that list carries some text found
   nowhere else. Items 2 and 10 stay in `CLAUDE.md` with their numbers and exact text, because approved texts require
   their wording in `CLAUDE.md` itself (Q-388-5); the other eight move to the last section of the page,
   `CLAUDE.md items`, with their exact text and their numbers, and the page cites items 2 and 10 there by number. All are
   cited as `CLAUDE.md item N` as before; none is dropped and none is renumbered, and each list counts up by one, so no
   item renders under another number.
3. **No rule changes (answer 3).** Nothing in `constitution/principles.md`, `config/session-rules.md` or a spec changes.
4. **Tests first (answer 4).** `tests/kit/test_core_rules_page.py` checks that every rule the page names exists; that the
   page names exactly the core of row 13; that each summary is at most one sentence; that every item of `CLAUDE.md` before
   the change is on the page or, for items 2 and 10, still in `CLAUDE.md`, with its number and exact text; that the page
   cites items 2 and 10 by number; that no list renders with other numbers; that the page has at most 60 lines; and that
   `CLAUDE.md` points at the page, keeps only items 2 and 10, keeps its compaction-recovery section and still points at
   `config/session-rules.md` (the existing test of REQ-037 AC1 is unchanged and passes).
5. **Existing tests that read the moved text.** The existing tests that pin the wording of items 2 and 10 in `CLAUDE.md`
   (`tests/kit/test_session_rules.py`, `tests/kit/test_solo_mode.py`, `tests/kit_dev/test_flow_texts.py` and
   `tests/kit_dev/test_playbook.py`) are unchanged and still read `CLAUDE.md` alone. `tests/kit_dev/test_init.py` on an
   installed project, which asserts that no text assumes `origin/main`, reads the installed `CLAUDE.md` together with the
   installed page, so it checks more text and no less (principle 11). `tests/kit_dev/test_kit_manifest.py` lists the
   page among the single verbatim files.

## Consequences

- A session reads one page of at most 60 lines first; the numbered rules stay the source, cited by number.
- A rule now lives once: the page holds eight former `CLAUDE.md` items, `CLAUDE.md` keeps items 2 and 10, and the page
  only cites the constitution, the session rules and those two items.
- When a session rule named on the page is merged into another by a later brief, its number stays as a pointer line, so the
  page's citations stay valid; a later change of the core is a change of this page with its own ADR.

## Residual

- Q-388-1: the review context's `Operating rules` section is the text of `CLAUDE.md` (SPEC-0003 rule 5 (h)), so after this
  change it holds the pointer and items 2 and 10 rather than the ten items. Brief #388 answer 3 changes no spec, so `review_context.py` is not
  changed; adding the page to that section is a spec amendment for a later brief (conservative reading: no spec change).
- Q-388-2: the compaction-recovery section is kept word for word (answer 2), so it does not add the page to its list of
  files to re-read; the pointer at the top of `CLAUDE.md`, which is re-read, names the page (conservative reading).
- Q-388-3: row 13 names `CLAUDE.md` items 3, 5 and 8 as safety rules; the page lists them under the safety rules with a
  one-sentence summary and keeps their exact text, with items 1, 4, 6, 7 and 9, in its `CLAUDE.md items` section, so the
  exact text is held once (conservative reading: nothing dropped, nothing renumbered).
- Q-388-4: brief #388's `Touches:` line names four files; the manifest entry, the `.gitattributes` template line, the
  existing tests of decision 5 and this ADR are outside it and are needed for the kit to install the page and for the suite to read the moved text.
- Q-388-5: approved texts require the wording of items 2 and 10 in `CLAUDE.md` itself: SPEC-0013 rule 17 (the line on
  the state of a pull request, item 10), REQ-035 AC7 (one open pull request per session and `Depends-on`, item 2) and
  SPEC-0028 rule 7 (`CLAUDE.md rule 2`). Answer 3 changes no spec, so both items stay in `CLAUDE.md` with their exact
  text and numbers, the page cites them by number, and the tests that pin that wording read `CLAUDE.md` alone as before
  (conservative reading, the fix list on #465). Moving them to the page is a spec change the person may decide later.
