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
MAC = (0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xEF)

# Initialize ethernet interface
ip_address=(b'00C0',b'00A8',b'000A',b'0001')
ftp=file_transfer.ftp(True,spi_bus,cs,MAC)

ftp.receive_packets(ip_address,50007,1024)
print(ftp.num_packets)
print(*ftp.packets,sep='')