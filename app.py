import pickle
import redis
import uuid
from flask_cors import CORS
from flask import Flask, request
from board import ScrabbleBoard
from dawg import build_dawg, build_trie

app = Flask(__name__)
CORS(app)
r = redis.Redis(
    host='redis-12426.c275.us-east-1-4.ec2.redns.redis-cloud.com',
    port=12426,
    password='EOde9z4DNswjnXTvph1MIS3rDeSHXkK8')
# r = redis.Redis(host='127.0.0.1', port=6379, db=0)

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

    key = "game"

    pickled_root = pickle.dumps(root)
    # set Redis key to expire in 30 minutes
    r.set(key, pickled_root, ex=18000)

    return { 'player_hand': player_hand, 'computer_hand': computer_hand, 'tiles': tiles, 'key': key }

@app.route('/get-computer-first-move')
def computer_make_start_move():
    key = "game"

    root = pickle.loads(r.get(key))
   
    game = ScrabbleBoard(root)

    result = game.get_start_move()

    game.print_board()
    return result

@app.route('/get-best-move', methods = ['POST'])
def get_best_move():
    request_data = request.get_json()
    key = "game"
    board_values = request_data["board_values"]
    hand = request_data["hand"]
    computer_hand = request_data["computer_hand"]
    tile_bag = request_data["tile_bag"]

    print(board_values)

    root = pickle.loads(r.get(key))
    game = ScrabbleBoard(root)

    game.insert_board_values(board_values)
    game.set_computer_hand(computer_hand)
    game.set_player_hand(hand)
    game.set_tile_bag(tile_bag)

    result = game.get_move()

    game.print_board()
    return result

@app.route('/insert-letters', methods = ['POST'])
def insert_tiles():
    request_data = request.get_json()
    tiles = request_data['letters_and_coordinates']
    key = "game"
    max_word = request_data['max_word']
    start_row = request_data['start_row']
    start_col = request_data['start_col']
    is_vertical = request_data['is_vertical']
    board_values = request_data["board_values"]
    hand = request_data["hand"]
    computer_hand = request_data["computer_hand"]
    tile_bag = request_data["tile_bag"]

    root = pickle.loads(r.get(key))
    game = ScrabbleBoard(root)

    game.insert_board_values(board_values)
    game.set_computer_hand(computer_hand)
    game.set_player_hand(hand)
    game.set_tile_bag(tile_bag)

    result = game.insert_letters(tiles, max_word, start_row, start_col, is_vertical)
    game.print_board()

    return result

@app.route('/dump-letters', methods = ['POST'])
def dump_letters():
    request_data = request.get_json()
    key = "game"

    board_values = request_data["board_values"]
    hand = request_data["hand"]
    computer_hand = request_data["computer_hand"]
    tile_bag = request_data["tile_bag"]

    root = pickle.loads(r.get(key))
    game = ScrabbleBoard(root)

    game.insert_board_values(board_values)
    game.set_computer_hand(computer_hand)
    game.set_player_hand(hand)
    game.set_tile_bag(tile_bag)

    letters = request_data['letters']

    result = game.dump_letters(letters)
    game.print_board()

    return result
