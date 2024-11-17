import pickle
from flask_cors import CORS
from flask import Flask, request
from board import ScrabbleBoard
from dawg import build_dawg, build_trie

# This version of the app serializes the board object with pickle and stores the file in the tmp folder.
# Unfortunately, storing files in a tmp folder generated errors from vercel's read only file system.
# See link for discussion of using tmp folder with vercel: https://github.com/vercel/vercel/discussions/5320

app = Flask(__name__)
CORS(app)

@app.route('/')
def get_home():
    return 'homepage'

@app.route('/start')
def start_game():
    # build dawg
    text_file = open("lexicon/scrabble_words_complete.txt", "r")
    big_list = text_file.read().splitlines()
    text_file.close()
    build_trie(big_list)
    root = build_dawg(big_list)

    game = ScrabbleBoard(root)
    computer_hand = game.get_computer_hand()
    player_hand = game.get_player_hand()
    tiles = game.get_tiles()

    file_handler = open("tmp/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    return {'player_hand': player_hand, 'computer_hand': computer_hand, 'tiles': tiles}

@app.route('/get-computer-first-move')
def computer_make_start_move():
    r = redis.Redis(
        host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
        port=14591,
        password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
    
    to_load = open("tmp/game.pickle", 'rb')
    game = pickle.load(to_load)
    to_load.close()

    result = game.get_start_move()

    file_handler = open("tmp/game.pickle", 'wb')
    pickle.dump(game, file_handler)
    file_handler.close()
   
    game.print_board()
    return result

@app.route('/get-best-move')
def get_best_move():
    to_load = open("tmp/game.pickle", 'rb')
    game = pickle.load(to_load)
    to_load.close()

    result = game.get_best_move()

    file_handler = open("tmp/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    game.print_board()
    return result

@app.route('/insert-letters', methods = ['POST'])
def insert_tiles():
    request_data = request.get_json()
    tiles = request_data['letters_and_coordinates']

    to_load = open("tmp/game.pickle", 'rb')
    game = pickle.load(to_load)
    to_load.close()

    result = game.insert_letters(tiles)

    game.print_board()

    file_handler = open("tmp/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    return result

@app.route('/dump-letters', methods = ['POST'])
def dump_letters():
    to_load = open("tmp/game.pickle", 'rb')
    game = pickle.load(to_load)
    to_load.close()

    request_data = request.get_json()
    letters = request_data['letters']
    result = game.dump_letters(letters)
    game.print_board()
    print(result)

    file_handler = open("tmp/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    return result