# Coaster v0.3 — Design Specification

The circuit itself lives in `design.py` (the single source of truth); this document
records the design intent: how the MCU is wired, why each part is what it is, and what
to verify before committing to a batch. The previous revision (v0.2: ATtiny13A,
EasyEDA) is archived at release v0.2.1; every choice below traces to a lesson learned
debugging it.

## Design rationale

- **MCU: ATtiny202** — in production, real brown-out detector, UPDI single-wire
  programming, ~1µA power-down sleep. 2KB flash / 128B SRAM is 7× the current
  firmware; the ATtiny402 (4KB/256B) is a drop-in substitute at +$0.22 if the
  firmware ever outgrows it — a binary built for the 202 runs unmodified on a 402.
- **Button on a GPIO with pin-interrupt wake** — presses cost ~0 µAh and richer UX
  (double-tap, long-press) becomes possible. v0.2 woke by dead-shorting the battery,
  which cost ~11 µAh per press and destroyed SRAM state.
- **One series resistor per LED + low-side MOSFET driver** — LED current set by
  design, not by battery internal resistance and pin-driver luck.
- **Real decoupling (C1) and bulk (C2) capacitance** — transient immunity; rides
  through battery-holder micro-dropouts.
- **3-pad UPDI header** — programming cannot collide with the LEDs by construction
  (v0.2's ISP shared the LED pin, which made flashing finicky).

## MCU pin map (ATtiny202, SOIC-8)

| Pin | Port | Net      | Function |
|-----|------|----------|----------|
| 1   | VDD  | VCC      | Power |
| 2   | PA6  | BUTTON   | Button input, internal pull-up, falling-edge wake. PA6 chosen deliberately: Px2/Px6 are the fully-asynchronous pins that can edge-wake from power-down |
| 3   | PA7  | —        | Unused (firmware enables pull-up) |
| 4   | PA1  | —        | Unused / spare test pad (optional) |
| 5   | PA2  | —        | Unused / spare test pad (optional) |
| 6   | PA0  | UPDI     | Programming only — route to header, leave in UPDI mode (do NOT fuse to GPIO/RESET) |
| 7   | PA3  | LED_PWM  | TCA0 WO0 hardware PWM → MOSFET gate |
| 8   | GND  | GND      | Ground |

## Connections (net by net)

```
VCC:      BT1+, U1-1, C1-1, C2-1, R1-1, R2-1, R3-1, R4-1, J1-2 (UPDI header VDD)
GND:      BT1-, U1-8, C1-2, C2-2, Q1-source, SW1-(2nd terminal), C3-2, R5-2, J1-3
LED_PWM:  U1-7 (PA3), Q1-gate, R5-1 (100k pulldown to GND)
LED_K:    Q1-drain, L1-cathode, L2-cathode, L3-cathode, L4-cathode
LED legs: VCC → R{1..4} (150Ω) → L{1..4} anode ; all cathodes → LED_K
BUTTON:   U1-2 (PA6), SW1-(1st terminal), C3-1 (100nF debounce, optional)
UPDI:     U1-6 (PA0), J1-1
```

Notes:

- R5 (gate pulldown) keeps the LEDs off while PA3 floats during programming/reset.
- C1 must sit physically adjacent to U1 pins 1/8; C2 anywhere near the battery holder.
- 150Ω per LED ≈ 2–4mA per LED across the battery's life (3.2V fresh → 2.8V worn);
  total LED load ~8–16mA. Through the MOSFET, the MCU pin only drives gate charge.
- J1: 1×3 through-hole pads, 2.54mm pitch, near the board edge: [UPDI | VDD | GND].
  Through-hole so a header can be pressed in at an angle or soldered for batch work.

## BOM (with JLCPCB catalog tier)

| Ref | Part | Package | LCSC # | Tier | ~Unit USD |
|-----|------|---------|--------|------|-----------|
| U1 | ATtiny202-SSN | SOIC-8 | C2052951 (-SSNR) | Extended | 0.43 |
| Q1 | AO3400A N-MOSFET | SOT-23 | C20917 | Basic | 0.01 |
| L1–L4 | White LED XL-1608UWC-04 | 0603 | C965808 | Extended | 0.01 |
| R1–R4 | 150Ω 1% | 0603 | C22808 | Basic | 0.001 |
| R5 | 100kΩ 1% | 0603 | C25803 | Basic | 0.001 |
| C1 | 100nF X7R 50V | 0603 | C14663 | Basic | 0.001 |
| C2 | 22µF X5R 25V | 0805 | C45783 | Basic | 0.01 |
| C3 | 100nF (debounce, optional) | 0603 | C14663 | Basic | 0.001 |
| SW1 | Tactile switch TS-1187A-B-A-B | SMD | C318884 | Extended | 0.02 |
| BT1 | CR2016 holder MY-2016-02 | SMD | C2979176 | Extended | 0.16 |

These LCSC numbers are the source of truth in `design.py`'s `LCSC` map, from
which `make fab` emits the BOM — the table here is documentation. The five
non-jellybean parts are deliberate (see below); the passives are pinned to
in-stock JLCPCB *Basic* SKUs (no feeder fee), substitutable by any same
value/package/tolerance Basic part if one lapses. Per-board parts ≈ $0.74 USD. Extended parts (U1, L1–L4, SW1, BT1) cost a $3 feeder fee
each per order — $0.40/board at qty 30. Option: leave BT1 off the assembly and
hand-solder it (two large pads) to save its fee.

Part choices worth defending:

- **Q1 must be a logic-level FET.** The AO3400A (Vgs(th) 0.65–1.45V) is fully enhanced
  at worn-cell voltage; a 2N7002 (Vgs(th) up to 2.5V worst-case) would be driven barely
  above threshold for most of the cell's life and read as dim/flickering LEDs.
- **L1–L4 buy brightness, not cost.** The XL-1608UWC-04 delivers 400 min / 630 typ mcd
  @ 20mA versus the basic-catalog KT-0603W's 173–207 — about 3× the light at the same
  current, in the same footprint, with coin-cell-friendly Vf. The glow is the entire
  point of the device, so this is the one place the feeder fee is clearly worth it.
- **SW1 is mechanically load-bearing.** The enclosure flexure is dimensioned around
  this switch's body height and actuation force, and its footprint is the one extracted
  from the manufactured v0.2 board. A basic-catalog switch would save $0.10/board and
  risk re-validating the press feel.
- **BT1 takes a CR2016, not a CR2032.** Same Ø20mm cell, but the MY-2016-02 holder is
  2.2mm tall versus 3.6mm, slimming the enclosure (the holder was the tallest
  component). ~75mAh still gives 2+ years at a few presses a day — µA sleep dominates
  and presses are now ~free.

## Ordering plan

30 boards, JLCPCB Economic assembly (30 is the Economic cap — the per-unit sweet spot).
Estimated ~$100–105 AUD shipped (economy mail).

`make fab` generates the three JLCPCB uploads into `pcb/dist/` (gitignored) from the
board geometry and `design.py`'s part data: `coaster-gerbers.zip` (Gerbers + drill),
`coaster-bom.csv`, and `coaster-cpl.csv` (pick-and-place). The UPDI header (J1,
through-hole) and the mounting holes are excluded from assembly — J1 is pressed/soldered
by hand for batch flashing. Then at the JLCPCB quote tool:

1. Upload `coaster-gerbers.zip`; set **white soldermask** (same price): the board face
   sits under the clear shield and is the reflector behind the LEDs — dark mask absorbs a
   large fraction of the show's light for free.
2. Quantity 30, SMT assembly on the top side; upload `coaster-bom.csv` and
   `coaster-cpl.csv`.
3. Confirm **ATtiny202 (C2052951)** stock/tier at order time; if out of stock, the
   ATtiny402 is a drop-in substitute (same firmware binary), or order assembly without U1
   and hand-solder the SOIC-8s.
4. On the assembly preview, **verify part orientations**. The KiCad and JLCPCB rotation
   conventions differ for some packages, and `ROTATION_CORRECTION` in `design.py` is empty
   until a real preview is checked. The one that bites: BT1's pads are symmetric but the
   part is not — the insertion mouth must face the **west** board edge (cell slides in/out
   over bare board). Record any rotation fix in `ROTATION_CORRECTION` (keyed by footprint)
   and re-run `make fab`, so the next order is right by construction.

Boards arrive **blank**: program each over the UPDI header (`make fuses` once to set the
1.8V BOD, then `make flash`) and drop in a CR2016 — the cells are not part of the JLCPCB
order. Validate one unit against the first-article checklist below before committing the
batch to enclosures and cells.

## Firmware port checklist (ATtiny13A → ATtiny202)

- [x] PWM: TCA0 in single-slope PWM, WO0 on PA3 (default PORTMUX routing); duty updates
      via CMP0BUF; bright phase at full duty now that R1–R4 set the current
- [x] Button: PA6 input, internal pull-up (PORTA.PIN6CTRL), falling-edge interrupt, wake from power-down
- [x] Sleep: SLPCTRL power-down; expected sleep current ~0.1–2µA (BOD in sampled mode)
- [x] BOD: configured via FUSE.BODCFG at programming time (`make fuses`, 0x06) — enabled
      at 1.8V, sampled mode in sleep
- [x] Debounce in firmware (20ms, also filters release-bounce edges); C3 is belt-and-suspenders
- [x] Show logic carries over: ramp, breathe ×5 ending on the dim phase, squared perceptual
      fade (~8s total; the v0.2 battery-recovery settle phase is gone — presses no longer
      touch the supply rail)
- [x] Reset logic: show on `PORF` only (battery insertion = self-test); a brown-out reset
      skips to sleep so a dying cell cannot reset-relight; button wakes are not resets at all
- [x] Programming: avrdude serialupdi (any USB-serial adapter + 1 resistor), `make flash`

Builds at 422 / 2048 bytes with avr-gcc 14. Hardware verification of all of the above
lives in the first-article checklist below.

## First-article validation (before deploying all 30)

- [ ] Programming via UPDI header works
- [ ] Sleep current measured < 5µA
- [ ] Show plays on button press; press costs no measurable charge
- [ ] Brightness through an actual glass: 150Ω is a starting value, not a decision —
      if too dim, rework toward 100Ω and re-measure worn-battery behavior
- [ ] Worn-battery test: show degrades gracefully (dims) with no reset loop
- [ ] Bench-supply + series-resistor test (30–50Ω) simulating a dying cell
- [ ] Press during show, long-press, rapid double-press behave sanely
- [ ] Splash test: assembled unit, dribble water over the flexure — the shield sheds
      it, nothing reaches the PCB, battery contact stays dry, button still clicks
