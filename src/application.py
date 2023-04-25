import argparse
from DRTP import *

def server(local_port, file_name, reliability_func, test_case=None):
    # Create DRTP object and listen on local_port
    drtp = DRTP(local_port)

    # Wait for connection from client
    drtp.connect(remote_address, remote_port)

    # Receive file from client and write to file_name
    with open(file_name, 'wb') as f:
        while True:
            # Receive data using DRTP protocol
            data = drtp.receive()

            # If data is None, then the transfer is complete
            if not data:
                break

            # Write received data to file
            f.write(data)

    # Gracefully close the DRTP protocol and the connection
    drtp.close()

def client(remote_address, remote_port, file_name, reliability_func, test_case=None):
    # Create DRTP object and connect to remote_address:remote_port
    drtp = DRTP(0)  # local_port will be assigned by the operating system
    drtp.connect(remote_address, remote_port)

    # Send file to server
    with open(file_name, 'rb') as f:
        while True:
            # Read file in chunks of 1460 bytes (maximum data size for DRTP packet)
            data = f.read(1460)

            # If there is no more data, then the transfer is complete
            if not data:
                break

            # Send data using DRTP protocol
            drtp.send(data)

    # Gracefully close the DRTP protocol and the connection
    drtp.close()
    
# Define the DRTP header structure
def create_header(seq_num, ack_num, flags, window):
    # Your header creation code here

# Connection establishment functions
def send_syn(drtp, addr):
    # Your code for sending SYN packet

def send_ack(drtp, addr, seq_num, ack_num):
    # Your code for sending ACK packet

def send_fin(drtp, addr, seq_num):
    # Your code for sending FIN packet

# Data transfer functions
def send_data(drtp, addr, data, seq_num, window):
    # Your code for sending data packet

def receive_data(drtp, seq_num, window):
    # Your code for receiving data packet

# Reliability functions
def stop_and_wait(drtp, data):
    # Your stop-and-wait implementation
    # Send data using DRTP protocol
    while True:
        drtp.send(data)

        try:
            # Wait for ACK
            ack = drtp.receive()
            if ack:
                break
        except socket.timeout:
            # If timeout, resend the data
            continue


def gbn(drtp, data, window_size):
    packets = [data[i:i+1460] for i in range(0, len(data), 1460)]
    expected_ack = 1
    i = 0

    while i < len(packets):
        # Send packets in the window
        for j in range(i, min(i+window_size, len(packets))):
            drtp.send(packets[j])

        # Wait for ACK
        try:
            ack = drtp.receive()
        except socket.settimeout:
            # If timeout, resend packets in the window
            continue

        # Check if ACK matches expected_ack
        if ack == expected_ack:
            expected_ack += 1
            i += 1
        else:
            # Resend packets from expected_ack onwards
            i = expected_ack - 1

def sr(drtp, data,window_size):
    packets = [data[i:i+1460] for i in range(0, len(data), 1460)]
    expected_ack = 1
    i = 0
    buffer = {}

    while i < len(packets):
        # Send packets in the window
        for j in range(i, min(i+window_size, len(packets))):
            drtp.send(packets[j])

        # Wait for ACK
        try:
            ack = drtp.receive()
        except socket.timeout:
            # If timeout, resend packets in the window
            continue

        # Check if ACK matches expected_ack
        if ack in buffer:
            del buffer[ack]

        while expected_ack in buffer:
            drtp.send(buffer[expected_ack])
            del buffer[expected_ack]
            expected_ack += 1

        if ack == expected_ack:
            expected_ack += 1
            i += 1
        else:
            buffer[ack] = packets[ack-1]



    with open(file_name, 'rb') as f:
        while True:
        # Read file in chunks of 1460 bytes (maximum data size for DRTP packet)
         data = f.read(1460)

        # If there is no more data, then the transfer is complete
         if not data:
            break

        # Send data using DRTP protocol with reliability function
        reliability_func(drtp, data)



if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
    parser.add_argument('-s', '--server', action='store_true', help='Run as server')
    parser.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-a', '--remote-address', help='Remote server IP address')
    parser.add_argument('-p', '--remote-port', type=int, help='Remote server port number')
    parser.add_argument('-l', '--local-port', type=int, default=5000, help='Local port number (default: 5000)')
    parser.add_argument('-f', '--file-name', help='File name to transfer')
    parser.add_argument('-r', '--reliability-function', choices=['stop-and-wait', 'GBN', 'SR'], default='stop-and-wait', help='Reliability function to use (default: stop-and-wait)')
    parser.add_argument('-t', '--test-case', choices=['skip-ack', 'skip-sequence-number', 'loss'], help='Test case to simulate (default: None)')

    args = parser.parse_args()

    if args.reliability_function == 'stop-and-wait':
        reliability_func = stop_and_wait
    elif args.reliability_function == 'GBN':
        reliability_func = gbn
    elif args.reliability_function == 'SR':
        reliability_func = sr
    else:
        parser.error('Invalid reliability function specified')

    if args.server:
        server(args.local_port, args.file_name, reliability_func, args.test_case)
    elif args.client:
        client(args.remote_address, args.remote_port, args.file_name, reliability_func, args.test_case)
    else:
        parser.print_help()

    
