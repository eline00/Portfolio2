import argparse
import time
import os
from DRTP3 import *
import time
import os


def server(args):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', args.port))
    server_drtp = DRTP(args.bind, args.port, server_socket)

    print("-----------------------------------------------")
    print("A server is listening on port", args.port)
    print("-----------------------------------------------")

    server_drtp.syn_server()

    if args.reliability_func == "stop-and-wait":
        stop_and_wait_server(server_drtp, args.file_name, args.test_case)
    elif args.reliability_func == "gbn":
        gbn_server(server_drtp, args.file_name, args.test_case)
    elif args.reliability_func == "sr":
        sr_server(server_drtp, args.file_name, args.test_case)


def client(args):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_drtp = DRTP(args.remote_ip, args.port, client_socket)
    print("\nSending SYN from the client. Waiting for SYN-ACK.")
    client_drtp.syn_client()

    start_time = time.time()

    if args.reliability_func == "stop-and-wait":
        stop_and_wait_client(client_drtp, args.file_name)
    else:
        data_transfer(client_drtp, args.remote_ip, args.port, args.reliability_func, args.file_name, args.window_size, args.test_case)

    end_time = time.time()
    elapsed_time = end_time - start_time

    file_size = (os.path.getsize(args.file_name) * 8) / 1000000  # Convert to bits
    throughput = file_size / elapsed_time  # Mb per second
    print(f"\nElapsed Time: {elapsed_time:.2f} s")
    print(f"Transfered data: {(file_size):.2f} Mb")
    print(f"Throughput: {throughput:.2f} Mbps")

    client_drtp.close()


def data_transfer(drtp, remote_ip, port, reliable_method, file_name, window_size, test_case):
    if reliable_method == 'gbn':
        if test_case == 'skip_ack':
            gbn_client(drtp, file_name, window_size, skip_ack=True)
        elif test_case == 'skip_seq':
            gbn_client(drtp, file_name, window_size, skip_seq=True)
        else:
            gbn_client(drtp, file_name, window_size)
    elif reliable_method == 'sr':
        if test_case == 'skip_ack':
            sr_client(drtp, file_name, window_size, skip_ack=True)
        elif test_case == 'skip_seq':
            sr_client(drtp, file_name, window_size, skip_seq=True)
        else:
            sr_client(drtp, file_name, window_size)

"""
def skip_acknowledgment(args, skip_ack=False):
    if args.reliability_func == "gbn":
        gbn_server(args, skip_ack=skip_ack)
    elif args.reliability_func == "sr":
        sr_server(args, skip_ack=skip_ack)


def skip_sequence_number(args, skip_seq=False):
    if args.reliability_func == "gbn":
        gbn_server(args, skip_seq=skip_seq)
    elif args.reliability_func == "sr":
        sr_server(args, skip_seq=skip_seq)

"""

def stop_and_wait_server(drtp, file, test_case):
    print("\nStop-and-wait server started.")
    with open(file, 'wb') as f:
        expected_seq = 0
        skip_ack_counter = 0

        print("Receiving data...")
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                if flags & drtp.FIN:
                    print("\nFIN flag received. Sending FIN-ACK")
                    # Send an ACK packet for the received FIN packet
                    ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
                    break

                if seq_num == expected_seq:
                    f.write(data)
                    expected_seq += 1

                    if test_case == 'skip_ack' and skip_ack_counter == 0:
                        # Adding a sleep to skip an ack
                        time.sleep(0.5)
                        skip_ack_counter += 1
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)
                else:
                    ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)

            except socket.timeout:
                print("\nTimeout occurred on the server.")
                continue


def stop_and_wait_client(drtp, file):
    print("\nStop-and-wait client started.")
    with open(file, 'rb') as f:
        seq = 0

        print("Sending data...")
        while True:
            data = f.read(1460)
            if not data:
                break

            packet = drtp.create_packet(seq, 0, 0, 0, data)
            ack_received = False
            while not ack_received:
                drtp.send_packet(packet, (drtp.ip, drtp.port))

                try:
                    drtp.socket.settimeout(0.5)
                    ack_packet, ack_addr = drtp.receive_packet()
                    seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                    if flags & 0x10:
                        ack_received = True

                except socket.timeout:
                    print(f"\nTimeout occurred. Resending packet with sequence number: {seq}")

            seq += 1

        # Send a packet with the FIN flag set after the file data has been sent
        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(seq, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def gbn_server(drtp, file, test_case):
    print("\nGBN server started.")
    with open(file, 'wb') as f:
        expected_seq_num = 0
        skip_ack_counter = 0
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                if flags & drtp.FIN:
                    print("FIN flag received.")
                    break

                if seq_num == expected_seq_num:
                    f.write(data)
                    expected_seq_num += 1

                    # Skip sending an ACK if the test_case is 'skip_ack' and skip_ack_counter is 0
                    if test_case == "skip_ack" and skip_ack_counter == 0:
                        time.sleep(0.5)
                        skip_ack_counter += 1
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)
                else:
                    ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
            except socket.timeout:
                print("\nTimeout occurred on the server.")
                continue



def gbn_client(drtp, file, window_size, skip_ack=False, skip_seq=False):
    print("\nGBN client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}

        while True:
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window[next_seq_num] = packet
                next_seq_num += 1

            if not packets_in_window:
                break

            try:
                drtp.socket.settimeout(2)
                ack_packet, ack_addr = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    for seq_num in range(base, ack_num):
                        packets_in_window.pop(seq_num)
                    base = ack_num
            except socket.timeout:
                print("\nTimeout occurred.")
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Resending packet with sequence number: {seq_num}")

        # Send a packet with the FIN flag set after the file data has been sent
        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def sr_server(drtp, file, test_case):
    print("\nSR server started.")
    with open(file, 'wb') as f:
        expected_seq_num = 0
        received_packets = {}
        skip_ack_counter = 0
        skipped_ack_num = None

        print("Receiving data...")
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                if flags & drtp.FIN:
                    print("\nFIN flag received.")
                    break

                if seq_num not in received_packets:  # Check if the packet is already in the received_packets
                    received_packets[seq_num] = data

                send_ack = False
                while expected_seq_num in received_packets:
                    f.write(received_packets[expected_seq_num])
                    received_packets.pop(expected_seq_num)
                    expected_seq_num += 1
                    send_ack = True

                if send_ack:
                    if test_case == "skip_ack" and skip_ack_counter == 0:
                        skip_ack_counter += 1
                        skipped_ack_num = expected_seq_num
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)

            except socket.timeout:
                if test_case == "skip_ack" and skipped_ack_num is not None:
                    # Send the ACK for the skipped packet after the initial timeout
                    ack_packet = drtp.create_packet(0, skipped_ack_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
                    skipped_ack_num = None
                else:
                    print("Timeout occurred on the server.")
                    continue


def sr_client(drtp, file, window_size, skip_ack=False, skip_seq=False):
    print("\nSR client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        unacknowledged_packets = set()  # Keep track of unacknowledged packets

        print("Sending data...")
        while True:
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break

                if len(data) < 1460:
                    data = data.ljust(1460, b'\0')

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window[next_seq_num] = packet
                unacknowledged_packets.add(next_seq_num)  # Add the packet to the unacknowledged set
                next_seq_num += 1

            if not packets_in_window:
                break

            try:
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    if ack_num in packets_in_window:
                        packets_in_window.pop(ack_num)
                        unacknowledged_packets.discard(ack_num)  # Remove the acknowledged packet from the set
                    if ack_num == base:
                        base += 1
            except socket.timeout:
                print("\nTimeout occurred")
                for seq_num in unacknowledged_packets:
                    drtp.send_packet(packets_in_window[seq_num], (drtp.ip, drtp.port))
                    print(f"Resending packet with sequence number: {seq_num}")

        # Send a packet with the FIN flag set after the file data has been sent
        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def main():
    args = parse_arguments()

    if args.server:
        server(args)
    elif args.client:
        client(args)
    else:
        print("Please specify either --server or --client.")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
    parser.add_argument('-s', '--server', action='store_true', help='Run as server')
    parser.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-I', '--remote_ip', default='127.0.0.1', help='Remote server IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port number')
    parser.add_argument('-b', '--bind', default='127.0.0.1', type=str, help='Local IP address')
    parser.add_argument('-f', '--file_name', type=str, help='File name to transfer')
    parser.add_argument('-r', '--reliability_func', choices=['stop-and-wait', 'gbn', 'sr'], default='stop-and-wait',
                        help='Reliability function to use (default: stop_and_wait)')
    parser.add_argument('-w', '--window_size', type=int, default=4, help='Window size for GBN and SR (default: 4)')
    parser.add_argument('-t', '--test_case', choices=['skip_ack', 'skip_seq'], default=None,
                        help='Test case to simulate packet loss (skip_ack or skip_seq)')

    return parser.parse_args()


if __name__ == '__main__':
    main()