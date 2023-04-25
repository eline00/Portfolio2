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
    
def stop_and_wait():
    return

def GBN():
    return

def SR():
    return

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

    if args.server:
        server(args.local_port, args.file_name, args.reliability_function, args.test_case)
    elif args.client:
        client(args.remote_address, args.remote_port, args.file_name, args.reliability_function, args.test_case)
    else:
        parser.print_help()