"""Heuristics estimating the moves still needed to reach the goal.

A heuristic is *admissible* if it never overestimates the true remaining
distance, which is what makes A* return optimal solutions, and *consistent*
if h(s) <= 1 + h(s') for every neighbour s', which additionally means no
state is ever reached again by a cheaper path. Both properties are checked
exhaustively against the BFS oracle in the tests, over the whole state space.
"""

from puzzle8.board import GOAL, N_CELLS, SIZE


def _distance_table():
    """DISTANCE[tile][index] = moves from `index` to `tile`'s goal cell."""
    table = []
    for tile in range(N_CELLS):
        goal_row, goal_col = divmod(GOAL.index(tile), SIZE)
        row_distances = []
        for index in range(N_CELLS):
            row, col = divmod(index, SIZE)
            row_distances.append(abs(row - goal_row) + abs(col - goal_col))
        table.append(tuple(row_distances))
    return tuple(table)


# Precomputed once at import: the search calls manhattan() millions of times,
# so the per-call work is a table lookup, never row/column arithmetic.
DISTANCE = _distance_table()


def manhattan(state):
    """Sum over tiles of the moves needed to slide each one home alone.

    The blank is excluded: it is not a tile, and counting it would break
    admissibility, since a single move relocates both a tile and the blank.
    Every move shifts exactly one tile by one cell, so it changes this sum
    by at most 1 -- hence no overestimate, and never a jump of more than 1
    between neighbouring states.
    """
    return sum(DISTANCE[tile][index] for index, tile in enumerate(state) if tile)
