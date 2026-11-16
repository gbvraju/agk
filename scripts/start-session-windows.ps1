# scripts/start-session-windows.ps1: one background job per session, in its own worktree; a tab only with show_jobs.
# This repository's launch adapter (brief #1030, ADR-0439): the guide's script (getting-started, the Windows
# Terminal adapter) with one change, an existing worktree folder is reused. Not installed by the kit.
# Needs PowerShell 7: winget install Microsoft.PowerShell. Run: pwsh -NoProfile -File scripts/start-session-windows.ps1
$ErrorActionPreference = 'Stop'
$session = $env:AGK_SESSION
$brief = $env:AGK_BRIEF
if (-not $session) { throw 'AGK_SESSION is not set' }
$prompt = [Console]::In.ReadToEnd()

# 1. The worktree first, and wait until its folder exists.
$repo = (git rev-parse --show-toplevel).Trim()
$worktree = Join-Path (Split-Path $repo -Parent) "agk-$session"
git -C $repo fetch --quiet origin
if (Test-Path -LiteralPath $worktree) {
    # The folder is there from an earlier start (brief #1030, ADR-0439): reuse it when it is a clean
    # worktree of this repository, otherwise start nothing for this session.
    function Get-FullPath([string]$Path) {
        [IO.Path]::GetFullPath($Path).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    }
    $ours = Get-FullPath (git -C $repo rev-parse --path-format=absolute --git-common-dir).Trim()
    $common = git -C $worktree rev-parse --path-format=absolute --git-common-dir 2>$null
    $top = git -C $worktree rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $common -or -not $top -or
        (Get-FullPath $common.Trim()) -ne $ours -or (Get-FullPath $top.Trim()) -ne (Get-FullPath $worktree)) {
        [Console]::Error.WriteLine("start-session-windows: $worktree exists and is not a worktree of this repository; nothing started"); exit 2
    }
    $changes = @(git -C $worktree status --porcelain --untracked-files=all | Where-Object { $_ -and $_ -notmatch '\.agk-session-(exit|pid)$' })
    if ($LASTEXITCODE -ne 0 -or $changes.Count -gt 0) {
        [Console]::Error.WriteLine("start-session-windows: $worktree is not clean; nothing started"); exit 2
    }
    git -C $worktree fetch --quiet origin
    git -C $worktree checkout --quiet --detach origin/main   # your default branch
    if ($LASTEXITCODE -ne 0) { throw 'git checkout of origin/main failed' }
} else {
    git -C $repo worktree add --detach $worktree origin/main   # your default branch
    if ($LASTEXITCODE -ne 0) { throw 'git worktree add failed' }
}
$deadline = (Get-Date).AddSeconds(30)
while (-not (Test-Path -LiteralPath (Join-Path $worktree '.git'))) {
    if ((Get-Date) -gt $deadline) { throw 'the worktree folder did not appear' }
    Start-Sleep -Milliseconds 200
}
# Keep the exit file, the process record and the log out of git: the worktree's exclude file names them.
$exclude = (git -C $worktree rev-parse --git-path info/exclude).Trim()
if (-not [IO.Path]::IsPathRooted($exclude)) { $exclude = Join-Path $worktree $exclude }
New-Item -ItemType Directory -Force -Path (Split-Path $exclude -Parent) | Out-Null
if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session-exit'))) {
    Add-Content -LiteralPath $exclude -Value '.agk-session-exit'
}
if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session-pid'))) {
    Add-Content -LiteralPath $exclude -Value '.agk-session-pid'
}
if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session.log'))) {
    Add-Content -LiteralPath $exclude -Value '.agk-session.log'
}

# 2. The prompt and the wrapper, in a folder of the session under the long temporary path.
$longTemp = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
$work = Join-Path $longTemp "agk-$session"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$promptFile = Join-Path $work 'prompt.txt'
Set-Content -LiteralPath $promptFile -Value $prompt -Encoding utf8
# The job's kind, item and head (SPEC-0064 rule 3), from AGK_JOB_KIND, AGK_ITEM and AGK_HEAD, for the record.
$Kind = $env:AGK_JOB_KIND; $Item = $env:AGK_ITEM; $Head = $env:AGK_HEAD
Set-Content -LiteralPath (Join-Path $work 'job.txt') -Encoding utf8 -Value "kind=$Kind", "item=$Item", "head=$Head"
# A tab only with [autopilot] show_jobs = true, which launch.py passes as AGK_SHOW_JOBS (SPEC-0064 rule 5).
$show = $env:AGK_SHOW_JOBS -eq 'true'
Set-Content -LiteralPath (Join-Path $work 'show.txt') -Encoding utf8 -Value $(if ($show) { 'true' } else { 'false' })
$wrapper = Join-Path $work 'run.ps1'
Set-Content -LiteralPath $wrapper -Encoding utf8 -Value @'
param($Worktree, $PromptFile, $LongTemp, $Session, $Brief, $Model, $Effort)
# The job's environment: PATH fresh, TEMP long, no inherited child-session marker.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')
$env:TEMP = $LongTemp
$env:TMP = $LongTemp
$env:TMPDIR = $LongTemp
Remove-Item Env:CLAUDE_CODE_CHILD_SESSION -ErrorAction SilentlyContinue
$env:AGK_SESSION = $Session
$env:AGK_BRIEF = $Brief
Set-Location -LiteralPath $Worktree
# The process record before the first turn: this wrapper's process holds claude.
$started = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
$job = @(Get-Content -LiteralPath (Join-Path (Split-Path $PromptFile -Parent) 'job.txt'))
Set-Content -LiteralPath (Join-Path $Worktree '.agk-session-pid') -Value (@("session=$Session", "pid=$PID", "started_utc=$started", "brief=$Brief") + $job)
$prompt = Get-Content -LiteralPath $PromptFile -Raw
# The tier's model name and effort: no flag without a model (verify: the flags are claude's).
$flags = @()
if ($Model) { $flags += '--model', $Model; if ($Effort) { $flags += '--effort', $Effort } }
# Headless (-p), the output in the log; with show_jobs also in the tab (verify: the runtime's headless flag on Windows).
$log = Join-Path $Worktree '.agk-session.log'
$shown = (Get-Content -LiteralPath (Join-Path (Split-Path $PromptFile -Parent) 'show.txt') -ErrorAction SilentlyContinue) -eq 'true'
try {
    if ($shown) { & claude @flags -p $prompt 2>&1 | Tee-Object -FilePath $log } else { & claude @flags -p $prompt *> $log }
    $code = $LASTEXITCODE
} catch { $code = 1 }
if ($null -eq $code) { $code = 1 }
$at = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
Set-Content -LiteralPath (Join-Path $Worktree '.agk-session-exit') -Value "exit_code=$code", "ended_utc=$at"
exit $code
'@

# 3. The job, only now that the worktree exists: hidden, with no Windows Terminal, or with show_jobs a tab that closes
#    when it ends. The model and effort follow as arguments, never empty ones (verify: Start-Process's quoting).
$extra = @()
if ($env:AGK_MODEL) { $extra += $env:AGK_MODEL; if ($env:AGK_EFFORT) { $extra += $env:AGK_EFFORT } }
if ($show) {
    wt -w 0 new-tab --profile "AGK builder" --title $session -d $worktree `
        pwsh -NoProfile -File $wrapper $worktree $promptFile $longTemp $session $brief @extra
} else {
    $quoted = @($wrapper, $worktree, $promptFile, $longTemp, $session, $brief) + $extra | ForEach-Object { '"' + $_ + '"' }
    Start-Process -FilePath pwsh -WindowStyle Hidden -WorkingDirectory $worktree -ArgumentList (@('-NoProfile', '-File') + $quoted)
}

