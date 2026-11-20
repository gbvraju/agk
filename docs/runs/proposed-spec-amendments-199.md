# Proposed spec amendments 199 (SPEC-0029; REQ-036, REQ-069)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0671 (brief #1591), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0029-a-product-owner-starts-from-a-brief-idea-the-vision-the-stac.md` (rule 5, the `## Tests` section and a
new `## Contexts` section). Brief #1591 reserved amendment 199. This file proposes the lines and does not edit the spec.
They are applied word for word, on a person's `Approve: SPEC-0029`; no session posts it.

The sentence (brief #1591): "The stack is offered to a business person as two or three options, each with its cost,
build speed, security and uptime in plain words, one recommended for the product's shape and needs, and accepted with
one plain yes."

## Why

SPEC-0029 rule 5 asks for options "with their trade-offs" and nothing more, so a record written for an architect passes
`stack-check`; SPEC-0062 rule 6 asks the steward for each choice in plain words with its effect on cost, speed and
security and its recommendation. Amendment 142 (`check_specs.py` `contexts_failures`) refuses any change to an Approved
spec without a `## Contexts` section, and SPEC-0029 has none, so item 3 supplies one.

## Items

1. **Rule 5, two sentences added after its second sentence.** "In a Proposed record, each option's trade-offs give its
   `Cost:`, `Build speed:`, `Security:` and `Uptime:` as plain phrases, and exactly one option is marked
   `(recommended)` with a `Why:` that names a need from the charter or the discovery document; the check names the rule
   and the option letter, never a value, and an Accepted record is checked as before. The kit proposes one default per
   shape (`config/stack-defaults.toml`, the maintainers' rows), which the skeleton writes as Option A unless the
   repository already holds another stack, which is then kept, and an option whose stack has no standards pack yet says
   so in plain words." (answers 1 to 3)
2. **Rule 5, one sentence added at its end.** "The accepting change is made by `engines.py stack-accept` in the two
   ordinary commits that the stack skill names, after one plain yes of the person who owns the stack (in team mode a
   spec approver), never a typed line." (answer 4)
3. **A `## Contexts` section, new, after `## Open questions`**, each entry one line with no top-level semicolon, as
   `check_specs.py` joins the section's lines with `; ` and cuts them there:

   ```
   ## Contexts

   - kit: the stack check's four effects and recommendation, the per-shape defaults, the accept command and the steward's plain presentation.
   - github: no workflow change.
   - local: the same check.
   - personal: the same check, and the yes is printed for the developer to post.
   - stacks: each default names one stack of the signal table, and no stack's test or build step changes.
   ```

   (answers 5 and 6)
4. **The `## Tests` section, one line added after the rule 5 line.** "- Rule 5, the choice: a Proposed record missing an
   effect, with no recommendation or with two is refused naming the option letter; two skeletons for one shape recommend
   the same option; the accept command writes exactly its two commits; an Accepted record written before still passes;
   REQ-036 AC4 and REQ-069 AC4." (answer 7)
5. **Unchanged:** rules 1 to 4 and 6 to 10, the Proof, the Residual and the Open questions. Rule 8 ("No default engine")
   stays true: a default row is data that the kit's own template writes, not an engine, and the maintainers accept it
   in ADR-0671.

## Questions (brief #1591), each with the reading this proposal takes

- Q-1591-1: who makes the accepting change after the yes? Reading: a builder, from a mechanical brief the steward drafts,
  cleared like any build (the brief's recommendation).
- Q-1591-2: the default rows are a kit decision. Reading: ADR-0671 proposes three rows (`default`, `web-app`,
  `data-pipeline`), each on `python-pyproject`, and the maintainers accept or change them there.
- Q-1591-3: do Accepted records need the four effects? Reading: no; the new sentences hold for a Proposed record only.
