"""Ground truth: the exact optimal distance for every solvable state.

This is the reference everything else is checked against, so it is kept
deliberately independent of the solver. It uses breadth-first search and
nothing else -- no heuristic, no priority queue, no A*. BFS explores states
in order of distance, so the first time it reaches a state it has reached it
by a shortest path; that is true by construction and needs no assumption
about any heuristic being admissible.

The search runs outward from GOAL rather than inward from some start. Every
move is reversible (the blank steps back the way it came), so the distance
from GOAL to a state equals the distance from that state to GOAL, and one
sweep yields the answer for every state at once.

Only solvable states are reachable, so the table holds 9!/2 = 181440 of the
9! = 362880 arrangements -- the rest have odd inversion parity and are
absent by construction, not by being filtered out.
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
    """The full table, built on first use and reused afterwards."""
    global _DISTANCES
    if _DISTANCES is None:
        _DISTANCES = build_distance_table()
    return _DISTANCES


def optimal_distance(state):
    """Exact number of moves from `state` to GOAL.

    Raises KeyError for an unsolvable state, which has no distance at all --
    it is absent from the table rather than stored as infinity.
    """
    return distances()[state]
