# ADR-0566: One connection per command, and the guarded merge reads through the shared reader

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1336, brief #1335, brief #1251, brief #1314, ADR-0548, ADR-0555, ADR-0565, plan #661
- Requirements: REQ-050

## Context

Brief #1336 found that `scripts/agk/session.py` `gh()` starts one `gh api` process per call, about one second a
call on Linux, most of it starting the program and a new TLS connection; a 304 saves the hourly limit but not that
second. The reads are already few, conditional and serial (ADR-0548, ADR-0555). `scripts/agk/merge_cleared.py`
had its own caller with no ETag cache, no limit wait and no call count. The owner ruled (`Maintainer answer:
Q-1336-1` on the brief) that reading the GitHub sign-in token in memory for the life of one command fits principle
5 when it is never written down and is sent only to GitHub.

## Decision

1. `[flow] github_transport` of `agk.toml`: `"gh"` (today's behaviour, every call a `gh api` process) or
   `"direct"`. It is read from the nearest `agk.toml` at or above the working folder with its default and needs no line; any other value reads as `"gh"` with one line on standard error that names the setting, never the value, so a read never stops on it. With
   `"direct"`, the plain GETs of `gh()` (no extra arguments) of one process go over one kept-alive HTTPS
   connection of the standard library to the API host of the host `gh` is signed in to (`GH_HOST`, else
   `github.com`, whose API host is `api.github.com`; any other host's API is `/api/v3` on that host
   `(verify: the enterprise path)`). The answer is handed to `gh()` in the form `gh api -i` prints, so the ETag
   cache, the 304s, paging, counting and the limit waits of ADR-0565 are the same code. Writes, reads with extra
   arguments and `GET rate_limit` stay with `gh api`.
2. The token is asked from `gh auth token --hostname <host>` once per process, held in memory only and sent only
   in the `Authorization` header to that host over TLS with the default certificate checks. It is never written
   to a file, the cache, the environment, an argument list, a log or an error message; no text of an exception is
   printed. A redirect is never followed: the header can reach no other host.
3. The process falls back to `gh api` for the rest of the run, and prints `github: direct transport unavailable,
   using gh` once on standard error, when: the token cannot be read; a proxy variable (`HTTPS_PROXY`,
   `https_proxy`, `ALL_PROXY`, `all_proxy`) is set, since the standard library connection does not go through it;
   the connection or TLS fails twice in a row for one call (a dropped kept-alive connection is opened once again
   first); the answer is cut short; or GitHub answers 401 or a redirect. The call that fell back is asked again
   with `gh api`, so the run completes. A 4xx or 5xx answer is handed on as `gh api` reports it.
4. The default stays `"gh"`. Brief #1336 answer 7 makes `"direct"` the default only when its regression and stress
   gates pass with their figures in the pull request body; the stress gate of the recorded double passes, the
   suite twice with each transport forced and the 20 live plans could not be run in the cloud session that built
   it (the session reaches GitHub only through a proxy), so that switch is a later change.
5. `merge_cleared.py`'s GETs (`read_json`, `read_once`, and `read_pages` through `read_json`, which keeps its own
   paging of keyed lists and its five tries) ask through `session.gh`,
   which reaches GitHub through `merge_cleared.gh_api` (`session.RUN`), so they are conditional, counted and
   limit-aware. Every merge decision still revalidates with GitHub: `merge_cleared.py` never sets the plan's
   memo, the comment store or the unchanged-issue list, so a cached body is used only on a 304 for that same
   request. Its retries, refusals and outputs are unchanged. Its writes and its one GraphQL call keep `gh_api`.

## Consequences

A command with `"direct"` pays the start of `gh` once (the token) and one TLS handshake, not one of each per call.
The guarded merge's reads are counted in `session.CALLS`, and the 304s spare its hourly limit. A project that
sees anything unexpected returns to `"gh"` by one line; `"gh"` stays supported for at least one release. Protected
path classes changed: `scripts/agk/` (`session.py`, `merge_cleared.py`), `tests/kit/`
(`test_github_direct_transport.py`) and `agk.toml` (the new test file in the `[[testing.map]]` entries of the two
scripts).

## Residual

- 2026-11-15: the headers that `gh api` sends are matched by `Accept: application/vnd.github+json` and
  `X-GitHub-Api-Version: 2022-11-28` `(verify: gh's own defaults)`.
- 2026-11-15: the default switch to `"direct"` waits for the two gates of decision 4 that need a person's machine.
