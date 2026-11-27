# ADR-0839: Knowledge is read in one order through one resolver and a pack never weakens a gate

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2032, 2026-11-27T07:25:55Z)
- Related: ADR-0837, ADR-0838, ADR-0697, ADR-0759, ADR-0806, ADR-0817, ADR-0824, SPEC-0077, SPEC-0074, SPEC-0048, REQ-084, brief #2032, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `kit/`

## Context

SPEC-0077 (Approved, ADR-0837) rule 14 build (b) asks for rule 5: one resolver, `packs.files(root, kind)`, that gives
the files of each knowledge kind in one order, and the readers of rule 2 reading through it. On main at 7e53df82 each
reader had its own order: `playbook_format.folder` (the project's, else the plugin's), `check_domains.folders` (the
project's, then the kit's), `check_playbooks.standards_file` (the kit's only), `engines.DEFAULTS` (a constant kit path,
brief #1591) and `front_door`'s stack- and domain-signal readers (the kit's only). Build (a) (ADR-0838) added the pack
format, its check and the `[packs]` table; no reader read a pack.

## Decision

1. **The resolver.** New `scripts/agk/packs.py`: `files(root, kind, core=None)` returns `(layer, path)` for each file
   of one of rule 2's nine kinds, in order: `agk-core` (the kit's file or folder through `kit_root.kit_file`, or CORE
   when a reader is given its kit root), each pack of `[packs] use` in its listed order (the files its manifest lists
   under `<kind>/`), then the project's own files. In the installed layout the kit's file is the project's path, so it is
   read once, as `agk-core` (`Q-2032-1`). A refused `[packs]` table, or a pack in use that `check_packs.problems`
   fails, raises `packs.Refused` (a `CheckError`) with one line naming the setting or the rule and the pack, never a
   value; a reader stops there, never with a partial read. `rows` composes rows by a key, a later layer's rows of a
   value replacing every earlier row of it at its first place (`Q-PB-1`); `plain` drops a pack entry's provenance
   keys (`source`, `basis`, rule 3) before a reader checks its form. Standard library, `common`, `kit_root`, and
   `config` and `check_packs` imported where used; no network, no model.
2. **The readers.** `playbook_format.folder` gives the folder of the last layer holding `<name>.toml` (a derived name
   stays the project's, SPEC-0048 rule 22), `playbooks` the project's files then the packs'; `playbook_format`
   imports `packs` inside its functions (`resolver`), so its own imports stay those of the standing import ruling
   (ADR-0824). `check_domains.folders` reads through `files` (a refused pack stops it) and keeps the project's and the
   kit's folders: a domain pack a pack carries waits for build (j) (`Q-2032-2`). `check_playbooks.standards_file`
   composes the file of each layer. `engines.stack_defaults(root)` replaces the constant `DEFAULTS` path.
   `front_door.signal_table(kit, root)` and `domain_rows(kit, root)` read the kit's table, then each pack's; the
   repository's own copy is never read, as SPEC-0057's `Q-S0057-2` holds (`Q-2032-4`). `domain_ask` passes the root.
3. **Composition.** A pack's playbook of a kit name is composed over the same-named playbooks of the layers before it
   (`Q-2032-3`): a gate restated weaker is `rule 21: config/packs/<id>: a gate is restated weaker (key: <key>)` and
   the held gate stays. A standards entry restated by a later layer replaces the held one only when its `rules` drops
   no code, else `SPEC-0072 rule 2: config/packs/<id>: a pack's `rules` drops a rule code (key: standards.rules)`.
   Stack-signal rows compose by `name`, stack defaults by `work_type` (their key in the file), and domain-signal rows
   by `name`, each a proposal for a person to confirm; `no_signal` and `ignore` words are added.
4. **Wiring.** `kit/manifest.json` lists `packs.py` in `verbatim`, because the installed readers import it. The
   `[testing]` map names `tests/kit/test_packs_resolver.py`.

## Consequences

With no `[packs]` table every reader's result is today's on the kit's tree and on a clean-layout project (the recorded
snapshot test). A pack in use adds rows or strengthens gates and standards, and a weakening is refused naming the pack
and the key. A reader added later that opens a knowledge file by a literal path in a new module fails
`test_ac2_no_other_kit_module_opens_a_knowledge_file_by_a_literal_path`.

## Residual

Pack-carried domain packs wait for build (j); `playbook_format.stacks`, `survey.SIGNALS`, `adopt.SIGNALS` (`Q-PB-2`)
and the form check of the kit's own signal table still read the kit's file by name. A pack's playbook in full form
needs the provenance key on each entry, which `playbook_format.problems` does not yet drop: the pack check of build (a)
and the playbook check read the same file with different key sets (`Q-2032-5`).
