"""
ROOMS CLASS FILE
this can be used to import the rooms class into the main server file
"""


class Rooms:
    """
    This class is used to create, delete, and store all the rooms
    in the game.
    it is also responsible for sending updates to clients
    when an update occurs
    """

    class Room:
        """
        this class is used to store connected clients who want to play
        a game.
        it is also responsible for sending updates to clients
        when an update occurs.
        this class is passed to the game initiator, so it can be used
        to connect the clients to a game
        """

        def __init__(self, name, room_handler):
            self.connected = set()
            self.room_handler = room_handler

            self.name = name
            self.min_players = 2
            self.max_players = 8

        # returns a unique hash (id) of the room as well as the name
        # used for sending a list of rooms to clients
        def get_data(self):
            return {"HASH": hash(self), "NAME": self.name}

        # used to connect a client to the room
        async def add_client(self, client):
            # checks if the room is full. If so an error is sent to
            # the client
            if len(self.connected) + 1 > self.max_players:
                client.error("This room is full!")
                return

            self.connected.add(client)
            if client.room is not None:
                await client.room.remove_client(client)
            client.room = self
            client.ready = False
            client.location = "ROOM"

            data = self.get_data()
            await client.send({"TYPE": "JOINED_ROOM", "DATA": data})

            await self.update_clients()

        # used to disconnect a client from the room
        async def remove_client(self, client):
            self.connected.remove(client)
            client.location = "ROOM_LIST"
            client.room = None
            client.ready = False
            try:
                await client.send(
                    {
                        "TYPE": "LOAD_ROOMS",
                        "DATA": self.room_handler.get_room_list()
                    }
                )
            except:
                print("client was disconnected")
            if len(self.connected) == 0:
                await self.room_handler.remove_room(self)
                return

            await self.update_clients()

        # this function is used to generate and send information about
        # the clients connected to the room
        async def update_clients(self):
            for client in self.connected:
                client_info = {}
                client_id = 0
                for other in self.connected:
                    info = {
                        "NAME": other.name,
                        "READY": other.ready,
                        "YOU": other == client,
                    }
                    client_info[client_id] = info
                    client_id += 1
                await client.send(
                    {"TYPE": "ROOM_CONNECTED_UPDATE", "DATA": client_info}
                )

        # this function is run whenever a client changes their status to
        # ready. If a game is allowed to start, it will return true
        # the server network class deals with starting the game
        async def start_game(self):
            if len(self.connected) < self.min_players:
                return False

            for client in self.connected:
                if not client.ready:
                    return False

            return True

    def __init__(self, network):
        self.rooms = {}
        self.network = network

    # returns a list of all rooms being tracked, + an identifying hash
    def get_room_list(self):
        return [
            {"NAME": self.rooms[id].name, "HASH": hash(self.rooms[id])}
            for id in self.rooms
        ]

    # sends an update of the currently active rooms to all connected
    # clients
    async def update_rooms(self):
        await self.network.send_all(
            {"TYPE": "LOAD_ROOMS", "DATA": self.get_room_list()}, "ROOM_LIST"
        )

    # creates and tracks a new room
    async def add_room(self, name):
        room = self.Room(name, self)
        self.rooms[hash(room)] = room
        await self.update_rooms()
        return room

    # removes and untracks a room
    async def remove_room(self, room):
        self.rooms.pop(hash(room))

        await self.update_rooms()
