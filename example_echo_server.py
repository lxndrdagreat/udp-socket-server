from server import ThreadedUDPServer
import threading


# Create the server instance and assign the binding address for it
server = ThreadedUDPServer(('localhost', 9999))


# Set up a few example event handlers
@server.on('connected')
def connected(msg, socket):
    """ Both 'connected' and 'disconnected' are events
        reserved by the server. It will call them automatically.
    """
    print("New client: {}".format(socket))


@server.on('message')
def got_message(msg, socket):
    """ This is a custom event called "message".
        When a client sends a message event, this handler
        will repeat that message back to all connected clients.
    """
    print("[{}]: {}".format(socket, msg))
    server.send_all('message', msg)


if __name__ == "__main__":
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    while True:
        pass

    server.shutdown()
