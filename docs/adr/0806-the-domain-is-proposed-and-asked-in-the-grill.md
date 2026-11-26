# ADR-0806: The domain is proposed from signals, confirmed with one yes, and its questions join the grill

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0074, SPEC-0073, ADR-0824, SPEC-0062, SPEC-0057, ADR-0805, ADR-0802, ADR-0801, ADR-0735, brief #1937, brief #1936, brief #1934, brief #1757, plan #661
- Requirements: REQ-081

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `agk.toml`, `kit/`

## Context

SPEC-0074 (Approved) rule 16 build (c): rule 5 (recognising the domain) and rule 6 (discovery is the grill), with rule
14's grill-budget, pilot and own-words edge cases. Before it, on the default branch at e3646ac, `front_door.py detect`
printed no `domain:` line, no command asked the person for a domain, and `grill.py questions` listed the playbook's
items only. Build (b) (brief #1936, ADR-0805) shipped `config/domain-signals.toml` and `check_domains.items`; SPEC-0073
builds (a) and (b) (ADR-0801, ADR-0802) shipped `grill.py` and `/agk:grill`.

## Decision

1. **Detect.** `front_door.detect_facts` adds a `domain` fact from `config/domain-signals.toml` of the kit's root: a
   pack's `files` matched by a file's base name in the head tree, its `dependencies` as a word in a stack manifest the
   table already reads. `detect_lines` prints, after the tests lines, `domain: <pack> (proposed) file "<path>"` or
   `dependency <name>` for one pack, `domain: mixed (<n> candidates)` with one `domain candidate:` line each for
   several, and `domain: none (proposed; no signal of a domain)` for none. A kit copy without the table prints no
   `domain:` line. The repository only (`Q-D74C-2`).
2. **The ask.** `scripts/agk/domain_ask.py` (`propose`, run by `steward_owner.py domain --propose`) adds to the
   repository's signals the pack `words` found in the recorded vision (`constitution/vision.md`) and discovery
   documents (`docs/discovery/*.md`), never chat text. One candidate: "This looks like <the pack's title>. Shall I use
   what is known about that business when I ask my questions? Yes or not yet; I recommend yes." Two or more: one choice
   of the three with most signals (`offered`, ties by name), "or none of these", recommending the first. The question
   passes `question_problem` and is saved as the one open ask (`save_asks`). A declared `[domain] packs` proposes
   nothing: `domain: declared; nothing to propose`, or `domain: declared; it differs from the signals and the declared
   one is kept (setting: domain.packs)`. No signal: `domain: none; nothing to propose`.
3. **The yes.** `domain_ask.yes` (`steward_owner.py domain --yes --said FILE --at TIME [--by LOGIN]`) follows
   `work_type_yes`: the reply time, the asking session, `[flow] owner_wait_minutes` (`age_limit`) and the data guard.
   "not yet" or "none of these" closes the ask, records a `Decision:` and writes nothing. A plain yes chooses the
   recommended pack; words that name an offered pack, by name or by its number in the offer, choose those, in the
   offer's order. In team mode `--by` must be a `spec_approvers` login (`yes_of`) and a plain yes is refused naming
   `review_mode`; the change is printed only in team and personal mode, as for the work type. In solo mode with one
   person it records the `Decision:`, makes the branch `steward/domain`, writes `[domain] packs` into `agk.toml` and a
   Proposed project ADR naming `agk.toml`, and commits nothing. A session whose `AGK_ROLE` is set to a role other than
   `steward` is refused, naming `AGK_ROLE`. `agk.toml` is written only in `yes`, after the recorded ask is found.
4. **The grill (rule 6, `Q-S0074-5`).** `grill.composed` appends the `[[discovery]]` items with a `depth` of the
   composed packs (`check_domains.items`, in `check_domains.order`) after the playbook's and the work type's, before
   `success`; an id the playbook holds keeps its first place. A regulated pack (one with a `[[regulations]]` entry
   whose `critical` is true): its critical items are asked at `light`, its other items at `standard` at the least. A
   non-regulated pack's items keep their depth. They are records of the one answers file, count toward the one budget
   and, when critical, in the `ready` critical total. Once the answers file holds as many asked items as the depth's
   budget, `questions` prints only the regulated packs' critical items still open and, when there is one, the line "A
   few more questions are needed for the rules of this business."; no second interview, no second record.
5. SPEC-0073 offers no `grill = "off"`, so the brief's `off` case has nothing to read (named in the pull request).
6. **The grill's import (Q-1937-K1).** `grill.pack_items` imports `check_domains`, which is outside ADR-0824's set
   because `check_domains` imports `domain_model` at module level. The owner ruled on #1992 (comment 7193360337,
   2026-11-26T13:26:41Z, quoted as data): "Maintainer answer: Q-1937-K1 accept check_domains in grill.py". So
   `rules.GRANTED` holds that one pair, and `rules.py imports scripts/agk/grill.py` reads it as within the ruling.
   `KIT_IMPORTS` is unchanged, and no other script or module gains a grant.
7. `domain_ask.py` joins `kit/manifest.json` (a class the reserved line did not name), and `[[testing.map]]` maps it,
   `grill.py`, `front_door.py` and `steward_owner.py` to `tests/kit/test_domain_grill.py`.

## Consequences

With no `[domain]` table or `packs = []` the grill lists exactly what it listed before (a test compares both). A
project with no pack signal sees one more `detect` line. No workflow, label, required check, `agk.mk` recipe or
`governance_map.CHECKS` entry changes.

## Residual

- 2026-11-26: the person's own word for a term (rule 14) stays a `Term:` memory entry until SPEC-0073 build (e)'s
  glossary record lands.
