# ADR-0315: The rag-app playbook as checked data (REQ-045, brief 662)

- Status: Proposed
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0251, ADR-0313, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (d) ships the second playbook, `rag-app`, as checked data with the phases,
lanes, testing profile, milestone shape and gates that rules 10 and 11 give it, every speed claim
`expected`, since no run has measured it. ADR-0251 sets the direction and lists the classes the
builds of SPEC-0038 change; ADR-0259 added the format module `scripts/agk/playbook_format.py` and
the governance step `check_playbooks.py` that this file must pass; ADR-0313 shipped the web-app
playbook of build (c), whose shape and tests this build follows. Brief #662 gives the build; this
ADR number was reserved for it by the conductor.

## Decision

1. `config/playbooks/rag-app.toml` (new, installed, in `verbatim` of `kit/manifest.json`) holds
   the content of SPEC-0038 rule 11 for rag-app: phases `corpus` (with the privacy review),
   `evaluation-set`, `retrieval`, `answers` and `joins`, each after the one before it; brief kinds
   in that order, with the evaluation set a dependence of every retrieval and answer brief; one
   lane for the retrieval kind and one for the answer kind; `[testing]` profile `balanced`,
   `always_full` for the evaluation set folder and a per-module `map` suggestion; the evaluation
   run as its one heavy step; milestone shape `per-brief`; the four rag-app gates of rule 10; and
   two speed claims, both `expected`, with no `record`.
2. The four gates of rule 10 are five gate entries, because the format gives a gate one `kind`: a
   versioned evaluation set, `check` (`evaluation-set`); the quality bars for retrieval and for
   answers, `check` that both are declared as numbers (`quality-bars`) and `judgement` that the
   recorded run meets them (`quality-bars-met`); prompt and model version pinning, `check`
   (`version-pinning`); a privacy review of the corpus, `judgement` (`privacy-review`). None is
   `owner_only`: rule 10 marks no rag-app gate so.
3. Rule 11 lists the phases in order and says nothing of parallel lanes for rag-app, unlike
   web-app; so `answers` follows `retrieval` and no lane runs the two kinds together. Whether the
   two may run in parallel against a retrieval contract, which the brief's parenthesis names and
   rules 10 and 11 do not, is asked on the pull request (`Q-662-2`); the sequential order is the
   conservative reading and a later ruling makes it parallel by a change of this file.
4. Rule 11 names no milestone shape for rag-app; `per-brief` is one pull request per brief, as
   today (rule 7), so it changes nothing until a person rules otherwise.
5. The three check gates name governance steps (`evaluation-set`, `quality-bars`,
   `version-pinning`) that no build has added yet; as for web-app (ADR-0313 decision 4,
   `Q-651-2`), this build adds no step to `agk-governance` and changes no file under `.github/`
   or `agk.mk`, and the conductor and the owner read those gates as judgement until a build adds
   their steps (brief #662 answer 2).
6. The playbook holds the shape of the work and its gates only: no tool, vendor, framework, model,
   URL or project name, and no version of anything (brief #662 answer 1). The folders it names
   (`corpus/`, `evaluation/`, `retrieval/`, `answers/` and their `tests/` mirrors) are suggestions
   a project maps to its own. No `reviewed` key is added (rule 2; `Q-651-1`, amendment 129 is its
   own item).
7. `tests/kit_dev/test_kit_manifest.py` lists the playbook among the installed files outside the
   law roots; the LF pin of `kit/templates/gitattributes` (`config/playbooks/**`, ADR-0313
   decision 5) already covers it. `kit/hashes.json` is not edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the rag-app playbook unchanged, and
`check_playbooks.py` prints `ok playbooks (2 playbooks)` there. Nothing reads the file until a
project declares `work_type = "rag-app"` by its own ADR (rule 5, ADR-0312), and the readers of
rules 6 to 9 are builds (e) to (h), so a project that declares no work type runs exactly as today.

## Residual

- 2026-11-07: the three check gates name governance steps that do not exist yet; until a build adds
  them, the conductor and the owner read those gates as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-07: whether retrieval and answers may run in parallel lanes awaits the ruling on
  `Q-662-2` (due 2026-12-31).
- 2026-11-07: every claim is `expected`; no run of this playbook has been measured (SPEC-0038 rule
  11, due 2026-12-31).
