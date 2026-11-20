# Proposed spec amendments 192 (SPEC-0039; REQ-046)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0660 (brief #1573), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rules 3 and 5, and the
`## Tests` section). Brief #1573 reserved ADR-0660 and named two amendment proposals without their numbers; this
session took 192, the next free one (Q-1573-3). This file proposes the lines and does not edit the spec. Builds (b) to
(d) apply them word for word, on a person's `Approve: SPEC-0039` on the pull request of build (b); no session posts it.
Amendment 193 carries the SPEC-0059 side (the ask and the record).

The sentence (brief #1573): "When the owner's yes on a brief's answers already approves a change to an approved spec,
the steward records it with its link and the merger accepts it for the amendment whose text matches those answers, so
the owner is not asked twice."

The owner's word, quoted as data (brief #1573, 2026-11-20T04:23Z): "file it".

## What is on the default branch today

Read in the code by this session on main at 90bf2753 (2026-11-20). The brief traced 0d0e6266; where a line moved, the
new line is named:

- `scripts/agk/route.py` `asks_owner` is line 502 (the brief: 495 to 516): it keeps `agk:question` while an
  `Owner needed:` by a listed verdict author has no later `Maintainer answer:` or `Approve:` by an account in
  `spec_approvers`, by login only, through an app or not.
- `scripts/agk/merge_cleared.py` line 1152 holds `owner ask (rule 5)` on `agk:question` (amendment 170, brief #1134);
  `owner_only` (line 1166) lifts only a release or a protected class for `--owner`; `unapproved` (line 959) and
  `same_text` (line 907, amendment 124) hold an `Approval: SPEC-nnnn` line until a spec approver's `Approve:` names the
  head's text.
- `scripts/agk/reviewers.py` `approval_shas` (line 297) never counts a comment posted through an app of `agent_apps`
  (`via_agent`, line 239); `agent_apps = ["claude"]` in this repository.
- Rule 5 of the spec on the default branch does not carry the `owner ask` item that amendment 170 item 2 proposed,
  though the code holds it (Q-1573-5). Item 2 below writes that item with its exception.
- `kit/templates/runtime/conductor.txt` item 8 names the `Owner needed:` form; no kit script names the line
  `Maintainer answer: amendment <n> approved`.

## Items

1. **Rule 5, a new paragraph after the hold list, the intake check.** "`reviewers.py` `intake_approval(pull, brief,
   comments, files, approvers)` returns `agrees` or `differs: <reason>`, reading only what the command already reads
   plus one GET of the brief and one page of its comments, and fails closed: an unreadable brief or comment page is
   `differs`. It is `agrees` only when all of these hold: the pull request's first `Brief: #n` line names the brief
   that holds the record; the record (SPEC-0059 rule 5) is the newest comment of the brief whose first line has the
   form `Maintainer answer: Q-<n>-intake approved at intake: answers <list>; text sha256 <64 hex>`, its second line is
   an `Owner said` line, and its author is an account in `spec_approvers`, posted from that account's own login in team
   mode (not through an app of `agent_apps`); the brief's current `Answers:` section hashes to the recorded value; the
   pull request adds exactly one `docs/runs/proposed-spec-amendments-*.md` file, of a number the brief reserves, and its
   `Approved at intake:` line equals the record; every numbered item of that file ends `(answer <n>)` or
   `(answers <n>[, <n>...])` naming only answers of the record's list, and every answer of the list is named by an
   item; the pull request body's `Questions:` list holds no question answered by a reading; and no `Correction:` and no
   `Maintainer answer: Q-<n>-intake withdrawn` by an account in `spec_approvers` is on the brief after the record. Each
   `differs` reason names the condition, the item and the answer, never a value of the record." (answer 4)
2. **Rule 5, the owner ask item.** Added after `hold label`: "- one labelled `agk:question`, an open owner ask, whatever
   the ask is (`owner ask`), except that the ask of the amendment's approval is not held when the intake check above
   is `agrees` on the head; any other ask on the same pull request still holds;" (answers 4 and 5)
3. **Rule 3, the verdict's line, one sentence at the end.** "On `agrees` (rule 5) the conductor posts no `Owner needed:`
   for the amendment's approval, and its clearing verdict carries one line `Intake approval: agrees, #<brief> comment
   <id>`, written only after its own review finds that each numbered item says what its cited answer says; on `differs`,
   or when its review finds an item that says more or less than its answer, it posts `Owner needed:` naming only what
   differs (the item and its answer, the edited answer, or the open reading). The command re-runs the check and never
   trusts the verdict's line alone; the line clears nothing on its own." (answers 4 and 5)
4. **Rule 5, what the record never lifts, one sentence after item 2's.** "The intake check never lifts `release`,
   `spec approval` (the `Approve: SPEC-<n>` of the build that applies the amendment stays the approver's own line),
   `protected class <class>`, `hold label`, `draft`, `depends-on`, `conflict`, the red default branch or `paused`."
   (answer 6)
5. **The amendment's line (a sentence added at the end of rule 5).** "An amendment file written for a brief with an
   intake record carries one line `Approved at intake: #<brief> comment <id>; answers <list>; sha256 <hex>`, the
   record's values copied by the `spec` skill; `check_specs.py` checks the line's form only (a brief number, a comment
   id, a comma-separated list of answer numbers and 64 lower-case hex characters), with no network." (answer 3)
6. **The `## Tests` section, one line added.** "- Rule 5, the intake check, on saved responses with example.com logins:
   a matching record and amendment is `agrees` and the merger merges with no `Owner needed:` answered; a brief edited
   after the yes is `differs` naming the answer; an item citing no answer and an answer cited by no item are
   `differs`; a reading in `Questions:` is `differs` for that question only; a record by an account outside
   `spec_approvers`, a malformed second line, a record through an agent app in team mode, a withdrawn record and a
   `Correction:` count as no record; two amendment files and a second pull request on the same brief are `differs`; an
   unreadable brief or comment page is `differs`; `release`, `spec approval` and `protected class` still hold on
   `agrees`; `check_specs.py` refuses a malformed `Approved at intake:` line; REQ-046 AC1." (answer 9)
7. **Unchanged:** rules 1, 2, 4 and 6 to 12, the Proof and the Residual. `route.py` keeps closing an `Owner needed:` on
   a spec approver's `Maintainer answer:` as today; the record is posted on the brief, not on the pull request, so it
   closes no ask of the pull request.

## What each setting does with it

| Setting | Impact |
| --- | --- |
| `review_mode` | `solo`: the steward's relay counts (SPEC-0062 rule 13, Q-1573-1); `team`: only the approver's own post (SPEC-0062 rule 15) |
| `pr_mode` | `strict` and `flow` alike: one record per brief for its one amendment pull request; a second open pull request naming the brief and adding an amendment is `differs` |
| `execution` | `hosted`, `hybrid`, `pool`: the router relabels on the record as on any `Maintainer answer:` and the merger job runs the check; `local`: the conductor's pass and the supervisor's sweep do the same, with no workflow run |
| `[flow] auto_merge` | `true`: the guarded merge proceeds on `agrees`; `false`: nothing merges by itself, the record only removes the owner's wait |
| `[flow] owner_wait_minutes` | unchanged: a `differs` ask parks as today |
| `[kit] layout = "plugin"` | the same check, read from the plugin; the record and the amendment line stay project records |
| `[steward] auto_file` | unchanged: the record is not a filing |
| `forge = "files"` | personal mode has no conductor or merger: the record is printed only (amendment 193 item 4) |

No workflow, ruleset, required check, secret or `agent_apps` changes. A button merge from the phone bypasses the merger
as today (brief #1539's area); nothing here changes it. Customer projects run the same kit behaviour; the record quotes
only the owner's own words, scanned by the data guard.

## The builds (this spec's side)

Each from the default branch, filed later by the `brief` skill, tests first, about 300 changed lines or fewer, invented
data only (example.com), no network and no model in checks, no workflow change. No existing assertion is removed or
loosened (principle 11).

- (b) `reviewers.py` `intake_approval` and its tests (item 6's cases); item 1 applied to the spec on the owner's
  `Approve: SPEC-0039`.
- (c) the conductor and the merger read it: the verdict line and no `Owner needed:` on `agrees`
  (`kit/templates/runtime/conductor.txt` item 8), `merge_cleared.py`'s re-check at the `owner ask (rule 5)` hold, and
  `--status` naming `intake approval: differs (<condition>)`; items 2 to 4 applied. `Depends-on` (b).
- (d) the `spec` skill's line and item tags, `check_specs.py`'s form check, and the guides
  (`docs/guides/product-owner.md` and `docs/guides/reference.md`); item 5 applied. `Depends-on` (b).

Build (a) is SPEC-0059's (amendment 193).

## Questions (brief #1573), each with the reading this proposal takes

- Q-1573-2 (the brief's Q-2): does a record also stand for the later `Approve: SPEC-<n>` of the build that applies the
  amendment word for word? Reading: no, not in this brief (principle 6, SPEC-0039 rule 5); item 4 keeps `spec approval`
  held, and ADR-0660's Residual measures before any later proposal.
- Q-1573-5: amendment 170 item 2 (the `owner ask` item of rule 5) is held by the code but not written in the spec on
  the default branch. Reading: item 2 here writes that item with its exception, so build (c) applies one line, not two;
  a reviewer who finds amendment 170 applied elsewhere drops item 2's first half.
- Q-1573-6: the record lives on the brief, so the `agk:question` label of the pull request's own `Owner needed:` is not
  closed by it. Reading: on `agrees` no such ask is posted (item 3), and an ask already posted before the check is
  closed by the owner's answer as today; the merger's re-check lifts only the hold for the amendment's approval
  (item 2). Build (c) checks that the label on a pull request whose only open ask is the amendment's approval is not
  set again by the router on `agrees` `(verify: route.py base_state at build (c))`.
