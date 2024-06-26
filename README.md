# Coaster

Very simple battery-operated device. When you push a button, the light turns on for a few seconds
and then it turns off. It is designed to be used as a coaster such that, when gently pushing a glass
down on the device, the light activates making the contents of the glass glow.

Because there's no on/off switch, the device remains on but it will do so in low power mode which
for the ATTINY13A it consumes about 4 µA. While the light is on, the device consumes under 10 mA.

## BOM

> TODO: Add 3D printing source files and estimated costs.

All prices are in AUD.

* $1.77 [ATiny13A][attiny]*
* $1.56 [Coin Cell Battery Holder][holder]
* $0.99 [CR2032 Battery][battery]
* $0.28 [LED][led]
* $0.16 [Push Button][button]

Total unit cost, excluding shipping and without any volume discounts: **$4.76**.

\* The ATiny13A chip is no longer in production, instead use one of the newer Atmel microchips from
the tinyAVR family or the ATiny10 which can be found for under $1.

[attiny]: https://www.digikey.com.au/en/products/detail/microchip-technology/ATTINY13A-PU/1914671
[holder]: https://www.amazon.com.au/gp/product/B0BDRR8SQ3/
[button]: https://www.digikey.com.au/en/products/detail/cui-devices/TS02-66-43-BK-160-LCR-D/15634343
[led]: https://www.digikey.com.au/en/products/detail/w%C3%BCrth-elektronik/151033RS03000/4490003
[battery]: amazon.com.au/CR2032-Batteries-Packaging-Calculator-Electronic/dp/B0CP7SYQ3W/

## Software

To build the code, you need to first install `avrdude`, `avr-libc` and `avr-gcc`. Then, you can run:

```bash
make
```

To flash the code to the ATiny13A chip, you'll need a USB programmer like
[this one](https://www.fischl.de/usbasp/) and run:

```bash
make install
```

This step assumes a `usbasp` programmer available at `/dev/ttyACM0`.

## Hardware

> TODO: Add hardware assembly instructions.

## Demo

> TODO: Add demo pictures / video.
