"""
Main server file responsible for running the backend
this file starts up and binds the server network
this file is run when the server is deployed/run
"""

import os
from os import environ
from classes.Game import Game
from classes.ServerNetwork import Network

# testing environment variables to see if server has been deployed
on_heroku = False
if "RUNNING_ON_HEROKU" in os.environ:
    on_heroku = True

"""
this function runs when the server is deployed.
It starts and binds the network. However due to the nature of websockets
none of the functionality can be in this file
"""


def main():
    network = Network(
        "0.0.0.0" if on_heroku else "localhost",
        environ.get("PORT") if on_heroku else 5555,
    )
    network.bind()


# only runs if the file has not been imported. Fail safe against possible
# import loops
if __name__ == "__main__":
    main()
