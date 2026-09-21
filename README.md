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

`--adopt` is only for the first run on a machine. Afterwards this repo *is*
`~/.config/mise`, so updating it is an ordinary pull:

```sh
git -C ~/.config/mise pull && mise bootstrap
```

Each phase compares declared state against the machine and changes only what
differs, so re-running is cheap and safe.

Prefer that over re-running `--adopt --update`, which reaches the same config
but also fast-forwards every `[bootstrap.repos]` checkout — an unasked-for
nvim-lspconfig bump — and fails outright if you have local changes in one.

> [!NOTE]
> A **failed** first run still leaves `~/.config/mise` cloned, because `--adopt`
> clones before it applies. A second `--adopt` then reuses that checkout
> *without* updating it, silently re-running the commit that just failed. After
> fixing a config bug upstream, pull before re-running.
>
> `git -C ~/.config/mise log --oneline -1` shows which commit is actually being
> applied — the first thing to check when a fix appears to have had no effect.

Useful variants:

| Command                                | Does                                             |
| -------------------------------------- | ------------------------------------------------ |
| `mise bootstrap status`                 | what every phase would change, without doing it  |
| `mise bootstrap --dry-run`              | full preview                                     |
| `mise bootstrap --only dotfiles,tools`  | one or two phases                                |
| `mise bootstrap --update`               | also refresh package metadata and fast-forward the checkouts below; add `--skip-dirty` if any has local changes |
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
| `dotfiles/lsd/`           | `~/.config/lsd`           | `ls` replacement — `.zshrc` aliases `ls` to it |
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

## macOS defaults

The menu bar clock is declared in `[bootstrap.macos.defaults]` and applied by
the macOS-defaults phase of `mise bootstrap`:

| Key                                      | Value   | Effect                           |
| ---------------------------------------- | ------- | -------------------------------- |
| `AppleICUForce24HourTime` (NSGlobalDomain) | `true`  | **24-hour clock**              |
| `ShowSeconds`                            | `true`  | minutes and seconds              |
| `ShowAMPM`                               | `false` | no AM/PM suffix                  |
| `ShowDate`                               | `2`     | never — CalendR already shows it |
| `ShowDayOfWeek`                          | `false` | likewise CalendR's job           |
| `IsAnalog`                               | `false` | digital                          |
| `FlashDateSeparators`                    | `false` | no blinking `:`                  |

Result: `14:01:28`. The two menu bar items divide the work — the system clock
shows the time, CalendR shows the date in the format `calendr/defaults.toml`
sets.

**`ShowAMPM = false` is not what makes it 24-hour.** That key only decides
whether an AM/PM suffix is drawn; alone it leaves a 12-hour clock with no way to
tell 02:00 from 14:00. The switch is `AppleICUForce24HourTime`, which is what
System Settings › General › Date & Time › "24-hour time" writes. It is
system-wide, not menu-bar-only — every app's short and medium time formatting
follows it, and macOS offers no menu-bar-only equivalent.

It has to be declared explicitly because the locale does not imply it:
`AppleLocale` here is `en_CA`, which formats 12-hour, so without this key a new
machine comes up showing `2:01:28 PM`.

This domain *can* live here, unlike CalendR's, because it is a plain file in
`~/Library/Preferences` rather than an app sandbox container — which is exactly
the distinction that decides whether `[bootstrap.macos.defaults]` works or
silently writes somewhere nothing reads.

### Menu bar layout

Right to left: **clock, Control Center, CalendR's date, battery, volume,
bluetooth.**

`NSStatusItem Preferred Position <item>` is points from the right edge, so
ascending values read right to left:

| Position | Item                        |
| -------- | --------------------------- |
| *(none)* | clock — pinned rightmost    |
| `83`     | Control Center (`BentoBox`) |
| `125`    | CalendR's date — *not declared, see below* |
| `218`    | battery                     |
| `260`    | volume (`Sound`)            |
| `298`    | bluetooth                   |

The clock has no position key at all: macOS pins it rightmost and it cannot be
moved. Control Center cannot be moved past it either in practice, so it stays
where macOS puts it.

**CalendR's slot is deliberately not declared.** That key lives in CalendR's own
sandboxed domain and `calendr/sync.py` excludes it as machine-specific — these
are coordinates tuned to one menu bar's particular set of items. On a new
machine CalendR picks its own slot and may need dragging once. Pinning it would
mean re-introducing a key documented as excluded, for a value that is unlikely
to be right elsewhere.

Declaring positions means bootstrap *restores* this order, so an item dragged
elsewhere moves back on the next run.

Visibility is the **module mode integer** (per-host, needs `-currentHost`).
Three values are in use, established by changing each item in System Settings ›
Menu Bar and reading the result back:

| Value | Meaning             | Items here                          |
| ----- | ------------------- | ----------------------------------- |
| `18`  | always show         | battery, volume, bluetooth          |
| `2`   | show when active    | display, focus                      |
| `8`   | never show          | Wi-Fi                               |

`18` is the canonical always-show value — what the
[CIS Benchmark for macOS Sonoma](https://www.tenable.com/audits/items/CIS_Apple_macOS_14.0_Sonoma_v1.0.0_L1.audit:bc25d4cb104347ebb162cdabd712d8b7)
prescribes, and what an MDM `com.apple.controlcenter` payload uses; it also
confirms `-currentHost` is required for both read and write. Apple documents
none of them and no published mapping of the rest exists — `nix-darwin` declined
to model these keys for
[that reason](https://github.com/nix-darwin/nix-darwin/issues/1721).

Screen Mirroring is deliberately absent: it has no per-host mode key even when
set to "show when active", which appears to be that mode's default, so there is
nothing to declare.

**Spotlight is not a Control Center module.** It is drawn by its own process and
hidden by a legacy per-host key in a different domain entirely:

```toml
[[bootstrap.macos.defaults_entries]]
domain = "com.apple.Spotlight"
key = "MenuItemHidden"
host = "current"
value = true
```

That key was found rather than guessed, by a technique worth reusing for any
setting whose key is unknown: dump the candidate domains, toggle the item in
System Settings, then diff.

```sh
defaults -currentHost read com.apple.Spotlight > before.txt
# flip the setting in System Settings
diff before.txt <(defaults -currentHost read com.apple.Spotlight)
```

That named `MenuItemHidden` immediately, flipping `1` → `0`. It also exposed a
decoy: enabling Spotlight makes a `Spotlight = 2` key appear under
`com.apple.controlcenter`, which looks like the obvious lever and is not —
hiding Spotlight again leaves it sitting at `2`, so it is residue, not state,
and is not declared.

The only Terminal method published anywhere for this is `chmod 600` on a binary
inside `/System/Library`, which needs SIP disabled and modifies the OS. It is
not used here.

**`NSStatusItem Visible <item>`** (any-host, boolean) is *not* a second setting
to declare alongside the mode. It reads as macOS's record of whether a
conditional item is showing right now — anything set to always-show has no such
key at all. It is declared here only for `Shortcuts`, `AirDrop`,
`MusicRecognition` and `NowPlaying`, which have no mode key of their own, plus
`BentoBox` for Control Center itself. Pinning it for anything conditional would
contradict "show when active" the moment the condition fired.

`Battery = 3` and `Bluetooth = 2` were earlier values this machine had drifted
to through the Control Center UI; both are normalised to `18`. Bluetooth showing
at `2` is what made these integers look contradictory at first — `2` is "show
when active", and bluetooth was simply active.

#### Checking what is actually drawn

Stored preferences are not proof that the menu bar looks right. With the
terminal granted Accessibility access, the drawn items can be read directly:

```sh
osascript -e 'tell application "System Events" to tell process "ControlCenter" \
  to get description of every menu bar item of menu bar 1'
osascript -e 'tell application "System Events" to tell process "ControlCenter" \
  to get value of attribute "AXPosition" of every menu bar item of menu bar 1'
```

Descriptions and `AXPosition` come back in the same order, so zipping them and
sorting by descending *x* gives the menu bar right to left. Currently:

```
x=3285  Clock
x=3243  Control Center
x=3074  Battery
x=3036  Sound
x=3004  Bluetooth
```

Two caveats. Without Accessibility access every item's name reads
`missing value`, so this needs the grant — a separate one from the Full Disk
Access that CalendR's settings need. And third-party status items, CalendR's
included, report `AXPosition` as `{0, 30}`, so they can be *counted* but not
placed; CalendR's slot between Control Center and the battery can only be
confirmed by looking. Note also that `name` is empty for these items and
`description` is the attribute that carries anything useful.

### Battery percentage

`BatteryShowPercentage` shows the battery as a number beside the icon. It is
declared through the `defaults_entries` array form rather than a domain table,
because Control Center stores it **per host** — the real file is
`~/Library/Preferences/ByHost/com.apple.controlcenter.<hardware UUID>.plist`,
not the any-host `com.apple.controlcenter.plist`:

```toml
[[bootstrap.macos.defaults_entries]]
domain = "com.apple.controlcenter"
key = "BatteryShowPercentage"
host = "current"
value = true
```

`host = "current"` is mise's `defaults -currentHost`, and resolves to whichever
machine is running bootstrap, so the UUID never appears in the repo. Written to
the any-host domain instead it would be accepted and ignored — the same class of
silent miss as writing a sandboxed app's preferences outside its container.
`mise bootstrap macos defaults status` labels it `(current host)`, which is how
you can tell the scope was understood.

Apple has relocated this setting before — it was
`com.apple.menuextra.battery ShowPercent` until Big Sur moved battery into
Control Center — so it is worth re-checking after a major macOS upgrade. `status`
reporting `differs` immediately after a clean apply is the signal that the key
has moved again.

Changes take effect after `killall SystemUIServer ControlCenter`, or a log out.
That is deliberately not a bootstrap hook: it would restart the menu bar on
every run to no purpose, since the phase is a no-op once the values are set.

Note when checking your work that the `.plist` on disk lags — cfprefsd caches
writes and flushes later — so `defaults read com.apple.menuextra.clock` is
authoritative and reading the file is not.

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

### Starting apps at login

LinearMouse and Lunar are started by LaunchAgents declared in
`[bootstrap.macos.launchd.agents]`, which `mise bootstrap` writes to
`~/Library/LaunchAgents/dev.mise.<name>.plist` and loads:

```toml
[bootstrap.macos.launchd.agents.linearmouse]
program = "/usr/bin/open"
args = ["-a", "/Applications/LinearMouse.app"]
run_at_load = true

[bootstrap.macos.launchd.agents.lunar]
program = "/usr/bin/open"
args = ["-a", "/Applications/Lunar.app"]
run_at_load = true
```

Neither obvious alternative works. **Neither app has a preference for this** —
LinearMouse's only related key is `LaunchAtLogin__hasMigrated`, a migration
marker, and Lunar has nothing beyond launch counters; both register through
`SMAppService`, and that state lives in the system's BTM database, which is
SIP-protected. CalendR is the same, which is why `~/Library/LaunchAgents` held
nothing even though all three start at login here. And `osascript … make login
item` needs Automation permission for System Events at bootstrap time, which a
fresh machine has not granted — the same wall as CalendR's settings.

`open -a` rather than the binary inside the bundle, so macOS launches it as a
proper application; it exits once the app is up, which is why there is no
`keep_alive`. This starts LinearMouse, it does not supervise it. Running
alongside the app's own SMAppService registration is harmless: `open -a` on a
running app activates it rather than starting a second copy.

Check either with `launchctl print gui/$UID/dev.mise.<name>`, or test one
without rebooting:

```sh
osascript -e 'quit app "Lunar"'
launchctl kickstart gui/$UID/dev.mise.lunar
```

Starting Lunar this way touches none of its preferences, so the Paddle licence
token and `apiKey` noted above stay out of the repo — the agent only says which
app to open.

## Notes

- GUI apps still installed outside this repo (Firefox, Slack, Zoom, Figma,
  Spotify) are not captured — several of these are what `finicky.ts` routes to.
- Containers are colima + the docker CLI, both `[tools]` entries. `colima`
  shells out to `limactl`, and nothing declares that for it, so `lima` is
  listed explicitly.
- `mise bootstrap packages import --manager brew` is the equivalent of
  `brew bundle dump` if Homebrew ever accumulates something worth declaring.
