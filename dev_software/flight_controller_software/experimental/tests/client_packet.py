import file_transfer
import board
import busio
import digitalio
import time

print("W5500 SimpleServer Test")

# For Adafruit Ethernet FeatherWing
cs = digitalio.DigitalInOut(board.SPI1_CS1)
# For Particle Ethernet FeatherWing
# cs = digitalio.DigitalInOut(board.D5)
spi_bus = busio.SPI(board.SPI1_SCK, MOSI=board.SPI1_MOSI, MISO=board.SPI1_MISO)
MAC = (0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xEE)

# Initialize ethernet interface
ftp=file_transfer.ftp(True,spi_bus,cs,MAC)
HOST = "48.48.67.48"
PORT = 50007
TIMEOUT = 10
ftp.packetize(ftp.img_to_hex('mc_had_it.jpg'),1024)
print("packet num: " + str(ftp.num_packets))
ftp.send_packets(HOST,PORT,TIMEOUT)