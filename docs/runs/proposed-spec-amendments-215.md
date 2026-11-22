# Proposed spec amendments 215 (SPEC-0059; REQ-066)

Date: 2026-11-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0714 (brief #1715), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0059-a-steward-answers-what-the-evidence-settles-and-asks-the-owner-only-the-rest.md` (rules 11 and 12).
This file proposed the lines; they are applied word for word on a person's
`Approve: SPEC-0059` (Q-1715-3); no session posts it. The number 215 is the next free one after the open #1721's 214;
brief #1715 reserved none (Q-1715-4).

The sentence (brief #1715): "The steward fixes a brief's mechanical lines itself and files a draft the owner said yes
to as a buildable brief, so no brief waits hours on a person to copy text the steward already checked."

## Why

Rule 6 lets the steward file a project brief once `check_brief.py` passes; rule 11's last bullet and ADR-0594 decision 4
allow it no label but `agk:parked` and `agk-steward`, so a steward filing is never offered by the plan
(`session_plan.plan_briefs` reads `agk-brief` only), and no rule lets it apply its own corrected body.

## Rule 11, its last bullet

Today:

    - any label write other than `agk:parked` on a pull request and `agk-steward` on its memory issue.

Proposed:

    - any label write other than `agk:parked` on a pull request and `agk-steward` on its memory issue; `agk-brief` is written only by `steward_owner.py file-brief`, after rule 6's checks pass (brief #1715, ADR-0714);
    - an issue body edit, unless `[steward] fix_briefs = true` (rule 12).

## Rule 12, its last two sentences

Today:

    An unknown key, or a value that is neither `false` nor an integer from 0 to 3, is refused naming the setting, never the value. With no table the default holds.

Proposed:

    `fix_briefs`, `true` or `false` (default `false`, `Q-1715-1`): with `true`, in solo mode with one person listed, `steward_owner.py fix-brief` replaces an open, untaken brief's body when only its `Adds:`, `Touches:`, `Reserved:`, `Depends-on:` or `Evidence` lines change and rule 6's checks pass, posting the old body first as one `Body fixed:` comment; any other change, and every other mode, prints `Proposed body:` for the owner (brief #1715, ADR-0714). An unknown key, or a value that is neither `false` nor an integer from 0 to 3 (for `fix_briefs`, neither `true` nor `false`), is refused naming the setting, never the value. With no table the default holds.

## Applied

Approved by the owner on #1723 (comment 7076972645, `Maintainer answer: amendment 215 approved`, `Owner said
(2026-11-22T09:09Z): "Yes"`); the two proposed blocks above are applied to the spec word for word in the same pull
request.
