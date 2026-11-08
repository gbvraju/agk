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
   wave. The workflow that runs it needs the owner's yes (`Q-770-1`).
3. **Rule 3, the report.** `session.py plan` prints each brief refused for a brief-check rule on its own line
   `MALFORMED: #<n> <rule> (fix: <filer>)`, and the conductor's report carries those lines under `Needs a fix`.
