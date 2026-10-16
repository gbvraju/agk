# Proposed amendments to SPEC-0005 (found while building the plugin, ADR-0019)

Date: 2026-10-16 (from `date -u`). SPEC-0005 is Approved; these changes are proposed, not applied. They take effect only
on the maintainers' instruction. Evidence: `docs/runs/spec-0005-verify-facts.md`.

## A. Rule 16 and the Residual: a permission rule that names the plugin's script (Q-K3-73)

`${CLAUDE_PLUGIN_ROOT}` is documented in the `allowed-tools` frontmatter of a plugin skill (Bash rules), and not in
`settings.json` permission rules. Proposed text for rule 16:

> Approval friction. In K1 and K2 each kit script run from outside the project needed an approval. A plugin skill can
> name its own script in `allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/<script>.py" *)`
> (confirmed in the Claude Code documentation); whether `${CLAUDE_PLUGIN_ROOT}` expands in a `settings.json` rule is
> not documented `(verify)`. The built skills set no `allowed-tools`: pre-approving a script run is a permission
> decision for the maintainers. Until it is decided each command asks once per session, a residual.

The built plugin follows the conservative reading (no pre-approval). If the maintainers decide to pre-approve, the change
is one frontmatter line per skill and a test update.

## B. Rule 14: the `ref` of a `github` source in `extraKnownMarketplaces` (Q-K3-72)

The settings reference shows `{"source": "github", "repo": ...}` there and documents `ref` for the same source type only in
the `strictKnownMarketplaces` table. The printed entry carries `"ref": "v<kit_version>"` and a `(verify)` line. Two
alternatives, for the maintainers to choose: keep it (it is the spec's text, unconfirmed); or print the entry without `ref`
and tell users to add the marketplace with `claude plugin marketplace add gbvraju/agk#v<kit_version>` (documented), which
loses the pin in the committed file.

## C. Rule 8: the commands `/agk:spec` and `/agk:brief`

- `/agk:spec` runs `new_spec.py spec` or `new_spec.py requirement`; `--from-issue N` is implemented by the command reading
  the issue (`gh issue view`, read-only) and passing the text with `--issue N --issue-text FILE`; the script never reads an
  issue (rule 17 d).
- `/agk:brief` runs `new_spec.py brief`, so rule 5 and rule 19 (a script for every command that writes) hold; the table
  gives no script for it. Proposed table cell: "`new_spec.py brief`".

## D. Rule 6: the `(verify)` mark on skills against commands

Confirmed. Proposed: remove the mark and keep the sentence.

## E. Rule 12 and the Residual: results

`claude plugin validate .` passes (Claude Code 2.1.301) with one warning about `CLAUDE.md` at the plugin root. Proposed:
add "(one warning: `CLAUDE.md` at the plugin root is not loaded as plugin context)". The Residual item that lists five
`(verify)` facts becomes: two confirmed (key, skills against commands), one confirmed for a different place
(`allowed-tools`), one not confirmed (`ref`), one confirmed (auto-update default), as in the record.
