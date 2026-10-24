# Proposed spec amendments 45 (SPEC-0001, SPEC-0002, SPEC-0006, SPEC-0007; REQ-032 part c, dependence and mode)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0086. The paths: `docs/specs/0001-agk-init.md`, `docs/specs/0002-agk-adopt.md`,
`docs/specs/0006-doctor.md`, `docs/specs/0007-metrics.md`.

1. **SPEC-0001 and SPEC-0002, the `agk.toml` templates.** The `agk.toml` written by `init` and by `adopt` carries `pr_mode = "strict"` with a comment (SPEC-0025 rule 6); an existing `agk.toml` without the key
   reads as `strict`.
2. **SPEC-0006, the doctor.** The table of checks gains `pr-mode` (warn, local): it fails when `pr_mode` in `agk.toml` is neither `strict` nor `flow`; the message names the setting, and an `ok` message states the mode. Printed fix:
   set `pr_mode` in `agk.toml` to `strict` or `flow` (a change needs an ADR).
3. **SPEC-0007, the governance workflow (rule 13).** The workflow gains one fetch step (read-only GETs into `states.json` and `open-prs.json` in the runner's temporary directory) and one check step,
   `check_pr_mode`; the checks are twelve, one step each.
