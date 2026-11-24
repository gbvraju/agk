# ADR-0762: The design browser calls stay offline and the imported shot reaches its own server (REQ-044)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1828, ADR-0450 (brief #1063), ADR-0350 (brief #461), ADR-0107, PB-08 of #1770, plan #661
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `skills/`

## Context

ADR-0450 decision 4 sends every request of an imported page through `FilesServer`, a server on 127.0.0.1 named by
`--proxy-server`, beside the offline rule `--host-resolver-rules=MAP * ~NOTFOUND` (measured working on 2026-11-12).
On Google Chrome for Testing 153 the resolver rule also maps the proxy's own address, so the browser never connects:
the shot is the `No internet` page (`ERR_PROXY_CONNECTION_FAILED`) and every imported page reads `drift: pixels`, or,
on a white page, a false `match` under the default `pixel_tolerance` (brief #1828, measured share
0.009568576388888889). No test ran a real browser. The `file:` calls were offline only because the same rule also
blocked a machine proxy (`HTTPS_PROXY`, system settings); `design.py screenshots --folder` had no offline rule at all
and sent `CONNECT` requests to a stand-in machine proxy. A refused `CONNECT` whose browser had closed printed a
`BrokenPipeError` traceback. The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, brief the four
blockers".

## Decision

1. One definition of the offline flags, `design.OFFLINE`: `--headless`, `--disable-gpu`,
   `--host-resolver-rules=MAP * ~NOTFOUND` and `--no-proxy-server`. `design_render.OFFLINE` is that tuple. Every call
   that opens a `file:` page uses it: `design_render.measure` and `shoot`, `design_compare.shoot_at` without a port and
   `design.py screenshots --folder`.
2. `design_render.proxied(port)` gives the flags of the one call through `FilesServer`: `--headless`, `--disable-gpu`,
   `--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1`, `--proxy-server=http://127.0.0.1:<port>` and
   `--proxy-bypass-list=<-loopback>`. The exclusion appears only beside `--proxy-server`; `localhost` and `::1` are not
   excluded (`<-loopback>` sends them to the server, which refuses them). The flags are not a setting (Q-G4-2).
3. `FilesServer` records each path it served with 200. After the imported shot, `compare_imported` exits 1 with
   `rule 11: the headless browser did not open the imported page through the files server` when the mapped file is not
   among them, whatever `pixel_tolerance` (Q-G4-1). This adds one case to ADR-0450 decision 3's list of exits 1.
4. A refused request stays a 403 and is counted. A page line whose page or a stylesheet it links has references in
   `docs/design/imported/i<n>/external.txt` ends `; external: <n> not loaded (docs/design/imported/i<n>/external.txt)`,
   the count from that file; no URL or host is printed (Q-G4-4). The line stays one line, read by `plan_ceremony.MATCH`
   as before.
5. The handler and the server print nothing for `BrokenPipeError` and `ConnectionResetError`; any other error still
   prints.
6. `tests/kit_dev/test_design_offline_browser.py` runs the real flags with a headless browser on PATH (skipped without
   one) against a real `FilesServer`, a stand-in loopback service and a stand-in machine proxy, and checks with a fake
   browser that every browser command of the kit carries the offline rule and that only the proxied one has the
   exclusion and `--proxy-server`.
7. `FilesServer` binds 127.0.0.1 only (Q-G4-3). The browser's own background requests are not turned off by further
   flags in this decision (Q-G4-5): they are refused by the server or blocked by the offline flags.

Path classes changed: `scripts/agk/` (`design.py`, `design_render.py`, `design_compare.py`), `tests/kit_dev/` (the new
test file and `test_design_compare.py`, `test_design_render.py`, `test_design_write.py`) and `skills/`
(`skills/design/SKILL.md`). The scripts are kit-only; no installed file changes. No workflow or check runs them.

## Consequences

An imported page that matches reads `match` again, and an error page can no longer read `match` or `drift`. No browser
call of the design commands uses a machine proxy, so an external font is never fetched off the machine. A browser
update that reopens either hole fails the real-browser test wherever the kit's suite runs with a browser on PATH.

## Residual

Windows and macOS browsers read their system proxy, which `--no-proxy-server` and `--proxy-server` override (verify on
such a machine). A browser older than 153 was not measured with the exclusion (verify).
