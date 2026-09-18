# dotfiles

macOS dotfiles and machine setup, managed entirely by
[mise](https://mise.jdx.dev). This repository *is* `~/.config/mise`, so
[`config.toml`](config.toml) is mise's global configuration — one declarative
file covering packages, dotfile links, vendored checkouts, and tools.

## Bootstrap

On a fresh machine, with git available (Xcode's command line tools are enough):

```sh
curl https://mise.run | sh
export PATH="$HOME/.local/bin:$PATH"
mise bootstrap --adopt https://github.com/andrewarcher/.dotfiles.git
```

The full URL rather than the `owner/repo` shorthand, both because the repo name
starts with a dot and because HTTPS needs no SSH key on a machine that has not
been set up yet.

`--adopt` clones this repo into `$MISE_CONFIG_DIR` (`~/.config/mise`) and runs
[`mise bootstrap`](https://mise.jdx.dev/bootstrap.html) against it. That is the
whole install — there is no installer script, and Homebrew does not need to be
installed first.

Re-run `mise bootstrap` after every pull; each phase compares declared state
against the machine and changes only what differs. Useful variants:

| Command                                | Does                                             |
| -------------------------------------- | ------------------------------------------------ |
| `mise bootstrap status`                 | what every phase would change, without doing it  |
| `mise bootstrap --dry-run`              | full preview                                     |
| `mise bootstrap --only dotfiles,tools`  | one or two phases                                |
| `mise bootstrap --update`               | also refresh package metadata and the repos below |
| `mise bootstrap --force-dotfiles`       | replace a target that conflicts with its link    |

Phases run in a fixed order: packages → repos → dotfiles → shell activation →
macOS defaults → tools → the `bootstrap` task. Bootstrap is a sequence, not a
transaction: if a phase fails, earlier changes stay. Fix and re-run.

## Layout

| Path                      | Links to                  | Notes                                |
| ------------------------- | ------------------------- | ------------------------------------ |
| `config.toml`             | —                         | global mise config; all of the below |
| `dotfiles/zshrc`          | `~/.zshrc`                | PATH, prompt, history, integrations  |
| `dotfiles/inputrc`        | `~/.inputrc`              | readline arrow-key history search    |
| `dotfiles/zsh/`           | `~/.config/zsh`           | holds the fzf-tab checkout           |
| `dotfiles/nvim/`          | `~/.config/nvim`          | `init.lua` + LSP — needs nvim ≥ 0.11 |
| `dotfiles/git/`           | `~/.config/git`           | `config` + global `ignore`           |
| `dotfiles/ghostty/`       | `~/.config/ghostty`       | terminal                             |
| `dotfiles/lsd/`           | `~/.config/lsd`           | `ls` replacement                     |
| `dotfiles/linearmouse/`   | `~/.config/linearmouse`   | per-device mouse/trackpad tuning     |
| `dotfiles/finicky.ts`     | `~/.config/finicky.ts`    | browser/URL routing                  |

These are `[dotfiles]` entries in symlink mode, so editing the live path edits
the file here. `mise dot status` shows what is linked, `mise dot diff` what has
drifted, and `mise dot add <path>` adopts a new file into `dotfiles/`.

`~/.zprofile` is not in the table: mise owns a marker block in it via
`[bootstrap.mise_shell_activate]` rather than the whole file.

## Tools come from mise, not Homebrew

Every tool with a mise backend is a global `[tools]` entry. Because this repo is
the *global* config, those tools are on PATH everywhere — and **a project that
pins its own version in `mise.toml` wins inside that directory**. That is the
point of not installing them from Homebrew: `go`, `ruff`, `gopls` and the rest
follow the project, not the machine.

Activation is deliberately split:

- `~/.zprofile` puts the **shim farm** on PATH, via
  `[bootstrap.mise_shell_activate]`. This is what reaches processes that never
  display a prompt — GUI apps, and nvim spawning language servers.
- `~/.zshrc` runs `mise activate zsh`, which puts **resolved tool paths ahead
  of the shims** and exports mise's env vars, which shims alone do not do.

Homebrew keeps only what mise has no backend for — `git`, `htop`, `watch`,
`wget` and the five GUI casks. Those stay in `[bootstrap.packages]`, and mise
pours the bottles and casks into `/opt/homebrew` itself: it never shells out to
`brew` and does not require Homebrew to be installed. Formulae poured by mise
and by a real `brew` are mutually legible, so an existing Homebrew install
keeps working either way. `adopt = true` claims apps already in `/Applications`
instead of replacing their bundles, which would reset their macOS Privacy &
Security grants.

`ruby` is in `[tools]` but unused directly — see the comment on it in
`config.toml`.

Add a tool with `mise use -g <tool>`, or a package with
`mise bootstrap packages use brew:<formula>`; both edit `config.toml` in place.

## Vendored checkouts

`[bootstrap.repos]` clones the two upstream plugins, replacing what used to be
git submodules — no `--recurse-submodules`, and `mise bootstrap --update`
fast-forwards them:

| Path                                          | Repo                        |
| --------------------------------------------- | --------------------------- |
| `dotfiles/zsh/fzf-tab`                        | `Aloxaf/fzf-tab`            |
| `dotfiles/nvim/pack/plugins/start/nvim-lspconfig` | `neovim/nvim-lspconfig` |

Both are gitignored here. Their paths in `config.toml` are absolute
(`~/.config/mise/...`) because relative repo paths are only valid in a project
config, not a global one.

## Secrets

`~/.config/env_keys` is sourced first thing in `.zshrc` and is deliberately
**not** in this repo. The `bootstrap` task creates it empty and `0600` if it is
missing, and never touches it otherwise, so re-running bootstrap cannot lose
keys.

## Editor

`nvim` is the editor: `.zshrc` exports `EDITOR`/`VISUAL` and aliases both `vi`
and `vim` to it. Git needs no `core.editor` — it falls back to `$EDITOR`, so
that stays the single source of truth.

The nvim config is a single `init.lua` (~200 lines) plus the `nvim-lspconfig`
checkout under `dotfiles/nvim/pack/plugins/start/`, loaded via nvim's native
packpath — no plugin manager.

LSP and as-you-type completion are nvim built-ins (`vim.lsp.enable`,
`vim.lsp.completion`). nvim-lspconfig supplies the per-server definitions;
`init.lua` overrides only gopls analyses and ruff's hover.

| Language   | Server                 | `[tools]` entry                      |
| ---------- | ---------------------- | ------------------------------------ |
| Go         | `gopls`                | `go:golang.org/x/tools/gopls`        |
| TypeScript | `ts_ls`                | `npm:typescript-language-server`     |
| Python     | `basedpyright` (types) | `pipx:basedpyright`                  |
| Python     | `ruff` (lint + format) | `ruff`                               |

Add a language by putting its server in `[tools]` and adding a row to the
`servers` table in `init.lua`. Servers start lazily per filetype, so an unlisted
or uninstalled one costs nothing.

### Server versions follow the project

Each server binary is resolved **per project root**, in order:

1. project-local bin — `node_modules/.bin`, `.venv/bin`
2. `mise which <bin>`, run in that directory, so a repo's pinned version applies
3. `PATH`

Run `:LspWhich` in any buffer to see what the current project resolves to.

Why mise is consulted directly rather than trusting `PATH`: a mise shim sits on
`PATH` globally and is executable even where no version applies, then exits 1
the instant it spawns (`No version is set for shim: gopls`) — so nvim would see
a working command and get a server that dies immediately. Asking mise yields
either a real absolute path for that directory or a clean failure.

One TypeScript caveat: `typescript-language-server` needs `typescript`
resolvable in the workspace. Any repo with it in `devDependencies` works; a bare
`.ts` file outside a project will not.

## GUI app config

Of the casks in `[bootstrap.packages]`, only some keep config worth versioning:

| App         | Config                                   | In repo                     |
| ----------- | ---------------------------------------- | --------------------------- |
| Ghostty     | `~/.config/ghostty/config`               | yes — `dotfiles/ghostty/`   |
| LinearMouse | `~/.config/linearmouse/linearmouse.json` | yes — `dotfiles/linearmouse/` |
| Finicky     | `~/.config/finicky.ts`                   | yes — `dotfiles/finicky.ts` |
| CalendR     | app-managed plist, UI state only         | no                          |
| Lunar       | `fyi.lunar.Lunar` plist                  | **no — contains secrets**   |

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

Lunar and LinearMouse start at login as legacy login items, which have no
plain-file equivalent — enable those by hand in each app. If something with a
real preference key needs carrying to a new machine, it belongs in
`[bootstrap.macos.defaults]` rather than a script.

## Notes

- GUI apps still installed outside this repo (Firefox, Slack, Zoom, Figma,
  Spotify) are not captured — several of these are what `finicky.ts` routes to.
- Containers are colima + the docker CLI, both `[tools]` entries. `colima`
  shells out to `limactl`, and nothing declares that for it, so `lima` is
  listed explicitly.
- `mise bootstrap packages import --manager brew` is the equivalent of
  `brew bundle dump` if Homebrew ever accumulates something worth declaring.
