# ADR-0041: `/agk:ruleset` and `ruleset.py plan` (SPEC-0013 rules 19 to 22), kit 0.21.0

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0001, ADR-0021, ADR-0040
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `skills/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

G2 of the four-part build of SPEC-0013 (ADR-0040). The pilot's first day showed that applying the ruleset by hand is the slowest step of a new
repository and that a required check that has never run blocks the first merge. Q-K4-101 (ruled with the `(verify)`) requires the implementation to
prove on the sandbox what GitHub does for such a check before relying on phase detection. The sandbox ruling (corrected 2026-10-18): the existing
`gbvraju/agk-sandbox`; fixtures and a dry run first; the only writes are added rulesets there, each naming it; the existing ruleset is never edited or
deleted; no write to `gbvraju/agk`, `gbvraju/cors` or any upstream; a second GET afterwards listing what was added; stop and report if the `gh` login
lacks admin; never ask for or handle a token.

## Decision

1. **`scripts/agk/ruleset.py plan`** (kit-only) reads with `gh api --method GET` (the repository, its rulesets and each branch ruleset, the successful runs of
   `governance.yml` on the default branch) or from recorded files in `--api-dir`, and prints the plan. It calls no write method, holds no credential
   and imports no `subprocess`: reads go through the doctor's `Reads`. The desired ruleset is `kit/templates/ruleset.json` (kit-only): ADR-0001 decision 3,
   with the required check as `phase2_rules`, and the two repository settings.
2. **Add-only and idempotent** (rule 20): it creates the ruleset when none matches the default branch; adds a missing rule (to the first matching
   ruleset, counting the rules of every active matching ruleset as the doctor does), adds `governance` to an existing status-check rule that lacks it, and
   sets a missing repository setting. It never removes a rule, a context, a setting or a bypass actor. A looser value (enforcement not active, a bypass
   actor, stale approvals kept on push, a merge method other than squash) is a printed `finding:` and changes only with `--tighten`; a stricter value
   (two approvals) is left. A plan after the plan is applied prints `nothing to do`.
3. **Two phases** (rule 21): `--phase auto` (the default) is phase 2 when the runs read returns at least one successful run of `governance.yml` on the
   default branch, phase 1 when it returns none, and phase 1 when the read fails. Phase 1 omits the required status check.
4. **Cannot apply** (rule 19): not an admin, `gh` missing or not logged in, or any failed read prints the text of `kit/templates/branch-rules.txt` and the path in
   the settings, nothing else, exit 4.
5. **The skill `/agk:ruleset`** shows the plan (with `--payload-dir` in a temporary directory), asks, and only then runs the printed
   `gh api --method POST|PUT|PATCH ... --input FILE` commands; it never passes `--tighten` itself. It is the second command that writes outside the
   working tree (Q-K4-97 ruled). **Amendments applied here** (`proposed-spec-amendments-15.md`): item 1 for `/agk:ruleset` (SPEC-0005 rules 8, 9, 10; the
   rows for `start` and `architect` are applied by the later parts), item 4 (SPEC-0006 rule 5: the printed fix of `required-check-governance` names
   `/agk:ruleset`; `doctor.py` prints it), item 5 (SPEC-0001 rule 19 and SPEC-0002: `init` and `adopt` print one line pointing to `/agk:ruleset` after the
   branch rules).
6. **The sandbox proof (Q-K4-101) is not complete.** `docs/runs/ruleset-sandbox-proof.md` records the first GETs of the repository and its rulesets, the
   dry run (`nothing to do`: the sandbox's `Main` ruleset is complete and `governance` has succeeded on `main`), and the one write attempted (adding an
   inert ruleset that requires a check that has never run, on a branch name that does not exist): the session's proxy refused it with HTTP 403 ("Write
   access to this GitHub API path is not permitted through this proxy"). No retry, no other route, no token. A second GET shows the rulesets unchanged.
   The record gives the maintainers the exact payload and command and what to observe. Until then the behaviour of GitHub for a never-run required check
   stays `(verify)` and phase 1 stays the default whenever `governance` has not succeeded.
7. **Tests**: `tests/kit_dev/test_ruleset.py` on the doctor's recorded `ok` responses with variants (no ruleset; phase 1 and 2; auto from the runs read;
   unknown runs; a missing rule; the check added; another context; a stricter value; looser values with and without `--tighten`; a bypass actor; a disabled
   ruleset; the PUT payload without read-only fields; repository settings; idempotence; rules spread over two rulesets; not admin; unreadable; no `gh`;
   usage errors), a fake `gh` that logs every call (all `GET`), a static check that the script has no `subprocess`, credential or environment access, and
   the payload files. `test_distribution.py` gains the skill (nine commands; user-invoked; the write verb only in `ruleset`).
8. **Kit 0.21.0**: manifest, hashes, plugin version (installed file changed: `doctor.py`).

## Consequences

- A new repository can be protected in two commands and a person's yes; the doctor's phase-1 failure of `required-check-governance` now says what to do.
- The never-run check question is open until the maintainers run the steps of `docs/runs/ruleset-sandbox-proof.md` or allow the session a branch and a pull
  request on the sandbox.

## Questions

| Q | Question | Reading taken |
| --- | --- | --- |
| Q-K4-177 | Rule 19 says `plan` writes nothing; the skill must run commands "from payload files in a temporary directory". Who writes the files? | `plan --payload-dir DIR` writes them, only there, only when asked; without it the payloads are printed inline. No file in the repository, nothing to GitHub. |
| Q-K4-178 | `--phase auto` when the runs read fails. | Phase 1 (never require a check on a guess). |
| Q-K4-179 | Which values count as "looser" than the kit's? Rule 20 gives examples. | Enforcement not active; any bypass actor; stale approvals not dismissed on push; a merge method list other than exactly `squash`. The approval count only goes up (stricter is left). |
| Q-K4-180 | The proxy of this environment refuses writes to the rulesets path. | Reported, not worked around; the proof is left to the maintainers' login (see Decision 6). |

## Residual

- 2026-10-18: what GitHub does for a required check that has never run is not proven on the sandbox (due 2026-11-30, as the Residual of SPEC-0013).
- 2026-10-18: the plan finds the ruleset to extend by the default branch it targets, not by name; a repository with several matching rulesets gets additions in
  the first active one by id (due 2026-12-31).
