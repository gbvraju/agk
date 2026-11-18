# ADR-0633: Personal adopt renders only the claims whose citations exist, for the person to confirm

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: ADR-0267, ADR-0632, SPEC-0041, brief #1504
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `skills/`, `kit/`, `agk.toml`, `tests/kit/`

## Context

SPEC-0041 rules 13 and 14 ask that the model's reading of the code become records in the sidecar only through claims
whose citations exist, and that nothing rendered counts as decided until the person confirms it (rule 15, built by
ADR-0632). On main `survey.py` writes the inventory and the reading list (build (f)), but there is no
`personal_adopt.py` and no `/agk:personal-adopt` skill. ADR-0267 asks each build of the spec for its own ADR naming its
classes; this is build (g), part 2.

## Decision

1. The proposals are one JSON object with the optional lists `requirements`, `specs` and `adrs`; each record has a
   non-empty `title` and a non-empty list `claims`, each claim a non-empty `statement`, a non-empty list `citations`
   of `path:start-end@blob` (a 40- or 64-hex blob) and an optional `verify` flag; a spec may name `requirements` and
   an ADR `specs` and `requirements` by their index in the same file. A file of another shape is refused whole.
2. `personal_adopt.py check FILE [--clone DIR] [--sidecar DIR]` refuses each claim with a citation whose path is not
   tracked in the clone's index, whose blob is not that path's blob at a commit reachable from a ref of the clone
   (`git log --all -m --raw`), or whose range is not inside the blob; a claim whose statement holds more cited lines
   (each of eight or more characters) than `[personal] quote_lines`; and a claim or title in which the data guard
   (`guard.scan_text`) finds a value. Each refusal is one line naming the position (`adrs[0].claims[1]`) and the rule,
   never the text or the path. It exits 1 when any claim is refused.
3. `render` makes the same checks and, from a clean sidecar, writes each record with at least one claim left:
   requirements appended to `docs/requirements.md` as `planned` with one `- Acceptance:` line of the claims and
   `- Source: observed in code at <citations>`; specs `Draft` under `docs/specs/`; ADRs `Proposed` with
   `- Kind: recorded` under `docs/adr/`; a claim with `verify` and each point the citations cannot show (an unnamed
   link, an ADR's consequences) marked `(verify)`. Numbers come from `common.next_free_ids` on the sidecar's `HEAD`,
   a requirement never below `REQ-101` (the sidecar's own text keeps `REQ-001` to `REQ-099` for AGK, `Q-1504-1`). A
   record whose title and citations are already in the sidecar is not rendered again. The data guard scans each
   rendered text before any write; a finding writes nothing. One sidecar commit under the files forge's lock holds
   the files, and the script prints the `personal.py confirm` command of each new record. All git calls on the clone
   are read-only with `--no-optional-locks`.
4. The skill `/agk:personal-adopt`, shipped in the plugin, runs every script from `${CLAUDE_PLUGIN_ROOT}`, writes the
   proposals file under the sidecar's ignored `cache/`, tells the person the coverage line and the count refused,
   renders only after the person agrees and lists the `confirm` commands; it never runs `confirm`.
5. `personal_adopt.py` joins the manifest's `verbatim` list and `agk.toml` maps it to
   `tests/kit/test_personal_adopt.py`.

## Consequences

The model's reading of a codebase leaves cited Draft and Proposed records in the sidecar, and an uncited, quoted or
secret-shaped claim never reaches a file. A citation proves that the lines exist, not that they show the statement:
that is the person's to judge when they confirm.

## Residual

- 2026-11-18: the read ledger of the survey (rule 11) is not updated by a render; the skill reads the reading list
  of each run.
