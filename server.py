import websockets
import asyncio
import os
import http
import time
from os import environ
from classes.Game import Game
#from classes.ServerNetwork import Network
from classes.Client import Client

on_heroku = False
if 'RUNNING_ON_HEROKU' in os.environ:
    on_heroku = True

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
        self.sockets = {}
        self.connected = {}
    
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
        self.sockets[socket] = None
        print("connected")
        try:
            name = await socket.recv()
            client = Client(socket, path, name)
            #self.connected.add(client)
            self.client_added(self, client)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected.pop(socket, None)
            print("removed a socket")
            print(f"{len(self.connected)} remaining")
    
    def client_added(network, client):
        self.connected
        print(f"client connected: {client.name}")
        print(f"number of clients connected: {len(network.connected)}")
        


"""
    this is the main section of the game, where the game loop and functionality
    occurs
"""
def main():
    network = Network(
        "0.0.0.0" if on_heroku else "localhost",
        environ.get("PORT") if on_heroku else 5555
        )
    network.bind()

if __name__ == "__main__":
    main()