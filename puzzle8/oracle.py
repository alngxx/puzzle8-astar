"""Ground truth: the exact optimal distance of every solvable state.

Everything else is checked against this table, so it shares no code with
search.py: plain breadth-first search, with no heuristic and no priority
queue. BFS reaches each state first by a shortest path, whatever any
heuristic says.

The search runs outward from GOAL. Every move is reversible, so the distance
from GOAL to a state equals the distance back, and one sweep covers every
state.

Only solvable states are reachable, so the table holds 9!/2 = 181440 of the
9! = 362880 arrangements. The odd-parity half is never reached, rather than
filtered out.
"""

from collections import deque

from puzzle8.board import GOAL, neighbours

# 9! / 2: half the arrangements are unreachable (see board.is_solvable).
SOLVABLE_STATES = 181440


def build_distance_table():
    """Return {state: optimal moves to GOAL} for every solvable state."""
    distances = {GOAL: 0}
    queue = deque([GOAL])
    while queue:
        state = queue.popleft()
        next_distance = distances[state] + 1
        for _, neighbour in neighbours(state):
            if neighbour not in distances:
                distances[neighbour] = next_distance
                queue.append(neighbour)
    return distances


_DISTANCES = None


def distances():
    """The full table, built on first use."""
    global _DISTANCES
    if _DISTANCES is None:
        _DISTANCES = build_distance_table()
    return _DISTANCES


_BY_DEPTH = None


def states_at_depth(depth):
    """Every state exactly `depth` moves from GOAL, sorted so a seeded sample
    is reproducible. Empty outside 0..31."""
    global _BY_DEPTH
    if _BY_DEPTH is None:
        _BY_DEPTH = {}
        for state, d in distances().items():
            _BY_DEPTH.setdefault(d, []).append(state)
        for pool in _BY_DEPTH.values():
            pool.sort()
    return _BY_DEPTH.get(depth, [])


def optimal_distance(state):
    """Exact number of moves from `state` to GOAL.

    Raises KeyError for an unsolvable state: it has no entry, not an
    infinite one.
    """
    return distances()[state]
