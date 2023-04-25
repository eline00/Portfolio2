import argparse
from draftDRTP import *


def server(local_ip, local_port, file_name, reliability_func):
	# Creating DRTP instance
	drtp = DRTP(local_ip, local_port, reliability_func)
	
	print('-' * 60)
	print(f'Server is listening on port {local_port}')
	print('-' * 60 + '\n')

	while True:
		# Connecting to client
		drtp.establish_receiver_connection()

		print(f'\nA client is connected with {local_ip}:{local_port}\n')

		# Recieveing a file from client
		drtp.receive_data(file_name)

	# Closing connection
	drtp.close_connection()


def client(remote_ip, remote_port, file_name, reliability_func):
	# Creating DRTP instance
	drtp = DRTP(remote_ip, remote_port, reliability_func)  
	drtp.establish_sender_connection()
 
	print('\n' + '-' * 70)
	print(f"A client connecting to server {remote_ip}, port {remote_port}")
	print('-' * 70) 
	
	while True:

		print(f"Client connected with {remote_ip}, port {remote_port}\n") 

		drtp.send_file(file_name)

	drtp.close_connection()


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
	parser.add_argument('-s', '--server', action='store_true', help='Run as server')
	parser.add_argument('-c', '--client', action='store_true', help='Run as client')
	parser.add_argument('-i', '--remote-ip', help='Remote server IP address')
	parser.add_argument('-p', '--port', type=int, help='Server port number')
	parser.add_argument('-b', '--bind', type=str, help='Local IP address')
	parser.add_argument('-f', '--file-name', type=str, help='File name to transfer')
	parser.add_argument('-r', '--reliability-function', choices=['stop-and-wait', 'GBN', 'SR'], default='stop-and-wait', help='Reliability function to use (default: stop-and-wait)')

	args = parser.parse_args()

	if args.reliability_function == 'stop-and-wait':
		reliability_func = DRTP.stop_and_wait
	elif args.reliability_function == 'GBN':
		reliability_func = DRTP.gbn
	elif args.reliability_function == 'SR':
		reliability_func = DRTP.sr
	else:
		parser.error('Invalid reliability function specified')

	if args.server:
		server(args.bind, args.port, args.file_name, reliability_func)
	elif args.client:
		client(args.remote_ip, args.port, args.file_name, reliability_func)
	else:
		parser.print_help()

