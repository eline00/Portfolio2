import argparse
from DRTP import *
import time
import os

def server(args):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', args.port))
    server_drtp = DRTP(args.bind, args.port, server_socket)
    
    print("-----------------------------------------------")
    print("A server is listening on port", args.port)             #Communicates that the server is ready to recieve transmition
    print("-----------------------------------------------")
    
    server_drtp.syn_server()

    if args.reliability_func == "stop-and-wait":
        stop_and_wait_server(server_drtp, args.file_name)
    elif args.reliability_func == "gbn":
        gbn_server(server_drtp, args.file_name)
    elif args.reliability_func == "sr":
        sr_server(server_drtp, args.file_name)
    
def client(args):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_drtp = DRTP(args.remote_ip, args.port, client_socket)
    print("Sending SYN from the client. Waiting for SYN-ACK.")
    client_drtp.syn_client()
    

    start_time = time.time()
    if args.reliability_func == "stop-and-wait":
        stop_and_wait_client(client_drtp, args.file_name)  # Fix this line
    elif args.reliability_func == "gbn":
        gbn_client(client_drtp, args.file_name, args.window_size)  # Fix this line
    elif args.reliability_func == "sr":
        sr_client(client_drtp, args.file_name, args.window_size)  # Fix this line

    end_time = time.time()
    elapsed_time = end_time - start_time

    file_size = os.path.getsize(args.file_name) * 8  # Convert to bits
    throughput = file_size / (elapsed_time * 1000000)  # bits per second
    print(f"\nElapsed Time: {elapsed_time:.2f} s")
    print(f"Transfered data: {(file_size / 1000000):.2f} Mb")
    print(f"Throughput: {throughput:.2f} Mbps")

    client_drtp.close()

def stop_and_wait_server(drtp, file):
    print("Server started.")
    with open(file, 'wb') as f:
        print("Receiving data")
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)
                
                if flags & drtp.FIN:
                    print("FIN flag received.")
                    received_fin = True
                    # Send an ACK packet for the received FIN packet
                    print("Sending FIN-ACK")
                    ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
                    break
                else:
                    
                    # Send an ACK packet for the received packet
                    ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')
                    drtp.send_packet(ack_packet, data_addr)
                    
                    f.write(data)
                        
            except socket.timeout:
                    print("Timeout occurred on the server.")
                    continue


def stop_and_wait_client(drtp, file):
    print("Stop-and-wait client started.")
    with open(file, 'rb') as f:
        seq = 0
        print("Sending data")
        while True:
            data = f.read(1460)
            if not data:
                break
            
            packet = drtp.create_packet(seq, 0, 0, 0, data)
            ack_received = False
            while not ack_received:
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                
                try:
                    drtp.socket.settimeout(2)
                    ack_packet, ack_addr = drtp.receive_packet()
                    seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                    
                    if flags & 0x10:
                        ack_received = True
                      
                except socket.timeout:
                    print("Timeout occurred. Resending packet with sequence number:", seq_num)
                    
            seq += 1
        
        # Send a packet with the FIN flag set after the file data has been sent
        print("Sending FIN packet.")
        fin_packet = drtp.create_packet(seq, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def gbn_server(drtp, file):
    print("GBN server started.")
    with open(file, 'wb') as f:
        expected_seq_num = 0
        print("Receiving data")
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

                ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                drtp.send_packet(ack_packet, data_addr)
            except socket.timeout:
                print("Timeout occurred on the server.")
                continue

def gbn_client(drtp, file, window_size):
    print("GBN client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        print("Sending data")
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
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    for seq_num in range(base, ack_num):
                        packets_in_window.pop(seq_num)
                    base = ack_num
            except socket.timeout:
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num}")

        # Send a packet with the FIN flag set after the file data has been sent
        print("Sending FIN packet.")
        fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))



def sr_server(drtp, file):
    print("SR server started.")
    with open(file, 'wb') as f:
        print("Receiving data")
        expected_seq_num = 0
        received_packets = {}
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

                if flags & drtp.FIN:
                    print("FIN flag received.")
                    break

                received_packets[seq_num] = data
                
                while expected_seq_num in received_packets:
                    f.write(received_packets[expected_seq_num])
                    received_packets.pop(expected_seq_num)
                    expected_seq_num += 1
                
                ack_packet = drtp.create_packet(0, expected_seq_num, 0x10, 0, b'')
                drtp.send_packet(ack_packet, data_addr)
            except socket.timeout:
                print("Timeout occurred on the server.")
                continue

def sr_client(drtp, file, window_size):
    print("SR client started.")
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        print("Sending data")
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
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)

                if flags & 0x10:
                    for seq_num in range(base, ack_num):
                        packets_in_window.pop(seq_num)
                    base = ack_num
            except socket.timeout:
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num}")

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

    args = parser.parse_args()

    if args.server:
        server(args)
    elif args.client:
        client(args)
    else:
        parser.print_help()
