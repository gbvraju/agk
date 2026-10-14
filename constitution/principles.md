# Principles

The twelve rules. Briefs cite them by number.

1. A protected change requires an ADR in the same PR.
2. Agents never merge, and never bypass checks.
3. One PR per item, branched from the default branch; no stacks.
4. Build-state is only appended, and only by docs commits.
5. Generated files are never committed.
6. Approved specs are owned by a reviewer group; agents propose patches.
7. Questions are recorded, never guessed; unconfirmed facts are marked (verify).
8. Refusals name the setting or path class, never the value.
9. No secrets in the repository or in an agent session; scanners' ignore lists never grow.
10. Dates come from `date -u`; PR bodies state what they advance; tests carry REQ markers.
11. A check is never weakened to go green; it is changed by ADR.
12. Unattended work stops on ambiguity and reports per PR.
