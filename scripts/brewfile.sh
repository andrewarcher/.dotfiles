#!/usr/bin/env bash
set -euo pipefail

BASEDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=scripts/brew-env.sh
source "${BASEDIR}/scripts/brew-env.sh"

# Previously this exited 0 when brew was missing, so a fresh machine silently
# installed nothing while dotbot reported success. If brew cannot be found even
# at its standard prefixes, that is a real failure.
if ! command -v brew >/dev/null 2>&1; then
  echo "brew not found, checked PATH and the standard prefixes" >&2
  exit 1
fi

brew bundle install --file="${BASEDIR}/Brewfile"
