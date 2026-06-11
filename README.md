# Coaster

Very simple battery-operated device. When you push a button, the light turns on for a few seconds
and then it turns off. It is designed to be used as a coaster such that, when gently pushing a glass
down on the device, the light activates making the contents of the glass glow.

Pressing down on the coaster triggers a ~8 second light show: the LEDs ramp up to full
brightness, "breathe" gently five times, and fade back to black. Between shows the device
sleeps at ~1 µA — there is no on/off switch and none is needed.

## Repository layout

- `firmware/` — AVR C firmware and its build/flash Makefile.
- `pcb/` — v0.3 board design (KiCad, generated from python scripts) and footprints.
- `enclosure/` — 3D-printed shell (FreeCAD source + STEP/STL export).

All subdirectories share the same verbs, and the top-level Makefile forwards to each:
`make build` (firmware hex + board + enclosure exports), `make test` (flash-fit check +
board DRC + enclosure solidity check), `make clean`. Domain-specific verbs forward to the
relevant subdirectory: `make flash` / `make fuses` (firmware programming),
`make review` (board render / PDF / STEP).

## How it works

The button connects an MCU pin (with its internal pull-up) to ground. Pressing it fires a
falling-edge interrupt on one of the ATtiny202's fully-asynchronous pins, which wakes the
chip from power-down sleep with the main clock stopped — a press costs effectively no
charge. The firmware debounces the edge, plays the show over hardware PWM through a
MOSFET driving four series-resistored LEDs, and goes back to sleep.

Two details carry hard-won lessons from v0.2:

- The show also plays once when the battery is inserted (a power-on reset doubles as a
  built-in self test), but *only* on a power-on reset: a brown-out reset means a dying
  cell sagged below 1.8V mid-show, and playing again would loop the cell to death — so a
  brown-out goes straight back to sleep and the coaster simply dims gracefully as the
  battery wears out.
- Wake edges that turn out not to be presses (e.g. contact bounce while lifting a glass
  off a held-down button) are filtered by a 20ms debounce check, so the show plays on
  deliberate presses only.

## Hardware

![coaster v0.3 board](pcb/board.png)

The v0.3 design (KiCad) lives in `pcb/`:

- `pcb/design.py` is the circuit as data — parts, placements, and the netlist defined
  once. This is the file to read or edit; it is the source of truth.
- `pcb/DESIGN.md` is the design specification: pin map, BOM with part rationale,
  ordering plan, and the validation checklists.
- `pcb/generate.py` turns `design.py` into `coaster.kicad_pcb` (committed for
  convenience). `make build` regenerates the board and validates connectivity; `make
  test` runs DRC; `make review` produces a board render, a 1:1 printable PDF, and a STEP
  model for CAD fit checks.
- `pcb/coaster.pretty/` — project footprints with pad geometry extracted from the
  manufactured v0.2 board (battery holder, tactile switch).

There is no schematic: JLCPCB takes Gerbers + BOM + CPL (not a schematic), the board is
built and checked directly against `design.py`, and `design.py` itself documents the
circuit — so a derived schematic would add nothing.

The previous revision (v0.2: ATtiny13A, EasyEDA, CR2032) is archived at release
[v0.2.1](https://github.com/owahltinez/coaster/releases/tag/v0.2.1), including its
firmware, schematic renderings, and 3D printing assets.

### Production

All SMD parts are LCSC-stocked, so the board can be fabricated and assembled through
JLCPCB — the only hand-assembly per unit is dropping a CR2016 into the holder. Order
with **white soldermask** (the board face is the reflector behind the LEDs; see the
ordering plan in [pcb/DESIGN.md](pcb/DESIGN.md)).

Rough estimates as of June 2026, assembled and shipped: **~A$3.30/board at qty 30,
~A$2.70 at qty 100** (~US$2.15/$1.75). A finished coaster — board, name-brand CR2016,
and ~29g of printed shell — lands around **A$5.25 at qty 30**. Prices drift; get a real
quote from the [JLCPCB quote tool](https://jlcpcb.com/quote) and confirm ATtiny202
stock at order time (the ATtiny402 is a firmware-compatible drop-in substitute).

## Software

To build the firmware you need `avr-gcc` (≥ 12, for ATtiny202 support; `avr-gcc@14`
from the [osx-cross/avr](https://github.com/osx-cross/homebrew-avr) tap works) and
`avrdude` (≥ 7, for `serialupdi`). Then:

```bash
make -C firmware build   # or `make build` from the repo root to build everything
```

The board build needs KiCad (`kicad-cli` and the `pcbnew` python bindings) and the
enclosure build needs FreeCAD (`freecadcmd`). On Linux both land on PATH; macOS app
bundles don't expose their CLIs, so symlink them once:

```bash
ln -s /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli /opt/homebrew/bin/kicad-cli
ln -s /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/kicad-python
ln -s /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd /opt/homebrew/bin/freecadcmd
```

### Flashing

No dedicated programmer needed: UPDI works over any USB-serial adapter with a single
~1kΩ resistor bridging the adapter's TX to RX, and RX wired to the board's UPDI pad
(plus VDD and GND — the J1 pads are labeled on the silkscreen).

```bash
make flash   # writes main.hex over serialupdi
make fuses   # once per chip: brown-out detector at 1.8V, sampled in sleep
```

The fuses matter: the factory default leaves the BOD disabled, which allows undefined
behavior when the battery sags, and the firmware's brown-out logic depends on it.

Gotchas:

- **Remove the coin cell before flashing.** The adapter drives VDD and would back-feed
  the (non-rechargeable) lithium cell.
- That's it. The v0.2 list of ISP gotchas (LEDs clamping MOSI, flaky readback, wedged
  programmers) died with the ISP header: UPDI shares no pins with anything else on this
  board, by construction.

## Power estimates

Assumptions: CR2016 rated at 75 mAh (~70 mAh usable), ~8 mA LED draw at 100% duty on a
fresh cell, ~1 µA sleep current (BOD sampled).

| Event                  | Cost     | Notes                                          |
|------------------------|----------|------------------------------------------------|
| Light show (~8 s)      | ~15 µAh  | avg ~60% LED duty + ~1.5 mA MCU active         |
| Button press           | ~0       | pin-change wake; nothing touches the supply    |
| Standby (per day)      | ~26 µAh  | ~1 µA sleep + battery self-discharge           |

Expected battery life:

| Usage pattern               | Battery life      |
|-----------------------------|-------------------|
| Never pressed (shelf)       | ~7 years          |
| ~5 presses/day              | ~2 years          |
| ~30 presses/day (bar duty)  | ~5 months         |
| Theoretical max shows       | ~4,500            |

The punchline: v0.3 runs on a cell with a third of the v0.2 battery's capacity and
still matches its life, because presses are now free (each v0.2 press dead-shorted the
battery and cost as much as a show) and sleep current dropped ~4×.

## Demo

> TODO: Add demo pictures / video.
