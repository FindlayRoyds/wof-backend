import websockets
import socket
import asyncio
import os
import http
import time
import threading
import multiprocessing
from os import environ
from classes.Game import Game
from classes.ServerNetwork import Network
from classes.Room import Room

on_heroku = False
if 'RUNNING_ON_HEROKU' in os.environ:
    on_heroku = True
        


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