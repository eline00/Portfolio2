import argparse
from DRTP import *
import time
import os

import sys

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
def server(ip, port, file_name, reliability_func, test_case):

	try:
		server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	except socket.error as e:
		print(f"Error creating socket: {e}")
	try:
		server_socket.bind(('', port))
	except socket.error as e:
		print(f"Error binding socket: {e}")
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
  
# Description:
# creates a client socket using UDP and utilizes DRTP for reliable data transfer
# establishes a connection with the server before selecting and running a specified reliability function
# calculates and prints the throughput for the file transfer before closing the connection
# Arguments: 
# ip: holds the ip address for the server
# port: port number of the server
# file_name: holds the filename for the received file
# reliablility_func: reliability function to use for sending data 
# window_size: specifies a size for the sliding window in the gbn and sr functions
# test_case: test case to test the reliability functions
# Returns: 
# No returns, only prints the throughput of the file transfer
def client(ip, port, file_name, reliability_func, window_size, test_case):
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	client_drtp = DRTP(ip, port, client_socket)
	print("\nSending SYN from the client. Waiting for SYN-ACK.")
	client_drtp.syn_client()

	start_time = time.time()
 
	if reliability_func == "stop-and-wait":
		stop_and_wait_client(client_drtp, file_name, test_case)
	elif reliability_func == "gbn":
		gbn_client(client_drtp, file_name, window_size, test_case)
	elif reliability_func == "sr":
		sr_client(client_drtp, file_name, window_size, test_case)

	end_time = time.time()
	elapsed_time = end_time - start_time										# Finds the elapsed time

	file_size = (os.path.getsize(file_name) * 8) / 1000000  					# Finds the size of the file in Mb
	throughput = file_size / elapsed_time 											  	
 
	# Printing the statistics
	print(f"\nElapsed Time: {elapsed_time:.2f} s")
	print(f"Transferred data: {(file_size):.2f} Mb")
	print(f"Throughput: {throughput:.2f} Mbps")

	print("\nFIN-ACK received. Closing connection.")
	client_drtp.close()															# Closing the connection upon receiving FIN
 
# Helper function for error handling related to file
def open_file(file_path, mode):
	try:
		return open(file_path, mode)
	except FileNotFoundError:
		print(f"\nFile not found: {file_path}")
		sys.exit(1)
	except PermissionError:
		print(f"\nPermission denied for file: {file_path}")
		sys.exit(1)

# Description:
# Implements a stop-and-wait server for receiving a file over a reliable transport protocol
# Arguments:
# drtp: an instance of the reliable transport protocol
# file: the file path to save the received data
# test_case: a test case to simulate (e.g., 'skip_ack' to skip an acknowledgment)
def stop_and_wait_server(drtp, file, test_case):

	print("\nStop-and-wait server started.")
	with open_file(file, 'wb') as f:
		expected_seq = 0																# Expects the first packet to have sequence number 0
		skip_ack_counter = 0															# Initializing skip ack counter to 0

		print("Receiving data...\n")
		while True:
			try:
				drtp.socket.settimeout(0.5)												# Sets a timeout of 500ms
				data_packet, data_addr = drtp.receive_packet()							# Receives packet from client
				seq_num, _, flags, _, data = drtp.parse_packet(data_packet)				# Parses the packet and stores the received values

				# Checks if the FIN flag is set, indicating the end of the file transfer
				if flags & drtp.FIN:
					print("\nFIN flag received. Sending FIN-ACK")
					ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')			# Creates an ACK packet for the received FIN packet
					drtp.send_packet(ack_packet, data_addr)								# Send the ACK packet to client
					break

				# Checks if the received packet's sequence number matches the expected sequence number
				if seq_num == expected_seq:
					f.write(data)														# Writes data to file
					expected_seq += 1													# Increasing the expected sequence number

					# Implements the 'skip_ack' test case by skipping an acknowledgment
					if test_case == 'skip_ack' and skip_ack_counter == 0:
						print(f"Skip ACK triggered at sequence number {seq_num} \n")
						skip_ack_counter += 1											# Updates counter
					else:
						# Creating and sening ACK to the client
						ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
						drtp.send_packet(ack_packet, data_addr)
				else:
					# Sends an ACK for the last correctly received packet if the received sequence number does not match the expected one
					if seq_num < expected_seq:
						print(f"Duplicate packet received: {seq_num}")

					elif seq_num > expected_seq:
						print(f"Out-of-order packet received: {seq_num}")
      
					ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
					drtp.send_packet(ack_packet, data_addr)

			except socket.timeout:
				# Handles a timeout and continues to receive packets
				print(f"\nTimeout occurred on the server")
				continue

# Description:
# Implements a stop-and-wait client for sending a file over a reliable transport protocol
# Arguments:
# drtp: an instance of the reliable transport protocol
# file: the file path to the file to be sent
def stop_and_wait_client(drtp, file, test_case):

	print("\nStop-and-wait client started.")
 
	# Opening file in read binary mode
	with open_file(file, 'rb') as f:
		expected_seq = 0									# Expecting the first sequence number to be 0
  
		# Initializing variables for calculating RTT
		rtt_sum = 0
		packet_count = 0

		print("Transmitting data...")
		while True:
			data = f.read(1460)								# Reads data to send in chunks of size 1460
			if not data:
				break

			# Creates a packet with the current sequence number and data
			packet = drtp.create_packet(expected_seq, 0, 0, 0, data)
   
			# Sends the packet and waits for an acknowledgment from server
			drtp.send_packet(packet, (drtp.ip, drtp.port))

			# Sends duplicate packet with sequence number 6 if test case 'duplicate' is invoked
			if test_case == "duplicate" and expected_seq == 6:
				print(f"Sending duplicate packet with sequence number: {expected_seq}")
				drtp.send_packet(packet, (drtp.ip, drtp.port))
	
			ack_received = False												# ack_received is False until an ACK is received
			while not ack_received:												# Waits for ACK as long as the packet is not already ACKed
				try:
					send_time = time.time()
					drtp.socket.settimeout(0.5) 								# Initial timeout value to 500ms
					ack_packet, ack_addr = drtp.receive_packet()				# Receives ACK packet from server
					recv_time = time.time()
					_, _, flags, _, _ = drtp.parse_packet(ack_packet)			# Parsing the ACK packet
					
					#Checks if the received packet is an ACK
					if flags & 0x10:
						ack_received = True
	  
						# Finding the RTT
						rtt = recv_time - send_time
						rtt_sum += rtt
						packet_count += 1

						# Calculate the average RTT and set the timeout to 4RTTs
						avg_rtt = rtt_sum / packet_count if packet_count > 0 else 0.5
						timeout = 4 * avg_rtt
						drtp.socket.settimeout(timeout)

				except socket.timeout:
					# Handles a timeout and resends the packet
					print(f"\nTimeout occurred. Resending packet with sequence number: {expected_seq}")
					drtp.send_packet(packet, (drtp.ip, drtp.port))
					
			expected_seq += 1					# Increasing the expected sequence number

		# Sends a packet with the FIN flag set after the file data has been sent
		print("\nSending FIN packet.")
		fin_packet = drtp.create_packet(expected_seq, 0, drtp.FIN, 0, b'')
		drtp.send_packet(fin_packet, (drtp.ip, drtp.port))

# Description:
# Implements a Go-Back-N server for receiving a file over a reliable transport protocol
# Arguments:
# drtp: an instance of the reliable transport protocol
# file: the file path where the received file will be saved
# test_case: a test case to execute, such as 'skip_ack' to simulate a skipped acknowledgment
def gbn_server(drtp, file, test_case):

	print("\nGo-Back-N server started.")
 
	# Opening the file in write binary mode
	with open_file(file, 'wb') as f:
		expected_seq = 0											# Expecting the sequence number to start at 0
		skip_ack_counter = 0										# Initializing the skip ack variable so that the first packet is skipped
  
		print("Receiveing data...\n")
		while True:
			try:
				drtp.socket.settimeout(0.5)							# Sets a timeout for receiving packets and attempts to receive a data packet
				data_packet, data_addr = drtp.receive_packet()		# Receives a packet from the client
				seq_num, _, flags, _, data = drtp.parse_packet(data_packet)

				# Checks if the received packet has the FIN flag set, indicating the end of transmission
				if flags & drtp.FIN:
					print("\nFIN flag received.")
					break

				# Processes and write the received packet to file if it has the expected sequence number
				if seq_num == expected_seq:
					f.write(data)
					expected_seq += 1

					# Skips sending an ACK if the test_case is 'skip_ack' and skip_ack_counter is 0
					if test_case == "skip_ack" and skip_ack_counter == 0:
						time.sleep(0.5)
						skip_ack_counter += 1
						print(f"Skip ACK triggered at sequence number {seq_num} \n")
					else:
						# Creating and sending ACK packet
						ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
						drtp.send_packet(ack_packet, data_addr)

				else:
					# Sends an ACK for the last correctly received packet if the received packet is out of order or a duplicate
					if seq_num < expected_seq:
						print(f"Duplicate packet received: {seq_num}")

					elif seq_num > expected_seq:
						print(f"Out-of-order packet received: {seq_num}")
					ack_packet = drtp.create_packet(0, expected_seq, 0x10, 0, b'')
					drtp.send_packet(ack_packet, data_addr)
	 
			except socket.timeout:
				# Retransmitts the packet if no packet was received and a timeout occures
				print("\nTimeout occurred on the server.")
				continue

# Description:
# Implements a Go-Back-N client for sending a file over a reliable transport protocol
# Arguments:
# drtp: an instance of the reliable transport protocol
# file: the file path of the file to be sent
# window_size: the window size for the Go-Back-N protocol
# test_case: a test case to execute, such as 'skip_seq' to simulate a skipped packet
def gbn_client(drtp, file, window_size, test_case):

	print("\nGo-Back-N client started.")
 
	# Opening file in read binary mode
	with open_file(file, 'rb') as f:
		base = 0
		next_seq_num = 0
		packets_in_window = {}
		received = {}

		# Variables for calculating average RTT
		rtt_sum = 0
		packet_count = 0
  
		# Variables for skip_seq and duplicate test cases
		skipped_packet = None
		skip_seq = 4
		duplicate_packet = None

		print("Transmitting data...")
		while True:
			# Reads packets within the window size
			while next_seq_num < base + window_size:
				data = f.read(1460)
				if not data:
					break

				packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)			# Creating a packet with data and sequence number

				# Skips sending a packet if the test_case is 'skip_seq' and next_seq_num is 0
				if test_case == "skip_seq" and next_seq_num == skip_seq:
					print(f"\nSkipping packet with sequence number: {next_seq_num}")
					skipped_packet = packet
				else:
					# Sending the packet and adding it to the window of unacknowledged packets
					drtp.send_packet(packet, (drtp.ip, drtp.port))					
					packets_in_window[next_seq_num] = packet
	 
				next_seq_num += 1
				
				# Sending an old sequence number to test the handling of duplicate packets
				if test_case == "duplicate" and next_seq_num == 6:
					duplicate_packet = packets_in_window[next_seq_num - 1]
					print(f"Sending duplicate packet with sequence number: {next_seq_num - 1}")
					drtp.send_packet(duplicate_packet, (drtp.ip, drtp.port))
					duplicate_packet = None

			# Exits the loop if all packets have been sent
			if not packets_in_window:
				break

			# Receives ACK packets and updates the base pointer accordingly
			try:
				send_time = time.time()
				
				drtp.socket.settimeout(0.5)							# Setting a timeout of 500ms
				ack_packet, ack_addr = drtp.receive_packet()		# receiveing packet from server
	
				recv_time = time.time()				
				_, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)		# Parsing the received packet

				if flags & 0x10:									# Checks if the received packet is an ACK
					for seq_num in range(base, ack_num):
						if seq_num in packets_in_window:  			# Check if seq_num exists in the dictionary
							packets_in_window.pop(seq_num)			# Removes acknowledged packet from window
					base = ack_num

				# Finding the RTT
				rtt = recv_time - send_time
				rtt_sum += rtt
				packet_count += 1
				
				# Calculate the average RTT and set the timeout to 4RTTs
				avg_rtt = rtt_sum / packet_count if packet_count > 0 else 0.5
				timeout = 4 * avg_rtt
				drtp.socket.settimeout(timeout)
				
			except socket.timeout:

				# Resends all packets in the current window upon a timeout
				if test_case == "skip_seq" and skipped_packet and base == skip_seq:
					packets_in_window[skip_seq] = skipped_packet
					skipped_packet = None

				# Resends all packets in the window in case of timeout
				print("\nTimeout occurred.")
				for seq_num in sorted(packets_in_window.keys()):
					packet = packets_in_window[seq_num]
					drtp.send_packet(packet, (drtp.ip, drtp.port))
					print(f"Resending packet with sequence number: {seq_num}")

		# Sends a packet with the FIN flag set after the file data has been sent
		print("\nSending FIN packet.")
		fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
		drtp.send_packet(fin_packet, (drtp.ip, drtp.port))

# Description:
# Implements a Selective Repeat server for receiving a file over a reliable transport protocol
# Arguments:
# drtp: an instance of the reliable transport protocol
# file: the file path of the file to be received
# test_case: a test case to execute, such as 'skip_ack' to simulate a skipped ACK packet
def sr_server(drtp, file, test_case):

	print("\nSelective Repeat server started.")
 
	# Opening file in write binary mode
	with open_file(file, 'wb') as f:
		expected_seq = 0
		skip_ack_counter = 0
		received = {}																# A dictionary to buffer out-of-order packets

		print("Receiving data...\n")
		while True:
			try:
				drtp.socket.settimeout(0.5)											# Setting a timeout of 500ms
				data_packet, data_addr = drtp.receive_packet()						# Receiving packet from client
				seq_num, _, flags, _, data = drtp.parse_packet(data_packet)			# Parsing the received packet

				# Checks for FIN flag and sends FIN-ACK in response
				if flags & drtp.FIN:
					print("\nFIN flag received. Sending FIN-ACK")
					ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')		# Send an ACK packet for the received FIN packet
					drtp.send_packet(ack_packet, data_addr)
					break
				
				ack_packet = drtp.create_packet(0, seq_num, 0x10, 0, b'')
	
				# Skips sending an ACK if the test_case is 'skip_ack' and skip_ack_counter is 0
				if test_case == 'skip_ack' and skip_ack_counter == 0:
					skip_ack_counter += 1
					print(f"Skip ACK triggered at sequence number {seq_num} \n")
				else:
					# Writes data to the file if the received sequence number matches the expected sequence number
					if seq_num == expected_seq:
						drtp.send_packet(ack_packet, data_addr)
						f.write(data)
						expected_seq += 1
      
						# While there are in-order packets in the buffer, write them to the file
						while expected_seq in received:
							data = received.pop(expected_seq)
							f.write(data)
							expected_seq += 1
		
					elif seq_num > expected_seq:
						print(f"Out-of-order packet received: {seq_num}")
						received[seq_num] = data
						drtp.send_packet(ack_packet, data_addr)
					else:
						print(f"Duplicate packet received: {seq_num}")
						drtp.send_packet(ack_packet, data_addr)	  
      
			except socket.timeout:
				print("\nTimeout occurred on the server.")
				continue

# Description:
# Implements a Selective Repeat client for sending a file over a reliable transport protocol
# Arguments:
# drtp: an instance of the reliable transport protocol
# file: the file path of the file to be sent
# window_size: the size of the sliding window
# test_case: a test case to execute, such as 'skip_seq' to simulate skipping a packet sequence number
def sr_client(drtp, file, window_size, test_case):

	print("\nSelective Repeat client started.")
 
	# Opening file in read binary mode
	with open_file(file, 'rb') as f:
		base = 0
		next_seq_num = 0
		packets_in_window = {}
		received = {}
  
		# Variables for calculating average RTT
		rtt_sum = 0
		packet_count = 0
  
		# Variables for skip_seq and duplicate test case
		skip_seq = 5
		duplicate_packet = None
		
		print("Transmitting data...")
		while True:
			# Reading 1460 bytes of data from the file until theres no more data
			while next_seq_num < base + window_size:
				data = f.read(1460)
				if not data:
					break

				# Creating a packet with correct sequence number and data
				packet = drtp.create_packet(next_seq_num, 0, 0, 0, data)
	
				# Skipping a sequence number to simulate loss
				if test_case == "skip_seq" and next_seq_num == skip_seq:
					print(f"\nSkipping packet with sequence number: {next_seq_num}")
					packets_in_window[next_seq_num] = (packet, False)
				else:
					# Sending the packet and storing it in the window
					drtp.send_packet(packet, (drtp.ip, drtp.port))
					packets_in_window[next_seq_num] = (packet, True)
				
				next_seq_num += 1
	
				# Sending an old sequence number to test the handling of duplicate packets
				if test_case == "duplicate" and next_seq_num == 2:
						duplicate_packet, sent = packets_in_window[next_seq_num - 1]
						print(f"Sending duplicate packet with sequence number: {next_seq_num - 1}")
						drtp.send_packet(duplicate_packet, (drtp.ip, drtp.port))
						duplicate_packet = None

			if not packets_in_window:
				break

			# Receives ACK packets and updates the base sequence number and window accordingly
			try:
				send_time = time.time()											# Time before receiveing ACK packet
				drtp.socket.settimeout(0.5)										# Setting a timeout of 500ms
				ack_packet, ack_addr = drtp.receive_packet()					# Receiving ACK from server
				recv_time = time.time()											# Time after receiving ACK packet
				seq_num, ack_num, flags, _, _ = drtp.parse_packet(ack_packet)	# Parsing the packet received

				if flags & 0x10:												# Cheking if the received packet is an ACK
					packets_in_window.pop(ack_num, None)    							# Removing acknowledged packet from window
					received[ack_num] = True
					while base in received:    									# Move the base if the packet is acknowledged
						base += 1
				
				# Calculates the RTT
				rtt = recv_time - send_time
				rtt_sum += rtt
				packet_count += 1
				
				# Calculates the average RTT and set the timeout to 4RTTs
				avg_rtt = rtt_sum / packet_count if packet_count > 0 else 0.5
				timeout = 4 * avg_rtt
				drtp.socket.settimeout(timeout)
				
			except socket.timeout:
				print("\nTimeout occurred.")
				# Retransmits the skipped packet aftes timeout occurs
				for seq_num in packets_in_window.keys():
					packet, sent = packets_in_window[seq_num]
					if not sent or seq_num not in received:
						drtp.send_packet(packet, (drtp.ip, drtp.port))
						print(f"Resending packet with sequence number: {seq_num}")
						

		# Sends a packet with the FIN flag set after the file data has been sent
		print("\nSending FIN packet.")
		fin_packet = drtp.create_packet(next_seq_num, 0, drtp.FIN, 0, b'')
		drtp.send_packet(fin_packet, (drtp.ip, drtp.port))


if __name__ == '__main__':
	# Parsing all the available flags to an argument parser
	parser = argparse.ArgumentParser(description='Simple file transfer application using DRTP protocol')
	parser.add_argument('-s', '--server', action='store_true', help='Run as server')
	parser.add_argument('-c', '--client', action='store_true', help='Run as client')
	parser.add_argument('-i', '--ip', default='127.0.0.1', help='Remote server IP address')
	parser.add_argument('-p', '--port', type=int, default=8080, help='Server port number')
	parser.add_argument('-f', '--file_name', type=str, help='File name to transfer')
	parser.add_argument('-r', '--reliability_func', default='stop-and-wait',
						help='Reliability function to use (default: stop_and_wait)')
	parser.add_argument('-w', '--window_size', default=5, type=int, help="Size of the sliding window")
	parser.add_argument('-t', '--test_case', type=str, default=None, help='Test case to run (e.g., skip_ack)')

	args = parser.parse_args()
 
	# Error message for port out of range
	if args.port not in range(1024, 65536):
		print('Port out of range: port must be between 1024 and 65536!')
		sys.exit(1)
  
	# Error message for invalid reliability function
	if args.reliability_func not in ['stop-and-wait', 'gbn', 'sr']:
		print('Invalid reliability function: choose between stop-and-wait, gbn or sr!')
		sys.exit(1)
  
	# Error message for invalid test case
	if args.test_case is not None and args.test_case not in ['skip_ack', 'skip_seq', 'duplicate']:
		print('No such test case: choose between skip_ack, skip_seq or duplicate!')
		sys.exit(1)

	# Runs eiter server or client, otherwise an error message is shown
	if args.server:
		server(args.ip, args.port, args.file_name, args.reliability_func, args.test_case)
	elif args.client:
		client(args.ip, args.port, args.file_name, args.reliability_func, args.window_size, args.test_case)
	else:
		print('Error: must be in either client(-c) or server(-s) mode!')
		sys.exit(1)
