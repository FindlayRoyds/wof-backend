import socket
import http
import websockets
import threading
import asyncio
import json

"""
    the server class handles information about the server, and handles
    connections between the server and the client
"""
class Network:
    """
        this stores the connection information on the player
    """
    class Client():
        def __init__(self, socket, path, name, location):
            self.socket, self.path, self.name =socket, path, name
            self.game = None
            self.location = location
        
        async def send(self, data):
            await self.socket.send(json.dumps(data))

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
            name = await socket.recv()
            await self.add_client(socket, path, name)
        except Exception as exception:
            print(exception)
        finally:
            self.sockets.remove(socket)
    
    async def add_client(self, socket, path, name):
        client = self.Client(socket, path, name, "ROOM_VIEW")
        self.connected.add(client)

        try:
            await self.send_all({"TYPE": "LOAD_ROOMS", "DATA": [other_client.name for other_client in self.connected]}, "ROOM_VIEW")

            listener_process = threading.Thread(target = asyncio.run, args = (await self.listener(client)))
            listener_process.start()
        except Exception as exception:
            print(exception)
            self.connected.remove(client)
            print(f"removed client: {client.name}")
            await self.send_all({"TYPE": "LOAD_ROOMS", "DATA": [other_client.name for other_client in self.connected]}, "ROOM_VIEW")

    async def listener(self, client):
        for i in range(3):
            print(f"message {i} from {client.name}: {await client.socket.recv()}")
        print('finishing')
    
    async def send_all(self, data, location):
        for client in self.connected:
            if location == None or client.location == location:
                await client.send(data)