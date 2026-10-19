# SPEC-0014: The weekly product report footer names the kit version

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-021

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The weekly product report names the kit version it was rendered with in its footer, so a reader
can tell which rules produced it." The maintainers answered two questions before it was written: the version is carried by the facts and read as the
upgrade command reads the installed stamp, and the number alone is the content of the line.

Negative cases: none beyond AC2, because the only way for the line to be wrong is a guessed version, which AC2 forbids.

## Rules

1. **The facts carry the version.** The facts document gains an optional top-level property `kit_version`: the version string, or `"unknown"` when it cannot be
   read. `schema` stays `1`: no released consumer reads the property (as for `path` and `proof_reason`), and a renderer that does not know it ignores it.
2. **One reader of the installed version.** The installed version is read by one function of `common.py`: the `version` of `agk.toml`, or, when `agk.toml` is absent, the
   `version` of the legacy `[tool.agk]` table of `pyproject.toml` (the stamp of kits 0.1.0 and 0.2.0). `facts.py` calls it, and `upgrade.py` calls it for the stamp it
   already reads; the output of `upgrade.py` on the existing fixtures is byte-identical before and after. `upgrade.py` is not installed, so the function lives in
   `common.py`.
3. **Unknown, never a guess.** A missing file, an unreadable file, a missing `version` key or a value that is not a string gives `"unknown"`. Nothing falls back to a
   constant, to the kit's manifest or to the version of the script that renders.
4. **The footer line.** The weekly report prints `kit version: <value>` as the line directly after the `facts:` line of the footer, where `<value>` is the facts'
   `kit_version`, or `unknown` when the facts carry none (a document made before this rule). The line has no link: its evidence is the facts commit named above it.
5. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13). The inbox output has no
   footer and does not change.

## Tests

- Rule 1: the facts of a fixture repository carry `kit_version` equal to its `agk.toml` version; REQ-021 AC1.
- Rule 4: the report of that fixture has the line `kit version: <version>` directly after `facts: <commit>`; REQ-021 AC1.
- Rules 2 and 3: a fixture with no readable version gives `kit_version` `"unknown"` and the footer `kit version: unknown`, and a version guessed from anywhere else
  fails the test; REQ-021 AC2.
- Rule 4 with a facts document that has no `kit_version`: the footer says `kit version: unknown`; REQ-021 AC2.
- Rule 2: a fixture stamped only in the legacy table gives its version, through the same function that `upgrade.py` calls, and the `upgrade.py` outputs on the
  existing fixtures are unchanged; REQ-021 AC3.
- Rule 5: the renderer's imports and file reads are those of SPEC-0011 rule 13, and the inbox output of every fixture is unchanged (the existing goldens).

## Proof

REQ-021 AC1: *the footer names the kit version that the facts record.* Rules 1 and 4. REQ-021 AC2: *an unreadable version is printed as unknown and never guessed.*
Rules 3 and 4. REQ-021 AC3: *one reader serves the facts and the upgrade command.* Rule 2. The first weekly report rendered after the implementation is merged
shows the line, and the maintainers read it in that week's report issue.

## Residual

- 2026-10-19: the number is the only identification; the release notes a reader would look it up in do not exist as one file today (due 2026-12-31).

## Open questions

- Q-S0014-1 Where does a reader look up what a kit version changed? There is no single file of release notes by version today (the history is the merged pull
  requests and the ADRs). The criteria assume the number alone is enough for this requirement and build no release notes; a person decides whether a file of release
  notes is wanted, and if so it is a requirement of its own.
