"""
    this stores the connection information on the player
"""
class Client():
    def __init__(self, socket, path, name):
        self.socket, self.path, self.name =socket, path, name
        print(f"User {self.name} created!")