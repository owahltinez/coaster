BIN=main
OBJS=${BIN}.o
MODEL=ATTINY13A
PROGRAMMER=usbasp
PORT=/dev/ttyACM0

CC=avr-gcc
OBJCOPY=avr-objcopy
CFLAGS=-Os -DF_CPU=1200000UL -mmcu=$(shell echo ${MODEL} | tr '[:upper:]' '[:lower:]')

${BIN}.hex: ${BIN}.elf
	${OBJCOPY} -O ihex -R .eeprom $< $@

${BIN}.elf: ${OBJS}
	${CC} -o $@ $^

install: ${BIN}.hex
	avrdude -F -c ${PROGRAMMER} -p ${MODEL} -P ${PORT} -B 4 -b 115200 -U flash:w:$<

clean:
	rm -f ${BIN}.elf ${BIN}.hex ${OBJS}
