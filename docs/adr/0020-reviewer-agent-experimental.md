# ADR-0020: the reviewer agent becomes experimental and is no longer installed by default

- Status: Proposed
- Date: 2026-10-16
- Deciders: maintainers
- Amends: ADR-0011
- Related: ADR-0011, ADR-0015, ADR-0019
- Requirements: REQ-013

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.toml`, `.claude-plugin/`, `skills/`

## Context

ADR-0015 criterion e asks the reviewer agent to catch at least 3 of 5 recorded human findings, with at least 1 held-out
finding caught, and otherwise to be moved to experimental. Shadow review 4 (`docs/runs/shadow-review-4.md`) caught 0 of 5
and 0 of 2 held-out; shadow reviews 2 and 3 caught 0 of 3 recorded findings. Criterion e is not met. Three of the five
reports of shadow review 4 failed the report validator because of notes after a finding; the validator correctly rejects a
malformed report. In four of five runs the context was truncated, which may have contributed.

## Decision

1. **Experimental.** The reviewer agent and `/agk:review` are experimental: advisory, never a gate, never counted as
   review. Human review stays required. This amends ADR-0011, which installed the reviewer by default.
2. **Not installed by default.** `agk init` and `agk adopt` no longer write `.claude/agents/reviewer.md`,
   `scripts/agk/review_context.py`, `scripts/agk/check_review_report.py` or the four installed tests of them
   (`tests/kit/review_fixtures.py`, `test_review_context.py`, `test_review_report.py`, `test_reviewer_definition.py`)
   unless the target's `agk.toml` sets `experimental_reviewer = true`. The seven paths move from `verbatim` to a new
   `experimental` list in `kit/manifest.json`; `kit/hashes.json` hashes them like any installed file so a later upgrade can
   tell an old copy from an edit.
3. **Opt-in and effects.** The key is read from the target's `agk.toml` by `common.experimental_enabled`. A fresh `init`
   has no `agk.toml` to read, so the way in is: install, set the key, run `agk upgrade`, which creates the seven files
   (they were never installed, so they are not reported as deleted). `agk doctor` compares the seven files with the kit's
   copies only when the key is set. A target that already has the files and no key is told by `agk upgrade`:
   `removed-in-kit`; nothing is deleted. Re-running `init` or `adopt` after editing `agk.toml` stays a conflict, as for any
   edit of that file (Q-D10-1).
4. **`/agk:review`** says the reviewer is experimental and stops with an instruction when `.claude/agents/reviewer.md` is
   absent.
5. **This repository** keeps its own copies and sets `experimental_reviewer = true` in its `agk.toml` for the experiment.
6. **README:** the reviewer section is headed "Experimental: reviewer agent", states the measured result in one sentence
   and links to `docs/runs/shadow-review-4.md`.
7. **Rulings** (maintainers, 2026-10-16). Q-SR4-1: yes, experimental now; any widening of SPEC-0003 rule 11 waits for K4
   and a new held-out set. Q-SR4-2: neither change; the validator correctly rejects malformed reports, and that stays
   recorded.
8. **Kit version 0.11.0** (the next minor): installed content changed (the verbatim set, `common.py`, `doctor.py`, the
   `agk.toml` templates). The plugin version is bumped with it.

## Consequences

- New installs carry five fewer verbatim scripts and tests; existing installs keep their files until the maintainers
  choose to delete them.
- SPEC-0003 stays Approved and unchanged; its rules describe the experiment, not a default.
- Q-D10-1 (below) is open.

## Residual

- 2026-10-16: context truncation in 4 of 5 shadow-review runs may have contributed to the misses; record it for K4
  (due 2026-12-31).
- 2026-10-16: a fresh `init` cannot opt in at install time; the first opt-in is a second step through `agk upgrade`.
  Q-D10-1: should init and adopt take a flag that writes the key into `agk.toml`? Not built; the conservative reading
  keeps one source of truth, the key (due 2026-12-31).
