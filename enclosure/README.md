# Enclosure

3D-printed shell for the coaster. The top face is a spiral flexure that holds
the static weight of a glass but yields to a deliberate push, clicking the
tactile button at the center of the PCB.

> TODO: add the FreeCAD source and exported STL files.

## Design constraints (from the PCB)

- Board outline: 50 x 50 mm, 3 mm mounting holes in all four corners at
  (3, 3), (3, 47), (47, 3), (47, 47).
- The flexure must press the button at the board center.
- Center clearance: the LED ring sits 6 mm from center; a center press-post
  must stay narrower than ~9 mm so it does not cover the LEDs.
- Battery holder (CR2016, MY-2016-02) is 2.2mm tall — about button height, no longer
  the dominant constraint, but the base must still clear it.

To check fit against the actual board, run `make review` in `pcb/` to export
`coaster.step` and import it into the FreeCAD assembly.
