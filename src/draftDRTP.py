import socket
from struct import *
import time
import threading


class DRTP:
    HEADER_FORMAT = '!IIHH'
    HEADER_SIZE = calcsize(HEADER_FORMAT)

    def __init__(self, ip, port, reliability_method, timeout=0.5, window_size=5):
        self.ip = ip
        self.port = port
        self.reliability_method = reliability_method
        self.timeout = timeout
        self.window_size = window_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self.timeout)

    def create_packet(self, seq, ack, flags, win, data):
        header = pack(self.HEADER_FORMAT, seq, ack, flags, win)
        return header + data

    def parse_header(self, header):
        return unpack(self.HEADER_FORMAT, header)

    def parse_flags(self, flags):
        syn = flags & (1 << 3)
        ack = flags & (1 << 2)
        fin = flags & (1 << 1)
        return syn, ack, fin

    def establish_connection(self):
        if self.reliability_method == 'send':
            self.establish_sender_connection()
        elif self.reliability_method == 'recv':
            self.establish_receiver_connection()

    def establish_sender_connection(self):
        seq = 0
        ack = 0
        syn_flag = 1 << 3
        self.socket.sendto(self.create_packet(seq, ack, syn_flag, 0, b''), (self.ip, self.port))
        while True:
            try:
                data, _ = self.socket.recvfrom(1472)
                header = data[:self.HEADER_SIZE]
                seq, ack, flags, win = self.parse_header(header)
                syn, ack_flag, fin = self.parse_flags(flags)
                if syn and ack_flag:
                    seq = 0
                    ack = 1
                    ack_flag = 1 << 2
                    self.socket.sendto(self.create_packet(seq, ack, ack_flag, 0, b''), (self.ip, self.port))
                    break
            except socket.timeout:
                self.socket.sendto(self.create_packet(seq, ack, syn_flag, 0, b''), (self.ip, self.port))

    def establish_receiver_connection(self):
        while True:
            try:
                data, addr = self.socket.recvfrom(1472)
                header = data[:self.HEADER_SIZE]
                seq, ack, flags, win = self.parse_header(header)
                syn, ack_flag, fin = self.parse_flags(flags)
                if syn:
                    seq = 0
                    ack = 1
                    syn_flag = 1 << 3
                    ack_flag = 1 << 2
                    self.socket.sendto(self.create_packet(seq, ack, syn_flag | ack_flag, 0, b''), addr)
                    break
            except socket.timeout:
                pass
            
    def send_file(self, file_name):
        with open(file_name, 'rb') as f:
            file_data = f.read()
        self.send_data(file_data)


    def send_data(self, data):
        if self.reliability_method == 'stop_and_wait':
            self.stop_and_wait(data)
        elif self.reliability_method == 'gbn':
            self.gbn(data)
        elif self.reliability_method == 'sr':
            self.sr(data)

    def receive_data(self, file_name):
        if self.reliability_method == 'stop_and_wait':
            return self.stop_and_wait_recv(file_name)
        elif self.reliability_method == 'gbn':
            return self.gbn_recv(file_name)
        elif self.reliability_method == 'sr':
            return self.sr_recv(file_name)


    def close_connection(self):
        self.socket.close()

    def stop_and_wait(self, data):
        seq = 0
        data_idx = 0
        while data_idx < len(data):
            chunk = data[data_idx:data_idx + 1472 - self.HEADER_SIZE]
            self.socket.sendto(self.create_packet(seq, 0, 0, 0, chunk), (self.ip, self.port))
            try:
                _, addr = self.socket.recvfrom(1472)
            except socket.timeout:
                continue
            data_idx += len(chunk)
            seq = 1 - seq

    def stop_and_wait_recv(self, file_name):
        seq = 0
        with open(file_name, 'wb') as f:
            while True:
                try:
                    data, addr = self.socket.recvfrom(1472)
                    header = data[:self.HEADER_SIZE]
                    r_seq, _, _, _ = self.parse_header(header)
                    if r_seq == seq:
                        f.write(data[self.HEADER_SIZE:])
                        self.socket.sendto(self.create_packet(seq, 0, 0, 0, b''), addr)
                        seq = 1 - seq
                except socket.timeout:
                    break

    def gbn(self, data):
        base = 0
        next_seq = 0
        unacknowledged_packets = {}
        send_thread = threading.Thread(target=self.gbn_send, args=(data, unacknowledged_packets))
        send_thread.start()
        while base < len(data):
            try:
                _, addr = self.socket.recvfrom(1472)
                header = data[:self.HEADER_SIZE]
                _, ack, _, _ = self.parse_header(header)
                if ack >= base:
                    base = ack + 1
            except socket.timeout:
                base = self.gbn_resend(base, unacknowledged_packets)

    def gbn_send(self, data, unacknowledged_packets):
        seq = 0
        data_idx = 0
        while data_idx < len(data):
            chunk = data[data_idx:data_idx + 1472 - self.HEADER_SIZE]
            packet = self.create_packet(seq, 0, 0, 0, chunk)
            self.socket.sendto(packet, (self.ip, self.port))
            unacknowledged_packets[seq] = packet
            seq = (seq + 1) % self.window_size
            data_idx += len(chunk)

    def gbn_resend(self, base, unacknowledged_packets):
        for seq in range(base, base + self.window_size):
            if seq in unacknowledged_packets:
                self.socket.sendto(unacknowledged_packets[seq], (self.ip, self.port))
        return base

    def gbn_recv(self, file_name):
        seq = 0
        with open(file_name, 'wb') as f:
            while True:
                try:
                    data, addr = self.socket.recvfrom(1472)
                    header = data[:self.HEADER_SIZE]
                    r_seq, _, _, _ = self.parse_header(header)
                    if r_seq == seq:
                        f.write(data[self.HEADER_SIZE:])
                        seq = (seq + 1) % self.window_size
                    self.socket.sendto(self.create_packet(0, seq, 0, 0, b''), addr)
                except socket.timeout:
                    break

    def sr(self, data):
        base = 0
        next_seq = 0
        unacknowledged_packets = {}
        lock = threading.Lock()
        send_thread = threading.Thread(target=self.sr_send, args=(data, unacknowledged_packets, lock))
        send_thread.start()

        while base < len(data):
            try:
                _, addr = self.socket.recvfrom(1472)
                header = data[:self.HEADER_SIZE]
                _, ack, _, _ = self.parse_header(header)

                with lock:
                    if ack in unacknowledged_packets:
                        del unacknowledged_packets[ack]
                        if ack == base:
                            base += 1
                            while base in unacknowledged_packets:
                                del unacknowledged_packets[base]
                                base += 1
            except socket.timeout:
                self.sr_resend(unacknowledged_packets, lock)

    def sr_send(self, data, unacknowledged_packets, lock):
        seq = 0
        data_idx = 0
        while data_idx < len(data):
            chunk = data[data_idx:data_idx + 1472 - self.HEADER_SIZE]
            packet = self.create_packet(seq, 0, 0, 0, chunk)
            self.socket.sendto(packet, (self.ip, self.port))
            with lock:
                unacknowledged_packets[seq] = packet
            seq = (seq + 1) % self.window_size
            data_idx += len(chunk)

    def sr_resend(self, unacknowledged_packets, lock):
        with lock:
            for seq, packet in unacknowledged_packets.items():
                self.socket.sendto(packet, (self.ip, self.port))

    def sr_recv(self, file_name):
        buffer = {}
        expected_seq = 0

        with open(file_name, 'wb') as f:
            while True:
                try:
                    data, addr = self.socket.recvfrom(1472)
                    header = data[:self.HEADER_SIZE]
                    r_seq, _, _, _ = self.parse_header(header)

                    if r_seq == expected_seq:
                        f.write(data[self.HEADER_SIZE:])
                        expected_seq = (expected_seq + 1) % self.window_size
                        while expected_seq in buffer:
                            f.write(buffer[expected_seq])
                            del buffer[expected_seq]
                            expected_seq = (expected_seq + 1) % self.window_size
                    elif r_seq not in buffer:
                        buffer[r_seq] = data[self.HEADER_SIZE:]

                    self.socket.sendto(self.create_packet(0, r_seq, 0, 0, b''), addr)

                except socket.timeout:
                    break

