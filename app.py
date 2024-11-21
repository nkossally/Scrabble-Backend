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
    host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
    port=14591,
    password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
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

    # for key in r.scan_iter("prefix:*"):
    #     print("deleting key")
    #     print(key)
    #     r.delete(key)

    # r.flushall()

    # key = str(uuid.uuid4())
    key = "game"

    pickled_game = pickle.dumps(game)
    # set Redis key to expire in 30 minutes
    r.set(key, pickled_game, ex=18000)

    return {'player_hand': player_hand, 'computer_hand': computer_hand, 'tiles': tiles, 'key': key}

@app.route('/get-computer-first-move')
def computer_make_start_move():
    key = request.args.get('key') 
    key = "game"

    game = pickle.loads(r.get(key))

    result = game.get_start_move()
   
    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=18000)

    game.print_board()
    return result

@app.route('/get-best-move')
def get_best_move():
    key = request.args.get('key') 
    key = "game"

    game = pickle.loads(r.get(key))

    result = game.get_move()

    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=18000)

    game.print_board()
    return result

@app.route('/insert-letters', methods = ['POST'])
def insert_tiles():
    request_data = request.get_json()
    tiles = request_data['letters_and_coordinates']
    key = request_data['key']
    key = "game"
    max_word = request_data['max_word']
    start_row = request_data['start_row']
    start_col = request_data['start_col']
    is_vertical = request_data['is_vertical']

    game = pickle.loads(r.get(key))
    result = game.insert_letters(tiles, max_word, start_row, start_col, is_vertical)
    game.print_board()

    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=18000)

    return result

@app.route('/dump-letters', methods = ['POST'])
def dump_letters():
    request_data = request.get_json()
    key = request_data['key']
    key = "game"
    game = pickle.loads(r.get(key))


    request_data = request.get_json()
    letters = request_data['letters']
    result = game.dump_letters(letters)
    game.print_board()

    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=18000)

    return result
