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
4. Check out submodules (dotbot, nvim plugins, fzf-tab)
5. Install Homebrew if missing (`scripts/homebrew.sh`)
6. Install everything in `Brewfile` (`scripts/brewfile.sh`)

Useful flags: `./install --except shell` links only, `./install -v` for verbose output.

## Layout

| Path                  | Links to             | Notes                                     |
| --------------------- | -------------------- | ----------------------------------------- |
| `target/zshrc`        | `~/.zshrc`           | prompt, history, tool integrations        |
| `target/inputrc`      | `~/.inputrc`         | readline arrow-key history search         |
| `target/zsh/`         | `~/.config/zsh`      | fzf-tab submodule                         |
| `target/nvim/`        | `~/.config/nvim`     | init.lua + LSP — needs nvim ≥ 0.11        |
| `target/git/`         | `~/.config/git`      | `config` + global `ignore`                |
| `target/ghostty/`     | `~/.config/ghostty`  | terminal                                  |
| `target/lsd/`         | `~/.config/lsd`      | `ls` replacement                          |
| `target/linearmouse/` | `~/.config/linearmouse` | per-device mouse/trackpad tuning       |
| `target/finicky.ts`   | `~/.config/finicky.ts` | browser/URL routing                     |

## Secrets

`~/.config/env_keys` is sourced first thing in `.zshrc` and is deliberately **not**
in this repo. `./install` creates it empty; put API keys and other per-machine
exports there.

## Notes

- The `Brewfile` covers CLI tools plus the casks for GUI apps that are worth
  reinstalling automatically. GUI apps still installed outside Homebrew
  (Firefox, Slack, Zoom, Figma, Spotify) are not captured — several of these are
  what `finicky.ts` routes to.
- Regenerate after installing something new: `brew bundle dump --force --no-vscode`
- `target/nvim/pack/` uses nvim's native package loading; plugins are submodules.

## Editor

`nvim` is the editor: `.zshrc` exports `EDITOR`/`VISUAL` and aliases both `vi`
and `vim` to it. Git needs no `core.editor` — it falls back to `$EDITOR`, so
that stays the single source of truth.

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

## GUI app config

Of the casks in the `Brewfile`, only some keep config worth versioning:

| App         | Config                                 | In repo                     |
| ----------- | -------------------------------------- | --------------------------- |
| Ghostty     | `~/.config/ghostty/config`             | yes — `target/ghostty/`     |
| LinearMouse | `~/.config/linearmouse/linearmouse.json` | yes — `target/linearmouse/` |
| Hidden Bar  | sandboxed plist, 9 keys of UI state    | no                          |
| Lunar       | `fyi.lunar.Lunar` plist                | **no — contains secrets**   |

The LinearMouse copy has the `serialNumber` from each device matcher removed.
That field is optional (matching falls back to `productName` + `vendorID` +
`productID`), the values are Bluetooth MAC addresses, and this repo is public.
Dropping them also makes the config portable — the same model of mouse on
another machine still matches. Re-add a serial only to tell two identical
devices apart.

Lunar's plist is deliberately not versioned: alongside per-display calibration
keyed to hardware serials, it holds a Paddle licence token and an `apiKey`.
Its `~/Library/Application Support/Lunar/*.padl` licence files are likewise
machine-bound and must stay out of the repo.

Hidden Bar stores nine keys of menu-bar UI state in a sandboxed container
plist. Capture it with `defaults export com.dwarvesv.minimalbar -` if it ever
becomes worth keeping.
