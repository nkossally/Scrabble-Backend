import pickle
import redis
from flask import Flask, request
from board import ScrabbleBoard
import random
import uuid

app = Flask(__name__)

def build_trie(lexicon):
    num_nodes = 1
    trie = {0: {}}
    next_node = 1
    for word in lexicon:
        curr_node = 0
        for let in word:
            # if letter is present, move down its edge to next node
            if let in trie[curr_node]:
                edge_dict = trie[curr_node]
                curr_node = edge_dict[let]
            # otherwise, create new node and store its edge in current node
            # then move to it
            else:
                num_nodes += 1
                trie[next_node] = {}
                trie[curr_node][let] = next_node
                curr_node = next_node
                next_node += 1
        trie[curr_node]["END"] = True

    print(num_nodes)
    return trie

# Define a node to be stored in DAWG
class Node:
    next_id = 0

    def __init__(self):
        self.is_terminal = False
        self.id = Node.next_id
        Node.next_id += 1
        self.children = {}

    def __str__(self):
        out = [f"Node {self.id}\nChildren:\n"]
        letter_child_dict = self.children.items()
        for letter, child in letter_child_dict:
            out.append(f" {letter} -> {child.id}\n")
        return " ".join(out)

    def __repr__(self):
        out = []
        if self.is_terminal:
            out.append("1")
        else:
            out.append("0")
        for key, val in self.children.items():
            out.append(key)
            out.append(str(val.id))
        return "_".join(out)

    def __hash__(self):
        return self.__repr__().__hash__()

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

# returns length of common prefix
def length_common_prefix(prev_word, word):
    shared_prefix_length = 0
    for letter1, letter2 in (zip(prev_word, word)):
        if letter1 == letter2:
            shared_prefix_length += 1
        else:
            return shared_prefix_length
    return shared_prefix_length

# minimization function
def minimize(curr_node, common_prefix_length, minimized_nodes, non_minimized_nodes):
    # Start at end of the non_minimized_node list. Then minimize nodes until lengths of
    # non_min_nodes and common_prefix are equal.
    for _ in range(len(non_minimized_nodes), common_prefix_length, -1):

        parent, letter, child = non_minimized_nodes.pop()

        if child in minimized_nodes:
            parent.children[letter] = minimized_nodes[child]

        else:
            minimized_nodes[child] = child

        curr_node = parent

    return curr_node

# function to build dawg from given lexicon
def build_dawg(lexicon):
    root = Node()
    minimized_nodes = {root: root}
    non_minimized_nodes = []
    curr_node = root
    prev_word = ""
    for i, word in enumerate(lexicon):
        # get common prefix of new word and previous word
        common_prefix_length = length_common_prefix(prev_word, word)

        # minimization step: only call minimize if there are nodes in non_minimized_nodes
        if non_minimized_nodes:
            curr_node = minimize(curr_node, common_prefix_length, minimized_nodes, non_minimized_nodes)

        # adding new nodes after the common prefix
        for letter in word[common_prefix_length:]:
            next_node = Node()
            curr_node.children[letter] = next_node
            non_minimized_nodes.append((curr_node, letter, next_node))
            curr_node = next_node

        # by the end of this process, curr_node should always be a terminal node
        curr_node.is_terminal = True
        prev_word = word
        # if i % 1000 == 0:
        #     print(i)

    minimize(curr_node, 0, minimized_nodes, non_minimized_nodes)
    print(len(minimized_nodes))
    return root

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

    for key in r.scan_iter("prefix:*"):
        print("deleting key")
        print(key)
        r.delete(key)

    r.flushall()

    key = str(uuid.uuid4())
    key = "game"

    pickled_game = pickle.dumps(game)
    # set Redis key to expire in two hours
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

# Alternative for local development is storing serialized game locally, just using pickle and not Redis.

# @app.route('/start')
# def start_game():
#     # build dawg
#     r = redis.Redis(
#         host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
#         port=14591,
#         password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
#     text_file = open("lexicon/scrabble_words_complete.txt", "r")
#     big_list = text_file.read().splitlines()
#     text_file.close()
#     build_trie(big_list)
#     root = build_dawg(big_list)
#     pickled_root = pickle.dumps(root)
#     r.set('dawg', pickled_root)

#     game = ScrabbleBoard(root)
#     computer_hand = game.get_computer_hand()
#     player_hand = game.get_player_hand()
#     tiles = game.get_tiles()

#     pickled_game = pickle.dumps(game)
#     r.set('game', pickled_game)

#     return {'player_hand': player_hand, 'computer_hand': computer_hand, 'tiles': tiles}

# @app.route('/get-computer-first-move')
# def computer_make_start_move():
#     r = redis.Redis(
#         host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
#         port=14591,
#         password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
#     game = pickle.loads(r.get('game'))

#     result = game.get_start_move()
   
#     pickled_game = pickle.dumps(game)
#     r.set('game', pickled_game)

#     game.print_board()
#     return result

# @app.route('/get-best-move')
# def get_best_move():
#     r = redis.Redis(
#         host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
#         port=14591,
#         password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
#     game = pickle.loads(r.get('game'))

#     result = game.get_best_move()

#     pickled_game = pickle.dumps(game)
#     r.set('game', pickled_game)

#     game.print_board()
#     return result

# @app.route('/insert-letters', methods = ['POST'])
# def insert_tiles():
#     r = redis.Redis(
#         host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
#         port=14591,
#         password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
#     game = pickle.loads(r.get('game'))

#     request_data = request.get_json()
#     tiles = request_data['letters_and_coordinates']
#     result = game.insert_letters(tiles)
#     game.print_board()

#     pickled_game = pickle.dumps(game)
#     r.set('game', pickled_game)

#     return result

# @app.route('/dump-letters', methods = ['POST'])
# def dump_letters():
#     r = redis.Redis(
#         host='redis-14591.c261.us-east-1-4.ec2.redns.redis-cloud.com',
#         port=14591,
#         password='pfFOtNMBlIPZ2XqAGgt3NbJm7n38brgh')
#     game = pickle.loads(r.get('game'))


#     request_data = request.get_json()
#     letters = request_data['letters']
#     result = game.dump_letters(letters)
#     game.print_board()
#     print(result)

#     pickled_game = pickle.dumps(game)
#     r.set('game', pickled_game)

#     return result