# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
<#
.SYNOPSIS
  /agk:setup's native Windows bootstrap (SPEC-0065 rule 7, build (c), ADR-0620).

.DESCRIPTION
  Kit-only: run the plugin's copy from the project's folder (or name it with -Root); it is never installed into a
  project. A machine with nothing installed has no Python
  to run setup.py, so this script installs Python alone through winget, then hands every other tool to
  `setup.py install`. It holds no version and no package name of its own: it reads both from the one table in setup.py
  (MINIMUM and WINGET). Before its one install it reads winget, winget's policy, the administrator right and a test
  download, and on any of them stops with one line naming what IT must allow; without -Yes it installs nothing.
  It never asks for, stores or prints a password or a sign-in secret.

.EXAMPLE
  pwsh -NoProfile -File scripts/agk/setup_windows.ps1 -Yes
#>
[CmdletBinding()]
param([string] $Root = (Get-Location).Path, [switch] $Yes, [switch] $Json)

$ErrorActionPreference = 'Continue'
$Setup = Join-Path $PSScriptRoot 'setup.py'
$Hand = 'or install Python by hand, then run /agk:setup again'

function Stop-Line([string]$Text) { Write-Output "stop: $Text"; exit 1 }

function Read-Table([string]$Name, [string]$Key) {
    $text = Get-Content -Raw -Encoding UTF8 $Setup
    $block = [regex]::Match($text, "(?s)$Name = \{(.*?)\}").Groups[1].Value
    return [regex]::Match($block, "`"$Key`":\s*`"([^`"]+)`"").Groups[1].Value
}

function Find-Python([string]$Least) {
    foreach ($cmd in @('py', 'python')) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { continue }
        $out = & $cmd --version 2>$null
        if ($LASTEXITCODE -eq 0 -and "$out" -match '(\d+\.\d+(\.\d+)?)' -and [version]$Matches[1] -ge [version]$Least) {
            return $cmd
        }
    }
    return $null
}

$least = Read-Table 'MINIMUM' 'python'
$package = Read-Table 'WINGET' 'python'
$py = Find-Python $least
if (-not $py) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Stop-Line "winget is missing: allow winget (the App Installer), $Hand"
    }
    $policy = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AppInstaller' `
        -Name EnableAppInstaller -ErrorAction SilentlyContinue  # (verify) the policy value
    if ($policy -and $policy.EnableAppInstaller -eq 0) {
        Stop-Line "winget is refused by policy: allow winget (the App Installer), $Hand"
    }
    $me = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Stop-Line "this account is not an administrator: ask IT for the administrator right, $Hand"
    }
    winget show --id $package --exact --source winget *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-Line "the test download was refused: allow downloads from winget's source, $Hand"
    }
    if (-not $Yes) { Stop-Line 'nothing installed: installs run only after the person''s yes (setting: -Yes)' }
    winget install --id $package --exact --source winget --accept-package-agreements --accept-source-agreements `
        --disable-interactivity --silent
    if ($LASTEXITCODE -ne 0) { Stop-Line "Python did not install and is left as it was, $Hand" }
    # An install does not refresh this process's PATH: read it again from the machine and the user.
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    $py = Find-Python $least
    if (-not $py) { Stop-Line "Python reads below $least after its install, $Hand" }
}

$rest = @('install', '--root', $Root)  # the project's folder: its containers decide the engine
if ($Yes) { $rest += '--yes' }
if ($Json) { $rest += '--json' }
& $py $Setup @rest
exit $LASTEXITCODE
