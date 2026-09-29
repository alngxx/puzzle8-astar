"""A* search for the 8-puzzle.

Every move costs 1, so g(s) counts the moves from the start to s. A*
expands states in order of f = g + h. With an admissible h, the goal's g
when first popped is the optimal length.
"""

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
    # Otherwise an unsolvable start makes the search exhaust all 181440
    # states of its parity class before giving up.
    if not is_solvable(start):
        raise UnsolvableError("state is unsolvable (odd inversion parity)")

    t0 = time.perf_counter()
    h0 = heuristic(start)
    # Entries are (f, h, counter, state). Equal f breaks toward lower h (the
    # state believed nearer the goal), then push order. The unique counter
    # also means two states are never compared directly.
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

        # Lazy deletion: heapq can't lower a key, so a cheaper path pushes a
        # second entry. Skip the older one, whose g no longer matches best_g.
        if g != best_g[state]:
            continue

        # Closed set: expand each state at most once.
        #
        # Moves are reversible, so the graph is full of cycles. With no
        # duplicate detection at all (neither this nor best_g), A* becomes
        # tree search and re-expands a state once per path to it: 290108
        # expansions instead of 1436 on one depth-24 state. Without the
        # parity check above, it would never finish on an unsolvable start.
        #
        # With a consistent heuristic (both of ours), best_g already makes
        # this check redundant: a state's g is optimal when first popped. The
        # check keeps "at most once" true for any heuristic, at a price: with
        # an admissible but inconsistent heuristic, a cheaper path to a closed
        # state can turn up later, and refusing to reopen it returns a
        # suboptimal path (scripts/demonstrate_invariants.py shows one).
        if state in closed:
            continue

        # Goal test on pop, not on generation. Generating the goal shows only
        # that some path reaches it; a frontier entry with smaller f may lead
        # there more cheaply. When the goal pops, its f = g is the smallest in
        # the heap, and admissibility makes every other f a lower bound on
        # solutions through that entry, so none beats g.
        #
        # On this puzzle, testing on generation would still be correct: all
        # paths from a start to the goal share parity, so a cheaper one is at
        # least 2 moves shorter. Every state on it has f below the current
        # state's and would have been expanded first. The bug needs unequal
        # edge costs: a goal generated through one expensive edge while a path
        # of cheap edges is still pending.
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
            # best_g also guards parent. Without this check, a later, costlier
            # push overwrites parent[nxt], and the rebuilt path is valid but
            # not optimal.
            if new_g < best_g.get(nxt, new_g + 1):
                best_g[nxt] = new_g
                parent[nxt] = (state, move)
                h_nxt = heuristic(nxt)
                heapq.heappush(frontier, (new_g + h_nxt, h_nxt, counter, nxt))
                counter += 1
        max_frontier = max(max_frontier, len(frontier))

    # Unreachable for a solvable start: the goal is in its component.
    raise AssertionError("frontier exhausted without reaching the goal")


def _reconstruct(parent, state):
    moves = []
    while parent[state] is not None:
        state, move = parent[state]
        moves.append(move)
    return "".join(reversed(moves))
