import argparse
from draft3DRTP import *

def server(args):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', args.port))
    server_drtp = DRTP(args.bind, args.port, server_socket)
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
    client_drtp.syn_client()
    print("SYN sent from the client. Waiting for SYN-ACK.")
    
    if args.reliability_func == "stop-and-wait":
        stop_and_wait_client(client_drtp, args.file_name)  # Fix this line
    elif args.reliability_func == "gbn":
        gbn_client(client_drtp, args.file_name)  # Fix this line
    elif args.reliability_func == "sr":
        sr_client(client_drtp, args.file_name)  # Fix this line

    client_drtp.close()

def stop_and_wait_server(drtp, file):
    print("Server started.")
    with open(file, 'wb') as f:
        received_fin = False
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
                    print("Received data")
                    
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
        while True:
            data = f.read(1460)
            if not data:
                break
            
            print("Sending data")
            
            packet = drtp.create_packet(seq, 0, 0, 0, data)
            ack_received = False
            while not ack_received:
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                print("Data packet sent to the server")
                
                try:
                    drtp.socket.settimeout(2)
                    ack_packet, ack_addr = drtp.receive_packet()
                    seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                    
                    if flags & 0x10:
                        ack_received = True
                        print("ACK received")
                        
                        
                except socket.timeout:
                    print("Timeout occurred. Resending packet with sequence number:", seq_num)
                    
            seq += 1
        
        # Send a packet with the FIN flag set after the file data has been sent
        print("Sending FIN packet.")
        fin_packet = drtp.create_packet(seq, 0, drtp.FIN, 0, b'')
        drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


def gbn_server(drtp, file):
    with open(file, 'wb') as f:
        base = 0
        seq_num = 0  # Initialize seq_num before the while loop
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                _, _, _, _, data = drtp.parse_packet(data_packet)

                seq_num, _, flags, window = unpack("!IIHH", data_packet[:12])

                
                if flags & 0x01:  # Check if the FIN flag is set
                    break
                
                # Send an ACK packet for the received packet
                ack_packet = drtp.create_packet(seq_num, 0, 0x10, 0, b'')
                drtp.send_packet(ack_packet, data_addr)
                
                if seq_num == base:
                    f.write(data)
                    base += 1
            except socket.timeout:
                # If timeout occurs, resend all unacknowledged packets in the window
                for i in range(base, seq_num):
                    packet = drtp.create_packet(i, 0, 0, 0, b'')
                    drtp.send_packet(packet, data_addr)
            except Exception:
                # Catch other exceptions separately
                pass
                

def gbn_client(drtp, file):
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = []
        
        while True:
            # Send new packets until the sliding window is full or there's no more data to send
            while next_seq_num < base + args.window_size and not packets_in_window and len(packets_in_window) < args.window_size:
                data = f.read(1460)
                if not data:
                    break
                
                packet = drtp.create_packet(next_seq_num, 0, 0, args.window_size, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window.append((next_seq_num, packet))
                next_seq_num += 1
            
            if not packets_in_window and not data:
                break
            
            try:
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                
                if flags & 0x10:  # Check if received packet is an ACK
                    while packets_in_window and ack_num >= packets_in_window[0][0]:
                        base += 1
                        packets_in_window.pop(0)
            except socket.timeout:
                # If timeout occurs, resend all unacknowledged packets in the window
                for seq_num, packet in packets_in_window:
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num}")


def sr_server(drtp, file):
    with open(file, 'wb') as f:
        base = 0
        packets_in_window = {}
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet, data_addr = drtp.receive_packet()
                _, _, _, _, data = drtp.parse_packet(data_packet)
                seq_num, _, flags, window = unpack("!IIHH", data_packet[:12])

                
                if flags & 0x01:  # Check if the FIN flag is set
                    break
                
                # Send an ACK packet for the received packet
                ack_packet = drtp.create_packet(seq_num, 0, 0x10, 0, b'')
                drtp.send_packet(ack_packet, data_addr)
                
                packets_in_window[seq_num] = data
                while base in packets_in_window:
                    f.write(packets_in_window[base])
                    packets_in_window.pop(base)
                    base += 1

            except Exception:
                # If timeout occurs, resend all unacknowledged packets in the window
                for i in range(base, seq_num):
                    packet = drtp.create_packet(i, 0, 0, 0, b'')
                    drtp.send_packet(packet, data_addr)


def sr_client(drtp, file):
    with open(file, 'rb') as f:
        base = 0
        next_seq_num = 0
        packets_in_window = {}
        
        while True:
            # Send new packets until the sliding window is full or there's no more data to send
            while next_seq_num < base + args.window_size and not packets_in_window and len(packets_in_window) < args.window_size:
                data = f.read(1460)
                if not data:
                    break
                
                packet = drtp.create_packet(next_seq_num, 0, 0, args.window_size, data)
                drtp.send_packet(packet, (drtp.ip, drtp.port))
                packets_in_window[next_seq_num] = packet
                next_seq_num += 1
            
            if not packets_in_window and not data:
                break
            
            try:
                drtp.socket.settimeout(0.5)
                ack_packet, ack_addr = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                
                if flags & 0x10:  # Check if received packet is an ACK
                    if ack_num in packets_in_window:
                        packets_in_window.pop(ack_num)
                        base = min(packets_in_window.keys()) if packets_in_window else next_seq_num
            except socket.timeout:
                # If timeout occurs, resend only unacknowledged packets in the window
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet, (drtp.ip, drtp.port))
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num}")


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
