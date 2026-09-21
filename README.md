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

### If the first run fails

Bootstrap is a sequence, not a transaction, and `--adopt` clones before it
applies. So a failed first run still leaves `~/.config/mise` checked out — and a
second `--adopt` **reuses that checkout without updating it**, silently
re-running the same commit that just failed. Fix a config bug upstream, then
either update the checkout first or tell `--adopt` to:

```sh
git -C ~/.config/mise pull --ff-only && mise bootstrap
# or
mise bootstrap --adopt https://github.com/andrewarcher/.dotfiles.git --update
```

`git -C ~/.config/mise log --oneline -1` tells you which commit is actually
being applied, which is the first thing to check when a fix appears not to have
taken effect.

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
| CalendR     | sandboxed plist, 36 real preferences     | yes — `tasks/calendr-defaults` |
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

### Apps with no file to symlink

CalendR keeps its settings in a plist, so there is nothing to link.
`calendr/defaults.toml` holds them and is the source of truth; `calendr/sync.py`
moves them in both directions:

```sh
mise run calendr-defaults             # write the repo's values into the app
mise run calendr-capture              # show what you changed in CalendR's UI
mise run calendr-capture -- --update  # bring those changes into the repo
```

`[tasks.bootstrap]` depends on `calendr-defaults`, so `mise bootstrap` applies
them — but it will not silently discard a setting you changed in the app. When
the live app holds anything the repo does not, it stops and asks:

```
CalendR differs from the repo:
  changed  show_week_numbers = false   (repo: true)
  new      some_new_pref = "hello"

  2 changed, 1 new in CalendR.
  [o]verwrite from repo, [s]ave into repo, [k]eep and skip?
```

`save` writes them into `calendr/defaults.toml` for you to commit. Only a
*difference* prompts — a fresh machine, where the repo simply has keys the app
does not yet, applies without asking.

How it decides when nobody can answer, in order:

| Condition                            | Choice                                    |
| ------------------------------------ | ----------------------------------------- |
| `MISE_CALENDR_DRIFT=overwrite\|save\|skip` | that, without asking                |
| `mise bootstrap --yes`               | `overwrite` — unattended, so declared state wins |
| a controlling terminal               | asks on it                                |
| no terminal (launchd, CI)            | `skip`, reports the drift, changes nothing |

The prompt is read from `/dev/tty`, not stdin, because mise pipes a task's
stdin. Bare Enter and EOF both mean `skip`: nothing is written and nothing is
lost, which is the only safe default when the answer is unknown.

`capture` also names any key a new CalendR version starts writing, so additions
get noticed rather than silently ignored.

#### macOS will not let bootstrap grant itself this

CalendR is sandboxed, so its preferences sit in `~/Library/Containers/`, and
reaching another app's container needs the calling program — whichever terminal
runs bootstrap — to hold Full Disk Access. **Bootstrap cannot grant that to
itself, and no script can.** The TCC databases are SIP-protected, so even root
cannot write them; `tccutil` only *resets* permissions; and a Full Disk Access
grant is accepted only from System Settings or an MDM-delivered PPPC profile.
That is the point of the mechanism, not a gap in it.

So the step degrades instead of failing. When access is refused it names the app
needing the grant, prints the command that jumps to the right settings pane, and
**exits 0** — `[tasks.bootstrap]` depends on this task, so failing would abort
the whole bootstrap over a cosmetic step. Re-run `mise run calendr-defaults`
after granting. `calendr-capture` does exit non-zero, since you asked for it
directly.

Reading a container is sometimes permitted where writing is not, so a run can
report differences and still be unable to apply them.

One thing that is *not* a permission problem: with the container root absent — a
machine where CalendR was installed but never opened — `defaults write` exits 0
and writes `~/Library/Preferences/<domain>.plist`, outside the sandbox, where
the app never looks. `apply` therefore launches CalendR once to let it create
the container, and its write probe checks the value reads back through the
domain and that nothing appeared outside, rather than trusting the exit code.

It does **not** use `[bootstrap.macos.defaults]`, and this is worth knowing
before reaching for that section: CalendR is sandboxed, so its preferences live
under `~/Library/Containers/br.paker.Calendr/`. `defaults` redirects there
automatically; mise's macos-defaults writer does not — it writes
`~/Library/Preferences/br.paker.Calendr.plist`, a path the app never reads, and
**reports success**. Verified by writing a probe key both ways. Any sandboxed app
needs a `defaults write` task, not a defaults block.

Two details in that script that are easy to get wrong: floats are written as
`'<real>1.4</real>'` fragments rather than `-float`, because `-float` stores a
32-bit float (1.4 becomes 1.399999976158142 and never matches); and the app is
quit first, because it rewrites its plist on exit and would otherwise clobber
what was just written.

Excluded from version control deliberately: `wdsAuthToken` (a JWT — this repo is
public), the security-scoped bookmark blobs, `disabled_calendars` (account
UUIDs), and the `NSStatusItem` menu bar coordinates. Those keys stay whatever
the app makes them.

Lunar and LinearMouse start at login as legacy login items, which have no
plain-file equivalent — enable those by hand in each app.

## Notes

- GUI apps still installed outside this repo (Firefox, Slack, Zoom, Figma,
  Spotify) are not captured — several of these are what `finicky.ts` routes to.
- Containers are colima + the docker CLI, both `[tools]` entries. `colima`
  shells out to `limactl`, and nothing declares that for it, so `lima` is
  listed explicitly.
- `mise bootstrap packages import --manager brew` is the equivalent of
  `brew bundle dump` if Homebrew ever accumulates something worth declaring.
