# Enclosure. coaster.FCStd is the CAD source of truth; export.py (run under
# FreeCAD's headless interpreter) validates it and exports STEP/STL per body.

build:
	freecadcmd export.py

# Enclosure "test": full recompute, every body must be a valid closed solid.
# (--pass forwards the remaining args to the script instead of freecadcmd.)
test:
	freecadcmd export.py --pass --check

clean:
	rm -f coaster-top.step coaster-top.stl coaster-bottom.step coaster-bottom.stl \
	  coaster-shield.step coaster-shield.stl

.PHONY: build test clean
