import random
import re
import asyncio

phrases_file = "src/phrases"

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

    class PlayerHandler(Service):
        """
        the player class, stores information such as their name, their score, etc.
        """

        class Player:
            def __init__(self, game, client):
                self.game = game
                self.client = client
                self.score = 0

            def __repr__(self):
                return self.client.name

        def __init__(self, game):
            super().__init__(game)
            self.players = []

        def __repr__(self):
            return ", ".join([player.name for player in self.players])

        def add_player(self, client):
            player = self.Player(self.game, client)
            self.players.append(player)
            client.player = player

        async def remove_player(self, player):
            self.players.remove(player)

            player.client.game = None
            player.client.player = None
            player.client.location = "ROOM_LIST"

            current_round = self.game.round_handler.current_round
            if len(self.players) == 0:
                del self.game
            else:
                if player == current_round.current_player:
                    current_round.current_player_index -= 1
                    await current_round.advance()
                else:
                    current_round.current_player_index = self.players.index(
                        current_round.current_player
                    )

    """
        The phrases service stores the different sayings/text which can appear in
        a round
    """

    class PhraseHandler(Service):
        """
        phrase objects store some text as well as the genre for the text. These may
        be selected during a game to be guessed by the players
        """

        class Phrase:
            def __init__(self):
                self.text = random.choice(open(phrases_file).readlines()).rstrip()

                line_lengths = [12, 14, 14, 12]
                lines = [[], [], [], []]
                line_num = 0
                cur_line_lengths = [0, 0, 0, 0]
                word_num = 0

                words = self.text.split(" ")

                while True:
                    word = words[word_num]
                    if cur_line_lengths[line_num] + len(word) > line_lengths[line_num]:
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

        def __init__(self, game):
            super().__init__(game)

    """
        The round handler service handles information on the rounds in the
        game, such as what round number the game is on, and which player's turn
        it is.
    """

    class RoundHandler(Service):
        class Round:
            def __init__(self, game):
                self.game = game
                self.phrase = game.phrase_handler.Phrase()
                self.current_player = random.choice(game.player_handler.players)
                self.current_player_index = game.player_handler.players.index(
                    self.current_player
                )

            async def start(self):
                print("starting")
                self.prize = self.game.wheel_handler.generate_prize()

                print(self.current_player.client.name)

                self.guessed_letters = set([",", "-", "'", '"', " "])
                self.total_guessed = 0

                await self.game.send_all(
                    {"TYPE": "GAME_MESSAGE", "DATA": "A new round is starting"}
                )

                await asyncio.sleep(1.5)
                await self.game.send_all({"TYPE": "SET_PRIZE", "DATA": self.prize})

                await asyncio.sleep(5)
                await self.send_turn_data()

            async def advance(self):
                players = self.game.player_handler.players

                next_index = (self.current_player_index + 1) % len(players)

                self.current_player = players[next_index]
                self.current_player_index = next_index

                self.prize = self.game.wheel_handler.generate_prize()
                await self.game.send_all({"TYPE": "SET_PRIZE", "DATA": self.prize})

                await asyncio.sleep(5)
                await self.send_turn_data()

            async def send_turn_data(self):
                for player in self.game.player_handler.players:
                    name = self.current_player.client.name
                    msg_data = "Your" if player == self.current_player else f"{name}'s"
                    msg = f"It is {msg_data} turn"
                    data = {"TYPE": "GAME_MESSAGE", "DATA": msg}
                    await player.client.send(data)

            async def make_guess(self, player, guess: str):
                if player != self.current_player:
                    await player.client.error(
                        "You can only make a guess when it is your turn"
                    )
                    return

                guess = guess.lower()
                phrase = self.phrase.text.lower()

                print(f"guessed {guess}")

                if len(guess) == 1:
                    if guess.isalpha():
                        if guess not in self.guessed_letters:
                            occurances = phrase.count(guess)

                            self.guessed_letters.add(guess)
                            self.total_guessed += occurances

                            if occurances == 0:
                                await self.game.send_all(
                                    {
                                        "TYPE": "GAME_MESSAGE",
                                        "DATA": f"{player.client.name} incorrectly guessed the letter {guess}",
                                    }
                                )

                                await asyncio.sleep(1)

                                await self.advance()
                            else:
                                print(occurances)
                                score = self.prize * occurances
                                player.score += score

                                if self.total_guessed >= len(
                                    re.sub(r"\W+", "", phrase)
                                ):
                                    print("got the complete phrase!")

                                    await asyncio.sleep(3)
                                    await self.game.round_handler.new_round()
                                else:
                                    await self.game.send_all(
                                        {
                                            "TYPE": "GAME_MESSAGE",
                                            "DATA": f"{player.client.name} guessed the letter {guess} and won {self.prize * occurances} dollars!",
                                        }
                                    )

                                    await asyncio.sleep(2)
                                    self.prize = (
                                        self.game.wheel_handler.generate_prize()
                                    )
                                    await self.game.send_all(
                                        {"TYPE": "SET_PRIZE", "DATA": self.prize}
                                    )

                        print(
                            "".join(
                                [
                                    letter if letter in self.guessed_letters else "_"
                                    for letter in self.phrase.text
                                ]
                            )
                        )
                    else:
                        await player.client.error(
                            "Your guess must only be alphabetical characters"
                        )
                elif len(guess) == 0:
                    await player.client.error(
                        f"You must submit a guess; you attempted to submit nothing {random.randint(1, 100)}"
                    )
                else:
                    print("guessed a phrase")
                    if guess == phrase:
                        print("is phrase")
                        player.score += 1000
                        await self.game.round_handler.new_round()
                    else:
                        print("not phrase")
                        await self.advance()

        def __init__(self, game):
            super().__init__(game)
            self.current_round = None

        async def new_round(self):
            print("new round")
            round = self.Round(self.game)
            await round.start()
            print("did the start()")
            self.current_round = round
            return round

    class WheelHandler(Service):
        def __init__(self, game):
            super().__init__(game)
            self.prizes = [50, 100, 150, 200, 250, 500, 1000]

        def generate_prize(self):
            return random.choice(self.prizes)

    def __init__(self, room):
        self.add_services()

        for client in room.connected:
            client.game = self
            self.player_handler.add_player(client)

        print("adding from this thing")

    async def start(self):
        data = {"TYPE": "JOINED_GAME", "DATA": ""}
        await self.send_all(data)

        print("adding from beliw thing")
        self.current_round = await self.round_handler.new_round()

    def add_services(self):
        self.player_handler = self.PlayerHandler(self)
        self.phrase_handler = self.PhraseHandler(self)
        self.round_handler = self.RoundHandler(self)
        self.wheel_handler = self.WheelHandler(self)

    async def update_players(self):
        for player in self.player_handler.players:
            player_info = {}
            player_id = 0
            for other in self.player_handler.players:
                info = {
                    "NAME": other.client.name,
                    "YOU": other == player,
                    "SCORE": other.score,
                    "IS_TURN": self.round_handler.current_round.current_player == other,
                }
                player_info[player_id] = info
                player_id += 1

            await player.client.send(
                {"TYPE": "GAME_CONNECTED_UPDATE", "DATA": player_info}
            )

    async def send_all(self, data):
        for player in self.player_handler.players:
            await player.client.send(data)
