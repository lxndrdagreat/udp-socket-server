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

ARGS = argparse.ArgumentParser(description="UDP Echo Client Example")
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


def client(mv_speed):
    HOST, PORT = "localhost", 9999

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
        sock.sendto(data, (HOST, PORT))

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
                    sock.sendto(data, (HOST, PORT))
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
                        sock.sendto(data, (HOST, PORT))
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
    movement_speed = float(args.speed)
    client_threads = []
    for i in range(0, num_clients):
        print("starting client {}".format(i))
        client_thread = threading.Thread(target=client, args=[movement_speed])
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

