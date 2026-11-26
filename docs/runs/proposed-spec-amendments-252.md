# Proposed spec amendments 252 (SPEC-0039; REQ-066)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0813 (brief #1957), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rule 5). Brief #1957
reserved amendment 252. This file proposes the lines and does not edit the spec. They are applied word for word, on a
person's `Approve: SPEC-0039`; no session posts it.

## Why

The merger holds a pull request labelled `agk:approve` until the owner's line; with ADR-0813 the steward's settled line
(amendment 251 item 1) approves a correction or implementation amendment, and the merger must read it the same way.

## Items

1. **SPEC-0039 rule 5, `spec approval`.** After "or whose label is `agk:approve`" insert ", unless `[steward]
   settle_amendments = true` on the checkout read and every approval the `Owner needed:` comments ask is an amendment
   that a steward's settled line (SPEC-0059 rule 4 as amendment 251 proposes) by an account in `spec_approvers` settles
   after its ask (amendment 252)".
   Class: behaviour

No other rule changes.

2026-11-26 (from `date -u`), brief #1966: item 1 (to rule 5) applied to `docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` word for word, on the maintainer's answer on #1959 (comment 7181601613).
