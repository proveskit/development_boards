# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
from time import sleep
import board
import busio
from digitalio import DigitalInOut
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest
from adafruit_mcp2515 import MCP2515 as CAN


cs = DigitalInOut(board.SPI1_CS2)
cs.switch_to_output()
spi = busio.SPI(board.SPI1_SCK,board.SPI1_MOSI,board.SPI1_MISO)

can_bus = CAN(
    spi, cs, loopback=False, silent=False
)  # use loopback to test without another device
while True:
    with can_bus.listen(timeout=1.0) as listener:

        message = Message(id=0x1234ABCE, data=b"Hey", extended=True)
        send_success = can_bus.send(message)
        print("Send success:", send_success)
        message = Message(id=0x1234ABCE, data=b"Ernesto!", extended=True)
        send_success = can_bus.send(message)
        print("Send success:", send_success)
        message_count = listener.in_waiting()
        print(message_count, "messages available")
        for _i in range(message_count):
            msg = listener.receive()
            print("Message from ", hex(msg.id))
            if isinstance(msg, Message):
                print("message data:", msg.data)
            if isinstance(msg, RemoteTransmissionRequest):
                print("RTR length:", msg.length)
    sleep(1)
