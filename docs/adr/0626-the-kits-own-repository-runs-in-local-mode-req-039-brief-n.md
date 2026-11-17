# ADR-0626: The kit's own repository runs in local mode, every gate recorded as evidence

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1471, brief #1447, ADR-0182, ADR-0237, ADR-0536, ADR-0605, ADR-0306, plan #661
- Requirements: REQ-039

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`

## Context

Brief #1471 (the owner's direction of 2026-11-17): `gbvraju/agk` is public, so GitHub bills no Actions minutes for it,
and `agk.toml` has no `execution` key, so it runs `hosted` (ADR-0237): every pull request's `proof` and `governance` run
on GitHub Actions. Made private, those runs are metered. Local mode exists for projects (ADR-0182, the guide, `local_mode.py`,
the record issue, `Local evidence:` and `Evidence check: agrees` before `merge_cleared.py` merges), and since ADR-0536 and
ADR-0605 the builder's record travels with its pushed head as a git note that the conductor's `evidence.py check --head`
reads from another machine. The kit's own repository has never run in it. A cloud session's container has no gitleaks, so
`prepush.py`'s secret scan fails there or is deferred to a CI that local mode turns off.

## Decision

1. **The setting (answer 1).** The kit's own `agk.toml` gains the top-level `execution = "local"` with its comment.
   Nothing else in it changes: `required_checks` still names `proof` and `governance`, which in local mode are read from
   the builder's evidence, not from Actions (SPEC-0039 rule 4 as built).
2. **Every gate still runs (answer 2).** No check is dropped; only where it runs changes: the builder runs
   `prepush.py --record` on its head, the conductor runs `evidence.py check --head <sha>` on the note, the verdict carries
   `Local evidence:` and `Evidence check: agrees`, and `merge_cleared.py` holds a pull request without both, as today
   (`tests/kit/test_kit_repo_local_mode.py` pins that hold).
3. **gitleaks in a cloud session (answer 4).** When gitleaks is missing and `CLAUDE_CODE_REMOTE` is `true` (the
   variable `common.REMOTE_RUNTIME` names, `(verify)`), the doctor's secret-scan line names the tool, the pinned version
   and the one line the owner adds to the cloud environment's setup script `(verify: the environment setup script of the
   runtime)`: it downloads the pinned release archive, checks the SHA-256 that `.github/workflows/governance.yml` pins and
   unpacks gitleaks onto PATH. The doctor prints that line and never runs it; no session downloads or installs gitleaks.
   Outside a cloud session the line is unchanged.
4. **The switch-over (answer 5).** `docs/guides/local-mode.md` gains the section "A kit's own repository goes private"
   with the owner's six steps in order, each printed for the owner and never run by a session.
5. **The doctor's line (answer 6).** `doctor.py` gains the warning `local-mode-switch`: with `execution = "local"` it
   reads, with GET only, the repository's workflows, its open issues and its rulesets (the reads the ruleset checks
   already make, so no new ruleset read), and warns, naming the setting `execution` and counts, never a value, when a
   workflow is still `active`, when no open issue (not a pull request) is titled `Local mode since`, or when an active
   ruleset of the default branch still requires a check of `required_checks`. A read that fails is `cannot-check`, never
   `ok`. Without `execution = "local"` it reads nothing and is `ok (not applicable)`.
6. **By mode (answer 7).** Hosted and hybrid projects: unchanged. Local-mode projects: they gain only the doctor line of
   decision 5 (and, in a cloud session, the setup line of decision 3). Personal mode and customer projects: unchanged.
7. **The owner's changes stay the owner's.** Rulesets, workflows and the repository's visibility change only by the owner;
   no workflow file, ruleset or required check changes here, and no workflow is deleted.

## Consequences

The kit's own repository can be made private once the owner has taken the six steps, without metered minutes and without
dropping a check. From the merge of this decision, `merge_cleared.py`, the router and `prepush.py` read the kit's own
repository as local: the conductor merges on evidence, and a builder's `--record` also writes the note. The doctor's
`local-mode-switch` warns until the owner's steps are done. The release pull request's full-suite record read by
`check_release.py` (answer 3) and the readings of the brief's questions are recorded on the pull request (Q-1471-n).
Tests: `tests/kit/test_kit_repo_local_mode.py`; `tests/kit/test_doctor.py` counts the new check.

## Residual

- 2026-11-17: answer 3 (the release pull request's full-suite record, read by `check_release.py`) is not built here;
  `check_release.py` is outside the brief's `Touches` (Q-1471-3 on the pull request).
- 2026-11-17: with `execution = "local"`, `common.clone_shared_by` makes a cloud builder's own clone a shared one, so
  `session.py claim` and `push-check` refuse its main folder; a builder starts in its own worktree (Q-1471-1).
- 2026-11-17: in local mode `required-check-governance` and `drift-workflow-state` fail once the owner's steps are done,
  which `local-mode-switch` asks for (Q-1471-2).
