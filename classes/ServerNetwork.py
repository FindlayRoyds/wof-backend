import socket
import http
import websockets
import threading
import asyncio
import json
import os
import traceback
from classes.Rooms import Rooms

on_heroku = False
if 'RUNNING_ON_HEROKU' in os.environ:
    on_heroku = True

def start_game(room):
    pass

"""
    the server class handles information about the server, and handles
    connections between the server and the client
"""
class Network:
    """
        this stores the connection information on the player
    """
    class Client():
        def __init__(self, network, socket, path, name, location):
            self.network = network
            self.socket, self.path, self.name =socket, path, name
            self.game = None
            self.room = None
            self.location = location
            self.ready = False
            self.game = None

            network.connected.add(self)
        
        async def send(self, data):
            await self.socket.send(json.dumps(data))
        
        async def recv(self):
            #return await self.socket.recv()
            return json.loads(await self.socket.recv())
        
        async def disconnect(self, reason="Unknown reason"):
            if self in self.network.connected:
                self.network.connected.remove(self)
            if self.socket in self.network.sockets:
                self.network.sockets.remove(self.socket)
            
            if self.room != None:
                await self.room.remove_client(self)
            
    def __init__(
        self,
        ip:str="0.0.0.0",
        port:int=5555
         ):
        self.ip, self.port = ip, port
        self.sockets = set()
        self.connected = set()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rooms = Rooms(self)

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
    
    async def health_check(self, path, request_headers):
        if path == "/health/":
            return http.HTTPStatus.OK, [], b"OK\n"
    
    async def client_init(self, socket, path):
        self.sockets.add(socket)
        try:
            if not on_heroku:
                await asyncio.sleep(2.5)
            await socket.send(
                json.dumps(
                    {"TYPE": "CONNECTED"}
                )
            )

            data = json.loads(await socket.recv())
            if data["TYPE"] == "LOGIN":
                await self.add_client(socket, path, data["DATA"])
            else:
                raise Exception("Client did not attempt to login")
        except Exception as exception:
            print("socket exception")
            traceback.print_exc()
        finally:
            if socket in self.sockets:
                self.sockets.remove(socket)
    
    async def add_client(self, socket, path, name):
        client = self.Client(self, socket, path, name, "ROOM_LIST")

        try:
            await client.send({"TYPE": "LOAD_ROOMS", "DATA": self.rooms.get_room_list()})
            """await self.send_all(
                {"TYPE": "LOAD_ROOMS", "DATA": [other_client.name for other_client in self.connected]},
                "ROOM_LIST"
                )"""
            
            while True:
                recv = await client.recv()
                type = recv["TYPE"]
                if "DATA" in recv:
                    data = recv["DATA"]

                if type == "CREATE_ROOM":
                    room = await self.rooms.add_room(data)
                    await room.add_client(client)
                elif type == "JOIN_ROOM":
                    if data in self.rooms.rooms:
                        room = self.rooms.rooms[data]
                        await room.add_client(client)
                elif type == "LEAVE_ROOM":
                    if client.room != None:
                        await client.room.remove_client(client)
                elif type == "CHANGE_READY":
                    room = client.room
                    if room != None:
                        client.ready = data
                        await room.update_clients()
                        starting = await room.start_game()

                        if starting:
                            start_game(room)


            #listener_thread = threading.Thread(target = asyncio.run, args = (await self.listener(client)))
            #listener_thread.start()
        except Exception as exception:
            if exception.__class__.__name__ != "ConnectionClosedOK":
                traceback.print_exc()
            await client.disconnect(str(exception))
            print(f"removed client: {client.name}")

    async def listener(self, client):
        while True:
            print(await client.recv())

    async def send_all(self, data, location):
        for client in self.connected:
            if location == None or client.location == location:
                await client.send(data)