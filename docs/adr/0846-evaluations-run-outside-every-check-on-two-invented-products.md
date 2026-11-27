# ADR-0846: Evaluations run outside every check on two invented products

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2042, 2026-11-27T13:17:52Z)
- Related: ADR-0837, ADR-0838, ADR-0839, ADR-0430, ADR-0835, ADR-0544, ADR-0052, SPEC-0077, REQ-084, brief #2042, brief #2020, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `config/`, `agk.toml`, `evals/`, `.github/`, `tests/kit/`

## Context

SPEC-0077 (Approved, ADR-0837) rule 9 asks for a kit-only `evals/` holding invented reference products and a rubric,
and a kit-only `eval_run.py` that runs the AGK path on each product three times on the `strongest` tier and keeps the
median, an incomplete run never scored 0; rule 10 lets the rubric's `tolerance` decide promotion. Rule 14 build (g)
builds it. Brief #2042 splits it in two (`Q-PG-1`): build (a), this record, holds the products, the rubric, the record
form, `check` and `median`, with no model; build (b) adds `run`. On main at e4030a83 there was no `evals/` and no
`eval_run.py`.

## Decision

1. **The set.** `evals/rubric.toml` and one folder per product, `evals/booking-web/product.toml` (#1769's yoga studio
   class booking, `web-app`, domain `none`) and `evals/payments-api/product.toml` (an invented marketplace's payments
   API, `api-service`, domain `payments`), in the keys of brief #2042 answer 1. Every host is `example.com` and every
   address `.invalid`. Nothing under `evals/` is listed in `kit/manifest.json`, so no installer, upgrade, uninstall or
   plugin snapshot carries it.
2. **The rubric.** `format = 1`, `scale = 6`, `tolerance` (0 to 6; 0 until the maintainers set another, `Q-PG-2`) and
   eight `[[layer]]` tables in rule 9's order (`problem`, `scope`, `domain-rules`, `architecture`, `threats`, `data`,
   `usability`, `code`), each criterion with a `source`: an Approved spec's rule, or a public standard's URL with
   `accessed`. The runs and the tier are rule 9's and are no keys: a rubric that sets them is refused as unknown.
3. **The check.** New kit-only `scripts/agk/eval_run.py`: `check [--root DIR]` fails a product or rubric file that is
   not TOML, a missing or unknown key, a `bool` for a number, a `work_type` or `domain` outside its list, a repeated
   acceptance id, a host other than `example.com`, an address outside `.invalid`, a layer missing or out of order, a
   criterion with no source and a line that `guard.scan_text` flags, each as
   `FAIL evals: <file class>: <rule> (setting: <key>)`, never a value, else `ok evals: <n> products, <m> layers`.
4. **The record and the median.** One run record, `<DIR>/<product>/run-<n>.json` (n 1 to 3), in brief #2042 answer 3's
   form. `median DIR` checks each record and prints per product and layer the median of three complete runs, and
   `cost per accepted feature`, the median over the runs of `usd` over the accepted ids (`unknown` when a run's money is
   not a number or it accepted none); a product with fewer than three complete runs prints only
   `incomplete (<k> of 3 runs complete)`, never 0 (`Q-PG-3`).
5. **Kit-only and closed.** `eval_run.py` runs only in the kit's own repository (`kit/manifest.json` and `evals/` beside
   it); elsewhere it refuses naming the path class `evals/`, exit 2. It is in `KIT_ONLY` of the manifest test, and no
   check, gate, workflow, `agk.mk` recipe, governance step or `prepush.py` names it. It is listed with its reason in
   `config/kit-only.txt`, and the ceiling of that list in `tests/kit/test_parity.py` rises from 10 to 11, as ADR-0627
   raised it once: the Approved rule 9 makes the script kit-only, so it can be neither installed nor shipped (principle
   11: the check is changed by this record, not weakened to go green).
6. **Protected.** `evals/` joins the kit's `config/protected-paths.txt` and the `protected` class of its
   `config/reviewers.yaml`, not the project templates, so a rubric change carries an ADR (principles 1 and 11,
   `Q-PG-7`). `.github/CODEOWNERS`, rendered from `config/reviewers.yaml` by `reviewers.py --codeowners --write`, gains
   its one line `/evals/`, which is why this record also names `.github/`; no workflow changes.
7. **Wiring.** The `[testing]` map names `tests/kit_dev/test_eval_run.py` for `scripts/agk/eval_run.py` and `evals/**`,
   and the reference guide lists both commands.

## Consequences

The bar of rule 10 has fixed products and a fixed rubric to read, and a malformed record is refused before any median.
No governance run, CI job or required check changes: the check runs only when a person calls it.

## Residual

Build (b) of brief #2042 adds `eval_run.py run` (the scratch sidecar, the person's adapter, the fresh reviewer); build
(h) of SPEC-0077 writes `docs/runs/evals/<date>.md` and the promotion rule (2026-11-27).
