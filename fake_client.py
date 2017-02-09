# fake client
#
# Connects to example game server and pretends to be a player moving around.
# Goal is to stress the server.
#
# Ctrl+C to kill
#
import socket
import sys
import time
import json
import argparse
from message import MessageProtocol
import random
import threading

ARGS = argparse.ArgumentParser(description="UDP Echo Client Example")
ARGS.add_argument(
    '--count', action="store", dest="count", default='5', help='How many fake players to spawn. Each player is a thread.')

def client():
    HOST, PORT = "localhost", 9999

    # SOCK_DGRAM is the socket type to use for UDP sockets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)

    message_protocol = MessageProtocol()

    time_last = time.time()
    movement_timer = 0
    movement_time = 2
    count = 0

    movement = [0, 0]

    welcomed = False

    my_player = None

    try:

        data = message_protocol.create("message", "hello, world")
        sock.sendto(data, (HOST, PORT))

        while True:

            if welcomed and my_player:
                time_now = time.time()
                delta = time_now - time_last
                time_last = time_now

                movement_timer -= delta
                if movement_timer < 0:
                    movement[0] = random.randrange(-1, 1)
                    movement[1] = random.randrange(-1, 1)
                    data = message_protocol.create("player_move", movement)
                    sock.sendto(data, (HOST, PORT))
                    movement_timer = movement_time

            try:
                message, address = sock.recvfrom(8192)
                if message:
                    message_type, payload = message_protocol.parse(message)

                    if message_type == 'welcome':
                        welcomed = True
                        my_player = json.loads(payload)
                        print("me: {}".format(my_player))
            except:
                pass
                
    except KeyboardInterrupt:
        pass
    finally:

        sock.close()

if __name__ == '__main__':
    args = ARGS.parse_args()

    num_clients = int(args.count)
    print("Spawning {} clients.".format(num_clients))
    client_threads = []
    for i in range(0, num_clients):
        print("starting client {}".format(i))
        client_thread = threading.Thread(target=client)
        client_thread.daemon = True
        client_thread.start()
        client_threads.append(client_thread)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        # close everything down
        pass

