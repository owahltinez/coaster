# Enclosure. coaster.FCStd is the CAD source of truth; export.py (run under
# FreeCAD's headless interpreter) validates it and exports STEP/STL per body.

build:
	freecadcmd export.py

# Enclosure "test": full recompute, every body must be a valid closed solid.
# (--pass forwards the remaining args to the script instead of freecadcmd.)
test:
	freecadcmd export.py --pass --check

# Press-mechanics simulation of the donut-piston Top (sim/). Slices the real
# solid, meshes the meridian section, and solves axisymmetric press loads in
# CalculiX (gmsh + ccx ship inside the FreeCAD container). Writes sim/results.md.
sim:
	freecadcmd sim/run.py
	@cat sim/results.md

clean:
	rm -f coaster-top.step coaster-top.stl coaster-bottom.step coaster-bottom.stl \
	  coaster-shield.step coaster-shield.stl sim/results.md sim/curve.svg

.PHONY: build test sim clean
