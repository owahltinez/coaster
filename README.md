# Coaster

Very simple battery-operated device. When you push a button, the light turns on for a few seconds
and then it turns off. It is designed to be used as a coaster such that, when gently pushing a glass
down on the device, the light activates making the contents of the glass glow.

Pressing down on the coaster triggers a ~11 second light show: the LEDs ramp up, "breathe" gently
between two brightness levels five times, ramp back down, and the device returns to deep sleep.

Because there's no on/off switch, the device remains on but it will do so in low power mode which
for the ATTINY13A it consumes about 4 µA. While the light is on, the device consumes under 10 mA.

## How it works

The button is wired directly across the battery (through R1), so pressing it collapses the supply
voltage and power-cycles the microcontroller. Booting up *is* the wake mechanism: the firmware runs
the light show once on every boot, then enters power-down sleep until the next press.

Because any unexpected reset would also replay the show, the firmware keeps a magic cookie in
`.noinit` SRAM (which survives brown-out resets) to detect a show interrupted by a reset — a worn
battery sagging below 1.8V under LED load. In that case it goes straight back to sleep instead of
replaying, which makes a reset-relight loop impossible. Note that the show must play on every
*other* cookie state including scrambled SRAM: a button press collapses VCC entirely and destroys
SRAM, so it cannot leave evidence behind — requiring positive proof of a clean sleep would brick
the button (learned the hard way). The brown-out detector is enabled at 1.8V while awake (clean
resets instead of undefined behavior at low voltage, and it preserves SRAM so the cookie check is
reliable) and disabled in software during sleep via `BODCR` (to keep standby current at ~4 µA).

## BOM

> TODO: Add 3D printing source files and estimated costs.

All prices are in USD (as of June 2026). LCSC prices are at low-volume price breaks; single-unit
costs are slightly higher.

| Part                     | Part Number      | Source            	| Count 	| Unit Price 	| Subtotal 	|
|--------------------------|------------------|-------------------	|-------	|------------	|----------	|
| ATTINY13A (SOIC-8)\*     | ATTINY13A-SSUR   | [Digikey][attiny] 	| 1     	| $0.750     	| $0.750   	|
| CR2032 Battery           | -                | [Amazon][battery] 	| 1     	| ~$1.000    	| ~$1.000  	|
| White LED (0603)         | KT-0603W (C2290) | [LCSC][led]       	| 4     	| $0.006     	| $0.024   	|
| Coin Cell Battery Holder | MY-2032-12       | [LCSC][holder]    	| 1     	| $0.067     	| $0.067   	|
| Push Button (SMD)        | TS-1187A-B-A-B   | [LCSC][button]    	| 1     	| $0.011     	| $0.011   	|
| 0.1Ω Resistor (1206)     | R1, R2           | -                 	| 2     	| ~$0.010    	| ~$0.020  	|

Total unit cost, excluding shipping and the 3D printed shell: **~$1.87**.

\*The ATTINY13A is not recommended for new designs, but the SOIC variant remains stocked and
cheap. For a new design, consider one of the newer tinyAVR series microcontrollers or the
ATTINY10, which are in active production.

[attiny]: https://www.digikey.com/en/products/detail/microchip-technology/ATTINY13A-SSUR/2522791
[holder]: https://lcsc.com/product-detail/Battery-Connectors_MYOUNG-MY-2032-12_C964833.html
[button]: https://www.lcsc.com/product-detail/C318884.html
[led]: https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_0603White-light_C2290.html
[battery]: https://www.amazon.com.au/CR2032-Batteries-Packaging-Calculator-Electronic/dp/B0CP7SYQ3W/

## Software

To build the code, you need to first install `avrdude`, `avr-libc` and `avr-gcc`. Then, you can run:

```bash
make
```

### Flashing

To flash the code to the ATTINY13A chip, you'll need a USB programmer like [this one][usbasp].

```bash
make install
```

The fuses must be set once per chip to enable the 1.8V brown-out detector (factory default leaves
it disabled, which allows undefined behavior when the battery sags):

```bash
avrdude -c usbasp -p attiny13a -B 125kHz -U hfuse:w:0xfd:m
```

Expected fuse values: `lfuse=0x6A` (factory default: 9.6MHz internal oscillator ÷8 = 1.2MHz),
`hfuse=0xFD` (BOD at 1.8V).

Gotchas learned the hard way:

- **Remove the coin cell before flashing.** The programmer drives 5V onto VCC, which back-feeds
  the (non-rechargeable) lithium cell.
- **The LEDs hang on the MOSI line** (PB0 doubles as the ISP data-in pin) and clamp it to their
  forward voltage, which can sit below the logic-high threshold at 5V. If programming fails with
  `target does not answer` and signature reads as `0x000000`, this is why. A programmer with a
  3.3V supply jumper avoids the problem entirely.
- **Writes are reliable at 125kHz but readback isn't** when holding the ISP cable against the
  board by hand — a flaky MISO contact corrupts reads, not the flash. `make install` handles this
  by writing without inline verification and then verifying in a separate pass at 16kHz.
- **Unplug the programmer from USB before taking the ISP cable off the board.** Hot-detaching the
  cable (transients/shorts on the target side) hangs the USBasp's bit-banged USB stack, and it
  stops responding (`cannot find USB device`) until physically replugged. `make reset` recovers
  the milder wedge where the device still enumerates.

[usbasp]: https://www.fischl.de/usbasp/

## Hardware

The design files in this repo:

- `schematic.net` — netlist (Protel/Altium format), the canonical machine-readable description of
  the circuit: every net and the component pins on it, plus values and footprints.
- `schematic.svg` — the schematic drawing, for humans.
- `easyeda.json` — EasyEDA native source, for re-importing and editing the design in EasyEDA.

Circuit summary: PB0 drives four parallel white LEDs through R2; the button connects VCC to GND
through R1 to power-cycle the MCU as a wake mechanism; the 6-pin AVRISP header exposes
RESET/MISO/MOSI/SCK for in-circuit programming.

### Production

All SMD parts are LCSC-stocked, so the board can be fabricated and assembled through JLCPCB
directly from `easyeda.json` (EasyEDA has a built-in "order at JLCPCB" flow). Rough estimates as
of June 2026: ~$18–20 of fixed fees per order (setup, stencil, feeder loading), ~$0.87 of parts
and ~$0.05 of assembly per board, with the PCB itself at the ~$2-per-5-boards promotional tier.
That works out to roughly **$3.00/board at qty 10, $1.85 at qty 30, $1.35 at qty 100** —
excluding shipping, the battery, and the 3D printed shell. The ISP header is left unpopulated.

Check ATTINY13A-SSUR stock in JLCPCB's parts library before ordering; if their feeder stock is
empty, the "global sourcing" option (from LCSC/Digikey) adds some cost and lead time. Prices
drift — get a real quote from the [JLCPCB quote tool](https://jlcpcb.com/quote).

### Known quirks (v0.2) and wishlist for a future revision

The current board works, but relies on the firmware to compensate for a few design shortcuts:

- The LEDs have no meaningful series resistance (R2 = 0.1Ω); current is limited only by the
  battery's internal resistance and the PB0 pin driver. The firmware caps LED duty cycle via PWM
  to limit average current. A future revision should give each LED a proper series resistor.
- The button dead-shorts the battery (through R1 = 0.1Ω) to wake the chip. It works, but each
  press wastes about as much charge as the entire light show. A future revision should wire the
  button to RESET (or to a GPIO with a pin-change interrupt) instead.
- There is no decoupling capacitor. Add a 100nF ceramic across VCC/GND next to the MCU, plus a
  bulk capacitor (~100µF) to buffer the coin cell during LED pulses.
- Programming requires hand-holding the ISP cable against the board. Pogo-pin pads or a small
  header footprint would make reflashing a batch much less finicky.

## Power estimates

Assumptions: CR2032 rated at 220 mAh (~190 mAh usable after pulse-load derating), ~10 mA LED
draw at 100% duty, measured 4 µA sleep current.

Per event:

| Event                       | Cost      | Notes                                              |
|-----------------------------|-----------|----------------------------------------------------|
| Light show (~11 s)          | ~13 µAh   | avg ~40% LED duty + ~0.5 mA MCU active             |
| Button press (~200 ms)      | ~11 µAh   | dead short through R1; dissipated inside the cell  |
| Standby (per day)           | ~100 µAh  | 4 µA sleep + ~0.25 µA battery self-discharge       |

The battery's own self-discharge (~1%/year for lithium primary cells) is negligible compared to
the MCU sleep current, which alone consumes ~35 mAh/year.

Expected battery life:

| Usage pattern               | Battery life      |
|-----------------------------|-------------------|
| Never pressed (shelf)       | ~5–6 years        |
| ~5 presses/day              | ~2 years          |
| ~30 presses/day (bar duty)  | ~7 months         |
| Theoretical max presses     | ~8,000            |

Rule of thumb: standby costs ~100 µAh/day and each press costs about a quarter-day of standby, so
below ~4 presses/day the sleep current dominates; above it, presses dominate.

## Demo

> TODO: Add demo pictures / video.
