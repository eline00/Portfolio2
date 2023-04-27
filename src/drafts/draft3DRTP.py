from socket import *
from struct import pack, unpack

class DRTP:
    def __init__(self, ip, port, socket):
        # Initialize DRTP instance variables
        self.ip = ip
        self.port = port
        self.socket = socket
        self.ACK = 1 << 0
        self.SYN = 1 << 1
        self.FIN = 1 << 2

    def send_packet(self, packet):
        addr = (self.ip, self.port)
        self.socket.sendto(packet, addr)
        

    def receive_packet(self):
        packet, addr = self.socket.recvfrom(1472)
        return packet, addr

    def create_packet(self, seq_num, ack_num, flags, window, data):
        header = pack("!IIHH", seq_num, ack_num, flags, window)
        packet = header + data
        return packet
    
    def parse_packet(self, packet):
        header = packet[:12]
        data = packet[12:]
        seq_num, ack_num, flags, window = unpack("!IIHH", header)
        return seq_num, ack_num, flags, window, data if data else b''

    def syn_server(self):
        # Server side logic for connection establishment
        while True:
            packet, addr = self.receive_packet()
            seq_num, ack_num, flags, window, _ = self.parse_packet(packet)
            if flags & self.SYN:
                # Received SYN packet from the client
                self.send_packet(self.create_packet(seq_num+1, ack_num+1, self.SYN | self.ACK, window, b''))
                break

    def syn_client(self):
        # Client side logic for connection establishment
        syn_seq_num = 0  # You can use a random sequence number or a fixed one like this
        syn_packet = self.create_packet(syn_seq_num, 0, self.SYN, 64, b'')
        self.send_packet(syn_packet)

        while True:
            try:
                packet = self.receive_packet()
                seq_num, ack_num, flags, window, _ = self.parse_packet(packet)
                if flags & self.SYN and flags & self.ACK and ack_num == syn_seq_num + 1:
                    # Received SYN-ACK packet from the server
                    self.send_packet(self.create_packet(seq_num+1, ack_num, self.ACK, window, b''))
                    break
            except socket.timeout:
                # Resend the SYN packet if the timeout occurs
                self.send_packet(syn_packet)


    def fin(self):
        fin_flag = 0x01
        fin_packet = self.create_packet(0, 0, fin_flag, 64, b'')
        self.send_packet(fin_packet)

        while True:
            try:
                self.socket.settimeout(1)  # Set a timeout of 1 second
                ack_packet, _ = self.receive_packet()
                _, _, flags, _, _ = self.parse_packet(ack_packet)
                if flags != 0x10:  # ACK flag is set
                    break
            except socket.timeout:
                # Resend the FIN packet if the timeout occurs
                self.send_packet(fin_packet)
        else:
            raise Exception("FIN-ACK not received")

        
    def close(self):
        self.socket.close()
