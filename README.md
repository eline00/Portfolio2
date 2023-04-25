# Guide to test the code thoroughly  

## Unit testing individual functions: 

Test each function in the DRTP class in isolation. For example, test the header 
creation and parsing functions, connection establishment and tear down functions, and the reliability functions (stop_and_wait, gbn, sr).
Provide different inputs to the functions and validate their output to ensure they work as intended.

Unit testing individual functions: You can use a testing framework like pytest to create test cases for each function 
in the DRTP class. Write separate test functions for different scenarios and use assertions to validate the output. 
Run the tests using the pytest command.

## Integration testing: 

Test the client-server interaction as a whole by running both the client and the server simultaneously.
Check if the file transfer is successful under normal conditions, i.e., no packet loss, reordering, or delay. 
Verify if the transferred file is identical to the original file by comparing their checksums or hashes (e.g., MD5 or SHA-256).

- server:
> python3 application.py -s -b <local_ip> -p <local_port> -f received_file.txt -r stop_and_wait

- client: 
> python3 application.py -c -I <remote_ip> -p <remote_port> -f original_file.txt -r stop_and_wait

- After the transfer is complete, compare the original and received files using the diff command (fc windows):
> diff original_file.txt received_file.txt

If there's no output, the files are identical.

## Test reliability functions: For each reliability function (stop_and_wait, gbn, sr):

-  a. Packet loss: Introduce artificial packet loss in the network using a tool like tc-netem or by modifying the DRTP 
class to randomly drop packets. Test each reliability function under different packet loss rates, e.g., 1%, 5%, and 10%. 
Verify if the file transfer is still successful and if the transferred file is identical to the original file.

Packet loss: Use tc-netem to introduce packet loss on the server side. First, add a network emulation rule:

> sudo tc qdisc add dev <network_interface> root netem loss 5%

"Replace <network_interface> with the appropriate network interface name (e.g., eth0, enp0s3). This command introduces 
5% packet loss. Then, run the client and server as described in step 2. Repeat the test for different packet loss rates, 
such as 1% and 10%, and for different reliability functions by changing the -r argument in the application.py commands."

After testing, remove the network emulation rule with:

> sudo tc qdisc del dev <network_interface> root


- b. Packet reordering: Introduce artificial packet reordering in the network using tc-netem or by modifying the DRTP 
class to reorder packets. Test each reliability function under different reordering rates and verify if the file 
transfer is successful and the transferred file is identical to the original file.

> sudo tc qdisc add dev <network_interface> root netem delay 10ms reorder 25% 50%

This command introduces a 10ms delay and reorders 25% of the packets with a correlation of 50%. Run the client and server as described in step 2. Repeat the test for different reordering rates and for different reliability functions.

After testing, remove the network emulation rule.

- c. Packet duplication: Introduce artificial packet duplication in the network using tc-netem or by modifying the DRTP 
class to duplicate packets. Test each reliability function under different duplication rates and verify if the file 
transfer is successful and the transferred file is identical to the original file.

Use tc-netem to introduce packet duplication. Add a network emulation rule:

> sudo tc qdisc add dev <network_interface> root netem duplicate 10%

This command introduces a 10% packet duplication rate. Run the client and server as described in step 2. Repeat the test
for different duplication rates and for different reliability functions.

## Test timeout and retransmission: 
Test the code's behavior under different network conditions, such as varying latency or 
packet loss rates. Check if the retransmission mechanism works correctly and if the timeout values are appropriately 
chosen for the given network conditions.

Modify the DRTP class to introduce a logging mechanism, such as using Python's logging module, to print messages related 
to retransmission and timeouts. Run the client and server as described in step 2 under different network conditions, such 
as varying latency or packet loss rates

## Test connection establishment and tear down: 

Test the three-way handshake and connection tear down processes by monitoring 
the packet exchange between the client and server. Ensure that the connection is established correctly and gracefully closed
when the transfer is complete.

 start capturing packets in Wireshark before you run the client and server as described in step 2. Then, filter the packets 
 by the IP addresses and port numbers used in the application to observe the connection establishment and tear down processes.

## Test edge cases and error handling: 

Test the code's behavior under edge cases, such as empty files, very large files, 
invalid file names, incorrect IP addresses or port numbers, and unsupported reliability functions. Ensure that the code 
handles these cases gracefully and provides meaningful error messages to the user.

## Test performance: 

Measure the performance of the file transfer, such as throughput and latency, for different file sizes
and network conditions. Compare the performance of each reliability function to determine their efficiency and suitability 
for different scenarios.
