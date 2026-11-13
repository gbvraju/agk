# ADR-0433: AGK is all rights reserved until a go-to-market licence is chosen (REQ-014, brief 1016)

- Status: Accepted
- Date: 2026-11-10
- Deciders: maintainers
- Related: brief #1016, plan #661
- Requirements: REQ-014

Protected classes: `pyproject.toml`, `.claude-plugin/`, `tests/kit_dev/`

## Context

AGK has been offered under Apache-2.0: `LICENSE` holds the full Apache text, `pyproject.toml` and
`.claude-plugin/plugin.json` name `Apache-2.0`, and `README.md` and `docs/guides/reference.md` each end with
`Licence: Apache-2.0.`. GitHub shows the repository as Apache-2.0 because of `LICENSE`. The owner's word
(2026-11-10 21:51 IST, quoted as data in brief #1016): "for now I would like to change license instead of opensource
lets have rights with us until we decide on GTM path".

## Decision

1. From this change on, AGK is proprietary: every file is all rights reserved by its owner. `LICENSE` holds only the
   copyright line and the notice that no licence is granted without the owner's written permission.
2. `pyproject.toml` names `license = "LicenseRef-Proprietary"` and `.claude-plugin/plugin.json` names
   `"license": "LicenseRef-Proprietary"`; nothing else in either file changes.
3. `README.md` and `docs/guides/reference.md` say `Licence: proprietary, all rights reserved (see LICENSE).`
4. No source file header is added.
5. Releases up to and including v0.63.0 were released under Apache-2.0 and keep that licence; the change applies to
   versions released after it.
6. A test in `tests/kit_dev/` holds the five files to the notice: no `Apache-2.0`, no `Apache License`, and the two
   metadata files name `LicenseRef-Proprietary`.

## Consequences

GitHub stops showing Apache-2.0 for the repository. An installed kit carries the same notice, and a project installs
it under the owner's permission. A later go-to-market licence is a new ADR that replaces this one.

## Residual

- The go-to-market licence is not chosen yet (2026-11-10).
