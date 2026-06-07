# v0.3 hardware. design.py is the circuit (the source of truth); generate.py
# turns it into the committed coaster.kicad_pcb file.

build:
	python3 generate.py

# Board "test": DRC (clearances, shorts, unconnected copper). Connectivity
# against design.py is validated inside generate.py during build.
test: build
	kicad-cli pcb drc coaster.kicad_pcb --severity-error --exit-code-violations

# Review artifacts (only board.png is committed): render, 1:1 printable PDF for
# a paper fit check, and a STEP model for CAD interference checks.
review: build
	kicad-cli pcb render coaster.kicad_pcb -o board.png --side top --quality high --width 1600 --height 1600
	kicad-cli pcb export pdf coaster.kicad_pcb -o coaster-1to1.pdf --layers F.Cu,F.SilkS,Edge.Cuts,F.Mask
	kicad-cli pcb export step coaster.kicad_pcb -o coaster.step --subst-models

clean:
	rm -f coaster-*.rpt coaster-1to1.pdf coaster.step

.PHONY: build test review clean
