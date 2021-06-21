class Rooms():
    class Room():
        def __init__(self):
            self.connected = set()

        def add_client(self, client):
            self.connected.add(client)
            self.update_clients()
        
        def remove_client(self, client):
            self.connected.remove(client)
            self.update_clients()

        def update_clients(self):
            client_names = [client.name for client in self.connected]
            for client in self.connected:
                client.send({"TYPE": "ROOM_CONNECTED_UPDATE", "DATA": client_names})

    def __init__(self):
        self.rooms = set()
    
    