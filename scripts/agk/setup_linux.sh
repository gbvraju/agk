#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
#
# /agk:setup's Linux and cloud virtual machine bootstrap (SPEC-0065 rule 7, build (e), ADR-0622).
# Kit-only: run the plugin's copy from the project's folder; it is never installed into a project.
#
#   bash setup_linux.sh [--yes] [--json] [--root DIR]   Python and curl first, then `setup.py install`
#   bash setup_linux.sh node apt|dnf URL                one step, called by `setup.py install`
#   bash setup_linux.sh gitleaks VERSION                one step, called by `setup.py install`
#   bash setup_linux.sh claude URL                      one step, called by `setup.py install`
#
# It holds no version and no URL of its own but gitleaks' release folder: Python's floor is read from
# setup.py's MINIMUM table as text and every other version and URL comes in setup.py's call. Before
# its one install it reads apt or dnf, root or sudo and one test download, and on any of them it
# stops with one line naming what to allow; without --yes it installs nothing. sudo asks for its
# own sign-in; this script never sees, asks for or stores one.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP="$HERE/setup.py"
HAND="or install Python and curl by hand, then run /agk:setup again"

stop() { echo "stop: $1"; exit 1; }
as_root() { if [ "$(id -u)" = 0 ]; then "$@"; else sudo "$@"; fi; }
manager() { if command -v apt-get >/dev/null; then echo apt; elif command -v dnf >/dev/null; then echo dnf; fi; }
pm_install() { if [ "$1" = apt ]; then shift; as_root apt-get install -y -q "$@"; else shift; as_root dnf install -y -q "$@"; fi; }

step_node() {  # wsl_setup.ps1's path: NodeSource's setup script, then the distribution's nodejs package
  local pm="$1" url="$2"
  curl -fsSL "$url" | as_root bash - >/dev/null || { echo "the Node.js download failed: allow $url"; return 1; }
  pm_install "$pm" nodejs >/dev/null
}

step_gitleaks() {  # the pinned release, checked against its published checksum file before unpacking
  local v="$1" arch tmp archive sums base=https://github.com/gitleaks/gitleaks/releases/download
  case "$(uname -m)" in
    x86_64 | amd64) arch=x64 ;;
    aarch64 | arm64) arch=arm64 ;;
    *) echo "no gitleaks release for this machine's architecture; nothing was installed"; return 1 ;;
  esac
  archive="gitleaks_${v}_linux_${arch}.tar.gz"; sums="gitleaks_${v}_checksums.txt"; tmp="$(mktemp -d)"
  if ! curl -fsSL -o "$tmp/$archive" "$base/v$v/$archive" || ! curl -fsSL -o "$tmp/$sums" "$base/v$v/$sums"; then
    rm -rf "$tmp"; echo "the gitleaks download failed: allow github.com release downloads; nothing was installed"; return 1
  fi
  if ! (cd "$tmp" && grep " $archive\$" "$sums" | sha256sum --check --strict --status); then
    rm -rf "$tmp"; echo "the gitleaks archive does not match its published checksum; nothing was installed"; return 1
  fi
  tar -xzf "$tmp/$archive" -C "$tmp" gitleaks && as_root install -m 0755 "$tmp/gitleaks" /usr/local/bin/gitleaks
  local code=$?; rm -rf "$tmp"; return $code
}

step_claude() {  # Claude Code by its own installer, as the user (it installs into ~/.local/bin)
  curl -fsSL "$1" | bash >/dev/null 2>&1 || { echo "Claude Code did not install: allow $1"; return 1; }
}

case "${1:-}" in
  node) step_node "$2" "$3"; exit $? ;;
  gitleaks) step_gitleaks "$2"; exit $? ;;
  claude) step_claude "$2"; exit $? ;;
esac

if [ "$(uname -s)" = Darwin ]; then  # rule 7, Q-S0065-3: setup.py's MAC_LINE, word for word
  echo "stop: macOS is not covered by /agk:setup yet (setting: the platform); nothing was changed"
  exit 1
fi

YES=0; JSON=0; ROOT="$PWD"
while [ $# -gt 0 ]; do
  case "$1" in
    --yes) YES=1 ;;
    --json) JSON=1 ;;
    --root) ROOT="$2"; shift ;;
    *) stop "unknown argument (setting: the command line)" ;;
  esac
  shift
done

least="$(awk '/^MINIMUM = \{/,/^\}/' "$SETUP" | sed -n 's/.*"python": "\([0-9.]*\)".*/\1/p')"
python_ok() {
  command -v python3 >/dev/null \
    && python3 -c "import sys; sys.exit(sys.version_info[:2] < tuple(map(int, '$least'.split('.'))))"
}

if ! python_ok || ! command -v curl >/dev/null; then
  pm="$(manager)"
  [ -n "$pm" ] || stop "no package manager this command knows (apt or dnf) is here: $HAND"
  if [ "$(id -u)" != 0 ] && ! { command -v sudo >/dev/null && sudo -n true 2>/dev/null; }; then
    stop "this account is not root and cannot use sudo here without a prompt: run \`sudo -v\` in a terminal first, or ask for sudo, $HAND"
  fi
  [ "$YES" = 1 ] || stop "nothing installed: installs run only after the person's yes (setting: --yes)"
  if [ "$pm" = apt ]; then as_root apt-get update -q >/dev/null; else as_root dnf makecache -q >/dev/null; fi \
    || stop "the test download was refused: allow the distribution's package mirrors (a company proxy or certificate is the usual cause), $HAND"
  pm_install "$pm" python3 curl ca-certificates >/dev/null || stop "Python did not install and is left as it was, $HAND"
  python_ok || stop "Python reads below $least after its install, $HAND"
fi

REST=(install --root "$ROOT")
[ "$JSON" = 1 ] && REST+=(--json)
[ "$YES" = 1 ] && REST+=(--yes)
exec python3 "$SETUP" "${REST[@]}"
