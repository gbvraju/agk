# scripts/start-session-windows.ps1: one Windows Terminal tab per session, in its own worktree.
$ErrorActionPreference = 'Stop'
$session = $env:AGK_SESSION
$brief = $env:AGK_BRIEF
if (-not $session) { throw 'AGK_SESSION is not set' }
$prompt = [Console]::In.ReadToEnd()

# 1. The worktree first, and wait until its folder exists.
$repo = (git rev-parse --show-toplevel).Trim()
$worktree = Join-Path (Split-Path $repo -Parent) "agk-$session"
git -C $repo fetch --quiet origin
git -C $repo worktree add --detach $worktree origin/{{default_branch}}   # your default branch
if ($LASTEXITCODE -ne 0) { throw 'git worktree add failed' }
$deadline = (Get-Date).AddSeconds(30)
while (-not (Test-Path -LiteralPath (Join-Path $worktree '.git'))) {
    if ((Get-Date) -gt $deadline) { throw 'the worktree folder did not appear' }
    Start-Sleep -Milliseconds 200
}
# Keep the exit file out of git: the worktree's exclude file names it.
$exclude = (git -C $worktree rev-parse --git-path info/exclude).Trim()
if (-not [IO.Path]::IsPathRooted($exclude)) { $exclude = Join-Path $worktree $exclude }
New-Item -ItemType Directory -Force -Path (Split-Path $exclude -Parent) | Out-Null
if (-not ((Test-Path -LiteralPath $exclude) -and (Select-String -LiteralPath $exclude -SimpleMatch -Quiet '.agk-session-exit'))) {
    Add-Content -LiteralPath $exclude -Value '.agk-session-exit'
}

# 2. The prompt and the wrapper, in a folder of the session under the long temporary path.
$longTemp = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
$work = Join-Path $longTemp "agk-$session"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$promptFile = Join-Path $work 'prompt.txt'
Set-Content -LiteralPath $promptFile -Value $prompt -Encoding utf8
$wrapper = Join-Path $work 'run.ps1'
Set-Content -LiteralPath $wrapper -Encoding utf8 -Value @'
param($Worktree, $PromptFile, $LongTemp, $Session, $Brief)
# The tab's environment: PATH fresh, TEMP long, no inherited child-session marker.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')
$env:TEMP = $LongTemp
$env:TMP = $LongTemp
$env:TMPDIR = $LongTemp
Remove-Item Env:CLAUDE_CODE_CHILD_SESSION -ErrorAction SilentlyContinue
$env:AGK_SESSION = $Session
$env:AGK_BRIEF = $Brief
Set-Location -LiteralPath $Worktree
$prompt = Get-Content -LiteralPath $PromptFile -Raw
try { & claude $prompt; $code = $LASTEXITCODE } catch { $code = 1 }
if ($null -eq $code) { $code = 1 }
$at = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
Set-Content -LiteralPath (Join-Path $Worktree '.agk-session-exit') -Value "exit_code=$code", "ended_utc=$at"
exit $code
'@

# 3. The tab, only now that the worktree exists.
wt -w 0 new-tab --profile "AGK builder" --title $session -d $worktree `
    pwsh -NoProfile -File $wrapper $worktree $promptFile $longTemp $session $brief
