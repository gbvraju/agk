# ADR-0094: this repository switches to flow mode (SPEC-0025 rule 8, phase 0a of the conductor plan)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0082, ADR-0086
- Requirements: REQ-032

Protected classes: `agk.toml`

## Context

SPEC-0025 (Approved) lets a repository choose how many pull requests a person may have open. Its parts (a), (b) and (c) are built and released (kits 0.46.0 to 0.49.0: duplicate numbers fail and `intake.py renumber`,
`merge=union` on the append-only logs, the author rule, `Depends-on` and `pr_mode`). Rule 8 says that after they are released a separate pull request switches this repository to `flow` by an ADR; until then it stays
`strict`, with the maintainers' docs-only exception of 2026-10-24 (`docs/runs/decisions-log.md`). The brief in issue #160 (step 0a) asks for the switch, for this repository only: users' projects keep the default.

## Decision

1. `agk.toml` sets `pr_mode = "flow"` (it was `"strict"`). In flow mode any number of pull requests may be open, the `pr-mode` check passes an older open pull request of the same author, and a `Depends-on` line is allowed.
2. The maintainers' docs-only exception of 2026-10-24 ends: it existed because the strict check cannot tell a docs-only pull request apart, and flow mode needs no exception.
3. A pull request that needs another one's unmerged change declares `Depends-on: #n` in its body and cannot merge before it (the `pr-mode` check fails while the named pull request is not merged).
4. Every pull request still starts from `origin/<default branch>`; a dependence is declared, never a stack. `make governance` must pass on each pull request, and what a pull request must prove (tests first, proof, review, a
   listed author's verdict and a person's merge) is the same in every mode.

## Consequences

- Several pull requests of this repository can be open at once. Kit builds still bump the version themselves until the release pull requests of step 0b exist, so two parallel kit builds collide in
  `kit/manifest.json`, `agk.toml`, the plugin version and `kit/hashes.json`; the working rule keeps one kit build open at a time until 0b is merged.
- `CLAUDE.md` rule 2 still says one open pull request at a time; it is a protected file and this ADR does not change it.

## Residual

None.
