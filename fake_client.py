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
# from message import MessageProtocol
from example_game_server import PacketProtocol, PacketId
import random
import threading
import msgpack

ARGS = argparse.ArgumentParser(description="UDP Fake Player")
ARGS.add_argument(
    '--count',
    action="store",
    dest="count",
    default='32',
    help='How many fake players to spawn. Each player is a thread.')

ARGS.add_argument(
    '--speed',
    action="store",
    dest="speed",
    default="1",
    help="How often the AI changes directions."
)

ARGS.add_argument(
    '--host',
    action="store",
    dest="host",
    default="localhost",
    help="Address of server to connect to."
)

ARGS.add_argument(
    '--port',
    action="store",
    dest="port",
    default="9999",
    help="Server port to connect to."
)


def client(mv_speed, host_port):

    # SOCK_DGRAM is the socket type to use for UDP sockets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)

    # message_protocol = MessageProtocol()
    message_protocol = PacketProtocol()

    time_last = time.time()
    movement_timer = 0
    movement_time = mv_speed

    movement = [0, 0]

    welcomed = False

    my_player = None

    try:

        # send first message to the server to tell it we want to join.
        data = message_protocol.create(PacketId.JOIN, "hello, world", 0)
        sock.sendto(data, host_port)

        while True:

            if welcomed and my_player:
                time_now = time.time()
                delta = time_now - time_last
                time_last = time_now

                movement_timer -= delta
                if movement_timer < 0:
                    movement[0] = random.randrange(-1, 2)
                    movement[1] = random.randrange(-1, 2)
                    data = message_protocol.create(PacketId.PLAYER_INPUT, json.dumps(movement), 0)
                    sock.sendto(data, host_port)
                    movement_timer = movement_time

            try:
                message, address = sock.recvfrom(8192)
                if message:
                    parsed = message_protocol.parse(message)
                    message_type = parsed['t']
                    payload = parsed['p']
                    needs_ack = True if parsed['a'] == 1 else False
                    sequence_number = parsed['s']

                    if message_type == PacketId.WELCOME:
                        welcomed = True
                        my_player = json.loads(payload)
                        print("me: {}".format(my_player))

                    if needs_ack:
                        # send Ack
                        data = message_protocol.create(PacketId.ACK, json.dumps([sequence_number]), 0)
                        sock.sendto(data, host_port)
            except:
                pass
                
    except KeyboardInterrupt:
        pass
    finally:

        sock.close()

if __name__ == '__main__':
    args = ARGS.parse_args()

    host_port = (args.host, int(args.port))

    num_clients = int(args.count)
    print("Spawning {} clients.".format(num_clients))
    movement_speed = float(args.speed)
    client_threads = []
    for i in range(0, num_clients):
        print("starting client {}".format(i))
        client_thread = threading.Thread(target=client, args=[movement_speed, host_port])
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

