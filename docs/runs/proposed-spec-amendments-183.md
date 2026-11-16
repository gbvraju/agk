# Proposed spec amendments 183 (SPEC-0045; REQ-050, REQ-052)

Date: 2026-11-15 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It was
written for ADR-0571 (brief #1359), which stays `Proposed` until the maintainers decide. The path is
`docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md`. The maintainers chose to change the rule in the
same pull request (`Maintainer answer: Q-1359-3 (a) change the rule in this pull request; first reviews and risky
changes stay on the strongest model`, comment 6901739865 on #1364), so the spec lines below are edited there, for a
reviewer's approval of that head.

The sentence (brief #1359): "The conductor runs each pass on the model the pass needs: routine passes on the mid tier,
design, protected paths, first reviews of large changes and any disagreement on the strongest, with an automatic step
up when a mid pass is unsure."

## Items

1. **Rule 2:** "`[models]` accepts `routes` (rule 3) and `prices` (rule 8)" becomes "`[models]` accepts `routes`
   (rule 3), `prices` (rule 8) and `conductor` (rule 6, amendment 183)".
2. **Rule 6 gains, after its first sentence:** "One exception (amendment 183, ADR-0571): a job that `conductor.py
   watchdog --pass` starts runs on `mid` at `medium` when no pull request of the queue it is handed is a first
   review, changes a protected path class, adds or changes a spec or ADR, carries a `Question:`, a `Correction:` or a
   disagreement between verdicts, or is an intake, and no brief of it holds a question; otherwise on `strongest` at
   `high`. A mid job posts no verdict on a pull request that meets one of those or whose verdict it is unsure of, and
   ends with `escalate: #<n> <reason>`, after which the watchdog runs one strongest job at once.
   `[models] conductor = "strongest"` (no other value) pins every job to `strongest`."
3. **Unchanged:** every reviewer and review agent other than the conductor; the conductor started by hand or by
   `watchdog` without `--pass`; `REVIEW_FLOOR`; rule 6's sentences on what a first review and a re-review read.
4. **Tests.** `tests/kit/test_conductor_tier.py` (brief #1359 answer 5). `tests/kit/test_launch_kinds.py`
   (`test_every_review_agent_runs_on_strongest_at_high`, REQ-052 AC4) is unchanged and still holds: the role file
   still says "the `strongest` tier at `high` effort" and names the exception.
