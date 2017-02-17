# udp-socket-server
A messy, threaded UDP socket server written in Python

## Echo Example

There is an included example that is just an echo server.

Start the server by running `example_echo_server.py`.

Then start as many copies of `example_echo_client.py` as you want.

## Game Example

There is a simple "game" (term used loosely) server example.

Run it via `example_game_server.py`.

### Message Protocol

The MessageProtocol for the example game server uses [msgpack](http://msgpack.org/index.html).

Messages are formatted as follows:

```
{
  "t": int, // The packet's type ID.
  "p": string, // The payload, encoded as a string
  "a": bool, // Is "ack" needed? True/False as a 1 or 0 
  "s": int // packet's sequence number
}
```

## References

- http://unitycode.blogspot.com/2012/04/udp.html
- http://gafferongames.com/networking-for-game-programmers/
- https://www.gamedev.net/topic/328867-udp-with-ack/
- http://fabiensanglard.net/quake3/network.php
- https://developer.valvesoftware.com/wiki/Source_Multiplayer_Networking
- https://www.howtogeek.com/225487/what-is-the-difference-between-127.0.0.1-and-0.0.0.0/

## Known Issues

```
Exception happened during processing of request from ('71.12.73.70', 59414)
New client: ('71.12.73.70', 59414) is now player 106
Traceback (most recent call last):
  File "/usr/lib/python3.5/socketserver.py", line 625, in process_request_thread
    self.finish_request(request, client_address)
  File "/root/udp-socket-server/server.py", line 32, in finish_request
    self.message_received(request[0], socket_address)
  File "/root/udp-socket-server/server.py", line 140, in message_received
    self._trigger(message_type, payload, socket_address)
  File "/root/udp-socket-server/server.py", line 104, in _trigger
    self.handlers[event](data, addr)
  File "example_game_server.py", line 381, in player_movement
    player = self._clients[self._socket_to_player[socket]]
KeyError: 94
```