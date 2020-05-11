import socket
import errno
from threading import Thread
from kivy.config import Config
Config.set("graphics", 'resizable', True)

HEADER_LENGTH = 10
client_socket = None

def connect(ip, port, my_username, error_callback):
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((ip, port))
    except Exception as e:
        error_callback('Connection error: {}'.format(str(e)))
        return False
    username = my_username.encode('utf-8')
    username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(username_header + username)
    return True

def send(message):
    message = message.encode('utf-8')
    message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(message_header + message)

def start_listening(incoming_message_callback, error_callback):
    Thread(target=listen, args=(incoming_message_callback, error_callback), daemon=True).start()

def listen(incoming_message_callback, error_callback):
    while True:
        try:
            while True:
                data = client_socket.recv(1024).decode()
                if data.startswith("You have been"):
                    incoming_message_callback("admin", data)
                elif data.startswith("gamehasbeenacceptedandwillnowbegin"):
                    game = data.split("<---->")
                    incoming_message_callback("acceptedgame", game)
                elif data.startswish("playermoveis"):
                    incoming_message_callback("playermoveis", data)
                else:
                    mess = data.split("<---->")
                    incoming_message_callback(mess[0],mess[1])
        except Exception as e:
            pass