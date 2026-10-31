# ADR-0230: every proof run publishes a test manifest: what ran, what did not, and why (REQ-016, brief 425)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0172, ADR-0185, ADR-0196, ADR-0220
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `.github/`, `tests/kit/`

## Context

A tag such as `@needs-renderer` was skipped by a project's own test configuration on one operating system, and nothing listed
it (#289, field note 2). Proof's `--json` holds areas, files and seconds (brief #305), and the test plan lists test files in no
area (brief #325), but the CI job shows one line, `proof: <outcome>`. Brief #425 gives the answers.

## Decision

1. **The manifest (answer 1).** `proof.py --manifest FILE` writes a Markdown manifest with three sections. `Ran`: per run of
   the plan, the area (or `project_tests`), the command as run, its folder, the number of files and the first 40 of them, then
   `and n more`, and the seconds of the base run and of the head run, each kept apart, a run ended by `proof_timeout` marked so.
   `Not run`: each changed test file in no `[proof]` area (`in no [proof] area`), each deleted test file (`deleted`), and for a
   skip each planned run with its reason: `Behaviour: unchanged` in the body, or a draft or a status-only final commit. An
   unknown outcome with nothing run names its reason (no `project_tests`, no added or changed test file). `Excluded by the
   project`: the `[testing] excluded` entries. The output line, `--json` and the exit statuses are unchanged; the manifest is
   written only when asked for, and a bad `[testing]` setting is then refused before anything runs.
2. **The skips the workflow decides (answer 1, Q-425-1).** A draft and a status-only final commit are decided by `proof.yml`,
   not by proof. Read conservatively, `proof.py --not-run draft|status-only` builds the plan, runs nothing, prints
   `proof: skipped (<reason>)` and writes the manifest of that skip, so the reason is proof's text and not the workflow's.
3. **`excluded` (answer 2).** The `[testing]` table accepts `excluded`, a list of `"<tag>: <reason>"` texts: a tag with no
   space or colon, `: `, and one line of reason. Proof never interprets them; it lists them in every manifest. A malformed
   entry is refused naming the setting (`testing.excluded` or `testing.excluded[n]`), never the value, by `impact.py`, so
   the test plan and the pre-push gate refuse it too. The dictionary `testing_table` returns is unchanged; `excluded_entries`
   reads the list.
4. **The job summary (answer 3).** The `Red-then-green` step passes `--manifest`, and a last step, `Test manifest`, appends
   the manifest to the job summary on every outcome, skipped included, and also after a failed run step, when it appends one
   line that says no manifest was written. While agk is paused the step is skipped like every other step (ADR-0196): the
   `Paused` step already writes `agk paused` to the summary.
5. **Tests first (answer 4).** `tests/kit/test_proof_manifest.py`: two areas with files, more than 40 files, a file in no area,
   a deletion with and without a `[proof]` table, `Behaviour: unchanged`, a draft and a status-only skip, the unknown reasons,
   excluded tags in every manifest, malformed entries, a timed-out run, and the two workflow steps.

## Consequences

Every ready push of a pull request shows in its job summary what proof ran and what it did not, with the reason, and every
exclusion a project declares. A project that excludes tests says so in `agk.toml`, a protected path, with an ADR.

## Residual

- 2026-10-31: Q-425-1 (decision 2): `--not-run` is the conservative reading of "the reason for a draft".
- 2026-10-31: Q-425-2: `docs/guides/testing.md` and the commented `[testing]` table of the kit templates do not yet name
  `excluded`; they are outside the brief's `Touches:` line and are left to a later brief.
