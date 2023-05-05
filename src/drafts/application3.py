import argparse
from DRTP4 import *
import time
import os


def calculate_timeout(send_time, recv_time, multiplier=4):
    rtt = recv_time - send_time
    print(f"RTT: {rtt:.50f} seconds")  # Print the RTT value
    return rtt * multiplier


def server(ip, port, file_name, reliability_func, test_case):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', port))
    server_drtp = DRTP(ip, port, server_socket)

    print("-----------------------------------------------")
    print("A server is listening on port", port)
    print("-----------------------------------------------")

    server_drtp.syn_server()

    if reliability_func == "stop-and-wait":
        stop_and_wait_server(server_drtp, file_name, test_case)
    elif reliability_func == "gbn":
        gbn_server(server_drtp, file_name, test_case)
    elif reliability_func == "sr":
        sr_server(server_drtp, file_name, test_case)


def client(ip, port, file_name, reliability_func, window_size, test_case):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_drtp = DRTP(ip, port, client_socket)
    print("\nSending SYN from the client. Waiting for SYN-ACK.")
    client_drtp.syn_client()

    start_time = time.time()
    if reliability_func == "stop-and-wait":
        stop_and_wait_client(client_drtp, file_name)
    elif reliability_func == "gbn":
        gbn_client(client_drtp, file_name, window_size, test_case)
    elif reliability_func == "sr":
        sr_client(client_drtp, file_name, window_size, test_case)

    end_time = time.time()
    elapsed_time = end_time - start_time

    file_size = (os.path.getsize(file_name) * 8) / 1000000  # Convert to bits
    throughput = file_size / elapsed_time  # Mb per second
    print(f"\nElapsed Time: {elapsed_time:.2f} s")
    print(f"Transfered data: {(file_size):.2f} Mb")
    print(f"Throughput: {throughput:.2f} Mbps")

    client_drtp.close()


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

                # Checks if the FIN flag is set, indicating the end of the file transfer
                # Use of other input and output parameters in the function:
                # flags: holds the flags of the received packet
                if flags & drtp.FIN:
                    print("\nFIN flag received. Sending FIN-ACK")
                    # Send an ACK packet for the received FIN packet
                    ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
                    break

                # Checks if the received packet's sequence number matches the expected sequence number
                if seq_num == expected_seq:
                    f.write(data)
                    expected_seq += 1

                    if test_case == 'skip_ack' and skip_ack_counter == 0:
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
                    send_time = time.time()
                    drtp.socket.settimeout(0.5)  # Initial timeout value
                    ack_packet, ack_addr = drtp.receive_packet()
                    recv_time = time.time()
                    seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                    # Checks if the received packet is an ACK
                    if flags & 0x10:
                        ack_received = True
                        timeout = calculate_timeout(send_time, recv_time)  # Calculate the new timeout value
                        drtp.socket.settimeout(timeout)  # Update the socket's timeout value

                except socket.timeout:
                    print(f"\nTimeout occurred. Resending packet with sequence number: {seq}")

            seq += 1

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


def gbn_client(drtp, file, window_size, test_case):
    print("\nGBN client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        skipped_packet = None
        while True:
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break
                if test_case == "skip_seq" and next_seq_num == 0:
                    print(f"Skipping packet with sequence number: {next_seq_num}")
                    skipped_packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                    next_seq_num += 1
                    continue

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window[next_seq_num] = packet
                next_seq_num += 1

                if skipped_packet is not None:
                    print(f"Sending out-of-order packet: {skipped_packet[1]}")
                    drtp.send_packet(skipped_packet, (drtp.ip, drtp.port))
                    skipped_packet = None

            if not packets_in_window:
                break

            try:
                send_time = time.time()
                drtp.socket.settimeout(0.5)  # Initial timeout value
                ack_packet, ack_addr = drtp.receive_packet()
                recv_time = time.time()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    timeout = calculate_timeout(send_time, recv_time)  # Calculate the new timeout value
                    drtp.socket.settimeout(timeout)  # Update the socket's timeout value
                    for seq_num in range(base, ack_num):
                        if seq_num in packets_in_window:  # Check if seq_num exists in the dictionary
                            packets_in_window.pop(seq_num)
                    base = ack_num

            except socket.timeout:
                print("\nTimeout occurred.")
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Resending packet with sequence number: {seq_num}")

        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def sr_server(drtp, file, test_case):
    print("\nSR server started.")
    with open(file, 'wb') as f:
        expected_seq = 0
        skip_ack_counter = 0

        print("Receiving data...")
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                # Checks for FIN flag and sends FIN-ACK in response
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
                        print(f"Skip ACK triggered at sequence number {seq_num}")
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)

                else:
                    ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)

            except socket.timeout:
                print("\nTimeout occurred on the server.")
                continue


def sr_client(drtp, file, window_size, test_case):
    print("\nSelective Repeat client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        received = {}

        skipped_packet = None

        while True:
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break

                if test_case == "skip_seq" and next_seq_num == 0:
                    print(f"Skipping packet with sequence number: {next_seq_num}")
                    skipped_packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                    next_seq_num += 1
                    continue

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window[next_seq_num] = packet
                next_seq_num += 1

                if skipped_packet is not None:
                    print(f"Sending out-of-order packet: {skipped_packet[1]}")
                    drtp.send_packet(skipped_packet, (drtp.ip, drtp.port))
                    skipped_packet = None

            if not packets_in_window:
                break
            try:
                send_time = time.time()
                drtp.socket.settimeout(0.5)  # Initial timeout value
                ack_packet, ack_addr = drtp.receive_packet()
                recv_time = time.time()
                seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    timeout = calculate_timeout(send_time, recv_time)  # Calculate the new timeout value
                    drtp.socket.settimeout(timeout)  # Update the socket's timeout value
                    if ack_num > base:
                        for seq_num in range(base, ack_num):
                            packets_in_window.pop(seq_num, None)
                            received[seq_num] = True
                        base = ack_num

            except socket.timeout:
                print("\nTimeout occurred.")
                for seq_num, packet in packets_in_window.items():
                    if seq_num not in received:
                        drtp.send_packet(packet, (drtp.ip, drtp.port))
                        print(f"Resending packet with sequence number: {seq_num}")

        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
    parser.add_argument('-s', '--server', action='store_true', help='Run as server')
    parser.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-I', '--remote_ip', default='127.0.0.1', help='Remote server IP address')
    parser.add_argument('-i', '--ip', default='127.0.0.1', help='Remote server IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port number')
    parser.add_argument('-b', '--bind', default='127.0.0.1', type=str, help='Local IP address')
    parser.add_argument('-f', '--file_name', type=str, help='File name to transfer')
    parser.add_argument('-r', '--reliability_func', choices=['stop-and-wait', 'gbn', 'sr'], default='stop-and-wait',
                        help='Reliability function to use (default: stop_and_wait)')
    parser.add_argument('-w', '--window_size', default=5, type=int, help="Size of the sliding window")
    parser.add_argument('-t', '--test_case', type=str, default=None, help='Test case to run (e.g., skip_ack)')

    args = parser.parse_args()

    if args.server:
        server(args.ip, args.port, args.file_name, args.reliability_func, args.test_case)
    elif args.client:
        client(args.ip, args.port, args.file_name, args.reliability_func, args.window_size, args.test_case)
    else:
        parser.print_help()
        
