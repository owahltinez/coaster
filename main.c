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

  // Disable ADC to save power
  ADCSRA &= ~(1 << ADEN);

  // Disable analog comparator to save power
  ACSR |= (1 << ACD);

  // Set PB0 as output.
  DDRB |= (1 << PB0);
  PORTB &= ~(1 << PB0);

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

  // Enable global interrupts.
  // sei();

  // Turn on LED for 10 seconds.
  PORTB |= (1 << PB0);
  _delay_ms(10000);
  PORTB &= ~(1 << PB0);
  _delay_ms(1000);

  // Set sleep mode to power-down mode
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);

  // Sleep indefinitely.
  while (1)
  {
    sleep_mode();
  }

  return 0;
}
