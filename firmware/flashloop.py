#!/usr/bin/env python3
"""Hands-free continuous UPDI flashing station for the coaster board.

Walk up with a handful of boards: plug one onto the jig, watch it flash, and
move to the next. The board signals its own result -- a successful flash arms a
one-shot EEPROM flag (see firmware/main.c) and the board plays a distinct rapid
blink on the launch reset; a failed flash leaves it dark. No need to look at the
screen.

The loop is edge-triggered on insertion: it flashes a board once, waits for the
blink to finish, then waits for you to remove the board before arming again, so a
board left on the jig is never re-flashed in a tight loop.
"""

import glob
import os
import subprocess
import sys
import time

import click

# UPDI over any USB-serial adapter (TX->1k->RX, RX->UPDI pad); see README.
PART = "attiny202"
PROGRAMMER = "serialupdi"

# Programming steps, applied in order in a single avrdude run. avrdude aborts on
# the first failing -U, so the EEPROM arm is LAST: it is reached only when flash
# and fuses both verified, which is exactly the condition the board's confirm
# blink should signal. bodcfg 0x06 = BOD at 1.8V, sampled in sleep (see Makefile).
# eeprom 0xa5 = FLASH_CONFIRM_ARMED (see main.c); the first boot blinks + clears it.
BODCFG_VALUE = "0x06"
CONFIRM_ARMED = "0xa5"

# Port globs, most-reliable first. On macOS prefer the cu.* device (it does not
# block waiting for carrier detect the way tty.* does).
PORT_GLOBS = (
    "/dev/cu.usbserial*",
    "/dev/cu.usbmodem*",
    "/dev/tty.usbserial*",
    "/dev/ttyUSB*",
)

# Pacing. The confirm blink is ~0.64s; dwell longer so it completes and clears
# its flag before any removal poll resets the chip again.
POLL_INTERVAL_S = 0.5
CONFIRM_DWELL_S = 1.2


def find_port(override: str | None) -> str | None:
    """Return the device to use: the explicit override, else the first match."""
    # An explicit --port is honored only while it actually exists on disk.
    if override is not None:
        return override if os.path.exists(override) else None

    # Otherwise probe each glob in priority order (adapter may be unplugged).
    for pattern in PORT_GLOBS:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]

    return None


def _avrdude(port: str, extra: list[str], quiet: bool) -> int:
    """Run avrdude against the part on `port`, returning its exit code."""
    # Base invocation; extra holds the -U operations (empty = signature read only).
    cmd = ["avrdude", "-c", PROGRAMMER, "-p", PART, "-P", port]
    cmd += ["-qq"] if quiet else []
    cmd += extra

    # Presence checks are silenced; real programming runs inherit the terminal so
    # failures are visible on screen.
    out = subprocess.DEVNULL if quiet else None
    return subprocess.run(cmd, stdout=out, stderr=out).returncode


def board_present(port: str) -> bool:
    """True if a board on the jig answers the UPDI signature read."""
    # No -U: avrdude just enters programming mode, reads the signature, and exits.
    return _avrdude(port, [], quiet=True) == 0


def program_board(port: str, hexfile: str) -> bool:
    """Flash + fuses + arm-confirm in one run; True only if every step verified."""
    # Arm step is last so it is reached only after flash and fuses both pass.
    steps = [
        "-U", f"flash:w:{hexfile}:i",
        "-U", f"bodcfg:w:{BODCFG_VALUE}:m",
        "-U", f"eeprom:w:{CONFIRM_ARMED}:m",
    ]
    return _avrdude(port, steps, quiet=False) == 0


def wait_for(override: str | None, want_present: bool) -> str:
    """Block until a board is present/absent as requested; return the live port."""
    # Re-resolve the port each pass so unplugging/replugging the adapter recovers.
    while True:
        port = find_port(override)
        if port is not None and board_present(port) == want_present:
            return port

        time.sleep(POLL_INTERVAL_S)


def flash_one(port: str, hexfile: str) -> None:
    """Flash a single seated board and report the result to the screen."""
    # The board itself is the primary indicator; the screen line is the backup.
    click.secho("→ board detected, flashing…", fg="cyan")

    if program_board(port, hexfile):
        click.secho("✓ flashed — board will blink to confirm", fg="green")
    else:
        click.secho("✗ FLASH FAILED — board stays dark, set aside", fg="red")


@click.command()
@click.option("--hex", "hexfile", default="firmware/main.hex", show_default=True,
              help="Path to the firmware .hex to flash.")
@click.option("--port", default=None,
              help="USB-serial device; auto-detected from common globs if unset.")
@click.option("--once", is_flag=True,
              help="Flash the next board that appears, then exit.")
def main(hexfile: str, port: str | None, once: bool) -> None:
    """Continuously flash boards as they are plugged onto the UPDI jig."""
    # Fail fast on a missing hex rather than discovering it per board.
    if not os.path.exists(hexfile):
        click.secho(f"hex not found: {hexfile} (run `make -C firmware build`)", fg="red")
        sys.exit(1)

    click.secho("flashing station ready — plug in a board (Ctrl-C to stop)", fg="yellow")

    # Edge-triggered loop: wait for insertion -> flash -> let the blink finish ->
    # wait for removal before arming the next board.
    while True:
        live = wait_for(port, want_present=True)
        flash_one(live, hexfile)
        time.sleep(CONFIRM_DWELL_S)

        if once:
            return

        click.secho("  remove the board to arm the next…", fg="bright_black")
        wait_for(port, want_present=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        click.secho("\nstopped", fg="yellow")
