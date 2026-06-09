#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay.h>

#define LED_PWM_STEP_MS 5
// LED brightness duty cycle (0-255). Lower duty = less battery sag + longer
// battery life. The LEDs have no series resistance, so this is the only
// current limiting we control. Kept conservative so the bright phase doesn't
// sag a cell weakened by the wake dead-short (see the settle phase below).
#define LED_DUTY_MAX 120
// Subtle "glow" effect: breathe between LED_DUTY_MIN and LED_DUTY_MAX.
// Show duration = LED_GLOW_CYCLES * 2 * (MAX - MIN) * LED_GLOW_STEP_MS.
#define LED_DUTY_MIN 64
#define LED_GLOW_CYCLES 5
#define LED_GLOW_STEP_MS 10

// Battery-recovery soft start. A press wakes the MCU by dead-shorting the
// CR2032 through R1; a long press holds that short for seconds and depresses
// the cell's voltage. The board can't sense VCC (the ATtiny13A has no
// bandgap-vs-VCC ADC path and no divider is wired), so rather than measure, we
// open the show at a low duty and hold there: the LED current is small, so the
// depressed cell climbs back under this light load before the bright phase
// loads it. Without this the show sags the weakened cell below the 1.8V BOD
// and the chip resets mid-show -- a bright frame snapping to black. A fresh
// cell (short press) is already recovered, so this just reads as a dim
// soft-start. Lengthen LED_SETTLE_MS if a long press still cuts out.
#define LED_DUTY_SETTLE 24
#define LED_SETTLE_MS 1200

int main(void)
{
  // Setup.

  // Snapshot the reset cause, then clear MCUSR (with WDRF set the watchdog
  // cannot be disabled, so MCUSR must be cleared before wdt_disable).
  //
  // This is how we tell a real button press apart from a brown-out that
  // interrupted the show, so a worn battery can't get stuck relighting:
  //
  // - A press dead-shorts the battery through R1, collapsing VCC to ~0V. On
  //   release VCC rises from zero, which is a power-on reset (PORF set).
  // - A mid-show brown-out only sags VCC to the 1.8V BOD threshold; the moment
  //   the MCU resets, the LED pin releases, the load drops, and VCC recovers
  //   without ever reaching the power-on level. That sets BORF, never PORF.
  //
  // So PORF means "play the show" and its absence means "a reset interrupted
  // us -- go back to sleep." Unlike the SRAM state this replaced, PORF only
  // cares that VCC reached ~0V, which every press does regardless of how long
  // the button is held, so short and long presses behave identically.
  uint8_t reset_flags = MCUSR;
  MCUSR = 0;
  wdt_reset();
  wdt_disable();

  // Disable global interrupts during setup.
  cli();

  // Disable ADC to save power
  ADCSRA &= ~(1 << ADEN);

  // Disable analog comparator to save power
  ACSR |= (1 << ACD);

  // Enable pull-ups on unused pins (PB1-PB4) so they don't float.
  // PB5 is the RESET pin and is not affected by PORTB.
  DDRB &= ~((1 << PB1) | (1 << PB2) | (1 << PB3) | (1 << PB4));
  PORTB |= (1 << PB1) | (1 << PB2) | (1 << PB3) | (1 << PB4);

  // Play the show only on a real power-on (button press). Any other reset
  // cause -- a mid-show brown-out, the ISP reset line -- skips straight to
  // sleep, so a sagging battery can't sustain a reset-relight loop.
  if (reset_flags & (1 << PORF))
  {
    // Set PB0 as output, driven low.
    DDRB |= (1 << PB0);
    PORTB &= ~(1 << PB0);

    // Fast PWM on PB0 (OC0A), ~590Hz at 1.2MHz with /8 prescaler. Running
    // the LEDs below 100% duty reduces the load on the coin cell, which is
    // what drags VCC down during the show.
    TCCR0A = (1 << COM0A1) | (1 << WGM01) | (1 << WGM00);
    TCCR0B = (1 << CS01);

    // Soft start to a low duty, then hold there to let a cell weakened by the
    // wake dead-short recover before the bright phase (see LED_SETTLE_MS).
    for (uint8_t duty = 0; duty <= LED_DUTY_SETTLE; duty++)
    {
      OCR0A = duty;
      _delay_ms(LED_PWM_STEP_MS);
    }
    for (uint16_t held = 0; held < LED_SETTLE_MS; held += LED_GLOW_STEP_MS)
      _delay_ms(LED_GLOW_STEP_MS);

    // Ramp the rest of the way up to full brightness.
    for (uint8_t duty = LED_DUTY_SETTLE + 1; duty < LED_DUTY_MAX; duty++)
    {
      OCR0A = duty;
      _delay_ms(LED_PWM_STEP_MS);
    }

    // Glow effect: breathe gently between min and max brightness. The last
    // cycle ends at the dim point: rising back to full brightness right
    // before the fade-out reads as the show restarting.
    for (uint8_t cycle = 0; cycle < LED_GLOW_CYCLES; cycle++)
    {
      for (uint8_t duty = LED_DUTY_MAX; duty > LED_DUTY_MIN; duty--)
      {
        OCR0A = duty;
        _delay_ms(LED_GLOW_STEP_MS);
      }
      if (cycle == LED_GLOW_CYCLES - 1)
        break;
      for (uint8_t duty = LED_DUTY_MIN; duty < LED_DUTY_MAX; duty++)
      {
        OCR0A = duty;
        _delay_ms(LED_GLOW_STEP_MS);
      }
    }

    // Fade from the dim point to dark. PWM duty is linear in light output
    // but perception is logarithmic, so a linear ramp reads as "still on,
    // still on, snap off". Squaring the ramp position spends most of the
    // time at the dim end, which reads as an even fade to black.
    for (uint8_t step = LED_DUTY_MIN; step > 0; step--)
    {
      OCR0A = (uint8_t)((step * step) / LED_DUTY_MIN);
      _delay_ms(LED_PWM_STEP_MS * 4);
    }

    // Disable PWM and drive the pin firmly low.
    TCCR0A = 0;
    TCCR0B = 0;
    PORTB &= ~(1 << PB0);
  }

  // Set sleep mode to power-down mode
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);

  // Sleep indefinitely.
  while (1)
  {
    // Disable BOD during sleep to save power (~20uA when the BOD fuse is
    // enabled, hfuse 0xFD = 1.8V). On the ATtiny13A this lives in the BODCR
    // register (not MCUCR), and the SLEEP instruction must execute within 3
    // clock cycles of the BODS write -- so SE is set first and we use the
    // avr-libc sequence, which targets the right register.
    sleep_enable();
    sleep_bod_disable();
    sleep_cpu();
    sleep_disable();
  }

  return 0;
}
