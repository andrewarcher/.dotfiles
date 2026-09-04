#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  echo "brew not found, skipping Brewfile" >&2
  exit 0
fi

BASEDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
brew bundle install --file="${BASEDIR}/Brewfile"
