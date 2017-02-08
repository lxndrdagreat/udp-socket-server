# Example Game Server
#
# This is a simple game server for a silly "game".
from server import ThreadedUDPServer
import threading
import uuid
import random
import time
import json

class PlayerClient():
    def __init__(self, client_addr):
        self.uuid = uuid.uuid4().hex
        self.color = (random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.uniform(0.0, 1.0))
        self.position = [0.0, 0.0]
        self.rotation = 0.0
        self._client_addr = client_addr

        self.speed = 1
        self.movement = [0, 0]

    def as_dict(self):
        data = {
            "uuid": self.uuid,
            "colorRed": self.color[0],
            "colorGreen": self.color[1],
            "colorBlue": self.color[2],
            "position": self.position,
            "rotation": self.rotation
        }
        return data


CONNECTED_CLIENTS = {}

# Create the server instance and assign the binding address for it
udp_server = ThreadedUDPServer(('localhost', 9999))


# Set up a few example event handlers
@udp_server.on('connected')
def connected(msg, socket):
    """ Both 'connected' and 'disconnected' are events
        reserved by the server. It will call them automatically.
    """
    print("New client: {}".format(socket))
    player = PlayerClient(socket)
    CONNECTED_CLIENTS[socket] = player

    # send welcome
    udp_server.send(socket, "welcome", player.as_dict())


@udp_server.on('disconnected')
def disconnected(msg, socket):
    if socket in CONNECTED_CLIENTS:
        player = CONNECTED_CLIENTS[socket]

        # send player_left message to everyone else
        udp_server.send_all("player_left", player.uuid)

        del CONNECTED_CLIENTS[socket]
        

@udp_server.on('message')
def got_message(msg, socket):
    """ This is a custom event called "message".
        When a client sends a message event, this handler
        will repeat that message back to all connected clients.
    """
    print("[{}]: {}".format(socket, msg))


@udp_server.on('player_move')
def player_movement(msg, socket):
    if socket not in CONNECTED_CLIENTS:
        return

    print("PLAYER MOVE: {}".format(msg))

    player = CONNECTED_CLIENTS[socket]
    movement = json.loads(msg)
    player.movement = movement


def game_loop(delta):

    updated_players = []

    for socket, player in CONNECTED_CLIENTS.items():
        if player.movement[0] != 0 or player.movement[1] != 0:
            player.position[0] += player.movement[0] * player.speed * delta
            player.position[1] += player.movement[1] * player.speed * delta
            updated_players.append(player.as_dict())


    if len(updated_players) > 0:
        # print("sending player updates for {} players".format(len(updated_players)))
        udp_server.send_all("players", updated_players)

    # spam test
    #udp_server.send_all("message", "hello!")

if __name__ == "__main__":    
    last_time = time.time()

    server_thread = threading.Thread(target=udp_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    loop_time = 1.0 / 60
    loop_timer = 0

    while True:
        time_now = time.time()
        delta = time_now - last_time
        last_time = time_now

        loop_timer += delta
        if loop_timer >= loop_time:

            game_loop(loop_timer)
            loop_timer = 0

    udp_server.shutdown()
