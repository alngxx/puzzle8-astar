import pytest

from puzzle8.board import (
    GOAL,
    INVERSE_MOVE,
    IllegalMoveError,
    ParseError,
    apply_moves,
    format_board,
    inversions,
    is_solvable,
    neighbours,
    parse_state,
)


# --- Parser -----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "123456780",
    "1 2 3 4 5 6 7 8 0",
    "1,2,3,4,5,6,7,8,0",
    "  1, 2, 3, 4, 5, 6, 7, 8, 0  ",
    "1 2 3\n4 5 6\n7 8 0",
])
def test_parse_accepts_all_formats(text):
    assert parse_state(text) == GOAL


@pytest.mark.parametrize("text, message", [
    ("12345678", "expected 9 tiles, got 8"),
    ("1234567800", "expected 9 tiles, got 10"),
    ("", "expected 9 tiles, got 0"),
    ("123456708 1", "expected 9 tiles, got 2"),  # mixed forms: two tokens
    ("12345678x", "invalid tile 'x'"),
    ("1 2 3 4 5 6 7 8 -1", "invalid tile '-1'"),
    ("123456788", "missing blank"),
    ("123456789", "missing blank"),
    ("1 2 3 4 5 6 7 10 0", "tile 10 out of range"),
    ("123456700", "duplicate tile 0"),
    ("1 1 3 4 5 6 7 8 0", "duplicate tile 1"),
])
def test_parse_rejects_bad_input_with_specific_message(text, message):
    with pytest.raises(ParseError, match=message):
        parse_state(text)


# --- Moves ------------------------------------------------------------------

def test_neighbour_counts_by_blank_position():
    # Corner blank has 2 moves, edge 3, centre 4.
    expected = [2, 3, 2, 3, 4, 3, 2, 3, 2]
    for blank, count in enumerate(expected):
        state = tuple(0 if i == blank else 1 for i in range(9))  # tiles irrelevant
        assert len(list(neighbours(state))) == count


def test_move_then_inverse_returns_original():
    # Blank at every one of the 9 positions, every legal move.
    for blank in range(9):
        tiles = iter([1, 2, 3, 4, 5, 6, 7, 8])
        state = tuple(0 if i == blank else next(tiles) for i in range(9))
        for move, nxt in neighbours(state):
            assert nxt != state
            assert apply_moves(nxt, INVERSE_MOVE[move]) == state


def test_apply_moves_matches_neighbours():
    state = parse_state("123405786")
    for move, nxt in neighbours(state):
        assert apply_moves(state, move) == nxt


def test_blank_direction_convention():
    # 'L' moves the blank left: tile 8 slides right into the old blank cell.
    assert apply_moves(GOAL, "L") == parse_state("123456708")


def test_illegal_move_reports_step():
    # From GOAL: U (blank up), D (back to bottom-right), then D again is off
    # the board -- the 3rd move, counted from 1.
    with pytest.raises(IllegalMoveError, match="move 3: move D is illegal"):
        apply_moves(GOAL, "UDD")


def test_unknown_move_rejected():
    with pytest.raises(IllegalMoveError, match="unknown move"):
        apply_moves(GOAL, "X")


# --- Solvability ------------------------------------------------------------

def test_already_solved_state():
    assert inversions(GOAL) == 0
    assert is_solvable(GOAL)
    assert apply_moves(GOAL, "") == GOAL


def test_known_unsolvable_state_rejected():
    # Goal with tiles 1 and 2 swapped: exactly one inversion.
    state = parse_state("213456780")
    assert inversions(state) == 1
    assert not is_solvable(state)


def test_states_reached_by_legal_moves_stay_solvable():
    # Parity is invariant under moves: walk around and check every step.
    state = GOAL
    for move in "ULURDDLURDLLUURDRULDDR":
        state = apply_moves(state, move)
        assert is_solvable(state)


def test_blank_position_does_not_affect_inversions():
    # The blank is excluded, so these differ only in where 0 sits.
    assert inversions(parse_state("123456780")) == inversions(parse_state("012345678"))


# --- Pretty-print -----------------------------------------------------------

def test_format_board():
    assert format_board(parse_state("123405786")) == "1 2 3\n4 . 5\n7 8 6"
