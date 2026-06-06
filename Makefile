BIN=main
OBJS=${BIN}.o
MODEL=ATTINY13A
PROGRAMMER=usbasp
PORT=usb
# Slow ISP clocks: the LEDs hang on MOSI, so writes (long MOSI data bursts
# that drive the LED bank through the programmer) silently truncate at higher
# clocks over a marginal hand-held contact. Reads are more tolerant (data
# returns on the unloaded MISO line) but verify at the slowest clock anyway.
# Write without inline verify, then verify in a separate pass.
ISP_CLOCK=32kHz
ISP_CLOCK_VERIFY=16kHz
AVRDUDE=avrdude -c ${PROGRAMMER} -p ${MODEL} -P ${PORT}

CC=avr-gcc
OBJCOPY=avr-objcopy
CFLAGS=-Os -DF_CPU=1200000UL -mmcu=$(shell echo ${MODEL} | tr '[:upper:]' '[:lower:]')

${BIN}.hex: ${BIN}.elf
	${OBJCOPY} -O ihex -R .eeprom $< $@

${BIN}.elf: ${OBJS}
	${CC} -o $@ $^

install: ${BIN}.hex
	${AVRDUDE} -B ${ISP_CLOCK} -V -U flash:w:$<
	${AVRDUDE} -B ${ISP_CLOCK_VERIFY} -U flash:v:$<

# One-time per chip: enable the brown-out detector at 1.8V (see README).
fuses:
	${AVRDUDE} -B ${ISP_CLOCK} -U hfuse:w:0xfd:m

# Try to reset a wedged USBasp (USB errors / "cannot find USB device"). Only
# works for a mild wedge where the device still enumerates; if its USB stack
# hung completely (gone from lsusb -- happens when the ISP cable hot-detaches
# from the board), only a physical replug recovers it. Prevention: unplug the
# programmer from USB *before* taking the ISP cable off the board.
reset:
	@python3 -c "import fcntl, re, subprocess; \
	  out = subprocess.check_output(['lsusb']).decode(); \
	  m = re.search(r'Bus (\d+) Device (\d+).*16c0:05dc', out); \
	  fcntl.ioctl(open('/dev/bus/usb/%s/%s' % (m[1], m[2]), 'wb'), 0x5514); \
	  print('USBasp reset OK')" \
	|| echo "USBasp is off the bus: unplug and replug it."

clean:
	rm -f ${BIN}.elf ${BIN}.hex ${OBJS}

.PHONY: install fuses reset clean
