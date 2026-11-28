# ADR-0869: The python-pyproject parts catalogue

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2069, 2026-11-27T19:43:37Z; the steward's answer to Q-PB-1 on #2069)
- Related: ADR-0859, ADR-0861, ADR-0858, ADR-0834, ADR-0671, ADR-0804, ADR-0844, SPEC-0076, SPEC-0072, REQ-083, brief #2069, plan #661
- Requirements: REQ-083

Protected classes: `config/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (b) asks for the `node` (with React) and `python-pyproject` catalogues,
each row sourced and dated. Build (b1) (ADR-0859, #2080) shipped `config/parts/node.toml`; by the steward's answer to
`Q-PB-1` on brief #2069, `python-pyproject` is build (b2), its own pull request with the next free ADR, this one. Rule 5
makes the rows "the maintainers' rows and never an agent's", so they are proposed here for the maintainers to accept or
change, as ADR-0859 and ADR-0671 decision 3 did.

## Decision

1. **The file.** `config/parts/python-pyproject.toml` in ADR-0859's form (`format = 1`, `[[parts]]` rows with `need`,
   `pick`, `name`, `when`, `trade_offs`, `licence`, `source` and `reviewed`, never a `version`). `kit/manifest.json` lists
   it in `verbatim`; `check_parts_catalogue.SHIPPED` becomes `("node", "python-pyproject")`, and the test holds that
   tuple equal to the manifest's stack catalogues and to the files present (rule 11).
2. **The rows, for the maintainers to accept or change here.** Every source page was opened on 2026-11-28: for a
   package, its public registry record (`https://pypi.org/pypi/<name>/json`), which states its licence (its licence
   expression, or its licence classifier where it has none) and its development status (none is inactive or yanked); for
   the runtime's own parts, the Python documentation source page of the module in the CPython repository
   (`https://raw.githubusercontent.com/python/cpython/main/Doc/library/<module>.rst`), under the Python licence
   (`PSF-2.0`, the CPython `LICENSE`). Each `reviewed` date is 2026-11-28; a row the verdict changes is changed in this
   pull request with a new `reviewed` date. A Python service has no browser front end, so `ui-components`, `routing`,
   `state`, `forms`, `e2e-tests` and `accessibility` have no row (brief #2069 answer 1).

   | need | recommended | alternatives |
   |---|---|---|
   | `web-api` | `fastapi` | `flask` |
   | `http-client` | `stdlib` | `httpx` |
   | `validation` | `pydantic` | - |
   | `data-access` | `sqlalchemy` | - |
   | `migrations` | `alembic` | - |
   | `auth` | `authlib` | `pyjwt` |
   | `config` | `stdlib` | `pydantic-settings` |
   | `secrets` | `stdlib` | - |
   | `logging` | `stdlib` | - |
   | `telemetry` | `opentelemetry-sdk` | - |
   | `jobs` | `celery` | `rq` |
   | `email` | `stdlib` | - |
   | `payments` | `stripe` | - |
   | `files` | `python-multipart` | - |
   | `cache` | `stdlib` | `cachetools` |
   | `time` | `stdlib` | - |
   | `money` | `stdlib` | - |
   | `i18n` | `babel` | - |
   | `unit-tests` | `pytest` | - |
   | `contract-tests` | `pact-python` | `schemathesis` |
   | `lint` | `ruff` | - |
   | `format` | `ruff` | - |
3. **The standard library first** (rule 4). `http-client` (`urllib.request`), `config` (`os.environ` and `tomllib`),
   `secrets` (`os.environ`), `logging`, `email` (`smtplib`), `cache` (`functools.lru_cache`), `time` (`datetime` and
   `zoneinfo`) and `money` (`decimal`) are `stdlib` rows, recommended only, each with the runtime's licence; a library
   appears only as an alternative with its `when`.
4. **Agreement with the tools the kit runs** (SPEC-0072 rule 6). `lint` and `format` name `ruff`
   (`config/standards.toml`, `gates/python_pack`) and `unit-tests` names `pytest`, which the stack template configures;
   the test fails on a disagreement. No `stdlib` row for `unit-tests`: `unittest` would contradict the template.
5. **No row off the licence list.** Every row's licence is on the kit list (`kit/templates/licences.toml`). structlog
   is not offered for `logging`: its licence is the expression `MIT OR Apache-2.0`, and a row holds one SPDX id.
6. **Outside services.** The `payments` row (`stripe`) says in plain words that the service charges and receives card
   data, the `email` row that mail goes through a mail server the project runs or pays for, and the `jobs` rows that
   they need a broker server (Redis or RabbitMQ for `celery`, Redis for `rq`).

## Consequences

The steward's draft (build (c)) starts from cited, dated, licence-checked rows for a Python product too. Every
governance run checks the file in the `playbooks` step, in CI and in `prepush.py`; ADR-0861 already lets its `source` and
`reviewed` dates pass the literal date test. No setting is added; a project's own `config/parts/python-pyproject.toml`
is read first, as build (a) ordered. With this build both catalogues of SPEC-0076 rule 15 build (b) are shipped.

## Residual

`python-pip` and the other stacks get a catalogue only with their reader (rule 11, build (h)). An old `reviewed` date
is not stale by any rule (`Q-PB-5`).
