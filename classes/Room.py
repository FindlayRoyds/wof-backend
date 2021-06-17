class Room():
    def __init__(self):
        self.connected = set()
    
    def add_client(self, client):
        for other_client in self.connected:
            other_client.send({"NEW_CLIENT": client.name})
        
        client.send({"JOINED_ROOM": {[other_client for other_client in self.connected]}})
        
        self.connected.add(client)