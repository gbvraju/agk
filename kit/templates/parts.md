# Parts

The parts record of this project (SPEC-0076 rule 7): each library the product uses, chosen per need, with its reason,
the alternatives considered, its licence and its health on the day it was read. The steward drafts it once with
`parts_record.py draft` after the stack is accepted; the architect reviews it and the person answers only the
questions below. One section per runtime of the stack record, one row per need. A second part for one need takes one
line `Decision: <need>: <reason>` under its section. `stdlib` is the runtime's own library: no version, no health.

## example-runtime

| Need | Part | Version | Kind | Why | Alternatives considered | Licence | Health (date) | For the business |
|---|---|---|---|---|---|---|---|---|
| web-api | example-server | 1.2.3 | runtime | REQ-001; a small JSON service | example-other: slower to grow | MIT | maintained; advisories none; last release 2026-10-02; 10000 weekly downloads; scorecard 7.0 (read 2026-11-27, https://example.com/registry/example-server) | Lets the booking page at shop.example.com ask for free times. |
| time | stdlib | none | runtime | engineering; the runtime's own library | none | MIT | none (stdlib) | Shows each booking in the customer's own time zone. |

Questions for the person:

Confirmed by: none yet
