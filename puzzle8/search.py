"""A* search for the 8-puzzle, with unit move costs and f = g + h."""

import heapq
import time
from dataclasses import dataclass

from puzzle8.board import GOAL, is_solvable, neighbours
from puzzle8.heuristics import manhattan


class UnsolvableError(ValueError):
    """Raised when the start state has odd inversion parity."""


@dataclass(frozen=True)
class SearchResult:
    path: str             # blank moves from start to goal, e.g. "ULDR"
    nodes_expanded: int   # states whose neighbours were generated
    nodes_generated: int  # heap pushes, including the start
    max_frontier: int     # largest heap size, stale entries included
    seconds: float

    @property
    def length(self):
        return len(self.path)


def astar(start, heuristic=manhattan):
    """Find an optimal move sequence from `start` to GOAL."""
    # Fail fast: otherwise A* exhausts all 181440 reachable states first.
    if not is_solvable(start):
        raise UnsolvableError("state is unsolvable (odd inversion parity)")

    t0 = time.perf_counter()
    h0 = heuristic(start)
    # (f, h, counter, state): ties go to lower h, then push order. The
    # counter also keeps states from ever being compared.
    frontier = [(h0, h0, 0, start)]
    counter = 1
    best_g = {start: 0}
    parent = {start: None}  # state -> (previous state, move), for the path
    closed = set()
    expanded = 0
    max_frontier = 1

    while frontier:
        f, h, _, state = heapq.heappop(frontier)
        g = f - h

        # Lazy deletion: skip entries superseded by a cheaper path.
        if g != best_g[state]:
            continue

        # Expand each state once. Safe only for a consistent heuristic: with
        # an inconsistent one, a cheaper path to a closed state is discarded.
        # With no duplicate detection at all, A* degrades to tree search.
        # See scripts/demonstrate_invariants.py for both.
        if state in closed:
            continue

        # Goal test on pop, not on generation: g is only guaranteed optimal
        # once the goal has the smallest f in the heap.
        if state == GOAL:
            return SearchResult(
                path=_reconstruct(parent, state),
                nodes_expanded=expanded,
                nodes_generated=counter,
                max_frontier=max_frontier,
                seconds=time.perf_counter() - t0,
            )

        closed.add(state)
        expanded += 1
        for move, nxt in neighbours(state):
            if nxt in closed:
                continue
            new_g = g + 1
            # Also keeps parent[nxt] on the cheapest known path.
            if new_g < best_g.get(nxt, new_g + 1):
                best_g[nxt] = new_g
                parent[nxt] = (state, move)
                h_nxt = heuristic(nxt)
                heapq.heappush(frontier, (new_g + h_nxt, h_nxt, counter, nxt))
                counter += 1
        max_frontier = max(max_frontier, len(frontier))

    # Unreachable: a solvable start always reaches GOAL.
    raise AssertionError("frontier exhausted without reaching the goal")


def _reconstruct(parent, state):
    moves = []
    while parent[state] is not None:
        state, move = parent[state]
        moves.append(move)
    return "".join(reversed(moves))
