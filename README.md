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
4. Check out submodules (dotbot, vim/nvim plugins, fzf-tab)
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
| `target/nvim/`        | `~/.config/nvim`     | init.lua + LSP — needs nvim ≥ 0.11        |
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

## Editor

`nvim` is the default editor: `.zshrc` exports `EDITOR`/`VISUAL` and aliases
`vi`. Git needs no `core.editor` — it falls back to `$EDITOR`, so that stays the
single source of truth. `vim` is deliberately left unaliased, so `target/vim/`
stays reachable by name as a fallback (it still has vim-go).

The nvim config is a single `init.lua` (~200 lines) plus the `nvim-lspconfig`
submodule under `target/nvim/pack/plugins/start/`, loaded via nvim's native
packpath — no plugin manager.

LSP and as-you-type completion are nvim built-ins (`vim.lsp.enable`,
`vim.lsp.completion`). nvim-lspconfig supplies the per-server definitions;
`init.lua` overrides only gopls analyses and ruff's hover.

| Language   | Server                       | Brewfile default             |
| ---------- | ---------------------------- | ---------------------------- |
| Go         | `gopls`                      | `gopls`                      |
| TypeScript | `ts_ls`                      | `typescript-language-server` |
| Python     | `basedpyright` (types)       | `basedpyright`               |
| Python     | `ruff` (lint + format)       | `ruff`                       |

Add a language by putting its server in the `Brewfile` and adding a row to the
`servers` table in `init.lua`. Servers start lazily per filetype, so an unlisted
or uninstalled one costs nothing.

### Server versions follow the project

The Brewfile installs a working default of every server, but a project that pins
its own toolchain wins. Each server binary is resolved **per project root**, in
order:

1. project-local bin — `node_modules/.bin`, `.venv/bin`
2. `mise which <bin>`, run in that directory, so a repo's pinned version applies
3. Homebrew — the Brewfile default
4. `PATH`

Run `:LspWhich` in any buffer to see what the current project resolves to.

Why mise is consulted directly rather than trusting `PATH`: a mise shim sits on
`PATH` globally and is executable even when no version is set for it, then exits
1 the instant it spawns (`No version is set for shim: gopls`). Asking mise
yields either a real absolute path for that directory or a clean failure into
the Homebrew default — which is also why Homebrew is tried ahead of bare `PATH`.

One TypeScript caveat, found by testing: Homebrew's `typescript` is now 7.x, the
Go-native rewrite, which ships no `tsserver.js` and so cannot act as a global
fallback. `typescript-language-server` needs `typescript` resolvable in the
workspace. Any repo with it in `devDependencies` works; a bare `.ts` file
outside a project will not.

Update plugins with `git submodule update --remote`.
