import argparse
from DRTP import *
import time
import os

def server(ip, port, file_name, reliability_func, test_case):
    # Description:
    # creates a server socket using UDP and utilizes DRTP for reliable data transfer
    # establishes a connection with the client before selecting and running a specified reliability function
    # Arguments:
    # ip: holds the ip address for the server
    # port: port number of the server
    # file_name: holds the filename for the received file
    # reliablility_func: reliability function to use for sending data
    # test_case: test case to test the reliability functions
    # Returns:
    # No returns, only prints message that the server is listening
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
    # Description:
    # creates a client socket using UDP and utilizes DRTP for reliable data transfer
    # establishes a connection with the server before selecting and running a specified reliability function
    # calculates and prints the throughput for the file transfer
    # Arguments: 
    # ip: holds the ip address for the server
    # port: port number of the server
    # file_name: holds the filename for the received file
    # reliablility_func: reliability function to use for sending data 
    # window_size: specifies a size for the sliding window in the gbn and sr functions
    # test_case: test case to test the reliability functions
    # Returns: 
    # No returns, only prints the throughput of the file transfer
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
    # Description:
    # Implements a stop-and-wait server for receiving a file over a reliable transport protocol
    # Arguments:
    # drtp: an instance of the reliable transport protocol
    # file: the file path to save the received data
    # test_case: a test case to simulate (e.g., 'skip_ack' to skip an acknowledgment)

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

                    # Implements the 'skip_ack' test case by skipping an acknowledgment
                    if test_case == 'skip_ack' and skip_ack_counter == 0:
                        # Adding a sleep to skip an ack
                        time.sleep(0.5)
                        skip_ack_counter += 1
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)
                else:
                    # Sends an ACK for the last correctly received packet if the received sequence number does not match the expected one
                    ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)

            except socket.timeout:
                # Handles a timeout and continues to receive packets
                print("\nTimeout occurred on the server. Did not receive packet: {expected_seq}")
                continue


def stop_and_wait_client(drtp, file):
    # Description:
    # Implements a stop-and-wait client for sending a file over a reliable transport protocol
    # Arguments:
    # drtp: an instance of the reliable transport protocol
    # file: the file path to the file to be sent

    print("\nStop-and-wait client started.")
    with open(file, 'rb') as f:
        seq = 0
        rtt_sum = 0
        packet_count = 0

        print("Sending data...")
        while True:
            # Reads a chunk of data from the file to send
            data = f.read(1460)
            if not data:
                break

            # Creates a packet with the current sequence number and data
            packet = drtp.create_packet(seq, 0, 0, 0, data)
            ack_received = False
            while not ack_received:

                # Sends the packet and waits for an acknowledgment (ACK)
                drtp.send_packet(packet, (drtp.ip, drtp.port))

                try:
                    send_time = time.time()
                    drtp.socket.settimeout(0.5) #Initial timeout value
                    ack_packet, ack_addr = drtp.receive_packet()
                    recv_time = time.time()
                    seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                    
                    #Checks if the received packet is an ACK
                    if flags & 0x10:
                        ack_received = True
                        rtt = recv_time - send_time
                        rtt_sum += rtt
                        print(rtt)
                        packet_count += 1

						# Calculate the average RTT and set the timeout to 4RTTs
                        avg_rtt = rtt_sum / packet_count if packet_count > 0 else 0.5
                        timeout = 4 * avg_rtt
                        drtp.socket.settimeout(timeout)

                except socket.timeout:
                    # Handles a timeout and resends the packet
                    print(f"\nTimeout occurred. Resending packet with sequence number: {seq}")

            seq += 1

        # Sends a packet with the FIN flag set after the file data has been sent
        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(seq, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def gbn_server(drtp, file, test_case):
    # Description:
    # Implements a Go-Back-N server for receiving a file over a reliable transport protocol
    # Arguments:
    # drtp: an instance of the reliable transport protocol
    # file: the file path where the received file will be saved
    # test_case: a test case to execute, such as 'skip_ack' to simulate a skipped acknowledgment

    print("\nGo-Back-N server started.")
    with open(file, 'wb') as f:
        expected_seq_num = 0
        skip_ack_counter = 0
        while True:
            try:
                # Sets a timeout for receiving packets and attempts to receive a data packet
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                # Checks if the received packet has the FIN flag set, indicating the end of transmission
                if flags & drtp.FIN:
                    print("FIN flag received.")
                    break

                # Processes the received packet if it has the expected sequence number
                if seq_num == expected_seq_num:
                    f.write(data)
                    expected_seq_num += 1

                    # Skips sending an ACK if the test_case is 'skip_ack' and skip_ack_counter is 0
                    if test_case == "skip_ack" and skip_ack_counter == 0:
                        time.sleep(0.5)
                        skip_ack_counter += 1
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)

                else:
                    # Sends an ACK for the last correctly received packet if the received packet is out of order
                    ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
            except socket.timeout:

                # Handles a timeout, indicating that no packet was received during the specified time
                print("\nTimeout occurred on the server.")
                continue


def gbn_client(drtp, file, window_size, test_case):
    # Description:
    # Implements a Go-Back-N client for sending a file over a reliable transport protocol
    # Arguments:
    # drtp: an instance of the reliable transport protocol
    # file: the file path of the file to be sent
    # window_size: the window size for the Go-Back-N protocol
    # test_case: a test case to execute, such as 'skip_seq' to simulate a skipped packet

    print("\nGo-Back-N client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        rtt_sum = 0
        packet_count = 0
        skipped_packet = None

        while True:
            # Sends packets within the window size
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break

                # Skips sending a packet if the test_case is 'skip_seq' and next_seq_num is 0
                if test_case == "skip_seq" and next_seq_num == 4:
                    print(f"Skipping packet with sequence number: {next_seq_num}")
                    skiped_seq_num = next_seq_num
                    skipped_packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                    next_seq_num += 1
                    continue

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window[next_seq_num] = packet
                next_seq_num += 1

                # Sends a skipped packet after the next packet has been sent
                if skipped_packet is not None:
                    print(f"Sending out-of-order packet: {skiped_seq_num}")
                    drtp.send_packet(skipped_packet, (drtp.ip, drtp.port))
                    skipped_packet = None

            # Exits the loop if all packets have been sent
            if not packets_in_window:
                break

            # Receives ACK packets and updates the base pointer accordingly
            try:
                send_time = time.time()
                
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                recv_time = time.time()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    for seq_num in range(base, ack_num):
                        if seq_num in packets_in_window:  # Check if seq_num exists in the dictionary
                            packets_in_window.pop(seq_num)
                    base = ack_num
                rtt = recv_time - send_time
                rtt_sum += rtt
                packet_count += 1
                
                # Calculate the average RTT and set the timeout to 4RTTs
                avg_rtt = rtt_sum / packet_count if packet_count > 0 else 0.5
                timeout = 4 * avg_rtt
                drtp.socket.settimeout(timeout)
                
            except socket.timeout:

                # Resends all packets in the current window upon a timeout
                print("\nTimeout occurred.")
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Resending packet with sequence number: {seq_num}")

        # Sends a packet with the FIN flag set after the file data has been sent
        print("\nSending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def sr_server(drtp, file, test_case):
    # Description:
    # Implements a Selective Repeat server for receiving a file over a reliable transport protocol
    # Arguments:
    # drtp: an instance of the reliable transport protocol
    # file: the file path of the file to be received
    # test_case: a test case to execute, such as 'skip_ack' to simulate a skipped ACK packet

    print("\nSelective Repeat server started.")
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

                # Writes data to the file if the received sequence number matches the expected sequence number
                if seq_num == expected_seq:
                    f.write(data)
                    expected_seq += 1

                    # Skips sending an ACK if the test_case is 'skip_ack' and skip_ack_counter is 0
                    if test_case == 'skip_ack' and skip_ack_counter == 0:
                        # Adding a sleep to skip an ack
                        time.sleep(0.5)
                        skip_ack_counter += 1
                        print(f"Skip ACK triggered at sequence number {seq_num}")
                    else:
                        ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                        drtp.send_packet(ack_packet, data_addr)

                else:
                    # Re-sends ACK packet for the previous packet if the received sequence number does not match
                    ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)

            except socket.timeout:
                print("\nTimeout occurred on the server.")
                continue


def sr_client(drtp, file, window_size, test_case):
    # Description:
    # Implements a Selective Repeat client for sending a file over a reliable transport protocol
    # Arguments:
    # drtp: an instance of the reliable transport protocol
    # file: the file path of the file to be sent
    # window_size: the size of the sliding window
    # test_case: a test case to execute, such as 'skip_seq' to simulate skipping a packet sequence number

    print("\nSelective Repeat client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        received = {}
        rtt_sum = 0
        packet_count = 0

        skipped_packet = None
        skip_seq = 0

        while True:
            # Sends packets within the window size and handles skipping packets for the test case
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                if test_case == "skip_seq" and next_seq_num == skip_seq:
                    print(f"Skipping packet with sequence number: {next_seq_num}")
                    skipped_packet = packet
                else:
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    packets_in_window[next_seq_num] = packet
                next_seq_num += 1

            if not packets_in_window:
                break

            # Receives ACK packets and updates the base sequence number and window accordingly
            try:
                send_time = time.time()
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                recv_time = time.time()
                seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    if ack_num > base:
                        for seq_num in range(base, ack_num):
                            packets_in_window.pop(seq_num, None)
                            received[seq_num] = True
                        base = ack_num
                rtt = recv_time - send_time
                rtt_sum += rtt
                packet_count += 1
                
                # Calculate the average RTT and set the timeout to 4RTTs
                avg_rtt = rtt_sum / packet_count if packet_count > 0 else 0.5
                timeout = 4 * avg_rtt
                drtp.socket.settimeout(timeout)
				
            except socket.timeout:
                # Handles timeouts and resends packets that have not been acknowledged

                if test_case == "skip_seq" and skipped_packet and base == skip_seq:
                    drtp.send_packet(skipped_packet, (drtp.ip, drtp.port))
                    print(f"Resending the previously skipped packet with seq: {skip_seq}")
                    packets_in_window[skip_seq] = skipped_packet
                    skipped_packet = None

                print("\nTimeout occurred.")
                for seq_num in sorted(packets_in_window.keys()):
                    packet = packets_in_window[seq_num]
                    if seq_num not in received:
                        drtp.send_packet(packet, (drtp.ip, drtp.port))
                        print(f"Resending packet with sequence number: {seq_num}")

        # Sends a packet with the FIN flag set after the file data has been sent
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
