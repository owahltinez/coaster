#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay.h>

#define LED_TIME_ON 10000


int main(void)
{
  // Setup.

  // Disable global interrupts during setup.
  cli();

  // Disable any previously set watchdogs.
  wdt_reset();
  wdt_disable();

  // Set PB4 as output.
  DDRB |= (1 << PB4);

  // Configure unused pins as input with no pull-up to reduce power consumption.

  // Set PB0 as input and disable pull-up.
  DDRB &= ~(1 << PB0);  
  PORTB &= ~(1 << PB0); 

  // Set PB1 as input and disable pull-up.
  DDRB &= ~(1 << PB1);  
  PORTB &= ~(1 << PB1); 

  // Set PB2 as input and disable pull-up.
  DDRB &= ~(1 << PB2);  
  PORTB &= ~(1 << PB2); 

  // Set PB3 as input and disable pull-up.
  DDRB &= ~(1 << PB3);  
  PORTB &= ~(1 << PB3); 

  // Disable brown-out detector.
  MCUCR |= (1 << BODS) | (1 << BODSE);
  MCUCR = (MCUCR & ~(1 << BODSE)) | (1 << BODS);

  // Disable ADC to save power
  ADCSRA &= ~(1 << ADEN);

  // Disable analog comparator to save power
  ACSR |= (1 << ACD);

  // Set sleep mode to power-down mode
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);

  // Turn on the LED for LED_TIME_ON seconds.
  // NOTE: Ideally we would go to sleep during this time... But WD interrupts
  // don't work as documented for the ATTINY13A.
  PORTB |= (1 << PB4);
  _delay_ms(LED_TIME_ON);
  PORTB &= ~(1 << PB4);

  // Sleep indefinitely.
  while (1)
  {
    sleep_mode();
  }

  return 0;
}
