#!/usr/bin/env bash
# Put brew on PATH for the calling script. Source this, do not execute it.
#
# Within a single ./install run, the step that installs Homebrew cannot change
# the environment of the steps after it -- each dotbot shell step is its own
# process. The `brew shellenv` in .zshrc only affects new shells, so on a fresh
# machine nothing between installing brew and opening a new terminal can find
# it. Any script needing brew therefore has to resolve it itself instead of
# trusting the inherited PATH.

if ! command -v brew >/dev/null 2>&1; then
  for _brew_prefix in /opt/homebrew /usr/local; do
    if [[ -x "${_brew_prefix}/bin/brew" ]]; then
      eval "$("${_brew_prefix}/bin/brew" shellenv)"
      break
    fi
  done
  unset _brew_prefix
fi
