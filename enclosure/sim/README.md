# Press-mechanics simulation

Predicts the coaster's **click force** — how hard you must press, and where, to
actuate the center switch — directly from the CAD. Run it after changing the
Top to check the press feel before committing a print.

```bash
make sim                 # from the repo root: runs in the pinned container
make -C enclosure sim     # on the host (needs FreeCAD with bundled gmsh + ccx)
```

Outputs (regenerated each run, git-ignored): `results.md` (the report) and
`curve.svg` (the headline plot — click force vs. load radius).

---

## The method (reusable for any solid-of-revolution part)

This harness is a worked example of a general technique: **calibrated
axisymmetric FEA driven straight off the CAD solid.** The ideas below transfer
to any revolved mechanism (a snap dome, a diaphragm, a Belleville spring, a
press-fit boss).

### 1. Slice the real solid — don't reconstruct it

The Top is a solid of revolution, so its press mechanics reduce *exactly* to a
2D axisymmetric problem. Instead of re-authoring the shape as code (which then
drifts from the CAD), `model.meridian_polygon` **cuts the real FreeCAD solid**
through an arm-free axial plane and returns the `(r, z)` meridian outline. Gmsh
meshes that polygon into quadratic axisymmetric triangles (CAX6); CalculiX
solves a linear static load. Because the mesh *is* the sliced section, the
simulation can never disagree with the model — change the donut, the hinge, the
post, re-run, and the section follows. It also handles whatever the shape
becomes (corrugations, fillets) with no code change.

The snap arms break strict axisymmetry but carry no press load, so the slicer
sweeps azimuths to find a plane that misses them.

### 2. Why 2D, not the "real" 3D solid

A full 3D solve of the *actual* solid is the obvious thing to want, and it's the
wrong tool here. The press response is dominated by bending of the 0.4 mm
membrane/hinge, which needs ~3 elements through its thickness. In a 2D
axisymmetric slice that is free (~10k elements, sub-second). In 3D it forces
~0.13 mm elements across a 90 mm disk — millions of tetrahedra, minutes to mesh,
many minutes to hours to solve, and finicky to even mesh cleanly (we measured
this). Axisymmetry is the correct, cheap, *more accurate* tool for a revolved
part. 3D only earns its cost for genuinely non-axisymmetric questions (e.g. how
much an off-center glass *tilts*), which this design doesn't hinge on.

### 3. Calibrate the scale from one measured press

The model is linear, so the absolute modulus only sets an overall compliance
scale — it cancels. We fix that scale with **one measured click force**: press
the printed part at a known spot, read the grams at the click (`CALIBRATION`).
Everything else then follows from FE compliance *ratios*, which need no
material constant. (`E_MPA`, `MESH_SIZE` are solver settings, not design data.)

### 4. Validate with a second press at a different radius

With two measured presses at different radii, the model must reproduce their
**click-force ratio from geometry alone** — a real falsifiable check, not a fit.
Here the center press (330 g) and a two-finger press on the donut (1400 g) give
a 4.24× ratio; the model predicts it within ~10% and the two presses agree on
the absolute scale to ~10%. The residual is the center press's sensitivity to
how a fingertip's pressure distributes; the two-finger press (a clean ring) is
the robust scale anchor.

### 5. The output is a curve, because contact location is everything

A glass is a tube: the press force runs **down its walls** and enters the base
as a *ring at the wall radius* — not spread over the base, not at the base rim.
So the meaningful input is the **load radius**, and the output is a click-force-
vs-load-radius curve (`curve.svg`). To predict a glass, read the curve at its
load radius:

- **Recessed base** → loads on its recess ring (clean; the model nails it).
- **Flat base** → loads a few mm *inboard* of its contact edge (the surface
  dishes away from the rim under load), so use ~edge radius minus a few mm.

### 6. Don't model the presser — and know the limits

Modeling the glass as a body (contact analysis) was tried and isn't worth it:
its entire effect reduces to "a ring at the load radius," while a contact solve
adds fragile unilateral-contact nonlinearity and per-glass geometry — and it
would *not* remove the residual uncertainty, because that's set by sub-mm base
flatness. Honest accuracy budget: **point/finger presses and the curve *shape*
are reliable; flat-glass absolute force carries ~±1 kg** from contact detail.
That's fine for "comfortable and won't self-trigger," not a precision number.

---

## Files

- `model.py` — the model as data + functions: the calibration presses and
  validation glasses (the only inputs the CAD lacks), and the slice → mesh →
  solve → parse machinery. Geometry is read from the FCStd, never typed here.
- `run.py` — orchestration: slice + mesh once, solve the presses (scale +
  validation) and the radius sweep, write `results.md` and `curve.svg`.
- `gmsh` and `ccx` ship inside the pinned FreeCAD container, so `make sim`
  needs no extra tools; `model.locate` also finds them in a host FreeCAD.

## Reusing this on another part

1. Point `model.DESIGN_FILE` at the new FCStd; make sure the bodies/sketches the
   model reads by label (`Wall Profile` for the seat radius, etc.) exist or
   adjust `read_design`.
2. Print it, measure one click force to set `CALIBRATION`, and ideally a second
   at a different radius to validate.
3. `make sim`.

## Note on the design file

This models `enclosure/coaster-v0.2.2.FCStd` (the donut-piston redesign). The
canonical enclosure in this tree is still the v0.2 spiral (`coaster.FCStd`,
built by `export.py`); the two coexist until the donut design is promoted.
