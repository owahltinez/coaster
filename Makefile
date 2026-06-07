# Top-level Makefile. Each subdirectory has a self-contained Makefile with the
# same verbs (build / test / clean); this forwards to both from the repo root.
# Domain-specific verbs forward to the one subdir that has them.

.PHONY: build test clean flash fuses reset review

build:
	$(MAKE) -C firmware build
	$(MAKE) -C pcb build

test:
	$(MAKE) -C firmware test
	$(MAKE) -C pcb test

clean:
	$(MAKE) -C firmware clean
	$(MAKE) -C pcb clean

# firmware only: program the chip, set fuses, recover a wedged programmer
flash fuses reset:
	$(MAKE) -C firmware $@

# pcb only: render / 1:1 PDF / STEP
review:
	$(MAKE) -C pcb $@
