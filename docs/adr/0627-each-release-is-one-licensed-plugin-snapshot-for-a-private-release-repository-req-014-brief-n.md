# ADR-0627: Each release is one licensed plugin snapshot for a private release repository (REQ-014, brief 1476)

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1476, ADR-0596, ADR-0326, SPEC-0071 rules 5 and 7, plan #661
- Requirements: REQ-014

Protected classes: `scripts/agk/`, `kit/`, `agk.toml`, `config/`, `tests/kit/`, `tests/kit_dev/`

## Context

The plugin's marketplace is the development repository itself (`.claude-plugin/marketplace.json`, `"source": "."`), so
installing the plugin clones `gbvraju/agk` whole: every commit, tag, ADR, spec, brief and run record, and the history
published under Apache 2.0 before 0.64.0. Claude Code installs a plugin from a private repository with the person's own
git credentials, so read access to the development repository would expose all of it `(verify: the Claude Code
documentation on private marketplaces)`. ADR-0596 licensed every kit file; SPEC-0071 rule 7 keeps the plugin on the
machine from the owner's private source. A customer's machine needs far less than the whole repository. The owner's
direction (2026-11-17, quoted as data in brief #1476) is a separate private release repository holding only tagged,
licensed plugin copies.

## Decision

1. Each release builds one plugin snapshot with the kit-only script `scripts/agk/plugin_snapshot.py build --tag vX.Y.Z
   --out DIR`. It reads the tag only, by `git archive`, and writes exactly the paths of the allow list `snapshot` of
   the tag's own `kit/manifest.json`: an entry ending in `/` is a folder, any other one file. A `--tag` that is not a tag
   (`refs/tags/<tag>`) and a tag without the list are refused, naming the setting, so a tag always gives the same
   snapshot; the first release after this change is the first that builds. The list is the plugin (`.claude-plugin/`, `skills/`, `scripts/agk/`, `.claude/agents/`,
   `.claude/hooks/`), `kit/`, `config/`, `constitution/`, `tests/kit/`, `LICENSE`, `LICENSE-AGK`, `REUSE.toml` and
   every path the manifest installs into a project, so the installer and upgrade work from the snapshot. It holds no
   `docs/adr/`, `docs/specs/`, `docs/runs/`, `docs/briefs/`, `changelog.d/`, `tests/kit_dev/`, workflow of the kit's
   own repository or `.git`. The same tag gives a byte-identical tree and one printed SHA-256 digest.
2. The build fails, naming the path class and writing nothing, when a kit file of the snapshot (as
   `check_licence_notice.py` defines kit files, read from the snapshot's own manifest and `REUSE.toml`) has no owner and
   licence header, when `guard.scan_text` finds a secret or personal-data shape in any file of the snapshot, and when the
   tag's own `kit_hashes.py --check` fails in a throwaway clone of the tag. `kit/hashes.json` is copied as the tag holds
   it, with every release row, since uninstall and upgrade read them. The header is checked on the kit files only: the
   other files of the snapshot (`tests/kit/`, the kit-only lists of `config/`, `constitution/vision.md`) carry no header
   in the kit either, and `LICENSE` and `LICENSE-AGK`, which the snapshot holds, cover them.
3. The snapshot carries its own `.claude-plugin/marketplace.json`: one plugin `agk`, `"source": "."`, `version` the tag
   without its `v`. A customer adds `<owner>/<release repository>#vX.Y.Z` and installs `agk@agk`, pinned to the tag.
   The repository is the setting `[release] repository` in `agk.toml`; `publish` refuses while it is unset, naming the
   setting.
4. Creating the release repository, pushing and tagging it, and granting or revoking access are the owner's.
   `plugin_snapshot.py publish` prints, and never runs, the commands that commit the snapshot as one commit
   `Release vX.Y.Z` on top of the last release, tag it and push, and the grant (`permission=pull`) and revoke lines for
   one person. The release repository so holds one commit per release and no development history; an upgrade is a pull
   of the next tag.
5. `plugin_snapshot.py verify --tag vX.Y.Z --clone DIR` compares a clone of the release repository at the tag with a
   fresh build, byte for byte, and fails naming the first path that differs. The owner runs it after the push as the
   release's last step; no workflow changes.
6. Every mode installs the same plugin from the release repository; CI mode keeps today's install of kit files into the
   project (SPEC-0071 rule 5); the development repository keeps its own marketplace for the maintainers.
7. The script is kit-only, listed in `config/kit-only.txt` like `kit_hashes.py`, since it serves the kit's own
   release; the exception ceiling of ADR-0326 rises once, from 9 to 10, for it.

## Consequences

- A customer never receives the development history, the decisions or the briefs; a revoked person keeps the copy
  already installed, which the licence and the written grant cover.
- The manifest gains one key, `snapshot`, which the manifest shape test names.
- A release gains two owner steps (publish's commands and verify) and no session gains any power to push, tag or grant.

## Residual

- The owner creates the private release repository, names it in `[release] repository`, pushes the first snapshot and
  grants access; nothing of that is done by this change.
- At v0.64.8 the build refuses: `guard.scan_text` finds an address, number or key shape in 54 files of the snapshot,
  each an invented or code value (test fixtures, `zip(args[::2], ...)` read as an address). Whether the scan stays as
  the brief states, scans fewer shapes, or the files change first is Q-1476-1.
- `verify` stays the owner's documented step after the publish, not a row of the release pull request's check
  (Q-1476-2, answered by the conductor 2026-11-17); a later brief may add it to a check once a workflow change is ruled.
