#!/usr/bin/env bash
# scripts/start-session-local.sh: one session per call, in its own worktree; the twin of
# scripts/start-session-windows.ps1 for Linux and macOS. Set launch_adapter = "bash scripts/start-session-local.sh".
# It reads AGK_SESSION and the prompt on standard input, creates the worktree ../agk-<session> from
# origin/main (your default branch), or reuses it when a clean one is left from an earlier start, and starts claude there
# headless with the prompt, in the background with its output in <worktree>/.agk-session.log (SPEC-0064 rule 5). With
# AGK_SHOW_JOBS=true ([autopilot] show_jobs, which launch.py passes) and a desktop, the job also shows in a GNOME Terminal
# tab that closes when it ends, its output still in the log (verify: the terminal's options, a tab closing when its
# command exits, and claude's print mode, -p, are the terminal's and the runtime's, and were not run by the session that
# wrote this).
# Before claude starts, <worktree>/.agk-session-pid holds session=, pid= (this wrapper's process, whose tree holds
# claude), started_utc=, brief= and, from AGK_JOB_KIND, AGK_ITEM and AGK_HEAD, kind=, item= and head= (SPEC-0064
# rule 3); the watchdog, launch.py and autopilot.py status read it.
# When claude exits, <worktree>/.agk-session-exit holds exit_code=<code> and ended_utc=<UTC time>.
# With AGK_MODEL set (the tier's name from [models.names]) claude gets --model AGK_MODEL, and
# --effort AGK_EFFORT beside it when that is set; without AGK_MODEL it gets no flag (verify: the flags are claude's).
set -euo pipefail
session="${AGK_SESSION:?AGK_SESSION is not set}"
prompt="$(cat)"

# 1. The worktree first, and keep the session's own files out of git.
repo="$(git rev-parse --show-toplevel)"
worktree="$(dirname "$repo")/agk-$session"
# One conductor per machine (brief #1409): a conductor job starts nothing while a record of kind conductor beside this
# checkout names a live process that has not written its exit file.
if [ "${AGK_JOB_KIND:-}" = conductor ]; then
    field() { sed -n "s/^$1=//p" "$2" 2>/dev/null | tr -d '\r' || true; }
    for record in "$(dirname "$repo")"/agk-*/.agk-session-pid; do
        [ -f "$record" ] || continue
        pid="$(field pid "$record")"; started="$(field started_utc "$record")"
        ended="$(field ended_utc "$(dirname "$record")/.agk-session-exit")"
        if [ "$(field kind "$record")" = conductor ] && [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null \
            && { [ -z "$ended" ] || [[ "$ended" < "$started" ]]; }; then
            echo "start-session-local: conductor $(field session "$record") is running on this machine; nothing started" >&2
            exit 3
        fi
    done
fi
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
for name in .agk-session-exit .agk-session-pid .agk-session.log; do
    grep -qxF "$name" "$exclude" 2>/dev/null || printf '%s\n' "$name" >> "$exclude"
done

# 2. The prompt in a file outside the worktree, and the wrapper that runs claude and writes the exit file.
prompt_file="$(mktemp "${TMPDIR:-/tmp}/agk-$session-prompt.XXXXXX")"
printf '%s' "$prompt" > "$prompt_file"
# shellcheck disable=SC2016  # the wrapper expands its own arguments
wrapper='cd "$1" || exit 1
unset CLAUDE_CODE_CHILD_SESSION
prompt="$(cat "$2")"; rm -f "$2"
printf "session=%s\npid=%s\nstarted_utc=%s\nbrief=%s\nkind=%s\nitem=%s\nhead=%s\n" "$6" "$$" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$7" "$8" "$9" "${10}" > "$1/.agk-session-pid"
flags=()
if [ -n "${4:-}" ]; then flags=(--model "$4"); if [ -n "${5:-}" ]; then flags+=(--effort "$5"); fi; fi
code=0
if [ "$3" = tab ]; then
    claude "${flags[@]}" -p "$prompt" 2>&1 | tee "$1/.agk-session.log"; code=${PIPESTATUS[0]}
else
    claude "${flags[@]}" -p "$prompt" || code=$?
fi
printf "exit_code=%s\nended_utc=%s\n" "$code" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$1/.agk-session-exit"
exit "$code"'

# 3. The background, or with show_jobs on a desktop a tab that closes when the job ends.
if [ "${AGK_SHOW_JOBS:-}" = true ] && command -v gnome-terminal >/dev/null 2>&1 \
    && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    gnome-terminal --tab --title "$session" --working-directory "$worktree" -- \
        bash -c "$wrapper" agk-session "$worktree" "$prompt_file" tab "${AGK_MODEL:-}" "${AGK_EFFORT:-}" \
        "$session" "${AGK_BRIEF:-}" "${AGK_JOB_KIND:-}" "${AGK_ITEM:-}" "${AGK_HEAD:-}"
else
    nohup bash -c "$wrapper" agk-session "$worktree" "$prompt_file" background "${AGK_MODEL:-}" "${AGK_EFFORT:-}" \
        "$session" "${AGK_BRIEF:-}" "${AGK_JOB_KIND:-}" "${AGK_ITEM:-}" "${AGK_HEAD:-}" > "$worktree/.agk-session.log" 2>&1 < /dev/null &
fi
