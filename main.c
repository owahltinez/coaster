#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay.h>

#define LED_PULSE_COUNT 5
#define LED_PWM_STEP_MS 5
#define LED_DUTY_MIN 32


int main(void)
{
  // Setup.

  // Disable global interrupts during setup.
  cli();

  // Disable any previously set watchdogs.
  wdt_reset();
  wdt_disable();

  // Set PB0 as output.
  DDRB |= (1 << PB0);

  // Set Timer0 to Fast PWM mode with non-inverted output
  TCCR0A |= (1 << WGM00) | (1 << WGM01) | (1 << COM0A1);
  TCCR0B |= (1 << CS01) | (1 << CS00); // Set prescaler to 64

  // Start with 0% duty cycle
  OCR0A = 0;

  // Configure unused pins as input with no pull-up to reduce power consumption.

  // Set PB1 as input and disable pull-up.
  DDRB &= ~(1 << PB1);
  PORTB &= ~(1 << PB1);

  // Set PB2 as input and disable pull-up.
  DDRB &= ~(1 << PB2);
  PORTB &= ~(1 << PB2);

  // Set PB3 as input and disable pull-up.
  DDRB &= ~(1 << PB3);
  PORTB &= ~(1 << PB3);

  // Set PB4 as input and disable pull-up.
  DDRB &= ~(1 << PB4);
  PORTB &= ~(1 << PB4);

  // Set PB5 as input and disable pull-up.
  DDRB &= ~(1 << PB5);
  PORTB &= ~(1 << PB5);

  // Set PB6 as input and disable pull-up.
  DDRB &= ~(1 << PB5);
  PORTB &= ~(1 << PB5);

  // Disable brown-out detector.
  MCUCR |= (1 << BODS) | (1 << BODSE);
  MCUCR = (MCUCR & ~(1 << BODSE)) | (1 << BODS);


  // Bring brightness to min value slowly.
  for (uint8_t duty = 0; duty < LED_DUTY_MIN; duty++) {
      OCR0A = duty;
      _delay_ms(LED_PWM_STEP_MS * 2);
  }

  // Pulse the LED LED_PULSE_COUNT times.
  for (int i = 0; i < LED_PULSE_COUNT; i++) {
    // Increase brightness.
    for (uint8_t duty = LED_DUTY_MIN; duty < 255; duty++) {
        OCR0A = duty;
        _delay_ms(LED_PWM_STEP_MS);
    }
    // Decrease brightness.
    for (uint8_t duty = 255; duty > LED_DUTY_MIN; duty--) {
        OCR0A = duty;
        _delay_ms(LED_PWM_STEP_MS);
    }
  }

  // Bring brightness back to zero slowly.
  for (uint8_t duty = LED_DUTY_MIN; duty > 0; duty--) {
      OCR0A = duty;
      _delay_ms(LED_PWM_STEP_MS * 2);
  }

  // Disable ADC to save power
  ADCSRA &= ~(1 << ADEN);

  // Disable analog comparator to save power
  ACSR |= (1 << ACD);

  // Set sleep mode to power-down mode
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);

  // Sleep indefinitely.
  while (1)
  {
    sleep_mode();
  }

  return 0;
}
