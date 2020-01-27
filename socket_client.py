import socket
import errno
from threading import Thread
from kivy.config import Config
Config.set("graphics", 'resizable', True)

HEADER_LENGTH = 10
client_socket = None

# Connects to the server


def connect(ip, port, my_username, error_callback):

    global client_socket

    # Create a socket
    # socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
    # socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to a given ip and port
        client_socket.connect((ip, port))
    except Exception as e:
        # Connection error
        error_callback('Connection error: {}'.format(str(e)))
        return False

    # Prepare username and header and send them
    # We need to encode username to bytes, then count number of bytes and prepare header of fixed size, that we encode to bytes as well
    username = my_username.encode('utf-8')
    username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(username_header + username)

    return True

# Sends a message to the server
def send(message):
    # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
    message = message.encode('utf-8')
    message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(message_header + message)

# Starts listening function in a thread
# incoming_message_callback - callback to be called when new message arrives
# error_callback - callback to be called on error
def start_listening(incoming_message_callback, error_callback):
    Thread(target=listen, args=(incoming_message_callback, error_callback), daemon=True).start()

# Listens for incoming messages
def listen(incoming_message_callback, error_callback):
    while True:

        try:
            # Now we want to loop over received messages (there might be more than one) and print them
            while True:

                data = client_socket.recv(1024).decode()
                if data.startswith("You have been"):
                    incoming_message_callback("admin", data)

                elif data.startswith("gamehasbeenacceptedandwillnowbegin"):
                    game = data.split("<---->")
                    incoming_message_callback("acceptedgame", game)
                
                elif data.startswish("playermoveis"):
                    incoming_message_callback("playermoveis", data)
                # Receive our "header" containing username length, it's size is defined and constant
                else:
                    mess = data.split("<---->")
                    incoming_message_callback(mess[0],mess[1])

        except Exception as e:
            pass
            #error_callback('Reading error: {}'.format(str(e)))