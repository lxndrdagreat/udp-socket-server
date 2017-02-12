# Example Game Server
#
# This is a simple game server for a silly "game".
from server import ThreadedUDPServer
import threading
import uuid
import random
import time
import json

lock = threading.Lock()


class PlayerClient:
    def __init__(self, client_addr):
        self.uuid = uuid.uuid4().hex
        self.color = (
            random.uniform(0.0, 1.0),
            random.uniform(0.0, 1.0),
            random.uniform(0.0, 1.0))
        self.position = [
            random.uniform(-10.0, 10.0),
            random.uniform(-10.0, 10.0)]
        self.rotation = 0.0
        self._client_addr = client_addr

        self.speed = 5
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

class GameServer:
    def __init__(self):
        self._clients = {}
        self._clients_to_remove = []

        self._socket_server = None


    def start(self):
        self._socket_server = ThreadedUDPServer(('localhost', 9999))
        self._socket_server.heartbeat_rate = 10
        # Turn on the socket server's debug log of message sizes:
        # self._socket_server.debug_message_size = True

        # set up handlers
        self._socket_server.on('connected', self.client_connected)
        self._socket_server.on('disconnected', self.client_disconnected)
        self._socket_server.on('player_move', self.player_movement)

        self._server_thread = threading.Thread(target=self._socket_server.serve_forever)
        self._server_thread.daemon = True
        self._server_thread.start()

        # for a fixed update tick
        last_time = time.time()
        loop_time = 1.0 / 60
        loop_timer = 0

        while True:
            time_now = time.time()
            delta = time_now - last_time
            last_time = time_now

            loop_timer += delta
            if loop_timer >= loop_time:

                self.game_loop(loop_timer)
                loop_timer = 0

        self._socket_server.shutdown()


    def game_loop(self, dt):
        updated_players = []

        with lock:
            # remove disconnected players
            for socket in self._clients_to_remove:
                if socket not in self._clients:
                    continue
                player = self._clients[socket]

                # send player_left message to everyone else
                self._socket_server.send_all("player_left", player.uuid)

                del self._clients[socket]

            # loop through players and handle updates
            for socket, player in self._clients.items():
                if player.movement[0] != 0 or player.movement[1] != 0:
                    player.position[0] += player.movement[0] * player.speed * dt
                    player.position[1] += player.movement[1] * player.speed * dt
                    if player.position[0] < -20:
                        player.position[0] = -20
                    elif player.position[0] > 20:
                        player.position[0] = 20 
                    if player.position[1] < -10:
                        player.position[1] = -10
                    elif player.position[1] > 10:
                        player.position[1] = 10
                    updated_players.append(player.as_dict())

        if len(updated_players) > 0:
            # print("sending player updates for {} players".format(len(updated_players)))
            self._socket_server.send_all("players", updated_players)
        
    def client_connected(self, msg, socket):
        """ Both 'connected' and 'disconnected' are events
            reserved by the server. It will call them automatically.
        """
        with lock:
            print("New client: {}".format(socket))
            player = PlayerClient(socket)
            self._clients[socket] = player

            # send welcome
            self._socket_server.send(socket, "welcome", player.as_dict())
    
    def client_disconnected(self, msg, socket):
        print("Player {} has disconnected.".format(socket))
        if socket in self._clients and socket not in self._clients_to_remove:
            self._clients_to_remove.append(socket)

    def player_movement(self, msg, socket):
        if socket not in self._clients:
            return        

        player = self._clients[socket]
        movement = json.loads(msg)
        player.movement = movement

if __name__ == "__main__":    
    
    game = GameServer()
    game.start()
