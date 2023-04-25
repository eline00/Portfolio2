import socket
import sys
import struct
import time
from threading import Timer

SEQUENCE_SIZE = 32
ACKNOWLEDGEMENT_SIZE = 32
FLAGS_SIZE = 16
WINDOW_SIZE = 16

SYN = 0x08
ACK = 0x04
FIN = 0x02
RESET = 0x01

HEADER_SIZE = 12
PACKET_SIZE = 1472
APPLICATION_SIZE = PACKET_SIZE - HEADER_SIZE

WINDOW = 64
TIMEOUT = 0.5

def create_packet(seq, ack, flags, window, msg=b''):
    header = struct.pack('!IIHH', seq, ack, flags, window)
    return header + msg

def parse_packet(packet):
    seq, ack, flags, window = struct.unpack('!IIHH', packet[:HEADER_SIZE])
    msg = packet[HEADER_SIZE:]
    return seq, ack, flags, window, msg

def stop_and_wait(sock, addr, msg):
    seq = 0
    ack = 0
    for i in range(0, len(msg), APPLICATION_SIZE):
        data_chunk = msg[i:i + APPLICATION_SIZE]
        packet = create_packet(seq, ack, ACK, WINDOW, data_chunk)
        while True:
            sock.sendto(packet, addr)
            sock.settimeout(TIMEOUT)
            try:
                response, address = sock.recvfrom(PACKET_SIZE)
                received_seq, received_ack, received_flags, received_window, received_msg = parse_packet(response)
                if resceived_ack == seq + 1 and recieved_flags & ACK:
                    seq += 1
                    break
            except socket.timeout:
                continue

    fin_packet = create_packet(seq, ack, FIN, WINDOW)
    sock.sendto(fin_packet, addr)

def gbn(sock, addr, msg):
    base = 0
    next_seq = 0
    window_size = 5
    
    # Initialize a list of empty byte strings with a fixed size
    packets = [b""]
    for i in range(1, window_size):
        packets.append(b"")

    def resend_unacked_packets():
        nonlocal base
        for i in range(base, next_seq):
            sock.sendto(packets[i % window_size], addr)
        timer = Timer(TIMEOUT, resend_unacked_packets)
        timer.start()

    while base < len(msg):
        while next_seq < base + window_size and next_seq * APPLICATION_SIZE < len(msg):
            start_idx = next_seq * APPLICATION_SIZE
            end_idx = start_idx + APPLICATION_SIZE
            data_chunk = msg[start_idx:end_idx]
            packet = create_packet(next_seq, 0, ACK, WINDOW, data_chunk)
            packets[next_seq % window_size] = packet
            sock.sendto(packet, addr)
            next_seq += 1

        sock.settimeout(TIMEOUT)
        try:
            response, address = sock.recvfrom(PACKET_SIZE)
            received_seq, received_ack, received_flags, received_window, received_msg = parse_packet(response)

            if received_flags & ACK:
                base = received_ack
        except socket.timeout:
            resend_unacked_packets()

    fin_packet = create_packet(next_seq, 0, FIN, WINDOW)
    sock.sendto(fin_packet, addr)

def sr(sock, addr, msg):
    raise NotImplementedError("Selective-Repeat protocol is not yet implemented")

def main():
    if len(sys.argv) < 5:
        print("Usage: python DRTP.py <IP> <PORT> -r <PROTOCOL>")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])
    protocol = sys.argv[4].lower()

    if protocol not in ["stop_and_wait", "gbn", "sr"]:
        print("Invalid protocol. Choose from 'stop_and_wait', 'gbn', or 'sr'.")
        sys.exit(1)

    server_address = (ip, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    message = b'Test message for reliable data transfer protocols.'

    if protocol == "stop_and_wait":
        stop_and_wait(sock, server_address, message)
    elif protocol == "gbn":
        gbn(sock, server_address, message)
    elif protocol == "sr":
        sr(sock, server_address, message)

    sock.close()

if __name__ == "__main__":
    main()

