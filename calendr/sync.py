#!/usr/bin/env python3
"""Keep CalendR's preferences and calendr/defaults.toml in step.

    apply     write every key in defaults.toml into the app
    capture   report where the app differs, and with --update save it back here

Both directions go through this one file so they cannot disagree about which
keys are managed or how a TOML type maps to a plist type.

Why `defaults` and not mise's `[bootstrap.macos.defaults]`: CalendR is
sandboxed, so its preferences live in
~/Library/Containers/br.paker.Calendr/Data/Library/Preferences. `defaults`
redirects there on its own. mise's macos-defaults writer does not -- it writes
~/Library/Preferences/br.paker.Calendr.plist, a path the app never reads, and
still reports success.

Why values are written as XML plist fragments rather than `defaults write
-bool/-int/-float`: `-float` stores a 32-bit float, so 1.4 reads back as
1.399999976158142 and never matches what the app wrote. A fragment is parsed as
the exact type while still going through `defaults`, so cfprefsd and the sandbox
redirect both still apply.
"""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

DOMAIN = "br.paker.Calendr"
APP = "Calendr"
HERE = Path(__file__).resolve().parent
DATA = HERE / "defaults.toml"

# Keys that must never be captured into this repo. `capture` reports anything
# live that is neither managed nor listed here, so a setting a new CalendR
# version starts writing gets noticed instead of silently ignored.
EXCLUDE_EXACT = {
    "wdsAuthToken": "a JWT; this repo is public",
    "installation_bookmark": "security-scoped bookmark, encodes local paths",
    "NSOSPLastRootDirectory": "security-scoped bookmark, encodes local paths",
    "disabled_calendars": "calendar UUIDs, specific to one account",
    "last_checked_version": "the app's own updater state",
    "NSNavPanelExpandedSizeForOpenMode": "window geometry",
}
EXCLUDE_PREFIX = {
    "NSStatusItem": "menu bar coordinates, depend on the machine's other items",
    "saved NSStatusItem": "menu bar coordinates, depend on the machine's other items",
}


def excluded(key: str) -> str | None:
    if key in EXCLUDE_EXACT:
        return EXCLUDE_EXACT[key]
    for prefix, why in EXCLUDE_PREFIX.items():
        if key.startswith(prefix):
            return why
    return None


def uncapturable(key: str, value) -> str | None:
    """Why this live key cannot go in defaults.toml, or None if it can.

    Separate from `excluded`, which is about keys we refuse on principle. This
    is about values TOML and `defaults write` cannot faithfully round-trip.
    """
    reason = excluded(key)
    if reason:
        return reason
    if isinstance(value, bytes):
        return "binary data"
    if isinstance(value, dict):
        return "nested dictionary, not supported here"
    if isinstance(value, (list, dict)) and not value:
        return "empty, nothing to carry"
    return None


class Denied(Exception):
    """macOS refused us access to CalendR's preferences.

    Its settings live in its sandbox container, which macOS protects: reaching
    another app's container needs the calling program -- here, whichever
    terminal or agent is running bootstrap -- to have been granted access.
    A fresh machine has granted nothing yet, so this is the normal state there,
    not a broken config.
    """


GUIDANCE = """CalendR's preferences live in its sandbox container, which macOS protects, and
  this terminal has not been granted access to it. Nothing else was affected.

  Grant {app} Full Disk Access, then apply them with
    mise run calendr-defaults

  That pane cannot be opened for you -- macOS only accepts this grant from the
  settings app itself -- but this jumps straight to it:
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"

  Reading the container is sometimes allowed where writing is not, so a run can
  get as far as reporting differences and still be unable to apply them."""


def live() -> dict:
    result = subprocess.run(["defaults", "export", DOMAIN, "-"], capture_output=True)
    if result.returncode != 0:
        raise Denied((result.stderr or result.stdout).decode().strip())
    return plistlib.loads(result.stdout) if result.stdout.strip() else {}


# Only the app can create its container root. `defaults` will happily create the
# Preferences directory inside it, but with the root absent it writes
# ~/Library/Preferences/<domain>.plist instead -- outside the sandbox, where the
# app never looks -- and still exits 0. So the root is what has to exist first.
CONTAINER_ROOT = Path.home() / "Library/Containers" / DOMAIN
CONTAINER_PLIST = CONTAINER_ROOT / "Data/Library/Preferences" / f"{DOMAIN}.plist"
STRAY_PLIST = Path.home() / "Library/Preferences" / f"{DOMAIN}.plist"


def responsible_app() -> str:
    """The .app running us, which is what needs the Full Disk Access grant.

    Walks up the process tree because the grant applies to the enclosing
    application bundle, not to python3 or to mise.
    """
    pid, found = os.getpid(), []
    for _ in range(24):
        fields = subprocess.run(
            ["ps", "-o", "ppid=,comm=", "-p", str(pid)],
            capture_output=True, text=True,
        ).stdout.split(None, 1)
        if len(fields) < 2:
            break
        parent, command = fields[0], fields[1].strip()
        if ".app/Contents/MacOS/" in command:
            found.append(command.split(".app/Contents/MacOS/")[0].split("/")[-1])
        if parent in ("0", "1", str(pid)):
            break
        pid = int(parent)
    # The outermost bundle is the one the user launched and the one the grant
    # attaches to. Nearer ones are interpreters and helpers -- a bundled
    # Python.app, for instance -- which cannot be granted anything useful.
    return found[-1] if found else "your terminal"


def ensure_container() -> None:
    """Make sure CalendR has created its container before writing into it.

    With the container absent -- a machine where CalendR has been installed but
    never opened -- `defaults write` does not fail. It writes
    ~/Library/Preferences/<domain>.plist instead, outside the container, which
    the app never reads. So the settings would silently not apply. Only the app
    can create its own container, so launch it once and wait.
    """
    if CONTAINER_ROOT.is_dir():
        return
    if not Path(f"/Applications/{APP}.app").is_dir():
        raise Denied("CalendR is not installed, so it has no container to write to")
    print("CalendR has never run; launching it once so it creates its container")
    subprocess.run(["open", "-a", APP], capture_output=True)
    for _ in range(60):
        if CONTAINER_ROOT.is_dir():
            return
        subprocess.run(["sleep", "0.5"])
    raise Denied(f"CalendR did not create {CONTAINER_ROOT} within 30s")


def check_writable() -> None:
    """Fail before changing anything if the container is not writable.

    Probing up front keeps a refusal from landing halfway through, which would
    leave CalendR holding some of the repo's values and some of its own, and
    avoids quitting the app or asking a question we cannot act on.
    """
    probe = "mise_write_probe"
    result = subprocess.run(
        ["defaults", "write", DOMAIN, probe, "<true/>"], capture_output=True
    )
    landed_outside = STRAY_PLIST.exists()
    try:
        if result.returncode != 0:
            raise Denied((result.stderr or result.stdout).decode().strip())
        # Exit 0 is not enough. A write can succeed into the wrong file, so
        # confirm the value is actually readable back through the domain and
        # that nothing appeared outside the container.
        if landed_outside:
            raise Denied(
                f"the write went to {STRAY_PLIST}, outside CalendR's container, "
                "where it never reads"
            )
        if probe not in live():
            raise Denied("the write reported success but cannot be read back")
    finally:
        subprocess.run(["defaults", "delete", DOMAIN, probe], capture_output=True)
        if landed_outside:
            STRAY_PLIST.unlink(missing_ok=True)


def declared() -> dict:
    return parse_settings(DATA.read_text())


def parse_settings(text: str) -> dict:
    """Read the `key = value` subset of TOML that `write_data` emits.

    Deliberately not a TOML parser. `tomllib` would be the obvious tool, but it
    is Python 3.11+ and macOS ships 3.9 -- so on a fresh machine, before any
    mise-managed python exists, importing it raises ModuleNotFoundError and
    takes bootstrap down with it. This module has to run on whatever python3 the
    OS provides.

    Every value the writer emits is also valid JSON -- bools, integers, reals,
    basic strings with the same two escapes, and arrays of those -- so `json`
    parses the right-hand side with exact types and no bespoke scanner. A
    TOML-only spelling a hand edit might introduce, such as a single-quoted
    string or `1_000`, is rejected with the line number rather than guessed at.
    """
    settings = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(f"{DATA.name}:{lineno}: expected `key = value`, got {raw!r}")
        key, value = key.strip(), value.strip()
        try:
            key = json.loads(key) if key.startswith('"') else key
            settings[key] = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{DATA.name}:{lineno}: cannot read {value!r} ({exc.msg}). "
                "Only bools, integers, reals, double-quoted strings and arrays "
                "of those are supported here."
            ) from None
    return settings


def fragment(value) -> str:
    """Render a value as the XML plist fragment `defaults write` accepts."""
    # bool first: it is a subclass of int.
    if isinstance(value, bool):
        return "<true/>" if value else "<false/>"
    if isinstance(value, int):
        return f"<integer>{value}</integer>"
    if isinstance(value, float):
        return f"<real>{value!r}</real>"
    if isinstance(value, str):
        return f"<string>{escape(value)}</string>"
    if isinstance(value, list):
        return "<array>" + "".join(fragment(v) for v in value) + "</array>"
    raise TypeError(f"no plist mapping for {type(value).__name__}")


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # Round-trip through %.10g so a double that came back as
        # 1.4000000000000001 is written as 1.4, while staying a float.
        text = repr(float(f"{value:.10g}"))
        return text if ("." in text or "e" in text) else text + ".0"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    raise TypeError(f"no TOML mapping for {type(value).__name__}")


def running() -> bool:
    return subprocess.run(["pgrep", "-xq", APP]).returncode == 0


def quit_app() -> None:
    subprocess.run(
        ["osascript", "-e", f'quit app "{APP}"'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        if not running():
            return
        subprocess.run(["sleep", "0.5"])


CHOICES = ("overwrite", "save", "skip")


def ask(changed: dict, new: dict) -> str:
    """How to resolve drift: overwrite the app, save into the repo, or skip.

    An explicit MISE_CALENDR_DRIFT wins. Otherwise `mise bootstrap --yes` means
    unattended, so the declared state wins without asking. Otherwise ask on the
    controlling terminal -- mise pipes a task's stdin, so /dev/tty is the only
    way to reach the person running it. With no terminal at all (launchd, CI)
    nothing is guessed: drift is reported and left alone, because silently
    discarding settings someone changed is the one outcome worth avoiding.
    """
    forced = os.environ.get("MISE_CALENDR_DRIFT", "").strip().lower()
    if forced in CHOICES:
        print(f"  MISE_CALENDR_DRIFT={forced}")
        return forced
    if forced:
        print(f"  ignoring MISE_CALENDR_DRIFT={forced!r}, expected one of "
              f"{', '.join(CHOICES)}", file=sys.stderr)
    if os.environ.get("MISE_YES"):
        print("  --yes, so taking the repo's values")
        return "overwrite"
    try:
        with open("/dev/tty", "r+") as tty:
            while True:
                tty.write(
                    f"\n  {len(changed)} changed, {len(new)} new in CalendR.\n"
                    "  [o]verwrite from repo, [s]ave into repo, [k]eep and skip? "
                )
                tty.flush()
                answer = (tty.readline() or "").strip().lower()
                if answer in ("o", "overwrite"):
                    return "overwrite"
                if answer in ("s", "save"):
                    return "save"
                if answer in ("k", "keep", "skip", ""):
                    return "skip"
                tty.write("  please answer o, s or k.\n")
    except OSError:
        print("  no terminal to ask on; leaving CalendR alone. Resolve with "
              "`mise run calendr-capture`,\n  or set "
              "MISE_CALENDR_DRIFT=overwrite|save to decide up front.",
              file=sys.stderr)
        return "skip"


def cmd_apply() -> int:
    want = declared()
    try:
        ensure_container()
        have = live()
        check_writable()
    except Denied as exc:
        # Deliberately exit 0: `[tasks.bootstrap]` depends on this task, so a
        # non-zero status would abort the whole bootstrap over a cosmetic step
        # that needs a permission no unattended run can grant itself.
        print(f"skipping CalendR settings -- {GUIDANCE.format(app=responsible_app())}", file=sys.stderr)
        if str(exc):
            print(f"  ({exc})", file=sys.stderr)
        return 0

    changed, new, _missing, _skipped = diff(want, have)

    # Drift means the app holds settings the repo does not. Applying would
    # discard them, so resolve it before writing anything.
    if changed or new:
        print("CalendR differs from the repo:")
        report(want, changed, new, [], {})
        choice = ask(changed, new)
        if choice == "skip":
            print("left CalendR as it is; nothing written", file=sys.stderr)
            return 0
        if choice == "save":
            want = {**want, **changed, **new}
            write_data(want)
            print(f"saved into calendr/defaults.toml ({len(want)} keys) "
                  "-- commit it")

    # CalendR rewrites its plist as it exits, so values written underneath a
    # running copy get clobbered.
    if running():
        quit_app()

    for count, key in enumerate(sorted(want, key=str.lower), 1):
        result = subprocess.run(
            ["defaults", "write", DOMAIN, key, fragment(want[key])],
            capture_output=True,
        )
        if result.returncode != 0:
            # check_writable() should have caught this, so reaching here means
            # access changed underneath us. Still not worth a traceback, and
            # still not worth failing bootstrap over.
            detail = (result.stderr or result.stdout).decode().strip()
            print(
                f"stopped after {count - 1} of {len(want)} CalendR preferences "
                f"at {key!r}; the app now holds a mix of its own values and this "
                f"repo's.\n  {GUIDANCE.format(app=responsible_app())}",
                file=sys.stderr,
            )
            if detail:
                print(f"  ({detail})", file=sys.stderr)
            return 0
    print(f"wrote {len(want)} CalendR preferences")

    # Launching lets CalendR read the values and register the login-item
    # LaunchAgent that `launch_agent_enabled` only asks for. `open -a` just
    # activates an already-running copy, so this is safe to repeat.
    if Path(f"/Applications/{APP}.app").is_dir():
        subprocess.run(["open", "-a", APP], check=True)
        print("launched CalendR to apply them and register its login item")
    else:
        print("CalendR not installed, skipping launch", file=sys.stderr)
    return 0


def diff(want: dict, have: dict) -> tuple[dict, dict, list, dict]:
    """(changed, new, missing, skipped) between the repo and the live app.

    `changed` and `new` together are drift: things the app holds that the repo
    does not. `missing` is not drift -- it is simply a key not applied yet,
    which is every key on a fresh machine.
    """
    changed = {k: have[k] for k in want if k in have and have[k] != want[k]}
    missing = [k for k in want if k not in have]
    unmanaged = {k: v for k, v in have.items() if k not in want}
    new = {k: v for k, v in unmanaged.items() if not uncapturable(k, v)}
    skipped = {k: r for k, v in unmanaged.items() if (r := uncapturable(k, v))}
    return changed, new, missing, skipped


def report(want: dict, changed: dict, new: dict, missing: list, skipped: dict) -> None:
    for key, value in sorted(changed.items(), key=lambda kv: kv[0].lower()):
        print(f"  changed  {key} = {toml_value(value)}   (repo: {toml_value(want[key])})")
    for key, value in sorted(new.items(), key=lambda kv: kv[0].lower()):
        print(f"  new      {key} = {toml_value(value)}")
    for key in sorted(missing, key=str.lower):
        print(f"  absent   {key}   in the repo but not in the app")
    if skipped:
        # Named individually in defaults.toml's header and in EXCLUDE_* above;
        # printing all of them every run would bury the lines that matter.
        print(f"  ({len(skipped)} unmanaged keys left alone, incl. secrets and machine state)")


def cmd_capture(update: bool) -> int:
    want = declared()
    try:
        have = live()
    except Denied as exc:
        # An explicit command, unlike apply, so a refusal is worth a failure.
        print(f"cannot read CalendR's settings -- {GUIDANCE.format(app=responsible_app())}", file=sys.stderr)
        if str(exc):
            print(f"  ({exc})", file=sys.stderr)
        return 1
    changed, new, missing, skipped = diff(want, have)
    report(want, changed, new, missing, skipped)

    if not (changed or new or missing):
        print("CalendR matches the repo; nothing to capture")
        return 0

    if not update:
        print(
            f"\n{len(changed)} changed, {len(new)} new, {len(missing)} absent."
            "\nRe-run with --update to write them into calendr/defaults.toml."
        )
        return 0

    merged = dict(want)
    merged.update(changed)
    merged.update(new)
    write_data(merged)
    print(f"\nupdated calendr/defaults.toml ({len(merged)} keys)")
    if missing:
        print("kept the keys absent from the app; delete them by hand if intended")
    return 0


def write_data(settings: dict) -> None:
    lines = [
        "# CalendR's preferences, versioned. This file is the source of truth:",
        "# `mise run calendr-defaults` writes every key below into the app, and",
        "# `mise run calendr-capture` brings changes you made in CalendR's UI back here.",
        "#",
        "# The value's TOML type sets the plist type, so they must match what CalendR",
        "# expects. Note that `1.0` is a real and `1` is an integer -- they are not",
        "# interchangeable, and a bool is neither.",
        "#",
        "# Keys are deliberately absent rather than forgotten. `calendr-capture`",
        "# reports any new one the app starts writing. Never add:",
    ]
    reasons = dict(EXCLUDE_EXACT)
    reasons.update({f"{p} *": why for p, why in EXCLUDE_PREFIX.items()})
    for key in sorted(reasons, key=str.lower):
        lines.append(f"#   {key:36} {reasons[key]}")
    lines.append("")
    for key in sorted(settings, key=str.lower):
        quoted = key if all(c.isalnum() or c == "_" for c in key) else f'"{key}"'
        lines.append(f"{quoted} = {toml_value(settings[key])}")
    lines.append("")
    DATA.write_text("\n".join(lines))


def main(argv: list[str]) -> int:
    args = argv[1:]
    mode = args[0] if args else ""
    if mode == "apply":
        return cmd_apply()
    if mode == "capture":
        return cmd_capture(update="--update" in args[1:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
