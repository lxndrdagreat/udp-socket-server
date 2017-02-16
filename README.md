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
