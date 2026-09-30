from itertools import permutations

import pytest

from puzzle8.board import GOAL, apply_moves, is_solvable, neighbours, parse_state
from puzzle8.oracle import SOLVABLE_STATES, distances, optimal_distance

# Known property of the 8-puzzle, independent of this code.
MAX_OPTIMAL_DISTANCE = 31


# --- Coverage of the state space --------------------------------------------

def test_table_holds_every_solvable_state_and_nothing_else():
    table = distances()
    assert len(table) == SOLVABLE_STATES
    solvable = {p for p in permutations(range(9)) if is_solvable(p)}
    assert set(table) == solvable


def test_unsolvable_state_has_no_distance():
    with pytest.raises(KeyError):
        optimal_distance(parse_state("213456780"))


# --- The distances are genuinely shortest ------------------------------------

def test_maximum_distance_is_31():
    assert max(distances().values()) == MAX_OPTIMAL_DISTANCE


def test_every_state_steps_down_towards_the_goal():
    # These two checks pin down a shortest-path table.
    table = distances()
    for state, distance in table.items():
        neighbour_distances = [table[n] for _, n in neighbours(state)]
        assert all(abs(distance - d) <= 1 for d in neighbour_distances)
        if distance == 0:
            assert state == GOAL
        else:
            assert min(neighbour_distances) == distance - 1


# --- Hand-checkable cases ----------------------------------------------------

# (moves from the goal, resulting state, oracle distance)
TRACES = [
    ("", "123456780", 0),
    ("L", "123456708", 1),
    ("UL", "123405786", 2),
    ("ULD", "123485706", 3),
    ("ULDR", "123485760", 4),
]


@pytest.mark.parametrize("moves, expected_state, expected_distance", TRACES)
def test_traced_states_match_their_move_count(moves, expected_state, expected_distance):
    state = apply_moves(GOAL, moves)
    assert state == parse_state(expected_state)
    assert optimal_distance(state) == expected_distance


def test_goal_is_the_only_state_at_distance_zero():
    assert optimal_distance(GOAL) == 0
    assert [s for s, d in distances().items() if d == 0] == [GOAL]


def test_every_neighbour_of_the_goal_is_one_move_away():
    for _, neighbour in neighbours(GOAL):
        assert optimal_distance(neighbour) == 1
