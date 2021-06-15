import socket
import websockets
import asyncio
import sys
import os
import _thread
from os import environ
from classes.Game import Game
from classes.ServerNetwork import Network
from classes.Client import Client

on_heroku = False
if 'RUNNING_ON_HEROKU' in os.environ:
  on_heroku = True

"""
    this is the main section of the game, where the game loop and functionality
    occurs
"""
def main():
    """
    game = Game()

    # declare service variables
    players = game.get_service("Players")
    phrases = game.get_service("Phrases")

    players.add_player("Bob")
    """

    network = Network(
        "0.0.0.0" if on_heroku else "localhost",
        environ.get("PORT") if on_heroku else 5555
        )
    network.bind()

if __name__ == "__main__":
    main()