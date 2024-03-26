'''
payload.py
This file contains all software to handle picture taking
Author: Nicole Maggard
'''
import time
import board
import busio
import traceback
from debugcolor import co

class PAYLOAD:
    def debug_print(self,statement):
        if self.debug:
            print(co("[Payload]" + statement, 'gray', 'bold'))
    
    def Enable(self, data):
        self.debug_print("Enabling the following: " + str(data))
        

    def __init__(self, debug, i2c):
        self.debug=debug
        self.debug_print("Initializing BNO055...")
        try:
            self.debug_print("Initialization of BNO complete without error!")
        except Exception as e:
            self.debug_print("ERROR Initializing BNO sensor: " + ''.join(traceback.format_exception(e)))
    
    def reinit(self):
        try:
            self.debug_print("Reinitializing BNO08x...")
            self.debug("Reinitialization of BNO complete without error!")
        except Exception as e:
            self.debug_print("ERROR Initializing BNO sensor: " + ''.join(traceback.format_exception(e)))
