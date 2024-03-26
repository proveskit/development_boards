#include "pysquared.h"
                                                      //instantiate tools class in pysquared
pysquared::pysquared(neopixel neo) : 
battery_power(i2c0, 0x40), solar_power(i2c0, 0x44), internal_temp(i2c0, 0x4f), led_driver(i2c0, 0x56), adc(i2c0,0x48),
t(true, "[PYSQUARED] "), can_bus(spi0, spi0_cs0_pin){
    /*
        Initialize hardware core to operations on satellite.
    */
    try {
        t.debug_print("Figure out how to write to flash memory\n");                 //figure our how to section out some memory for flags
        pwr_mode=2;
        assert(interrupt_instance == nullptr);
        interrupt_instance = this;
        /*
            GPIO init
        */
        gpio_init(fc_reset_pin);
        gpio_set_dir(fc_reset_pin, GPIO_OUT);
        gpio_init(spi0_cs0_pin);
        gpio_set_dir(spi0_cs0_pin, GPIO_OUT);
        gpio_init(rf_enable_pin);
        gpio_set_dir(rf_enable_pin, GPIO_OUT);
        gpio_init(vbus_reset_pin);
        gpio_set_dir(vbus_reset_pin, GPIO_OUT);
        gpio_init(relay_pin);
        gpio_set_dir(relay_pin, GPIO_OUT);
        gpio_init(spi1_cs0_pin);
        gpio_set_dir(spi1_cs0_pin, GPIO_OUT);
        gpio_init(d0_pin);
        gpio_set_dir(d0_pin, GPIO_IN);
        gpio_init(is_charge_pin);
        gpio_set_dir(is_charge_pin, GPIO_IN);
        gpio_init(jetson_enable_pin);
        gpio_set_dir(jetson_enable_pin, GPIO_OUT);
        gpio_init(five_volt_enable_pin);
        gpio_set_dir(five_volt_enable_pin, GPIO_OUT);
        t.debug_print("GPIO Pins Initialized!\n");
        /*
            PWM init
        */
        gpio_set_function(enable_burn_pin, GPIO_FUNC_PWM);
        gpio_set_function(enable_heater_pin, GPIO_FUNC_PWM);
        t.debug_print("PWM Pins Initialized!\n");
        /*
            I2C init
        */
        i2c_init(i2c0, 400*1000);
        gpio_set_function(i2c_sda0_pin, GPIO_FUNC_I2C);
        gpio_set_function(i2c_scl0_pin, GPIO_FUNC_I2C);
        t.i2c_scan(i2c0);
        i2c_init(i2c1, 400*1000);
        gpio_set_function(i2c_sda1_pin, GPIO_FUNC_I2C);
        gpio_set_function(i2c_scl1_pin, GPIO_FUNC_I2C);
        t.i2c_scan(i2c1);
        t.debug_print("I2C Bus Initialized!\n");
        /*
            SPI init
        */
        spi_init(spi0, 500 * 1000);
        gpio_set_function(spi0_miso_pin, GPIO_FUNC_SPI);
        gpio_set_function(spi0_sck_pin, GPIO_FUNC_SPI);
        gpio_set_function(spi0_mosi_pin, GPIO_FUNC_SPI);
        spi_init(spi1, 500 * 1000);
        gpio_set_function(spi1_miso_pin, GPIO_FUNC_SPI);
        gpio_set_function(spi1_sck_pin, GPIO_FUNC_SPI);
        gpio_set_function(spi1_mosi_pin, GPIO_FUNC_SPI);
        t.debug_print("SPI Bus Initialized!\n");
        /*
            UART init
        */
        uart_init(uart0, 115200);
        gpio_set_function(tx_pin, GPIO_FUNC_UART);
        gpio_set_function(rx_pin, GPIO_FUNC_UART);
        t.debug_print("UART Bus Initialized!\n");
        /*
            LED Driver init
        */
        try{
            led_driver.configure();
            all_faces_on();
            camera_on();
            t.debug_print("LED Driver Initialized!\n");
        }
        catch(...){
            t.debug_print("ERROR initializing LED Driver!\n");
            error_count++;
        }
        /*
            Thermocouple
        */
        try{ 
            adc.configure();
            t.debug_print("Thermocouple ADC Initialized!\n");
        }
        catch(...){
            t.debug_print("ERROR initializing Thermocouple ADC!\n");
            error_count++;
        }
        /*
            Battery Power Monitor init
        */
        try{
            battery_power.configure();
            t.debug_print("Battery Power Monitor Initialized!\n");
        }
        catch(...){
            t.debug_print("ERROR initializing Battery Power Monitor!\n");
            error_count++;
        }
        /*
            Solar Power Monitor init
        */
       try{
            solar_power.configure();
            t.debug_print("Solar Power Monitor Initialized!\n");
        }
        catch(...){
            t.debug_print("ERROR initializing Solar Power Monitor!\n");
            error_count++;
        }
        t.debug_print("Hardware fully initialized!\n");
    }
    catch(...){
        t.debug_print("ERROR Initializing Hardware: \n");
        error_count++;
    }
}

void pysquared::flash_init(){
    try{
        uint8_t data[1u<<8];
        uint8_t new_data[1u<<8];
        flash_read(data,0);
        if(data[0] != 0){
            t.debug_print("Initializing flash\n");
            uint32_t ints = save_and_disable_interrupts();
            flash_range_erase((2044*1024), FLASH_SECTOR_SIZE);
            restore_interrupts(ints);
            for(int i = 0; i < 256; i++){
                new_data[i]=0;
            }
            flash_variable_update(new_data);
            flash_update();
            t.debug_print("Testing initialization!\n");
            flash_read(data,0);
            for(int i = 0; i < 256; i++){
                if(data[i]!=new_data[i]){
                    t.debug_print("init failed on: " + to_string(i) + "; data[" + to_string(i) + "] = " + to_string(data[i]) + "\n");
                }
            }
            t.debug_print("Flash initialized!\n");
        }
        else{
            t.debug_print("Flash already initialized! Commencing with redundancy check...\n");
            flash_read(new_data,1);
            for(int i = 0; i<256; i++){
                if(data[i]!=new_data[i]){
                    t.debug_print("memory failure on register: " + to_string(i) + "\n");
                    trust_memory=false;
                }
            }
            if(trust_memory){
                t.debug_print("Memory is intact!\n");
            }
            else{
                t.debug_print("Memory can not be trusted and will not be used in this run!\n");
                t.debug_print("Updating flash! Memory may be intact on next boot!\n");
                flash_variable_update(data);
                flash_update();
            }
        }
    }
    catch(...){
        t.debug_print("error erasing flash and setting bit!\n");
        error_count++;
    }
}

void pysquared::flash_variable_update(const uint8_t *data){
    try{
        for(int i = 0; i < 256; i++){
            nvm_memory[i]=data[i];
        }
    }
    catch(...){
        t.debug_print("Failed to update variable for flash!\n");
        error_count++;
    }
}

void pysquared::flash_update(){
    try{
        t.debug_print("writing to flash...\n");
        uint32_t ints = save_and_disable_interrupts();
        flash_range_erase((2044*1024), FLASH_SECTOR_SIZE);
        flash_range_program((2044*1024), nvm_memory, FLASH_PAGE_SIZE);
        flash_range_program((2044*1024+256), nvm_memory, FLASH_PAGE_SIZE);
        restore_interrupts(ints);
        t.debug_print("Flash Updated!\n");
    }
    catch(...){
        t.debug_print("error writing to flag!\n");
        error_count++;
    }
}

void pysquared::flash_read(uint8_t *data, uint8_t page){
    try{
        flash_target_contents = (const uint8_t *) (XIP_BASE + 2044*1024 + 256*page);
        t.debug_print("reading flash!\n");
        uint32_t ints = save_and_disable_interrupts();
        for(int i = 0; i < 256; i++){
            data[i] = flash_target_contents[i];
        }
        restore_interrupts(ints);
    }
    catch(...){
        t.debug_print("error reading from flash!\n");
        error_count++;
    }
}

void pysquared::flash_variable_read(uint8_t *data){
    try{
        for(int i = 0; i < 256; i++){
            data[i] = nvm_memory[i];
        }
    }
    catch(...){
        t.debug_print("failed to read from memory variable!\n");
        error_count++;
    }
}

void pysquared::reg_set(const uint8_t reg, const uint8_t val){
    try{
        uint8_t data[1u<<8];
        flash_read(data,0);
        data[reg]=val;
        flash_variable_update(data);
        return;
    }
    catch(...){
        t.debug_print("ERROR Failed to update register!\n");
        error_count++;
    }
}

void pysquared::bit_set(const uint8_t reg, const uint8_t bit, bool state){
    try{
        uint8_t data[1u<<8];
        flash_read(data,0);
        if(state){
            data[reg] |= (0x01<<bit);
        }
        else{
            uint8_t temp = 0xFF << (bit+1);
            for(int i = 0; i < bit; i++){
                temp = temp + (1u << i);
            }
            data[reg] &= temp;
        }
        reg_set(reg,data[reg]);
    }
    catch(...){
        t.debug_print("ERROR with updating a NVM bit!\n");
        error_count++;
    }
}

void pysquared::bus_reset(){
    t.debug_print("Attempting to reset bus voltage...\n");
    try{
        bit_set(1,4,false);
        flash_update();
        for(int i = 10; i > 0; i --){
            t.debug_print("Bus being reset in " + to_string(i) + "seconds!\n");
        }
        gpio_put(vbus_reset_pin, true);
    }
    catch(...){
        t.debug_print("A failure occurred when trying to reset bus voltage!\n");
        error_count++;
    }
}

void pysquared::microcontroller_reset(){
    t.debug_print("Attempting to reset the microcontroller!\n");
    try{
        for(int i = 4; i > 0; i--){
            t.debug_print("Resetting the microcontroller in " + to_string(i) + "second(s)\n");
            sleep_ms(950);
        }
        AIRCR_Register = 0x5FA0004;
    }
    catch(...){
        t.debug_print("Failed to reset microcontroller!\n");
        error_count++;
    }
}

void pysquared::check_reboot(){
    try{
        t.debug_print("Checking for reboot...\n");
        uint32_t sec_since_boot = to_ms_since_boot(get_absolute_time())/1000;
        if(sec_since_boot>(60*60*24)){
            t.debug_print("Attempting to reboot!\n");
            bus_reset();
        }
        else{
            t.debug_print("No reboot yet.\n");
            return;
        }
    }
    catch(...){
        t.debug_print("ERROR while checking for reboot!\n");
        error_count++;
    }
}

void pysquared::all_faces_on(){
    try{
        t.debug_print("Attempting to turn all faces on!\n");
        led_driver.setPortState(0,true);
        led_driver.setPortState(1,true);
        led_driver.setPortState(2,true);
        led_driver.setPortState(3,true);
        led_driver.setPortState(4,true);
        faces_on_value=true;
        t.debug_print("all faces turned on!\n");
    }
    catch(...){
        t.debug_print("ERROR while turning all faces on!\n");
        error_count++;
    }
}

void pysquared::all_faces_off(){
    try{
        t.debug_print("Attempting to turn all faces off!\n");
        led_driver.setPortState(0,false);
        led_driver.setPortState(1,false);
        led_driver.setPortState(2,false);
        led_driver.setPortState(3,false);
        led_driver.setPortState(4,false);
        faces_on_value=false;
        t.debug_print("all faces turned off!\n");
    }
    catch(...){
        t.debug_print("ERROR while turning all faces off!\n");
        error_count++;
    }
}

void pysquared::five_volt_enable(){
    t.debug_print("Attempting to enable five volts...\n");
    try{
        gpio_put(five_volt_enable_pin, true);
        t.debug_print("five volts enabled!\n");
    }
    catch(...){
        t.debug_print("five volts could not be enabled!\n");
    }
}

void pysquared::five_volt_disable(){
    t.debug_print("Attempting to disable five volts...\n");
    try{
        gpio_put(five_volt_enable_pin, false);
        t.debug_print("five volts disabled!\n");
    }
    catch(...){
        t.debug_print("five volts could not be disabled!\n");
    }
}

void pysquared::flight_computer_off(){
    t.debug_print("Attempting to turn off flight computer...\n");
    try{
        gpio_put(fc_reset_pin, false);
        t.debug_print("flight computer off!\n");
    }
    catch(...){
        t.debug_print("flight computer could not be turned off!\n");
    }
}

void pysquared::flight_computer_on(){
    t.debug_print("Attempting to turn on flight computer...\n");
    try{
        gpio_put(fc_reset_pin, true);
        t.debug_print("flight computer on!\n");
    }
    catch(...){
        t.debug_print("flight computer could not be turned on!\n");
    }
}

void pysquared::camera_on(){
    try{
        t.debug_print("Attempting to turn the camera on!\n");
        led_driver.setPortState(5,true);
        t.debug_print("Camera turned on!\n");
        camera_on_value=true;
    }
    catch(...){
        t.debug_print("ERROR while turning the camera on!\n");
        error_count++;
    }
}

void pysquared::camera_off(){
    try{
        t.debug_print("Attempting to turn the camera off!\n");
        led_driver.setPortState(5,false);
        t.debug_print("Camera turned off!\n");
        camera_on_value=false;
    }
    catch(...){
        t.debug_print("ERROR while turning the camera off!\n");
        error_count++;
    }
}

void pysquared::heater_on(){
    try{
        t.debug_print("Turning Heater on...\n");
        led_driver.setDutyCycle(15,2048);
        t.debug_print("done!\n");
    }
    catch(...){
        t.debug_print("ERROR while turning on the heater!\n");
        led_driver.setDutyCycle(15,0);
        error_count++;
    }
}

void pysquared::heater_off(){
    try{
        t.debug_print("Turning Heater off...\n");
        led_driver.setDutyCycle(15,0);
        t.debug_print("done!\n");
    }
/*     catch(const std::exception &e){
        printf(e.what());
        error_count++;
    } */
    catch(...){
        t.debug_print("ERROR while turning off the heater!\n");
        error_count++;
    }
}

void pysquared::can_bus_init(){
    try{
        can_bus.configure();
    }
    catch(...){
        t.debug_print("ERROR while configuring can bus!\n");
        error_count++;
    }
}

bool pysquared::can_bus_send(uint8_t *data){
    try{
        if(can_bus.chip_responding()){
            t.debug_print("MCP is responsive!\n");
        }
        uint32_t id = 0x123;
        can_bus.sendMessage(id, 8, data);
        t.debug_print("Message sent.\n");
        return true;
    }
    catch(...){
        t.debug_print("ERROR while sending item on can bus!\n");
        error_count++;
    }
    return false;
}

void pysquared::can_bus_loopback(){
    can_bus.modifyRegister(MCP25625_CANCTRL, MCP25625_MODE_MASK, MCP25625_MODE_LOOPBACK);
}

void pysquared::can_bus_listen(){
    uint32_t received_id;
    uint8_t received_data[MCP25625_MAX_MESSAGE_LENGTH];
    uint8_t received_data_len = 0;
    if (can_bus.receiveMessage(received_id, received_data_len, received_data)) {
        t.debug_print("Received message in loopback mode:\n");
        t.debug_print("ID: " + to_string(received_id) + "\n");
        printf("Data: ");
        for (size_t i = 0; i < received_data_len; i++) {
            printf("%02x ", received_data[i]);
        }
        printf("\n");
    } else {
        t.debug_print("No message received in loopback mode.\n");
    }
}

bool pysquared::uart_send(const char *msg){
    try{
        string message(msg);
        t.debug_print("sending message: " + message + "\n");
        uart_puts(uart0, msg);
        t.debug_print("Successful send!\n");
        return true;
    }
    catch(...){
        t.debug_print("failed to send!\n");
    }
    return false;
}

void pysquared::uart_receive_handler(){
    t.debug_print("checking uart buffer!\n");
    uint8_t counter=0;
    char *words;
    while (uart_is_readable(uart0)) {
        words[counter] = uart_getc(uart0);
        counter++;
    }
    t.debug_print(to_string(counter) + " Characters received!\n");
    if(counter > 0){
        //string str(words);
        //t.debug_print("Received message: " + str + "\n");
        t.debug_print("Decoding message...\n");
        for(int i = 0; i < counter; i++){
            if(words[i]-'0' <= 9){
                t.debug_print("Command found!\n");
                command=words[i]-'0';
            }
        }
        if(command!=0){
            t.debug_print("A command will be executed!\n");
            //isr is not completing for some reason
            exec_uart_command();
        }
    }
}

void pysquared::exec_uart_command(){
    string message;
    const char *msg;
    t.debug_print("Command #" + to_string(command) + " will be executed!\n");
    switch (command)
    {
    case 1:
        t.debug_print("Executing command to send temperatures!\n");
        message = to_string(thermocouple_temp()) + "," + to_string(board_temp());
        msg=message.c_str();
        uart_send(msg);
        break;
    case 2:
        t.debug_print("Executing command to send Power Metrics!\n");
        message = to_string(battery_voltage()) + "," + to_string(draw_current()) + "," + to_string(charge_voltage()) + "," + to_string(charge_current()) + "," + to_string(is_charging());
        msg=message.c_str();
        uart_send(msg);
        break;
    case 3:
        t.debug_print("Executing command to send Error Metrics!\n");
        message = to_string(error_count) + "," + to_string(trust_memory);
        msg=message.c_str();
        uart_send(msg);
        break;
    case 4:
        t.debug_print("Executing command to toggle faces!\n"); //battery board usually makes this decision, but FC can override if important
        if(faces_on_value){
            all_faces_off();
        }
        else{
            all_faces_on();
        }
        message = to_string(faces_on_value);
        msg=message.c_str();
        uart_send(msg);
        break;
    case 5:
        t.debug_print("command received to reset entire power bus!\n");
        message="Consider it done...";
        msg=message.c_str();
        uart_send(msg);
        bus_reset();
        break;
    case 6:
        t.debug_print("command received to toggle camera power!\n");
        if(camera_on_value){
            camera_off();
        }
        else{
            camera_on();
        }
        message=to_string(camera_on_value);
        msg=message.c_str();
        uart_send(msg);
        break;
    case 7:
        t.debug_print("command received to start transmitting through auxillary radio!\n");
        //do some logic to trigger radio use!
        break;
    case 8:
        t.debug_print("command received to reset microcontroller!\n");
        //do stuff
        break;
    case 9:
        t.debug_print("do something here, idk!\n");
        //do stuff
        break;
    default:
        t.debug_print("an invalid command was received!\n");
        break;
    }
}

uint8_t pysquared::power_mode() {return pwr_mode;}
float pysquared::thermocouple_temp(){
    try{
        float val=static_cast< float >(adc.readSingleEnded(1))*2.048/2048;
        printf("ADC Voltage measured: %.3f\n", val);
        return ((val-1.25)/0.004);
    }
    catch(...){
        t.debug_print("ERROR while getting thermocouple temperature!\n");
        error_count++;
        return 0;
    }
}
float pysquared::board_temp() {
    try{
        float temp;
        for(int i = 0; i<50; i++){
            temp+=internal_temp.readTemperature();
        }
        return temp/50;
    }
    catch(...){
        t.debug_print("ERROR while getting internal temperature!\n");
        error_count++;
        return 0;
    }
}
float pysquared::battery_voltage(){
    try{
        float temp;
        for(int i = 0; i<50; i++){
            temp+=battery_power.readBusVoltage();
        }
        return temp/50;
    }
    catch(...){
        t.debug_print("ERROR while getting battery voltage!\n");
        error_count++;
        return 0;
    }
}
float pysquared::draw_current(){
    try{
        float temp;
        for(int i = 0; i<50; i++){
            temp+=battery_power.readCurrent();
        }
        return temp/50;
    }
    catch(...){
        t.debug_print("ERROR while getting draw current!\n");
        error_count++;
        return 0;
    }
}
float pysquared::charge_voltage(){
    try{
        float temp;
        for(int i = 0; i<50; i++){
            temp+=solar_power.readBusVoltage();
        }
        return temp/50;
    }
    catch(...){
        t.debug_print("ERROR while getting charge voltage!\n");
        error_count++;
        return 0;
    }
}
float pysquared::charge_current(){
    try{
        float temp;
        for(int i = 0; i<50; i++){
            temp+=solar_power.readCurrent();
        }
    return temp/50;
    }
    catch(...){
        t.debug_print("ERROR while getting charge current!\n");
        error_count++;
        return 0;
    }
}

bool pysquared::is_charging(){
    try{
        return gpio_get(is_charge_pin);
    }
    catch(...){
        t.debug_print("Failure to read charge logic pin!\n");
        error_count++;
        return false;
    }
}

bool pysquared::charging(bool state){
    try{
        charge_status=state;
        return true;
    }
    catch(...){
        t.debug_print("ERROR setting charge status!\n");
        error_count++;
        return false;
    }
}

int pysquared::num_error(){return error_count;}
