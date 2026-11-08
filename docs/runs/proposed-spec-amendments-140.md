# Proposed spec amendments 140 (SPEC-0030; REQ-037)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0357 (brief #770), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`. The number 140 is the one brief #770
reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it needs a
person's `Approve: SPEC-0030`; no session posts it.

1. **Rule 4, the wave.** When `[flow] plan_issue` is set, a brief also has exactly one line `Wave: <n>` naming a wave of
   that plan, a milestone titled `Wave <n>`. `check_brief.py` refuses a brief without it, or with a wave the plan does not
   have, naming the rule and never a value. With no plan issue the line is optional.
2. **Rule 4, the check on GitHub.** A brief is checked when it is filed or edited, not only by the conductor's guard:
   `check_brief.py --event PAYLOAD` decides, for one saved `issues` event of an issue labelled `agk-brief`, whether it gets
   the label `agk-brief-invalid` and one comment naming each failing rule, or loses both and has its milestone set to its
   wave. `.github/workflows/agk-brief.yml` runs it (the owner's yes is quoted in brief #770). It is installed in projects, in
   `verbatim` of `kit/manifest.json` (the owner's ruling Q-770-4), which changes the classes `kit/` and `.github/`.
3. **Rule 3, the report.** `session.py plan` prints each brief refused for a brief-check rule on its own line
   `MALFORMED: #<n> <rule> (fix: <filer>)`, and the conductor's report carries those lines under `Needs a fix`.
4. **SPEC-0006 rule 5.** A new row after `brief-finished`: `brief-invalid-label` | warn | the brief-check workflow is in the
   tree and the repository has no label `agk-brief-invalid`; one more GET, only where that workflow is present.
