# Proposed spec amendments 261 (SPEC-0045; REQ-052)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is
written for ADR-0835 (brief #2020), which stays `Proposed` for the maintainers' decision. The path is
`docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md` (rule 8). Amendments 254 to 260 are on the default
branch or in open pull requests (#2016, #2015 and #2018), so this one is 261, as brief #2001 chose its number (Q-EF-1).
This file proposes the lines and does not edit the spec. They are applied word for word on a person's
`Approve: SPEC-0045`; no session posts that line.

## Why

Brief #2020 counted 9 of 70 builder `Report:` comments carrying a figure. A `not shown` gave no reason, and the one
figure mixed four kinds of tokens whose prices differ. The pull request of brief #2020 builds the form that ADR-0835
decides; rule 8 still states the old form.

## Items

1. **SPEC-0045 rule 8, the line.** "Its one line is `Usage: <n> tokens`, or `Usage: not shown` when no transcript is
   found, none can be read or it holds no usage record" becomes "Its one line is `Usage: <n> tokens (input <a>, cache
   write <b>, cache read <c>, output <d>)`, `<n>` the sum and `, other <e>` added for a whole `*_tokens` count of
   another kind whose key names no cache, or `Usage: not shown (<class>)` with the class `no-session-id`,
   `no-transcript`, `unreadable` or `no-usage-record`, never a path or an id (amendment 261, ADR-0835)".
   Class: behaviour
2. **SPEC-0045 rule 8, the files read.** "or the file `--transcript FILE` names" becomes "or each file a `--transcript
   FILE` names (it may be given more than once, each message id counted once across them)". "The session's own
   transcript only is counted: a helper agent's tokens are counted only where the runtime writes them into that file
   (`Q-798-8`)" becomes "The session's own transcript is counted, and with `--helpers` its own sub-agents'
   transcripts, `<folder>/<session id>/subagents/*.jsonl`, too. A sub-agent sees its parent's session id, so only the
   top-level session passes `--helpers` (amendment 261, ADR-0835)".
   Class: behaviour
3. **SPEC-0045 rule 8, the readers.** After "The reader is unchanged by `usage.py`:" insert "it reads `<n>` before
   the split, and a `not shown` with its class counts as `not reported` (amendment 261);".
   Class: implementation
4. **Unchanged:** the `[models.prices]` table, rule 9 and `metrics.py --usage-by-kind`. Answers 3, 4 and 6 of brief
   #2020 wait for `Q-2020-1` and are not part of this amendment.
   Class: implementation
