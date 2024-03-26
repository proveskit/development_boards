import gc
import pysquared_w5500
import time
gc.enable()
print(str(gc.mem_free()) + " Bytes remaining")
class ftp:
    def debug_print(self, msg) -> None:
        if self.debug:
            print(str(msg))
    def __init__(self, debug,spi_bus,cs,MAC) -> None:
        self.debug=debug
        self.num_packets=0
        self.packets=[]
        if spi_bus is None:
            raise("please define SPI Bus")
        self.eth = pysquared_w5500.WIZNET5500(spi_bus, cs,mac=MAC,debug=self.debug)
    
    def img_to_hex(self, file: str ='') -> str:
        try:
            string = ''
            with open(file, 'rb') as f:
                binValue = f.read(1)
                self.debug_print("done reading image! converting data...")
                while len(binValue) != 0:
                    hexVal = hex(ord(binValue))
                    hexVal = hexVal.replace("0x","")
                    if len(hexVal) == 1:
                        hexVal = "0" + hexVal
                    string += hexVal
                    binValue = f.read(1)
            self.debug_print(str(gc.mem_free()) + " Bytes remaining")
            gc.collect()
            return string
        except Exception as e:
            self.debug_print("Error Converting image to Hex" + str(e))
    
    def packetize(self, string: str = '',packet_size: int = 1024) -> list:
        self.packets = [(string[i:i+packet_size]) for i in range(0, len(string), packet_size)]
        self.num_packets=len(self.packets)
        return self.num_packets,self.packets
    
    def send_packets(self,HOST,PORT,TIMEOUT):
        pysquared_w5500.set_interface(self.eth)
        s = pysquared_w5500.socket(pysquared_w5500.AF_INET, pysquared_w5500.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        self.debug_print(f"Connecting to {HOST}:{PORT}")
        s.connect((HOST, PORT))
        self.debug_print("Connected! Attempting to send packets...")
        try:
            for a in range(self.num_packets):
                size = s.send(self.packets[a])
                print("Sent", size, "bytes")
                buf = s.recv(1)
                buf=str(buf)
                self.debug_print("buffer: " + buf)
                if buf is 'b\'1\'':
                    self.debug_print("Aknowledgement received!")
                    continue
                elif buf is 'b\'0\'' or buf is '':
                    s.close()
                    raise("No aknowledgement received")
                else:
                    self.debug_print("Unknown command in buffer")
                    break
            s.close()
            return True
        except Exception as e:
            self.debug_print("Failed to send packets: " + str(e))
            return False
    
    def receive_packets(self,ip_address,port,packet_size):
        self.eth.ifconfig=ip_address

        # Initialize a socket for our server
        pysquared_w5500.set_interface(self.eth)
        server = pysquared_w5500.socket()  # Allocate socket for the server
        server_ip = self.eth.pretty_ip(self.eth.ip_address)  # IP address of server
        server_port = port  # Port to listen on
        server.bind((server_ip, server_port))  # Bind to IP and Port
        server.listen()  # Begin listening for incoming clients
        self.debug_print(f"Accepting connections on {server_ip}:{server_port}")
        conn, addr = server.accept()  # Wait for a connection from a client.
        self.debug_print(f"Connection accepted from {addr}, reading exactly 1024 bytes from client")
        conn.settimeout(10)
        while True:
            self.debug_print("loop iteration")
            self.debug_print("waiting for stuff...")
            stuff=conn.recv(packet_size)
            stuff=str(stuff)
            if stuff is not None or stuff is not 'b\'\'':
                stuff = stuff.replace("b\'","")
                stuff = stuff.replace("\'","")
                self.packets.append(stuff)
                self.debug_print(stuff)
                self.debug_print("sending aknowledgement!")
                try:
                    conn.send('1')
                except Exception as e:
                    self.debug_print("Couldnt send aknowledgement: " + str(e))
                    break
                self.debug_print("aknowledgement sent!")
            else:
                self.debug_print("stuff was none")
                conn.close()
                break
            self.debug_print("its about to iterate!")
        self.num_packets=len(self.packets)
        return self.num_packets,self.packets
