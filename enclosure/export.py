"""Export the enclosure bodies from coaster.FCStd to STEP and STL.

Runs under FreeCAD's bundled headless interpreter (not plain python):

    freecadcmd export.py                   # validate + write STEP/STL per body
    freecadcmd export.py --pass --check    # validate only (no files written)

The document is recomputed from scratch and every body must produce a valid,
closed solid -- that is the enclosure's "build": a broken sketch reference or
failed boolean shows up here instead of in the slicer.
"""
import sys

import FreeCAD
import MeshPart
import Part

DOC = "coaster.FCStd"

# Body label -> exported file basename. Labels are the human names shown in
# the FreeCAD tree; basenames follow the repo's lowercase convention.
BODIES = {
    "Top": "coaster-top",
    "Bottom": "coaster-bottom",
    "Shield": "coaster-shield",
}

# STL tessellation: 0.05mm max deviation is well below a 0.4mm FDM nozzle.
STL_LINEAR_DEFLECTION_MM = 0.05
STL_ANGULAR_DEFLECTION_RAD = 0.5


def find_bodies(doc):
    """Map the expected body labels to their PartDesign bodies, or die."""
    by_label = {o.Label: o for o in doc.Objects if o.TypeId == "PartDesign::Body"}
    missing = sorted(set(BODIES) - set(by_label))
    if missing:
        raise SystemExit(f"missing bodies in {DOC}: {', '.join(missing)} "
                         f"(found: {', '.join(sorted(by_label)) or 'none'})")
    return {label: by_label[label] for label in BODIES}


def validate(doc, bodies):
    """Recompute the document and require a valid closed solid per body."""
    # Force a full recompute so stale shapes can't mask a broken feature.
    for obj in doc.Objects:
        obj.touch()
    doc.recompute(None, True, True)

    errors = []
    for obj in doc.Objects:
        if obj.State and "Invalid" in [str(s) for s in obj.State]:
            errors.append(f"{obj.Label} ({obj.Name}) failed to recompute")
    for label, body in bodies.items():
        shape = body.Shape
        if not shape.isValid():
            errors.append(f"body {label}: shape is not valid")
        elif not shape.Solids:
            errors.append(f"body {label}: no solid (open shell?)")
        elif not shape.isClosed():
            errors.append(f"body {label}: shape is not closed")
    if errors:
        raise SystemExit("enclosure validation failed:\n  " + "\n  ".join(errors))

    for label, body in bodies.items():
        bb = body.Shape.BoundBox
        print(f"validated {label}: solid, "
              f"{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm")


def export(bodies):
    """Write one STEP and one STL per body."""
    for label, body in bodies.items():
        base = BODIES[label]
        Part.export([body], f"{base}.step")
        mesh = MeshPart.meshFromShape(Shape=body.Shape,
                                      LinearDeflection=STL_LINEAR_DEFLECTION_MM,
                                      AngularDeflection=STL_ANGULAR_DEFLECTION_RAD,
                                      Relative=False)
        mesh.write(f"{base}.stl")
        print(f"wrote {base}.step, {base}.stl ({mesh.CountFacets} facets)")


def main():
    doc = FreeCAD.openDocument(DOC)
    bodies = find_bodies(doc)
    validate(doc, bodies)
    if "--check" not in sys.argv:
        export(bodies)


main()
