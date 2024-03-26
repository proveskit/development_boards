#ifndef _MAIN_H
#define _MAIN_H
#include <iostream>
#include <stdio.h>
#include <neopixel/neopixel.h>
#include <tools/tools.h>
#include <pysquared/pysquared.h>
#include <functions/functions.h>
#include "hardware/pio.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/uart.h"
#include "hardware/irq.h"
#include "hardware/watchdog.h"
#include "hardware/flash.h"
#include "pico/stdlib.h"


#define status_reg 1
#define brownout_bit 0
#define watchdog_bit 1
#define burned_bit 2
#define heater_latch_bit 3
#define vbus_reset_bit 4

#define boot_reg 2

using namespace std;

void main_program(neopixel neo);

void critical_power_operations(tools t, satellite_functions functions);
void low_power_operations(tools t, neopixel neo, satellite_functions functions);
void normal_power_operations(tools t, neopixel neo, satellite_functions functions);
void maximum_power_operations(tools t, neopixel neo, satellite_functions functions);


#endif