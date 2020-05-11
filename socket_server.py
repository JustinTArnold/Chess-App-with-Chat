import socket
import select
from threading import Thread
from kivy.config import Config
Config.set("graphics", 'resizable', True)

HEADER_LENGTH = 10

IP = "127.0.0.1"
PORT = 1234


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((IP, PORT))
server_socket.listen()
sockets_list = [server_socket]
clients = {}


print(f'Listening for connections on {IP}:{PORT}...')

def get_key(d, value):
    for k, v in d.items():
        if type(v) is dict:
            if get_key(v, value) is not None:
                return k                     
        elif value in str(v):
            return k    
    return None

def receive_message(client_socket):
    try:   
        message_header = client_socket.recv(HEADER_LENGTH)
        if not len(message_header):
            return False
        message_length = int(message_header.decode('utf-8').strip())
        return {'header': message_header, 'data': client_socket.recv(message_length)}
    except:        
        return False

while True:   
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)  
    for notified_socket in read_sockets:      
        if notified_socket == server_socket:         
            client_socket, client_address = server_socket.accept()          
            user = receive_message(client_socket)  
            if user is False:
                continue 
            sockets_list.append(client_socket)
            clients[client_socket] = user
            print('Accepted new connection from {}:{}, username: {}'.format(*client_address, user['data'].decode('utf-8')))
        else: 
            message = receive_message(notified_socket)
            if message is False:
                print('Closed connection from: {}'.format(clients[notified_socket]['data'].decode('utf-8')))
                sockets_list.remove(notified_socket)
                del clients[notified_socket]
                continue
            user = clients[notified_socket]
            inv_message_check = f'{message["data"].decode("utf-8")}'
            inv_user_check = f'{user["data"].decode("utf-8")}'
            if inv_message_check.startswith("/invite"):
                inv_message_check = inv_message_check.split()
                senduser = clients[notified_socket]
                for user in clients:
                    if user == get_key(clients, f"b'{inv_message_check[1]}'"):
                        invite_message = f"You have been invited to a game by {senduser['data'].decode('utf-8')}, use /accept {senduser['data'].decode('utf-8')} to join"
                        user.send(invite_message.encode())
            
            elif inv_message_check.startswith("/accept"):
                inv_message_check = inv_message_check.split()
                senduser = clients[notified_socket]
                for user in clients:
                    if user == get_key(clients, f"b'{inv_message_check[1]}'"):
                        invite_message = f"gamehasbeenacceptedandwillnowbegin<---->{senduser['data'].decode('utf-8')}<---->{inv_message_check[2]}"
                        user.send(invite_message.encode())
            
            elif inv_message_check.startswith("playermoveis"):
                for user in clients:
                    if user != notified_socket:
                        print (inv_message_check)
                        user.send(inv_message_check.encode())
            else:             
                
                print(f'Received message from {user["data"].decode("utf-8")}: {message["data"].decode("utf-8")}')
                
                for client_socket in clients:
                    
                    if client_socket != notified_socket:
                        print (client_socket)
                        client_socket.send(user["data"]+"<---->".encode()+ message["data"])


