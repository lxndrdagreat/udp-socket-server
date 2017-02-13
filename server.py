# UDP threaded server
#
# Ctrl+C to kill
#
import socketserver
import socket
import threading
import json
from message import MessageProtocol
import time
import sys

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):

    def __init__(self, server_address, bind_and_activate=True):
        """Constructor.  May be extended, do not override."""
        socketserver.UDPServer.__init__(self, server_address, None, bind_and_activate)

        self._message_protocol = MessageProtocol()

        # remember connected clients
        self.clients = []

        # event handlers
        self.handlers = {}

        # heartbeat rate
        # call clients "dead" if we haven't received anything from them in
        # this amount of time.
        self.heartbeat_rate = 30 # seconds
        self._heartbeats = {}
        self._last_time = time.time()

        # Debug settings
        self.debug_message_size = False
        self.debug_message_unhandled = True

    def service_actions(self):
        """Called by the server_forever() loop"""
        time_now = time.time()
        delta = time_now - self._last_time
        self._last_time = time_now

        # check heartbeats if > 0.
        dead_clients = []
        if self.heartbeat_rate > 0:
            for client in self._heartbeats:
                heart = self._heartbeats[client]
                heart += delta
                if heart > self.heartbeat_rate:
                    # consider this client disconnected
                    # TODO: have a "staging" disconnect state
                    # print("removing dead client: {}".format(client))
                    dead_clients.append(client)
                else:
                    self._heartbeats[client] = heart

        for client in dead_clients:
            # remove from client list
            del self._heartbeats[client]
            self.clients.remove(client)
            # trigger disconnect event
            self._trigger('disconnected', None, client)

    def _trigger(self, event, data, addr):
        if event in self.handlers:
            self.handlers[event](data, addr)
        elif self.debug_message_unhandled:
            print("Unhandled event [{}]. Payload: {}".format(event, data))

    def finish_request(self, request, client_address):
        if client_address not in self.clients:            
            self.clients.append(client_address)
            self._heartbeats[client_address] = 0            
            self._trigger('connected', None, client_address)
        else:
            self._heartbeats[client_address] = 0

        if self.debug_message_size:
            print("[SOCKET INCOMING SIZE] {}".format(sys.getsizeof(request[0])))

        message = self._message_protocol.parse(request[0])
        message_type = message['t']
        payload = message['p']
        self._trigger(message_type, payload, client_address)

    def on(self, event, handler=None):
        def set_handler(handler):
            self.handlers[event] = handler
            return handler

        if handler is None:
            return set_handler
        set_handler(handler)

    def send(self, client, event, payload):
        """Send message to specific client"""
        msg = self._message_protocol.create(event, payload)
        if self.debug_message_size:
            print("[SOCKET OUTGOING SIZE] {}".format(sys.getsizeof(msg)))
        self.socket.sendto(msg, client)

    def send_raw(self, client, payload):
        """Send message to specific client, without using Message Protocol"""
        if self.debug_message_size:
            print("[SOCKET OUTGOING SIZE] {}".format(sys.getsizeof(payload)))
        self.socket.sendto(payload, client)

    def send_all(self, event, payload):
        """Send message to all known clients"""
        for client in self.clients:
            self.send(client, event, payload)    
