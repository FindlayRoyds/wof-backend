import socket
import http
import websockets
import threading
import asyncio
import json
from classes.Rooms import Rooms

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

            network.connected.add(self)
        
        async def send(self, data):
            await self.socket.send(json.dumps(data))
        
        async def recv(self):
            return await self.socket.recv()
            #return json.loads(await self.socket.recv())
        
        async def disconnect(self, reason="Unknown reason"):
            print("disconnecting client")

            if self in self.network.connected:
                self.network.connected.remove(self)
            if self.socket in self.network.sockets:
                self.network.sockets.remove(self.socket)
            


    def __init__(
        self,
        ip:str="0.0.0.0",
        port:int=5555
         ):
        self.ip, self.port = ip, port
        self.sockets = set()
        self.connected = set()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
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
            await asyncio.sleep(2)
            await socket.send(
                json.dumps(
                    {"TYPE": "CONNECTED"}
                )
            )

            data = await socket.recv()
            if data["TYPE"] == "LOGIN":
                await self.add_client(socket, path, data["DATA"])
            else:
                raise Exception("Client did not attempt to login")
        except Exception as exception:
            print(exception)
        finally:
            self.sockets.remove(socket)
    
    async def add_client(self, socket, path, name):
        client = self.Client(self, socket, path, name, "ROOM_LIST")

        try:
            await self.send_all(
                {"TYPE": "LOAD_ROOMS", "DATA": [other_client.name for other_client in self.connected]},
                "ROOM_LIST"
                )

            listener_thread = threading.Thread(target = asyncio.run, args = (await self.listener(client)))
            listener_thread.start()
        except Exception as exception:
            print(exception)
            client.disconnect(str(exception))
            print(f"removed client: {client.name}")
            await self.send_all(
                {"TYPE": "LOAD_ROOMS", "DATA": [other_client.name for other_client in self.connected]},
                "ROOM_LIST"
                )

    async def listener(self, client):
        while True:
            print(await client.recv())

    async def send_all(self, data, location):
        for client in self.connected:
            if location == None or client.location == location:
                await client.send(data)