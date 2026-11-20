# ADR-0665: Playbooks carry their layers, a place for standards packs and the eight enterprise gates (REQ-079)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0048, SPEC-0038, brief #1585, plan #661, ADR-0643
- Requirements: REQ-079

Protected classes this pull request changes: `config/` (`config/playbooks/`), `scripts/agk/` (`playbook_format.py`,
`check_playbooks.py`) and `tests/kit/` (the new `test_playbook_standard.py` and the playbook tests whose gate counts
change). `kit/hashes.json` is not edited: `kit_hashes.py` reports it current.

## Context

SPEC-0072 (Approved, REQ-079) rule 12 build (a) adds rule 2's three parts of a playbook. On the default branch at
be28f2a (2026-11-20) `playbook_format.py` holds no `architecture`, `standards` or enterprise gate; `default.toml` holds
five judgement gates; only `web-app.toml` and `rag-app.toml` have `[testing] map` codes (the other eight playbooks,
`data-pipeline.toml` among them, have `map = []`); `web-app.toml` already has a gate with the id `accessibility`; and
SPEC-0048 rule 21's composition refuses a weaker restatement without naming the gate, which
`tests/kit/test_playbook_modules.py` holds ("never a value"). Rule 12 gives this build its own ADR for
`config/playbooks/`.

## Decision

1. `playbook_format.py` reads two optional top-level tables, `[architecture]` (`layers` of `{ name, paths }`, `allow`
   of `{ from, to }` with an optional `adr`) and `[[standards]]` (`stack`, `lint`, `format`, `type`, `config` and
   `rules = { tool, version, codes }`), and an optional gate key `reason`. An enterprise gate id (the eight fixed ids of
   SPEC-0072 rule 2) restated as `judgement` needs a `reason` of at least 20 characters. A `[[standards]]` stack is a
   `[[stack]]` name of `config/stack-signals.toml` when that file is present, each once, and `config` is a relative
   path inside the project.
2. A playbook's own `[architecture]` puts each `[testing] map` code in exactly one layer and has no layer path that is
   not a map code, compared as strings with forward slashes. `default.toml`'s one layer `src`, `paths = ["**"]`, is the
   base and is exempt: it constrains nothing until a work type is set. A playbook with no `[architecture]` of its own
   takes the one composed before it.
3. `check_playbooks.py` composes `default`, then modules, then the playbook, as today: the architecture is the last
   one declared; an `allow` entry that a project's own playbook (a derived one, SPEC-0048 rule 22) adds over the held
   ones must name an `adr` whose file is under `docs/adr/` of the project, else it is refused naming the key `allow`;
   a `[[standards]]` entry restated for the same stack keeps every held rule code, else it is refused naming the key
   `standards.rules`; a stack of `config/stack-signals.toml` with no entry in any playbook is one warning line on
   stderr, never a failure.
4. A weaker restatement of one of the eight enterprise gates names the gate id, a fixed name of the kit and not a
   value of the project; every other gate stays unnamed, as SPEC-0048 rule 21 holds.
5. `default.toml` holds the eight gates: `secrets` and `environment-settings` as checks with steps of those names
   (executed from build (b)), the other six as judgement with their reasons, and one evidence item each.
6. Layers, one per map code: `web-app.toml` `contracts`, `mocks`, `frontend`, `backend`, with the three `allow` entries
   of brief #1585 answer 1 (`frontend`, `backend` and `mocks` to `contracts`); `rag-app.toml` `corpus`, `evaluation`,
   `retrieval`, `answers`, with no `allow` entry (the strictest reading; one may be added by an ADR). The other eight
   playbooks have no map code, so no layer of their own (`Q-1585-1`).
7. `accessibility` is restated as judgement with a no-screen reason in `cloud-migration.toml`, `data-pipeline.toml`,
   `mcp-server.toml` and `multi-agent.toml`; `web-app.toml`'s gate gains a reason; `mobile`, `rag-app`, `pilot` and
   `voice-agent` keep `default.toml`'s.

## Consequences

Every shipped playbook composes an architecture and the eight gates; a stub that weakens an enterprise gate, drops a
pack rule code or adds an `allow` entry without a project ADR fails `make governance` and the `governance` job, with no
workflow, ruleset or required-check change. No step runs yet: build (b) adds the runner. No `[[standards]]` entry is
shipped: build (e) adds the Python packs.

## Residual

- 2026-11-20: `Q-1585-1` (layers only from map codes) and `Q-1585-2` (`default.toml`'s `src` paths and rag-app's
  empty `allow`), on the pull request of brief #1585.
