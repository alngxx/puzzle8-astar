"""Heuristics for A*. Both are admissible and consistent; the tests check
this against the oracle on every state."""

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


DISTANCE = _distance_table()


def manhattan(state):
    """Sum of each tile's grid distance to its goal cell, blank excluded."""
    return sum(DISTANCE[tile][index] for index, tile in enumerate(state) if tile)


# --- Linear conflict ---------------------------------------------------------

GOAL_ROW = tuple(GOAL.index(tile) // SIZE for tile in range(N_CELLS))
GOAL_COL = tuple(GOAL.index(tile) % SIZE for tile in range(N_CELLS))


def _tiles_to_lift(goal_positions):
    """Fewest tiles to remove from a line so the rest are in goal order.

    Tiles can't pass each other within a line, so only a longest increasing
    subsequence of goal positions can stay. Counting conflicting pairs
    overcounts: 3 2 1 has three pairs but needs only two tiles moved.
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


# Penalties for every possible line content (9^3 per line), so
# linear_conflict is Manhattan plus six lookups.
ROW_PENALTY = tuple(_line_penalties(r, GOAL_ROW, GOAL_COL) for r in range(SIZE))
COL_PENALTY = tuple(_line_penalties(c, GOAL_COL, GOAL_ROW) for c in range(SIZE))


def linear_conflict(state):
    """Manhattan + 2 per tile that must leave its goal row or column.

    A tile in its goal row has no vertical distance, so stepping out and back
    costs 2 moves Manhattan doesn't count. Row penalties are vertical moves
    and column penalties horizontal, so no move is counted twice.
    """
    total = manhattan(state)
    for r in range(SIZE):
        total += ROW_PENALTY[r][state[r * SIZE:(r + 1) * SIZE]]
    for c in range(SIZE):
        total += COL_PENALTY[c][state[c::SIZE]]
    return total
