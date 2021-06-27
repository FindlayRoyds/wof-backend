"""
SERVER NETWORK CLASS FILE
this file can be imported by the main server file
this file will handle server connections, such as handshakes,
health checks, messages, etc.
"""

import socket
import http
import websockets
import asyncio
import json
import os
import traceback
from classes.Rooms import Rooms
from classes.Game import Game

# env variables for testing if the program has been deployed
on_heroku = False
if "RUNNING_ON_HEROKU" in os.environ:
    on_heroku = True


class Network:
    """
    the server class handles information about the server, and handles
    connections between the server and the client
    """
    class Client:
        """
        this stores the connection information on the player
        """
        def __init__(self, network, socket, path, name, location):
            self.network = network
            self.socket, self.path, self.name = socket, path, name
            self.game = None
            self.room = None
            self.location = location
            self.ready = False
            self.game = None
            self.player = None

            network.connected.add(self)

        # causes an error popup to appear on the client's GUI
        async def error(self, message):
            await self.send({"TYPE": "ERROR", "DATA": f"ERROR: {message}"})

        # encodes and sends data to the client
        async def send(self, data):
            await self.socket.send(json.dumps(data))

        # waits to recieve data from the client, and decodes it
        async def recv(self):
            #  return await self.socket.recv()
            return json.loads(await self.socket.recv())

        # disconnects the client from the server
        async def disconnect(self):
            if self.game is not None:
                await self.game.player_handler.remove_player(self.player)

            if self in self.network.connected:
                self.network.connected.remove(self)
            if self.socket in self.network.sockets:
                self.network.sockets.remove(self.socket)

            if self.room is not None:
                await self.room.remove_client(self)

    def __init__(self, ip: str = "0.0.0.0", port: int = 5555):
        self.ip, self.port = ip, port
        self.sockets = set()
        self.connected = set()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rooms = Rooms(self)

    # binds the server to the port and ip address, and starts the
    # asynchronous event loop
    def bind(self):
        print("initializing server...")

        self.server = websockets.serve(
            self.client_init,
            self.ip,
            self.port,
            process_request=self.health_check
        )

        asyncio.get_event_loop().run_until_complete(self.server)
        print(f"server initialized succesfully on {self.ip}:{self.port}")

        asyncio.get_event_loop().run_forever()

    # returns the health status of the connection in an http header
    async def health_check(self, path, request_headers):
        if path == "/health/":
            return http.HTTPStatus.OK, [], b"OK\n"

    # this function fires whenever a client requests the server
    # this will attempt to recieve a logon from the client
    async def client_init(self, socket, path):
        self.sockets.add(socket)
        try:
            if not on_heroku:
                await asyncio.sleep(0)
            await socket.send(json.dumps({"TYPE": "CONNECTED"}))

            # waits to recieve a login attempt from the client
            # before continuing
            while True:
                data = json.loads(await socket.recv())
                if data["TYPE"] == "LOGIN":
                    if len(data["DATA"]) == 0:
                        # did not supply a name
                        await socket.send(
                            json.dumps(
                                {
                                    "TYPE": "ERROR",
                                    "DATA": f"ERROR: Please input a username",
                                }
                            )
                        )
                    elif len(data["DATA"]) > 12:
                        # name was too short
                        await socket.send(
                            json.dumps(
                                {
                                    "TYPE": "ERROR",
                                    "DATA": "ERROR: Input a shorter name",
                                }
                            )
                        )
                    else:
                        # creates client
                        await self.add_client(socket, path, data["DATA"])
                        break
                else:
                    # client did not attempt to login. This causes an
                    # error box to popup on the client's GUI
                    await socket.send(
                        json.dumps(
                            {
                                "TYPE": "ERROR",
                                "DATA": "ERROR: An unexpected error occured " +
                                "while attempting to login.",
                            }
                        )
                    )

        # this exception fires when the client disconnects prematurely
        # this deals with disconnecting and untracking the websocket
        except Exception as exception:
            traceback.print_exc()
            try:
                await socket.send(
                    json.dumps({
                        "TYPE": "ERROR",
                        "DATA": f"ERROR: {exception}"
                    })
                )
            except:
                pass
        finally:
            if socket in self.sockets:
                self.sockets.remove(socket)

    # this function deals with creating a client class when a login
    # attempt is successful
    # it also deals with future messages and disconnects
    async def add_client(self, socket, path, name):
        client = self.Client(self, socket, path, name, "ROOM_LIST")

        # this try catches a websocket error, indicating a disconnect
        try:
            await client.send(
                {"TYPE": "LOAD_ROOMS", "DATA": self.rooms.get_room_list()}
            )

            # this is the main listener loop. This loop runs when a
            # message is recieved from the client
            while True:
                recv = await client.recv()
                type = recv["TYPE"]
                if "DATA" in recv:
                    data = recv["DATA"]

                if type == "CREATE_ROOM":
                    # client requested to create a room
                    if len(data) == 0:
                        await client.error(
                            "You must create a name for your room"
                        )
                        break
                    if len(data) > 20:
                        await client.error(
                            "The room name cannot be more than 20 characters"
                        )
                        break

                    room = await self.rooms.add_room(data)
                    await room.add_client(client)
                elif type == "JOIN_ROOM":
                    # client requested to join a room
                    if data in self.rooms.rooms:
                        room = self.rooms.rooms[data]
                        await room.add_client(client)
                elif type == "LEAVE_ROOM":
                    # client requested to leave a room
                    if client.room is not None:
                        await client.room.remove_client(client)
                elif type == "CHANGE_READY":
                    # client requested to change their ready status
                    # (inside a room)
                    room = client.room
                    if room is not None:
                        client.ready = data
                        await room.update_clients()
                        starting = await room.start_game()

                        if starting:
                            game = Game(room)
                            await self.rooms.remove_room(room)
                            await game.start()
                elif type == "SUBMIT_GUESS":
                    # client requested to submit a guess for their
                    # current game
                    if client.player is not None and client.game is not None:
                        current_round = client.game.round_handler.current_round
                        await current_round.make_guess(
                            client.player, data
                        )
                elif type == "LEAVE_GAME":
                    # client requested to leave their current game
                    if client.player is not None and client.game is not None:
                        await client.game.player_handler.remove_player(
                            client.player
                        )
                        await client.send(
                            {
                                "TYPE": "LOAD_ROOMS",
                                "DATA": self.rooms.get_room_list()
                            }
                        )

        except Exception as exception:
            if exception.__class__.__name__ != "ConnectionClosedOK":
                # client disconnected from websocket
                traceback.print_exc()
            try:
                # an unexpected error occured. Alerting the client
                await client.error(exception)
            except:
                pass
            await client.disconnect(str(exception))

    # used to send data to every client connected to the server
    # has the ability to specify the location of clients to send to
    async def send_all(self, data, location):
        for client in self.connected:
            if location is None or client.location == location:
                await client.send(data)
