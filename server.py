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

        # Debug settings
        self.debug_message_size = False

    def service_actions(self):
        """Called by the server_forever() loop"""
        pass

    def finish_request(self, request, socket_address):

        if self.debug_message_size:
            print("[SOCKET INCOMING SIZE] {}".format(sys.getsizeof(request[0])))

        self.message_received(request[0], socket_address)

    def send(self, address, data):
        """Send data to specific address"""
        if self.debug_message_size:
            print("[SOCKET OUTGOING SIZE] {}".format(sys.getsizeof(data)))
        self.socket.sendto(data, address)

    def send_raw(self, client, payload):
        """Send message to specific client, without using Message Protocol"""
        if self.debug_message_size:
            print("[SOCKET OUTGOING SIZE] {}".format(sys.getsizeof(payload)))
        self.socket.sendto(payload, client)

    def send_all(self, event, payload):
        """Send message to all known clients"""
        for client in self.clients:
            self.send(client, event, payload)

    def message_received(self, data, socket_address):
        """ This is called when we receive data. Override this. """
        pass


class EventServer(ThreadedUDPServer):
    """ EventServer

        Builds off of the ThreadedUDPServer to add an "event message" system.
    """
    def __init__(self, server_address, bind_and_activate=True):
        ThreadedUDPServer.__init__(self, server_address, bind_and_activate)

        # remember connected clients
        self.clients = []

        # heartbeat rate
        # call clients "dead" if we haven't received anything from them in
        # this amount of time.
        self.heartbeat_rate = 30 # seconds
        self._heartbeats = {}
        self._last_time = time.time()

        # event handlers
        self.handlers = {}

        # In order to call events based on message types, we need a protocol.
        # This protocol needs to be followed by the server and the clients.
        self._message_protocol = MessageProtocol()

        # Debug settings
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

    def on(self, event, handler=None):
        """ Used to register a function/method to handle a particular message """
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
        super(EventServer, self).send(client, msg)

    def message_received(self, data, socket_address):
        if socket_address not in self.clients:            
            self.clients.append(socket_address)
            self._heartbeats[socket_address] = 0            
            self._trigger('connected', None, socket_address)
        else:
            self._heartbeats[socket_address] = 0
        message = self._message_protocol.parse(data)
        message_type = message['t']
        payload = message['p']
        self._trigger(message_type, payload, socket_address)