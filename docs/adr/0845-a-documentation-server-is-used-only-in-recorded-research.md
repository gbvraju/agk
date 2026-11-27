# ADR-0845: A documentation server is used only in the steward's recorded research

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2044, 2026-11-27T13:18:12Z)
- Related: ADR-0837, ADR-0838, ADR-0840, ADR-0841, ADR-0639, SPEC-0077, SPEC-0072, SPEC-0048, REQ-084, brief #2044, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0077 (Approved, ADR-0837) rule 14 build (f) asks for rule 7's research path and rule 12's `mcp` key. Build (a)
(ADR-0838) reads `[packs] mcp` and refuses a name out of form or one no pack of `use` declares in `permissions.mcp`,
but nothing else reads the key: a declaring pack counts by its manifest's hash only, not by the lock (build (c),
ADR-0840) or the trust and `kit` checks (build (d), ADR-0841). `steward_owner.py research` records the person's yes and
prints `search: <TEXT>`; it knows no server. Rule 7 keeps a server out of every check, gate and verdict.

## Decision

1. **The allowed servers.** `packs.servers(root)` gives the names of `[packs] mcp`, in order, each declared in
   `permissions.mcp` by a pack of `[packs] use` that passes `packs.verify` (the lock, the trust, the `kit` range) and
   `check_packs.problems`; `packs.left_out(root)` gives the listed names every declaring pack of which fails. Both read
   files only and raise `packs.Refused` naming `packs.<key>` on a refused table. `packs.declared(root, use)` maps each
   declared name to its packs; `config.packs_settings` reads the declarations through it, so its refusal is still
   `the [packs] table is refused (setting: packs.mcp)`. It now also refuses a listed name that `guard.scan_text`, with
   the `[guard] patterns`, flags (brief answer 6).
2. **The research path.** `steward_owner.py research ... [--server NAME]`: a name outside `packs.servers`, an empty
   one, or any name on a refused table, is refused before anything is read or recorded,
   `refused: the documentation server is not allowed (setting: packs.mcp)`, exit 2, never the name. On an allowed name
   the yes is read and recorded as before, the record ending ` (server: <name>)`, and only on a yes it prints
   `server: <name>` before `search: <TEXT>`. Without `--server` nothing changes. The script opens no socket; the
   session uses the server through the runtime and its answer is data (session rule 38). A fact from it is pinned only
   as a `- Source: <URL> (accessed YYYY-MM-DD)` line naming the publisher's own page; `check_research` is unchanged.
3. **The name's form in a pack.** `check_packs._keys` fails a `permissions.mcp` name outside `NAMES` with
   `rule 3: config/packs/<id>: the key has the wrong value (key: permissions.mcp)`.
4. **Doctor.** The `packs-settings` row ends `, servers <n>`, the allowed count; `doctor.pack_server_lines` gives one
   `warn packs: a listed documentation server has no verified pack in use (setting: packs.mcp)` line per name
   `left_out` names, never the name, printed with the stale lines. Doctor never reads or writes the runtime's server
   settings.
5. **Never in a check, a gate or a verdict.** No script of `governance_map.CHECKS` or `scripts/agk/gates/` names
   `servers(` or `packs.mcp`, and no verdict agent's `tools:` line names an `mcp__` tool; a static test holds both.

## Consequences

A current fact can come from a declared, locked and verified pack's documentation server on the person's recorded
yes, and from no unlisted server. Setting the server up in the runtime stays the person's; where the runtime reads
that setting is not confirmed (`Q-PF-1`, `(verify)` in the guide). No workflow, ruleset, required check, label, hook,
agent file, `agk.mk` or `governance_map.CHECKS` changes.

## Residual

- 2026-11-27: where the runtime reads a project's documentation server setting stays `(verify)` (`Q-PF-1`), due with
  the spec's Residual, 2027-03-31.
- 2026-11-27: a hook on a session's calls to a server (`Q-PF-5`), a stricter research yes in team mode (`Q-PF-3`) and a
  steward agent tool line naming the server (`Q-PF-4`) are later briefs.
