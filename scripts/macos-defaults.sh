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
# NOTE: this seeds the preference only. Hidden Bar registers the actual login
# item with macOS (via SMAppService, which binds to the app's code signature)
# the first time it launches and reads this. A fresh machine therefore still
# needs Hidden Bar opened once before it really starts at login.
defaults write com.dwarvesv.minimalbar isAutoStart -bool true

echo "macOS defaults applied"
