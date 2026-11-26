# Proposed spec amendments 257 (SPEC-0039; REQ-057)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0830 (brief #2006), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rule 4). Amendment 256
was the newest on main and the open briefs name none above it, so this is 257 (Q-RP-1). This file proposes the lines
and does not edit the spec. They are applied word for word, on a person's `Approve: SPEC-0039`; no session posts them.

## Why

15 light merges of main on 2026-11-26 each asked the builder for a record the conductor could not make, and #1982 asked
the owner's accept on four heads whose record differed by the same field each time (brief #2006's measurement).

## Items

1. **SPEC-0039 rule 4, the accept over a light merge.** After "names that head and says it accepts the difference;"
   insert "an accept that names the old head carries to the light re-prove's merge of the default branch into it
   (SPEC-0050 rule 7a) when the verdict on the merge head carries the same `Differs: <name> (field: <field>)` lines,
   as a set, as the `differs` verdict on the old head that the accept follows, and no verdict with a numbered item is
   between them (amendment 257);".
   Class: behaviour
2. **SPEC-0039 rule 4, the lines.** After "that matches the head's first 12 characters (`Q-S0039-5`)." insert " An
   `Evidence check: differs` verdict carries one `Differs: <name> (field: <field>)` line per difference `evidence.py`
   printed, and the lines stand beside no other check (amendment 257)."
   Class: behaviour

No other rule changes.
