# dotfiles

macOS dotfiles, managed with [dotbot](https://github.com/anishathalye/dotbot).

## Bootstrap

```sh
git clone --recurse-submodules https://github.com/<you>/dotfiles ~/.dotfiles
cd ~/.dotfiles && ./install
```

`./install` is idempotent — re-run it after every pull. It will:

1. Symlink everything in `target/` into `~` and `~/.config` (see `install.conf.yaml`)
2. Remove stale symlinks from `~` and `~/.config`
3. Create `~/.cache/less` and an empty `~/.config/env_keys`
4. Check out submodules (dotbot, vim plugins, fzf-tab)
5. Install Homebrew if missing (`scripts/homebrew.sh`)
6. Install everything in `Brewfile` (`scripts/brewfile.sh`)

Useful flags: `./install --except shell` links only, `./install -v` for verbose output.

## Layout

| Path                  | Links to             | Notes                                     |
| --------------------- | -------------------- | ----------------------------------------- |
| `target/zshrc`        | `~/.zshrc`           | prompt, history, tool integrations        |
| `target/inputrc`      | `~/.inputrc`         | readline arrow-key history search         |
| `target/zsh/`         | `~/.config/zsh`      | fzf-tab submodule                         |
| `target/vim/`         | `~/.config/vim`      | XDG vimrc — needs vim ≥ 9.1.0327          |
| `target/git/`         | `~/.config/git`      | `config` + global `ignore`                |
| `target/ghostty/`     | `~/.config/ghostty`  | terminal                                  |
| `target/lsd/`         | `~/.config/lsd`      | `ls` replacement                          |
| `target/finicky.ts`   | `~/.config/finicky.ts` | browser/URL routing                     |

## Secrets

`~/.config/env_keys` is sourced first thing in `.zshrc` and is deliberately **not**
in this repo. `./install` creates it empty; put API keys and other per-machine
exports there.

## Notes

- The `Brewfile` was seeded from `brew bundle dump` and lists CLI tools only.
  GUI apps installed outside Homebrew (Ghostty, Firefox, Slack, Zoom, Figma,
  Spotify) are not captured — several of these are what `finicky.ts` routes to.
- Regenerate after installing something new: `brew bundle dump --force --no-vscode`
- `target/vim/pack/` uses vim's native package loading; plugins are submodules.
