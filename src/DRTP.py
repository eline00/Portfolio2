import sys
import socket
import time
from struct import *

header_format = '!IIHH'

def create_packet(seq, ack, flags, win, data):
    header = pack(header_format, seq, ack, flags, win)
    packet = header + data
    return packet


def parse_header(header):
    return unpack(header_format, header)


def parse_flags(flags):
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    return syn, ack, fin


def stop_and_wait_sender(file_data, sockfd, addr):
    # Sender code for stop_and_wait
    pass


def GBN_sender(file_data, sockfd, addr):
    # Sender code for GBN
    pass


def SR_sender(file_data, sockfd, addr):
    # Sender code for SR
    pass


def stop_and_wait_receiver(sockfd, addr, output_file):
    # Receiver code for stop_and_wait
    pass


def GBN_receiver(sockfd, addr, output_file):
    # Receiver code for GBN
    pass


def SR_receiver(sockfd, addr, output_file):
    # Receiver code for SR
    pass


def sender_main():
    # Sender main function
    pass


def receiver_main():
    # Receiver main function
    pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python DRTP.py sender|receiver <arguments>")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "sender":
        sender_main()
    elif mode == "receiver":
        receiver_main()
    else:
        print("Invalid mode. Choose 'sender' or 'receiver'.")
        sys.exit(1)

        