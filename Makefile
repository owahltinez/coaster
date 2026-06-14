# Top-level Makefile. Each subdirectory has a self-contained Makefile with the
# same verbs (build / test / clean); this forwards to both from the repo root.
# Domain-specific verbs forward to the one subdir that has them.
#
# The artifact-producing toolchains run in pinned containers (see tools/): the
# committed board is KiCad-10 format and host KiCad drifts (Debian's v9 cannot
# even open it), and the ATtiny202 firmware needs avr-gcc >= 12 — pinning both
# is what makes the board, the fab bundle, and the binary reproducible here and
# in CI. `docker` is a podman alias locally; override CONTAINER_ENGINE for
# another runtime. Rootless podman maps container-root to your UID (--user 0),
# so files generated in the mount come back owned by you. The rule is: produce
# artifacts in a container, touch hardware on the host — so `make flash` /
# `make fuses` stay on the host (USB-serial adapter + udev rule); everything
# else (firmware build, board, enclosure) runs in its pinned container.
CONTAINER_ENGINE ?= docker
KICAD_IMAGE      ?= coaster-pcb
FW_IMAGE         ?= coaster-fw
CAD_IMAGE        ?= coaster-cad
DOCKER_RUN        = $(CONTAINER_ENGINE) run --rm --user 0 -v $(CURDIR):/work -w /work
PCB_RUN          ?= $(DOCKER_RUN) $(KICAD_IMAGE)
FW_RUN           ?= $(DOCKER_RUN) $(FW_IMAGE)
CAD_RUN          ?= $(DOCKER_RUN) $(CAD_IMAGE)

.PHONY: build test clean flash fuses review fab sim image image-pcb image-fw image-cad

# Build the pinned toolchain images (run once, and after editing a Containerfile).
image: image-pcb image-fw image-cad
image-pcb:
	$(CONTAINER_ENGINE) build -t $(KICAD_IMAGE) -f tools/Containerfile.pcb tools
image-fw:
	$(CONTAINER_ENGINE) build -t $(FW_IMAGE) -f tools/Containerfile.fw tools
image-cad:
	$(CONTAINER_ENGINE) build -t $(CAD_IMAGE) -f tools/Containerfile.cad tools

build:
	$(FW_RUN) make -C firmware build
	$(PCB_RUN) make -C pcb build
	$(CAD_RUN) make -C enclosure build

test:
	$(FW_RUN) make -C firmware test
	$(PCB_RUN) make -C pcb test
	$(CAD_RUN) make -C enclosure test

clean:
	$(MAKE) -C firmware clean
	$(MAKE) -C pcb clean
	$(MAKE) -C enclosure clean

# firmware only: program the chip, set fuses (host — needs the USB-serial adapter)
flash fuses:
	$(MAKE) -C firmware $@

# pcb only: render / 1:1 PDF / STEP, and the JLCPCB order bundle (in the container)
review fab:
	$(PCB_RUN) make -C pcb $@

# enclosure only: press-mechanics simulation of the donut-piston Top (in the container)
sim:
	$(CAD_RUN) make -C enclosure sim
