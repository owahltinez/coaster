# Enclosure

3D-printed shell for the coaster. The top face is a spiral flexure that holds
the static weight of a glass but yields to a deliberate push, clicking the
tactile button at the center of the PCB.

`coaster.FCStd` (FreeCAD) is the CAD source of truth. It contains three bodies,
each exported as its own print/CAD artifact:

| Body   | Size (mm)        | What it is |
|--------|------------------|------------|
| Top    | Ø90 x 5.6        | Lid with the spiral flexure pressing the center button |
| Bottom | Ø90 x 7.5        | Base tray holding the PCB |
| Shield | Ø88 x 0.6        | Thin insert between the PCB and the top face |

## Building

Requires FreeCAD (the Makefile finds `freecadcmd` on PATH or in the macOS app
bundle). Same verbs as the other subdirectories:

```bash
make build   # validate + export coaster-{top,bottom,shield}.{step,stl}
make test    # validate only: full recompute, every body a valid closed solid
make clean
```

The STL files are the 3D printing assets; the STEP files are for CAD
interference checks against the board (`make -C ../pcb review` exports the
matching `coaster.step` board model).

## Liquid strategy

The coaster lives under sweating glasses, and the spiral cuts in the flexure are an open
path into the shell. The Shield is the answer: a continuous membrane over the whole PCB,
so drips and condensation that get through the flexure land on it and shed outward
instead of reaching the electronics, the bare battery contact, or the switch. It is
printed in clear PETG (not PLA like the rest of the shell): the LED light has to pass
through it, and a wet-environment membrane should not hydrolyze.

The shield currently snap-fits around the center press-post by hoop tension, which has
two long-term weaknesses: plastic creep slowly relaxes the grip, and every button press
flexes the already-stressed hole edge. Planned change (CAD TODO): a shallow retention
groove in the post at shield height, so the shield drops in over a chamfered tip and
seats relaxed -- located by shape, with no standing stress.

## Design constraints (v0.2 board, which this enclosure fits)

- Board outline: 50 x 50 mm, 3 mm mounting holes in all four corners at
  (3, 3), (3, 47), (47, 3), (47, 47).
- The flexure must press the button at the board center.
- Center clearance: the LED ring sits 6 mm from center; a center press-post
  must stay narrower than ~9 mm so it does not cover the LEDs.

## Changes for a future v0.3 enclosure

- Battery holder shrinks: the CR2016 holder (MY-2016-02) is 2.2 mm tall vs the
  v0.2 CR2032 holder's 3.6 mm — about button height, no longer the dominant
  thickness constraint.
- The UPDI programming header (J1, board edge near a corner) replaces the ISP
  header; keep it reachable or accept opening the shell to reflash.
