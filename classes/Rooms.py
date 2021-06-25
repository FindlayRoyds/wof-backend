class Rooms():
    class Room():
        def __init__(self, name, room_handler):
            self.connected = set()
            self.name = name
            self.room_handler = room_handler
        
        def get_data(self):
            return {
                "HASH": hash(self),
                "NAME": self.name
                }
        
        def get_connected_list(self):
            return [connected.name for connected in self.connected]
        
        def get_full_data(self):
            return {
                "ROOM_DATA": self.get_data(),
                "CONNECTED_LIST": self.get_connected_list()
            }

        async def add_client(self, client):
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
            client_names = [client.name for client in self.connected]
            for client in self.connected:
                await client.send({"TYPE": "ROOM_CONNECTED_UPDATE", "DATA": client_names})

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