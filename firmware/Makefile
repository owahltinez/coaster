BIN=main
OBJS=${BIN}.o
MODEL=attiny202
# ATtiny202 program flash size, in bytes (the "test" target checks the fit)
FLASH_BYTES=2048
# UPDI programming needs no dedicated programmer: any USB-serial adapter with
# TX bridged to RX through a ~1k resistor, RX to the board's UPDI pad, plus
# VDD/GND. avrdude's serialupdi driver does the rest. Remove the coin cell
# before connecting -- the adapter drives VDD and would back-feed the cell.
PROGRAMMER=serialupdi
PORT?=$(firstword $(wildcard /dev/tty.usbserial* /dev/ttyUSB*))
AVRDUDE=avrdude -c ${PROGRAMMER} -p ${MODEL} -P ${PORT}

CC=avr-gcc
OBJCOPY=avr-objcopy
# 20MHz internal oscillator / 6 (the default prescaler) = 3.33MHz
CFLAGS=-Os -DF_CPU=3333333UL -mmcu=${MODEL}

build: ${BIN}.hex

${BIN}.hex: ${BIN}.elf
	${OBJCOPY} -O ihex -R .eeprom $< $@

${BIN}.elf: ${OBJS}
	${CC} ${CFLAGS} -o $@ $^

# Firmware "test": does it fit in flash? Overflow is the basic embedded failure.
test: build
	@avr-size ${BIN}.elf | awk 'NR==2 { used=$$1+$$2; \
	  printf "flash: %d / ${FLASH_BYTES} bytes\n", used; \
	  if (used > ${FLASH_BYTES}) { print "FLASH OVERFLOW"; exit 1 } }'

flash: ${BIN}.hex
	${AVRDUDE} -U flash:w:$<

# One-time per chip: brown-out detector at 1.8V while awake, sampled in sleep
# (FUSE.BODCFG: LVL=BODLEVEL0, ACTIVE=enabled, SLEEP=sampled). The factory
# default leaves the BOD disabled, which allows undefined behavior when the
# battery sags; sampled mode in sleep keeps standby current in the ~1uA range.
fuses:
	${AVRDUDE} -U bodcfg:w:0x06:m

clean:
	rm -f ${BIN}.elf ${BIN}.hex ${OBJS}

.PHONY: build test flash fuses clean
