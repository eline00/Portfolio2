import argparse
from draft3DRTP import *

def server(args):
    drtp = DRTP(args.bind, args.port)
    drtp.socket.bind((args.bind, args.port))
    drtp.syn_server()

    if args.reliability_func == "stop-and-wait":
        stop_and_wait_server(drtp, args.file_name)
    elif args.reliability_func == "gbn":
        gbn_server(drtp, args.file_name)
    elif args.reliability_func == "sr":
        sr_server(drtp, args.file_name)

    drtp.fin()
    drtp.close()
    
def client(args):
    drtp = DRTP(args.remote_ip, args.port)
    drtp.syn_client()

    if args.reliability_func == "stop-and-wait":
        stop_and_wait_client(drtp, args.file_name)
    elif args.reliability_func == "gbn":
        gbn_client(drtp, args.file_name)
    elif args.reliability_func == "sr":
        sr_client(drtp, args.file_name)

    # Send a FIN packet to signal the end of the file
    fin_packet = drtp.create_packet(0, 0, 0x01, 0, b'')
    drtp.send_packet(fin_packet)

    # Wait for the server to acknowledge the FIN packet before closing the connection
    while True:
        try:
            drtp.socket.settimeout(0.5)
            ack_packet = drtp.receive_packet()
            _, _, flags, _, _ = drtp.parse_packet(ack_packet)
            
            # Check if received packet is an ACK for the FIN packet
            if flags & 0x10:
                break
        except socket.timeout:
            continue

    drtp.fin()
    drtp.close()


def stop_and_wait_server(drtp, file):
    with open(file, 'wb') as f:
        seq_num = 0
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet = drtp.receive_packet()
                _, _, flags, _, data = drtp.parse_packet(data_packet)
                
                if flags & 0x01:  # Check if the FIN flag is set
                    break
                
                # Send an ACK packet for the received packet
                ack_packet = drtp.create_packet(seq_num, 0, 0x10, 0, b'')
                drtp.send_packet(ack_packet)
                
                f.write(data)
                seq_num += 1
            except socket.timeout:
                continue

def stop_and_wait_client(drtp, file):
    with open(file, 'rb') as f:
        seq_num = 0
        while True:
            data = f.read(1460)
            if not data:
                break
            
            # Send a packet and wait for an ACK before sending the next packet
            packet = drtp.create_packet(seq_num, 0, 0, 0, data)
            ack_received = False
            while not ack_received:
                drtp.send_packet(packet)
                
                try:
                    drtp.socket.settimeout(0.5)
                    ack_packet = drtp.receive_packet()
                    _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                    
                    # Check if received packet is an ACK for the sent packet
                    if flags & 0x10 and ack_num == seq_num:
                        ack_received = True
                        
                except socket.timeout:
                    # If timeout occurs, the code will go back to the beginning of the loop and resend the packet 
                    print("Timeout occurred. Resending packet with sequence number:", seq_num)
                    
            seq_num += 1

"""
def gbn_server(drtp, file):
    with open(file, 'wb') as f:
        base = 0
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet = drtp.receive_packet()
                header, data = drtp.parse_packet(bytes(data_packet))

                seq_num, _, flags, _, window = unpack("!IIHH", header)

                
                if flags & 0x01:  # Check if the FIN flag is set
                    break
                
                # Send an ACK packet for the received packet
                ack_packet = drtp.create_packet(seq_num, 0, 0x10, 0, b'')
                drtp.send_packet(ack_packet)
                
                if seq_num == base:
                    f.write(data)
                    base += 1
            except Exception:
                # If timeout occurs, resend all unacknowledged packets in the window
                for i in range(base, seq_num):
                    packet = drtp.create_packet(i, 0, 0, 0, b'')
                    drtp.send_packet(packet)
            
"""

def gbn_server(drtp, file):
    with open(file, 'wb') as f:
        base = 0
        seq_num = 0  # Initialize seq_num before the while loop
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet = drtp.receive_packet()
                header, data = drtp.parse_packet(bytes(data_packet))

                seq_num, _, flags, _, window = unpack("!IIHH", header)

                
                if flags & 0x01:  # Check if the FIN flag is set
                    break
                
                # Send an ACK packet for the received packet
                ack_packet = drtp.create_packet(seq_num, 0, 0x10, 0, b'')
                drtp.send_packet(ack_packet)
                
                if seq_num == base:
                    f.write(data)
                    base += 1
            except socket.timeout:
                # If timeout occurs, resend all unacknowledged packets in the window
                for i in range(base, seq_num):
                    packet = drtp.create_packet(i, 0, 0, 0, b'')
                    drtp.send_packet(packet)

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
                drtp.send_packet(packet)
                packets_in_window.append((next_seq_num, packet))
                next_seq_num += 1
            
            if not packets_in_window and not data:
                break
            
            try:
                drtp.socket.settimeout(0.5)
                ack_packet = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                
                if flags & 0x10:  # Check if received packet is an ACK
                    while packets_in_window and ack_num >= packets_in_window[0][0]:
                        base += 1
                        packets_in_window.pop(0)
            except socket.timeout:
                # If timeout occurs, resend all unacknowledged packets in the window
                for seq_num, packet in packets_in_window:
                    drtp.send_packet(packet)
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num}")


def sr_server(drtp, file):
    with open(file, 'wb') as f:
        base = 0
        packets_in_window = {}
        while True:
            try:
                drtp.socket.settimeout(0.5)
                data_packet = drtp.receive_packet()
                header, data = drtp.parse_packet(data_packet)
                seq_num, _, flags, _, window = unpack("!IIHH", header)

                
                if flags & 0x01:  # Check if the FIN flag is set
                    break
                
                # Send an ACK packet for the received packet
                ack_packet = drtp.create_packet(seq_num, 0, 0x10, 0, b'')
                drtp.send_packet(ack_packet)
                
                packets_in_window[seq_num] = data
                while base in packets_in_window:
                    f.write(packets_in_window[base])
                    packets_in_window.pop(base)
                    base += 1

            except Exception:
    # If timeout occurs, resend all unacknowledged packets in the window
                for i in range(base, seq_num):
                    packet = drtp.create_packet(i, 0, 0, 0, b'')
                    drtp.send_packet(packet)


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
                drtp.send_packet(packet)
                packets_in_window[next_seq_num] = packet
                next_seq_num += 1
            
            if not packets_in_window and not data:
                break
            
            try:
                drtp.socket.settimeout(0.5)
                ack_packet = drtp.receive_packet()
                _, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)
                
                if flags & 0x10:  # Check if received packet is an ACK
                    if ack_num in packets_in_window:
                        packets_in_window.pop(ack_num)
                        base = min(packets_in_window.keys()) if packets_in_window else next_seq_num
            except socket.timeout:
                # If timeout occurs, resend only unacknowledged packets in the window
                for seq_num, packet in packets_in_window.items():
                    drtp.send_packet(packet)
                    print(f"Timeout occurred. Resending packet with sequence number: {seq_num}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
    parser.add_argument('-s', '--server', action='store_true', help='Run as server')
    parser.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-I', '--remote_ip', default='127.0.0.1', help='Remote server IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port number')
    parser.add_argument('-b', '--bind', default='127.0.0.1', type=str, help='Local IP address')
    parser.add_argument('-f', '--file_name', type=str, help='File name to transfer')
    parser.add_argument('-r', '--reliability_func', choices=['stop-and-wait', 'gbn', 'sr'], default='stop_and_wait',
                        help='Reliability function to use (default: stop_and_wait)')

    args = parser.parse_args()

    if args.server:
        server(args)
    elif args.client:
        client(args)
    else:
        parser.print_help()
