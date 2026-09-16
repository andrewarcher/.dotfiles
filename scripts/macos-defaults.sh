#!/usr/bin/env bash
set -euo pipefail

# GUI app settings that have no config file to symlink, so they cannot be
# linked from target/ like everything else and have to be written as macOS
# defaults instead.
#
# Only settings worth carrying to a new machine belong here -- not every
# preference an app happens to store.

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "not macOS, skipping defaults" >&2
  exit 0
fi

# Hidden Bar: start at login.
#
# The app is sandboxed, so this lands in its container rather than
# ~/Library/Preferences; `defaults` redirects there on its own.
#
# This seeds the preference only. The actual login item is a separate helper
# bundle (com.dwarvesv.LauncherApplication) that the app registers via
# SMLoginItemSetEnabled when it launches and reads this key -- which is why the
# launch below is part of the same step.
defaults write com.dwarvesv.minimalbar isAutoStart -bool true

echo "macOS defaults applied"

# Launch Hidden Bar so it reads the key above and registers its login-item
# helper, which is the step `defaults write` cannot do on its own. Running it
# here means a fresh machine is set up by `./install` rather than needing the
# app opened by hand afterwards.
#
# Whether the registration took can only really be confirmed by rebooting;
# reading it back needs `sudo sfltool dumpbtm`.
#
# `open -a` only activates an already-running copy, so this is safe to re-run.
if [[ -d "/Applications/Hidden Bar.app" ]]; then
  open -a "Hidden Bar" && echo "launched Hidden Bar to register its login item"
else
  echo "Hidden Bar not installed, skipping launch" >&2
fi
