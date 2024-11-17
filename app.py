import pickle
import redis
import uuid
from flask_cors import CORS
from flask import Flask, request
from board import ScrabbleBoard
from dawg import build_dawg, build_trie

app = Flask(__name__)
CORS(app)

@app.route('/')
def get_home():
    return 'homepage'

@app.route('/start')
def start_game():
    # build dawg
    r = redis.Redis(
        host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
        port=14591,
        password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
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
    r.set('key', pickled_game, ex=1800)

    return {'player_hand': player_hand, 'computer_hand': computer_hand, 'tiles': tiles, 'key': key}

@app.route('/get-computer-first-move')
def computer_make_start_move():
    r = redis.Redis(
        host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
        port=14591,
        password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
    
    key = request.args.get('key') 
    key = "game"

    game = pickle.loads(r.get('key'))

    result = game.get_start_move()
   
    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=1800)

    game.print_board()
    return result

@app.route('/get-best-move')
def get_best_move():
    r = redis.Redis(
        host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
        port=14591,
        password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')

    key = request.args.get('key') 
    key = "game"

    print("printing key")
    print(key)
    game = pickle.loads(r.get(key))

    result = game.get_best_move()

    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=1800)

    game.print_board()
    return result

@app.route('/insert-letters', methods = ['POST'])
def insert_tiles():
    r = redis.Redis(
        host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
        port=14591,
        password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')

    request_data = request.get_json()
    tiles = request_data['letters_and_coordinates']
    key = request_data['key']
    key = "game"
    game = pickle.loads(r.get(key))
    result = game.insert_letters(tiles)
    game.print_board()

    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=1800)

    return result

@app.route('/dump-letters', methods = ['POST'])
def dump_letters():
    r = redis.Redis(
        host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
        port=14591,
        password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')

    request_data = request.get_json()
    key = request_data['key']
    key = "game"
    game = pickle.loads(r.get(key))


    request_data = request.get_json()
    letters = request_data['letters']
    result = game.dump_letters(letters)
    game.print_board()
    print(result)

    pickled_game = pickle.dumps(game)
    r.set(key, pickled_game, ex=1800)

    return result