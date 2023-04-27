import argparse
from DRTP import DRTP


def server(local_ip, local_port, file_name, reliability_func):
    print('-' * 60)
    print(f'Server is listening on port {local_port}')
    print(f'Using reliability function: {args.reliability_function}')
    print('-' * 60 + '\n')
    
    drtp = DRTP(local_ip, local_port, reliability_func)
    drtp.establish_connection()

    
    # Receiving a file from the client
    print(f'A client is connected with {local_ip}:{local_port}\n')
    success = drtp.receive_data(file_name)
    if success:
        print("The transfer was successful!")
    else:
        print("The transfer failed.")

    # Closing connection
    drtp.close_connection()


def client(remote_ip, remote_port, file_name, reliability_func):
    print('\n' + '-' * 70)
    print(f"A client connecting to server {remote_ip}, port {remote_port}")
    print(f'Using reliability function: {args.reliability_function}')
    print('-' * 70)
    
    # Creating DRTP instance
    drtp = DRTP(remote_ip, remote_port, reliability_func)
    drtp.establish_connection()

    while True:
        print(f"Client connected with {remote_ip}, port {remote_port}\n")

    success = drtp.send_file(file_name)
    if success:
        print("The transfer was successful!")
    else:
        print("The transfer failed.")

    drtp.close_connection()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
    parser.add_argument('-s', '--server', action='store_true', help='Run as server')
    parser.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-I', '--remote-ip', default='127.0.0.1', help='Remote server IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port number')
    parser.add_argument('-b', '--bind', default='127.0.0.1', type=str, help='Local IP address')
    parser.add_argument('-f', '--file-name', type=str, help='File name to transfer')
    parser.add_argument('-r', '--reliability-function', choices=['stop_and_wait', 'gbn', 'sr'], default='stop_and_wait',
                        help='Reliability function to use (default: stop_and_wait)')

    args = parser.parse_args()

    if args.reliability_function == 'stop_and_wait':
        reliability_func = DRTP.stop_and_wait
    elif args.reliability_function == 'gbn':
        reliability_func = DRTP.gbn
    elif args.reliability_function == 'sr':
        reliability_func = DRTP.sr
    else:
        parser.error('Invalid reliability function specified')

    if args.server:
        server(args.bind, args.port, args.file_name, reliability_func)
    elif args.client:
        client(args.remote_ip, args.port, args.file_name, reliability_func)
    else:
        parser.print_help()
