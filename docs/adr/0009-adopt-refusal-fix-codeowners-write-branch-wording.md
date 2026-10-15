# ADR-0009: Adopt refusal names its fix, CODEOWNERS --write, branch-rule wording

- Status: Accepted
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0001, ADR-0007, ADR-0008
- Requirements: REQ-005, REQ-010

## Context

The live proof on the colorama fork (`docs/runs/k2-live-proof.md`) produced two findings and one wording point:
(a) a session clone may lack `refs/remotes/origin/HEAD`, and adopt then refuses without saying how to fix it;
(b) `reviewers.py --codeowners` prints to stdout, which an agent may not be allowed to redirect into a file;
(c-wording) the printed branch-rule text says "ruleset `main`" although the default branch can have any name.
This repository's ADR-0001 is Accepted and immutable, so it keeps its wording; the template and the printed text
change instead.

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `tests/kit_dev/`. This PR changes all four.

## Decision

1. **Adopt's refusal names the fix.** When the default branch cannot be read, adopt refuses (exit 1, nothing
   written) and the message names the path class `.git/refs/remotes/origin/HEAD` and the command
   `git remote set-head origin --auto`. Adopt gains no option and still makes no git call.
2. **`reviewers.py --codeowners --write`.** Writes `.github/CODEOWNERS` instead of printing it: the whole file in an
   init or kit repository; in adopt mode (`agk.toml` `mode = "adopt"`) only the marked block (appended when absent,
   replaced when present, the rest of the file untouched; an absent file is created whole, as adopt does). It says
   `wrote`, or `unchanged` when nothing changes, refuses a broken or duplicated block and an invalid configuration
   without writing, and treats `--write` alone or with another mode as a usage error. Plain `--codeowners` still
   prints. CODEOWNERS stays the one generated file that is committed (ADR-0003 decision 3).
3. **Printed branch-rule text.** `kit/templates/branch-rules.txt` reads "The ruleset for the default branch is
   exactly: ..." instead of "The ruleset `main` is exactly: ...". This repository's ADR-0001 text is untouched; the
   equality test compares everything after "is exactly:" and checks the head wording separately. The ADR templates
   already say "ruleset for the default branch (`{{default_branch}}`)" (ADR-0007).
4. **Kit version** `0.4.1`: installed content changed (`scripts/agk/reviewers.py`).
5. **Specs.** Approved specs are not edited. Two rules name the old text and are proposed for amendment in
   `docs/runs/proposed-spec-amendments-4.md`.

## Consequences

- An adopt refusal after a fresh clone now says what to run; no new option to maintain.
- Agents can regenerate CODEOWNERS with one command and no shell redirect; an adopted repository's own CODEOWNERS
  lines are never rewritten.
- The printed ruleset text no longer equals this repository's ADR-0001 word for word (only the first words differ).

## Residual

- 2026-10-14: `--write` writes through `Path.write_text`, not atomically; a crash mid-write could leave a partial file
  that `--check-codeowners` then reports.
- 2026-10-14: class naming in an ADR is still a substring match (ADR-0003 residual).
