# ADR-0019: the agk plugin, its marketplace, the issue intake and REQ-014

- Status: Proposed
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0001, ADR-0015, ADR-0017, ADR-0018
- Requirements: REQ-014

Protected classes: `.claude-plugin/`, `skills/`, `.claude/`, `.github/`, `config/`, `docs/requirements.md`, `scripts/agk/`, `kit/`, `tests/kit_dev/`

## Context

SPEC-0005 (Approved on 2026-10-15) recommends the hybrid distribution: the law stays vendored and enforced by CI, and a
Claude Code plugin carries the workflow commands. The plugin root is the root of this repository, which is also the
marketplace (rulings Q-K3-5 and Q-K3-8). The spec leaves two things to an ADR: adding REQ-014 (`docs/requirements.md` is
protected) and protecting the plugin's own paths (rule 20). Building it adds the manifest and marketplace file, one skill per
command, `scripts/agk/new_spec.py`, issue templates, an optional `Issue:` line in the pull request template, print-only
plugin settings entries in init and adopt, a README section, and `tests/kit_dev/`. The five `(verify)` facts of the spec were
read against the current Claude Code documentation; the record is `docs/runs/spec-0005-verify-facts.md`.

## Decision

1. **REQ-014 is added** to `docs/requirements.md`, Status `planned`, with AC1 to AC5 as listed in
   `docs/runs/spec-0008-notes.md` (the criteria the test markers imply).
2. **The plugin is built as SPEC-0005 specifies**: `.claude-plugin/plugin.json` (`name` `agk`, `version` equal to
   `kit_version`), `.claude-plugin/marketplace.json` (this repository, one entry `agk`, `source` `.`, no `version` of its
   own), and `skills/<command>/SKILL.md` for `init`, `adopt`, `doctor`, `upgrade`, `spec`, `issue`, `brief` and `review`.
   No hook, server, monitor, `bin/` or agent is shipped. The writing skills (all but `doctor` and `review`) set
   `disable-model-invocation: true`. No skill pre-approves a tool with `allowed-tools` (Q-K3-73).
3. **`scripts/agk/new_spec.py` is kit-only** (never installed, like `init.py`): it writes a Draft spec, an ADR draft that
   carries a requirement proposal, or a brief, from the repository's templates, only as new files. It never edits
   `docs/requirements.md`, never sets a status beyond `Draft` or `Proposed`, and records `Issue: #N` with the copied issue text.
4. **Issues are intake only.** `.github/ISSUE_TEMPLATE/{proposal,question,report}.md` are installed verbatim; the pull request
   template carries an optional `Issue: #nnn` line; `check_pr_body.py` is unchanged and does not require it.
5. **Init and adopt print the plugin settings entries** (`kit/templates/plugin-settings.txt`, print only; no JSON is merged),
   with `ref` set to the release tag `v<kit_version>`.
6. **Protected classes.** `.claude-plugin/` and `skills/` are added to `config/protected-paths.txt` and to the `protected` and
   `kit` classes of `config/reviewers.yaml`; CODEOWNERS is re-rendered; `.claude/settings.json` gets an `Edit` ask rule
   for each (the stop-hook test requires one for every protected path, as for `kit/` and `tests/kit_dev/`). The plugin
   directories are not installed into projects; the two ask rules are, and are inert there.
7. **Kit version 0.10.0** (one bump): the installed pull request template, three issue templates and the `ask` rules of `.claude/settings.json` change.
8. Deviations from the Approved text are in `docs/runs/proposed-spec-amendments-13.md`, not applied.

## Consequences

- A plugin install gives `/agk:<command>`; a repository without the plugin keeps working (SPEC-0005 rule 2).
- `claude plugin validate .` passes with one warning: `CLAUDE.md` at the plugin root is not loaded as plugin context.
- Every release is a tag `vX.Y.Z` on the default branch with the same version in the manifest and `plugin.json`.

## Residual

- 2026-10-16: whether `ref` is read on a `github` source inside `extraKnownMarketplaces` is not confirmed by the settings
  reference (Q-K3-72); the printed entry carries it and a `(verify)` note (due 2026-11-30).
- 2026-10-16: whether `${CLAUDE_PLUGIN_ROOT}` expands in a permission rule of `settings.json` is undocumented; the skills
  `allowed-tools` frontmatter documents it for Bash rules, and no skill uses it until the maintainers decide (Q-K3-73)
  (due 2026-11-30).
- 2026-10-16: the proof of SPEC-0005 rule 18 (add the marketplace, install, `/agk:init` on a fresh repository, `governance`
  green) is the maintainers' step, as for K1 and K2 (due 2026-11-30).
