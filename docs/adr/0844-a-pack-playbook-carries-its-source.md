# ADR-0844: A pack's playbook carries its source and passes the playbook check

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2040, 2026-11-27T13:03:24Z)
- Related: ADR-0837, ADR-0838, ADR-0839, ADR-0259, ADR-0316, SPEC-0077, SPEC-0048, REQ-084, brief #2040, brief #2032, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0077 (Approved, ADR-0837) rule 3 asks every knowledge item of a pack to carry `source` with an access date, or
`basis = "expected"`; rule 5 reads a pack's playbook through `packs.files` (ADR-0839). On main at e4030a8 the two
checks of one pack playbook refused each other (`Q-2032-5`): `check_packs._knowledge` required the provenance on
each top-level `[[...]]` entry, and `playbook_format.problems` refused `source` and `basis` as keys outside the format
on every entry but a derived playbook's gate. The kit's `web-app.toml` read as a pack file gave 16 `check_packs`
lines without provenance and 18 `problems` lines with it, so no pack playbook could pass both.

## Decision

1. **The layer.** `playbook_format._pack_layer(path, root)` asks the resolver for the file's layer: the pack of
   `packs.used` whose manifest lists the file under `playbooks/`, as `packs.files` reads it, or None: no resolver (a
   partial copy), no pack in use, a refused `[packs]` table or pack, the kit's (`agk-core`) or the project's own file.
2. **The format of a pack's playbook.** For a pack layer each `[[phases]]`, `[[lanes]]`, `[[gates]]`, `[[claims]]`,
   `[[discovery]]` and `[[standards]]` entry also takes `source` and `basis` (`PACK_KEYS`, strings). A present one is
   checked by rule 3, each line `SPEC-0077 rule 3: <file>: <what> (key: <key>)`, never a value: a `source` that is not
   a URL and an access date, a `basis` other than `expected`. A claim's `basis` keeps its claim meaning, `measured`
   or `expected` (`Q-PS-1`). A missing provenance is `check_packs`'s line alone. A nested table (`[split]`,
   `[[testing.map]]`) takes neither key, as today (`Q-PS-2`).
3. **The pack check and claims.** `check_packs._sourced(entry, section)` accepts a `[[claims]]` entry with
   `basis = "measured"` when it carries a dated `source`; every other entry keeps today's rule.
4. **Nothing else changes.** The kit's and the project's own playbooks keep today's format (SPEC-0048 rule 22: a gate
   of a shipped playbook carries neither key); a derived playbook's gates keep rule 22. Composition reads the keys it
   read before; provenance never makes a gate stronger or weaker. The standards file of a pack already drops the
   keys before its form check (`packs.plain`, ADR-0839), so `check_playbooks` is unchanged.
5. **Wiring.** The `[testing]` map entries of `playbook_format.py` and `check_packs.py` name
   `tests/kit/test_pack_playbook_source.py`.

## Consequences

A pack playbook with a dated `source` or `basis = "expected"` on each top-level entry gives no line from either check;
without them it gives the pack check's line only. With no `[packs]` table the kit's tree gives today's result. A later
kind or reader that refuses a key the pack check requires fails
`test_no_key_the_pack_check_requires_is_refused_by_the_playbook_check`.

## Residual

A pack's domain files wait for build (j) and are not covered here; a `basis` of the wrong type is named by the pack
check under the key `source`, since a pack in use that fails it stops the resolver before the playbook check reads it.
