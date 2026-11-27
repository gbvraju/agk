# ADR-0841: A pack is scanned for secrets, instructions, licence, size, trust and kit version before it is written

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2034, 2026-11-27T07:25:55Z)
- Related: ADR-0837, ADR-0838, ADR-0840, ADR-0327, SPEC-0077, SPEC-0059, SPEC-0042, REQ-084, brief #2034, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `kit/`

## Context

SPEC-0077 (Approved, ADR-0837) rule 14 build (d) asks for rule 6, "safe to adopt". Build (c) (ADR-0840) copies a pack
only after `check_packs.problems` passed on it, which checks the manifest, the listed files' hashes and runs
`guard.scan_text`. Nothing checked whether a pack's text asks an agent to act, its licence, its size, what kinds of
file it holds, its tier against `[packs] trust` or its `kit` range against the running kit. Rule 6 leaves the size
numbers to this ADR (`Q-PD-2`).

## Decision

1. **One module, no detector of its own.** `scripts/agk/pack_scan.py` (installed, verbatim) holds `scan(root, folder)`,
   run by `packs.add` on the staged pack beside `check_packs.problems`, before anything is written. It reuses
   `steward_outbound.check` (the neutrality lists, `guard.scan_text` with the `[guard] patterns`, the project's hosts)
   on every text file and `gates/licences.allowed_list` and `passes` for the licence. A test asserts it holds no
   secret or token list.
2. **The instruction scan.** `instructions(text)` gives the numbers of the lines that ask an agent to approve, merge,
   push, skip or disable a check, reveal a secret, change its role or task, or ignore the rules (session rule 38): a
   verb with its object where a line asks (its start, after a sentence, after `please`, or after `you/agents must`),
   and the ignore-the-rules and change-of-role phrases anywhere. Every line is scanned, a fenced example too
   (`Q-PD-1`); there is no allow list and no ignore entry. A line that describes a review ("the reviewer approves a
   pull request when its tests pass") is not flagged.
3. **The size limits** (`Q-PD-2`). Measured on main 2bf8c76: the largest kit knowledge file is 7,000 bytes (a domain
   pack), the largest playbook 6,847 bytes, the largest skill 14,653 bytes, and all playbooks and domain packs
   together 55,999 bytes. The limits are 64 KiB per file (over four times the largest skill) and 512 KiB per pack (over
   nine times today's playbooks and domain packs), constants in `pack_scan.py`.
4. **The content rule** (`Q-S0077-2`). Refused, naming the pack's path class: a hook, an agent file, a workflow, a
   settings file or `.mcp.json`, a script (by suffix or the executable bit) outside a `skills/<name>/` folder, a binary
   file outside a skill's `assets/` (never read as text) and a file outside the kinds' folders. `permissions` keys stay
   `check_packs`' (only `network = "research"` and `mcp`).
5. **Trust and kit.** `admitted` refuses a tier below `[packs] trust` (`official` > `curated` > `community`) naming
   `packs.trust`, and a `kit` range not of the form `>=x.y.z,<a.b.c` or that does not hold the running kit's version
   naming `kit`. The running version is the plugin's in the clean layout, else `agk.toml` `version`, else the plugin
   manifest beside the script. `packs.verify` runs `admitted` on each locked pack, so the `playbooks` step does.
6. **A pack changed at the locked version.** A real update is `add` of the new tag (ADR-0840). `add` of a pack whose
   version is the lock's but whose files' hashes differ is refused naming the pack and `version`; the lock stays.
7. **Lines.** Each refusal is `rule 6: config/packs/<id>: ...` naming the key, setting or path class (and a line
   number), never a value or a line's text. `add` adds `gitleaks: not run`: gitleaks runs where prepush runs it
   (ADR-0327).

## Consequences

An outside pack can carry knowledge but never an instruction, a secret, a hook or an off-list licence. The outbound
guard fails closed: a project without a readable neutrality list or git remotes cannot add a pack, and a pack whose
text names another repository on a forge (its `source` on github.com, say) is refused (`Q-2034-1`). No workflow,
ruleset, required check, label, `agk.mk` or `governance_map.CHECKS` changes.

## Residual

`[packs] mcp` and the research path are build (f); the stale warning and `withdrawn` are build (i).
