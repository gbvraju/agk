#!/usr/bin/env bash
# scripts/start-session-local.sh: one session per call, in its own worktree; the twin of
# scripts/start-session-windows.ps1 for Linux and macOS. Set launch_adapter = "bash scripts/start-session-local.sh".
# It reads AGK_SESSION and the prompt on standard input, creates the worktree ../agk-<session> from
# origin/main (your default branch), or reuses it when a clean one is left from an earlier start, and starts claude there with the prompt: in a new GNOME Terminal tab when a desktop is there,
# otherwise in the background with its output in <worktree>/.agk-session.log (verify: the terminal's options and
# claude's print mode, -p, are the terminal's and the runtime's, and were not run by the session that wrote this).
# When claude exits, <worktree>/.agk-session-exit holds exit_code=<code> and ended_utc=<UTC time>.
# With AGK_MODEL set (the tier's name from [models.names], brief #1252, ADR-0530) claude gets --model AGK_MODEL, and
# --effort AGK_EFFORT beside it when that is set; without AGK_MODEL it gets no flag (verify: the flags are claude's).
set -euo pipefail
session="${AGK_SESSION:?AGK_SESSION is not set}"
prompt="$(cat)"

# 1. The worktree first, and keep the session's own files out of git.
repo="$(git rev-parse --show-toplevel)"
worktree="$(dirname "$repo")/agk-$session"
git -C "$repo" fetch --quiet origin
if [ -e "$worktree" ]; then
    # The folder is there from an earlier start (a session that ended or crashed): reuse it when it is a clean
    # worktree of this repository, otherwise start nothing for this session.
    ours="$(cd "$(git -C "$repo" rev-parse --path-format=absolute --git-common-dir)" && pwd -P)"
    common="$(git -C "$worktree" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || common=""
    top="$(git -C "$worktree" rev-parse --show-toplevel 2>/dev/null)" || top=""
    if [ -z "$common" ] || [ -z "$top" ] || [ "$(cd "$common" && pwd -P)" != "$ours" ] \
        || [ "$(cd "$top" && pwd -P)" != "$(cd "$worktree" && pwd -P)" ]; then
        echo "start-session-local: $worktree exists and is not a worktree of this repository; nothing started" >&2
        exit 2
    fi
    if ! changes="$(git -C "$worktree" status --porcelain --untracked-files=all)" || [ -n "$changes" ]; then
        echo "start-session-local: $worktree is not clean; nothing started" >&2
        exit 2
    fi
    git -C "$worktree" fetch --quiet origin
    git -C "$worktree" checkout --quiet --detach origin/main   # your default branch
else
    git -C "$repo" worktree add --quiet --detach "$worktree" origin/main   # your default branch
fi
exclude="$(git -C "$worktree" rev-parse --git-path info/exclude)"
case "$exclude" in /*) ;; *) exclude="$worktree/$exclude" ;; esac
mkdir -p "$(dirname "$exclude")"
for name in .agk-session-exit .agk-session.log; do
    grep -qxF "$name" "$exclude" 2>/dev/null || printf '%s\n' "$name" >> "$exclude"
done

# 2. The prompt in a file outside the worktree, and the wrapper that runs claude and writes the exit file.
prompt_file="$(mktemp "${TMPDIR:-/tmp}/agk-$session-prompt.XXXXXX")"
printf '%s' "$prompt" > "$prompt_file"
# shellcheck disable=SC2016  # the wrapper expands its own arguments
wrapper='cd "$1" || exit 1
unset CLAUDE_CODE_CHILD_SESSION
prompt="$(cat "$2")"; rm -f "$2"
flags=()
if [ -n "${4:-}" ]; then flags=(--model "$4"); if [ -n "${5:-}" ]; then flags+=(--effort "$5"); fi; fi
code=0
if [ "$3" = tab ]; then claude "${flags[@]}" "$prompt" || code=$?; else claude "${flags[@]}" -p "$prompt" || code=$?; fi
printf "exit_code=%s\nended_utc=%s\n" "$code" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$1/.agk-session-exit"
exit "$code"'

# 3. A tab on a desktop, the background anywhere else.
if command -v gnome-terminal >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    gnome-terminal --tab --title "$session" --working-directory "$worktree" -- \
        bash -c "$wrapper" agk-session "$worktree" "$prompt_file" tab "${AGK_MODEL:-}" "${AGK_EFFORT:-}"
else
    nohup bash -c "$wrapper" agk-session "$worktree" "$prompt_file" background "${AGK_MODEL:-}" "${AGK_EFFORT:-}" \
        > "$worktree/.agk-session.log" 2>&1 < /dev/null &
fi
