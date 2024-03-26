'''
This is the class that contains all of the functions for our CubeSat. 
We pass the cubesat object to it for the definitions and then it executes 
our will.
Authors: Nicole Maggard, Michael Pham, and Rachel Sarmiento
'''
import time
import alarm
import gc
import traceback
import random
from debugcolor import co

# Import for the CAN Bus Manager 
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest #pylint: disable=import-error

class functions:
    #Placeholders for the CAN Bus Manager
    FILE_IDS = {
        'file1': 0x01,
        'file2': 0x02,
        'file3': 0x03,
        # Add more files as needed
    }

    def debug_print(self,statement):
        if self.debug:
            print(co("[Functions]" + str(statement), 'green', 'bold'))
    def __init__(self,cubesat):
        self.cubesat = cubesat
        self.debug = cubesat.debug
        self.debug_print("Initializing Functionalities")
        self.Errorcount=0
        self.facestring=[]
        self.jokes=["Hey Its pretty cold up here, did someone forget to pay the electric bill?"]
        self.last_battery_temp = 20
        self.callsign="Callsign"
        self.face_id=0x00AA
        self.state_bool=False
        self.face_data_baton = False
        self.detumble_enable_z = True
        self.detumble_enable_x = True
        self.detumble_enable_y = True
        try:
            self.cubesat.all_faces_on()
        except Exception as e:
            self.debug_print("Couldn't turn faces on: " + ''.join(traceback.format_exception(e)))
    
    def current_check(self):
        return self.cubesat.current_draw

    '''
    Radio Functions
    '''  
    def send(self,msg):
        """Calls the RFM9x to send a message. Currently only sends with default settings.
        
        Args:
            msg (String,Byte Array): Pass the String or Byte Array to be sent. 
        """
        import Field
        self.field = Field.Field(self.cubesat,self.debug)
        message=f"{self.callsign} " + str(msg) + f" {self.callsign}"
        self.field.Beacon(message)
        if self.cubesat.f_fsk:
            self.cubesat.radio1.cw(message)
        if self.cubesat.is_licensed:
            self.debug_print(f"Sent Packet: " + message)
        else:
            self.debug_print("Failed to send packet")
        del self.field
        del Field

    def beacon(self):
        """Calls the RFM9x to send a beacon. """
        import Field
        try:
            lora_beacon = f"{self.callsign} Hello I am Yearling^2! I am in: " + str(self.cubesat.power_mode) +" power mode. V_Batt = " + str(self.cubesat.battery_voltage) + f"V. IHBPFJASTMNE! {self.callsign}"
        except Exception as e:
            self.debug_print("Error with obtaining power data: " + ''.join(traceback.format_exception(e)))
            lora_beacon = f"{self.callsign} Hello I am Yearling^2! I am in: " + "an unidentified" +" power mode. V_Batt = " + "Unknown" + f". IHBPFJASTMNE! {self.callsign}"

        self.field = Field.Field(self.cubesat,self.debug)
        self.field.Beacon(lora_beacon)
        if self.cubesat.f_fsk:
            self.cubesat.radio1.cw(lora_beacon)
        del self.field
        del Field
    
    def joke(self):
        self.send(random.choice(self.jokes))
    

    def state_of_health(self):
        import Field
        self.state_list=[]
        #list of state information 
        try:
            self.state_list = [
                f"PM:{self.cubesat.power_mode}",
                f"VB:{self.cubesat.battery_voltage}",
                f"ID:{self.cubesat.current_draw}",
                f"IC:{self.cubesat.charge_current}",
                f"VS:{self.cubesat.system_voltage}",
                f"UT:{self.cubesat.uptime}",
                f"BN:{self.cubesat.c_boot}",
                f"MT:{self.cubesat.micro.cpu.temperature}",
                f"RT:{self.cubesat.radio1.former_temperature}",
                f"AT:{self.cubesat.internal_temperature}",
                f"BT:{self.last_battery_temp}",
                f"AB:{int(self.cubesat.burned)}",
                f"BO:{int(self.cubesat.f_brownout)}",
                f"FK:{int(self.cubesat.f_fsk)}"
            ]
        except Exception as e:
            self.debug_print("Couldn't aquire data for the state of health: " + ''.join(traceback.format_exception(e)))
        
        self.field = Field.Field(self.cubesat,self.debug)
        if not self.state_bool:
            self.field.Beacon(f"{self.callsign} Yearling^2 State of Health 1/2" + str(self.state_list)+ f"{self.callsign}")
            if self.cubesat.f_fsk:
                self.cubesat.radio1.cw(f"{self.callsign} Yearling^2 State of Health 1/2" + str(self.state_list)+ f"{self.callsign}")
            self.state_bool=True
        else:
            self.field.Beacon(f"{self.callsign} YSOH 2/2" + str(self.cubesat.hardware) +f"{self.callsign}")
            if self.cubesat.f_fsk:
                self.cubesat.radio1.cw(f"{self.callsign} YSOH 2/2" + str(self.cubesat.hardware) +f"{self.callsign}")
            self.state_bool=False
        del self.field
        del Field

    def send_face(self):
        """Calls the data transmit function from the field class
        """
        import Field
        self.field = Field.Field(self.cubesat,self.debug)
        self.debug_print("Sending Face Data")
        self.field.Beacon(f'{self.callsign} Y-: {self.facestring[0]} Y+: {self.facestring[1]} X-: {self.facestring[2]} X+: {self.facestring[3]}  Z-: {self.facestring[4]} {self.callsign}')
        if self.cubesat.f_fsk:
                self.cubesat.radio1.cw(f'{self.callsign} Y-: {self.facestring[0]} Y+: {self.facestring[1]} X-: {self.facestring[2]} X+: {self.facestring[3]}  Z-: {self.facestring[4]} {self.callsign}')
        del self.field
        del Field
    
    def listen(self):
        import cdh
        #This just passes the message through. Maybe add more functionality later. 
        try:
            self.debug_print("Listening")
            self.cubesat.radio1.receive_timeout=10
            received = self.cubesat.radio1.receive(keep_listening=True)
        except Exception as e:
            self.debug_print("An Error has occured while listening: " + ''.join(traceback.format_exception(e)))
            received=None

        try:
            if received is not None:
                self.debug_print("Recieved Packet: "+str(received))
                cdh.message_handler(self.cubesat,received)
                return True
        except Exception as e:
            self.debug_print("An Error has occured while handling command: " + ''.join(traceback.format_exception(e)))
        finally:
            del cdh
        
        return False
    
    def listen_joke(self):
        try:
            self.debug_print("Listening")
            self.cubesat.radio1.receive_timeout=10
            received = self.cubesat.radio1.receive(keep_listening=True)
            if received is not None and "HAHAHAHAHA!" in received:
                return True
            else:
                return False
        except Exception as e:
            self.debug_print("An Error has occured while listening: " + ''.join(traceback.format_exception(e)))
            received=None
            return False
    
    def all_face_data(self):
        
        #create method to check all faces are on (can do by polling battery board or by polling faces or both)
        try:
            import Big_Data
            a = Big_Data.AllFaces(self.debug,self.cubesat.tca)
            
            self.facestring = a.Face_Test_All()
            
            del a
            del Big_Data
        except Exception as e:
            self.debug_print("Big_Data error" + ''.join(traceback.format_exception(e)))
        
        return self.facestring
    
    def get_imu_data(self):
        
        try:
            data=[]
            data.append(self.cubesat.accel.acceleration)
            data.append(self.cubesat.gyro.gyro)
            data.append(self.cubesat.mag.magnetic)
        except Exception as e:
            self.debug_print("Error retrieving IMU data" + ''.join(traceback.format_exception(e)))
        
        return data
    
    #=======================================================#
    # Interboard Communitication Functions                 #
    #=======================================================#

    def send_face(self):
        try:
            self.debug_print("Sending Face Data to FC")
            for x in self.facestring:
                self.send_can(self.face_id,x)    
        except Exception as e:
            self.debug_print("Error Sending data over CAN bus" + ''.join(traceback.format_exception(e))) #pylint: disable=no-value-for-parameter


    # Example of how the calling class might handle the result
    #can_helper = CanBusHelper(can_bus, owner, debug)
    #
    #result = can_helper.listen_messages(timeout=5)
    #if result is not None:
    #    if result['type'] == 'RTR':
    #        # Handle Remote Transmission Request
    #        data_to_send = retrieve_data_based_on_rtr_id(result['id'])
    #        can_helper.send_can("DATA_RESPONSE", data_to_send)
    #    elif result['type'] == 'FAULT':
    #        # Handle Fault Message
    #        handle_fault(result['content'])



    def send_can(self, id, messages):
        if not isinstance(messages, list):
            messages = [messages]  # If messages is not a list, make it a list
        try:
            for message in messages:
                message=str(message)
                if isinstance(message, str):
                    byte_message = bytes(message, "UTF-8")
                else:
                    byte_message = bytes(message)
                self.cubesat.can_bus.send(Message(id,byte_message))
                self.debug_print("Sent CAN message: " + str(message))
        except Exception as e:
            self.debug_print("Error Sending data over CAN bus" + ''.join(traceback.format_exception(None, e, e.__traceback__)))  #pylint: disable=no-value-for-parameter

    # Made by CoPilot - Probably Not Working
    def listen_can_messages(self):
        with self.cubesat.can_bus.listen(timeout=1.0) as listener:
            message_count = listener.in_waiting()
            self.debug_print(str(message_count) + " messages available")
            for _i in range(message_count):
                msg = listener.receive()
                self.debug_print("Message from " + hex(msg.id))

                # We aren't sure if isinstance checks currently work
                if isinstance(msg, Message):
                    self.debug_print("message data: " + str(msg.data))
                if isinstance(msg, RemoteTransmissionRequest):
                    self.debug_print("RTR length: " + str(msg.length))
                    # Here you can process the RTR request
                    # For example, you might send a response with the requested data
                    response_data = self.get_data_for_rtr(msg.id)
                    if isinstance(response_data, list):
                        response_messages = [Message(id=msg.id, data=data, extended=True) for data in response_data]
                    else:
                        response_messages = [Message(id=msg.id, data=response_data, extended=True)]
                    self.cubesat.send_can(response_messages)

    def get_data_for_rtr(self, id):

        if id == 0x01:  # Replace with the actual ID for all_face_data
            all_face_data = bytes(self.all_face_data())  # This should return a bytes object
            messages = []
            start_message = Message(id=0x01, data=b'start', extended=True)
            messages.append(start_message)
            for i in range(0, len(all_face_data), 8):
                chunk = all_face_data[i:i+8]
                message = Message(id=0x02, data=chunk, extended=True)
                messages.append(message)
            stop_message = Message(id=0x03, data=b'stop', extended=True)
            messages.append(stop_message)
            return messages
        
        elif id == 0x02:  # Replace with the actual ID for sensor 2
            return self.get_sensor_2_data()
        elif id == 0x03:  # Replace with the actual ID for sensor 3
            return self.get_sensor_3_data()
        else:
            # Default case if no matching ID is found
            return bytes([0x01, 0x02, 0x03, 0x04])
        
    def request_file(self, file_id, timeout=5.0):
        # Send RTR for the file
        rtr = RemoteTransmissionRequest(id=file_id)
        self.cubesat.can_bus.send(rtr)

        # Listen for response and reconstruct the file
        file_data = bytearray()
        start_time = time.monotonic()
        while True:
            if time.monotonic() - start_time > timeout:
                raise TimeoutError("No response received for file request")
            msg = self.cubesat.can_bus.receive()
            if msg is None:
                continue  # No message received, continue waiting
            if isinstance(msg, Message) and msg.id == file_id:
                if msg.data == b'start':
                    continue
                elif msg.data == b'stop':
                    break
                else:
                    file_data.extend(msg.data)
        return file_data
    
    def OTA(self):
        # resets file system to whatever new file is received
        pass

    '''
    Logging Functions
    '''  
    def log_face_data(self,data):
        
        self.debug_print("Logging Face Data")
        try:
                self.cubesat.log("/faces.txt",data)
        except:
            try:
                self.cubesat.new_file("/faces.txt")
            except Exception as e:
                self.debug_print('SD error: ' + ''.join(traceback.format_exception(e)))
        
    def log_error_data(self,data):
        
        self.debug_print("Logging Error Data")
        try:
                self.cubesat.log("/error.txt",data)
        except:
            try:
                self.cubesat.new_file("/error.txt")
            except Exception as e:
                self.debug_print('SD error: ' + ''.join(traceback.format_exception(e)))
    
    '''
    Misc Functions
    '''  
    #Goal for torque is to make a control system 
    #that will adjust position towards Earth based on Gyro data
    def detumble(self,dur = 7, margin = 0.2, seq = 118):
        self.debug_print("Detumbling")
        self.cubesat.RGB=(255,255,255)
        self.cubesat.all_faces_on()
        try:
            import Big_Data
            a=Big_Data.AllFaces(self.debug, self.cubesat.tca)
        except Exception as e:
            self.debug_print("Error Importing Big Data: " + ''.join(traceback.format_exception(e)))

        try:
            a.sequence=52
        except Exception as e:
            self.debug_print("Error setting motor driver sequences: " + ''.join(traceback.format_exception(e)))
        
        def actuate(dipole,duration):
            #TODO figure out if there is a way to reverse direction of sequence
            if abs(dipole[0]) > 1:
                a.Face2.drive=52
                a.drvx_actuate(duration)
            if abs(dipole[1]) > 1:
                a.Face0.drive=52
                a.drvy_actuate(duration)
            if abs(dipole[2]) > 1:
                a.Face4.drive=52
                a.drvz_actuate(duration)
            
        def do_detumble():
            try:
                import detumble
                for _ in range(3):
                    data=[self.cubesat.IMU.Gyroscope,self.cubesat.IMU.Magnetometer]
                    data[0]=list(data[0])
                    for x in range(3):
                        if data[0][x] < 0.01:
                            data[0][x]=0.0
                    data[0]=tuple(data[0])
                    dipole=detumble.magnetorquer_dipole(data[1],data[0])
                    self.debug_print("Dipole: " + str(dipole))
                    self.send("Detumbling! Gyro, Mag: " + str(data))
                    time.sleep(1)
                    actuate(dipole,dur)
            except Exception as e:
                self.debug_print("Detumble error: " + ''.join(traceback.format_exception(e)))
        try:
            self.debug_print("Attempting")
            do_detumble()
        except Exception as e:
            self.debug_print('Detumble error: ' + ''.join(traceback.format_exception(e)))
        self.cubesat.RGB=(100,100,50)
        
    
    def Short_Hybernate(self):
        self.debug_print("Short Hybernation Coming UP")
        gc.collect()
        #all should be off from cubesat powermode
        self.cubesat.all_faces_off()
        self.cubesat.enable_rf.value=False
        self.cubesat.f_softboot=True
        time.sleep(120)
        self.cubesat.all_faces_on()
        self.cubesat.enable_rf.value=True
        return True
    
    def Long_Hybernate(self):
        self.debug_print("LONG Hybernation Coming UP")
        gc.collect()
        #all should be off from cubesat powermode
        self.cubesat.all_faces_off()
        self.cubesat.enable_rf.value=False
        self.cubesat.f_softboot=True
        time.sleep(600)
        self.cubesat.all_faces_on()
        self.cubesat.enable_rf.value=True
        return True
    