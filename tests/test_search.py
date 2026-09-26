import random

import pytest

from puzzle8.board import GOAL, apply_moves, parse_state
from puzzle8.oracle import distances, optimal_distance
from puzzle8.search import UnsolvableError, astar


def assert_solves(state, result):
    """Replay the path independently; never trust the search's bookkeeping."""
    assert apply_moves(state, result.path) == GOAL


# --- Trivial and near-trivial -----------------------------------------------

def test_solved_state_needs_no_moves():
    result = astar(GOAL)
    assert result.path == ""
    # The start is popped and passes the goal test before it is expanded.
    assert result.nodes_expanded == 0


@pytest.mark.parametrize("moves", ["L", "U", "UL", "LU"])
def test_one_and_two_move_states(moves):
    state = apply_moves(GOAL, moves)
    result = astar(state)
    assert result.length == len(moves)
    assert_solves(state, result)


# --- Correctness against ground truth ----------------------------------------

def test_moderately_scrambled_state_replays_to_goal():
    state = parse_state("724506831")
    result = astar(state)
    assert_solves(state, result)
    assert result.length == optimal_distance(state) == 20


def test_random_states_match_oracle():
    # 200 states drawn uniformly from the whole solvable space, seeded so any
    # failure is reproducible. Sorted first so the sample doesn't depend on
    # dict ordering.
    rng = random.Random(41052)
    for state in rng.sample(sorted(distances()), 200):
        result = astar(state)
        assert result.length == optimal_distance(state), state
        assert_solves(state, result)


@pytest.mark.parametrize("text", ["867254301", "647850321"])
def test_hardest_instances(text):
    state = parse_state(text)
    # Confirm the claim before relying on it: these should be the two states
    # the oracle places at the maximum depth.
    assert optimal_distance(state) == 31
    result = astar(state)
    assert result.length == 31
    assert_solves(state, result)


def test_the_two_hardest_instances_are_the_only_ones():
    deepest = {s for s, d in distances().items() if d == 31}
    assert deepest == {parse_state("867254301"), parse_state("647850321")}


# --- Behaviour ---------------------------------------------------------------

def test_unsolvable_state_rejected():
    with pytest.raises(UnsolvableError):
        astar(parse_state("213456780"))


def test_search_is_deterministic():
    state = parse_state("724506831")
    first, second = astar(state), astar(state)
    assert first.path == second.path
    assert first.nodes_expanded == second.nodes_expanded
    assert first.nodes_generated == second.nodes_generated
    assert first.max_frontier == second.max_frontier


def test_counters_are_coherent():
    result = astar(parse_state("724506831"))
    # Every expansion was preceded by a push, and the goal is pushed too.
    assert result.nodes_generated > result.nodes_expanded > 0
    assert 1 <= result.max_frontier <= result.nodes_generated
    assert result.seconds >= 0
