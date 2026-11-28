# ADR-0859: The first parts catalogue: node, with React rows

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2069, 2026-11-27T19:43:37Z)
- Related: ADR-0858, ADR-0834, ADR-0671, ADR-0804, ADR-0844, SPEC-0076, SPEC-0072, REQ-083, brief #2069, plan #661
- Requirements: REQ-083

Protected classes: `config/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (b) asks for the `node` (with React) and `python-pyproject` catalogues,
each row sourced and dated. Build (a) (ADR-0858) shipped the needs catalogue and `check_parts_catalogue.py`, but no stack
catalogue: `config/parts/` held only `needs.toml`. Rule 5 makes the rows "the maintainers' rows and never an agent's", so
the rows are proposed here for the maintainers to accept or change, as ADR-0671 decision 3 did for the stack defaults.
By the brief's `Q-PB-1` reading this is build (b1), the `node` catalogue; `python-pyproject` is (b2), with its own ADR.

## Decision

1. **The file.** `config/parts/node.toml` (`format = 1`), one `[[parts]]` per row with `need`, `pick`, `name`, `when`,
   `trade_offs`, `licence`, `source` (`<URL> (accessed YYYY-MM-DD)`) and `reviewed`, never a `version`. `kit/manifest.json`
   lists it in `verbatim`; `check_parts_catalogue.SHIPPED` names `node`, and a test holds that tuple equal to the
   manifest's stack catalogues and to the files present (rule 11).
2. **The rows, for the maintainers to accept or change here.** Every source page was opened on 2026-11-28: for a
   package, its public registry record (`https://registry.npmjs.org/<name>/latest`), which states its licence and would
   carry a `deprecated` mark (none had one); for the runtime's own parts, the Node.js documentation page, under the Node.js
   licence (MIT). Each `reviewed` date is 2026-11-28; a row the verdict changes is changed in this pull request with a new
   `reviewed` date.

   | need | recommended | alternatives |
   |---|---|---|
   | `web-api` | `express` | `fastify` |
   | `http-client` | `stdlib` | - |
   | `validation` | `zod` | - |
   | `data-access` | `prisma` | - |
   | `migrations` | `prisma` | - |
   | `auth` | `passport` | - |
   | `config` | `stdlib` | - |
   | `secrets` | `stdlib` | - |
   | `logging` | `pino` | - |
   | `telemetry` | `@opentelemetry/sdk-node` | - |
   | `jobs` | `bullmq` | - |
   | `payments` | `stripe` | - |
   | `files` | `multer` | - |
   | `cache` | `quick-lru` | - |
   | `time` | `luxon` | - |
   | `money` | `dinero.js` | - |
   | `i18n` | `i18next` | - |
   | `ui-components` | `react` | - |
   | `routing` | `react-router` | - |
   | `state` | `react` | `zustand` |
   | `forms` | `react-hook-form` | - |
   | `accessibility` | `eslint-plugin-jsx-a11y` | - |
   | `unit-tests` | `stdlib` | `vitest` |
   | `contract-tests` | `@pact-foundation/pact` | - |
   | `e2e-tests` | `@playwright/test` | - |
   | `lint` | `eslint` | - |
   | `format` | `prettier` | - |
3. **The standard library first** (rule 4). `http-client` (the global `fetch`), `config` and `secrets` (`process.env`
   and `process.loadEnvFile`) and `unit-tests` (`node:test`, run by `npm test`) are `stdlib` rows, recommended only.
4. **Agreement with the tools the kit runs** (SPEC-0072 rule 6). `lint` names `eslint` (`config/standards.toml`) and
   `format` names `prettier` (`gates/node_pack.TOOLS`); a test fails on a disagreement.
5. **No row off the licence list.** `email` has no row: its usual library, nodemailer, is `MIT-0`, which is not on the
   kit list (`kit/templates/licences.toml`), so it falls to the steward's research (`catalogue: none`, rule 11) and rule
   7's question. lru-cache (`BlueOak-1.0.0`) is not offered for `cache`; `quick-lru` (MIT) is.
6. **Outside services.** The `payments` row (`stripe`) says in plain words that the service charges and receives card
   data, and the `jobs` row (`bullmq`) that it needs a Redis server.

## Consequences

The steward's draft of build (c) starts from cited, dated, licence-checked rows for a Node product. Every governance run
checks the file in the `playbooks` step, in CI and in `prepush.py`. No setting is added; a project's own
`config/parts/node.toml` is read first, as build (a) ordered.

## Residual

`python-pyproject` is build (b2), whose ADR takes the next free number. Adding the `email` row needs a permissive library
or a list change, each a later brief. An old `reviewed` date is not stale by any rule (`Q-PB-5`).
