# example_echo_client.py
#
# This spams one message, over and over again, to a server.
# It also handles responses from the server.
#
# Ctrl+C to kill
#
import socket
import sys
import time
import json
import argparse
from message import MessageProtocol

ARGS = argparse.ArgumentParser(description="UDP Echo Client Example")
ARGS.add_argument(
    '--wait', action="store", dest="wait", default='1', help='How long to wait inbetween sending messages.')

if __name__ == '__main__':
    args = ARGS.parse_args()

    HOST, PORT = "localhost", 9999

    # SOCK_DGRAM is the socket type to use for UDP sockets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)

    message_protocol = MessageProtocol()

    time_last = time.time()
    send_timer = 0
    send_timer_amount = int(args.wait)
    count = 0

    try:
        while True:

            # this will send a message to the server periodically
            time_now = time.time()
            delta = time_now - time_last
            time_last = time_now        
            send_timer -= delta
            if send_timer <= 0:
                data = message_protocol.create("message", "hello, world {}".format(count))
                count += 1
                sock.sendto(data, (HOST, PORT))
                send_timer = send_timer_amount

            try:
                message, address = sock.recvfrom(8192)
                if message:
                    print(message)
            except:
                pass
                
    except KeyboardInterrupt:
        pass
    finally:

        sock.close()
