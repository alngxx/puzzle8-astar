import pytest

from puzzle8.board import GOAL, apply_moves, neighbours, parse_state
from puzzle8.heuristics import manhattan
from puzzle8.oracle import distances, optimal_distance


# --- Exhaustive properties, checked against the oracle -----------------------

def test_manhattan_never_overestimates():
    # Admissibility over every solvable state, not a sample: this is what
    # guarantees A* returns optimal solutions.
    worst = None
    for state, true_distance in distances().items():
        estimate = manhattan(state)
        assert estimate <= true_distance, (
            f"manhattan({state}) = {estimate} exceeds true distance {true_distance}"
        )
        gap = true_distance - estimate
        if worst is None or gap > worst[0]:
            worst = (gap, state)
    # Sanity on the check itself: the bound is tight somewhere (the goal) and
    # loose elsewhere, so the loop really is comparing varying values.
    assert worst[0] > 0


def test_manhattan_is_consistent():
    # |h(s) - h(s')| <= 1 for every edge: one move slides one tile one cell,
    # so the estimate cannot jump. Consistency means A* never needs to revisit
    # a state it has already expanded.
    for state in distances():
        estimate = manhattan(state)
        for _, neighbour in neighbours(state):
            assert abs(estimate - manhattan(neighbour)) <= 1


def test_only_the_goal_has_a_zero_estimate():
    zeros = [s for s in distances() if manhattan(s) == 0]
    assert zeros == [GOAL]


# --- Hand-checkable cases ----------------------------------------------------

# (state, expected manhattan, why)
CASES = [
    ("123456780", 0, "solved"),
    ("123456708", 1, "tile 8 is one cell right of home"),
    ("123405786", 2, "6 is two cells from home (down one, right one); 5,7,8 home"),
    ("123485706", 3, "8 up one, 5 left one, 6 up one"),
]


@pytest.mark.parametrize("text, expected, _why", CASES)
def test_manhattan_hand_cases(text, expected, _why):
    assert manhattan(parse_state(text)) == expected


def _manhattan_directly(state):
    """The same sum, worked out from scratch without the lookup table."""
    total = 0
    for index, tile in enumerate(state):
        if tile == 0:
            continue  # the blank is not a tile
        goal_index = GOAL.index(tile)
        total += abs(index // 3 - goal_index // 3) + abs(index % 3 - goal_index % 3)
    return total


def test_lookup_table_matches_a_direct_calculation():
    # The table is precomputed at import; recompute the long way over the
    # whole state space to confirm it was built correctly, and that skipping
    # the blank is what the table does too.
    for state in distances():
        assert manhattan(state) == _manhattan_directly(state)


def test_estimate_changes_by_at_most_one_along_a_real_solution():
    # Walk a concrete path and watch the estimate track the true distance.
    state = GOAL
    for move in "ULDRUL":
        previous = manhattan(state)
        state = apply_moves(state, move)
        assert abs(manhattan(state) - previous) == 1
        assert manhattan(state) <= optimal_distance(state)
