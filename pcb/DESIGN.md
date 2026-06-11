# Coaster v0.3 — Design Specification

Goals: eliminate the v0.2 design shortcuts that the firmware currently compensates for
(see "Known quirks" in the README), modernize the MCU, and make programming painless.
Every change below maps to a lesson learned debugging v0.2.

## Summary of changes from v0.2

| # | Change | Replaces | Why |
|---|--------|----------|-----|
| 1 | MCU: ATtiny402-SSN (SOIC-8) | ATtiny13A-SSUR | In production, $0.65, real BOD, UPDI single-wire programming, 4KB flash / 256B SRAM headroom |
| 2 | Button on GPIO (PA6) to GND, wake via pin interrupt | Button dead-shorting the battery | Presses cost ~0 µAh instead of ~11; no more SRAM-destroying wake; richer UX (double-tap, long-press) |
| 3 | One series resistor per LED + low-side MOSFET driver | 4 LEDs straight on a pin through 0.1Ω | Predictable LED current, no pin-current limit, battery sag bounded by design instead of luck |
| 4 | 100nF decoupling + bulk capacitor | No capacitors at all | Transient immunity; rides through battery-holder micro-dropouts |
| 5 | 1×3 UPDI programming header | 6-pin ISP + hand-held cable | Three pads: UPDI/VDD/GND. No MOSI/MISO/SCK conflicts possible; LEDs can't interfere with programming by construction |

## MCU pin map (ATtiny402, SOIC-8)

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
- Q1 must be a logic-level FET (AO3400A: Vgs(th) 0.65-1.45V, fully enhanced at 2.5V).
  A 2N7002 (Vgs(th) up to 2.5V worst-case) would be driven barely above threshold for
  most of the cell's life and could read as dim/flickering LEDs on a worn battery.
- R5 (gate pulldown) keeps the LEDs off while PA3 floats during programming/reset.
- Decoupling C1 (100nF X7R) must sit physically adjacent to U1 pins 1/8.
- C2 (bulk, ≥22µF MLCC) anywhere near the battery holder.
- 150Ω per LED ≈ 2–4mA per LED across the battery's life (3.2V fresh → 2.8V worn);
  total LED load ~8–16mA. Through the MOSFET, the MCU pin only drives gate charge.
- J1: 1×3 pads, 2.54mm pitch, near the board edge: [UPDI | VDD | GND]. Through-hole
  pads preferred (a header can be pressed in at an angle or soldered for batch work).

## BOM (with JLCPCB catalog tier)

| Ref | Part | Package | LCSC # | Tier | ~Unit USD |
|-----|------|---------|--------|------|-----------|
| U1 | ATtiny402-SSN | SOIC-8 | C2053235 (-SSFR) | Extended | 0.65 |
| Q1 | AO3400A N-MOSFET | SOT-23 | C20917 | Basic | 0.01 |
| L1–L4 | White LED KT-0603W | 0603 | C2290 | Basic | 0.006 |
| R1–R4 | 150Ω | 0603 | any basic | Basic | 0.001 |
| R5 | 100kΩ | 0603 | any basic | Basic | 0.001 |
| C1 | 100nF X7R | 0603 | any basic | Basic | 0.001 |
| C2 | 22µF MLCC | 0805 | any basic | Basic | 0.01 |
| C3 | 100nF (debounce, optional) | 0603 | any basic | Basic | 0.001 |
| SW1 | Tactile switch | SMD | prefer a basic-catalog switch over TS-1187A | Basic if possible | 0.02 |
| BT1 | CR2016 holder MY-2016-02 | SMD | C2979176 | Extended | 0.16 |

Per-board parts ≈ $0.94 USD. Extended parts: U1 + BT1 (+SW1 if no basic alternative) →
$3 feeder fee each per order. Option: leave BT1 off the assembly and hand-solder it
(two large pads) to save the fee.

BT1 is a CR2016, not CR2032: same Ø20mm cell, but the MY-2016-02 holder is 2.2mm tall vs the
MY-2032-12's 3.6mm, slimming the enclosure (the holder was the tallest component). ~75mAh still
gives 2+ years at a few presses a day — µA sleep dominates and presses are now ~free.

## Ordering plan

30 boards, JLCPCB Economic assembly (30 is the Economic cap — the per-unit sweet spot).
Estimated ~$100–105 AUD shipped (economy mail). Confirm ATtiny402 stock/tier in the
JLCPCB parts library at order time; if out of stock, order assembly without U1 and
hand-solder the SOIC-8s.

## Firmware port checklist (ATtiny13A → ATtiny402)

- [ ] PWM: TCA0 in single-slope PWM, WO0 on PA3 (default PORTMUX routing)
- [ ] Button: PA6 input, internal pull-up (PORTA.PIN6CTRL), falling-edge interrupt, wake from power-down
- [ ] Sleep: SLPCTRL power-down; expected sleep current ~0.1–2µA (BOD in sampled mode)
- [ ] BOD: configured via FUSE.BODCFG at programming time — enabled at 1.8V, sampled mode in sleep
- [ ] Debounce in firmware (~20ms); C3 is belt-and-suspenders
- [ ] Show logic carries over: ramp, breathe ×5 ending on the dim phase, squared perceptual fade
- [ ] The v0.2 `PORF`-vs-brown-out check is no longer load-bearing (a GPIO/pin-interrupt wake is a
      normal wake, not a power-on); keep a minimal interrupted-show check for robustness, but
      fail-dark logic is now safe to use if desired
- [ ] Programming: avrdude 7.x supports serialupdi (any USB-serial adapter + 1 resistor), or pymcuprog

## First-article validation (before deploying all 30)

- [ ] Programming via UPDI header works
- [ ] Sleep current measured < 5µA
- [ ] Show plays on button press; press costs no measurable charge
- [ ] Worn-battery test: show degrades gracefully (dims) with no reset loop
- [ ] Bench-supply + series-resistor test (30–50Ω) simulating a dying cell
- [ ] Press during show, long-press, rapid double-press behave sanely
