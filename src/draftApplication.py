import os
import sys
from DRTP import DRTP

def main():
    if len(sys.argv) != 6:
        print("Usage: python application.py <IP> <port> <reliability_method> <send|recv> <file>")
        return

    ip, port, reliability_method, mode, file_path = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]

    if mode not in ['send', 'recv']:
        print("Invalid mode. Choose 'send' or 'recv'.")
        return

    if reliability_method not in ['stop_and_wait', 'gbn', 'sr']:
        print("Invalid reliability method. Choose 'stop_and_wait', 'gbn', or 'sr'.")
        return

    drtp = DRTP(ip, port, reliability_method)

    if mode == 'send':
        if not os.path.exists(file_path):
            print("File does not exist.")
            return

        with open(file_path, 'rb') as f:
            data = f.read()

        drtp.establish_connection()
        drtp.send_data(data)
        drtp.close_connection()

    elif mode == 'recv':
        drtp.establish_connection()
        data = drtp.receive_data(file_path)
        drtp.close_connection()

if __name__ == "__main__":
    main()

"""
To run the code, make sure you have the DRTP.py and application.py files in the same directory. Then, use the following command in the terminal to send or receive a file:

    To send a file: python application.py <IP> <port> <reliability_method> send <file>
    To receive a file: python application.py <IP> <port> <reliability_method> recv <file>

Replace <IP>, <port>, <reliability_method>, and <file> with the appropriate values for your use case. <reliability_method> should be one of the following: 'stop_and_wait', 'gbn', or 'sr'."""