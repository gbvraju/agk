# ADR-0165: the router wakes when any required check finishes (REQ-039, brief 285)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0137, ADR-0164
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #285 (priority 0). The router workflow `agk-route.yml` woke on `workflow_run` of `governance` and `proof` only. A project
that adds its own required checks to `required_checks` (two, in the pilot of 2026-10-27) gets no wake-up when they finish. If one
of them finishes last, the pull request stays `agk:ci-running` with every check green until the next push, edit or verdict.
The cause was reproduced first on this repository: the kit's `agk-route.yml` reads `workflows: [governance, proof]`, and no part
of the kit wrote any other name into it. SPEC-0032 rule 1 already says the router listens to "the workflows that hold the
required checks". The kit did not do that until now. The tests were written first (checkpoint 14175bd), and 20 of them were
red on the unchanged tree.

## Decision

1. **The list (answer 1).** The `workflows:` line of `workflow_run` in `agk-route.yml` is the one part of that file that belongs
   to the project. It is a one-line YAML flow list under `  workflow_run:`, and a comment above it names it. `common.py` reads and
   writes it (`router_names`, `with_router_names`). Only that line changes, and a name that YAML would misread is double-quoted.
   `router_wanted` builds the list: first the kit's names (`governance`, `proof`), then the names the installed file already
   lists (a project's own are kept), then, sorted, every other workflow of `.github/workflows/*.yml|*.yaml` that has a job whose
   check name is in `required_checks`. A job's check name is its `name:`, or its id when it has none. A name with an expression
   is never a fixed name and is left out. The router's own file is never a source. A workflow with no top-level `name:` is
   named by its path, as GitHub names it `(verify)`. A required check that no workflow holds (a commit status, say) adds nothing.
2. **Upgrade and init (answer 1).** `upgrade.py` compares the installed router as a whole file, with its list read as the kit's.
   So an unedited file of any release, with or without names a project added, is `replace` or `unchanged`. An edit anywhere
   else is still `conflict` (`differs from every released copy`). The file written is the kit's, with the list of decision 1.
   The line ends `(router workflows added: n)` when n is not zero. An upgrade at the same version still brings the list in step
   with `required_checks`. When `required_checks` is not a list of names, nothing is added, and the plan prints one note that
   names the setting. `init.py` writes the same list. It reads `required_checks` from the target's `agk.toml` when there is
   one, else from the rendered template. An empty target therefore gets the kit's file byte for byte.
3. **The doctor (answer 2).** There is a new check, `router-wake` (warn, after `vendored-differs`). It fails when a workflow that
   holds a check of `required_checks` is not in the router's list, or when the list cannot be read. It is `ok` when no router
   is installed. Its message names the setting, never a check or workflow. Its fix is `/agk:upgrade`, or adding the name by hand
   with an ADR. Until then, a verdict comment or an edit of the title or description wakes the router. `vendored-differs`
   compares the router with its list read as the kit's. The doctor now imports these helpers from `common.py` (until now it
   imported no kit script). `init.py` may import only `common` and `reviewers` (`test_init.py`), and two copies of one parser
   would drift.
4. **The guide (answer 3).** `docs/guides/getting-started.md` names the cure until a project upgrades. The brief's answer 3 says
   "any comment". The brief's comment of 2026-10-27 corrects that: only a first line `Verdict:`, `Approve:`, `Approval:` or
   `Correction:` (the #216 filter, kept) or an edit of the title or description wakes the router. The guide says the corrected
   text (Q-285-1).
5. **Tests (answer 4).** `tests/kit/test_route_triggers.py` and the doctor case `router-unwoken` test the helpers and the doctor
   with invented workflow names, and none of them reads the installed router, which a project may extend.
   `tests/kit_dev/test_upgrade_route_triggers.py` tests upgrade and init. They are kit-only, and the brief's Touches names only
   `tests/kit/` (Q-285-2). `test_doctor.py` counts one more check. `test_route.py` allows the comment line above the list.
   Flow mode: fragment `changelog.d/router-required-checks.md`, no version bump. `kit/hashes.json` is not edited (session
   rule 14).

## Proposed spec amendments (number to be reserved, Q-285-3)

1. **SPEC-0006 rule 5.** A new row: `router-wake` | warn | a workflow of ROOT that holds a check of `required_checks` is not in
   the `workflows:` list of `workflow_run` in `.github/workflows/agk-route.yml`, or that list cannot be read (`ok` when the file
   is absent) | run `/agk:upgrade`, or add the workflow's name to the list (an ADR); until then a verdict comment or an edit of
   the title or description wakes the router.
2. **SPEC-0006 rule 8.** "compares, byte for byte" gains: "the router `.github/workflows/agk-route.yml` with its `workflow_run`
   list read as the kit's (the names are the project's, ADR-0165)".
3. **SPEC-0008 rule 7.** A new paragraph: "The router `.github/workflows/agk-route.yml` is a whole file whose `workflow_run`
   list is the project's. T is compared with that list read as N's. The file written is N with the list of ADR-0165 decision 1,
   and its line ends `(router workflows added: n)` when n is not zero."

## Consequences

- A project that adds a required check gets a router that wakes when it finishes, from its next `agk upgrade`. Until then, the
  doctor warns.
- An extra name costs one router run per finished workflow. A name that is no longer needed is kept, because a name the kit
  wrote cannot be told from one the project added.

## Residual

- 2026-10-29: Q-285-1, Q-285-2 and Q-285-3 are for the conductor (due 2026-12-31).
- A check of a reusable workflow (`caller / callee`) or of a matrix job (`name (a, b)`) is not matched to its workflow. Its name
  is added by hand.
- `adopt.py` installs the kit's router as it is. The next upgrade of an adopt install writes the list. adopt.py is not in
  the brief's Touches.
