"""
CircuitPython driver for PySquared satellite board.
PySquared Hardware Version: mainboard-v01
CircuitPython Version: 8.0.0 alpha
Library Repo:

* Author(s): Nicole Maggard, Michael Pham, and Rachel Sarmiento
"""
# Common CircuitPython Libs
import board, microcontroller
import busio, time, sys, traceback
from storage import mount,umount,VfsFat
import digitalio, sdcardio, pwmio
from debugcolor import co
import gc

# Hardware Specific Libs
import pysquared_rfm9x  # Radio
import neopixel         # RGB LED
import adafruit_tca9548a # I2C Multiplexer
import adafruit_pct2075 # Temperature Sensor
import adafruit_vl6180x # LiDAR Distance Sensor for Antenna
import adafruit_lsm303_accel
import adafruit_lis2mdl
from adafruit_lsm6ds import lsm6dsox
import payload

# CAN Bus Import
from adafruit_mcp2515 import MCP2515 as CAN

# Common CircuitPython Libs
from os import listdir,stat,statvfs,mkdir,chdir
from bitflags import bitFlag,multiBitFlag,multiByte
from micropython import const


# NVM register numbers
_BOOTCNT  = const(0)
_VBUSRST  = const(6)
_STATECNT = const(7)
_TOUTS    = const(9)
_ICHRG    = const(11)
_DIST     = const(13)
_FLAG     = const(16)

SEND_BUFF=bytearray(252)

class Satellite:
    # General NVM counters
    c_boot      = multiBitFlag(register=_BOOTCNT, lowest_bit=0,num_bits=8)
    c_vbusrst   = multiBitFlag(register=_VBUSRST, lowest_bit=0,num_bits=8)
    c_state_err = multiBitFlag(register=_STATECNT,lowest_bit=0,num_bits=8)
    c_distance  = multiBitFlag(register=_DIST,    lowest_bit=0,num_bits=8)
    c_ichrg     = multiBitFlag(register=_ICHRG,   lowest_bit=0,num_bits=8)

    # Define NVM flags
    f_softboot  = bitFlag(register=_FLAG,bit=0)
    f_solar     = bitFlag(register=_FLAG,bit=1)
    f_burnarm   = bitFlag(register=_FLAG,bit=2)
    f_brownout  = bitFlag(register=_FLAG,bit=3)
    f_triedburn = bitFlag(register=_FLAG,bit=4)
    f_shtdwn    = bitFlag(register=_FLAG,bit=5)
    f_burned    = bitFlag(register=_FLAG,bit=6)
    f_fsk       = bitFlag(register=_FLAG,bit=7)

    def debug_print(self,statement):
        if self.debug:
            print(co("[pysquared]" + str(statement), "red", "bold"))

    def __init__(self):
        """
        Big init routine as the whole board is brought up.
        """
        self.debug=True #Define verbose output here. True or False
        self.BOOTTIME= 1577836800
        self.debug_print(f'Boot time: {self.BOOTTIME}s')
        self.CURRENTTIME=self.BOOTTIME
        self.UPTIME=0
        self.heating=False
        self.is_licensed=False
        self.NORMAL_TEMP=20
        self.NORMAL_BATT_TEMP=1#Set to 0 BEFORE FLIGHT!!!!!
        self.NORMAL_MICRO_TEMP=20
        self.NORMAL_CHARGE_CURRENT=0.5
        self.NORMAL_BATTERY_VOLTAGE=6.9#6.9
        self.CRITICAL_BATTERY_VOLTAGE=6.6#6.6
        self.data_cache={}
        self.filenumbers={}
        self.image_packets=0
        self.urate = 115200
        self.vlowbatt=6.0
        self.send_buff = memoryview(SEND_BUFF)
        self.micro=microcontroller
        self.radio_cfg = {
                        'id':   0xfb,
                        'gs':   0xfa,
                        'freq': 437.4,
                        'sf':   8,
                        'bw':   125,
                        'cr':   8,
                        'pwr':  23,
                        'st' :  80000
        }
        self.hardware = {
                       'ACCEL':  False,
                       'GYRO':   False,
                       'MAG':    False,
                       'Radio1': False,
                       'SDcard': False,
                       'CAN':    False,
                       'LiDAR':  False,
                       'WDT':    False,
                       'SOLAR':  False,
                       'PWR':    False,
                       'FLD':    False,
                       'TEMP':   False,
                       'Face0':  False,
                       'Face1':  False,
                       'Face2':  False,
                       'Face3':  False,
                       'Face4':  False,
                       }

        # Define SPI,I2C,UART | paasing I2C1 to BigData
        try:
            self.i2c0 = busio.I2C(board.I2C0_SCL,board.I2C0_SDA,timeout=5)
            self.spi0 = busio.SPI(board.SPI0_SCK,board.SPI0_MOSI,board.SPI0_MISO)
            self.i2c1 = busio.I2C(board.I2C1_SCL,board.I2C1_SDA,timeout=5,frequency=100000)
            self.uart = busio.UART(board.TX,board.RX,baudrate=self.urate)
        except Exception as e:
            self.debug_print("ERROR INITIALIZING BUSSES: " + ''.join(traceback.format_exception(e)))

        if self.c_boot > 250:
            self.c_boot=0

        if self.f_fsk:
            self.debug_print("Fsk going to false")
            self.f_fsk=False
        
        if self.f_softboot:
            self.f_softboot=False

        # Define radio
        _rf_cs1 = digitalio.DigitalInOut(board.SPI0_CS0)
        _rf_rst1 = digitalio.DigitalInOut(board.RF1_RST)
        self.radio1_DIO0=digitalio.DigitalInOut(board.RF1_IO0)
        self.radio1_DIO4=digitalio.DigitalInOut(board.RF1_IO4)

        # self.enable_rf.switch_to_output(value=False) # if U21
        _rf_cs1.switch_to_output(value=True)
        _rf_rst1.switch_to_output(value=True)
        self.radio1_DIO0.switch_to_input()
        self.radio1_DIO4.switch_to_input()

        # Initialize SD card
        try:
            # Baud rate depends on the card, 4MHz should be safe
            _sd = sdcardio.SDCard(self.spi0, board.SPI0_CS1, baudrate=4000000)
            _vfs = VfsFat(_sd)
            mount(_vfs, "/sd")
            self.fs=_vfs
            sys.path.append("/sd")
            self.hardware['SDcard'] = True
        except Exception as e:
            self.debug_print('[ERROR][SD Card]' + ''.join(traceback.format_exception(e)))

        # Initialize CAN Transceiver
        try:
            self.spi0cs2 = digitalio.DigitalInOut(board.SPI0_CS2)
            self.spi0cs2.switch_to_output()
            self.can_bus = CAN(self.spi0, self.spi0cs2, loopback=True, silent=True)
            self.hardware['CAN']=True

        except Exception as e:
            self.debug_print("[ERROR][CAN TRANSCEIVER]" + ''.join(traceback.format_exception(e)))

        # Initialize Neopixel
        try:
            self.neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, pixel_order=neopixel.GRB)
            self.neopixel[0] = (0,0,255)
            self.hardware['Neopixel'] = True
        except Exception as e:
            self.debug_print('[WARNING][Neopixel]' + ''.join(traceback.format_exception(e)))

        # Initialize IMU
        try:
            self.accel = adafruit_lsm303_accel.LSM303_Accel(self.i2c1)
            self.hardware['ACCEL'] = True
        except Exception as e:
            self.debug_print('[ERROR][ACCEL]' + ''.join(traceback.format_exception(e)))
        try:
            self.mag = adafruit_lis2mdl.LIS2MDL(self.i2c1)
            self.hardware['MAG'] = True
        except Exception as e:
            self.debug_print('[ERROR][MAG]' + ''.join(traceback.format_exception(e)))
        try:
            self.gyro = lsm6dsox.LSM6DSOX(self.i2c1,address=0x6b)
            self.hardware['GYRO'] = True
        except Exception as e:
            self.debug_print('[ERROR][GYRO]' + ''.join(traceback.format_exception(e)))

        # Initialize PCT2075 Temperature Sensor
        try:
            self.pct = adafruit_pct2075.PCT2075(self.i2c0, address=0x4F)
            self.hardware['TEMP'] = True
        except Exception as e:
            self.debug_print('[ERROR][TEMP SENSOR]' + ''.join(traceback.format_exception(e)))

        # Initialize TCA
        try:
            self.tca = adafruit_tca9548a.TCA9548A(self.i2c0,address=int(0x77))
            for channel in range(8):
                if self.tca[channel].try_lock():
                    self.debug_print("Channel {}:".format(channel))
                    addresses = self.tca[channel].scan()
                    print([hex(address) for address in addresses if address != 0x70])
                    self.tca[channel].unlock()
        except Exception as e:
            self.debug_print("[ERROR][TCA]" + ''.join(traceback.format_exception(e)))

        # Initialize LiDAR
        try:
            self.LiDAR = adafruit_vl6180x.VL6180X(self.i2c1,offset=0)
            self.hardware['LiDAR'] = True
        except Exception as e:
            self.debug_print('[ERROR][LiDAR]' + ''.join(traceback.format_exception(e)))

        # Initialize radio #1 - UHF
        try:
            self.radio1 = pysquared_rfm9x.RFM9x(self.spi0, _rf_cs1, _rf_rst1,self.radio_cfg['freq'],code_rate=8,baudrate=1320000)
            # Default LoRa Modulation Settings
            # Frequency: 437.4 MHz, SF7, BW125kHz, CR4/8, Preamble=8, CRC=True
            self.radio1.dio0=self.radio1_DIO0
            #self.radio1.dio4=self.radio1_DIO4
            self.radio1.max_output=True
            self.radio1.tx_power=self.radio_cfg['pwr']
            self.radio1.spreading_factor=self.radio_cfg['sf']
            self.radio1.node=self.radio_cfg['id']
            self.radio1.destination=self.radio_cfg['gs']
            self.radio1.enable_crc=True
            self.radio1.ack_delay=0.2
            if self.radio1.spreading_factor > 9: self.radio1.preamble_length = self.radio1.spreading_factor
            self.hardware['Radio1'] = True
            self.enable_rf.value = False
        except Exception as e:
            self.debug_print('[ERROR][RADIO 1]' + ''.join(traceback.format_exception(e)))

        # Prints init state of PySquared hardware
        self.debug_print(str(self.hardware))

        # set PyCubed power mode
        self.power_mode = 'normal'

    def reinit(self,dev):
        if dev=='pwr':
            self.pwr.__init__(self.i2c0)
        elif dev=='fld':
            self.faces.__init__(self.i2c0)
        elif dev=='lidar':
            self.LiDAR.__init__(self.i2c1)
        else:
            self.debug_print('Invalid Device? ->' + str(dev))

    @property
    def burnarm(self):
        return self.f_burnarm
    @burnarm.setter
    def burnarm(self, value):
        self.f_burnarm = value

    @property
    def burned(self):
        return self.f_burned
    @burned.setter
    def burned(self, value):
        self.f_burned = value

    @property
    def dist(self):
        return self.c_distance
    @dist.setter
    def dist(self, value):
        self.c_distance = int(value)

    @property
    def RGB(self):
        return self.neopixel[0]
    @RGB.setter
    def RGB(self,value):
        if self.hardware['Neopixel']:
            try:
                self.neopixel[0] = value
            except Exception as e:
                self.debug_print('[ERROR]' + ''.join(traceback.format_exception(e)))
        else:
            self.debug_print('[WARNING] neopixel not initialized')

    @property
    def uptime(self):
        self.CURRENTTIME=const(time.time())
        return self.CURRENTTIME-self.BOOTTIME

    @property
    def reset_vbus(self):
        # unmount SD card to avoid errors
        if self.hardware['SDcard']:
            try:
                umount('/sd')
                self.spi.deinit()
                time.sleep(3)
            except Exception as e:
                self.debug_print('error unmounting SD card' + ''.join(traceback.format_exception(e)))
        try:
            self._resetReg.drive_mode=digitalio.DriveMode.PUSH_PULL
            self._resetReg.value=1
        except Exception as e:
            self.debug_print('vbus reset error: ' + ''.join(traceback.format_exception(e)))
    
    @property
    def internal_temperature(self):
        return self.pct.temperature

    def distance(self):
        if self.hardware['LiDAR']:
            try:
                distance_mm = 0
                for _ in range(10):
                    distance_mm += self.LiDAR.range
                    time.sleep(0.01)
                self.debug_print('distance measured = {0}mm'.format(distance_mm/10))
                return distance_mm/10
            except Exception as e:
                self.debug_print('LiDAR error: ' + ''.join(traceback.format_exception(e)))
        else:
            self.debug_print('[WARNING] LiDAR not initialized')
        return 0

    def log(self,filedir,msg):
        if self.hardware['SDcard']:
            try:
                self.debug_print(f"writing {msg} to {filedir}")
                with open(filedir, "a+") as f:
                    t=int(time.monotonic())
                    f.write('{}, {}\n'.format(t,msg))
            except Exception as e:
                self.debug_print('SD CARD error: ' + ''.join(traceback.format_exception(e)))
        else:
            self.debug_print('[WARNING] SD Card not initialized')
    
    def check_reboot(self):
        self.UPTIME=self.uptime
        self.debug_print(str("Current up time: "+str(self.UPTIME)))
        if self.UPTIME>86400:
            self.reset_vbus()

    def print_file(self,filedir=None,binary=False):
        try:
            if filedir==None:
                raise Exception("file directory is empty")
            self.debug_print(f'--- Printing File: {filedir} ---')
            if binary:
                with open(filedir, "rb") as file:
                    self.debug_print(file.read())
                    self.debug_print('')
            else:
                with open(filedir, "r") as file:
                    for line in file:
                        self.debug_print(line.strip())
        except Exception as e:
            self.debug_print('[ERROR] Cant print file: ' + ''.join(traceback.format_exception(e)))
    
    def read_file(self,filedir=None,binary=False):
        try:
            if filedir==None:
                raise Exception("file directory is empty")
            self.debug_print(f'--- reading File: {filedir} ---')
            if binary:
                with open(filedir, "rb") as file:
                    self.debug_print(file.read())
                    self.debug_print('')
                    return file.read()
            else:
                with open(filedir, "r") as file:
                    for line in file:
                        self.debug_print(line.strip())
                    return file
        except Exception as e:
            self.debug_print('[ERROR] Cant print file: ' + ''.join(traceback.format_exception(e)))

    def new_file(self,substring,binary=False):
        '''
        substring something like '/data/DATA_'
        directory is created on the SD!
        int padded with zeros will be appended to the last found file
        '''
        if self.hardware['SDcard']:
            try:
                ff=''
                n=0
                _folder=substring[:substring.rfind('/')+1]
                _file=substring[substring.rfind('/')+1:]
                self.debug_print('Creating new file in directory: /sd{} with file prefix: {}'.format(_folder,_file))
                try: chdir('/sd'+_folder)
                except OSError:
                    self.debug_print('Directory {} not found. Creating...'.format(_folder))
                    try: mkdir('/sd'+_folder)
                    except Exception as e:
                        self.debug_print("Error with creating new file: " + ''.join(traceback.format_exception(e)))
                        return None
                for i in range(0xFFFF):
                    ff='/sd{}{}{:05}.txt'.format(_folder,_file,(n+i)%0xFFFF)
                    try:
                        if n is not None:
                            stat(ff)
                    except:
                        n=(n+i)%0xFFFF
                        # print('file number is',n)
                        break
                self.debug_print('creating file...'+str(ff))
                if binary: b='ab'
                else: b='a'
                with open(ff,b) as f:
                    f.tell()
                chdir('/')
                return ff
            except Exception as e:
                self.debug_print("Error creating file: " + ''.join(traceback.format_exception(e)))
                return None
        else:
            self.debug_print('[WARNING] SD Card not initialized')

    def burn(self,burn_num,dutycycle=0,freq=1000,duration=1):
        """
        Operate burn wire circuits. Wont do anything unless the a nichrome burn wire
        has been installed.

        IMPORTANT: See "Burn Wire Info & Usage" of https://pycubed.org/resources
        before attempting to use this function!

        burn_num:  (string) which burn wire circuit to operate, must be either '1' or '2'
        dutycycle: (float) duty cycle percent, must be 0.0 to 100
        freq:      (float) frequency in Hz of the PWM pulse, default is 1000 Hz
        duration:  (float) duration in seconds the burn wire should be on
        """
        try:
            # convert duty cycle % into 16-bit fractional up time
            dtycycl=int((dutycycle/100)*(0xFFFF))
            self.debug_print('----- BURN WIRE CONFIGURATION -----')
            self.debug_print('\tFrequency of: {}Hz\n\tDuty cycle of: {}% (int:{})\n\tDuration of {}sec'.format(freq,(100*dtycycl/0xFFFF),dtycycl,duration))
            # create our PWM object for the respective pin
            # not active since duty_cycle is set to 0 (for now)
            if '1' in burn_num:
                burnwire = pwmio.PWMOut(board.BURN_ENABLE, frequency=freq, duty_cycle=0)
            else:
                return False
            # Configure the relay control pin & open relay
            self._relayA.drive_mode=digitalio.DriveMode.PUSH_PULL
            self._relayA.value = 1
            self.RGB=(255,165,0)
            # Pause to ensure relay is open
            time.sleep(0.5)
            # Set the duty cycle over 0%
            # This starts the burn!
            burnwire.duty_cycle=dtycycl
            time.sleep(duration)
            # Clean up
            self._relayA.value = 0
            burnwire.duty_cycle=0
            self.RGB=(0,0,0)
            #burnwire.deinit()
            self._relayA.drive_mode=digitalio.DriveMode.OPEN_DRAIN
            return True
        except Exception as e:
            self.debug_print("Error with Burn Wire: " + ''.join(traceback.format_exception(e)))
            return False
        finally:
            self._relayA.value = 0
            burnwire.duty_cycle=0
            self.RGB=(0,0,0)
            burnwire.deinit()
            self._relayA.drive_mode=digitalio.DriveMode.OPEN_DRAIN

    def smart_burn(self,burn_num,dutycycle=0.1):
        """
        Operate burn wire circuits. Wont do anything unless the a nichrome burn wire
        has been installed.

        IMPORTANT: See "Burn Wire Info & Usage" of https://pycubed.org/resources
        before attempting to use this function!

        burn_num:  (string) which burn wire circuit to operate, must be either '1' or '2'
        dutycycle: (float) duty cycle percent, must be 0.0 to 100
        freq:      (float) frequency in Hz of the PWM pulse, default is 1000 Hz
        duration:  (float) duration in seconds the burn wire should be on
        """

        freq = 1000

        distance1=0
        distance2=0
        #self.dist=self.distance()

        try:
            # convert duty cycle % into 16-bit fractional up time
            dtycycl=int((dutycycle/100)*(0xFFFF))
            self.debug_print('----- SMART BURN WIRE CONFIGURATION -----')
            self.debug_print('\tFrequency of: {}Hz\n\tDuty cycle of: {}% (int:{})'.format(freq,(100*dtycycl/0xFFFF),dtycycl))
            # create our PWM object for the respective pin
            # not active since duty_cycle is set to 0 (for now)
            if '1' in burn_num:
                burnwire = pwmio.PWMOut(board.BURN_ENABLE, frequency=freq, duty_cycle=0)
            else:
                return False


            try:
                distance1=self.distance()
                self.debug_print(str(distance1))
                if distance1 > self.dist+2 and distance1 > 4 or self.f_triedburn == True:
                    self.burned = True
                    self.f_brownout = True
                    raise TypeError("Wire seems to have burned and satellite browned out")
                else:
                    self.dist=int(distance1)
                    self.burnarm=True
                if self.burnarm:
                    self.burnarm=False
                    self.f_triedburn = True

                    # Configure the relay control pin & open relay
                    self.RGB=(0,165,0)

                    self._relayA.drive_mode=digitalio.DriveMode.PUSH_PULL
                    self.RGB=(255,165,0)
                    self._relayA.value = 1

                    # Pause to ensure relay is open
                    time.sleep(0.5)

                    #Start the Burn
                    burnwire.duty_cycle=dtycycl

                    #Burn Timer
                    start_time = time.monotonic()

                    #Monitor the burn
                    while not self.burned:
                        distance2=self.distance()
                        self.debug_print(str(distance2))
                        if distance2 > distance1+1 or distance2 > 10:
                            self._relayA.value = 0
                            burnwire.duty_cycle = 0
                            self.burned=True
                            self.f_triedburn = False
                        else:
                            distance1=distance2
                            time_elapsed = time.monotonic() - start_time
                            print("Time Elapsed: " + str(time_elapsed))
                            if time_elapsed > 4:
                                self._relayA.value = 0
                                burnwire.duty_cycle = 0
                                self.burned=False
                                self.RGB=(0,0,255)
                                time.sleep(10)
                                self.f_triedburn = False
                                break

                    time.sleep(5)
                    distance2=self.distance()
                else:
                    pass
                if distance2 > distance1+2 or distance2 > 10:
                    self.burned=True
                    self.f_triedburn = False
            except Exception as e:
                self.debug_print("Error in Burn Sequence: " + ''.join(traceback.format_exception(e)))
                self.debug_print("Error: " + str(e))
                if "no attribute 'LiDAR'" in str(e):
                    self.debug_print("Burning without LiDAR")
                    time.sleep(120) #Set to 120 for flight
                    self.burnarm=False
                    self.burned=True
                    self.f_triedburn=True
                    self.burn("1",dutycycle,freq,4)
                    time.sleep(5)

            # Clean up
            self._relayA.value = 0
            burnwire.duty_cycle = 0
            self.RGB=(0,0,0)
            #burnwire.deinit()
            self._relayA.drive_mode=digitalio.DriveMode.OPEN_DRAIN
            return True
        except Exception as e:
            self.debug_print("Error with Burn Wire: " + ''.join(traceback.format_exception(e)))
            return False
        finally:
            self._relayA.value = 0
            burnwire.duty_cycle=0
            self.RGB=(0,0,0)
            burnwire.deinit()
            self._relayA.drive_mode=digitalio.DriveMode.OPEN_DRAIN



print("Initializing CubeSat")
cubesat = Satellite()
