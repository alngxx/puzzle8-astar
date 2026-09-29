"""Estimates of the moves left to reach the goal.

A heuristic is admissible if it never overestimates the true distance, which
makes A* optimal. It is consistent if h(s) <= 1 + h(s') for every neighbour
s', which means A* never reaches an expanded state again by a cheaper path.
The tests check both properties against the BFS oracle on every state.
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


# Precomputed at import, so each call is table lookups, not row/column
# arithmetic.
DISTANCE = _distance_table()


def manhattan(state):
    """Sum of each tile's distance from its goal cell.

    The blank is not a tile. Counting it would break admissibility, since one
    move shifts both the blank and a tile. Each move shifts one tile one cell
    and changes the sum by 1, so reaching the goal's 0 takes at least h
    moves, and neighbours never differ by more than 1.
    """
    return sum(DISTANCE[tile][index] for index, tile in enumerate(state) if tile)


# --- Linear conflict ---------------------------------------------------------

GOAL_ROW = tuple(GOAL.index(tile) // SIZE for tile in range(N_CELLS))
GOAL_COL = tuple(GOAL.index(tile) % SIZE for tile in range(N_CELLS))


def _tiles_to_lift(goal_positions):
    """Fewest tiles that must leave a line so the rest are in goal order.

    `goal_positions` lists where each tile belongs within the line, in current
    order. Tiles in a line cannot pass each other, so the ones that stay must
    already be in increasing goal order. At most the longest increasing
    subsequence can stay; every other tile must step out and back.

    Counting conflicting pairs instead overcounts: in 3 2 1 all three pairs
    conflict, but lifting only 3 and 1 lets 2 stay (+4, not +6).
    """
    longest = [1] * len(goal_positions)  # LIS length ending at each tile
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


# One table per line covering all 9^3 contents, so a call adds six lookups to
# Manhattan. ROW_PENALTY[r] compares the goal columns of tiles whose goal row
# is r; COL_PENALTY swaps rows and columns.
ROW_PENALTY = tuple(_line_penalties(r, GOAL_ROW, GOAL_COL) for r in range(SIZE))
COL_PENALTY = tuple(_line_penalties(c, GOAL_COL, GOAL_ROW) for c in range(SIZE))


def linear_conflict(state):
    """Manhattan plus 2 moves per tile that must leave its goal line.

    Admissible: count each tile's vertical and horizontal moves separately. A
    tile in its goal row has vertical distance 0, so leaving the row and
    coming back costs at least 2 vertical moves that Manhattan ignores.
    Columns work the same way with horizontal moves. Each move shifts one
    tile in one direction, so adding these per-tile bounds counts no move
    twice.

    Consistent: a move shifts one tile t by one cell. Say it is horizontal.
    Row order is unchanged, so no row penalty changes, and t counts only
    toward its goal column's penalty. Entering that column lowers Manhattan
    by 1 and raises the penalty by 0 or 2; leaving does the reverse; any
    other move changes only Manhattan. Either way h changes by exactly 1.
    Vertical moves work the same with rows and columns swapped.
    """
    total = manhattan(state)
    for r in range(SIZE):
        total += ROW_PENALTY[r][state[r * SIZE:(r + 1) * SIZE]]
    for c in range(SIZE):
        total += COL_PENALTY[c][state[c::SIZE]]
    return total
