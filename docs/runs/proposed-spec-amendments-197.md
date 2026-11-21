# Proposed spec amendments 197 (SPEC-0066; REQ-069)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0664 (brief #1584), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0066-plain-claude-opens-the-steward-and-every-session-the-kit-starts-names-its-role.md` (rules 4 and 8 and the
`## Tests` section). The number is the brief's `Reserved:` one. This file proposes the lines and does not edit the spec;
they are applied word for word on a person's `Approve: SPEC-0066`, which no session posts. Amendment 196 carries setup's
side (SPEC-0065 rule 8).

## What is on the default branch today

Read on main at b633566 (2026-11-21): rule 4 says that outside an AGK project the steward reads and offers only, and that
"the one exception is rule 8's greeting mark". Rule 8's choice A "starts the product path (the vision, in plain words)",
which needs a repository, so the person's first answers had nowhere to go.

## Items

1. **Rule 4, its last sentence replaced by:** "The exceptions are rule 8's greeting mark and, on the person's yes to one
   plain question, rule 8's day-zero notes: both are written to the person's own Claude folder and never to the folder
   that was opened (`Q-S0066-8`, Q-1584-1)." (brief answer 2)
2. **Rule 8, one bullet added after the first.** "- **Day zero, choice A in a folder that is not a project yet:** the
   steward asks the discovery topics the idea leaves open, at most three per round, and plays back what it understood
   (SPEC-0062 rule 4). On a yes to 'Shall I keep notes of what you tell me, so nothing is lost before your project
   exists?', each answer is kept as given with its UTC time in one file of the person's Claude folder, named by the
   greeting mark's folder hash (`day_zero.py keep`). It offers to connect the folder to GitHub with SPEC-0065 rule 8's
   commands (amendment 196), which the person runs. After the install, `day_zero.py write` turns the answers into
   `docs/sources/day-zero.md` (`Kind: other`, SPEC-0043 rule 1, the words quoted, never rewritten) and the `vision`
   skill's answers file, in one pull request, and removes the kept file. Personal mode gets no offer; the answers go to
   the sidecar. An adopted repository gets no day-zero file." (brief answers 1 to 4 and 6, Q-1584-2)
3. **The `## Tests` section, one line added.** "- Rule 8, day zero: nothing is kept before a yes, and only in the person's
   Claude folder; the source `write` makes passes `check_plan.py`, and the kept file is removed; REQ-069 AC1."
4. **Unchanged:** rules 1 to 3, 5 to 7 and 9 onward, the Proof, the Residual and the Contexts.

## Questions

- Q-1584-1 (where the notes live): the recommendation taken, the person's Claude folder on a yes.
- Q-1584-2 (`Kind:`): the recommendation taken, the existing `other`, titled `Day-zero conversation`.
