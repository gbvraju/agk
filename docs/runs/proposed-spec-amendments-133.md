# Proposed spec amendments 133 (SPEC-0010; REQ-003)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0321 (brief #668), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0010-proof-checks.md`.
The number 133 is the one reserved for brief #668 in the brief. This amendment is not applied to the spec text in this
pull request (the brief's `Touches:` line leaves the spec out); a person's `Approve:` applies it or sends it back. No
session posts it.

1. **New section (c), status by evidence, rule 26.** `python3 scripts/agk/req_status.py report [--json] [--req REQ-nnn ...]
   [ROOT]` reads every requirement of `docs/requirements.md` that is not `retired`, and its proof as rule 1 defines it: for
   each criterion `ACn` of the acceptance line, the test files holding a `REQ-nnn ACn` marker (the parsers of rule 2). The
   proof passes when every one of those files passes when the command of its `[proof]` area (ADR-0172) runs it alone, each
   file once, each run within `proof_timeout` (rule 15). It prints one line per requirement whose status disagrees with the
   evidence: `REQ-nnn planned -> done (proof: <n> tests pass)` (also `in-progress -> done`; `<n>` is the number of test
   files), `REQ-nnn done but proof fails (<test file>, ...)`, `REQ-nnn proof unknown (<test file> timed out)`, and
   `REQ-nnn: no proof mapped` for a requirement whose acceptance line has no `ACn`, has a criterion with no marker, or
   has a test file that no `[proof]` area runs; then one summary line. It changes nothing. Exit 1 on any
   `done but proof fails`; 4 when a proof is unknown and none fails; 0 otherwise; 2 usage; 3 I/O or a refused setting.
2. **Rule 27, `apply`.** `python3 scripts/agk/req_status.py apply` evaluates the same way and then sets the `- Status:` line
   of each `-> done` requirement to `done`, and changes no other line, so the edit stays the status-only change that
   REQ-001 AC2 exempts. It never edits a `done` whose proof fails (it is flagged, and the exit is 1) and never edits a
   requirement with no proof mapped. It refuses, naming the path class, when `docs/requirements.md` already differs from
   the commit in the work tree. It is run in one pull request that the conductor opens for it, never by a builder in a
   feature pull request.
3. **Not in this amendment.** The weekly report (SPEC-0011) is unchanged: its sections are built from the facts document
   alone (SPEC-0011 rule 8 and the fixed item kinds of its rule 69), and a list of status disagreements would be a new item
   kind, which needs its own amendment. `check_requirements.py` is unchanged: refusing a status edit that disagrees with the
   proof would run the tests inside a governance check, which rule 7 keeps out of `make governance`.
4. **Tests.** `tests/kit/test_req_status.py`, marker `REQ-003 AC4`: a fixture requirements file and a fake runner that
   needs only `python3`, with the cases planned and in-progress to done, done with a failing file, an unmarked criterion,
   no `[proof]` table and a file outside every area, agreement (done passing, planned failing, retired), one run per file,
   a timeout, `--json`, `--req`, `apply` editing only status lines, `apply` refusing a changed file, and usage errors.
