"""8-puzzle board: representation, parsing, moves and solvability.

A state is a tuple of 9 ints in row-major order, with 0 as the blank:

    (1, 2, 3,
     4, 5, 6,      is the goal, printed as    1 2 3
     7, 8, 0)                                 4 5 6
                                              7 8 .

Moves are named by the direction the BLANK moves (not the tile):
U = blank moves up, D = down, L = left, R = right.
"""

import re

SIZE = 3
N_CELLS = SIZE * SIZE
GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)

# Index offset of each blank move in the flat tuple.
MOVE_DELTAS = {"U": -SIZE, "D": SIZE, "L": -1, "R": 1}
INVERSE_MOVE = {"U": "D", "D": "U", "L": "R", "R": "L"}


# A tile token: ASCII digits only, so int() below can never see anything else.
ASCII_DIGITS = re.compile(r"[0-9]+")


class ParseError(ValueError):
    """Raised when a puzzle string is not a valid 8-puzzle state."""


class IllegalMoveError(ValueError):
    """Raised when a move would push the blank off the board."""


def _legal_moves(index):
    """Moves the blank can make from `index`, as (move, target_index) pairs."""
    row, col = divmod(index, SIZE)
    moves = []
    if row > 0:
        moves.append(("U", index - SIZE))
    if row < SIZE - 1:
        moves.append(("D", index + SIZE))
    if col > 0:
        moves.append(("L", index - 1))
    if col < SIZE - 1:
        moves.append(("R", index + 1))
    return tuple(moves)


# NEIGHBOURS[i] = legal (move, target) pairs when the blank is at index i.
# Precomputed once so the search never redoes the row/column arithmetic.
NEIGHBOURS = tuple(_legal_moves(i) for i in range(N_CELLS))


def parse_state(text):
    """Parse '123456780', '1 2 3 4 5 6 7 8 0' or '1,2,3,4,5,6,7,8,0'.

    Raises ParseError with a message specific to the first problem found.
    """
    text = text.strip()
    if re.search(r"[,\s]", text):
        tokens = [t for t in re.split(r"[,\s]+", text) if t]
    else:
        tokens = list(text)  # compact form: one character per tile

    for tok in tokens:
        # Deliberately not str.isdigit(): that accepts non-ASCII digit-like
        # characters, which either crash int() with a bare ValueError (e.g.
        # the superscript '2') or parse silently into a tile the user never
        # typed (e.g. the Arabic-Indic '1'). Only ASCII 0-9 is a tile.
        if not ASCII_DIGITS.fullmatch(tok):
            raise ParseError(f"invalid tile {tok!r}: tiles must be digits 0-8")
    if len(tokens) != N_CELLS:
        raise ParseError(f"expected {N_CELLS} tiles, got {len(tokens)}")

    tiles = [int(t) for t in tokens]
    # Checked before duplicates: with exactly 9 in-range values, a missing 0
    # always forces a duplicate, and "missing blank" is the more useful message.
    if 0 not in tiles:
        raise ParseError("missing blank: the state must contain a 0")
    for t in tiles:
        if t >= N_CELLS:
            raise ParseError(f"tile {t} out of range: tiles must be 0-8")
    seen = set()
    for t in tiles:
        if t in seen:
            raise ParseError(f"duplicate tile {t}")
        seen.add(t)
    return tuple(tiles)


def neighbours(state):
    """Yield (move, next_state) for every legal blank move from `state`."""
    blank = state.index(0)
    for move, target in NEIGHBOURS[blank]:
        cells = list(state)
        cells[blank], cells[target] = cells[target], cells[blank]
        yield move, tuple(cells)


def apply_move(state, move):
    """Return the state after the blank makes `move`; raise if it's illegal."""
    blank = state.index(0)
    for legal_move, target in NEIGHBOURS[blank]:
        if legal_move == move:
            cells = list(state)
            cells[blank], cells[target] = cells[target], cells[blank]
            return tuple(cells)
    if move not in MOVE_DELTAS:
        raise IllegalMoveError(f"unknown move {move!r}: expected one of U, D, L, R")
    raise IllegalMoveError(f"move {move} is illegal with the blank at index {blank}")


def apply_moves(state, moves):
    """Replay a move sequence (e.g. 'ULDR' or ['U', 'L']) from `state`.

    This is deliberately independent of the search code: solutions are
    validated by replaying them here, not by trusting the search.
    """
    for i, move in enumerate(moves, start=1):
        try:
            state = apply_move(state, move)
        except IllegalMoveError as e:
            raise IllegalMoveError(f"move {i}: {e}") from None
    return state


def inversions(state):
    """Count pairs of tiles (a, b) with a before b but a > b, ignoring the blank."""
    tiles = [t for t in state if t != 0]
    count = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                count += 1
    return count


def is_solvable(state):
    """True iff `state` can reach GOAL.

    On a 3-wide board, a left/right blank move leaves the tile order unchanged,
    and an up/down move jumps one tile past exactly 2 others, changing the
    inversion count by -2, 0 or +2. So inversion parity never changes, and
    since GOAL has 0 inversions, only states with an even count are solvable.
    (This rule is specific to odd board widths.)
    """
    return inversions(state) % 2 == 0


def format_board(state):
    """Render a state as a 3x3 grid, with '.' for the blank."""
    rows = []
    for r in range(SIZE):
        row = state[r * SIZE:(r + 1) * SIZE]
        rows.append(" ".join("." if t == 0 else str(t) for t in row))
    return "\n".join(rows)
