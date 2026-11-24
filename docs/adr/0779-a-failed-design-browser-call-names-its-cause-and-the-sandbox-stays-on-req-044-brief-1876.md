# ADR-0779: A failed design browser call names its cause, and the browser's sandbox stays on (REQ-044)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1876, found-bug #1833 (from brief #1828, pull request #1830), ADR-0762, ADR-0350, ADR-0450, ADR-0107, plan #661
- Requirements: REQ-044

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit_dev/`, `skills/`

## Context

`design_render.measure` and `shoot`, `design_compare.shoot_at` and `design.py screenshots --folder` captured the
headless browser's standard error and dropped it. A browser that could not start its sandbox (CI's runner, job
137715904390 on #1830; a raw Chromium run as root, measured on main on 2026-11-24) read only `rule 8: the headless
browser did not make a screenshot` or its rule 11 and rule 6 forms, with no cause; a timeout or a browser that could not
be executed printed a traceback. SPEC-0037 rules 8 and 11 give `not run` only for a missing browser and say nothing of a
found one that fails. The owner's word on the brief (2026-11-24T02:36Z, quoted as data): "Yes".

## Decision

1. One runner, `design.browser_run(command)`, beside `design.OFFLINE`: no shell, captured output, UTF-8 with
   `errors="replace"`, a 120 second timeout. A `TimeoutExpired` or an `OSError` becomes a result marked as such. The four
   browser calls use it; `design_render._run` stays for `design_compare.pdf_page` (`pdftoppm`), unchanged.
2. One fixed clause, `design.browser_cause(result)`, from a closed list matched on the captured standard error:
   `No usable sandbox`, `Failed to move to new namespace` or `SUID sandbox helper binary` give `the browser could not start
   its sandbox (see "Design screenshots and comparison" in docs/guides/reference.md)`; `Running as root without
   --no-sandbox` gives `the browser does not start its sandbox as root (see ...)`; a timeout `the browser did not finish
   within 120 seconds`; an `OSError` `the browser could not be started`; anything else `the browser failed (its own
   message: AGK_DESIGN_BROWSER_LOG=1)`. Each refusal keeps its rule and text and appends `; <clause>`. The clause holds no
   browser text, path, URL, host or exit code (principle 8). The exit stays 1 (Q-1833-3).
3. With `AGK_DESIGN_BROWSER_LOG=1`, that exact value, `design.main` and `design_compare.main` print, after the refusal
   line, the last 20 lines of the browser's standard error to standard error, each starting `browser: `, the home folder
   written `~` (Q-1833-2, reading c). Nothing of it is written to a file; a passing call prints none of it.
4. The sandbox stays on: no browser command of the kit carries `--no-sandbox`, and a test reads every one (Q-1833-1,
   reading A). ADR-0762 decision 2 is kept: the flags are not a setting. The test-only wrapper of
   `tests/kit_dev/test_design_offline_browser.py` stays as it is.
5. `design.BROWSERS` and its order are unchanged and no setting is added (Q-1833-4); no doctor or setup check is added
   (Q-1833-5).

Path classes changed: `agk.toml` (the new test file joins the `[[testing.map]]` entries of the three scripts; no setting
is added), `scripts/agk/` (`design.py`, `design_render.py`, `design_compare.py`), `tests/kit_dev/`
(`test_design_browser_errors.py`) and `skills/` (`skills/design/SKILL.md`). The scripts are kit-only; no installed file
and no `kit/hashes.json` entry changes. No workflow or check runs them.

## Consequences

A person or builder whose browser cannot start its sandbox reads why at the first refusal, and the guide says what the
machine needs and why the kit keeps the sandbox: it confines the renderer that runs an imported customer page's script,
and without it a renderer flaw reached by such a page runs with the account's full rights, as root with the whole
machine's. A timeout or a browser that cannot be executed is a named refusal, not a traceback.

## Residual

The three sandbox texts are those of a raw Chromium on a kernel that restricts unprivileged user namespaces (verify on
the next CI run of the wrapped real-browser test); only the root text was measured here. A browser that words its
failure otherwise reads the last clause, whose setting shows its own words.
