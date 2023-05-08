DRTP File Transfer Application
This application is a file transfer program that uses the DRTP to transfer files between a client and a server. The application supports three functions:
Stop-and-wait, Go-back-N(GBN), and Selective Repeat(SR). The user can choose the desired reliability function, and the application will handle file transfer according to the selected method. 
The program also supports the execution of various test cases cases, such as skipping ACKs, sequence numbers or packet duplicates.
    Flags
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
    
    Examples
    Running as a server
    To run the application as a server, use the -s flag:
    python3 application.py -s -p 8080 -f received_photo.jpg 
    Running as a client 
    To run the application as a client, use the -c flag:
    python3 application.py -c -i 127.0.0.1 -p 8080 -f photo_to_send.jpg
    Using a specific reliability function
    To use a specific reliability function, use the -r flag followed by the desired reliability function
    python3 application.py -c -i 127.0.0.1 -p 8080 -f photo_to_send.jpg -r gbn
    Running with a specific test case
    To run the application with a specific test case, use the -t flag followed by the desired test case.
    python3 application.py -c -i 127.0.0.1 -p 8080 -f photo_to_send.jpg -t skip_ack
    

