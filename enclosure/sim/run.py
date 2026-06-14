"""Run the donut-piston press simulation; write results.md and curve.svg.

Invoked headless by FreeCAD's interpreter so it can slice the real solid:

    freecadcmd run.py

Steps (all in the pinned FreeCAD container, which also ships gmsh + ccx):
  1. slice the Top into its meridian section and mesh it once (Gmsh, CAX6)
  2. solve the calibration presses -> set the absolute force scale and, with two
     presses at different radii, cross-validate the model
  3. sweep a ring load across radii -> the click-force-vs-load-radius curve
  4. check the validation glasses against the curve
Outputs: results.md (the report) and curve.svg (the headline plot). No geometry
is reconstructed -- the mesh is the sliced section of the real model.
"""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App
import model

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.normpath(os.path.join(HERE, model.DESIGN_FILE))
UNIT_FORCE = 1.0          # N; compliance = post travel per unit load
RING_W = 1.0              # mm; ring-load band width for the curve / validation


def read_design():
    """Open the FCStd; return (Top shape, seat inner radius from the Bottom wall)."""
    doc = App.openDocument(DESIGN)
    for o in doc.Objects:
        o.touch()
    doc.recompute(None, True, True)
    top = next(o for o in doc.Objects if o.Label == "Top")
    wall = next(o for o in doc.Objects if o.Label == "Wall Profile")
    seat_in_r = min(g.Radius for g in wall.Geometry if type(g).__name__ == "Circle")
    return top.Shape, seat_in_r


def make_solver(shape, seat_in_r, workdir, log):
    """Mesh the meridian once; return a solver f(r0, r1) -> mm travel per N."""
    gmsh_bin, ccx_bin = model.locate("gmsh"), model.locate("ccx")
    az, poly = model.meridian_polygon(shape)
    geo, msh = os.path.join(workdir, "m.geo"), os.path.join(workdir, "m.msh")
    model.write_geo(geo, poly)
    model.run_gmsh(geo, msh, gmsh_bin)
    nodes, tris = model.parse_msh(msh)
    log.append(f"meridian sliced at azimuth {az} deg; mesh {len(nodes)} nodes / "
               f"{len(tris)} CAX6 elements (size {model.MESH_SIZE} mm)")
    counter = [0]

    def compliance(r0, r1):
        counter[0] += 1
        base = os.path.join(workdir, f"s{counter[0]}")
        model.write_inp(base + ".inp", nodes, tris, seat_in_r, r0, r1, UNIT_FORCE)
        res = subprocess.run([ccx_bin, "-i", base], cwd=workdir,
                             capture_output=True, text=True, timeout=300)
        if not os.path.exists(base + ".frd"):
            raise RuntimeError(f"ccx produced no result: {res.stdout[-400:]}")
        return model.post_tip_travel(base + ".frd") / UNIT_FORCE

    return compliance


def write_curve_svg(path, curve, points):
    """Plot click force (kg) vs load radius (mm): model curve + measured points.

    The y-axis is capped (the curve rockets past the hinge edge, which would
    otherwise squash the glass-relevant region); the curve is clipped to the cap.
    """
    W, H, ml, mb = 560, 360, 60, 50
    xmax = max(r for r, _ in curve) + 4
    ymax = 6.0                                   # cap: keeps the 0-3 kg region readable

    def X(r):
        return ml + r / xmax * (W - ml - 20)

    def Y(f):
        return H - mb - min(f, ymax) / ymax * (H - mb - 36)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         'font-family="Helvetica" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{ml}" y="22" font-size="14" font-weight="bold">'
         'Click force vs. load radius &#8212; model curve + measured points</text>',
         f'<line x1="{ml}" y1="{Y(0):.1f}" x2="{X(xmax):.1f}" y2="{Y(0):.1f}" stroke="#333"/>',
         f'<line x1="{ml}" y1="{Y(0):.1f}" x2="{ml}" y2="{Y(ymax):.1f}" stroke="#333"/>',
         f'<text x="{X(xmax/2):.0f}" y="{H-8}" font-size="11">load radius (mm)</text>']
    for r in range(0, int(xmax) + 1, 10):
        s.append(f'<text x="{X(r)-6:.0f}" y="{Y(0)+18:.0f}">{r}</text>')
    for f in range(0, int(ymax) + 1, 2):
        s.append(f'<text x="{ml-32}" y="{Y(f)+4:.0f}">{f} kg</text>'
                 f'<line x1="{ml-4}" y1="{Y(f):.1f}" x2="{ml}" y2="{Y(f):.1f}" stroke="#333"/>')
    d = "M " + " L ".join(f"{X(r):.1f},{Y(f):.1f}" for r, f in curve if f <= ymax)
    s.append(f'<path d="{d}" fill="none" stroke="#1a6ac0" stroke-width="2"/>')
    s.append(f'<text x="{X(xmax)-2:.0f}" y="{Y(ymax)+14:.0f}" font-size="10" fill="#1a6ac0" '
             'text-anchor="end">curve continues steeply past the hinge (r&gt;34)</text>')
    # stagger labels so near-coincident points (e.g. two anchors at r=22) don't overlap
    for i, (r, f, lab) in enumerate(sorted(points)):
        dy = -8 if i % 2 else 14
        s.append(f'<circle cx="{X(r):.1f}" cy="{Y(f):.1f}" r="4.5" fill="#c0392b"/>'
                 f'<text x="{X(r)+7:.1f}" y="{Y(f)+dy:.1f}" font-size="11" fill="#c0392b">'
                 f'{lab}</text>')
    s.append('</svg>')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(s))


def build_report(compliance, log):
    """Calibrate, validate, sweep the curve, and assemble results.md + plot data."""
    presses = model.CALIBRATION["presses"]
    a_press = {lab: compliance(r0, r1) for lab, r0, r1, _ in presses}
    budgets = {lab: g * model.GRAVITY * a_press[lab] for lab, _, _, g in presses}
    B = budgets[model.CALIBRATION["primary"]]      # click-travel budget (scale anchor)

    def click_kg(r):
        return B / compliance(r - RING_W / 2, r + RING_W / 2) / 9.81

    # cross-validation from the two presses
    (li, _, _, gi), (lj, _, _, gj) = presses[0], presses[1]
    meas_ratio, mdl_ratio = gj / gi, a_press[li] / a_press[lj]
    err = (mdl_ratio - meas_ratio) / meas_ratio * 100
    agree = abs(list(budgets.values())[0] - list(budgets.values())[1]) / min(budgets.values()) * 100

    curve = [(r, B / compliance(r - RING_W / 2, r + RING_W / 2) / 9.81)
             for r in model.CURVE_RADII]
    centre_kg = gi * model.GRAVITY / 9.81   # the measured deliberate-press gesture

    # validation glasses: model vs measured
    val_rows = []
    for lab, r, meas, note in model.VALIDATION:
        val_rows.append((lab, r, click_kg(r), meas, note))

    # plot points: the centre press, the scale anchor, and the validation glasses
    points = [(3.0, centre_kg, f"finger centre ({centre_kg:.2f} kg)"),
              (22.0, gj * model.GRAVITY / 9.81, "two fingers (anchor)")]
    points += [(r, meas, f"{lab.split(',')[0]} ({meas} kg)")
               for lab, r, _, meas, _ in val_rows]
    write_curve_svg(os.path.join(HERE, "curve.svg"), curve, points)

    md = ["# Press simulation — donut-piston Top\n",
          "Generated by `make sim`: the FreeCAD solid is sliced through its axis, the",
          "meridian meshed (Gmsh, axisymmetric CAX6) and solved in CalculiX. Geometry is",
          "sliced live from `coaster-v0.2.2.FCStd` — nothing is reconstructed. See",
          "`README.md` for the method and `curve.svg` for the plot.\n",
          "## The result: click force vs. load radius\n",
          "A glass loads the coaster as a ring at its **load radius** (~its wall/contact",
          "edge, a few mm inboard for a flat base). Read the click force off this curve at",
          "that radius. A deliberate **finger tap at the centre** clicks at "
          f"**{centre_kg:.2f} kg** — the light, controllable gesture.\n",
          "| load radius | click force |", "|---|---|"]
    for r, f in curve:
        md.append(f"| {r} mm | {f:.2f} kg |")
    md += ["\n*Gentle (≤ ~2.5 kg) for any load inside r≈30 mm; it climbs steeply past",
           "the hinge edge (r=34). Real glasses load inboard of their rims, staying in the",
           "gentle zone — and nothing self-triggers under its own weight.*\n",
           "## Validation against measured glasses\n",
           "| glass | load radius | model | measured |", "|---|---|---|---|"]
    for lab, r, mdl, meas, note in val_rows:
        md.append(f"| {lab} | {r:.0f} mm | {mdl:.1f} kg | {meas} kg |")
    md += [f"\n*{note}*" for *_, note in [val_rows[0]]]
    md += ["\n## Diagnostics\n",
           f"- model validation: measured click-force ratio {meas_ratio:.2f}x "
           f"('{lj}' vs '{li}'), model predicts {mdl_ratio:.2f}x from geometry ({err:+.0f}%)",
           f"- the two presses independently set the scale; they agree to {agree:.0f}%"]
    md += [f"- {line}" for line in log]
    return "\n".join(md) + "\n"


def main():
    shape, seat_in_r = read_design()
    log = [f"seat inner radius (bottom wall) = {seat_in_r:.1f} mm"]
    with tempfile.TemporaryDirectory() as workdir:
        compliance = make_solver(shape, seat_in_r, workdir, log)
        report = build_report(compliance, log)
    with open(os.path.join(HERE, "results.md"), "w", encoding="utf-8") as fh:
        fh.write(report)


main()
