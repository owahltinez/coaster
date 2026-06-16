# Enclosure

3D-printed shell for the coaster. The top is a solid "donut-piston": a
continuous disc that holds the static weight of a glass but deflects as a whole
— piston-style, carried on a ring of snap arms — to click the tactile button at
the center of the PCB. (The v0.2 lid was a spiral flexure; v0.3 replaced it with
this solid piston.)

`coaster.FCStd` (FreeCAD) is the CAD source of truth. It contains two bodies,
each exported as its own print/CAD artifact:

| Body   | Size (mm)  | What it is |
|--------|------------|------------|
| Top    | Ø90 x 5.4  | Solid donut-piston lid: skin + central press post + 6 snap arms |
| Bottom | Ø90 x 7.5  | Base tray holding the PCB |

## Building

The build runs in a pinned FreeCAD 1.1.1 container (`tools/Containerfile.cad`), so the
host needs no FreeCAD — `make image` (from the repo root) builds it once. The source is
authored in FreeCAD 1.1; stable 1.0.0 breaks the sketch/Origin attachment, so the
version is pinned to match. Same verbs as the other subdirectories (run from the repo
root so they route through the container, or `make -C enclosure …` inside it):

```bash
make build   # validate + export coaster-{top,bottom}.{step,stl}
make test    # validate only: full recompute, every body a valid closed solid
make clean
```

The STL files are the 3D printing assets; the STEP files are for CAD
interference checks against the board (`make -C ../pcb review` exports the
matching `coaster.step` board model).

Material use (solid volume from the model × 1.24 g/cm³ PLA; the bodies are
thin-walled, so a real print lands close): Top 8.3 cm³ (~10 g), Bottom 11.9 cm³
(~15 g) — about 25 g and ~$0.50 of filament per coaster. Re-slice to confirm.

## Liquid strategy

The coaster lives under sweating glasses. The v0.2 lid was a spiral flexure whose cuts
were an open path into the shell, plugged by a separate clear-PETG shield membrane. The
v0.3 donut-piston removes the problem instead of patching it: the top is a **continuous
solid skin with no cuts**, so drips and condensation that reach it shed outward and never
find a path to the electronics, the bare battery contact, or the switch. The lid is its
own barrier — which is why v0.3 has no Shield body.

## Press mechanics

The donut-piston's click force and travel are simulated in `sim/` — an axisymmetric FEA
of the Top sliced straight from this `coaster.FCStd` and calibrated to a measured press.
See `sim/README.md`.

## Design constraints (50 x 50 mm board)

- Board outline: 50 x 50 mm, 3 mm mounting holes in all four corners at
  (3, 3), (3, 47), (47, 3), (47, 47).
- The piston must press the button at the board center.
- Center clearance: the LED ring sits 6 mm from center; the central press post
  must stay narrow enough not to cover the LEDs.
- The UPDI programming header (J1, near a board-edge corner) must stay reachable,
  or accept opening the shell to reflash.
