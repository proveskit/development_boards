#ifndef _FUNCTIONS_H
#define _FUNCTIONS_H
#include <stdio.h>
#include <neopixel/neopixel.h>
#include <tools/tools.h>
#include <pysquared/pysquared.h>
#include <device_drivers/MCP25625_DRIVER.h>
#include "hardware/gpio.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/uart.h"
#include "hardware/pio.h"
#include "hardware/watchdog.h"

class satellite_functions{
    public:
    satellite_functions(pysquared& satellite);
    void battery_manager();
    void battery_heater();
    void long_hybernate();
    void short_hybernate();
    void handle_errors();
    pysquared& c;
    private:
    tools t;
};
#endif
