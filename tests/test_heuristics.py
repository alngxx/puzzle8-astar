from itertools import combinations

import pytest

from puzzle8.board import GOAL, apply_moves, neighbours, parse_state
from puzzle8.heuristics import GOAL_COL, GOAL_ROW, linear_conflict, manhattan
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


# --- Linear conflict: exhaustive properties ----------------------------------

def test_linear_conflict_never_overestimates():
    for state, true_distance in distances().items():
        estimate = linear_conflict(state)
        assert estimate <= true_distance, (
            f"linear_conflict({state}) = {estimate} exceeds true distance {true_distance}"
        )


def test_linear_conflict_is_consistent():
    for state in distances():
        estimate = linear_conflict(state)
        for _, neighbour in neighbours(state):
            assert abs(estimate - linear_conflict(neighbour)) <= 1


def test_linear_conflict_never_below_manhattan():
    # It only ever adds to Manhattan, so it must be at least as informed.
    # Strictly above somewhere, or the extra term would be doing nothing.
    strictly_above = 0
    for state in distances():
        assert linear_conflict(state) >= manhattan(state)
        strictly_above += linear_conflict(state) > manhattan(state)
    assert strictly_above > 0


def _lc_directly(state):
    """Linear conflict worked out without the tables or the DP.

    The fewest tiles to lift out of a line is found by brute force: try the
    largest subsets first, and keep the first one already in goal order.
    """
    def lift(goal_positions):
        n = len(goal_positions)
        for keep in range(n, 0, -1):
            for subset in combinations(goal_positions, keep):
                if list(subset) == sorted(subset):
                    return n - keep
        return 0

    total = _manhattan_directly(state)
    for r in range(3):
        row = [GOAL_COL[t] for t in state[3 * r:3 * r + 3] if t and GOAL_ROW[t] == r]
        total += 2 * lift(row)
    for c in range(3):
        col = [GOAL_ROW[t] for t in state[c::3] if t and GOAL_COL[t] == c]
        total += 2 * lift(col)
    return total


def test_linear_conflict_tables_match_a_direct_calculation():
    for state in distances():
        assert linear_conflict(state) == _lc_directly(state)


# --- Linear conflict: hand-checkable cases -----------------------------------

# (state, manhattan, linear conflict, why)
LC_CASES = [
    ("123456780", 0, 0, "solved: no conflicts"),
    ("213456780", 2, 4, "2 1 in the top row: lift one tile, +2"),
    ("321456780", 4, 8, "3 2 1: lift 3 and 1, keep 2, +4 (pairwise would say +6)"),
    ("321456870", 6, 12, "3 2 1 on top (+4), 8 7 on the bottom (+2)"),
    ("724506831", 14, 14, "no two tiles out of order within a goal line"),
]


@pytest.mark.parametrize("text, expected_manhattan, expected_lc, _why", LC_CASES)
def test_linear_conflict_hand_cases(text, expected_manhattan, expected_lc, _why):
    state = parse_state(text)
    assert manhattan(state) == expected_manhattan
    assert linear_conflict(state) == expected_lc


def _pairwise_conflicts(state):
    """The naive variant: +2 for every out-of-order pair in a goal line."""
    extra = 0
    for r in range(3):
        row = [t for t in state[3 * r:3 * r + 3] if t and GOAL_ROW[t] == r]
        extra += 2 * sum(GOAL_COL[a] > GOAL_COL[b] for a, b in combinations(row, 2))
    for c in range(3):
        col = [t for t in state[c::3] if t and GOAL_COL[t] == c]
        extra += 2 * sum(GOAL_ROW[a] > GOAL_ROW[b] for a, b in combinations(col, 2))
    return manhattan(state) + extra


def test_counting_pairs_instead_would_be_inadmissible():
    # Why the longest-in-order rule matters: on this state the pairwise
    # version overestimates the true distance, so A* using it could return
    # a non-optimal path. The real heuristic is exactly right here.
    state = parse_state("870654321")
    assert optimal_distance(state) == 26
    assert _pairwise_conflicts(state) == 28
    assert linear_conflict(state) == 26
