# Proposed spec amendments 259 (SPEC-0072; REQ-083)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0834 (brief #2017, SPEC-0076 rule 14), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 4). Amendment 256 is the newest on main and open briefs name 254, 255 and 257 (#2015), so this intake
proposes 258 to 260 (`Q-S0076-8`). This file proposes the lines and does not edit the spec. SPEC-0076's build (e), after (d),
applies it word for word, on the owner's `Maintainer answer: amendment 259 approved`; no session posts it.

The sentence (brief #2017), quoted as data: "Intake for the parts list: after the stack is accepted and before the foundation, each library a product uses is chosen per need from a cited catalogue, recorded with its reason, alternatives and health, explained in plain words, and kept in step with every build file and lock."

## Items

1. **SPEC-0072 rule 4, the build files written from the parts record.** After "(Python: `pyproject.toml`, its
   dependencies added with exact `==` pins only; `node`: `package.json` with exact versions)" insert: "; where the
   project holds a confirmed parts record (`docs/parts.md`, SPEC-0076 rule 7), `stack-files` writes the build file's
   dependencies from the record's rows, each runtime part as a dependency and each dev part as a dev dependency at its
   exact recorded version, and writes no dependency the record does not name (amendment 259)".
   Class: behaviour

No other rule changes.

2026-11-28 (from `date -u`), brief #2072: item 1 (to rule 4) applied to `docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` word for word, on the maintainer's answer on #2018 (comment 7227144062).
