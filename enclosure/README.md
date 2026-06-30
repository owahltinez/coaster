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
| Bottom | Ø90 x 6.5  | Base tray holding the PCB |

Assembled height is **8.1 mm** (the lid nests into the tray). The tray wall is
the single height knob (`VarSet.BottomHeight`): the lid sits on the wall rim and
its placement, the snap-pocket depth, and the rim ceiling all track it, so
changing `BottomHeight` moves the whole interlock rigidly. The one feature that
does *not* track is the central `Press Post` (it grows down from the lid skin);
its length must change by the same amount in the opposite sense to keep the post
tip on the button — at `BottomHeight` 6.5 the post is 3.5 mm. (v0.3.0 shipped at
`BottomHeight` 7.5 / 9.1 mm tall; the tray was thinned 1.0 mm after the CR2016
holder replaced the CR2032.)

**This 1.0 mm is on probation — confirm it on a printed article before a batch.**
The constraint is not static fit but press deflection: the donut-piston deflects
~0.6 mm down at the battery-holder radius under a heavy glass press, and at a
6.5 mm tray it has only ~0.25 mm of static clearance over the holder there. So
the lid is expected to *graze* the holder under the heaviest glasses — which
stiffens the press rather than blocking the click (the holder adds a support, it
does not lock the centre post). An axisymmetric sim can't settle how much this
changes the feel; print one tray, drop in a populated board, and press a real
glass. If the press feels notably stiffer or the holder shows witness marks,
back `BottomHeight` off toward 7.0 (each 0.1 mm buys ~0.1 mm of clearance).

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
thin-walled, so a real print lands close): Top 8.3 cm³ (~10 g), Bottom 11.4 cm³
(~14 g) — about 24 g and ~$0.50 of filament per coaster. Re-slice to confirm.

## Liquid strategy

The coaster lives under sweating glasses. The v0.2 lid was a spiral flexure whose cuts
were an open path into the shell, plugged by a separate clear-PETG shield membrane. The
v0.3 donut-piston removes the problem instead of patching it: the top is a **continuous
solid skin with no through-cuts**, so drips and condensation that reach it shed outward and
never find a path to the electronics, the bare battery contact, or the switch. The lid is
its own barrier — which is why v0.3 has no Shield body.

**Anti-stick web.** A bare smooth skin has a second liquid problem: a sweat film between a
glass base and the flat top is a capillary bond — order ~N of pull, against the coaster's
own ~0.24 N weight — that lifts the whole lightweight coaster when the glass is raised. The
lift is killed by *venting*, not by removing contact area (even half the area still pulls
~N). The glass face carries a shallow **polar web** of grooves (0.4 mm deep × 1.4 mm wide)
that vents the film the instant the glass lifts:

- **6 concentric rings + a rim ring** put every contact point within ~1 mm of a channel, so
  no suction can build over a peeling patch (the transient pull scales as that distance⁴).
- **24 radial spokes** run to the rim, tying the ring network to open air, so the web vents
  for *any* glass-base size — not just bases small enough to overhang the pattern.

The grooves are **blind**: floors leave ≥ 1.2 mm of skin in the disc, so the waterproof
barrier is intact. The two thin (0.4 mm) flexure hinges are the only places a groove can't
freely go. The inner hinge and the central button/LED zone are left ungrooved; the spokes
cross the **outer** hinge over a **continuous 0.6 mm backing ring** on the underside, which
(a) lets the spoke notches cross without breaching (≥ 0.4 mm skin remains) and (b) backs the
hinge enough to make the click ~10% *firmer* than the smooth lid, offsetting the disc
softening from the rings. The ring is axisymmetric, so `sim/` predicts that press shift
directly; the spokes are the only non-axisymmetric feature and the sim slices around them.
A crosshatch was rejected: it can't cross the thin hinge without islanding the membrane, and
a Cartesian grid fights a circular boundary.

## Press mechanics

The donut-piston's click force and travel are simulated in `sim/` — an axisymmetric FEA
of the Top sliced straight from this `coaster.FCStd` and calibrated to a measured press.
See `sim/README.md`.

## Snap arms (known weak point)

The six cantilever arms latch the lid into the tray pockets, and they are the enclosure's
fragility hotspot. The flexing beam is short (~1.5 mm), so even the ~0.25 mm it deflects
to clear the wall lip on insertion is a high bending strain at the root — the arms crack
there. Levers, in order of effect:

- **Beam thickness** (`Sketch004` datum 16, the radial dimension) — set to **1.6 mm**, the
  thickest the root fillets allow with the hook at mid-beam (1.8 mm+ makes the fillets fail
  to resolve). Two effects trade off: thicker prints more robustly with better layer bonding
  (a thin ~1.0 mm arm prints as a fragile near-single-wall column), but thicker also raises
  the bending strain on the ~0.25 mm snap-over. Which dominates is a print-test question.
  That thick + fillet fight for room at the root is the argument for eventually moving the
  hook to the tip — it frees the root for a thick, well-filleted, long-flexing beam.
- **Material** — print in **PETG** (ductile; the press sim assumes it). PLA snaps.
- **Orientation** — the arms bend radially, so on a flat-printed lid the layer lines run
  *across* the bending plane and the root fails by delamination regardless of strain. There
  is no single orientation that favours all six radial arms; print with extra perimeters so
  the beam is near-solid, and treat orientation as a likely co-cause if cracking persists.
- **Root fillets** — outer (tension-side) and inner both 0.8 mm; relieve the stress
  concentration only, not the bulk strain.

If thinning + PETG + perimeters still isn't enough, the cantilever is at the limit of what
this footprint allows and the retention method itself should be reconsidered.

Lateral fit between lid and tray is set entirely by the arms in their pockets — the lid
just rests on the wall rim, there is no separate register. The tangential fit is
`Pocket002.Length` minus the arm width `Pad003.Length` (4.0 mm), and it is a per-printer
tuning knob: the model is line-to-line radially and the pocket runs 0.1 mm wider than the
arm tangentially (`Pocket002.Length` = 4.1), so most felt play is print tolerance opening
the fit. Tighten `Pocket002.Length` toward 4.0 if the lid wobbles; loosen it if the lid
binds going on.

## Design constraints (50 x 50 mm board)

- Board outline: 50 x 50 mm, 3 mm mounting holes in all four corners at
  (3, 3), (3, 47), (47, 3), (47, 47).
- The piston must press the button at the board center.
- Center clearance: the LED ring sits 6 mm from center; the central press post
  must stay narrow enough not to cover the LEDs.
- The UPDI programming header (J1, near a board-edge corner) must stay reachable,
  or accept opening the shell to reflash.
