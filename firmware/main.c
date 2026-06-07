#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay.h>

#define LED_PWM_STEP_MS 5
// LED brightness duty cycle (0-255). Lower duty = less battery sag + longer
// battery life. The LEDs have no series resistance, so this is the only
// current limiting we control.
#define LED_DUTY_MAX 160
// Subtle "glow" effect: breathe between LED_DUTY_MIN and LED_DUTY_MAX.
// Show duration = LED_GLOW_CYCLES * 2 * (MAX - MIN) * LED_GLOW_STEP_MS,
// 5 cycles * 2 * 96 steps * 10ms = ~9.6s.
#define LED_DUTY_MIN 64
#define LED_GLOW_CYCLES 5
#define LED_GLOW_STEP_MS 10

// Magic cookie kept in .noinit SRAM, which survives any reset where VCC does
// not fully collapse. Used to detect a show interrupted by a reset (battery
// sag browning out the MCU mid-show): in that case skip the show and sleep,
// so a reset-relight loop cannot sustain itself.
//
// IMPORTANT: the show must play on any *other* cookie state, including
// scrambled SRAM. The button wakes the chip by collapsing VCC to ~0V (dead
// short through R1), which destroys SRAM -- so a button press cannot leave
// behind any "positive proof" to check for. Requiring a valid cookie to play
// (fail-dark) bricks the button. Only the BOD reset at 1.8V preserves SRAM,
// which is what makes the COOKIE_RUNNING check reliable.
#define COOKIE_RUNNING 0xB4
#define COOKIE_DONE 0x5A
uint8_t cookie __attribute__((section(".noinit")));
uint8_t cookie_inv __attribute__((section(".noinit")));

static inline uint8_t cookie_is(uint8_t value)
{
  return cookie == value && cookie_inv == (uint8_t)~value;
}

static inline void cookie_set(uint8_t value)
{
  cookie = value;
  cookie_inv = ~value;
}

int main(void)
{
  // Setup.

  // Clear reset flags, then disable any previously set watchdogs. With WDRF
  // set, the watchdog cannot be disabled, so MCUSR must be cleared first.
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

  // Skip the show only if it was interrupted by a reset mid-show.
  if (!cookie_is(COOKIE_RUNNING))
  {
    cookie_set(COOKIE_RUNNING);

    // Set PB0 as output, driven low.
    DDRB |= (1 << PB0);
    PORTB &= ~(1 << PB0);

    // Fast PWM on PB0 (OC0A), ~590Hz at 1.2MHz with /8 prescaler. Running
    // the LEDs below 100% duty reduces the load on the coin cell, which is
    // what drags VCC down during the show.
    TCCR0A = (1 << COM0A1) | (1 << WGM01) | (1 << WGM00);
    TCCR0B = (1 << CS01);

    // Ramp brightness up gently to avoid an inrush current step.
    for (uint8_t duty = 0; duty < LED_DUTY_MAX; duty++)
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

    // Let the battery voltage recover before declaring the show done: any
    // reset landing in this window still reads as a mid-show crash and stays
    // dark. A real button press scrambles SRAM and plays regardless, so this
    // costs nothing.
    _delay_ms(500);
  }

  // From here on, any reset means the button was pressed: run the show.
  cookie_set(COOKIE_DONE);

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
