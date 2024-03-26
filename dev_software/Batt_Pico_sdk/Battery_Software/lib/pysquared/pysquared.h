#ifndef _PYSQUARED_H
#define _PYSQUARED_H

#include <iostream>
#include <stdio.h>
#include <ctype.h>
#include <neopixel/neopixel.h>
#include <tools/tools.h>
#include <device_drivers/INA219.h>
#include <device_drivers/PCT2075.h>
#include <device_drivers/PCA9685.h>
#include <device_drivers/ADS1015.h>
#include <device_drivers/MCP25625_DRIVER.h>
#include <device_drivers/MCP25625.h>
#include "pico/stdlib.h"
#include "hardware/timer.h"
#include "hardware/gpio.h"
#include "hardware/flash.h"
#include "hardware/sync.h"
#include "hardware/i2c.h"
#include "hardware/irq.h"
#include "hardware/spi.h"
#include "hardware/uart.h"
#include "hardware/pio.h"

extern uint32_t ADDR_PERSISTENT[];
#define ADDR_PERSISTENT_BASE_ADDRESS (ADDR_PERSISTENT)
#define FLASH_TARGET_OFFSET (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE + FLASH_PAGE_SIZE)
#define AIRCR_Register (*((volatile uint32_t*)(PPB_BASE + 0x0ED0C)))

class pysquared{
public:
    INA219 battery_power;
    INA219 solar_power;
    PCT2075 internal_temp;
    PCA9685 led_driver;
    ADS1015 adc;
    MCP25625Driver can_bus;

    uint8_t nvm_memory[1u<<8];
    uint8_t tx_pin=0;       //rarely used
    uint8_t rx_pin=1;       //rarely used
    uint8_t i2c_sda1_pin=2; //rarely used
    uint8_t i2c_scl1_pin=3; //rarely used
    uint8_t i2c_sda0_pin=4;
    uint8_t i2c_scl0_pin=5;
    uint8_t enable_burn_pin=6;  //used once
    uint8_t fc_reset_pin=7;     //hopefully never used
    uint8_t spi0_miso_pin=8;    //used only for CAN bus
    uint8_t spi0_cs0_pin=9;     //used only for CAN bus
    uint8_t spi0_sck_pin=10;    //used only for CAN bus
    uint8_t spi0_mosi_pin=11;   //used only for CAN bus
    uint8_t rf_enable_pin=12;   //rarely used
    uint8_t usb_boot_pin=13;    //probably will never need to use
    uint8_t vbus_reset_pin=14;
    uint8_t relay_pin=15;
    uint8_t spi1_miso_pin=16;   //used for backup RF
    uint8_t spi1_cs0_pin=17;    //used for backup RF
    uint8_t spi1_sck_pin=18;    //used for backup RF
    uint8_t spi1_mosi_pin=19;   //used for backup RF
    uint8_t d0_pin=20;         
    uint8_t wdt_wdi_pin=21;     //dont touch already in use
    uint8_t enable_heater_pin=22;   
    uint8_t is_charge_pin=23;   //used frequently
    uint8_t neopixel_pin=24;    //dont touch already in use
    uint8_t neo_pwr_pin=25;     //dont touch already in use
    uint8_t a0_pin=26;          //not used
    uint8_t a1_pin=27;          //not used
    uint8_t jetson_enable_pin=28;   //rarely used
    uint8_t five_volt_enable_pin=29;    
    
    
    uint8_t pwr_mode;
    int command=0;
    int error_count;
    bool trust_memory=true;
    bool faces_on_value=false;
    bool camera_on_value=false;

    pysquared(neopixel neo);

    void bus_reset();
    void microcontroller_reset();
    void check_reboot();
    void all_faces_on();
    void all_faces_off();
    void flight_computer_off();
    void flight_computer_on();
    void five_volt_enable();
    void five_volt_disable();
    void camera_on();
    void camera_off();
    void heater_on();
    void heater_off();
    void exception_handler();
    void can_send(uint16_t id, char * message);
    void can_handler();
    void reg_set(const uint8_t reg, const uint8_t val);
    void bit_set(const uint8_t reg, const uint8_t bit, bool state);
    void flash_variable_update(const uint8_t * data);
    void flash_variable_read(uint8_t * data);
    void flash_update();
    void flash_read(uint8_t *data, uint8_t page);
    void flash_init();
    void can_bus_init();
    bool can_bus_send(uint8_t *data);
    void can_bus_loopback();
    void can_bus_listen();
    bool uart_send(const char *msg);
    void uart_receive_handler();
    void exec_uart_command();

    void install_isr_handler() {
        t.debug_print("interrupt handler being setup!\n");
        irq_set_exclusive_handler(UART0_IRQ, isrhandler);
    }

    uint8_t power_mode();
    float thermocouple_temp();
    float board_temp();
    float battery_voltage();
    float draw_current();
    float charge_voltage();
    float charge_current();
    bool is_charging();
    bool charging(bool state);
    int num_error();
private:
    tools t;
    const uint8_t *flash_target_contents;
    bool charge_status;
    static inline pysquared *interrupt_instance = nullptr;
    static void isrhandler() { //!< This is the actual ISR
        interrupt_instance->t.debug_print("Interrupt received!\n");
        interrupt_instance->uart_receive_handler();
    }
};
#endif