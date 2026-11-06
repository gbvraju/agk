# Proposed spec amendments 135 (SPEC-0044; REQ-051)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0323 (brief #670), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0044-a-large-test-suite-finishes-sooner-without-removing-a-test.md`. The number 135 is the one reserved for
brief #670. This amendment is not applied to the spec text in this pull request; the owner decides it, and it needs a
person's `Approve:`; no session posts it.

1. **SPEC-0044 rule 1, first sentence.** Replace "No rule here removes, skips, retries away or quarantines a test, or
   narrows what the default branch runs" with "No rule here removes, skips, retries away or quarantines a test, or narrows
   what the default branch runs, except one isolated rerun: with `[testing] rerun_alone = true` a test that fails in the
   full run is rerun alone once, a pass alone is a strike recorded in `docs/runs/flakes.md` with an owner and an expiry, a
   failure alone is a real failure, and the run is green only when every failed test passed alone (ADR-0323)".
2. **SPEC-0044 rule 1, the list of keys.** `rerun_alone` joins the optional keys of the `[testing]` table, false when
   absent.
3. **Tests, rule 1.** The bullet gains: with `rerun_alone` absent or false, a fixture suite with one flaky, one failing and
   one passing test runs and exits as today and writes no ledger; with it true, the flaky test is one strike and the
   failing one keeps the run red.
