"""
    The parent class for the entire game instance.
    Can be used to create a new round by removing the old game instance, and
    creating a new one
"""
class Game:
    """
        The parent service class. Services are all children of the game instance,
        and are used to implement functionality, such as generating the random number,
        or storing the score for players
    """
    class Service:
        def __init__(self, game):
            self.game = game

    """
        The players service stores the player instances, as well as the scores so
        far in the game
    """
    class Players(Service):
        """
            the player class, stores information such as their name, their score, etc.
        """
        class Player():
            def __init__(self, players_service, name):
                self.players_service = players_service
                self.name = name
            
            def __repr__(self):
                return self.name

        def __init__(self, game):
            super().__init__(game)
            self.players = []
            self.player_count = 0
        
        def __repr__(self):
            return ', '.join([player.name for player in self.players])
        
        def add_player(self, name:str):
            self.players.append(self.Player(self, name))
            self.update_player_count()
        
        def remove_player(self, id):
            self.players.pop(id)
            self.update_player_count()
        
        def get_player(self, id:int):
            return self.players[id]
        
        def update_player_count(self):
            self.player_count = len(self.players)

    """
        The phrases service stores the different sayings/text which can appear in
        a round
    """
    class Phrases(Service):
        """
            phrase objects store some text as well as the genre for the text. These may
            be selected during a game to be guessed by the players
        """
        class Phrase:
            def __init__(self, text:str, genre:str="None"):
                self.text = text
                def __init__(self, game):
                    super().__init__(game)
    
    """
        The round handler service handles information on the rounds in the
        game, such as what round number the game is on, and which player's turn
        it is.
    """
    class RoundHandler(Service):
        def __init__(self, game):
            super().__init__(game)
            self.round_number = 1
            self.player_id = 0
        
        def advance_round(self):
            player_count = self.game.get_service("Players").player_count
            self.round_number += 1
            self.player_id = (self.player_id + 1) % player_count

    def __init__(self):
        self.add_services()
        pass

    def add_services(self):
        self.services = {}
        self.services["Players"] = self.Players(self)
        self.services["Phrases"] = self.Phrases(self)

    def get_service(self, service_name:str):
        return self.services[service_name]