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
    PLAYER_FIRE = 21
    WORLD_INFO = 30
    BULLETS = 35


class PacketProtocol(MessageProtocol):
    def create(self, msg_type, payload, sequence_number=0, needs_ack=False):
        message = {
            "t": msg_type.value,
            "p": payload,
            "s": sequence_number,
            "a": 1 if needs_ack else 0
        }
        packed = msgpack.packb(message)
        return packed

    def parse(self, message):        
        unpacked = msgpack.unpackb(message, encoding='utf-8')
        # print(unpacked)
        unpacked['t'] = PacketId(int(unpacked['t']))
        return unpacked


class PlayerClient:
    """ Server-side representation of every connected player. """
    def __init__(self, player_id, client_addr):
        self.uuid = player_id
        self.color = (
            random.uniform(0.0, 1.0),
            random.uniform(0.0, 1.0),
            random.uniform(0.0, 1.0))
        self.position = [
            random.uniform(-10.0, 10.0),
            random.uniform(-10.0, 10.0)]
        self.address = client_addr

        self.speed = 5

        # Player's current input, stored as <x> and <y> deltas
        self.movement = [0, 0]

        # which direction is the player "facing" 
        # (aka, which way did he move last)
        self.facing = [1, 0]

    def set_movement(self, move):
        self.movement = move
        if move[0] != 0 or move[1] != 0:
            self.facing = move

    def as_dict(self):
        """ This is the information about the player that gets sent around
            to everyone.

            Color, position and rotation data are transformed from floats to
            integers for passing. This loses an acceptable degree of accuracy.
        """
        data = {
            "uuid": self.uuid,
            "colorRed": int(self.color[0] * 255),
            "colorGreen": int(self.color[1] * 255),
            "colorBlue": int(self.color[2] * 255),
            "position": (int(self.position[0] * 1000), int(self.position[1] * 1000))
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


class World:
    """ Server-side representation of the game world. """
    def __init__(self, size=(20, 10)):
        # size of the world, in "units"
        self.width = size[0]
        self.height = size[1]

    def as_dict(self):
        return {
            "width": self.width,
            "height": self.height
        }


class Bullet:
    """ Server-side representation of a bullet object. """
    def __init__(self, pos, direct, created_by):
        self.position = pos
        self.direction = direct
        self.speed = 8
        self.owner = created_by
        self.lifetime = 2.0

    def as_dict(self):
        return {
            "position": [self.position[0] * 1000, self.position[1] * 1000],
            "rotation": self.rotation * 1000
        }


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

        # game state stuff
        self._world = World()
        self._bullets = []

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
        self._socket_server.on(PacketId.PLAYER_FIRE, self.player_fire)

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
                
        msg_bytes = self.protocol.create(event, payload, seq_num, needs_ack)

        if needs_ack:
            info = PacketInfo(seq_num, time.time(), player_id, event, payload)
            print("new ACK for {} at time: {}".format(seq_num, info.sent_ticks))
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

        # update bullets
        dead_bullets = []
        bullet_update = []
        for bullet in self._bullets:
            bullet.lifetime -= dt
            if bullet.lifetime <= 0:
                dead_bullets.append(bullet)
                continue
            bullet.position[0] += bullet.direction[0] * bullet.speed * dt
            bullet.position[1] += bullet.direction[1] * bullet.speed * dt            
            bullet_update.append(bullet.as_dict())

        # remove dead bullets
        for bullet in dead_bullets:
            self._bullets.remove(bullet)

        # send bullet updates if some were updated or removed
        if len(bullet_update) > 0 or len(dead_bullets) > 0:
            self.send_all(PacketId.BULLETS, bullet_update)

        with lock:
            # loop through the Acks queue to see if we need to send more acks
            if len(self._ack_needed):
                resend_acks = []
                while len(self._ack_needed) > 0:
                    ack = self._ack_needed[0]
                    since = time.time() - ack.sent_ticks
                    if since >= 2:
                        # resend and requeue
                        # print("ACK needed for {}".format(ack.sequence_number))
                        resend_acks.append(self._ack_needed.pop())
                    else:
                        # hit a young pack, quit for now
                        # oldest packs will be at the front
                        break

                for ack in resend_acks:
                    self.send(ack.target, ack.event, ack.payload, True, ack.sequence_number)
    
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
            print(player.as_dict())
            self.send(player.uuid, PacketId.WELCOME, json.dumps(player.as_dict()), True)

            # send world, require acknowledge
            self.send(player.uuid, PacketId.WORLD_INFO, json.dumps(self._world.as_dict()), True)
    
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
        print("Got player input for {}: {}".format(player.uuid, movement))
        player.set_movement(movement)

    def player_fire(self, msg, socket):
        if socket not in self._socket_to_player:
            return

        player = self._clients[self._socket_to_player[socket]]
        
        # create bullet
        bullet = Bullet(player.position, player.facing, player.uuid)
        self._bullets.append(bullet)

    def received_ack(self, msg, socket):
        if socket not in self._socket_to_player:
            return
        acks = json.loads(msg)
        for ack in acks:
            ackInfo = next((a for a in self._ack_needed if a.sequence_number == ack), None)
            if ackInfo:
                print("ack received: {}".format(ackInfo.sequence_number))
                self._ack_needed.remove(ackInfo)                

if __name__ == "__main__":    
    
    game = GameServer()
    game.start()
