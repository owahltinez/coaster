#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/eeprom.h>
#include <util/delay.h>

// LED brightness is a PWM duty cycle (0-255). Unlike v0.2, the LEDs have real
// series resistors, so the bright phase can run at full duty: peak current is
// set by R1-R4 by design, and steady drive at low current is both more
// efficient and flicker-free compared to chopping a higher peak.
#define LED_DUTY_MAX 255
// Subtle "glow" effect: breathe between LED_DUTY_MIN and LED_DUTY_MAX.
#define LED_DUTY_MIN 136
#define LED_GLOW_CYCLES 5
#define LED_GLOW_STEP_MS 5
#define LED_RAMP_STEP_MS 5
#define LED_FADE_STEP_MS 10

// Post-flash confirm: the flashing station writes FLASH_CONFIRM_ARMED to the
// first EEPROM byte as its final step, only after flash + fuses both verify.
// The first boot afterwards plays a distinct rapid blink -- so a hands-free
// station shows success on the board itself -- then clears the flag, so it
// fires exactly once per flash. A factory chip (0xFF) or an already-cleared
// one never blinks, and a flash that erased EEPROM (to 0xFF) but then failed
// before arming never reads as armed, so a confirm only ever means full success.
#define FLASH_CONFIRM_ADDR    ((uint8_t *)0)
#define FLASH_CONFIRM_ARMED   0xA5
#define FLASH_CONFIRM_CLEARED 0x00
#define FLASH_CONFIRM_BLINKS  4
#define FLASH_CONFIRM_MS      80

// A wake edge only counts as a press if the button still reads pressed this
// much later. Filters contact bounce on *release* (which can also produce
// falling edges) so lifting a glass off the coaster doesn't replay the show.
#define BUTTON_DEBOUNCE_MS 20

// Rapid full-brightness blink, visually distinct from the gentle multi-second
// breathe of show(), so it reads as "just programmed" across a workbench.
// Drives PA3 directly (no PWM) -- the LEDs run at the peak current set by
// R1-R4, which is fine for a sub-second confirm.
static void flash_confirm(void)
{
  for (uint8_t i = 0; i < FLASH_CONFIRM_BLINKS; i++)
  {
    PORTA.OUTSET = PIN3_bm;
    _delay_ms(FLASH_CONFIRM_MS);
    PORTA.OUTCLR = PIN3_bm;
    _delay_ms(FLASH_CONFIRM_MS);
  }
}

// Play the light show: ramp up, breathe LED_GLOW_CYCLES times ending on the
// dim phase (rising right before the fade would read as a restart), then a
// perceptually-even fade to black. Roughly 8 seconds end to end.
static void show(void)
{
  // TCA0 single-slope PWM on PA3 (WO0, default PORTMUX routing):
  // 3.33MHz / 16 / 256 ~= 814Hz, comfortably above flicker.
  TCA0.SINGLE.PER = 0xFF;
  TCA0.SINGLE.CMP0 = 0;
  TCA0.SINGLE.CTRLB = TCA_SINGLE_CMP0EN_bm | TCA_SINGLE_WGMODE_SINGLESLOPE_gc;
  TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV16_gc | TCA_SINGLE_ENABLE_bm;

  // Ramp up to full brightness.
  for (uint8_t duty = 0; duty < LED_DUTY_MAX; duty++)
  {
    TCA0.SINGLE.CMP0BUF = duty;
    _delay_ms(LED_RAMP_STEP_MS);
  }

  // Glow effect: breathe gently between max and min brightness.
  for (uint8_t cycle = 0; cycle < LED_GLOW_CYCLES; cycle++)
  {
    for (uint8_t duty = LED_DUTY_MAX; duty > LED_DUTY_MIN; duty--)
    {
      TCA0.SINGLE.CMP0BUF = duty;
      _delay_ms(LED_GLOW_STEP_MS);
    }
    if (cycle == LED_GLOW_CYCLES - 1)
      break;
    for (uint8_t duty = LED_DUTY_MIN; duty < LED_DUTY_MAX; duty++)
    {
      TCA0.SINGLE.CMP0BUF = duty;
      _delay_ms(LED_GLOW_STEP_MS);
    }
  }

  // Fade from the dim point to dark. Duty is linear in light output but
  // perception is logarithmic; squaring the ramp position spends most of the
  // time at the dim end, which reads as an even fade instead of a snap.
  for (uint8_t step = LED_DUTY_MIN; step > 0; step--)
  {
    TCA0.SINGLE.CMP0BUF = (uint8_t)(((uint16_t)step * step) / LED_DUTY_MIN);
    _delay_ms(LED_FADE_STEP_MS);
  }

  // PWM off, gate driven firmly low (R5 also holds it low whenever PA3
  // floats, e.g. during programming or reset).
  TCA0.SINGLE.CTRLA = 0;
  TCA0.SINGLE.CTRLB = 0;
  PORTA.OUTCLR = PIN3_bm;
}

// The button interrupt exists only to wake the CPU from power-down; waking
// returns control to the main loop right after sleep_cpu().
ISR(PORTA_PORT_vect)
{
  PORTA.INTFLAGS = PORT_INT6_bm;
}

int main(void)
{
  // Snapshot and clear the reset cause (cleared by writing 1s).
  uint8_t reset_flags = RSTCTRL.RSTFR;
  RSTCTRL.RSTFR = reset_flags;

  // Unused pins: pull-up so they don't float, input buffer off to save power.
  // PA0 is UPDI and PA3 is the PWM output; both are left alone here.
  PORTA.PIN1CTRL = PORT_PULLUPEN_bm | PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN2CTRL = PORT_PULLUPEN_bm | PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN7CTRL = PORT_PULLUPEN_bm | PORT_ISC_INPUT_DISABLE_gc;

  // Button on PA6: internal pull-up, interrupt on falling edge. PA6 is one of
  // the two fully-asynchronous pins (Px2/Px6), so the edge wakes the chip
  // from power-down with the main clock stopped.
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm | PORT_ISC_FALLING_gc;

  // LED gate pin: output, low (LEDs off).
  PORTA.OUTCLR = PIN3_bm;
  PORTA.DIRSET = PIN3_bm;

  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  sei();

  // If the flashing station just armed the confirm flag, blink once to show
  // the board itself that programming succeeded, then clear it. This is a
  // UPDI-reset boot (not a power-on), so it never collides with the show below.
  if (eeprom_read_byte(FLASH_CONFIRM_ADDR) == FLASH_CONFIRM_ARMED)
  {
    flash_confirm();
    eeprom_write_byte(FLASH_CONFIRM_ADDR, FLASH_CONFIRM_CLEARED);
  }

  // Inserting the battery is a power-on reset: play one show as a built-in
  // self test. Any other reset cause -- in particular a brown-out, meaning a
  // dying cell sagged below 1.8V mid-show -- skips straight to sleep, so a
  // worn battery cannot sustain a reset-relight loop.
  if (reset_flags & RSTCTRL_PORF_bm)
    show();

  while (1)
  {
    // Discard any presses that arrived during the show, then sleep until the
    // next falling edge on the button. While a glass parks the button held
    // down, no further falling edges can occur, so the chip stays asleep.
    PORTA.INTFLAGS = PORT_INT6_bm;
    sleep_enable();
    sleep_cpu();
    sleep_disable();

    // Only a press that is still held after the debounce window plays the
    // show; edges from release bounce read as released here and fall through
    // back to sleep.
    _delay_ms(BUTTON_DEBOUNCE_MS);
    if (!(PORTA.IN & PIN6_bm))
      show();
  }

  return 0;
}
