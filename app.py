import time
import pickle
from flask import Flask, request
from board import ScrabbleBoard
import random

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

@app.route('/start')
def start_game():
    # build dawg
    text_file = open("lexicon/scrabble_words_complete.txt", "r")
    big_list = text_file.read().splitlines()
    text_file.close()
    build_trie(big_list)
    root = build_dawg(big_list)
    file_handler = open("lexicon/scrabble_words_complete.pickle", "wb")
    pickle.dump(root, file_handler)
    file_handler.close()

    game = ScrabbleBoard(root)
    computer_hand = game.get_computer_hand()
    player_hand = game.get_player_hand()
    tiles = game.get_tiles()

    file_handler = open("lexicon/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    return {'player_hand': player_hand, 'computer_hand': computer_hand, 'tiles': tiles}

@app.route('/get-computer-first-move')
def computer_make_start_move():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()
    result = game.get_start_move()
    file_handler = open("lexicon/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()
    game.print_board()
    return result

@app.route('/get-best-move')
def get_best_move():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()
    result = game.get_best_move()
    file_handler = open("lexicon/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()
    game.print_board()
    return result

@app.route('/get-tiles')
def get_tiles():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()
    result = game.get_tiles()
    return {'result': result}

@app.route('/get-computer-hand')
def get_computer_hand():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()
    result = game.get_computer_hand()
    return {'result': result}

@app.route('/get-player-hand')
def get_player_hand():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()
    result = game.get_player_hand()
    return {'result': result}

@app.route('/insert-letters', methods = ['POST'])
def insert_tiles():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()

    request_data = request.get_json()
    tiles = request_data['letters_and_coordinates']
    result = game.insert_letters(tiles)
    game.print_board()
    file_handler = open("lexicon/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    return result

@app.route('/dump-letters', methods = ['POST'])
def dump_letters():
    to_load = open("lexicon/game.pickle", "rb")
    game = pickle.load(to_load)
    to_load.close()

    request_data = request.get_json()
    letters = request_data['letters']
    result = game.dump_letters(letters)
    game.print_board()
    print(result)
    file_handler = open("lexicon/game.pickle", "wb")
    pickle.dump(game, file_handler)
    file_handler.close()

    return result