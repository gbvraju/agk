# Proposed spec amendments 114 (principle 9, the security guide, SPEC-0005, SPEC-0041; REQ-049)

Date: 2026-11-04 (from `date -u`). Approved text changes only through a proposal like this one (principle 6). Written for
ADR-0268 (brief #538), which stays `Proposed` for the maintainers' decision. The number 114 is the one the conductor
reserved on #538; 113 is reserved for the personal-mode intake (#536). None of the items below is applied by the intake
pull request: each is applied by build (f) of SPEC-0042 rule 18, after the owner's ruling, and the constitution's item is
merged by the owner by hand. No rule weakens: each item adds the data guard or states its limits.

The owner's direction of 2026-11-04 on brief #538, quoted as data: "can AGK doing data ratification or Guardrail to avoid
server reads, secret reads from logs, even somebody put direct logs, AGK should carefully use with PII and secrets exposure
risk".

1. **Principle 9 of `constitution/principles.md`.** "No secrets in the repository or in an agent session; scanners' ignore
   lists never grow." becomes "No secrets in the repository or in an agent session, and the data guard stops reads and
   writes that would carry one; scanners' ignore lists never grow." Nothing else of the constitution changes. The owner
   merges this item by hand (build (f)).
2. **`docs/guides/security.md`, the paragraph "Secrets in a session".** Its last two sentences, "That is a rule the checks
   and the scan look for. It is not a wall: the architect role can read any file in the folder it is started in.", become a
   short statement of what the data guard does (layer 1 denies reads of secret files, raw logs, remote shells and
   databases and the environment before they happen; layer 2, `agk logs`, is the one way to read a log; layer 3 blocks a
   pasted message that holds a secret or personal data; layer 4 refuses any AGK write that holds one) and what it does
   not do (SPEC-0042 rule 16: patterns cannot catch every secret or name; the hook guards a Claude Code session's tools,
   not other programs; the guard is a second line after least privilege), with a link to `docs/guides/data-guard.md`.
   The section "What AGK stores" gains one line for the guard log outside the repository (SPEC-0042 rule 15).
3. **SPEC-0005 rule 7 ("Footprint").** Only if the owner rules `Q-S0042-15` that the plugin ships the guard: "The plugin
   ships no hook, no MCP or LSP server, no monitor and no `bin/` directory in K3." becomes "The plugin ships one hook, the
   data guard of SPEC-0042 (`hooks/hooks.json` registering `data_guard.py` for `PreToolUse` and `UserPromptSubmit`), and
   no MCP or LSP server, no monitor and no `bin/` directory." The sentence "the plugin asks for neither" becomes "the plugin
   asks for no `bin/`, and its one hook only denies or blocks", and the matching line of SPEC-0005's security list (the
   plugin "ships no hook, server or `bin/`") changes the same way. If the owner rules that the plugin does not ship it,
   this item is withdrawn and SPEC-0005 does not change.
4. **SPEC-0041 (personal mode, proposed in #537).** Its builds gain `Depends-on` the data guard's builds (c) to (e) of
   SPEC-0042, and its state writer (the `forge/` JSON, `records/`, `metrics/` and the sidecar's documents) calls
   `guard.scan_text` before every write (SPEC-0042 rule 13). If SPEC-0041 is still `Draft` when this lands, the intake of
   #536 carries the sentence; otherwise it is applied to SPEC-0041 by this item.
5. **Tests.** `tests/kit/test_data_guard_guide.py`: principle 9 carries the one clause and nothing else of the
   constitution changed; the security guide no longer says "It is not a wall" and states the limits of SPEC-0042 rule 16;
   SPEC-0005 rule 7 names exactly one shipped hook when item 3 is applied and is unchanged otherwise; `check_specs.py`
   passes the change with this file. Its marker is `REQ-049`.
