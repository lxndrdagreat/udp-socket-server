# Example Game Server
#
# This is a simple game server for a silly "game".
from server import ThreadedUDPServer
import threading
import uuid

class PlayerClient():
    def __init__(self, client_addr):
        self.uuid = uuid.uuid4().hex
        self.color = (1.0, 0, 0)
        self.position = (0.0, 0.0)
        self.rotation = 0.0
        self._client_addr = client_addr

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
server = ThreadedUDPServer(('localhost', 9999))


# Set up a few example event handlers
@server.on('connected')
def connected(msg, socket):
    """ Both 'connected' and 'disconnected' are events
        reserved by the server. It will call them automatically.
    """
    print("New client: {}".format(socket))
    player = PlayerClient(socket)
    CONNECTED_CLIENTS[socket] = player

    # send welcome
    server.send(socket, "welcome", player.as_dict())


@server.on('message')
def got_message(msg, socket):
    """ This is a custom event called "message".
        When a client sends a message event, this handler
        will repeat that message back to all connected clients.
    """
    print("[{}]: {}".format(socket, msg))


if __name__ == "__main__":
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    while True:
        pass

    server.shutdown()
