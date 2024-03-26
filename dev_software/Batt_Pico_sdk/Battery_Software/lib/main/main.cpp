#include "main.h"

void main_program(neopixel neo){
    sleep_ms(10);
    tools t(true, "[MAIN] ");                                                       //instantiate tools class (set debug mode to true)
    t.debug_print("I am in main!\n");                                               //debug print can toggle print statements for debugging
    neo.put_pixel(neo.urgb_u32(0, 0xff, 0));                                        //makes the neopixel green
    t.debug_print("Initializing Hardware...\n");
    bool watchdog_reset = false;
    watchdog_enable(5000, 1);
    t.debug_print("Internal Watchdog enabled\n");
    if (watchdog_caused_reboot()) {
        t.debug_print("Rebooted by Watchdog!\n");
        watchdog_reset = true;
    } else {
        t.debug_print("Clean boot\n");
    }
    pysquared satellite(neo);

    //flash startup logic
    uint8_t data[1u<<8];
    satellite.flash_init();    
    if (watchdog_reset){
        t.debug_print("setting watchdog tracker!\n");
        satellite.bit_set(status_reg,watchdog_bit,true);
    }
    else{
        t.debug_print("unsetting watchdog tracker!\n");
        satellite.bit_set(status_reg,watchdog_bit,false);
    }
    data[boot_reg]++;
    satellite.reg_set(boot_reg, data[boot_reg]);
    satellite.flash_update();
    satellite.flash_read(data,0);
    t.debug_print("updated boot count: " + to_string(data[boot_reg]) + "\n");

    t.debug_print("Initializing CAN Bus!\n");
    satellite.can_bus_init();
    satellite.can_bus_loopback();
    t.debug_print("CAN Bus Initialized!\n");
    
    while(true){

        /*
            Hypothetical Code Logic (remove while)
        */
        satellite_functions functions(satellite);
        satellite.all_faces_off();
        satellite.camera_off();
        sleep_ms(1000);
        watchdog_update();
        satellite.all_faces_on();
        satellite.camera_on();
        functions.battery_manager(); //method obtains current battery status
        //uint loiter_time=270;
        //satellite.burn_flag = functions.smart_burn(loiter_time);
        functions.battery_manager();
        t.debug_print("about to enter the main loop!\n");
        satellite.install_isr_handler();
        irq_set_enabled(UART0_IRQ, true);
        uart_set_irq_enables(uart0, true, false);//can hang up here if isr function is poorly written/contains errors
        uint8_t stuff[]={0x05};
        while(true){
            watchdog_update();
            satellite.can_bus_send(stuff);
            satellite.can_bus_listen();
            switch(satellite.power_mode()){
                case 0:
                    critical_power_operations(t, functions);
                    break;
                case 1:
                    low_power_operations(t, neo, functions);
                    break;
                case 2:
                    normal_power_operations(t, neo, functions);
                    break;
                case 3:
                    maximum_power_operations(t, neo, functions);
                    break;
            }
            satellite.check_reboot();
        }
    }
    return;
}

void critical_power_operations(tools t, satellite_functions functions){
    t.debug_print("Satellite is in critical power mode!\n");
    functions.c.flight_computer_on();
    sleep_ms(2000);//consider replacing with CAN listen functions
    functions.c.flight_computer_off();
    functions.long_hybernate();
    functions.battery_manager();
    return;
}

void low_power_operations(tools t, neopixel neo, satellite_functions functions){
    t.debug_print("Satellite is in low power mode!\n");
    neo.put_pixel(neo.urgb_u32(0xFF,0x00,0x00));
    functions.c.flight_computer_on();
    sleep_ms(10000);//consider replacing with CAN listen functions
    functions.c.flight_computer_off();
    functions.short_hybernate();
    functions.battery_manager();
    return;
}

void normal_power_operations(tools t, neopixel neo, satellite_functions functions){
    t.debug_print("Satellite is in normal power mode!\n");
    neo.put_pixel(neo.urgb_u32(0xFF,0xFF,0x00));
    functions.c.flight_computer_on();
    functions.c.five_volt_enable();
    functions.battery_manager();
    sleep_ms(1000);
    //maybe consider tasking second core to stuff
}

void maximum_power_operations(tools t, neopixel neo, satellite_functions functions){
    t.debug_print("Satellite is in maximum power mode!\n");
    neo.put_pixel(neo.urgb_u32(0x00,0xFF,0x00));
    functions.c.flight_computer_on();
    functions.c.five_volt_enable();
    functions.battery_manager();
    sleep_ms(1000);
    //maybe consider tasking second core to stuff
}