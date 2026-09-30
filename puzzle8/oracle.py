"""Ground truth: the optimal distance of every solvable state, by BFS.

Shares no code with search.py, so A* can be checked against it. Moves are
reversible, so one sweep outward from GOAL covers every state.
"""

from collections import deque

from puzzle8.board import GOAL, neighbours

# 9!/2: the odd-parity half is unreachable.
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
    """States exactly `depth` moves from GOAL, sorted for reproducible sampling."""
    global _BY_DEPTH
    if _BY_DEPTH is None:
        _BY_DEPTH = {}
        for state, d in distances().items():
            _BY_DEPTH.setdefault(d, []).append(state)
        for pool in _BY_DEPTH.values():
            pool.sort()
    return _BY_DEPTH.get(depth, [])


def optimal_distance(state):
    """Moves from `state` to GOAL; KeyError if unsolvable."""
    return distances()[state]
