# Run report: day 1 (PR #3, ADR-0003)

Date: 2026-10-14 (from `date -u`). Source for every row: Claude Code documentation, fetched 2026-10-14 —
Permissions (https://code.claude.com/docs/en/permissions) and Hooks (https://code.claude.com/docs/en/hooks).

## Documentation checks

| Fact | Result | Evidence |
| --- | --- | --- |
| `ask` rules exist and prompt | confirmed | Permissions: "Ask rules prompt for confirmation whenever Claude Code tries to use the specified tool." |
| JSON key literally named `permissions.ask` | not confirmed (verify) | The pages read name "Ask rules" and the order below; no JSON snippet with an `ask` array was seen. The key stays marked (verify) in `day-0.md`. |
| Deny beats allow | confirmed | "Rules are evaluated in order: deny, then ask, then allow. The first match … determines the outcome"; "An allow rule can't carve an exception out of a deny rule." |
| Ask beats allow | confirmed | "a matching ask rule prompts even when a more specific allow rule also matches." |
| `:*` prefix syntax | confirmed, end of pattern only | "The `:*` suffix is an equivalent way to write a trailing wildcard, so `Bash(ls:*)` matches the same commands as `Bash(ls *)`"; "The `:*` form is only recognized at the end of a pattern." |
| Mid-pattern `*` in Bash rules | confirmed | "Bash rules match the whole command text, with `*` standing in for any text." Argument-order patterns are documented as fragile, so deny rules here cover flags before and after the remote. |
| Exact Bash rule without `*` | confirmed by contrast | A rule with `*` "reads the rule as a wildcard pattern, not an exact match"; the allow rule `Bash(git push -u origin HEAD)` has none. |
| `Write(path)` rules | **finding** | "Claude Code checks file permissions against `Edit(path)` and `Read(path)` rules only"; `Write(...)` rules are accepted but never consulted and warn at startup. The `Write(...)` rules in `settings.json` were therefore inert; removed in this PR. |
| `Edit` path anchoring | confirmed | "`path` or `./path` — relative to current directory"; "`/path` — relative to the settings source" (project root in project settings). Rules now use `/path`. |
| Stop hook `stop_hook_active` | confirmed | "true when Claude Code is already continuing as a result of a stop hook. Check this value … to avoid blocking on a condition that will never resolve." Also an 8-consecutive-continuation cap. |
| Stop block contract | confirmed | `{"decision": "block", "reason": …}`; exit code 2 also blocks. |
| `$CLAUDE_PROJECT_DIR` | confirmed | "the project root where the session started". |

## Notes

- Pages were read through a summarising fetch and, for the permissions page, a saved copy searched with grep; the
  `ask` array key is the one item not seen verbatim.
- Q-K1-2: the inert `Write(...)` rules were an error from day 0; they are removed here and recorded in ADR-0003.
