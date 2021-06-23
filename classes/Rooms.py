class Rooms():
    class Room():
        def __init__(self, name, room_handler):
            self.connected = set()
            self.name = name
            self.room_handler = room_handler

        async def add_client(self, client):
            self.connected.add(client)
            if client.room != None:
                await client.room.remove_client(client)
            client.room = self

            await client.send({"TYPE": "JOINED_ROOM", "DATA": self.name})

            await self.update_clients()
        
        async def remove_client(self, client):
            self.connected.remove(client)
            if len(self.connected) == 0:
                await self.room_handler.remove_room(self)
                return

            await self.update_clients()

        async def update_clients(self):
            client_names = [client.name for client in self.connected]
            for client in self.connected:
                await client.send({"TYPE": "ROOM_CONNECTED_UPDATE", "DATA": client_names})

    def __init__(self, network):
        self.rooms = set()
        self.network = network
    
    async def update_rooms(self):
        print("updating rooms")
        await self.network.send_all(
            {"TYPE": "LOAD_ROOMS", "DATA": [room.name for room in self.rooms]},
            "ROOM_LIST"
            )
    
    async def add_room(self, name):
        room = self.Room(name, self)
        self.rooms.add(room)
        await self.update_rooms()
        return room
    
    async def remove_room(self, room):
        self.rooms.remove(room)
        
        await self.update_rooms()