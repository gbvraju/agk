<#
.SYNOPSIS
  Moves this project's AI workforce (steward, conductor, builders) into WSL 2 on this Windows machine, and back.

.DESCRIPTION
  The machine work of /agk:wsl (brief #1376, ADR-0577), from the co-owner's host script. It is kit-only: run it from
  the plugin root, in the project's Windows checkout; it is never installed into a project. Every step checks first and
  skips what is done, so a stopped run resumes where it stopped. It ends with one table of steps marked done, skipped,
  waiting or failed; -Json prints that table as JSON instead, which the skill reads.

  It never asks for, stores or prints a password or a sign-in secret: the GitHub and Claude sign-ins are the normal
  browser sign-ins, which the person does when a step says waiting.

  Forms:
    wsl_setup.ps1                     set up, or resume a stopped run
    wsl_setup.ps1 -Status             run the checks only and change nothing
    wsl_setup.ps1 -InstallWatchdog    also move the watchdog into WSL (after the adapter pull request merged)
    wsl_setup.ps1 -Back               re-enable the Windows watchdog task and disable the WSL one
    -Engine podman|docker|docker-desktop  the container engine (brief #1379, ADR-0579): Podman by default; Docker
                                      Engine inside WSL; or Docker Desktop's WSL integration (detected, never
                                      installed). -DockerRootless uses Docker's rootless mode instead of the docker group.

.EXAMPLE
  pwsh -NoProfile -File scripts/agk/wsl_setup.ps1 -Json
#>
[CmdletBinding()]
param(
    [string] $RepoUrl = '',                # default: the origin of the checkout in the current folder
    [string] $GitName = '',                # default: git config user.name
    [string] $GitEmail = '',               # default: git config user.email
    [string] $Distro = 'Ubuntu-24.04',
    [string] $ProjectName = '',            # folder name inside ~/work; default: the repository's name
    [int]    $WslMemoryGB = 0,             # default: total memory less 5 GB, at least 6
    [int]    $WslSwapGB = 4,
    [string] $CorpCaFile = '',             # optional: a company root certificate (.crt or .cer, PEM or DER)
    [string] $WebDir = '',                 # optional: the folder with the Playwright tests; default: found
    [ValidateSet('podman', 'docker', 'docker-desktop')]
    [string] $Engine = 'podman',
    [switch] $DockerRootless,
    [switch] $SkipPodman,                  # skips the container engine, whichever is chosen
    [switch] $SkipPlaywright,
    [switch] $InstallWatchdog,
    [switch] $Back,
    [switch] $Status,
    [switch] $Json
)

# Native commands write progress to stderr; Windows PowerShell 5.1 would turn that into errors under 'Stop', so every
# native call is judged by its exit code instead.
$ErrorActionPreference = 'Continue'
$script:Results = [System.Collections.Generic.List[object]]::new()
$script:Restart = $false
$script:ProjectDir = ''
$script:MemoryGB = 0
$script:Doctor = ''
$script:WebPath = ''
$script:LinuxUser = ''
$script:Engines = $null
$WslTask = 'AGK conductor watchdog (WSL)'
$WindowsTask = 'AGK conductor watchdog'

function Say([string]$Text, [string]$Color = 'Gray') {
    if (-not $Json) { Write-Host $Text -ForegroundColor $Color }
}

function Add-Result([string]$Name, [string]$State, [string]$Note = '') {
    $script:Results.Add([pscustomobject]@{ Step = $Name; Result = $State; Note = $Note })
    $color = @{ done = 'Green'; skipped = 'DarkGray'; waiting = 'Yellow'; failed = 'Red' }[$State]
    Say ("[{0,-7}] {1}{2}" -f $State, $Name, $(if ($Note) { " - $Note" } else { '' })) $color
}

# One step: the check first; the action only when the check fails and this is not -Status; the check again after it.
# The action returns its note (a plain sentence), never a native command's output.
function Invoke-Step {
    param([string]$Name, [scriptblock]$Done, [scriptblock]$Do, [string]$Otherwise = 'failed')
    if (& $Done) { Add-Result $Name $(if ($Status) { 'done' } else { 'skipped' }); return $true }
    if ($Status) { Add-Result $Name 'waiting' 'to do'; return $false }
    $note = [string](& $Do | Select-Object -Last 1)
    if (& $Done) { Add-Result $Name 'done' $note; return $true }
    Add-Result $Name $Otherwise $note
    return $false
}

function Get-WatchdogState {
    $wslOn = $false; $winOn = $false
    try {
        $t = Get-ScheduledTask -TaskName $WslTask -ErrorAction Stop
        $wslOn = $t.State -ne 'Disabled'
    } catch { }
    try {
        $t = Get-ScheduledTask -TaskName $WindowsTask -ErrorAction Stop
        $winOn = $t.State -ne 'Disabled'
    } catch { }
    if ($wslOn -and $winOn) { return 'both' }
    if ($wslOn) { return 'wsl' }
    if ($winOn) { return 'windows' }
    return 'none'
}

function Write-State {
    $state = [ordered]@{
        steps = @($script:Results | ForEach-Object { [ordered]@{ step = $_.Step; result = $_.Result; note = $_.Note } })
        pending = @($script:Results | Where-Object { $_.Result -eq 'waiting' -and $_.Note } | ForEach-Object { "$($_.Step): $($_.Note)" })
        project_dir = $script:ProjectDir
        distro = $Distro
        memory_gb = $script:MemoryGB
        watchdog = (Get-WatchdogState)
        doctor = $script:Doctor
        engine = $Engine
        engines = $script:Engines
    }
    $state | ConvertTo-Json -Depth 5
}

function Finish {
    if ($Json) {
        Write-State
    } else {
        Write-Host ''
        Write-Host 'Summary' -ForegroundColor Cyan
        $script:Results | Format-Table -AutoSize | Out-String | Write-Host
        $waiting = @($script:Results | Where-Object { $_.Result -eq 'waiting' -and $_.Note })
        if ($waiting.Count) {
            Write-Host 'Still needs you (then run /agk:wsl again; it skips what is done):' -ForegroundColor Yellow
            $waiting | ForEach-Object { Write-Host "  * $($_.Note)" }
        }
        if ($script:ProjectDir) { Write-Host "Your project in WSL: $($script:ProjectDir)" }
    }
    $failed = @($script:Results | Where-Object { $_.Result -eq 'failed' })
    if ($failed.Count) { exit 1 }
    exit 0
}

# Write a bash script to a Windows temp file with LF endings and no BOM, and return its path inside WSL.
function Write-LinuxScript([string]$Name, [string]$Body) {
    $path = Join-Path $env:TEMP $Name
    [IO.File]::WriteAllText($path, ($Body -replace "`r`n", "`n"), (New-Object Text.UTF8Encoding $false))
    return (& wsl.exe -d $Distro -- wslpath -a ($path -replace '\\', '/')).Trim()
}

# Run one Linux phase and turn its `AGK_STEP=<id>|<result>|<note>` lines into results.
function Invoke-Phase([string]$User, [string]$Path, [string[]]$Environment) {
    $lines = & wsl.exe -d $Distro -u $User -- env @Environment bash $Path
    foreach ($line in $lines) {
        if ($line -match '^AGK_STEP=([a-z_]+)\|([a-z]+)\|(.*)$') { Add-Result $Matches[1] $Matches[2] $Matches[3] }
        elseif ($line -match '^AGK_WEB=(.+)$') { $script:WebPath = $Matches[1] }
        elseif ($line -match '^AGK_DOCTOR=(.*)$') { $script:Doctor = $Matches[1] }
        elseif ($line -match '^AGK_ENGINE_VERSION=(.*)$') { $script:Engines.wsl_version = $Matches[1] }
        else { Say "    $line" 'DarkGray' }
    }
}

function Test-WslTasks([bool]$WantWsl) {
    $wsl = Get-ScheduledTask -TaskName $WslTask -ErrorAction SilentlyContinue
    $win = Get-ScheduledTask -TaskName $WindowsTask -ErrorAction SilentlyContinue
    if ($WantWsl) { return ($wsl -and $wsl.State -ne 'Disabled') -and (-not $win -or $win.State -eq 'Disabled') }
    return (-not $wsl -or $wsl.State -eq 'Disabled') -and (-not $win -or $win.State -ne 'Disabled')
}

function Set-WslWatchdog {
    $arg = "-d $Distro -- bash -lc `"cd $($script:ProjectDir) && git fetch -q origin && python3 scripts/agk/conductor.py watchdog --pass`""
    $action = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument $arg
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    try {
        Register-ScheduledTask -TaskName $WslTask -Action $action -Trigger $trigger -Settings $settings -Force -ErrorAction Stop | Out-Null
        Enable-ScheduledTask -TaskName $WslTask -ErrorAction SilentlyContinue | Out-Null
        if (Get-ScheduledTask -TaskName $WindowsTask -ErrorAction SilentlyContinue) {
            Disable-ScheduledTask -TaskName $WindowsTask | Out-Null
        }
        return "$WslTask every 10 minutes; $WindowsTask disabled (not deleted)"
    } catch { return $_.Exception.Message }
}

function Set-WindowsWatchdog {
    if (Get-ScheduledTask -TaskName $WslTask -ErrorAction SilentlyContinue) { Disable-ScheduledTask -TaskName $WslTask | Out-Null }
    if (Get-ScheduledTask -TaskName $WindowsTask -ErrorAction SilentlyContinue) { Enable-ScheduledTask -TaskName $WindowsTask | Out-Null }
    return "$WindowsTask re-enabled; $WslTask disabled (not deleted)"
}

Say ''
Say 'AGK in WSL 2' 'Cyan'
Say '------------' 'Cyan'

# --- Windows and WSL -----------------------------------------------------------------------------------------------
$build = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber
if (-not (Invoke-Step -Name 'windows' -Done { $build -ge 19041 } -Do { "Windows build $build is too old for WSL 2; Windows 10 2004 (19041) or later is needed" })) { Finish }

# --- the container engines on Windows, read only (brief #1379): versions and volumes, nothing moved ----------------
function Get-EngineOutput([string]$Exe, [string[]]$Arguments) {
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return @() }
    $out = & $Exe @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($out | Where-Object { $_ })
}
$family = if ($Engine -eq 'podman') { 'podman' } else { 'docker' }
$desktopExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
function Test-DesktopRunning { [bool](Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue) }
function Test-PodmanMachine { [bool]((Get-EngineOutput 'podman' @('machine', 'list', '--format', '{{.Running}}')) -match 'true') }
$script:Engines = [ordered]@{
    desktop = (Test-Path $desktopExe)
    desktop_running = (Test-DesktopRunning)
    windows_docker = [string]((Get-EngineOutput 'docker' @('version', '--format', '{{.Server.Version}}')) | Select-Object -First 1)
    windows_podman = [string]((Get-EngineOutput 'podman' @('version', '--format', '{{.Client.Version}}')) | Select-Object -First 1)
    volumes = @(Get-EngineOutput $family @('volume', 'ls', '--format', '{{.Name}}'))
    wsl_version = ''
}
# After the move the Windows engine of the same family is stopped, never removed; back starts it again.
function Test-WindowsEngine([bool]$WantRunning) {
    if ($Engine -eq 'docker-desktop' -or $SkipPodman) { return $true }
    if ($Engine -eq 'podman') { if (-not $script:Engines.windows_podman) { return $true }; return (Test-PodmanMachine) -eq $WantRunning }
    if (-not $script:Engines.desktop) { return $true }
    return (Test-DesktopRunning) -eq $WantRunning
}
function Stop-WindowsEngine {
    if ($Engine -eq 'podman') { & podman machine stop *> $null; return 'the Podman machine on Windows is stopped (not removed)' }
    return 'quit Docker Desktop (it stays installed) so one engine holds the ports'
}
function Start-WindowsEngine {
    if ($Engine -eq 'podman') { & podman machine start *> $null; return 'the Podman machine on Windows started' }
    & wsl.exe -d $Distro -u root -- systemctl stop docker.service docker.socket *> $null
    Start-Process $desktopExe
    return 'Docker Engine inside WSL stopped (still installed), then Docker Desktop started'
}

if ($Back) {
    Invoke-Step -Name 'watchdog_back' -Done { Test-WslTasks $false } -Do { Set-WindowsWatchdog } | Out-Null
    Invoke-Step -Name 'windows_engine_back' -Done { Test-WindowsEngine $true } -Do { Start-WindowsEngine } | Out-Null
    Finish
}

if (-not (Invoke-Step -Name 'wsl' -Done { & wsl.exe --status *> $null; $LASTEXITCODE -eq 0 } -Do { 'in an Administrator PowerShell run  wsl --install --no-distribution  then restart Windows' } -Otherwise 'waiting')) { Finish }

function Get-Distros { (& wsl.exe -l -q) -replace "`0", '' | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
if (-not (Invoke-Step -Name 'distro' -Done { (Get-Distros) -contains $Distro } -Do { Start-Process wsl.exe -ArgumentList "--install -d $Distro"; "a window installs $Distro and asks you for a new Linux user name: create it, close the window, then run /agk:wsl again" } -Otherwise 'waiting')) { Finish }

function Test-Wsl2 { ((& wsl.exe -l -v) -replace "`0", '') -match "^\*?\s*$([regex]::Escape($Distro))\s+\S+\s+2\s*$" }
if (-not (Invoke-Step -Name 'wsl2' -Done { [bool](Test-Wsl2) } -Do { & wsl.exe --set-version $Distro 2 *> $null; "converted $Distro to WSL 2" })) { Finish }

function Get-LinuxUser { [string]((& wsl.exe -d $Distro -- whoami) | Select-Object -First 1) }
if (-not (Invoke-Step -Name 'linux_user' -Done { $u = (Get-LinuxUser).Trim(); $u -and $u -ne 'root' } -Do { "open $Distro once from the Start menu, create your own Linux user, then run /agk:wsl again" } -Otherwise 'waiting')) { Finish }
$script:LinuxUser = (Get-LinuxUser).Trim()

if (-not $RepoUrl) { $RepoUrl = [string](& git remote get-url origin 2>$null) }
if (-not $GitName) { $GitName = [string](& git config user.name 2>$null) }
if (-not $GitEmail) { $GitEmail = [string](& git config user.email 2>$null) }
$RepoUrl = $RepoUrl.Trim()
$repoName = ($RepoUrl -replace '\.git$', '' -replace '^git@github\.com:', 'https://github.com/').TrimEnd('/')
$ownerRepo = ($repoName -split '/')[-2..-1] -join '/'
if (-not $ProjectName) { $ProjectName = ($ownerRepo -split '/')[-1] }
$script:ProjectDir = "/home/$($script:LinuxUser)/work/$ProjectName"

# --- .wslconfig ----------------------------------------------------------------------------------------------------
$totalGB = [math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$script:MemoryGB = if ($WslMemoryGB -gt 0) { $WslMemoryGB } else { [math]::Max(6, $totalGB - 5) }
$lines = @('[wsl2]', "memory=$($script:MemoryGB)GB", "swap=${WslSwapGB}GB")
if ($build -ge 22621) { $lines += @('networkingMode=mirrored', 'autoProxy=true', 'dnsTunneling=true') }
$lines += @('', '[experimental]', 'autoMemoryReclaim=gradual', 'sparseVhd=true')
$wanted = ($lines -join "`r`n") + "`r`n"
$cfg = Join-Path $env:USERPROFILE '.wslconfig'
function Test-WslConfig { (Test-Path $cfg) -and ((Get-Content $cfg -Raw) -eq $wanted) }
function Set-WslConfig {
    if (Test-Path $cfg) { Copy-Item $cfg "$cfg.bak-$(Get-Date -Format yyyyMMddHHmmss)" }
    [IO.File]::WriteAllText($cfg, $wanted, (New-Object Text.UTF8Encoding $false))
    $script:Restart = $true
    return "memory $($script:MemoryGB) of $totalGB GB (an earlier file is kept as a backup)"
}
Invoke-Step -Name 'wslconfig' -Done { Test-WslConfig } -Do { Set-WslConfig } | Out-Null

# --- as root inside WSL --------------------------------------------------------------------------------------------
$caLinux = ''
if ($CorpCaFile) {
    if (-not (Test-Path $CorpCaFile)) { Add-Result 'company_ca' 'failed' 'the certificate file named by -CorpCaFile does not exist'; Finish }
    $caLinux = (& wsl.exe -d $Distro -- wslpath -a ((Resolve-Path $CorpCaFile).Path -replace '\\', '/')).Trim()
}
$rootScript = @'
#!/usr/bin/env bash
set -uo pipefail
exec 2>&1
export DEBIAN_FRONTEND=noninteractive
CA_FILE=/usr/local/share/ca-certificates/agk-company-root.crt

# step ID CHECK DO [RESULT]: the check first; the action only when it fails; RESULT (failed) when it still fails.
step() {
  local id="$1" check="$2" act="$3" otherwise="${4:-failed}" note
  if "$check"; then
    if [ "${AGK_CHECK_ONLY:-0}" = 1 ]; then echo "AGK_STEP=$id|done|"; else echo "AGK_STEP=$id|skipped|"; fi
    return 0
  fi
  if [ "${AGK_CHECK_ONLY:-0}" = 1 ]; then echo "AGK_STEP=$id|waiting|to do"; return 1; fi
  note="$("$act" 2>&1 | tail -1 | tr -d '|')"
  if "$check"; then echo "AGK_STEP=$id|done|"; return 0; fi
  echo "AGK_STEP=$id|$otherwise|$note"; return 1
}

want_conf() { printf '[boot]\nsystemd=true\n\n[interop]\nappendWindowsPath=false\n\n[user]\ndefault=%s\n' "$AGK_USER"; }
has_wsl_conf() { [ "$(cat /etc/wsl.conf 2>/dev/null)" = "$(want_conf)" ]; }
set_wsl_conf() {
  [ -f /etc/wsl.conf ] && cp /etc/wsl.conf "/etc/wsl.conf.bak-$(date +%Y%m%d%H%M%S)"
  want_conf > /etc/wsl.conf
}

has_company_ca() { [ -z "${AGK_CA:-}" ] || [ -s "$CA_FILE" ]; }
set_company_ca() {
  if openssl x509 -in "$AGK_CA" -noout 2>/dev/null; then cp "$AGK_CA" "$CA_FILE"
  else openssl x509 -inform der -in "$AGK_CA" -out "$CA_FILE"; fi
  update-ca-certificates >/dev/null
  printf 'export NODE_EXTRA_CA_CERTS=%s\nexport REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt\n' "$CA_FILE" \
    > /etc/profile.d/agk-ca.sh
}

PACKAGES="git make python3 python3-pip python3-venv curl jq unzip ca-certificates gnupg openssl uidmap slirp4netns fuse-overlayfs procps"
has_packages() { for p in $PACKAGES; do dpkg -s "$p" >/dev/null 2>&1 || return 1; done; }
set_packages() {
  apt-get update -qq || { echo "apt-get update failed: a company proxy or certificate is the usual cause"; return 1; }
  # shellcheck disable=SC2086
  apt-get install -y -qq $PACKAGES >/dev/null
}

has_gh_cli() { command -v gh >/dev/null; }
set_gh_cli() {
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    || { echo "the GitHub CLI download failed: a company certificate may be needed"; return 1; }
  chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update -qq && apt-get install -y -qq gh >/dev/null
}

has_nodejs() { command -v node >/dev/null && [ "$(node -v | cut -d. -f1 | tr -d v)" -ge 20 ]; }
set_nodejs() {
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null \
    || { echo "the Node.js download failed: a company certificate may be needed"; return 1; }
  apt-get install -y -qq nodejs >/dev/null
}

has_podman() {
  [ "${AGK_PODMAN:-1}" = 0 ] || [ "${AGK_ENGINE:-podman}" != podman ] && return 0
  command -v podman >/dev/null && grep -q "^$AGK_USER:" /etc/subuid && grep -q "^$AGK_USER:" /etc/subgid
}
set_podman() {
  command -v podman >/dev/null || apt-get install -y -qq podman >/dev/null
  grep -q "^$AGK_USER:" /etc/subuid || usermod --add-subuids 100000-165535 "$AGK_USER"
  grep -q "^$AGK_USER:" /etc/subgid || usermod --add-subgids 100000-165535 "$AGK_USER"
}

step wsl_conf has_wsl_conf set_wsl_conf
step company_ca has_company_ca set_company_ca
step packages has_packages set_packages
step gh_cli has_gh_cli set_gh_cli
step nodejs has_nodejs set_nodejs
# Docker Engine from Docker's own repository (verify: the names on Docker's install page), with the Compose plugin.
has_docker() {
  [ "${AGK_PODMAN:-1}" = 0 ] || [ "${AGK_ENGINE:-podman}" != docker ] && return 0
  command -v docker >/dev/null && docker compose version >/dev/null 2>&1 || return 1
  [ "${AGK_ROOTLESS:-0}" = 1 ] && return 0
  id -nG "$AGK_USER" | grep -qw docker && systemctl is-enabled docker >/dev/null 2>&1
}
set_docker() {
  # shellcheck disable=SC1091
  . /etc/os-release
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc \
    || { echo "the Docker download failed: a company certificate may be needed"; return 1; }
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq && apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
    docker-compose-plugin docker-ce-rootless-extras >/dev/null || return 1
  if [ "${AGK_ROOTLESS:-0}" = 1 ]; then
    systemctl disable --now docker.service docker.socket >/dev/null 2>&1
    echo "rootless mode: the step docker_rootless sets it up for your user"
  else
    usermod -aG docker "$AGK_USER"
    systemctl enable --now docker >/dev/null 2>&1 || echo "systemd starts Docker after WSL restarts: run /agk:wsl again"
  fi
}

step podman has_podman set_podman
step docker has_docker set_docker
exit 0
'@
# Never two engines on one port: Docker Engine inside WSL waits until Docker Desktop's engine is stopped.
if (-not (Invoke-Step -Name 'one_engine' -Done { $Engine -ne 'docker' -or -not (Test-DesktopRunning) } -Do { 'Docker Desktop is running: quit it (it stays installed) so one engine holds the ports, then run /agk:wsl again' } -Otherwise 'waiting')) { Finish }
$check = if ($Status) { '1' } else { '0' }
$rootless = if ($DockerRootless) { '1' } else { '0' }
$podmanFlag = if ($SkipPodman) { '0' } else { '1' }
$playFlag = if ($SkipPlaywright) { '0' } else { '1' }
Say 'System packages inside WSL (a few minutes on the first run)...'
$rootLinux = Write-LinuxScript 'agk-wsl-root.sh' $rootScript
Invoke-Phase 'root' $rootLinux @("AGK_USER=$($script:LinuxUser)", "AGK_CA=$caLinux", "AGK_PODMAN=$podmanFlag", "AGK_ENGINE=$Engine", "AGK_ROOTLESS=$rootless", "AGK_CHECK_ONLY=$check")
if ($script:Results | Where-Object { $_.Step -eq 'wsl_conf' -and $_.Result -eq 'done' -and -not $Status }) { $script:Restart = $true }

Invoke-Step -Name 'restart' -Done { -not $script:Restart } -Do { & wsl.exe --shutdown; Start-Sleep -Seconds 8; $script:Restart = $false; 'WSL restarted so the new settings apply' } | Out-Null

# Docker Desktop's WSL integration, when chosen: Desktop is detected, never installed.
function Test-DesktopWsl { & wsl.exe -d $Distro -u $script:LinuxUser -- docker version *> $null; $LASTEXITCODE -eq 0 }
function Set-DesktopWsl {
    if (-not $script:Engines.desktop) { return 'Docker Desktop is not installed here: run /agk:wsl with -Engine docker or podman' }
    return "in Docker Desktop, Settings, Resources, WSL integration, turn on $Distro, then run /agk:wsl again"
}
Invoke-Step -Name 'desktop_wsl' -Done { $Engine -ne 'docker-desktop' -or $SkipPodman -or (Test-DesktopWsl) } -Do { Set-DesktopWsl } -Otherwise 'waiting' | Out-Null

# --- the GitHub sign-in: the normal browser sign-in ----------------------------------------------------------------
function Test-GitHub { & wsl.exe -d $Distro -u $script:LinuxUser -- gh auth status *> $null; $LASTEXITCODE -eq 0 }
function Set-GitHub {
    if (-not $Json) {
        Write-Host 'GitHub sign-in: copy the one-time code shown below, open the address in your Windows browser and approve.' -ForegroundColor Yellow
        & wsl.exe -d $Distro -u $script:LinuxUser -- gh auth login --hostname github.com --git-protocol https --web | Out-Host
        & wsl.exe -d $Distro -u $script:LinuxUser -- gh auth setup-git | Out-Null
    }
    return 'open the AGK shell (WSL) tab, run  gh auth login --web  and approve in your browser'
}
Invoke-Step -Name 'github_signin' -Done { Test-GitHub } -Do { Set-GitHub } -Otherwise 'waiting' | Out-Null

# --- as you inside WSL ---------------------------------------------------------------------------------------------
$userScript = @'
#!/usr/bin/env bash
set -uo pipefail
exec 2>&1
export PATH="$HOME/.local/bin:$PATH"
[ "${AGK_ROOTLESS:-0}" = 1 ] && export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
[ -f /etc/profile.d/agk-ca.sh ] && . /etc/profile.d/agk-ca.sh
BASE="$(dirname "$AGK_DIR")"

# step ID CHECK DO [RESULT]: the check first; the action only when it fails; RESULT (failed) when it still fails.
step() {
  local id="$1" check="$2" act="$3" otherwise="${4:-failed}" note
  if "$check"; then
    if [ "${AGK_CHECK_ONLY:-0}" = 1 ]; then echo "AGK_STEP=$id|done|"; else echo "AGK_STEP=$id|skipped|"; fi
    return 0
  fi
  if [ "${AGK_CHECK_ONLY:-0}" = 1 ]; then echo "AGK_STEP=$id|waiting|to do"; return 1; fi
  note="$("$act" 2>&1 | tail -1 | tr -d '|')"
  if "$check"; then echo "AGK_STEP=$id|done|"; return 0; fi
  echo "AGK_STEP=$id|$otherwise|$note"; return 1
}

has_git_config() {
  [ "$(git config --global user.name)" = "$AGK_GIT_NAME" ] && [ "$(git config --global user.email)" = "$AGK_GIT_EMAIL" ] \
    && [ "$(git config --global core.autocrlf)" = input ]
}
set_git_config() {
  git config --global user.name "$AGK_GIT_NAME"
  git config --global user.email "$AGK_GIT_EMAIL"
  git config --global core.autocrlf input
  git config --global init.defaultBranch main
  git config --global pull.ff only
}

has_claude_code() { command -v claude >/dev/null; }
set_claude_code() {
  curl -fsSL https://claude.ai/install.sh | bash >/dev/null 2>&1
  grep -q 'HOME/.local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
  echo "Claude Code did not install: run  curl -fsSL https://claude.ai/install.sh | bash  in the AGK shell"
}

has_clone() { [ -d "$AGK_DIR/.git" ]; }
set_clone() {
  gh auth status >/dev/null 2>&1 || { echo "after the GitHub sign-in, run /agk:wsl again"; return 1; }
  mkdir -p "$BASE"
  gh repo clone "$AGK_REPO" "$AGK_DIR" -- --quiet && gh auth setup-git >/dev/null
}

has_worktrees() { [ -d "$BASE/agk-conductor" ] && [ -d "$BASE/agk-steward" ]; }
set_worktrees() {
  has_clone || { echo "the clone comes first"; return 1; }
  cd "$AGK_DIR" || return 1
  git fetch --quiet origin
  for wt in agk-conductor agk-steward; do
    [ -d "$BASE/$wt" ] || git worktree add --quiet --detach "$BASE/$wt" origin/HEAD
  done
}

has_kit_tools() {
  [ -f "$AGK_DIR/config/ci-tools.txt" ] || return 1
  [ "$(cat "$HOME/.cache/agk/ci-tools.sha" 2>/dev/null)" = "$(sha256sum "$AGK_DIR/config/ci-tools.txt" | cut -d' ' -f1)" ]
}
set_kit_tools() {
  has_clone || { echo "the clone comes first"; return 1; }
  python3 -m pip install --user --quiet --break-system-packages -r "$AGK_DIR/config/ci-tools.txt" >/dev/null 2>&1 \
    || python3 -m pip install --user --quiet -r "$AGK_DIR/config/ci-tools.txt" >/dev/null 2>&1 \
    || { echo "run  python3 -m pip install --user -r config/ci-tools.txt  in the project"; return 1; }
  mkdir -p "$HOME/.cache/agk"
  sha256sum "$AGK_DIR/config/ci-tools.txt" | cut -d' ' -f1 > "$HOME/.cache/agk/ci-tools.sha"
}

# The project folder trusted for Claude Code, so the role guards (hooks) run in every session of this clone (verify).
has_trust() {
  python3 - "$AGK_DIR" <<'PY'
import json, os, sys
p = os.path.expanduser("~/.claude.json")
d = json.load(open(p)) if os.path.exists(p) else {}
sys.exit(0 if d.get("projects", {}).get(sys.argv[1], {}).get("hasTrustDialogAccepted") else 1)
PY
}
set_trust() {
  has_clone || { echo "the clone comes first"; return 1; }
  python3 - "$AGK_DIR" <<'PY'
import json, os, sys
p = os.path.expanduser("~/.claude.json")
d = json.load(open(p)) if os.path.exists(p) else {}
d.setdefault("projects", {}).setdefault(sys.argv[1], {})["hasTrustDialogAccepted"] = True
json.dump(d, open(p, "w"), indent=2)
PY
}

has_plugin() { command -v claude >/dev/null && claude plugin list 2>/dev/null | grep -q 'agk'; }
set_plugin() {
  claude plugin marketplace add gbvraju/agk >/dev/null 2>&1
  claude plugin install agk@agk >/dev/null 2>&1
  echo "after the Claude sign-in run  claude plugin marketplace add gbvraju/agk  then  claude plugin install agk@agk"
}

web_dir() {
  local web="${AGK_WEBDIR:-}"
  if [ -z "$web" ] && [ -d "$AGK_DIR" ]; then
    web="$(cd "$AGK_DIR" && grep -rl --include=package.json '"@playwright/test"' . 2>/dev/null | grep -v node_modules | head -1 | xargs -r dirname)"
  fi
  [ -n "$web" ] && [ -f "$AGK_DIR/$web/package.json" ] && printf '%s' "$AGK_DIR/$web"
}
has_playwright() {
  [ "${AGK_PLAYWRIGHT:-1}" = 0 ] && return 0
  [ -z "$(web_dir)" ] && return 0
  ls -d "$HOME"/.cache/ms-playwright/chromium-* >/dev/null 2>&1
}
set_playwright() {
  local web; web="$(web_dir)"
  cd "$web" || return 1
  { [ -f package-lock.json ] && npm ci --silent || npm install --silent; } >/dev/null 2>&1
  npx playwright install chromium >/dev/null 2>&1 || echo "in $web run  npm ci  then  npx playwright install chromium"
}

has_podman_check() { [ "${AGK_PODMAN:-1}" = 0 ] || [ "${AGK_ENGINE:-podman}" != podman ] || podman info >/dev/null 2>&1; }
set_podman_check() { podman system migrate >/dev/null 2>&1; echo "run  podman info  in the AGK shell to see the error"; }

step git_config has_git_config set_git_config
step claude_code has_claude_code set_claude_code
step clone has_clone set_clone waiting
step worktrees has_worktrees set_worktrees waiting
step kit_tools has_kit_tools set_kit_tools
step trust has_trust set_trust waiting
step plugin has_plugin set_plugin waiting
step playwright has_playwright set_playwright
engine_cmd() { if [ "${AGK_ENGINE:-podman}" = podman ]; then echo podman; else echo docker; fi; }
has_docker_rootless() {
  { [ "${AGK_ENGINE:-podman}" = docker ] && [ "${AGK_ROOTLESS:-0}" = 1 ]; } || return 0
  systemctl --user is-active docker >/dev/null 2>&1 && grep -q DOCKER_HOST "$HOME/.bashrc"
}
set_docker_rootless() {
  dockerd-rootless-setuptool.sh install >/dev/null 2>&1 \
    || { echo "run  dockerd-rootless-setuptool.sh install  in the AGK shell"; return 1; }
  grep -q DOCKER_HOST "$HOME/.bashrc" || echo "export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock" >> "$HOME/.bashrc"
}
# One container and one compose service with the chosen engine (brief #1379 answer 5).
has_engine_check() {
  [ "${AGK_PODMAN:-1}" = 0 ] && return 0
  local e f; e="$(engine_cmd)"; f="$HOME/.cache/agk/compose-check.yaml"
  mkdir -p "$HOME/.cache/agk"
  printf 'services:\n  check:\n    image: docker.io/library/hello-world\n' > "$f"
  "$e" run --rm docker.io/library/hello-world >/dev/null 2>&1 || return 1
  "$e" compose -f "$f" up --abort-on-container-exit >/dev/null 2>&1 || return 1
  "$e" compose -f "$f" down >/dev/null 2>&1
}
set_engine_check() {
  echo "run  $(engine_cmd) run --rm hello-world  and  $(engine_cmd) compose version  in the AGK shell; podman compose needs podman-compose"
}

step podman_check has_podman_check set_podman_check
step docker_rootless has_docker_rootless set_docker_rootless
step engine_check has_engine_check set_engine_check

web="$(web_dir)"
[ -n "$web" ] && echo "AGK_WEB=$web"
if [ "$(engine_cmd)" = podman ]; then v="$(podman version --format '{{.Client.Version}}' 2>/dev/null)"
else v="$(docker version --format '{{.Server.Version}}' 2>/dev/null)"; fi
echo "AGK_ENGINE_VERSION=$v"
if has_clone; then
  echo "AGK_DOCTOR=$(cd "$AGK_DIR" && python3 scripts/agk/doctor.py 2>&1 | grep '^summary:' | tail -1)"
fi
exit 0
'@
Say 'Your Linux user...'
$userLinux = Write-LinuxScript 'agk-wsl-user.sh' $userScript
Invoke-Phase $script:LinuxUser $userLinux @("AGK_GIT_NAME=$GitName", "AGK_GIT_EMAIL=$GitEmail", "AGK_REPO=$ownerRepo", "AGK_DIR=$($script:ProjectDir)", "AGK_PODMAN=$podmanFlag", "AGK_ENGINE=$Engine", "AGK_ROOTLESS=$rootless", "AGK_PLAYWRIGHT=$playFlag", "AGK_WEBDIR=$WebDir", "AGK_CHECK_ONLY=$check")

# --- the Claude sign-in: the normal browser sign-in (verify: the runtime keeps it in ~/.claude/.credentials.json) ---
function Test-Claude { & wsl.exe -d $Distro -u $script:LinuxUser -- test -s "/home/$($script:LinuxUser)/.claude/.credentials.json"; $LASTEXITCODE -eq 0 }
Invoke-Step -Name 'claude_signin' -Done { Test-Claude } -Do { 'open the AGK shell (WSL) tab, run  claude  once and sign in in your browser' } -Otherwise 'waiting' | Out-Null

# Playwright's system libraries need root; they follow the project's own Playwright version.
function Test-PlaywrightLibs {
    if ($SkipPlaywright -or -not $script:WebPath) { return $true }
    & wsl.exe -d $Distro -u root -- test -f /var/lib/agk/playwright-deps.done; $LASTEXITCODE -eq 0
}
function Set-PlaywrightLibs {
    & wsl.exe -d $Distro -u root -- bash -c "cd '$($script:WebPath)' && npx playwright install-deps chromium >/dev/null 2>&1 && mkdir -p /var/lib/agk && touch /var/lib/agk/playwright-deps.done" | Out-Null
    return 'npx playwright install-deps chromium failed as root'
}
Invoke-Step -Name 'playwright_libs' -Done { Test-PlaywrightLibs } -Do { Set-PlaywrightLibs } | Out-Null

# --- Windows Terminal profiles -------------------------------------------------------------------------------------
$fragDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows Terminal\Fragments\AGK'
$fragFile = Join-Path $fragDir 'agk.json'
$base = "/home/$($script:LinuxUser)/work"
$profiles = @(
    [ordered]@{ name = 'AGK steward (WSL)'; commandline = "wsl.exe -d $Distro --cd $base/agk-steward -- bash -lc `"git fetch -q origin && git checkout -q --detach origin/HEAD; claude --agent steward`"" },
    [ordered]@{ name = 'AGK conductor (WSL)'; commandline = "wsl.exe -d $Distro --cd $base/agk-conductor -- bash -lc `"git fetch -q origin && git checkout -q --detach origin/HEAD; claude --agent conductor`"" },
    [ordered]@{ name = 'AGK shell (WSL)'; commandline = "wsl.exe -d $Distro --cd $($script:ProjectDir)" }
)
$fragment = (@{ profiles = $profiles } | ConvertTo-Json -Depth 4)
function Test-Terminal { (Test-Path $fragFile) -and ((Get-Content $fragFile -Raw) -eq $fragment) }
function Set-Terminal {
    New-Item -ItemType Directory -Force -Path $fragDir | Out-Null
    [IO.File]::WriteAllText($fragFile, $fragment, (New-Object Text.UTF8Encoding $false))
    return 'AGK steward, AGK conductor and AGK shell (restart Windows Terminal to see them)'
}
Invoke-Step -Name 'terminal' -Done { Test-Terminal } -Do { Set-Terminal } | Out-Null

# --- the watchdog: only after the launch-adapter pull request merged ----------------------------------------------
if ($InstallWatchdog) {
    Invoke-Step -Name 'watchdog' -Done { Test-WslTasks $true } -Do { Set-WslWatchdog } | Out-Null
    Invoke-Step -Name 'windows_engine' -Done { Test-WindowsEngine $false } -Do { Stop-WindowsEngine } -Otherwise 'waiting' | Out-Null
}

Finish
