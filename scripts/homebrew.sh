#!/usr/bin/env bash
set -euo pipefail

BASEDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# brew may already be installed but absent from PATH -- see brew-env.sh. Without
# this the check below would miss it and try to reinstall.
# shellcheck source=scripts/brew-env.sh
source "${BASEDIR}/scripts/brew-env.sh"

if command -v brew >/dev/null 2>&1; then
  echo "brew already installed"
  exit 0
fi

# Homebrew needs sudo to create /opt/homebrew (and to install the Xcode command
# line tools, if they are missing). NONINTERACTIVE makes its installer call
# `sudo -n`, which fails outright rather than prompting:
#
#   Need sudo access on macOS (e.g. the user <you> needs to be an Administrator)!
#
# So cache the credential up front. This is the one point in ./install that
# asks for a password.
if ! sudo -n true 2>/dev/null; then
  echo "Homebrew needs sudo to install. You will be prompted for your password."
  sudo -v
fi

# Installing the command line tools can take longer than sudo's 5 minute
# timeout. Without this the credential expires mid-install and the `sudo -n`
# calls start failing partway through, which is messier than failing up front.
while true; do
  sudo -n true
  sleep 60
  kill -0 "$$" 2>/dev/null || exit
done 2>/dev/null &
sudo_keepalive=$!
trap 'kill "${sudo_keepalive}" 2>/dev/null || true' EXIT

NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
