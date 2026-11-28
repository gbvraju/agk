# ADR-0862: The build files are written from the parts record

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2072, 2026-11-27T19:43:49Z; amendment 259 approved on #2018,
  2026-11-27T20:04:11Z)
- Related: ADR-0834, ADR-0860, ADR-0867, ADR-0672, SPEC-0076, SPEC-0072, REQ-083, brief #2072, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (e) asks for rule 8's "Written" half and amendment 259 to SPEC-0072 rule
4. On main at 5a03bd08, with an Accepted stack record and a confirmed `docs/parts.md` naming one runtime part,
`engines.py stack-files` wrote `"dependencies": {}`: the record was never read. Build (d) (ADR-0867) gave the one
reader of the record (`gates/parts.py`: `sections`, `confirmed`, `settings`).

## Decision

1. **Written from the record.** When `parts.confirmed(root)` is true, `cmd_stack_files` renders the chosen stack's
   template as before and fills it from the record's rows of the chosen runtime (a section that names another runtime
   by `pins.RUNTIME_NAMES` is not read): each `Kind: runtime` part as a dependency, each `Kind: dev` part as a dev
   dependency, at its exact recorded version, sorted by name and spelled as the record spells it; a `stdlib` part
   writes nothing. `node`: `package.json`'s `dependencies` and `devDependencies`, two-space JSON and a final newline.
   Python: the template's one `dependencies = []` line holds the runtime parts as `"<name>==<version>"`, and dev parts
   go to `[project.optional-dependencies] dev`, which `pins.direct` reads (`Q-PE-2`). It prints `wrote <file> from
   docs/parts.md (<r> runtime, <d> dev parts); make <lock> with the stack's own tool and commit both`, counts only.
2. **Refusals before any write**, not even `config/licences.toml`, each exit 1 and never a name or a version: a
   refused `[parts]` table (`the [parts] table is refused (setting: parts.<key>)`); `record = "required"` with no
   confirmed record (`SPEC-0076 rule 3: the build file waits for a confirmed parts record (setting: parts.record)`,
   `Q-PE-3`); a confirmed record with no table of the nine columns, or not UTF-8 (`SPEC-0076 rule 8: the parts record
   cannot be read (path class: docs/parts.md)`); a row whose version is not exact for its stack (`pins.EXACT_NPM`, or
   `pins.EXACT_PY` with `==` before it; a `(verify)` mark is not exact) or whose `Kind` is not `runtime` or `dev`
   (`SPEC-0076 rule 8: a record part cannot be written (component class: record part)`).
3. **No confirmed record.** With no `[parts]` table or `record = "optional"`, the output is today's byte for byte; with
   a record that is not confirmed one more line `not written from docs/parts.md: not confirmed (setting:
   parts.record)`. `max_age_months` and `advisories` are not read here.
4. **Unchanged.** No stack chosen, two runtimes (`Q-PE-5`), an adopted tree and a project's own or already written
   build file behave as before (`not run: no stack chosen`, `kept <name>`). The chosen option's `Parts:` (the platform)
   are not written (`Q-PE-4`). No workflow, ruleset, required check, `agk.mk` or `governance_map.CHECKS` changes.

## Consequences

A foundation whose record is confirmed starts with exactly the libraries chosen per need, so build (d)'s `parts` step is
green once the stack's own tool makes the lock. `stack-files` stays the one kit writer of a build file's dependencies.
SPEC-0072 rule 4 carries amendment 259 word for word.

## Residual

Two runtimes in one option stay `not run` until a build widens `stack-files` with `pins.runtimes` (`Q-PE-5`).
