"""Heuristics estimating the moves still needed to reach the goal.

A heuristic is *admissible* if it never overestimates the true remaining
distance, which is what makes A* return optimal solutions, and *consistent*
if h(s) <= 1 + h(s') for every neighbour s', which additionally means no
state is ever reached again by a cheaper path. Both properties are checked
exhaustively against the BFS oracle in the tests, over the whole state space.
"""

from itertools import product

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


# --- Linear conflict ---------------------------------------------------------

GOAL_ROW = tuple(GOAL.index(tile) // SIZE for tile in range(N_CELLS))
GOAL_COL = tuple(GOAL.index(tile) % SIZE for tile in range(N_CELLS))


def _tiles_to_lift(goal_positions):
    """Fewest tiles that must leave a line so the rest are in goal order.

    `goal_positions` lists, in their current order along the line, where
    each tile belongs within it. Tiles in a line cannot pass one another, so
    the ones allowed to stay must already be in increasing goal order: the
    most that can stay is the longest increasing subsequence, and every
    other tile has to step out of the line and back.

    Counting conflicting *pairs* instead overcounts: for 3 2 1 all three
    pairs conflict, but lifting 3 and 1 -- two tiles, not three -- lets 2
    stay, and moving those two out of the way is enough.
    """
    longest = [1] * len(goal_positions)  # longest run ending at each tile
    for i in range(len(goal_positions)):
        for j in range(i):
            if goal_positions[j] < goal_positions[i]:
                longest[i] = max(longest[i], longest[j] + 1)
    return len(goal_positions) - max(longest, default=0)


def _line_penalties(line, line_of, position_in_line):
    """{line contents: extra moves} for every possible 3-cell content."""
    table = {}
    for cells in product(range(N_CELLS), repeat=SIZE):
        home = [position_in_line[t] for t in cells if t and line_of[t] == line]
        table[cells] = 2 * _tiles_to_lift(home)
    return table


# Precomputed for every possible line content (9^3 per line), so a call is six
# lookups on top of Manhattan. ROW_PENALTY[r] looks at tiles whose goal row
# is r and compares their goal columns; COL_PENALTY the other way round.
ROW_PENALTY = tuple(_line_penalties(r, GOAL_ROW, GOAL_COL) for r in range(SIZE))
COL_PENALTY = tuple(_line_penalties(c, GOAL_COL, GOAL_ROW) for c in range(SIZE))


def linear_conflict(state):
    """Manhattan plus 2 moves per tile that must leave its goal line.

    Admissible: a tile already in its goal row has no vertical Manhattan
    distance, so if it has to step out of the row to let others pass, those
    2 vertical moves are uncounted by Manhattan. Row penalties only ever add
    vertical detours and column penalties horizontal ones, so the two never
    count the same move twice.

    Consistent: a move shifts one tile t by one cell. Say it is horizontal.
    The order of t's row is unchanged, so no row penalty changes, and t
    only counts toward a column penalty in its goal column. If it enters
    that column, Manhattan drops by 1 and the penalty rises by 0 or 2; if it
    leaves, Manhattan rises by 1 and the penalty drops by 0 or 2; otherwise
    only Manhattan changes. Either way h changes by exactly 1. (Vertical
    moves are the same with rows and columns swapped.)
    """
    total = manhattan(state)
    for r in range(SIZE):
        total += ROW_PENALTY[r][state[r * SIZE:(r + 1) * SIZE]]
    for c in range(SIZE):
        total += COL_PENALTY[c][state[c::SIZE]]
    return total
