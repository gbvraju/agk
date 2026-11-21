# Data model

The data model of this project (SPEC-0072 rule 5, ADR-0677). The architect agent drafts it in the `contract` brief's
pull request, beside `contracts/openapi.json`, and a fresh reviewer agent reviews it. The rows below are invented
examples; replace them with the product's own entities.

## Entities

| Entity | Keys | Personal data | Kept for | Who may see it |
|--------|------|---------------|----------|----------------|
| Studio | `id` | none | while the studio is listed | everyone |
| Booking | `id`; `studio_id` refers to Studio | `email`: contact | 12 months after `starts_at` | the person who booked and the studio's staff |

Personal data classes: `none`, `contact` (a name, an email address, a phone number), `sensitive` (health, money,
identity documents). A `sensitive` field needs the person's yes below before any build keeps it.

## The person's yes

The person is asked one plain question, with a recommendation: which data is kept, for how long, and who may see it.
The interface itself is an engineering matter, settled in review (SPEC-0062 rule 9).

Approved by the person: (date and the words of the yes)
