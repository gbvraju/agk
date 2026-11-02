# Design inventory

The screens and states of the product, written before anything is drawn (SPEC-0037 rule 3). `design.py inventory` wrote
this skeleton from `docs/requirements.md` and the `Requirements:` lines of `docs/specs/`; fill its slots from the
requirements and the specs, and from nothing else. A slot is a `- <field>:` line with nothing after the colon, and
`check_design.py` fails while any slot is empty, naming the rule and the screen.

Each requirement is a section of the Requirements part that lists the specs that name it and its screens, or
`no screen: <reason>` when it has none:

    ### REQ-<n> — <title>

    - Specs: <spec ids, or none>
    - Screens: <screen>, <screen>

Each screen is a `### <screen>` section of the Screens part, its id a lower-case slug, with these lines:

    - Flow: <the flow the screen belongs to>
    - Pattern: <one pattern of the kit's design standard>
    - Links to: <screen>, <screen>, or none
    - State default: yes
    - State <state>: yes

with one `- State <state>:` line for `default`, for each of the six required states (`empty`, `loading`, `error`,
`no-permission`, `long-content`, `success`) and for any other state a spec names. A required state that does not apply to
the screen reads `n/a: <reason>`; it is never left out. The person agrees the inventory with the line
`Approve: inventory <full head ID>` on its pull request; a session never posts that line.

## Requirements

{{requirements}}
## Screens
