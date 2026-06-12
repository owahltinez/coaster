#!/usr/bin/env python3
"""Generate the JLCPCB order bundle from coaster.kicad_pcb + design.py.

    python fab.py        # writes dist/coaster-gerbers.zip, -bom.csv, -cpl.csv

JLCPCB takes exactly three uploads to fabricate and assemble a board — Gerbers,
a BOM, and a CPL (pick-and-place) — and this writes all three. Nothing about
the parts is invented here: every LCSC number, every assembly exclusion, and
every rotation correction comes from design.py (the circuit as data), so the
bundle is generated and never hand-maintained.

Run generate.py first if design.py changed (the Makefile's `fab` target does);
this reads the committed board for geometry and design.py for part data.
"""
import csv
import os
import re
import subprocess
import sys
import zipfile

import design

BOARD = "coaster.kicad_pcb"
OUT = "dist"
GERBER_DIR = os.path.join(OUT, "gerbers")
# 2-layer board: copper, mask, silk, edge cuts. (No paste — JLCPCB makes the
# stencil from the pad geometry in the copper/mask layers.)
GERBER_LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def run(*args):
    subprocess.run(args, check=True)


def export_gerbers():
    os.makedirs(GERBER_DIR, exist_ok=True)
    for f in os.listdir(GERBER_DIR):
        os.remove(os.path.join(GERBER_DIR, f))
    run("kicad-cli", "pcb", "export", "gerbers", BOARD,
        "-o", GERBER_DIR + os.sep, "--layers", GERBER_LAYERS, "--no-protel-ext")
    run("kicad-cli", "pcb", "export", "drill", BOARD,
        "-o", GERBER_DIR + os.sep, "--format", "excellon", "--excellon-units", "mm")
    zip_path = os.path.join(OUT, "coaster-gerbers.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(GERBER_DIR)):
            z.write(os.path.join(GERBER_DIR, f), f)  # flat: gerbers at the zip root
    return zip_path


def read_pos():
    """KiCad CPL for every footprint: [(ref, package, x, y, rot, side), ...]."""
    pos_csv = os.path.join(OUT, "_kicad_pos.csv")
    run("kicad-cli", "pcb", "export", "pos", BOARD,
        "-o", pos_csv, "--format", "csv", "--units", "mm", "--side", "both")
    rows = []
    with open(pos_csv, newline="") as fp:
        for r in csv.DictReader(fp):
            rows.append((r["Ref"], r["Package"], float(r["PosX"]),
                         float(r["PosY"]), float(r["Rot"]), r["Side"]))
    os.remove(pos_csv)
    return rows


def placed_refs(rows):
    """Refs JLCPCB should place: on the board, not in ASSEMBLY_EXCLUDE."""
    return [r for r in rows if r[0] not in design.ASSEMBLY_EXCLUDE]


def write_cpl(rows):
    path = os.path.join(OUT, "coaster-cpl.csv")
    with open(path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, _pkg, x, y, rot, side in sorted(placed_refs(rows), key=ref_key):
            fpid = design.PARTS[ref].footprint
            rot = (rot + design.ROTATION_CORRECTION.get(fpid, 0)) % 360
            layer = "Top" if side.lower().startswith("t") else "Bottom"
            w.writerow([ref, f"{x:.4f}", f"{y:.4f}", layer, f"{rot:.0f}"])
    return path


def write_bom(rows):
    path = os.path.join(OUT, "coaster-bom.csv")
    groups, missing = {}, []
    for ref, _pkg, *_ in sorted(placed_refs(rows), key=ref_key):
        lcsc = design.LCSC.get(ref)
        if not lcsc:
            missing.append(ref)
        value = design.PARTS[ref].value
        footprint = design.PARTS[ref].footprint.split(":")[-1]
        groups.setdefault((value, footprint, lcsc or ""), []).append(ref)
    with open(path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, footprint, lcsc), refs in sorted(groups.items()):
            w.writerow([value, ",".join(sorted(refs, key=ref_key_str)),
                        footprint, lcsc])
    return path, missing


def ref_key(row):
    return ref_key_str(row[0])


def ref_key_str(ref):
    m = re.match(r"([A-Za-z]+)(\d*)", ref)
    return (m.group(1), int(m.group(2) or 0))


def main():
    os.makedirs(OUT, exist_ok=True)
    zip_path = export_gerbers()
    rows = read_pos()
    cpl_path = write_cpl(rows)
    bom_path, missing = write_bom(rows)
    placed = placed_refs(rows)

    print(f"wrote {zip_path}")
    print(f"wrote {bom_path}  ({len(placed)} parts placed)")
    print(f"wrote {cpl_path}")
    print()
    print("Before you pay:")
    print("  - White soldermask (the board is the reflector behind the LEDs).")
    print("  - Confirm ATtiny202 (C2052951) stock; ATtiny402 is the drop-in.")
    print("  - On the assembly preview, verify orientations — esp. BT1's mouth")
    print("    facing the WEST board edge. Record any fix in design.py's")
    print("    ROTATION_CORRECTION (keyed by footprint) and re-run.")
    if not design.ROTATION_CORRECTION:
        print("    (ROTATION_CORRECTION is empty: CPL angles are raw KiCad angles.)")
    if missing:
        raise SystemExit(f"\nERROR: no LCSC number for placed parts: {missing}\n"
                         "Add them to design.py's LCSC map (or ASSEMBLY_EXCLUDE).")


if __name__ == "__main__":
    sys.exit(main())
