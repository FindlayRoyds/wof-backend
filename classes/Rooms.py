class Rooms():
    class Room():
        def __init__(self, name, room_handler):
            self.connected = set()
            self.room_handler = room_handler

            self.name = name
            self.min_players = 2
            self.max_players = 4
        
        def get_data(self):
            return {
                "HASH": hash(self),
                "NAME": self.name
                }

        async def add_client(self, client):
            if len(self.connected) + 1 > self.max_players: return

            self.connected.add(client)
            if client.room != None:
                print("was already in room")
                await client.room.remove_client(client)
            client.room = self
            client.location = "ROOM"

            data = self.get_data()
            await client.send({"TYPE": "JOINED_ROOM", "DATA": data})

            await self.update_clients()
        
        async def remove_client(self, client):
            self.connected.remove(client)
            client.location = "ROOM_LIST"
            client.room = None
            try:
                await client.send({"TYPE": "LOAD_ROOMS", "DATA": self.room_handler.get_room_list()})
            except:
                print("client was disconnected")
            if len(self.connected) == 0:
                await self.room_handler.remove_room(self)
                return

            await self.update_clients()

        async def update_clients(self):
            for client in self.connected:
                print(client.ready)
                client_names = [
                    f"{other_client.name}: {'READY' if other_client.ready else 'NOT READY'}" if client != other_client else "You"
                    for other_client in self.connected
                    ]
                await client.send({"TYPE": "ROOM_CONNECTED_UPDATE", "DATA": client_names})
        
        async def start_game(self):
            if len(self.connected) < self.min_players: return False

            for client in self.connected:
                if client.ready == False:
                    return False
            print("starting game")
            return True

    def __init__(self, network):
        self.rooms = {}
        self.network = network

    def get_room_list(self):
        return [{"NAME": self.rooms[id].name, "HASH": hash(self.rooms[id])} for id in self.rooms]
    
    async def update_rooms(self):
        print("updating rooms")
        await self.network.send_all(
            {"TYPE": "LOAD_ROOMS", "DATA": self.get_room_list()},
            "ROOM_LIST"
            )
    
    async def add_room(self, name):
        room = self.Room(name, self)
        self.rooms[hash(room)] = room
        await self.update_rooms()
        return room
    
    async def remove_room(self, room):
        self.rooms.pop(hash(room))
        
        await self.update_rooms()