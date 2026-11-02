# Design sign-offs

The person's agreements of the design phase (SPEC-0037 rules 3 and 9), one row each, appended by the session after the
person's line and never edited. `kind` is `inventory` (after `Approve: inventory <full head ID>`) or `design` (after
`Approve: design <version> <full head ID>`); `version` is `-` for an inventory row and the version, `v<n>`, for a design
row; `digest` is the SHA-256 of what was agreed, as rule 9 computes it; `head` is the full commit ID the line names;
`date` is YYYY-MM-DD from `date -u`; `comment` is the link of the person's comment. A row counts only with that line by
an account listed in `spec_approvers`.

| kind | version | digest | head | date | comment |
|---|---|---|---|---|---|
