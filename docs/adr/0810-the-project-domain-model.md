# ADR-0810: The project domain model under docs/domain/, its BR-<n> rules, the data classification, the harvest and the one glossary

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0074, SPEC-0073, SPEC-0059, SPEC-0042, ADR-0794, ADR-0804, ADR-0812, ADR-0562, ADR-0677, brief #1954, brief #1935, brief #1951, plan #661
- Requirements: REQ-081

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0074 (Approved) rule 16 build (d) is the project domain model of rule 7, with rule 9's confirmations. Before it, on
the default branch at 13e11fc, no `docs/domain/` form existed, no script read a `BR-<n>` line, `check_domains.py`
(build (a), ADR-0804) checked packs only, the glossary step (SPEC-0073 build (e), ADR-0812) knew no pack and the
steward's harvest (ADR-0562) read no domain file. Rule 7 gives the rule line's form; it gives none for the entities,
the data classification or the regulations (`Q-D74D-2`).

## Decision

1. One module, `scripts/agk/domain_model.py` (standard library, `common.py`, `guard.py` and `config.py`; no network, no
   model), holds the four forms of `docs/domain/` and their readers, so `check_domains.py`, the harvest and the next
   reader (#1948) import one pattern of each:
   - `entities.md`: one `## <Entity>` section per entity, its meaning in one line, then lines
     `- relates to <Entity>: <one|many> to <one|many>, <plain reason>`.
   - `rules-<area>.md`, `<area>` a lower-case slug: lines
     `- BR-<n>: <rule>; source: <customer material|interview|code>, <where>; owner: <who>; <confirmed|inferred>`, read
     from the right so the rule may hold a `;`; `<n>` a whole number from 1 with no leading zero; at most 200 rules
     per file; `BR-<n>` unique across the folder.
   - `data.md`: lines `- <data item>: <personal|health|payment|confidential|public>`, each item once.
   - `regulations.md`: lines `- <pack id>.<regulation id>: <in scope|out of scope>, <one plain reason>`, each naming a
     regulation of a pack in `[domain] packs`.
2. `domain_model.findings(root)`, called by `check_domains.findings` and so run in the `playbooks` governance step,
   fails, only where `docs/domain/` exists, each breach of those forms and each line `guard.scan_text` flags with
   `[guard] patterns`, as `rule 7: docs/domain/<file>: <what> (id: <BR-n|item|entity|file|line n>)`, never a rule's
   text or a value. A refused `[domain]` table is not read here (doctor and the pack reader name it).
3. The writer, `domain_model.py init --area A | rule | classify | entity | regulation | confirm`, writes only under
   `docs/domain/`, never commits, refuses to overwrite a model, a 201st rule in a file ("split by area"), a value
   outside a form and a value the data guard flags (naming the class), and numbers a new rule with the next free
   `BR-<n>` across the folder. `init` writes the four files from `kit/templates/domain-*.md`, read from the kit root
   as `gates/glossary.py` reads its template. `confirm --id BR-<n>` changes only an `inferred` status word to
   `confirmed`, after the steward has recorded the person's yes as a `Decision:` (rule 9); the check does not read the
   memory (`Q-D74D-1`). The builder prompt is unchanged: the steward or the architect runs it in planning.
4. The steward's harvest (`steward_onboard.from_domain`) reads `docs/domain/`: each `confirmed` rule and each
   classified data item is a `harvested` `Decision:` citing its file and id; each `inferred` rule is one `Owner
   question:`, at most 20, then one line with the count; an unreadable file is a `Gap:`. `--again` adds only new lines.
5. The glossary step (`scripts/agk/gates/glossary.py`, `Q-D74D-3`) reads `[domain] packs`: with packs, the glossary
   holds one line `Packs: <id>, <id>` naming them in order; with none, no such line; a refused table fails naming
   `domain`. A pack's synonyms are included by reference, never as rows, so the cap counts rows only, and a row that
   is also a pack term is one term.
6. `domain_model.py` joins `kit/manifest.json` `verbatim` and the reference guide; the templates live in
   `kit/templates/` beside `glossary.md`; `kit/hashes.json` waits for the release (session rule 14). One
   `[[testing.map]]` entry in `agk.toml` maps the module to its tests.

## Consequences

Every business rule of a project has a number, a source, an owner and a status, and every data item a class, before the
data model or a build relies on them. The kit's own repository has no `docs/domain/`, so governance on the kit prints
nothing new. No workflow, label, required check, `agk.mk` recipe or `governance_map.CHECKS` changes.

## Residual

The `Rules:` line of `check_brief.py` is build (f); the domain expert's confirmation is build (h). The data model
record's three classes (ADR-0677) are mapped onto rule 7's five by #1948 (`Q-DM-4`), not here.
