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
RST = 0x01

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
                response, _ = sock.recvfrom(PACKET_SIZE)
                resp_seq_number, resp_ack_number, resp_flags, resp_window, resp_msg_body = parse_packet(response)
                if resp_ack_number == seq_number + 1 and resp_flags & ACK:
                    seq_number += 1
                    break
            except socket.timeout:
                continue

    fin_packet = create_packet(seq_number, ack_number, FIN, WINDOW)
    sock.sendto(fin_packet, addr)

def gbn(sock, addr, msg):
    base = 0
    next_seq_number = 0
    window_size = 5

    def resend_unacked_packets():
        nonlocal base
        for i in range(base, next_seq_number):
            sock.sendto(packets[i % window_size], addr)
        timer = Timer(TIMEOUT, resend_unacked_packets)
        timer.start()

    packets = [b'' for _ in range(window_size)]

    while base < len(msg):
        while next_seq_number < base + window_size and next_seq_number * APP_DATA_SIZE < len(msg):
            start_idx = next_seq_number * APP_DATA_SIZE
            end_idx = start_idx + APP_DATA_SIZE
            data_chunk = msg[start_idx:end_idx]
            packet = create_packet(next_seq_number, 0, ACK, WINDOW, data_chunk)
            packets[next_seq_number % window_size] = packet
            sock.sendto(packet, addr)
            next_seq_number += 1

        sock.settimeout(TIMEOUT)
        try:
            response, _ = sock.recvfrom(PACKET_SIZE)
            _, resp_ack_number, resp_flags, _, _ = parse_packet(response)

            if resp_flags & ACK:
                base = resp_ack_number
        except socket.timeout:
            resend_unacked_packets()

    fin_packet = create_packet(next_seq_number, 0, FIN, WINDOW)
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

