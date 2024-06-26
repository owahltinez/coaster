# Coaster

Very simple battery-operated device. When you push a button, the light turns on for a few seconds
and then it turns off. It is designed to be used as a coaster such that, when gently pushing a glass
down on the device, the light activates making the contents of the glass glow.

Because there's no on/off switch, the device remains on but it will do so in low power mode which
for the ATTINY13A it consumes about 4 µA. While the light is on, the device consumes under 10 mA.

## BOM

> TODO: Add 3D printing source files and estimated costs.

All prices are in AUD.

| Part                     	| Source            	| Count 	| Unit Price 	| Subtotal 	|
|--------------------------	|-------------------	|-------	|------------	|----------	|
| ATTINY13A\*              	| [Digikey][attiny] 	| 1     	| $1.947     	| $1.947   	|
| CR2032 Battery           	| [Amazon][battery] 	| 1     	| $0.990     	| $0.990   	|
| Color LED                	| [Digikey][led]    	| 4     	| $0.176     	| $0.704   	|
| Coin Cell Battery Holder 	| [Digikey][holder] 	| 1     	| $0.638     	| $0.638   	|
| Push Button              	| [Digikey][button] 	| 1     	| $0.176     	| $0.176   	|

Total unit cost, excluding shipping and without any volume discounts: **$4.455**.

\*The ATTINY13A chip is no longer in production and it causes the high price. It was used in this
project because I had a few of them laying around. You should instead use one of the newer Atmel
microchips from the tinyAVR family or the ATTINY10 which can be found for under $1.

[attiny]: https://www.digikey.com.au/en/products/detail/microchip-technology/ATTINY13A-PU/1914671
[holder]: https://www.digikey.com.au/en/products/detail/keystone-electronics/3034/4499289
[button]: https://www.digikey.com.au/en/products/detail/cui-devices/TS02-66-43-BK-160-LCR-D/15634343
[led]: https://www.digikey.com.au/en/products/detail/beking-optoelectronics/BQ-0402W005-S4YYD0N-B0/21512410
[battery]: amazon.com.au/CR2032-Batteries-Packaging-Calculator-Electronic/dp/B0CP7SYQ3W/

## Software

To build the code, you need to first install `avrdude`, `avr-libc` and `avr-gcc`. Then, you can run:

```bash
make
```

To flash the code to the ATTINY13A chip, you'll need a USB programmer like [this one][usbasp] and
run:

```bash
make install
```

This step assumes a `usbasp` programmer connected via USB and available at `/dev/ttyACM0`.

[usbasp]: https://www.fischl.de/usbasp/

## Hardware

> TODO: Add hardware assembly instructions.

## Demo

> TODO: Add demo pictures / video.
