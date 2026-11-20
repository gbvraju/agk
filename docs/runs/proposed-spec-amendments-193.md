# Proposed spec amendments 193 (SPEC-0059; REQ-066)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0660 (brief #1573), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0059-a-steward-answers-what-the-evidence-settles-and-asks-the-owner-only-the-rest.md` (rules 3 and 5, and
the `## Tests` and `## Contexts` sections). Brief #1573 reserved ADR-0660 and named two amendment proposals without
their numbers; this session took 193, the next free one after 192 (Q-1573-3). This file proposes the lines and does not
edit the spec. Build (a) applies them word for word, on a person's `Approve: SPEC-0059` on its pull request; no session
posts it. Amendment 192 carries the SPEC-0039 side (the check and the merger).

The sentence (brief #1573): "When the owner's yes on a brief's answers already approves a change to an approved spec,
the steward records it with its link and the merger accepts it for the amendment whose text matches those answers, so
the owner is not asked twice."

The owner's word, quoted as data (brief #1573, 2026-11-20T04:23Z): "file it". By SPEC-0062 rule 14 that is a word to
file, not a yes to the answers; this proposal is approved by the owner as any amendment is today.

## What is on the default branch today

Read in the code by this session on main at 90bf2753 (2026-11-20):

- `scripts/agk/steward_owner.py` `relay` (line 158) posts `relay_body` (line 101): `Maintainer answer: <Q> <answer>`,
  `Owner said (<UTC time>): "<words>"`, `Who: ProductOwner`; `relay_problem` (line 105) checks the three lines, and
  `ANSWER_FIRST` (line 84) is `Maintainer answer: Q-\d+-\w+ \S.*`, so a `Q-1573-intake` id already passes. `relay`
  refuses under `AGK_STEWARD_START=conductor` and, in personal mode, prints instead of posting.
- `.claude/hooks/steward_guard.py` `body_problem` (line 181) denies a first line starting `Approve:`, `Confirmed:`,
  `Verdict:`, `Final:` or `Correction:`, and a `Maintainer answer:` whose second line is not `OWNER_SAID` (line 40).
- `.claude/agents/steward.md` line 34 names `steward_owner.py ask` and `relay`; nothing asks the owner when a brief is
  filed.
- SPEC-0062 rules 13 to 15: a plain yes is one explicit sentence in reply to the one question just asked, and holds in
  solo mode only.

## Items

1. **Rule 5, the ask at intake, one paragraph added at the end.** "When the steward files, or drafts for the owner, a
   brief whose `Touches:` names an Approved spec or whose `Adds:` names a `proposed-spec-amendments` file, it asks the
   owner one plain question after the brief text is final, showing the decisions in three lines or fewer, for example
   'These 6 decisions change the approved rules for which jobs run. Approve them now, so you are not asked again when
   the write-up matches them? Yes (recommended) · ask me again at the write-up.' Only an explicit yes by SPEC-0062 rule
   14 counts; anything else, a word to file or a question included, records nothing, and the intake runs as before."
   (answer 1)
2. **Rule 5, the record, one paragraph added after item 1's.** "On that yes the steward posts one comment on the brief
   with `python3 scripts/agk/steward_owner.py relay --intake`, of exactly three lines:
   `Maintainer answer: Q-<brief>-intake approved at intake: answers <n>[, <n>...]; text sha256 <64 hex>`,
   `Owner said (<UTC time>): "<the owner's words, verbatim>"` and `Who: ProductOwner`. The hash is the SHA-256 of the
   brief body's `Answers:` section, from its heading line to the line before the next top-level heading or line that
   ends in a colon, with LF line ends and trailing spaces removed, and `--intake` computes it from the brief as read in
   that pass. The data guard of `steward.py record` scans the owner's words before posting and refuses a match naming
   the class. The steward also records one `Decision:` memory note (rule 8) with the comment's link. The owner may post
   the same three lines from their own account, from the browser or the phone app, and that record counts the same. In
   solo mode the steward's relay counts, as rule 5's relayed answer counts (SPEC-0062 rule 13); in team mode only a
   record posted by an account in `spec_approvers` from that person's own account counts, never one through an app of
   `agent_apps` (SPEC-0062 rule 15). The owner withdraws a record with one comment on the brief whose first line is
   `Maintainer answer: Q-<brief>-intake withdrawn`; a withdrawn or broken record is noted as a `Gap:` (rule 8). The
   record is never an `Approve:` line, a verdict or a confirmation, and never stands for a spec approval: SPEC-0039 rule
   5 holds the use the merger makes of it." (answers 2, 5 and 6)
3. **Rule 3, authority by stage, one sentence at the end of the `Planning` bullet.** "An intake record (rule 5) spares
   only the second ask of a decision the owner already made; it answers no requirement question, which still goes to
   the owner." (answer 6)
4. **Rule 14, by mode, one sentence at the end.** "Personal mode: the intake record of rule 5 is printed for the
   developer, its `Decision:` is written to the sidecar memory, and nothing is posted." (answer 8)
5. **The `## Tests` section, one line added.** "- Rule 5, the intake record: `relay --intake` posts the three lines with
   the hash of a fixture brief's `Answers:` section; a `file it` or a question in place of a yes records nothing; a
   malformed `Owner said` line is refused by the guard; personal mode prints and posts nothing; a matched data-guard
   class is refused by its name; REQ-066 AC1." (answer 9)
6. **The `## Contexts` section, the `personal` entry rewritten**, one line with no top-level semicolon, as
   `check_specs.py` joins the section's lines with `; ` and cuts them there:

   ```
   - personal: memory in a sidecar file, owner questions, answers, intake records and the daily list printed, nothing in the product repository.
   ```

   (answer 8)
7. **Unchanged:** rules 1, 2, 4 and 6 to 20, the Proof, the Residual and the `kit`, `github`, `local` and `stacks`
   contexts. The `github` entry stays true: the router relabels on the record as on any `Maintainer answer:`, with no
   workflow change.

## The builds (this spec's side)

Each from the default branch, filed later by the `brief` skill, tests first, about 300 changed lines or fewer, invented
data only (example.com), a `[[testing.map]]` entry for each new script, no workflow change. No existing assertion is
removed or loosened (principle 11).

- (a) `steward_owner.py relay --intake --brief <n> --answers <list>` (the hash computed from the brief as read; the
  `Q-<brief>-intake` id formed by the flag), the guard's allowed form (`steward_guard.py` accepts the record's first
  line, still with the `Owner said` second line), the role file's line in `.claude/agents/steward.md` and the
  `brief`-skill step that asks the question of item 1; items 1 to 6 applied to the spec word for word on the owner's
  `Approve: SPEC-0059`. The ADR of that build names `.claude/`, `scripts/agk/`, `skills/` and `tests/kit/`.

Builds (b) to (d) are SPEC-0039's (amendment 192).

## Questions (brief #1573), each with the reading this proposal takes

- Q-1573-1 (the brief's Q-1): does the steward's relay of the owner's chat yes count as the record in solo mode?
  Reading: yes in solo mode only, as a relayed `Maintainer answer:` counts today; in team mode only the approver's own
  post (the brief's recommendation).
- Q-1573-3: the brief names two amendment proposals but reserves no amendment number. Reading: the next free numbers on
  the default branch and in the open briefs' `Reserved:` lines, 192 (SPEC-0039) and 193 (SPEC-0059); `check_numbers.py`
  finds no clash. A reviewer may renumber both.
- Q-1573-4: where the `Answers:` section ends, for the hash. Reading: at the next line of the body that is a top-level
  heading or a line ending in a colon at column 0 (in #1573: `Questions (only what the evidence does not settle):`), so
  the questions and the plan lines are not hashed and may be edited without breaking the record.
