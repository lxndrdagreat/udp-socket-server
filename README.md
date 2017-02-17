# udp-socket-server
A messy, threaded UDP socket server written in Python

## Echo Example

There is an included example that is just an echo server.

Start the server by running `example_echo_server.py`.

Then start as many copies of `example_echo_client.py` as you want.

## Game Example

There is a simple "game" (term used loosely) server example.

### The Server

Run it via `example_game_server.py`.

### Stress Testing Player Connections

The Python script `fake_client.py` is a threaded application that creates `n`
 clients and has them connect to the server and spam movement commands.
 
 Run it like so:
 
 ```commandline
usage: fake_client.py [-h] [--count COUNT] [--speed SPEED] [--host HOST]
                      [--port PORT]

UDP Fake Player

optional arguments:
  -h, --help     show this help message and exit
  --count COUNT  How many fake players to spawn. Each player is a thread.
  --speed SPEED  How often the AI changes directions.
  --host HOST    Address of server to connect to. Default is 'localhost'.
  --port PORT    Server port to connect to. Defaults to 9999.
```

### Player Client

There is another learning project, built with Unity and C#, that is a player client.
Check it out [at its github](https://github.com/lxndrdagreat/udp-unity-tests).

### Message Protocol

The MessageProtocol for the example game server uses [msgpack](http://msgpack.org/index.html).

Messages are created as a list, formatted as follows:

```
[
    Packet ID (integer),
    Sequence Number (integer),
    Needs "ack" (bool, 0 or 1),
    payload (technically could be anything)
]
```

That message is then fed through `msgpack` which returns bytes, which are sent out.

## References

- http://unitycode.blogspot.com/2012/04/udp.html
- http://gafferongames.com/networking-for-game-programmers/
- https://www.gamedev.net/topic/328867-udp-with-ack/
- http://fabiensanglard.net/quake3/network.php
- https://developer.valvesoftware.com/wiki/Source_Multiplayer_Networking
- https://www.howtogeek.com/225487/what-is-the-difference-between-127.0.0.1-and-0.0.0.0/

## Known Issues

```
Traceback (most recent call last):
  File "example_game_server.py", line 381, in player_movement
    player = self._clients[self._socket_to_player[socket]]
KeyError: 94
```
