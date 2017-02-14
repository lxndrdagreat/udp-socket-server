# Example Game Server
#
# This is a simple game server for a silly "game".
# from server import ThreadedUDPServer
from server import EventServer
import threading
import random
import time
import json
from message import MessageProtocol
from enum import Enum
import msgpack
import sys

lock = threading.Lock()


class PacketId(Enum):
    JOIN = 0
    WELCOME = 1
    ACK = 2
    PLAYER_INFO = 10
    PLAYER_UPDATES = 11
    PLAYER_LEFT = 12
    PLAYER_INPUT = 20    


class PacketProtocol(MessageProtocol):
    def create(self, msg_type, payload, sequence_number=None):
        message = {
            "t": msg_type.value,
            "p": payload
        }
        if sequence_number is not None:
            message['s'] = sequence_number
        # print("[CREATED] {}".format(message))
        packed = msgpack.packb(message)
        return packed

    def parse(self, message):        
        unpacked = msgpack.unpackb(message, encoding='utf-8')
        unpacked['t'] = PacketId(int(unpacked['t']))
        # print("[PARSED] {}".format(unpacked))
        return unpacked


class PlayerClient:
    def __init__(self, player_id, client_addr):
        self.uuid = player_id
        self.color = (
            random.uniform(0.0, 1.0),
            random.uniform(0.0, 1.0),
            random.uniform(0.0, 1.0))
        self.position = [
            random.uniform(-10.0, 10.0),
            random.uniform(-10.0, 10.0)]
        self.rotation = 0.0
        self.address = client_addr

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


class PacketInfo:
    def __init__(self, seq_number, sent_at, target, event, payload):        
        self.sent_ticks = sent_at
        self.sequence_number = seq_number
        # id of the target player
        self.target = target
        # this is so we can send it again if needed
        self.payload = payload
        self.event = event


class GameServer:
    def __init__(self):
        self._clients = {}
        self._socket_to_player = {}
        self._clients_to_remove = []
        self._player_id_number = 0

        self._socket_server = None
        self._server_thread = None

        self._sequence_number = 0
        self._max_sequence_number = 10000
        self._ack_needed = []

        self.protocol = PacketProtocol()

    def start(self):
        self._socket_server = EventServer(('localhost', 9999))        
        self._socket_server.heartbeat_rate = 10
        self._socket_server._message_protocol = PacketProtocol()
        # Turn on the socket server's debug log of message sizes:
        # self._socket_server.debug_message_size = True

        # set up handlers
        self._socket_server.on('connected', self.client_connected)
        self._socket_server.on('disconnected', self.client_disconnected)
        self._socket_server.on(PacketId.PLAYER_INPUT, self.player_movement)
        self._socket_server.on(PacketId.ACK, self.received_ack)

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

    def next_player_id(self):
        self._player_id_number += 1
        return self._player_id_number

    def next_sequence_number(self):
        this_seq = self._sequence_number
        if self._sequence_number < self._max_sequence_number:
            self._sequence_number += 1
        else:
            print("SEQUENCE NUMBER LOOPED")
            self._sequence_number = 0
        return this_seq

    def send(self, player_id, event, payload, needs_ack=False, seq_num=None):
        if player_id not in self._clients:
            return

        if not seq_num:
            seq_num = self.next_sequence_number()

        player = self._clients[player_id]
        player_addr = player.address
                
        msg_bytes = self.protocol.create(event, payload, seq_num)        

        if needs_ack:
            info = PacketInfo(seq_num, time.time(), player_id, event, payload)
            self._ack_needed.append(info)

        self._socket_server.sendto(player_addr, msg_bytes)

    def send_all(self, event, payload, needs_ack=False):
        """Sends the message to all active players."""
        for player_id, player in self._clients.items():
            self.send(player_id, event, payload, needs_ack)

    def game_loop(self, dt):
        updated_players = []

        with lock:
            # remove disconnected players
            for player_id in self._clients_to_remove:
                if player_id not in self._clients:
                    continue
                player = self._clients[player_id]

                # send player_left message to everyone else
                self.send_all(PacketId.PLAYER_LEFT, player.uuid)

                del self._clients[player_id]

            # loop through players and handle updates
            for player_id, player in self._clients.items():
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
            self.send_all(PacketId.PLAYER_UPDATES, updated_players)

        # loop through the Acks queue to see if we need to send more acks
        if len(self._ack_needed):
            while len(self._ack_needed) > 0:
                ack = self._ack_needed[0]
                since = time.time() - ack.sent_ticks
                if since > 2:
                    # resend and requeue
                    self._ack_needed.pop()
                    print("ACK needed for {}".format(ack.sequence_number))
                    self.send(ack.target, ack.event, ack.payload, True, ack.sequence_number)
                else:
                    # hit a young pack, quit for now
                    # oldest packs will be at the front
                    break
    
    def sequence_more_recent(self, s1, s2):
        return (s1 > s2 and s1 - s2 <= self._max_sequence_number / 2) or (s2 > s1 and s2 - s1 > self._max_sequence_number/2)

    def client_connected(self, msg, socket):
        """ Both 'connected' and 'disconnected' are events
            reserved by the server. It will call them automatically.
        """
        with lock:            
            player = PlayerClient(self.next_player_id(), socket)
            print("New client: {} is now player {}".format(socket, player.uuid))
            self._clients[player.uuid] = player
            self._socket_to_player[socket] = player.uuid

            # send welcome
            self.send(player.uuid, PacketId.WELCOME, json.dumps(player.as_dict()), True)
    
    def client_disconnected(self, msg, socket):
        player = self._clients[self._socket_to_player[socket]]
        print("Player {} has disconnected.".format(player.uuid))
        if player.uuid in self._clients and player.uuid not in self._clients_to_remove:
            self._clients_to_remove.append(player.uuid)

    def player_movement(self, msg, socket):
        if socket not in self._socket_to_player:
            return        

        player = self._clients[self._socket_to_player[socket]]
        movement = json.loads(msg)
        player.movement = movement

    def received_ack(self, msg, socket):
        if socket not in self._socket_to_player:
            return
        acks = json.loads(msg)
        for ack in acks:
            ackInfo = next((a for a in self._ack_needed if a.sequence_number == ack), None)
            if ackInfo:
                self._ack_needed.remove(ackInfo)                

if __name__ == "__main__":    
    
    game = GameServer()
    game.start()
