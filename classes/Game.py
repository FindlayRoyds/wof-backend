"""
GAME CLASS FILE
this file can be used to import the game class into the
main server loop
"""

import random
import re
import asyncio

# stores a reference to the file containing the game's phrases
phrases_file = "src/phrases"
# used to check if a guess is in the alphabet
alphabet = "abcdefghijklmnopqrstuvwxyz"


class Game:
    """
    The parent class for the entire game instance.
    contains all of the specific handlers which are used to
    interact with the game
    """

    class Service:
        """
        The parent service class. Services are all children of the game
        instance, and are used to implement functionality, such as
        generating the random number, or storing the score for players
        """
        def __init__(self, game):
            self.game = game

    class PlayerHandler(Service):
        """
        The players service stores the player instances, as well as the
        scores so far in the game. allows for adding and removing
        players, as well as other functions such as sending a websocket
        message to all players
        """

        class Player:
            """
            the player class, stores information such as their name,
            their score, etc.
            """
            def __init__(self, game, client):
                self.game = game
                self.client = client
                self.score = 0

        def __init__(self, game):
            super().__init__(game)
            self.game = game
            self.players = []

        # allows players to be added to the game
        def add_player(self, client):
            player = self.Player(self.game, client)
            self.players.append(player)
            client.player = player

        # allows players to be removed from the game
        async def remove_player(self, player):
            self.players.remove(player)

            player.client.game = None
            player.client.player = None
            player.client.location = "ROOM_LIST"

            # shifts to the next person's turn if needed
            current_round = self.game.round_handler.current_round
            if len(self.players) == 0:
                if hasattr(self, 'game'):
                    del self.game
            else:
                if player == current_round.current_player:
                    current_round.current_player_index -= 1
                    await current_round.advance()
                else:
                    current_round.current_player_index = self.players.index(
                        current_round.current_player
                    )
            
            if hasattr(self, 'game'):
                await self.game.update_players()

    class PhraseHandler(Service):
        """
        The phrases service stores the different sayings/text which can
        appear in a round
        """

        class Phrase:
            """
            phrase objects store some text as well as the genre for the
            text. These may be selected during a game to be guessed by
            the players
            """
            def __init__(self):
                self.text = random.choice(
                    open(phrases_file).readlines()
                ).rstrip()

                """
                this section of code is unused. It was originally
                planned for displaying the phrase on a 3d board on
                the client with special formatting

                line_lengths = [12, 14, 14, 12]
                lines = [[], [], [], []]
                line_num = 0
                cur_line_lengths = [0, 0, 0, 0]
                word_num = 0

                words = self.text.split(" ")

                while True:
                    word = words[word_num]
                    if cur_line_lengths[line_num] +
                            len(word) > line_lengths[line_num]:
                        line_num += 1
                    else:
                        lines[line_num].append(word)
                        cur_line_lengths[line_num] += len(word) + 1
                        word_num += 1
                        if word_num >= len(words):
                            break

                if len(lines[3]) + len(lines[2]) == 0:
                    lines[2] = lines[1]
                    lines[1] = lines[0]
                    lines[0] = []

                for line in lines:
                    print(f"line: {' '.join(line)}")

                self.lines = lines
                """

        def __init__(self, game):
            super().__init__(game)

    class RoundHandler(Service):
        """
        The round handler service handles what round the game is
        currently on, by storing a reference to it. Allows new rounds
        to be created
        """

        class Round:
            """
            this class is the main functionality of the game, as it is
            what allows functionality to be added to induvidual rounds,
            such as making guesses, advancing to the next player,
            awarding points, etc.
            """
            def __init__(self, game):
                self.game = game
                self.phrase = game.phrase_handler.Phrase()
                self.current_player = random.choice(
                    game.player_handler.players
                )
                self.current_player_index = game.player_handler.players.index(
                    self.current_player
                )

            # this allows a new round to be started asynchronously, as
            # __init__ cannot be awaited
            async def start(self):
                self.prize = self.game.wheel_handler.generate_prize()

                self.guessed_letters = set([",", "-", "'", '"', " "])
                self.ignore_letters = set([",", "-", "'", '"', " "])
                self.total_guessed = 0

                await self.game.update_players()
                await self.update_phrase()

                await self.game.send_all(
                    {"TYPE": "GAME_MESSAGE", "DATA": "A new round is starting"}
                )

                await asyncio.sleep(1.5)
                await self.send_turn_data()
                await self.update_phrase()

                await self.game.send_all(
                    {"TYPE": "SET_PRIZE", "DATA": self.prize}
                )

                await asyncio.sleep(5)

            # moves onto the next persons turn. Maintains the correct
            # order even when people leave the game
            async def advance(self, change_score=True):
                players = self.game.player_handler.players

                next_index = (self.current_player_index + 1) % len(players)

                self.current_player = players[next_index]
                self.current_player_index = next_index

                await self.game.update_players()

                await self.send_turn_data()
                await self.update_phrase()

                self.prize = self.game.wheel_handler.generate_prize()
                await self.game.send_all(
                    {"TYPE": "SET_PRIZE", "DATA": self.prize}
                )

                await asyncio.sleep(5)

            # this sends a message to the client telling the player
            # who's turn it is
            async def send_turn_data(self):
                for player in self.game.player_handler.players:
                    name = self.current_player.client.name
                    is_turn = player == self.current_player
                    msg_data = "Your" if is_turn else f"{name}'s"
                    msg = f"It is {msg_data} turn"
                    data = {"TYPE": "GAME_MESSAGE", "DATA": msg}
                    await player.client.send(data)

            # this updates the phrase representation (with underscores)
            # and sends it to all the players. Also adds the guessed
            # letters
            async def update_phrase(self):
                self.display_phrase = (
                    "".join(
                        [
                            letter if letter.lower()
                            in self.guessed_letters else "_"
                            for letter in self.phrase.text
                        ]
                    ) +
                    " guessedletters: " +
                    ", ".join(
                        list(
                            filter(
                                (None).__ne__,
                                [
                                    letter
                                    if letter not in self.ignore_letters
                                    else None
                                    for letter in self.guessed_letters
                                ],
                            )
                        )
                    )
                )
                await self.game.send_all(
                    {"TYPE": "UPDATE_PHRASE", "DATA": self.display_phrase}
                )

            # this is fired when the server class recieves a guess
            # attempt from a client. It handles checking the
            # validity of the guess, awarding points, etc.
            async def make_guess(self, player, guess: str):
                if player != self.current_player:
                    await player.client.error(
                        "You can only make a guess when it is your turn"
                    )
                    return

                guess = guess.lower()
                phrase = self.phrase.text.lower()

                if guess in self.guessed_letters:
                    await player.client.error("Please submit a new letter")
                    return

                if len(guess) == 1:
                    # client guessed a single letter
                    if guess in alphabet:
                        if guess not in self.guessed_letters:
                            occurances = phrase.count(guess)

                            self.guessed_letters.add(guess)
                            self.total_guessed += occurances

                            if occurances == 0:
                                # client guessed incorrectly
                                name = player.client.name
                                data = f"{name} incorrectly guessed the letter\
'{guess}'"
                                await self.game.send_all(
                                    {
                                        "TYPE": "GAME_MESSAGE",
                                        "DATA": data,
                                    }
                                )

                                await asyncio.sleep(1)

                                await self.advance(False)
                            else:
                                # client guessed correctly
                                score = self.prize * occurances
                                player.score += score

                                name = player.client.name

                                await self.game.update_players()

                                await self.game.send_all(
                                    {
                                        "TYPE": "GAME_MESSAGE",
                                        "DATA": f"{name} guessed the letter \
'{guess}' and won {self.prize * occurances} dollars!",
                                    }
                                )

                                if self.total_guessed >= len(
                                    re.sub(r"\W+", "", phrase)
                                ):

                                    await asyncio.sleep(3)
                                    await self.game.round_handler.new_round()
                                    return
                                else:
                                    await asyncio.sleep(2)
                                    wheel_handler = self.game.wheel_handler
                                    self.prize = (
                                        wheel_handler.generate_prize()
                                    )
                                    await self.game.send_all(
                                        {
                                            "TYPE": "SET_PRIZE",
                                            "DATA": self.prize
                                        }
                                    )
                    else:
                        await player.client.error(
                            "Your guess must only be alphabetical characters"
                        )
                elif len(guess) == 0:
                    # client guessed nothing
                    await player.client.error(
                        "You must submit a guess; you attempted to submit \
nothing"
                    )
                else:
                    # client guessed a phrase
                    if guess == phrase:
                        # client got phrase correct
                        player.score += 1000

                        await self.game.send_all(
                            {
                                "TYPE": "GAME_MESSAGE",
                                "DATA": f"{player.client.name} correctly \
guessed the phrase '{guess}' and won $1000",
                            }
                        )

                        await self.update_phrase()
                        await asyncio.sleep(3)

                        await self.game.round_handler.new_round()
                        return
                    else:
                        # client got phrase incorrect
                        await self.game.send_all(
                            {
                                "TYPE": "GAME_MESSAGE",
                                "DATA": f"{player.client.name} incorrectly \
guessed the phrase '{guess}'",
                            }
                        )

                        await self.advance(False)

                await self.update_phrase()

        def __init__(self, game):
            super().__init__(game)
            self.current_round = None
            self.total_rounds = 0

        # this creates a new round and sets the current round to it
        async def new_round(self):
            self.total_rounds += 1

            if self.total_rounds > 3:
                # 3 rounds have already been played, finishing game
                max_score = 0
                best_player = "NOBODY"
                for player in self.game.player_handler.players:
                    if player.score >= max_score:
                        max_score = player.score
                        best_player = player.client.name

                await self.game.send_all(
                    {
                        "TYPE": "GAME_MESSAGE",
                        "DATA": f"GAME FINISHED! Winner: {best_player}",
                    }
                )
                # this is in order to keep clients connected with very
                # little overhead
                await asyncio.sleep(99999)

            round = self.Round(self.game)
            self.current_round = round
            await round.start()

            return round

    class WheelHandler(Service):
        """
        this class handles generating a random priE each time the wheel
        is spun
        """
        def __init__(self, game):
            super().__init__(game)
            self.prizes = [50, 100, 150, 200, 250, 500, 1000]

        # generates a random prize from the list of possible prizes
        def generate_prize(self):
            return random.choice(self.prizes)

    def __init__(self, room):
        self.add_services()

        for client in room.connected:
            client.game = self
            self.player_handler.add_player(client)

    # this starts up a new game instance. This is done seperately from
    # the __init__ dunder function, as it needs to be run asynchronously
    async def start(self):
        data = {"TYPE": "JOINED_GAME", "DATA": ""}
        await self.send_all(data)

        self.current_round = await self.round_handler.new_round()

    # this starts up and creates a reference to all of the services
    def add_services(self):
        self.player_handler = self.PlayerHandler(self)
        self.phrase_handler = self.PhraseHandler(self)
        self.round_handler = self.RoundHandler(self)
        self.wheel_handler = self.WheelHandler(self)

    # this sends out a websocket to all the players telling them who's
    # turn it is, who is in the game, and what score everyone has
    async def update_players(self):
        current_player = self.round_handler.current_round.current_player
        for player in self.player_handler.players:
            player_info = {}
            player_id = 0
            for other in self.player_handler.players:
                info = {
                    "NAME": other.client.name,
                    "YOU": other == player,
                    "SCORE": other.score,
                    "IS_TURN": current_player == other,
                }
                player_info[player_id] = info
                player_id += 1

            await player.client.send(
                {"TYPE": "GAME_CONNECTED_UPDATE", "DATA": player_info}
            )

    # this function can be used to send a message to every player in the game
    async def send_all(self, data):
        for player in self.player_handler.players:
            await player.client.send(data)
