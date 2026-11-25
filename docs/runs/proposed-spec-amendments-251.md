# Proposed spec amendments 251 (SPEC-0059; REQ-066)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0813 (brief #1957), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0059-a-steward-answers-what-the-evidence-settles-and-asks-the-owner-only-the-rest.md` (rules 4, 11, 12 and
13). Brief #1957 reserved amendment 251. This file proposes the lines and does not edit the spec. They are applied word
for word, on a person's `Approve: SPEC-0059`; no session posts it.

## Why

Of the 61 items of amendments 212 to 247, 31 only made the kit do what its Approved spec already said, and each waited
for the owner's `Maintainer answer: amendment <n> approved` (#1945 waited about 4 hours for amendment 245).

## Items

1. **SPEC-0059 rule 4, the settled form.** Append: "With `[steward] settle_amendments = true` (rule 12), an amendment
   whose every item is `Class: correction` or `Class: implementation` (ADR-0813 answer 1) is answered, once rule 13's
   re-check agrees, by one comment whose first line is `Answer: amendment <n> settled (evidence: <file and line or
   run>; class: <class>; rule: <spec and rule>)`, with a second line `Text: <digest>` of the amendment as it reads and
   ending `Who: AGK steward`, printed by
   `scripts/agk/check_amendments.py settle`; any other amendment, a disagreement, an intake's amendment and one that
   changes a principle, `constitution/` or `spec_approvers` go to the owner (amendment 251)."
   Class: behaviour
2. **SPEC-0059 rule 11, the guard's allow.** Append to the list: "a comment whose first line starts `Answer: amendment
   <n> settled` unless it is in rule 4's settled form with `Who: AGK steward` and the digest of a settleable amendment
   as the checkout reads it, and `[steward] settle_amendments` is on (amendment 251)."
   Class: behaviour
3. **SPEC-0059 rule 12, the setting.** Append: "`settle_amendments`, `true` or `false` (default `false`): rule 4's
   settled form; `true` is read as `false`, refused alone naming principle 6, until principle 6 holds ADR-0813's
   clause, and is read as off
   while `config/reviewers.yaml` lists no `spec_approvers` login (amendment 251)."
   Class: behaviour
4. **SPEC-0059 rule 13, the override share.** Append to the override share: "An owner `Maintainer answer:` or
   `Correction:` naming an amendment the steward settled is an override of that amendment's class; two in one class
   within seven days stop the steward settling that class until the owner says otherwise (amendment 251)."
   Class: behaviour

No other rule changes.
