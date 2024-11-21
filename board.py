import regex as re
import random
import copy
from dawg import find_in_dawg, find_prefix_in_dawg


BOARD_SIZE = 15
LETTER_TO_SCORE = {
    'A': 1,
    'B': 3,
    'C': 3,
    'D': 2,
    'E': 1,
    'F': 4,
    'G': 2,
    'H': 4,
    'I': 1,
    'J': 8,
    'K': 5,
    'L': 1,
    'M': 3,
    'N': 1,
    'O': 1,
    'P': 3,
    'Q': 10,
    'R': 1,
    'S': 1,
    'T': 1,
    'U': 1,
    'V': 4,
    'W': 4,
    'X': 8,
    'Y': 4,
    'Z': 10,
}

tileScoreIdx = {
    'ct': [112],
    'tw': [0, 7, 14, 105, 119, 210, 217, 224],
    'tl': [20, 24, 76, 80, 84, 88, 136, 140, 144, 148, 200, 204],
    'dw': [16, 28, 32, 42, 48, 56, 64, 70, 154, 160, 168, 176, 182, 192, 196, 208],
    'dl': [
        3, 11, 36, 38, 45, 52, 59, 88, 92, 96, 98, 102, 108, 116, 122, 126, 128,
        132, 165, 172, 179, 186, 188, 213, 221,
    ],
}


class Square:
    # default behavior is blank square, no score modifier, all cross-checks valid
    def __init__(self, letter=None, modifier="Normal", sentinel=1):
        self.letter = letter
        self.cross_checks_0 = [sentinel] * 26
        self.cross_checks_1 = [sentinel] * 26
        self.cross_checks = self.cross_checks_0
        self.modifier = modifier
        self.visible = True
        if sentinel == 0:
            self.visible = False

    def __str__(self):
        if not self.visible:
            return ""
        if not self.letter:
            return "_"
        else:
            return self.letter

    # maintain two separate cross-check lists depending on if the board is transpose or not
    def check_switch(self, is_transpose):
        if is_transpose:
            self.cross_checks = self.cross_checks_1
        else:
            self.cross_checks = self.cross_checks_0


class ScrabbleBoard:
    def __init__(self, dawg_root):

        row_1 = \
            [Square(modifier="3WS"), Square(), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="3WS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(), Square(modifier="3WS"),
             Square(sentinel=0)]
        row_15 = copy.deepcopy(row_1)

        row_2 = \
            [Square(), Square(modifier="2WS"), Square(), Square(), Square(),
             Square(modifier="3LS"), Square(), Square(
            ), Square(), Square(modifier="3LS"),
                Square(), Square(), Square(), Square(modifier="2WS"), Square(),
                Square(sentinel=0)]
        row_14 = copy.deepcopy(row_2)

        row_3 = \
            [Square(), Square(), Square(modifier="2WS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="2WS"), Square(), Square(),
             Square(sentinel=0)]
        row_13 = copy.deepcopy(row_3)

        row_4 = \
            [Square(modifier="2LS"), Square(), Square(), Square(modifier="2WS"), Square(),
             Square(), Square(), Square(modifier="2LS"), Square(), Square(),
             Square(), Square(modifier="2WS"), Square(), Square(), Square(modifier="2LS"),
             Square(sentinel=0)]
        row_12 = copy.deepcopy(row_4)

        row_5 = \
            [Square(), Square(), Square(), Square(), Square(modifier="2WS"),
             Square(), Square(), Square(), Square(), Square(),
             Square(modifier="2WS"), Square(), Square(), Square(), Square(),
             Square(sentinel=0)]
        row_11 = copy.deepcopy(row_5)

        row_6 = \
            [Square(), Square(modifier="3LS"), Square(), Square(), Square(),
             Square(modifier="3LS"), Square(), Square(
            ), Square(), Square(modifier="3LS"),
                Square(), Square(), Square(), Square(modifier="3LS"), Square(),
                Square(sentinel=0)]
        row_10 = copy.deepcopy(row_6)

        row_7 = \
            [Square(), Square(), Square(modifier="2LS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="2LS"), Square(), Square(),
             Square(sentinel=0)]
        row_9 = copy.deepcopy(row_7)

        row_8 = \
            [Square(modifier="3WS"), Square(), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="2WS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(), Square(modifier="3WS"),
             Square(sentinel=0)]

        row_16 = [Square(sentinel=0) for _ in range(16)]

        # variables to describe board state
        self.board = [row_1, row_2, row_3, row_4, row_5, row_6, row_7, row_8,
                      row_9, row_10, row_11, row_12, row_13, row_14, row_15, row_16]

        self.point_dict = {"A": 1, "B": 3, "C": 3, "D": 2,
                           "E": 1, "F": 4, "G": 2, "H": 4,
                           "I": 1, "J": 8, "K": 5, "L": 1,
                           "M": 3, "N": 1, "O": 1, "P": 3,
                           "Q": 10, "R": 1, "S": 1, "T": 1,
                           "U": 1, "V": 4, "W": 4, "X": 8,
                           "Y": 8, "Z": 10, "%": 0}

        self.words_on_board = []

        self.is_transpose = False

        # variables to encode best word on a given turn
        self.dawg_root = dawg_root
        self.word_rack = []
        self.word_score_dict = {}
        self.best_word = ""
        self.best_word_is_vertical = True
        self.highest_score = 0
        self.dist_from_anchor = 0
        self.letters_from_rack = []

        # rows and columns of highest-scoring word found so far.
        # these are the rows and columns of the tile already on the board
        self.best_row = 0
        self.best_col = 0

        # store squares that need updated cross-checks
        self.upper_cross_check = []
        self.lower_cross_check = []

        self.tile_bag = ["A"] * 9 + ["B"] * 2 + ["C"] * 2 + ["D"] * 4 + ["E"] * 12 + ["F"] * 2 + ["G"] * 3 + \
            ["H"] * 2 + ["I"] * 9 + ["J"] * 1 + ["K"] * 1 + ["L"] * 4 + ["M"] * 2 + ["N"] * 6 + \
            ["O"] * 8 + ["P"] * 2 + ["Q"] * 1 + ["R"] * 6 + ["S"] * 4 + ["T"] * 6 + ["U"] * 4 + \
            ["V"] * 2 + ["W"] * 2 + ["X"] * 1 + ["Y"] * 2 + ["Z"] * 1

        self.computer_word_rack = random.sample(self.tile_bag, 7)
        [self.tile_bag.remove(letter) for letter in self.computer_word_rack]

        self.player_word_rack = random.sample(self.tile_bag, 7)
        [self.tile_bag.remove(letter) for letter in self.player_word_rack]

    def get_tiles(self):
        return self.tile_bag

    def get_player_hand(self):
        return self.player_word_rack

    def get_computer_hand(self):
        return self.computer_word_rack

    # transpose method that modifies self.board inplace
    def _transpose(self):
        # https://datagy.io/python-transpose-list-of-lists/
        transposed_tuples = copy.deepcopy(list(zip(*self.board)))
        self.board = [list(sublist) for sublist in transposed_tuples]
        self.is_transpose = not self.is_transpose
    
    def map_square(self, square):
        return square.letter

    # TODO: fix scoring errors
    def _score_word(self, word, squares, dist_from_anchor):
        print("score word" )
        print(" word", word )
        print("squares", squares)
        print("dist_from_anchor", dist_from_anchor )
        print("map", list(map(self.map_square, squares )))
    
        score = 0
        score_multiplier = 1

        if self.is_transpose:
            cross_sum_ind = "-"
        else:
            cross_sum_ind = "+"

        # word that will be inserted onto board shouldn't have wildcard indicator
        board_word = word.replace("%", "")

        # don't add words that are already on the board
        if board_word in self.words_on_board:
            return board_word, 0

        # remove letters before wildcard indicators
        word = re.sub("[A-Z]%", "%", word)

        # maintain list of which tiles were pulled from word rack
        rack_tiles = []
        for letter, square in zip(word, squares):
            # add cross-sum by adding first and second letter scores from orthogonal two-letter word
            if cross_sum_ind in square.modifier:
                score += int(square.modifier[-1])
            if square.modifier:
                rack_tiles.append(letter)
            if "2LS" in square.modifier:
                score += (self.point_dict[letter] * 2)
            elif "3LS" in square.modifier:
                score += (self.point_dict[letter] * 3)
            elif "2WS" in square.modifier:
                score_multiplier *= 2
                score += self.point_dict[letter]
            elif "3WS" in square.modifier:
                score_multiplier *= 3
                score += self.point_dict[letter]
            else:
                score += self.point_dict[letter]

        score *= score_multiplier

        # check for bingo
        if len(rack_tiles) == 7:
            score += 50

        if score > self.highest_score:
            self.best_word = board_word
            self.highest_score = score
            # distance of leftmost placed tile from anchor. if anchor is leftmost tile distance will be 0.
            self.dist_from_anchor = dist_from_anchor
            self.letters_from_rack = rack_tiles

    def _extend_right(self, start_node, square_row, square_col, rack, word, squares, dist_from_anchor):
        square = self.board[square_row][square_col]
        square.check_switch(self.is_transpose)

        # execute if square is empty
        if not square.letter:
            if start_node.is_terminal:
                self._score_word(word, squares, dist_from_anchor)
            for letter in start_node.children:
                # if square already has letters above and below it, don't try to extend
                if self.board[square_row + 1][square_col].letter and self.board[square_row - 1][square_col].letter:
                    continue

                # conditional for blank squares
                if letter in rack:
                    wildcard = False
                elif "%" in rack:
                    wildcard = True
                else:
                    continue
                if letter in rack and self._cross_check(letter, square):
                    new_node = start_node.children[letter]

                    
                    new_rack = rack.copy()
                    if wildcard:
                        new_word = word + letter + "%"
                        new_rack.remove("%")
                    else:
                        new_word = word + letter
                        new_rack.remove(letter)
                    new_squares = squares + [square]
                    self._extend_right(new_node, square_row, square_col + 1, new_rack, new_word, new_squares,
                                       dist_from_anchor)
        else:
            if square.letter in start_node.children:
                new_node = start_node.children[square.letter]
                new_word = word + square.letter
                new_squares = squares + [square]
                self._extend_right(new_node, square_row, square_col + 1, rack, new_word, new_squares,
                                   dist_from_anchor)

    def _left_part(self, start_node, anchor_square_row, anchor_square_col, rack, word, squares, limit,
                   dist_from_anchor):
        potential_square = self.board[anchor_square_row][anchor_square_col - dist_from_anchor]
        potential_square.check_switch(self.is_transpose)
        if potential_square.letter:
            return
        self._extend_right(start_node, anchor_square_row,
                           anchor_square_col, rack, word, squares, dist_from_anchor)
        if 0 in potential_square.cross_checks:
            return
        if limit > 0:
            for letter in start_node.children:
                # conditional for blank squares
                if letter in rack:
                    wildcard = False
                elif "%" in rack:
                    wildcard = True
                else:
                    continue

                new_node = start_node.children[letter]
                new_rack = rack.copy()
                if wildcard:
                    new_word = word + letter + "%"
                    new_rack.remove("%")
                else:
                    new_word = word + letter
                    new_rack.remove(letter)
                new_squares = squares + [potential_square]
                self._left_part(new_node, anchor_square_row, anchor_square_col, new_rack, new_word, new_squares,
                                limit - 1, dist_from_anchor + 1)

    def _update_cross_checks(self):
        while self.upper_cross_check:
            curr_square, lower_letter, lower_row, lower_col = self.upper_cross_check.pop()
            curr_square.check_switch(self.is_transpose)

            # add to modifier for computing cross-sum
            if self.is_transpose:
                curr_square.modifier += f"-{self.point_dict[lower_letter]}"
            else:
                curr_square.modifier += f"+{self.point_dict[lower_letter]}"

            chr_val = 65
            # prevent cross stacking deeper than 2 layers
            if curr_square.letter:
                if not self.is_transpose:
                    self.board[lower_row -
                               2][lower_col].cross_checks_0 = [0] * 26
                    self.board[lower_row +
                               1][lower_col].cross_checks_0 = [0] * 26

                else:
                    self.board[lower_row -
                               2][lower_col].cross_checks_1 = [0] * 26
                    self.board[lower_row +
                               1][lower_col].cross_checks_1 = [0] * 26
                continue

            for i, ind in enumerate(curr_square.cross_checks):
                if ind == 1:
                    test_node = self.dawg_root.children[chr(chr_val)]
                    if (lower_letter not in test_node.children) or (not test_node.children[lower_letter].is_terminal):
                        curr_square.cross_checks[i] = 0
                chr_val += 1

        while self.lower_cross_check:
            curr_square, upper_letter, upper_row, upper_col = self.lower_cross_check.pop()
            curr_square.check_switch(self.is_transpose)

            # add to modifier for computing cross-sum
            if self.is_transpose:
                curr_square.modifier += f"-{self.point_dict[upper_letter]}"
            else:
                curr_square.modifier += f"+{self.point_dict[upper_letter]}"

            chr_val = 65
            # prevent cross stacking deeper than 2 layers
            if curr_square.letter:
                if not self.is_transpose:
                    self.board[upper_row -
                               1][upper_col].cross_checks_0 = [0] * 26
                    self.board[upper_row +
                               2][upper_col].cross_checks_0 = [0] * 26
                else:
                    self.board[upper_row -
                               1][upper_col].cross_checks_1 = [0] * 26
                    self.board[upper_row +
                               2][upper_col].cross_checks_1 = [0] * 26
                continue

            for i, ind in enumerate(curr_square.cross_checks):
                if ind == 1:
                    test_node = self.dawg_root.children[upper_letter]
                    if (chr(chr_val) not in test_node.children) or (not test_node.children[chr(chr_val)].is_terminal):
                        curr_square.cross_checks[i] = 0
                chr_val += 1

    def _cross_check(self, letter, square):
        square.check_switch(self.is_transpose)
        chr_val = 65
        for i, ind in enumerate(square.cross_checks):
            if ind == 1:
                if chr(chr_val) == letter:
                    return True
            chr_val += 1
        return False

    def print_board(self):
        print("    ", end="")
        [print(str(num).zfill(2), end=" ") for num in range(1, 16)]
        print()
        for i, row in enumerate(self.board):
            if i != 15:
                print(str(i + 1).zfill(2), end="  ")
            [print(square, end="  ") for square in row]
            print()
        print()
    
    def insert_best_word(self):
        letters = []
        old_computer_word_rack =  self.computer_word_rack.copy()
        word_rack = self.computer_word_rack
        curr_row = self.best_row
        curr_col = self.best_col
        for letter in self.best_word:
            if not self.board[curr_row][curr_col].letter:
                self.board[curr_row][curr_col].letter = letter
                letters.append(letter)
                if letter in word_rack:
                    word_rack.remove(letter)
            if self.best_word_is_vertical:
                curr_row += 1
            else:
                curr_col += 1

        word_rack, new_letters = refill_word_rack(word_rack, self.tile_bag)
        [self.tile_bag.remove(letter) for letter in new_letters]
        self.computer_word_rack = word_rack

        return {'word': self.best_word, 'computer_word_rack': word_rack, 'tile_bag': self.tile_bag, 'row': self.best_row, 'col': self.best_col, 'used_letters': letters, 'is_vertical': self.best_word_is_vertical, 'old_computer_word_rack': old_computer_word_rack, 'score': self.highest_score}


    def insert_letters(self, letters_and_coordinates, max_word, start_row, start_col, is_vertical):
        letters = []
        word_rack = self.player_word_rack
        for letter_and_coordinate in letters_and_coordinates:
            letter = letter_and_coordinate['letter']
            row = letter_and_coordinate['row']
            col = letter_and_coordinate['col']
            self.board[row][col].modifier = ""
            self.board[row][col].letter = letter
            letters.append(letter)
            if letter in word_rack:
                word_rack.remove(letter)

            # once letter is inserted, add squares above and below it to cross_check_queue
            if is_vertical:
                if col > 0:
                    self.upper_cross_check.append(
                        (self.board[row][col - 1], letter, row, col))
                if col < 15:
                    self.lower_cross_check.append(
                        (self.board[row][col + 1], letter, row, col))
            else:
                if row > 0:
                    self.upper_cross_check.append(
                        (self.board[row - 1][col], letter, row, col))
                if row < 15:
                    self.lower_cross_check.append(
                        (self.board[row + 1][col], letter, row, col))

        word_rack, new_letters = refill_word_rack(word_rack, self.tile_bag)
        [self.tile_bag.remove(letter) for letter in new_letters]
        self.player_word_rack = word_rack
        # # place 0 cross-check sentinel at the beginning and end of inserted words to stop accidental overlap.
        # # sentinels should only be for the board state opposite from the one the board is currently in
        if is_vertical:
            if start_row + len(max_word) < 15:
                self.board[start_row +
                           len(max_word)][start_col].cross_checks_1 = [0] * 26
            if start_row > 0:
                self.board[start_row - 1][start_col].cross_checks_1 = [0] * 26
        else:
            if start_col + len(max_word) < 15:
                self.board[start_row][start_col +
                                      len(max_word)].cross_checks_0 = [0] * 26
            if start_col > 0:
                self.board[start_row][start_col - 1].cross_checks_0 = [0] * 26

        self._update_cross_checks()

        self.words_on_board.append(max_word)

        return {'player_word_rack': self.player_word_rack, 'tile_bag': self.tile_bag}

    def dump_letters(self, letters):
        word_rack = self.player_word_rack
        renove_items_from_list(word_rack, letters)
        [self.tile_bag.append(letter) for letter in letters]
        word_rack, new_letters = refill_word_rack(word_rack, self.tile_bag)
        [self.tile_bag.remove(letter) for letter in new_letters]
        renove_items_from_list(self.tile_bag, new_letters)
        self.player_word_rack = word_rack
        return {'player_word_rack': self.player_word_rack, 'tile_bag': self.tile_bag}

    # method to insert words into board by row and column number
    # using 1-based indexing for user input
    def insert_word(self, row, col, word):
        row -= 1
        col -= 1
        if len(word) + col > 15:
            print(f'Cannot insert word "{word}" at column {col + 1}, '
                  f'row {row + 1} not enough space')
            return
        curr_col = col
        modifiers = []
        for i, letter in enumerate(word):
            curr_square_letter = self.board[row][curr_col].letter
            modifiers.append(self.board[row][curr_col].modifier)
            # if current square already has a letter in it, check to see if it's the same letter as
            # the one we're trying to insert. If not, insertion fails, undo any previous insertions
            if curr_square_letter:
                if curr_square_letter == letter:
                    if row > 0:
                        self.upper_cross_check.append(
                            (self.board[row - 1][curr_col], letter, row, curr_col))
                    if row < 15:
                        self.lower_cross_check.append(
                            (self.board[row + 1][curr_col], letter, row, curr_col))

                    curr_col += 1
                else:
                    print(f'Failed to insert letter "{letter}" of "{word}" at column {curr_col + 1}, '
                          f'row {row + 1}. Square is occupied by letter "{curr_square_letter}"')
                    self.upper_cross_check = []
                    self.lower_cross_check = []
                    for _ in range(i):
                        curr_col -= 1
                        self.board[row][curr_col].letter = None
                        self.board[row][curr_col].modifier = modifiers.pop()
                    return
            else:
                self.board[row][curr_col].letter = letter

                # reset any modifiers to 0 once they have a tile placed on top of them
                self.board[row][curr_col].modifier = ""

                # once letter is inserted, add squares above and below it to cross_check_queue
                if row > 0:
                    self.upper_cross_check.append(
                        (self.board[row - 1][curr_col], letter, row, curr_col))
                if row < 15:
                    self.lower_cross_check.append(
                        (self.board[row + 1][curr_col], letter, row, curr_col))

                curr_col += 1

        virtual_board = [["" for x in range(BOARD_SIZE)] for y in range(BOARD_SIZE)]
        curr_row = row
        curr_col = col

        
        for i in range(len(word)):
            virtual_board[curr_row][curr_col] = word[i]
            if True:
                curr_col += 1
            else:
                curr_row += 1
        result = self.checkAllWordsOnBoard(virtual_board, None, word)

        # place 0 cross-check sentinel at the beginning and end of inserted words to stop accidental overlap.
        # sentinels should only be for the board state opposite from the one the board is currently in
        if curr_col < 15:
            if self.is_transpose:
                self.board[self.best_row][curr_col].cross_checks_0 = [0] * 26
            else:
                self.board[self.best_row][curr_col].cross_checks_1 = [0] * 26
        if col - 1 > - 1:
            if self.is_transpose:
                self.board[self.best_row][col - 1].cross_checks_0 = [0] * 26
            else:
                self.board[self.best_row][col - 1].cross_checks_1 = [0] * 26

        self._update_cross_checks()

        self.words_on_board.append(word)

    # gets all words that can be made using a selected filled square and the current word rack
    def get_all_words(self, square_row, square_col, rack):
        square_row -= 1
        square_col -= 1

        # get all words that start with the filled letter
        self._extend_right(self.dawg_root, square_row,
                           square_col, rack, "", [], 0)

        # create anchor square only if the space is empty
        if self.board[square_row][square_col - 1].letter:
            return

        # try every letter in rack as possible anchor square
        for i, letter in enumerate(rack):
            # Only allow anchor square with trivial cross-checks
            potential_square = self.board[square_row][square_col - 1]
            potential_square.check_switch(self.is_transpose)
            if 0 in potential_square.cross_checks or potential_square.letter:
                continue
            temp_rack = rack[:i] + rack[i + 1:]
            self.board[square_row][square_col - 1].letter = letter
            self._left_part(self.dawg_root, square_row,
                            square_col - 1, temp_rack, "", [], 6, 1)

        # reset anchor square spot to blank after trying all combinations
        self.board[square_row][square_col - 1].letter = None

    # scan all tiles on board in both transposed and non-transposed state, find best move
    def get_best_move(self):

        old_computer_word_rack = self.computer_word_rack.copy()
        word_rack = self.computer_word_rack

        # clear out cross-check lists before adding new words
        self._update_cross_checks()

        # reset word variables to clear out words from previous turns
        self.best_word = ""
        self.highest_score = 0
        self.best_row = 0
        self.best_col = 0

        transposed = False
        for row in range(0, 15):
            for col in range(0, 15):
                curr_square = self.board[row][col]
                if curr_square.letter and (not self.board[row][col - 1].letter):
                    prev_best_score = self.highest_score
                    self.get_all_words(row + 1, col + 1, word_rack)
                    if self.highest_score > prev_best_score:
                        self.best_row = row
                        self.best_col = col

        self._transpose()
        for row in range(0, 15):
            for col in range(0, 15):
                curr_square = self.board[row][col]
                if curr_square.letter and (not self.board[row][col - 1].letter):
                    prev_best_score = self.highest_score
                    self.get_all_words(row + 1, col + 1, word_rack)
                    if self.highest_score > prev_best_score:
                        transposed = True
                        self.best_row = row
                        self.best_col = col

        # Don't try to insert word if we couldn't find one
        if not self.best_word:
            self._transpose()
            return {}

        if transposed:
            self.insert_word(self.best_row + 1, self.best_col +
                             1 - self.dist_from_anchor, self.best_word)
            self._transpose()
        else:
            self._transpose()
            self.insert_word(self.best_row + 1, self.best_col +
                             1 - self.dist_from_anchor, self.best_word)

        self.word_score_dict[self.best_word] = self.highest_score

        for letter in self.letters_from_rack:
            if letter in word_rack:
                word_rack.remove(letter)

        word_rack, new_letters = refill_word_rack(word_rack, self.tile_bag)
        [self.tile_bag.remove(letter) for letter in new_letters]
        self.computer_word_rack = word_rack

        col = self.best_col - self.dist_from_anchor if not transposed else self.best_row
        row = self.best_row if not transposed else self.best_col - self.dist_from_anchor

        return {'word': self.best_word, 'computer_word_rack': self.computer_word_rack, 'tile_bag': self.tile_bag, 'row': row, 'col': col, 'used_letters': self.letters_from_rack, 'is_vertical': transposed, 'old_computer_word_rack': old_computer_word_rack}

    def get_start_move(self):
        # board symmetrical at start so just always play the start move horizontally
        # try every letter in rack as possible anchor square
        old_computer_word_rack = self.computer_word_rack.copy()
        word_rack = self.computer_word_rack
        self.best_row = 7
        self.best_col = 8
        for i, letter in enumerate(word_rack):
            potential_square = self.board[7][8]
            temp_rack = word_rack[:i] + word_rack[i + 1:]
            potential_square.letter = letter
            self._left_part(self.dawg_root, 7, 8, temp_rack, "", [], 6, 1)

        # reset anchor square spot to blank after trying all combinations
        self.board[7][8].letter = None
        self.insert_word(self.best_row + 1, self.best_col +
                         1 - self.dist_from_anchor, self.best_word)
        self.board[7][8].modifier = ""
        self.word_score_dict[self.best_word] = self.highest_score

        for letter in self.letters_from_rack:
            if letter in word_rack:
                word_rack.remove(letter)

        word_rack, new_letters = refill_word_rack(word_rack, self.tile_bag)
        [self.tile_bag.remove(letter) for letter in new_letters]
        self.computer_word_rack = word_rack

        return {'computer_word_rack': self.computer_word_rack, 'old_computer_word_rack': old_computer_word_rack, 'tile_bag': self.tile_bag, 'row': self.best_row, 'col': self.best_col - self.dist_from_anchor, 'word': self.best_word}

    def get_is_valid_word(self, word):
        # result = find_in_dawg(word, self.dawg_root)
        result = find_prefix_in_dawg(word, self.dawg_root)
        return {'result': result}
    
    def checkAllWordsOnBoard(
        self,
        virtualBoard,
        tempBoardValues, 
        word_placed
    ):
        rowsAndCols = getPlacedLettersRowsAndCols(
            virtualBoard, tempBoardValues)
        rows = rowsAndCols['rows']
        cols = rowsAndCols['cols']
        score = 0
        word = ""
        maxWord = ""
        start_row = None
        start_col = None
        isVertical = None
    #    if the word is vertical
        if len(cols) == 1:
            col = cols[0]
            wordAndScore = self.getVerticalWordAtCoordinate(
                rows[0],
                col,
                virtualBoard,
                tempBoardValues
            )
            word = wordAndScore['word']
            if len(word) > len(maxWord):
                maxWord = word
                start_row = wordAndScore['start_row']
                start_col = wordAndScore['start_col']
                isVertical = True

            if len(word) > 1:
                score += wordAndScore['word_score']
                isValidWord = find_in_dawg(word, self.dawg_root)
                if not isValidWord:
                    return False

    #  check if any of the letters in a vertical word adjoin an already placed horizontal words.
            for i in range(len(rows)):
                row = rows[i]
                wordAndScore = self.getHorizontalWordAtCoordinate(
                    row,
                    col,
                    virtualBoard,
                    tempBoardValues
                )
                if wordAndScore:
                    word = wordAndScore['word']
                    if len(word) > len(maxWord):
                        maxWord = word
                        start_row = wordAndScore['start_row']
                        start_col = wordAndScore['start_col']
                        isVertical = False
                    if len(word) > 1:
                        score += wordAndScore['word_score']
                        isValidWord = find_in_dawg(word, self.dawg_root)
                        if not isValidWord:
                            return False

        else:
            #  word is horizontal
            row = rows[0]
            wordAndScore = self.getHorizontalWordAtCoordinate(
                row,
                cols[0],
                virtualBoard,
                tempBoardValues
            )
            word = wordAndScore['word']
            if len(word) > len(maxWord):
                maxWord = word
                start_row = wordAndScore['start_row']
                start_col = wordAndScore['start_col']
                isVertical = False

            if len(word) > 1:
                score += wordAndScore['word_score']
                isValidWord = find_in_dawg(word, self.dawg_root)

                if not isValidWord:
                    return False
            for i in range(len(cols)):

                col = cols[i]
                wordAndScore = self.getVerticalWordAtCoordinate(
                    row,
                    col,
                    virtualBoard,
                    tempBoardValues
                )
                if wordAndScore:
                    word = wordAndScore['word']
                    if len(word) > len(maxWord):
                        maxWord = word
                        start_row = wordAndScore['start_row']
                        start_col = wordAndScore['start_col']
                        isVertical = False
                    if len(word) > 1:
                        isValidWord = find_in_dawg(word, self.dawg_root)
                        score += wordAndScore['word_score']
                        if not isValidWord:
                            return False

        tempLetterArr = getAllTempLetters(virtualBoard, tempBoardValues)
        maybeFifty = 50 if len(tempLetterArr) == 7 else 0

    #   don't submit any one letter words
        if len(maxWord) < 2:
            return False

        return {'score': score + maybeFifty, 'maxWord': maxWord, 'start_row': start_row, 'start_col': start_col, 'isVertical': isVertical}



    def getVerticalWordAtCoordinate(
        self,
        x,
        y,
        virtualBoard,
        tempBoardValues,
    ):
        currX = x
        word = ""
        word_score = 0
        multiplier = 1
        start_row = x
        start_col = y
        while (
            getTempLetterAtCoordinate(currX, y, tempBoardValues) or
            self.getLetterAtCoordinate(currX, y) or
            getTempLetterOnVirtualBoard(currX, y, virtualBoard)
        ):
            word += (getTempLetterAtCoordinate(currX, y, tempBoardValues) or
                    self.getLetterAtCoordinate(currX, y) or
                    getTempLetterOnVirtualBoard(currX, y, virtualBoard))
            letterScoreObj = self.calculateScoreFromLetter(
                currX,
                y,
                virtualBoard,
                None,
                tempBoardValues,
            )
            word_score += letterScoreObj['letterPoints']
            multiplier *= letterScoreObj['wordMultiplier']
            currX += 1
        currX = x - 1
        while getTempLetterAtCoordinate(currX, y, tempBoardValues) or self.getLetterAtCoordinate(currX, y) or getTempLetterOnVirtualBoard(currX, y, virtualBoard):
            word = (getTempLetterAtCoordinate(currX, y, tempBoardValues) or
                    self.getLetterAtCoordinate(currX, y) or
                    getTempLetterOnVirtualBoard(currX, y, virtualBoard)) + word
            letterScoreObj = self.calculateScoreFromLetter(
                currX,
                y,
                virtualBoard,
                None,
                tempBoardValues,
            )
            word_score += letterScoreObj['letterPoints']
            multiplier *= letterScoreObj['wordMultiplier']
            start_row = currX
            currX -= 1
        word_score *= multiplier

        return {'word': word, 'word_score': word_score, 'start_row': start_row, 'start_col': start_col}


    def getHorizontalWordAtCoordinate(
        self,
        x,
        y,
        virtualBoard,
        tempBoardValues
    ):
        currY = y
        word = ""
        word_score = 0
        multiplier = 1
        start_row = x
        start_col = y
        while getTempLetterAtCoordinate(x, currY, tempBoardValues) or self.getLetterAtCoordinate(x, currY) or getTempLetterOnVirtualBoard(x, currY, virtualBoard):
            word += (getTempLetterAtCoordinate(x, currY, tempBoardValues) or
                    self.getLetterAtCoordinate(x, currY) or
                    getTempLetterOnVirtualBoard(x, currY, virtualBoard))
            letterScoreObj = self.calculateScoreFromLetter(
                x,
                currY,
                virtualBoard,
                None,
                tempBoardValues,
            )
            word_score += letterScoreObj['letterPoints']
            multiplier *= letterScoreObj['wordMultiplier']
            currY += 1

        currY = y - 1
        while (
            getTempLetterAtCoordinate(x, currY, tempBoardValues) or
            self.getLetterAtCoordinate(x, currY) or
            getTempLetterOnVirtualBoard(x, currY, virtualBoard)
        ):
            word = (getTempLetterAtCoordinate(x, currY, tempBoardValues) or
                    self.getLetterAtCoordinate(x, currY) or
                    getTempLetterOnVirtualBoard(x, currY, virtualBoard)) + word
            letterScoreObj = self.calculateScoreFromLetter(
                x,
                currY,
                virtualBoard,
                None,
                tempBoardValues,
            )
            word_score += letterScoreObj['letterPoints']
            multiplier *= letterScoreObj['wordMultiplier']
            start_col = currY
            currY -= 1

        word_score *= multiplier
        return {'word': word, 'word_score': word_score,'start_row': start_row, 'start_col': start_col}
    
    def getLetterAtCoordinate(self, x, y):
        return self.board[x][y].letter if is_on_board(x, y) else None

    def calculateScoreFromLetter(
        self,
        i,
        j,
        virtualBoard,
        letterArg,
        tempBoardValues,
    ):
        letter = letterArg or getTempLetterAtCoordinate(i, j, tempBoardValues) or self.getLetterAtCoordinate(
            i, j) or getTempLetterOnVirtualBoard(i, j, virtualBoard)
        letterPoints = LETTER_TO_SCORE[letter]
        wordMultiplier = 1

        if letterArg or getTempLetterAtCoordinate(i, j, tempBoardValues) or getTempLetterOnVirtualBoard(i, j, virtualBoard):
            specialScore = getSpecialTileScoreIdx(i, j)

            match specialScore:
                case "ct":
                    wordMultiplier = 2
                case "tw":
                    wordMultiplier = 3
                case "tl":
                    letterPoints *= 3
                case "dw":
                    wordMultiplier = 2
                case "dl":
                    letterPoints *= 2

        return {'letterPoints': letterPoints, 'wordMultiplier': wordMultiplier}
    
    def get_move(self):
        self.best_word = ''
        self.highest_score = 0

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if not (is_on_board(row - 1, col) and self.board[row - 1][col].letter):
                    self.get_move_helper( self.computer_word_rack.copy() , '', row, col, row, col, True, False, row == 7 and col == 7, False )
                if not (is_on_board(row, col - 1) and self.board[row][col - 1].letter):
                    self.get_move_helper( self.computer_word_rack.copy() , '', row, col, row, col, False, False, row == 7 and col == 7, False )
        return self.insert_best_word()
        

    def get_move_helper(self, letters, word_so_far, start_row, start_col, row, col, is_vertical, contains_prev_letter, contains_center, played_a_letter):

        curr_row = row
        curr_col = col
        new_contains_prev_letter = contains_prev_letter
        new_contains_center = contains_center
        new_word_so_far = word_so_far
        while is_on_board(curr_row, curr_col) and self.board[curr_row][curr_col].letter:
            new_word_so_far += self.board[curr_row][curr_col].letter
            if not find_prefix_in_dawg(new_word_so_far, self.dawg_root):
               return
            new_contains_prev_letter = True
            new_contains_center = new_contains_center or (curr_row == 7 and curr_col == 7)
            if is_vertical:
                curr_row += 1
            else:
                curr_col += 1
        
        if played_a_letter and find_in_dawg(new_word_so_far, self.dawg_root) and new_contains_prev_letter:
            virtual_board = [["" for x in range(BOARD_SIZE)] for y in range(BOARD_SIZE)]
            idx = 0
            v_row = start_row
            v_col = start_col
            while idx <  len(new_word_so_far):
                if not self.board[v_row][v_col].letter:
                    virtual_board[v_row][v_col] = new_word_so_far[idx]
                idx += 1
                if is_vertical:
                    v_row += 1
                else:
                    v_col += 1

            result = self.checkAllWordsOnBoard(virtual_board, None, new_word_so_far)
            if result:
                score = result['score']
                if score > self.highest_score:
                    self.highest_score = score
                    self.best_word = new_word_so_far
                    self.best_col = start_col
                    self.best_row = start_row
                    self.best_word_is_vertical = is_vertical

        if not is_on_board(curr_row, curr_col):
            return

        for letter in letters:
            if find_prefix_in_dawg(new_word_so_far + letter, self.dawg_root):
                new_letters = letters.copy()
                new_letters.remove(letter)
                next_row =  curr_row + 1 if is_vertical else curr_row
                next_col = curr_col if is_vertical else curr_col + 1
                self.get_move_helper( new_letters, new_word_so_far + letter, start_row, start_col, next_row, next_col, is_vertical, new_contains_prev_letter, new_contains_center, True)


# returns a list of all words played on the board
def all_board_words(board):
    board_words = []

    # check regular board
    for row in range(0, 15):
        temp_word = ""
        for col in range(0, 16):
            letter = board[row][col].letter
            if letter:
                temp_word += letter
            else:
                if len(temp_word) > 1:
                    board_words.append(temp_word)
                temp_word = ""

    # check transposed board
    for col in range(0, 16):
        temp_word = ""
        for row in range(0, 16):
            letter = board[row][col].letter
            if letter:
                temp_word += letter
            else:
                if len(temp_word) > 1:
                    board_words.append(temp_word)
                temp_word = ""

    return board_words


def refill_word_rack(rack, tile_bag):
    to_add = min([7 - len(rack), len(tile_bag)])
    new_letters = random.sample(tile_bag, to_add)
    rack = rack + new_letters
    return rack, new_letters


def renove_items_from_list(list_1, list_2):
    for item in list_2:
        if item in list_1:
            list_1.remove(item)



def getPlacedLettersRowsAndCols(virtualBoard, tempBoardValues):
    rows = []
    cols = []
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if (getTempLetterOnVirtualBoard(i, j, virtualBoard)):
                if i not in rows:
                    rows.append(i)
                if j not in cols:
                    cols.append(j)
            if (getTempLetterAtCoordinate(i, j, tempBoardValues)):
                if i not in rows:
                    rows.append(i)
                if j not in cols:
                    cols.append(j)

    return {'rows': rows, 'cols': cols}


def getTempLetterOnVirtualBoard(x, y, virtualBoard):
    if not is_on_board(x, y):
        return None
    if not virtualBoard:
        return
    if not virtualBoard[x]:
        return
    return virtualBoard[x][y] if is_on_board(x, y) else None


def getTempLetterAtCoordinate(x, y, tempBoardValues):
    if not tempBoardValues:
        return
    return tempBoardValues[x][y] if is_on_board(x, y) else None


def is_on_board(x, y):
    return x >= 0 and x < BOARD_SIZE and y >= 0 and y < BOARD_SIZE




def getSpecialTileScoreIdx(i, j):
    ti = toTileIndex(i, j)
    for t in tileScoreIdx:
        if ti in tileScoreIdx[t]:
            return t
    return ''


def toTileIndex(row, column):
    if row < BOARD_SIZE and row >= 0 and column < BOARD_SIZE and column >= 0:
        return row * BOARD_SIZE + column
    else:
        return -1

def getAllTempLetters (virtualBoard, tempBoardValues):
    letters = []
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            letter = getTempLetterOnVirtualBoard(i, j, virtualBoard) or getTempLetterAtCoordinate(i, j, tempBoardValues)
            if (letter):
                letters.append(letter)

    return letters
