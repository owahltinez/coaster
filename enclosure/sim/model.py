"""Press-mechanics model of the v0.2.2 donut-piston Top.

The geometry is NOT reconstructed here. The Top is a solid of revolution, so its
press mechanics reduce exactly to a 2D axisymmetric slice -- and we obtain that
slice by *cutting the real FreeCAD solid* through its axis (``meridian_polygon``)
and meshing that section. Nothing in this file re-authors a sketch, a pad, or a
revolve: change the shape in FreeCAD and the simulation follows, because it reads
the shape, it does not rebuild it. The only data that lives here is what the CAD
does not contain -- the glass library and the press calibration.

Pipeline per run (all in the pinned FreeCAD container, which also ships gmsh+ccx):
  1. open the FCStd, slice the Top through an arm-free meridian  -> (r,z) polygon
  2. Gmsh meshes that polygon into quadratic axisymmetric triangles (CAX6)
  3. CalculiX solves a linear static ring load; we read the press-post travel

Coordinates in the slice: x = radius (mm), y = height (mm, the model's own z).
Units throughout: mm, N, MPa.
"""

import math
import os
import shutil
import subprocess

import FreeCAD as App
import Part

# Design file the geometry is sliced from (relative to this module's directory).
DESIGN_FILE = "../coaster-v0.2.2.FCStd"

# --- material (printed PETG; the absolute scale is calibrated out, see run.py) ---
# The press model is linear, so modulus only sets an overall compliance scale,
# which we calibrate away against a measured press. Only geometry *ratios* from
# the FE results survive into the predictions, so an approximate modulus is fine.
E_MPA = 2000.0
NU = 0.38

# Target element edge (mm): ~3 quadratic elements through the 0.4 mm membrane,
# which is what resolves its bending. In 2D this is cheap (~10k elements).
MESH_SIZE = 0.13

GRAVITY = 9.81e-3     # N per gram

# --- what the coaster feels: load radius, not base diameter ------------------
# A glass is a tube: the press force runs down its walls and enters the base as
# a RING at the wall radius -- not spread over the base, not at the base rim.
# So the input that matters is the load radius: ~the wall/contact-edge radius,
# shifted a few mm inboard for a flat base (the surface dishes away from the
# rim, concentrating contact inward). The model output is therefore a click-
# force-vs-load-radius CURVE; to predict a glass, read it at the glass's load
# radius. Per-glass absolute force carries ~+/-1 kg of inherent uncertainty for
# flat bases (sub-mm base flatness sets the exact contact), which is why we do
# not maintain a precise glass catalogue -- the curve plus a measured anchor is
# the honest tool.
CURVE_RADII = list(range(2, 39, 2))    # mm; ring-load sweep that builds the curve

# --- calibration: measured click forces on the current donut-34 print -------
# Each press records the force needed to click at a known contact location.
# A single press pins the absolute scale; two presses at different radii also
# cross-validate the model (it must predict their click-force ratio from the
# geometry alone). r0/r1 are the contact band (mm): a fingertip is a small
# central patch; two fingers on the ring approximate a ring load there.
CALIBRATION = {
    "presses": [
        # label,                     r0,   r1,  grams
        ("one finger, centre",       0.0,  6.0,   330),
        ("two fingers, donut mid",  20.0, 24.0,  1400),
    ],
    "primary": "two fingers, donut mid",   # absolute-scale anchor
}

# --- validation glasses: measured click at a known load radius --------------
# Independent checks (not used to set the scale): each is a real glass pressed
# on a kitchen scale, with its load radius estimated from its base. The model
# should reproduce these from the same calibration.
VALIDATION = [
    # label,                     load_r, measured_kg, note
    ("flat whiskey, 65 mm base",   29.5,    2.5, "flat base loads ~3 mm inboard of its 32.5 mm edge"),
    ("recessed tumbler",           22.0,    1.5, "contacts on its recess ring"),
]


def locate(binary):
    """Find gmsh / ccx on PATH or inside the FreeCAD install (host or container)."""
    found = shutil.which(binary)
    if found:
        return found
    candidates = [os.path.join(App.getHomePath(), "bin", binary),
                  f"/opt/squashfs-root/usr/bin/{binary}",
                  f"/Applications/FreeCAD.app/Contents/Resources/bin/{binary}"]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"{binary} not found (looked on PATH and {candidates})")


def _arm_present(poly):
    """True if the meridian carries material below the ring (a snap arm was cut)."""
    return any(r > 5.0 and z < 7.0 for r, z in poly)


def _meridian_at(shape, az_deg):
    """Ordered (r, z) boundary of the meridian section at one azimuth, r >= 0."""
    s = shape.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -az_deg)
    half = s.common(Part.makeBox(120, 240, 240, App.Vector(0, -120, -120)))
    wires = half.slice(App.Vector(0, 1, 0), 0.0)
    if not wires:
        return None
    wire = max(wires, key=lambda w: w.Length)
    poly = [(p.x, p.z) for p in wire.discretize(Deflection=0.03) if p.x >= -0.02]
    # collapse near-duplicate consecutive points and the closing repeat
    out = []
    for r, z in poly:
        r = max(r, 0.0)
        if not out or math.hypot(r - out[-1][0], z - out[-1][1]) > 1e-4:
            out.append((r, z))
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-4:
        out.pop()
    return out


def meridian_polygon(shape):
    """Cut the solid through an arm-free axial plane; return the (r,z) meridian.

    Sweeps azimuths to find one whose section misses the polar-patterned snap
    arms (they break axisymmetry and carry no press load), so the polygon is the
    pure body of revolution.
    """
    for az in range(0, 60, 5):
        poly = _meridian_at(shape, az)
        if poly and not _arm_present(poly):
            return az, poly
    raise RuntimeError("no arm-free meridian azimuth found")


def write_geo(path, poly, size=MESH_SIZE):
    """Write a Gmsh .geo meshing the meridian polygon into 2nd-order triangles."""
    lines = [f"lc = {size};"]
    n = len(poly)
    for i, (r, z) in enumerate(poly, 1):
        lines.append(f"Point({i}) = {{{r:.5f}, {z:.5f}, 0, lc}};")
    for i in range(1, n + 1):
        lines.append(f"Line({i}) = {{{i}, {i % n + 1}}};")
    lines.append("Line Loop(1) = {" + ", ".join(str(i) for i in range(1, n + 1)) + "};")
    lines.append("Plane Surface(1) = {1};")
    lines.append("Mesh.ElementOrder = 2;")
    lines.append("Mesh.Algorithm = 6;")   # frontal-delaunay: clean grading
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def run_gmsh(geo, msh, gmsh_bin):
    """Mesh the .geo into a 2D MSH 2.2 file."""
    subprocess.run([gmsh_bin, "-2", geo, "-o", msh, "-format", "msh22", "-v", "0"],
                   check=True, capture_output=True, text=True, timeout=300)


def parse_msh(path):
    """Parse Gmsh MSH 2.2: return (nodes {id:(r,z)}, tris [[6 node ids]])."""
    nodes, tris = {}, []
    with open(path) as fh:
        lines = fh.read().splitlines()
    i = 0
    while i < len(lines):
        tag = lines[i]
        if tag == "$Nodes":
            count = int(lines[i + 1])
            for k in range(count):
                p = lines[i + 2 + k].split()
                nodes[int(p[0])] = (float(p[1]), float(p[2]))
            i += 2 + count
        elif tag == "$Elements":
            count = int(lines[i + 1])
            for k in range(count):
                p = lines[i + 2 + k].split()
                etype, ntags = int(p[1]), int(p[2])
                if etype == 9:   # 6-node 2nd-order triangle
                    tris.append([int(x) for x in p[3 + ntags:3 + ntags + 6]])
            i += 2 + count
        else:
            i += 1
    return nodes, tris


def write_inp(path, nodes, tris, seat_in_r, load_r0, load_r1, force, rigid=False):
    """Write a CalculiX axisymmetric (CAX6) deck with a load over [load_r0, load_r1].

    BCs: the axis (r=0) is held radially; the ring underside over the seat band
    (r >= seat_in_r) rests on the bottom wall, held vertically.

    Contact model for the load band:
      rigid=False -> uniform pressure (soft presser: a fingertip, or a recessed
                     glass touching on a narrow ring).
      rigid=True  -> a rigid flat punch: the band nodes are tied to one vertical
                     displacement (*EQUATION), so a stiff flat glass base holds
                     its whole footprint planar and the pressure redistributes
                     itself toward the stiffer regions, as it physically does.
    """
    top_z = max(z for _, z in nodes.values())
    seat_nodes = [nid for nid, (r, z) in nodes.items() if r >= seat_in_r - 1e-3]
    seat_z = min(nodes[n][1] for n in seat_nodes)
    seat = [n for n in seat_nodes if nodes[n][1] <= seat_z + 0.15]
    axis = [nid for nid, (r, z) in nodes.items() if r < 0.02]
    band = [nid for nid, (r, z) in nodes.items()
            if z >= top_z - 0.05 and load_r0 - 1e-6 <= r <= load_r1 + 1e-6]
    if not band:
        raise ValueError(f"no top-face nodes in load band [{load_r0}, {load_r1}]")

    # CalculiX axisymmetric elements need positive (counter-clockwise) area in
    # the r-z plane; Gmsh may emit either winding, so flip the clockwise ones.
    def oriented(t):
        (r1, z1), (r2, z2), (r3, z3) = (nodes[t[0]], nodes[t[1]], nodes[t[2]])
        area2 = (r2 - r1) * (z3 - z1) - (r3 - r1) * (z2 - z1)
        return [t[0], t[2], t[1], t[5], t[4], t[3]] if area2 < 0 else t

    out = ["*HEADING", f"coaster top axisym, {force}N over r[{load_r0},{load_r1}]", "*NODE"]
    out += [f"{nid}, {r:.6f}, {z:.6f}" for nid, (r, z) in sorted(nodes.items())]
    out.append("*ELEMENT, TYPE=CAX6, ELSET=EALL")
    out += [f"{i}, " + ", ".join(map(str, oriented(t))) for i, t in enumerate(tris, 1)]
    out += ["*NSET, NSET=AXIS"] + [", ".join(map(str, axis[k:k+12])) for k in range(0, len(axis), 12)]
    out += ["*NSET, NSET=SEAT"] + [", ".join(map(str, seat[k:k+12])) for k in range(0, len(seat), 12)]
    out += ["*MATERIAL, NAME=PETG", "*ELASTIC", f"{E_MPA}, {NU}",
            "*SOLID SECTION, ELSET=EALL, MATERIAL=PETG",
            "*BOUNDARY", "AXIS, 1, 1, 0.", "SEAT, 2, 2, 0."]
    if rigid and len(band) > 1:
        # Tie every band node's vertical DOF to the band's reference node, so
        # the footprint stays planar (rigid flat punch). Total force on the ref.
        ref = max(band, key=lambda n: nodes[n][0])
        for nid in band:
            if nid != ref:
                out += ["*EQUATION", "2", f"{nid}, 2, 1.0, {ref}, 2, -1.0"]
        out += ["*STEP", "*STATIC", "*CLOAD", f"{ref}, 2, {-force:.6f}"]
    else:
        # Uniform pressure: each node carries force ~ its tributary circumference.
        rsum = sum(nodes[n][0] for n in band) or 1.0
        out += ["*STEP", "*STATIC", "*CLOAD"]
        out += [f"{nid}, 2, {-force * nodes[nid][0] / rsum:.6f}" for nid in band]
    out += ["*NODE FILE", "U", "*END STEP"]
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")
    return {"top_z": top_z, "seat_z": seat_z, "n_band": len(band)}


def parse_frd(path):
    """Return (coords, disp) keyed by node id from a CalculiX .frd."""
    coords, disp, block = {}, {}, None
    with open(path) as fh:
        for line in fh:
            if line.startswith("    2C"):
                block = "coord"
            elif " -4  DISP" in line:
                block = "disp"
            elif line.startswith(" -3"):
                block = None
            elif line.startswith(" -1") and block:
                nid = int(line[3:13])
                vals = [float(line[13 + k * 12:25 + k * 12])
                        for k in range((len(line.rstrip()) - 13) // 12)]
                (coords if block == "coord" else disp)[nid] = tuple(vals[:3])
    return coords, disp


def post_tip_travel(frd_path):
    """Downward travel (mm) of the press-post tip (the lowest axis node)."""
    coords, disp = parse_frd(frd_path)
    if not disp:
        raise ValueError(f"no displacements in {frd_path}")
    tip = min((n for n in coords if coords[n][0] < 0.5), key=lambda n: coords[n][1])
    return abs(disp[tip][1])
