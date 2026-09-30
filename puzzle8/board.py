"""8-puzzle board: state representation, parsing, moves and solvability.

A state is a 9-tuple in row-major order with 0 as the blank. Moves (U, D,
L, R) name the direction the blank moves, not the tile.
"""

import re

SIZE = 3
N_CELLS = SIZE * SIZE
GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)

# Blank move -> index offset.
MOVE_DELTAS = {"U": -SIZE, "D": SIZE, "L": -1, "R": 1}
INVERSE_MOVE = {"U": "D", "D": "U", "L": "R", "R": "L"}


# Not str.isdigit(): it accepts '²' (int() then raises ValueError) and '١'
# (silently parsed as 1).
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


# NEIGHBOURS[i]: legal (move, target) pairs with the blank at index i.
NEIGHBOURS = tuple(_legal_moves(i) for i in range(N_CELLS))


def parse_state(text):
    """Parse '123456780', '1 2 3 4 5 6 7 8 0' or '1,2,3,4,5,6,7,8,0'."""
    text = text.strip()
    if re.search(r"[,\s]", text):
        tokens = [t for t in re.split(r"[,\s]+", text) if t]
    else:
        tokens = list(text)  # compact form: one character per tile

    for tok in tokens:
        if not ASCII_DIGITS.fullmatch(tok):
            raise ParseError(f"invalid tile {tok!r}: tiles must be digits 0-8")
    if len(tokens) != N_CELLS:
        raise ParseError(f"expected {N_CELLS} tiles, got {len(tokens)}")

    tiles = [int(t) for t in tokens]
    # Before the duplicate check: without a 0, some tile must repeat.
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
    """Replay `moves` (e.g. 'ULDR') from `state`; used to verify search output."""
    for i, move in enumerate(moves, start=1):
        try:
            state = apply_move(state, move)
        except IllegalMoveError as e:
            raise IllegalMoveError(f"move {i}: {e}") from None
    return state


def inversions(state):
    """Count tile pairs (a, b) with a before b and a > b, ignoring the blank."""
    tiles = [t for t in state if t != 0]
    count = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                count += 1
    return count


def is_solvable(state):
    """True iff `state` can reach GOAL.

    Horizontal moves keep the tile order; vertical moves change the inversion
    count by 0 or ±2. Parity is invariant and GOAL has 0 inversions.
    """
    return inversions(state) % 2 == 0


def format_board(state):
    """Render a state as a 3x3 grid, with '.' for the blank."""
    rows = []
    for r in range(SIZE):
        row = state[r * SIZE:(r + 1) * SIZE]
        rows.append(" ".join("." if t == 0 else str(t) for t in row))
    return "\n".join(rows)
