"""A* search for the 8-puzzle.

Every move costs 1, so g(s) is the number of moves from the start to s, and
A* expands states in order of f = g + h. With an admissible heuristic the
first time the goal is popped, its g is the optimal solution length.
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
    # Checked up front: an unsolvable start would make the search exhaust all
    # 181440 states of the other parity class before giving up.
    if not is_solvable(start):
        raise UnsolvableError("state is unsolvable (odd inversion parity)")

    t0 = time.perf_counter()
    h0 = heuristic(start)
    # Entries are (f, h, counter, state). Tuples compare left to right, so
    # equal f breaks toward lower h (the state believed nearer the goal),
    # and the counter settles any remaining tie in push order -- which also
    # means two states are never compared directly.
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

        # Lazy deletion: heapq can't lower a key in place, so finding a
        # shorter path pushes a second entry instead of updating the first.
        # The older, costlier entry is still in the heap; recognise it by its
        # g no longer matching the best known one, and drop it here.
        if g != best_g[state]:
            continue

        # Closed set: a state is expanded at most once.
        #
        # Every move is reversible, so the state graph is full of cycles. With
        # no duplicate detection at all (neither this nor best_g), A* degrades
        # to tree search: each expansion regenerates its own parent, and a
        # state is expanded again for every path that reaches it -- on one
        # depth-24 instance, 290108 expansions instead of 1436. On an
        # unsolvable start (were the parity check above missing) tree search
        # would never terminate at all, since the tree it walks is infinite.
        #
        # With Manhattan this check is redundant with best_g: the heuristic is
        # consistent, so a state's g is already optimal when it is first
        # popped, and best_g never admits a cheaper entry afterwards. The
        # check makes "at most once" hold for any heuristic, not just a
        # consistent one -- but that is also its cost. With an admissible yet
        # inconsistent heuristic, a cheaper path to a closed state can turn up
        # later, and refusing to reopen it returns a suboptimal solution.
        if state in closed:
            continue

        # Goal test on pop, not on generation. Generating the goal only shows
        # that *a* path reaches it; entries still on the frontier with smaller
        # f may lead to it more cheaply. When the goal is popped, its f = g is
        # the smallest f in the heap, and admissibility makes every other
        # entry's f a lower bound on any solution through it -- so none can
        # beat g, and g is optimal. A*'s optimality proof rests on this.
        #
        # On this particular puzzle, testing on generation would never
        # actually go wrong: every path from a given start to the goal has the
        # same parity, so a cheaper solution would be at least 2 moves
        # cheaper, and the frontier node leading to it, with an f below the
        # current state's, would already have been popped. The bug shows on
        # graphs with unequal edge costs: a goal generated through one
        # expensive edge while a path of several cheap edges is still pending.
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
