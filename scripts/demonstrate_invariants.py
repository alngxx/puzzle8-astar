"""Demonstrations of what breaks when A*'s safeguards are removed.

NOT part of the solver. Everything deliberately broken here -- the variant
search and the bad heuristic -- is defined in this file only, so nothing in
puzzle8/ can pick it up by accident.

1. Duplicate detection. With no closed set and no best-g check, A* becomes
   tree search and re-expands states once per path that reaches them.

2. Closed set + inconsistent heuristic. The real solver's closed set never
   reopens a state. That is safe for a consistent heuristic like Manhattan,
   but with a heuristic that is admissible yet inconsistent, a cheaper path
   to a closed state can turn up later and gets discarded.

Everything is deterministic; the output is identical on every run.

Run from the repo root:  python scripts/demonstrate_invariants.py
"""

import heapq
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puzzle8.board import GOAL, apply_moves, format_board, neighbours, parse_state
from puzzle8.heuristics import manhattan
from puzzle8.oracle import distances, optimal_distance
from puzzle8.search import astar


# --- Deliberately broken pieces (demonstration only) ------------------------

def astar_variant(start, heuristic, duplicate_detection):
    """A* without the closed set, for contrast with search.astar.

    duplicate_detection="none":   tree search -- every generated state is
                                  pushed, however it was reached.
    duplicate_detection="best_g": push only on a strictly cheaper path, and
                                  reopen already-expanded states if one
                                  turns up.

    Returns (solution length, nodes expanded). Same (f, h, counter) ordering
    and goal-on-pop test as the real solver, so counts are comparable.
    """
    h0 = heuristic(start)
    frontier = [(h0, h0, 0, start, 0)]
    counter = 1
    best_g = {start: 0}
    expanded = 0
    while frontier:
        f, h, _, state, g = heapq.heappop(frontier)
        if duplicate_detection == "best_g" and g != best_g[state]:
            continue  # stale entry
        if state == GOAL:
            return g, expanded
        expanded += 1
        for _, nxt in neighbours(state):
            new_g = g + 1
            if duplicate_detection == "best_g":
                if new_g >= best_g.get(nxt, new_g + 1):
                    continue
                best_g[nxt] = new_g
            h_nxt = heuristic(nxt)
            heapq.heappush(frontier, (new_g + h_nxt, h_nxt, counter, nxt, new_g))
            counter += 1
    raise AssertionError("frontier exhausted")


def tile_one_home_heuristic(state):
    """Exact distance if tile 1 is in its goal cell, otherwise 0.

    Admissible: it is either the true distance or 0, never more. But wildly
    inconsistent: moving tile 1 into or out of its home cell swings the
    estimate between 0 and the full distance in a single move.
    """
    return optimal_distance(state) if state[0] == 1 else 0


# --- Demonstrations ---------------------------------------------------------

def show_board(state):
    print("    " + format_board(state).replace("\n", "\n    "))


def demo_duplicate_detection():
    print("=" * 66)
    print("1. Removing duplicate detection (A* becomes tree search)")
    print("=" * 66)
    state = parse_state("625437810")
    print(f"State 625437810, oracle distance {optimal_distance(state)}:")
    show_board(state)

    t0 = time.perf_counter()
    graph = astar(state)
    t_graph = time.perf_counter() - t0
    t0 = time.perf_counter()
    tree_length, tree_expanded = astar_variant(state, manhattan, "none")
    t_tree = time.perf_counter() - t0

    print()
    print(f"  {'':<34} {'length':>6} {'expanded':>10} {'time':>9}")
    print(f"  {'graph search (search.astar)':<34} {graph.length:>6} "
          f"{graph.nodes_expanded:>10} {t_graph * 1000:>7.1f}ms")
    print(f"  {'tree search (no duplicate check)':<34} {tree_length:>6} "
          f"{tree_expanded:>10} {t_tree * 1000:>7.1f}ms")
    print()
    print(f"  Same optimal answer, {tree_expanded / graph.nodes_expanded:.0f}x "
          f"the expansions. Tree search re-expands a")
    print(f"  state once per path reaching it, and every move can be undone,")
    print(f"  so the paths multiply.")
    ok = graph.length == tree_length == optimal_distance(state)
    return ok and tree_expanded > graph.nodes_expanded


def demo_closed_set_with_inconsistent_heuristic():
    print()
    print("=" * 66)
    print("2. Closed set + admissible but inconsistent heuristic")
    print("=" * 66)
    table = distances()
    inconsistent_edges = sum(
        1 for s in table for _, n in neighbours(s)
        if abs(tile_one_home_heuristic(s) - tile_one_home_heuristic(n)) > 1
    )
    overestimates = sum(1 for s, d in table.items() if tile_one_home_heuristic(s) > d)
    print("Heuristic: exact distance if tile 1 is home, else 0.")
    print(f"  states where it overestimates: {overestimates}  (admissible)")
    print(f"  edges where it jumps by > 1:   {inconsistent_edges}  (inconsistent)")

    state = parse_state("104523786")
    true_length = optimal_distance(state)
    wrong = astar(state, heuristic=tile_one_home_heuristic)
    reopen_length, _ = astar_variant(state, tile_one_home_heuristic, "best_g")

    print()
    print(f"State 104523786:")
    show_board(state)
    print()
    print(f"  oracle (true optimal length):                {true_length}")
    print(f"  search.astar, closed set, never reopens:     {wrong.length}"
          f"   <-- WRONG")
    print(f"  same heuristic, reopening allowed:           {reopen_length}")
    print(f"  search.astar with Manhattan (consistent):    {astar(state).length}")
    print()
    print(f"  The path it returns is valid (it replays to the goal: "
          f"{apply_moves(state, wrong.path) == GOAL}), just not shortest.")
    print(f"  Same search, same heuristic: the only difference between {wrong.length} "
          f"and {reopen_length}")
    print(f"  is whether a closed state may be reopened when a cheaper path arrives.")
    return (wrong.length > true_length
            and reopen_length == true_length
            and apply_moves(state, wrong.path) == GOAL)


def main():
    ok = demo_duplicate_detection()
    ok = demo_closed_set_with_inconsistent_heuristic() and ok
    print()
    print("ALL DEMONSTRATIONS BEHAVED AS DESCRIBED" if ok else "UNEXPECTED RESULT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
