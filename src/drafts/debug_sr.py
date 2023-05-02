import argparse
from DRTP4 import *

def server(args):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', args.port))
    server_drtp = DRTP(args.bind, args.port, server_socket)
    server_drtp.syn_server()

    if args.reliability_func == "sr":
        sr_server(server_drtp, args.file_name, args.test_case)


def client(args):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_drtp = DRTP(args.remote_ip, args.port, client_socket)
    client_drtp.syn_client()
    print("SYN sent from the client. Waiting for SYN-ACK.")

    if args.reliability_func == "sr":
        sr_client(client_drtp, args.file_name, args.window_size)  

    client_drtp.close()

def sr_server(drtp, file, test_case):
        print("SR server started.")
        with open(file, 'wb') as f:
            expected_seq_num = 0
            received_packets = {}
            skip_ack_counter = 0
            skipped_ack_num = None

            while True:
                try:
                    drtp.socket.settimeout(0.5)
                    data_packet, data_addr = drtp.receive_packet()
                    seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                    if flags & drtp.FIN:
                        print("FIN flag received.")
                        break

                    if seq_num not in received_packets:  # Check if the packet is already in the received_packets
                        received_packets[seq_num] = data
                    else:
                        print(f"Duplicate packet with seq_num: {seq_num}")

                    send_ack = False
                    while seq_num in received_packets:
                        print(f"Writing packet with seq_num: {seq_num}")
                        f.write(received_packets[seq_num])
                        received_packets.pop(seq_num)
                        expected_seq_num += 1
                        send_ack = True
                        print(expected_seq_num)
                        if seq_num == 2:
                            print(data)
                    ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)

                    # Skip sending an ACK if the test_case is 'skip_ack' and skip_ack_counter is 0
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
                        print("ACK for the skipped packet sent after the timeout")
                        
                    else:
                        print("Timeout occurred on the server.")
                        continue


def sr_client(drtp, file, window_size):
    print("SR client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        unacknowledged_packets = set()  # Keep track of unacknowledged packets

        while True:
            while next_seq_num < base + window_size:
                data = f.read(1460)
                if not data:
                    break

                if len(data) < 1460:
                    data = data.ljust(1460, b'\0')

                packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                print(f"Sent packet with seq_num: {next_seq_num}")
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
                        print(f"Acknowledged packet with seq_num: {ack_num}")
                        packets_in_window.pop(ack_num)
                        unacknowledged_packets.discard(ack_num)  # Remove the acknowledged packet from the set
                    if ack_num == base:
                        base += 1
            except socket.timeout:
                for seq_num in unacknowledged_packets:
                    drtp.send_packet(packets_in_window[seq_num], (drtp.ip, drtp.port))
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num} \n")

        # Send a packet with the FIN flag set after the file data has been sent
        print("Sending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
    parser.add_argument('-s', '--server', action='store_true', help='Run as server')
    parser.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-I', '--remote_ip', default='127.0.0.1', help='Remote server IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port number')
    parser.add_argument('-b', '--bind', default='127.0.0.1', type=str, help='Local IP address')
    parser.add_argument('-f', '--file_name', type=str, help='File name to transfer')
    parser.add_argument('-r', '--reliability_func', choices=['stop-and-wait', 'gbn', 'sr'], default='stop-and-wait',
                        help='Reliability function to use (default: stop_and_wait)')
    parser.add_argument('-w', '--window_size', default=5, type=int, help="Size of the sliding window")
    parser.add_argument('-t', '--test_case', type=str, default=None, help='Test case to run (e.g., skip_ack)')

    args = parser.parse_args()

    if args.server:
        server(args)
    elif args.client:
        client(args)
    else:
        parser.print_help()