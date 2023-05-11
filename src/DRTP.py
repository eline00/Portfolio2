import socket
from struct import pack, unpack

class DRTP:
    
    # Description:
	# constructor that initializes IP, port and socket, as well as the falgs
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	# ip: holds the ip address for the server
	# port: port number of the server
	# socket: stores a socket object
	def __init__(self, ip, port, socket):
		self.ip = ip
		self.port = port
		self.socket = socket
		self.ACK = 1 << 0
		self.SYN = 1 << 1
		self.FIN = 1 << 2

	# Description:
	# sends a packet using UDP sockets 'sendto' method
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	# packet: holds a packet 
	# addr: the address we want to send the packet to
	def send_packet(self, packet, addr):
		self.socket.sendto(packet, addr)				
		
	# Description:
	# receives a packet using UDP sockets 'recvfrom' method
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	# Returns:
	# Returns the packet and address that was recevied so that they can be utilized later in the application code
	def receive_packet(self):
		packet, addr = self.socket.recvfrom(1472)						
		return packet, addr

	# Description:
	# creates the header as a byte sting using the struct module, and adds the data at the end
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	# seq_num: sequence number for the packet
	# ack_num: acknowledgement number for the packet
	# flags: specifies what type of packet is being sent (e.g. ACK, FIN or SYN)
	# window: the packets window size
	# data: the actual data payload of the packet
	# Returns:
	# Returns a packet that consists of a header and the data so that they can be utilized later in the application code
	def create_packet(self, seq_num, ack_num, flags, window, data):
		header = pack("!IIHH", seq_num, ack_num, flags, window)				
		packet = header + data												
		return packet
	
	# Description:
	# parses a packets header using structs unpack module, as well as the data at the end of the packet
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	# packet: hold a packet
	# Returns:
	# Returns the header (seq_num, ack_num, flags, window) and the data if there is any, otherwise an empty byte string
	# so that they can be utilized later in the application code
	def parse_packet(self, packet):
		header = packet[:12]												# header is the 12 first bytes of the packet
		data = packet[12:]													# data is the 12 last bytes of the packet
		seq_num, ack_num, flags, window = unpack("!IIHH", header)			
		return seq_num, ack_num, flags, window, data if data else b''		

	# Description:
	# Establishes a connection between the server and a client using the SYN/SYN-ACK handshake, 
 	# a part of the TCP three-way handshake process
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	def syn_server(self):
		while True:
			packet, addr = self.receive_packet()								# Receives a packet from the server
			seq_num, ack_num, flags, window, _ = self.parse_packet(packet)		# Parses the received packet
			if flags & self.SYN:												# Checks if SYN flag is set
				print("\nReceived SYN packet from the client")  
				syn_ack_packet = self.create_packet(seq_num+1, ack_num+1, self.SYN | self.ACK, window, b'')		# Creats ACK packet for the SYN packet
				self.send_packet(syn_ack_packet, addr)							# Sends ack for the syn packet
				print(f"SYN-ACK packet sent to {addr}")  
				break

	# Description:
	# Initiates a three way handshake with the server by sending a SYN packet to the server.
 	# Waits for acknowledgement from server, and retransmits the packet if ACK is not received
	# Arguments:
	# self: reference to the instance of the class that the method is being called on
	def syn_client(self):
		syn_seq_num = 0  														# Sequence number for the first SYN packet
		syn_packet = self.create_packet(syn_seq_num, 0, self.SYN, 64, b'')		# Creates the SYN packet
		self.send_packet(syn_packet, (self.ip, self.port))						# Sends the packet to the server address

		self.socket.settimeout(0.5)												# Setting a timeout of 50ms

		while True:
			try:
				packet, addr = self.receive_packet()							# Receiving packet from server
				seq_num, ack_num, flags, window, _ = self.parse_packet(packet)	# Parsing the packet
				if flags & self.SYN and flags & self.ACK and ack_num == syn_seq_num + 1:	# Checking if the packet is an ACK for the SYN packet
					print("Received SYN-ACK packet from the server") 
					ack_packet = self.create_packet(seq_num+1, ack_num, self.ACK, window, b'') 	# Create new ACK packet for the SYN-ACK packet
					self.send_packet(ack_packet, (self.ip, self.port))			# Sending ACK back to the server upon receiving SYN-ACK
					break
			except socket.timeout:
				print("\nTimeout occurred, resending SYN packet") 
				self.send_packet(syn_packet, (self.ip, self.port))				# Resend the SYN packet if the timeout occurs

	# Description:
	# Closes the connection using UDP sockets close method
	# Arguments:
	# self: reference to the instance of the class that the method is being called on	
	def close(self):
		self.socket.close()
