from typing import List
from tkinter.colorchooser import askcolor
import tkinter as tk
import threading
import sys
import random
#from network import Network


from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition, WipeTransition
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

import socket_client
from configurations import NUMBER_OF_ROWS, NUMBER_OF_COLUMNS, DIMENSION_OF_EACH_SQUARE
from controller import Controller
from exceptions import ChessError


CONFIG_FNAME = 'store.json'
gameid = ""

def run_in_thread(fn):
    def run(*k, **kw):
        t = threading.Thread(target=fn, args=k, kwargs=kw)
        t.start()
        return t
    return run


class Tile(Widget):
    # The piece image
    img = StringProperty()

    # The tile coords
    coords = ListProperty([None, None])

    # The background color
    bg_color = ListProperty([0, 0, 0])

    # The color that will be used for the move highlights
    highlight_color = ListProperty([0, 0, 0])

    # Whether the tile shoudl currently be highlighted or not
    highlighted = BooleanProperty(False)

    def on_touch_down(self, touch):
        # Called when we press a mouse button

        # By this if we ensure that we call the following function
        # only when we touch this particular instance of the widget
        if self.collide_point(*touch.pos):
            App.get_running_app().chess_app.clicked_square(*self.coords)


class AboutPopup(Popup):
    pass


class PreferencesPopup(Popup):
    @run_in_thread
    def _pick_dark_color(self):
        App.get_running_app().chess_app._board_color_1 = self._askcolor()

    @run_in_thread
    def _pick_light_color(self):
        App.get_running_app().chess_app._board_color_2 = self._askcolor()

    @run_in_thread
    def _pick_highlight_color(self):
        App.get_running_app().chess_app._highlight_color = self._askcolor()

    def _askcolor(self):
        """ Opens the tkinter color picker and returns the color
        in a RG tuple. """

        # Create the root window
        w = tk.Tk()

        # Make the window invisible
        w.attributes('-alpha', 0)     # Windows
        w.wait_visibility()           # Linux
        w.wm_attributes('-alpha', 0)

        # Open the color picker and wait for it to return a color
        color = askcolor()

        # Destroy the root window
        w.destroy()

        return map(lambda x: x / 255, color[0])


class Root(BoxLayout):
    controller: Controller

    # The text of the information label
    _status_text = StringProperty()

    # A table of the tiles
    _tiles: List[List[Tile]]

    # Colors
    _board_color_1 = ListProperty()
    _board_color_2 = ListProperty()
    _highlight_color = ListProperty([0, 0, 0])

    # The position of the currently selected piece to move
    _selected_pos = None

    def __init__(self, **kw):
        self.controller = Controller()
        self._tiles = []

        super().__init__(**kw)

    def on_kv_post(self, _):
        """ Called when the app widgets have been loaded. """

        # Create rows
        self._tiles = [[] for _ in range(NUMBER_OF_COLUMNS)]

        # Fill the rows with tiles
        for y, row in enumerate(self._tiles):
            for x in range(NUMBER_OF_COLUMNS):
                # We need to make reverse the y coordinate such as
                # 0 is at the bottom
                row.append(Tile(coords=[x, NUMBER_OF_ROWS - y - 1]))

        # Draw the tiles onto the screen
        for tile in self.all_tiles:
            self.ids.grid.add_widget(tile)

        # Reverse the rows
        self._tiles.reverse()

        # Start game
        self._start_new_game()

    @property
    def all_tiles(self) -> List[Tile]:
        """ Get the tiles in a flattened list. """
        return [item for sublist in self._tiles for item in sublist]

    # Color updating
    def on__board_color_1(self, *_):
        self._reload_colors()

    def on__board_color_2(self, *_):
        self._reload_colors()

    def on__highlight_color(self, *_):
        self._reload_colors()

    def _reload_colors(self):
        """ Update the color of each tile. Used when manipulating with
        the preferences. """

        for tile in self.ids.grid.children:
            tile.bg_color = self._board_color_1 if (
                sum(tile.coords) % 2) else self._board_color_2
            tile.highlight_color = self._highlight_color

    def _start_new_game(self):
        """ Start a new game. """
        self._status_text = 'White to start'
        self.controller.reset_game_data()
        self.controller.reset_to_initial_locations()
        self.redraw()
    
    def back_to_chat(self):
    	chat_app.screen_manager.current = 'Chat'

    def redraw(self):
        """ Update the GUI from the controller data. """

        # Delete all images
        for tile in self.all_tiles:
            tile.img = ''

        # Redraw images
        for pos, piece in self.controller.get_all_peices_on_chess_board():
            x, y = self.controller.get_numeric_notation(pos)
            filename = f'pieces_image/{piece.name.lower()}_{piece.color}.png'
            self._tiles[x][y].img = filename

    def clicked_square(self, x, y):
        click_pos = self.controller.get_alphanumeric_position((y, x))
        global gameid
        # In case the user has selected a piece before
        if self._selected_pos:
            message = ("playermoveis<---->"+self._selected_pos+"<---->"+click_pos+"<---->"+gameid)
            socket_client.send(message)
            self.shift(self._selected_pos, click_pos)
            self._unhighlight()
            self._selected_pos = None
            print (message)


        # In case we the user is selecting a piece to move
        else:
            piece = self.controller.get_piece_at(click_pos)

            if not piece or piece.color != self.controller.player_turn():
                return

            self._highlight_available_moves(piece, click_pos)
            self._selected_pos = click_pos

    def shift(self, from_, to):
        piece_src = self.controller.get_piece_at(from_)

        try:
            self.controller.pre_move_validation(from_, to)
        except ChessError as ex:
            self._status_text = ex.__class__.__name__
            return

        # Update the src and the dst tiles
        src_y, src_x = self.controller.get_numeric_notation(from_)
        dst_y, dst_x = self.controller.get_numeric_notation(to)
        self._tiles[src_y][src_x].img = ''
        self._tiles[dst_y][dst_x].img = f'pieces_image/{piece_src.name.lower()}_{piece_src.color}.png'

        # Update label
        _next_player = ("white" if piece_src.color ==
                        "black" else "black").capitalize()
        self._status_text = (
            f'{piece_src.color.capitalize()}: {to}, {_next_player}' + "'s turn")

    def _highlight_available_moves(self, piece, pos):
        """ Highlight the tiles based on the clicked position. """
        for coords in piece.moves_available(pos):
            x, y = self.controller.get_numeric_notation(coords)
            self._tiles[x][y].highlighted = True

    def _unhighlight(self):
        for tile in self.all_tiles:
            tile.highlighted = False


class ChatPage(GridLayout, Screen):
    opponet = ""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 2

        self.history = ScrollableLabel(height=Window.size[1] * 0.9, size_hint_y=None)
        self.add_widget(self.history)

        self.new_message = TextInput(width=Window.size[0] * 0.8, size_hint_x=None, multiline=False)
        self.send = Button(text="Send")
        self.send.bind(on_press=self.send_message)

        bottom_line = GridLayout(cols=2)
        bottom_line.add_widget(self.new_message)
        bottom_line.add_widget(self.send)
        self.add_widget(bottom_line)

        Window.bind(on_key_down=self.on_key_down)

        Clock.schedule_once(self.focus_text_input, 1)
        socket_client.start_listening(self.incoming_message, show_error)
        self.bind(size=self.adjust_fields)

        # Updates page layout
    def adjust_fields(self, *_):

        # Chat history height - 90%, but at least 50px for bottom new message/send button part
        if Window.size[1] * 0.1 < 50:
            new_height = Window.size[1] - 50
        else:
            new_height = Window.size[1] * 0.9
        self.history.height = new_height

        # New message input width - 80%, but at least 160px for send button
        if Window.size[0] * 0.2 < 160:
            new_width = Window.size[0] - 160
        else:
            new_width = Window.size[0] * 0.8
        self.new_message.width = new_width

        # Update chat history layout
        #self.history.update_chat_history_layout()
        Clock.schedule_once(self.history.update_chat_history_layout, 0.1)

    def accept(self):
        chat_app.screen_manager.current = 'chess'
    def on_key_down(self, instance, keyboard, keycode, text, modifiers):
        if keycode == 40:
            self.send_message(None)

    def send_message(self, _):
        message = self.new_message.text
        global gameid
        self.new_message.text = ""
        if message.startswith("/invite"):
            socket_client.send(message)
        if message.startswith("/accept"):
            self.accept()
            message = message+" "+str(random.randint(11111,99999))
            socket_client.send(message)
            op = message.split()
            gameid = op[2]

        else:
            self.history.update_chat_history(f"[color=dd2020]{chat_app.connect_page.username.text}[/color] > {message}")
            socket_client.send(message)

        Clock.schedule_once(self.focus_text_input, 0.1)

    def focus_text_input(self, _):
        self.new_message.focus = True

    def incoming_message(self, username, message):
        global gameid
        if username == "admin":
        	self.history.update_chat_history(f"[color=00fdff]{message}[/color]")
        elif username == "acceptedgame":
            chat_app.screen_manager.current = 'chess'
            gameid = message[2]
            print (gameid)

        elif username == "playermoveis":
        	message = message.split("<---->")
        	print (message)
        	if message[3] == gameid:
        		root.shift(message[1], message[2])

        else:
        	self.history.update_chat_history(f"[color=20dd20]{username}[/color] > {message}")

class ScrollableLabel(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = GridLayout(cols=1, size_hint_y=None)
        self.add_widget(self.layout)

        self.chat_history = Label(size_hint_y=None, markup=True)
        self.scroll_to_point = Label()

        self.layout.add_widget(self.chat_history)
        self.layout.add_widget(self.scroll_to_point)

    def update_chat_history(self, message):
        self.chat_history.text += '\n' + message

        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

        self.scroll_to(self.scroll_to_point)

    def update_chat_history_layout(self, _=None):
        # Set layout height to whatever height of chat history text is + 15 pixels
        # (adds a bit of space at the bottom)
        # Set chat history label to whatever height of chat history text is
        # Set width of chat history text to 98 of the label width (adds small margins)
        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

def show_error(message):
    chat_app.info_page.update_info(message)
    chat_app.screen_manager.current = 'Info'
    Clock.schedule_once(sys.exit, 10)

class ConnectPage(GridLayout, Screen):
    # runs on initialization
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2  # used for our grid

        with open("prev_details.txt", "r") as f:
            d = f.read().split(",")
            prev_ip = d[0]
            prev_port = d[1]
            prev_username = d[2]

        self.add_widget(Label(text='IP:'))  # widget #1, top left
        self.ip = TextInput(text=prev_ip, multiline=False)  # defining self.ip...
        self.add_widget(self.ip)  # widget #2, top right

        self.add_widget(Label(text='Port:'))
        self.port = TextInput(text=prev_port, multiline=False)
        self.add_widget(self.port)

        self.add_widget(Label(text='Username:'))
        self.username = TextInput(text=prev_username, multiline=False)
        self.add_widget(self.username)

        # add our button.
        self.join = Button(text="Join")
        self.join.bind(on_press=self.join_button)
        self.add_widget(Label())  # just take up the spot.
        self.add_widget(self.join)

    def join_button(self, instance):
        port = self.port.text
        ip = self.ip.text
        username = self.username.text
        with open("prev_details.txt", "w") as f:
            f.write(f"{ip},{port},{username}")
        # print(f"Joining {ip}:{port} as {username}")
        # Create info string, update InfoPage with a message and show it
        info = f"Joining {ip}:{port} as {username}"
        chat_app.info_page.update_info(info)
        chat_app.screen_manager.current = 'Info'
        Clock.schedule_once(self.connect, 1)

    # Connects to the server
    # (second parameter is the time after which this function had been called,
    #  we don't care about it, but kivy sends it, so we have to receive it)
    def connect(self, _):
        # Get information for sockets client
        port = int(self.port.text)
        ip = self.ip.text
        username = self.username.text

        if not socket_client.connect(ip, port, username, show_error):
            return

        # Create chat page and activate it
        chat_app.create_chat_page()
        chat_app.screen_manager.current = 'Chat'

class InfoPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.message = Label(halign="center", valign="middle", font_size=30)
        self.message.bind(width=self.update_text_width)
        self.add_widget(self.message)
    def update_info(self, message):
        self.message.text = message
    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)


class ChatChessApp(App):
    root: Root
    store: JsonStore

    def build(self):
        self.screen_manager = ScreenManager()
        
        self.connect_page = ConnectPage()
        screen = Screen(name='Connect')
        screen.add_widget(self.connect_page)
        self.screen_manager.add_widget(screen)

        self.info_page = InfoPage()
        screen = Screen(name='Info')
        screen.add_widget(self.info_page)
        self.screen_manager.add_widget(screen)

        self.chess_app = Root()
        screen = Screen(name='chess')
        screen.add_widget(self.chess_app)
        self.screen_manager.add_widget(screen)

        return self.screen_manager

    def create_chat_page(self):
        self.chat_page = ChatPage()
        screen = Screen(name='Chat')
        screen.add_widget(self.chat_page)
        self.screen_manager.add_widget(screen)

    def on_start(self):
        # Load store
        self.store = JsonStore(CONFIG_FNAME)

        # Load colors
        try:
            colors = self.store.get('colors')
        except KeyError:
            colors = dict(board_1=[.3, .3, .3, 1], board_2=[
                          1, 1, 1, 1], highlight=[0, 1, 0, 1])

        App.get_running_app().chess_app._board_color_1 = colors['board_1']
        App.get_running_app().chess_app._board_color_2 = colors['board_2']
        App.get_running_app().chess_app._highlight_color = colors['highlight']

    def on_stop(self):
        # Save colors
        self.store.put('colors', board_1=App.get_running_app().chess_app._board_color_1,
                       board_2=App.get_running_app().chess_app._board_color_2, highlight=App.get_running_app().chess_app._highlight_color)



if __name__ == "__main__":
    Window.size = (NUMBER_OF_COLUMNS * DIMENSION_OF_EACH_SQUARE,
                   NUMBER_OF_ROWS * DIMENSION_OF_EACH_SQUARE + 80)
    chat_app = ChatChessApp()
    chat_app.run()
