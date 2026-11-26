# ADR-0830: An owner's accept carries over a light merge, and the conductor names a missing scanner (REQ-057)

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #2006, SPEC-0039 rule 4, SPEC-0050 rules 6 and 7a, amendment 257, ADR-0685 (an owner's answer stays
  answered; its decision 3 is narrowed here), ADR-0725 (the re-prove state), ADR-0495 (the light re-prove), ADR-0718
  (a covered fix list carries over a light merge), ADR-0818 (the conductor's re-prove record in local mode), ADR-0654
  (a fresh take writes nothing), ADR-0306 (doctor's secret-scan line), ADR-0528 (the reviewer's gate), ADR-0583 (the
  rule budget), plan #661
- Requirements: REQ-057

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`, `agk.toml`

## Context

Of the 273 verdicts on the 90 pull requests merged from 2026-11-23 to 2026-11-26, 15 were fix lists after the
conductor's light merge of main, each asking the builder only to record the merge head again (brief #2006's
measurement). In local mode `conductor.reprove_record` makes that record itself, but returns `none (gitleaks is not
installed (tool: gitleaks))` on a machine without the scanner, and nothing said so before the first light merge. Each
light merge also voided the owner's `Maintainer answer: accept <head>`, since `merge_cleared.answered` counted only an
accept of the exact head (ADR-0685 decision 3, the maintainer answer to Q-1616-1): #1982 was asked on four heads whose
record differed by the same field each time. The owner's word (the steward chat, 2026-11-26, quoted as data): "Draft
1 , 2 and 3 then file it", and on the brief (2026-11-26T14:54Z): "yes".

## Decision

1. **The lease take names a missing scanner.** `conductor.py lease --take`, on a fresh take (no valid lease held; a
   renew by the holder prints nothing), reads local mode as `reprove_local` does. In local mode with no `gitleaks` on
   PATH it prints one more line, `lease: tools: gitleaks is missing; a light re-prove asks the builder for its record
   (tool: gitleaks)`, and its `Conductor: active` marker ends `; tools: gitleaks missing`. A renew of a marked lease
   checks the tool again, silently, and keeps the mark only while it is still missing. The take still exits 0. A
   malformed `execution` prints `lease: tools: not checked:` and the refusal naming the setting; a default branch not
   fetched says nothing.
2. **The accept carries over a light merge.** `merge_cleared.answered`, given the light-merge reader `light_of` (the
   default branch as last fetched and its `[flow] shared_indexes`; None, so no carry, when either cannot be read), also
   counts `Maintainer answer: accept <old>` by an account in `spec_approvers` for the head when: the newest earlier
   verdict naming another head is a readable `Verdict: cleared <old>` or a fix list on OLD whose `Final:` lines accept
   ADRs alone (`accepted_adrs`, as `carried_from` reads them; never `rejected`), names OLD in full, has no numbered item
   and an `Evidence check: differs` for OLD; its `Differs:` lines equal, as a set, those of the verdict on the head; the
   head is OLD's light merge (`session_plan.light_merge`); and the accept follows that verdict on OLD (or itself
   carries, up to 8 light merges in a row). Earlier verdicts on the same head are passed over only when they have no
   numbered item. Any other difference, a builder push (the head is then no light merge of OLD), a full re-prove or a
   verdict with a numbered item between them needs a new accept. `merge_cleared.holds` passes the reader for local mode
   and the lapse merge, so the conductor's merge, `--owner` and the router's merge-ready reading share it. This narrows
   ADR-0685 decision 3: without the reader the accept stays exact to the head, and the carry is only this one; its test
   (`test_1616_the_merger_evidence_accept_stays_exact`) now checks that exact reading by behaviour.
3. **The difference is written as lines.** A verdict whose `Evidence check:` is `differs` carries one line `Differs:
   <name> (field: <field>)` per `not what prepush runs:` line of `evidence.py`. `common.differs_problem`, read by
   `conductor.form_problem` before a post (so `check-verdict` and the guard refuse it), refuses a `differs` check
   without the lines, the lines beside no `differs` check, and a line of another shape, naming SPEC-0039 rule 4 and the
   shape, never the body. A posted verdict is read as before, so one posted before this build has no lines and no accept
   carries from it.
4. **The texts.** `.claude/agents/conductor.md`'s local-mode paragraph says that an owner's accept carries over light
   merges whose `Differs:` lines match, with words replaced, not added: its `config/rule-budget.txt` line (4895 words,
   37 rule lines) is unchanged. The `Owner needed:` text is unchanged.
5. **The spec.** Amendment 257 proposes the SPEC-0039 rule 4 lines; the spec approvers apply it (principle 6). Until it
   is approved, this ADR stays Proposed (Q-RP-4).

Settings: `execution` `local` (or the open local-mode record issue): decisions 1 and 2 apply; `hosted`, `hybrid` or
`pool`: CI proves the merge head, `local_evidence` is not read and decision 1 prints nothing; another value is refused
naming `execution`. `[flow] shared_indexes` decides `light` as today; a malformed list carries nothing. `[flow]
max_behind_merges`: a `behind` head is a full re-prove and never carries. `[flow] auto_merge` `true` or `false`: the
conductor's merge and `merge_cleared.py --owner` read the same `holds`. `review_mode` `solo` or `team`: the accept is
an account of `spec_approvers`, as today; an empty or `@REPLACE-ME` list counts no accept. `[personal]`
(`forge = "files"`): not applicable, `reprove` refuses there. `pr_mode`, `default_branch`, `required_checks`,
`version`, `plugin_version`: no effect. `paused = true`: nothing is posted, as today. A project using AGK gets the
same readers from its installed `scripts/agk/`.

## Consequences

With gitleaks on the conductor's machine, a light merge needs no builder round, and the owner is asked once per
difference rather than once per merge of main. Without it, the conductor says so at the take. Nothing that was held
for a different difference, a push or a fix list is let through.

## Residual

Where the conductor's machine is and why its setup lacks gitleaks is not read here (verify). Q-RP-2 (refuse the light
re-prove without the scanner) and Q-RP-3 (hold a re-prove while an owner ask is open) are taken with the brief's
conservative readings: no.
