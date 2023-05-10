# DRTP File Transfer Application

The DRPT is a robust utility designed to simplify a reliable file transfer system over an unreliable network. It is built around the  protocol of UDP, a reliable transport layer protocol created specifically for this application. The implementation ensure reliable data delivery by handling lost or corrupted packets, ensuring in-order packet delivery, and preventing duplicates. 

To achieve this we have constructed packets and acknowledgements, gracefully established closed connections and implemented flow control.

The main purpose of this application is to implement a simple file transfer program that utilizes the mentioned DRTP protocol and transfer the selected files correctly in an exuisite manner with no pakcet loss. This should take effect restrictvely between two nodes and the network is expected to use a specified reliability function, all included in the application.py program.

The application also supports multiple test cases to simulate a specific scenario, such as skipping an acknowledgement to trigger retransmission at the sender-side. These are all designed to simulate network conditions or behaviors to verify the robustness and correctness of the protocol implementation. 

Besides that the application is also programmed to support three main reliability functions:
Stop-and-wait, Go-back-N(GBN), and Selective Repeat(SR). The user can choose the desired reliability function, and the application will handle file transfer according to the selected method. 

All of these main components mentioned can be executed using different command line arguments. Further explanation on how to run the actual application.py including all the flags is interpreted below. 

# Application arguments

    -s, --server

    Runs the application in server mode. 

    -c, --client 
    Runs the application in client mode.

    -i 
    Specifies the local IP address.

    -p 
    Specifies the server port number.

    -f
    Specifies the file name to transfer.

    -r
    Specifies the reliability function to use. Choose from stop-and-wait, 'gbn' or 'sr'.

    -w 
    Specifies the size of the sliding window.

    -t
    Specifies a test case run.

    
# Example Usage

    Running as a server
    To run the application as a server, use the -s flag:
> python3 application.py -s -p 8080 -f received_photo.jpg 

    Running as a client 
    To run the application as a client, use the -c flag:
> python3 application.py -c -i 127.0.0.1 -p 8080 -f photo_to_send.jpg

    Using a specific reliability function
    To use a specific reliability function, use the -r flag followed by the desired reliability function:
> python3 application.py -c -i 127.0.0.1 -p 8080 -f photo_to_send.jpg -r gbn

    Running a specific test case
    To run the application with a specific test case, use the -t flag followed by the desired test case.
> python3 application.py -c -i 127.0.0.1 -p 8080 -f photo_to_send.jpg -t skip_ack
    


By using these command-line arguments the application will be able to process all the distinctive flags and invoke the program either in server or client mode. With the specified parameters both client and server functions will then handle the file transfer using a chosen reliability function.     

For each reliability functions, the application defines seperate functions for both server and client roles. Each of these functions implements the logic for handling packet transmission, acknowledgement, timeouts, and error recovery. All which is handled and coordinated in different test case scenarios. 

These flags and test cases are used throughout the program in the implementation of different reliable data transfer protocols. Each of these protocols has different ways of handling packet loss, transmission errors, and ordering issues, providing different trade-offs between complexity and efficiency. 








