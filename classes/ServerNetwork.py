import socket
import http
import websockets
import asyncio
import _thread
from classes.Client import Client

async def health_check(path, request_headers):
        if path == "/health/":
            return http.HTTPStatus.OK, [], b"OK\n"

"""
    the server class handles information about the server, and handles
    connections between the server and the client
"""
class Network:
    def __init__(
        self,
        ip:str="0.0.0.0",
        port:int=5555,
         ):
        self.ip, self.port = ip, port
    
    def bind(self):
        print("initializing server...")
        self.server = websockets.serve(
            self.listener,
            self.ip,
            self.port#,
            #process_request=health_check
            )

        asyncio.get_event_loop().run_until_complete(self.server)
        print(f"server initialized succesfully on {self.ip}:{self.port}")

        asyncio.get_event_loop().run_forever()
    
    async def listener(self, socket, path):
        async for message in socket:
            await socket.send(message)

    def accept_connection(self):
        connection, address = self.socket.accept()
        print(f"connected to {address}")
        return connection, address
