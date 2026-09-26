"""Hand-checkable sanity check for the BFS oracle and the Manhattan heuristic.

Each case starts at the goal and applies a short move sequence, printing the
board after every move alongside the oracle's distance and the heuristic's
estimate. A state reached in N moves can be no further than N from the goal,
so each trace can be checked by eye: the distance should count back down to
zero, and the estimate should never exceed it.

Run from the repo root:  python scripts/check_oracle.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puzzle8.board import GOAL, apply_move, format_board
from puzzle8.heuristics import manhattan
from puzzle8.oracle import distances, optimal_distance

TRACES = ["L", "UL", "ULD", "ULDR", "ULDRUL"]


def show(label, state):
    distance = optimal_distance(state)
    estimate = manhattan(state)
    board = format_board(state).split("\n")
    print(f"  {label:<14} {board[0]}   oracle distance: {distance}")
    print(f"  {'':<14} {board[1]}   manhattan:       {estimate}")
    print(f"  {'':<14} {board[2]}   admissible:      "
          f"{'OK' if estimate <= distance else 'OVERESTIMATE'}")
    print()
    return distance, estimate


def main():
    table = distances()
    print(f"States reachable from the goal: {len(table)}")
    print(f"Longest optimal solution:       {max(table.values())} moves")
    print(f"(9!/2 = 181440 states, 31 moves -- both are known properties)\n")

    all_ok = True
    for moves in TRACES:
        print(f"Trace {moves!r} applied to the goal:")
        state = GOAL
        show("start (goal)", state)
        for step, move in enumerate(moves, start=1):
            state = apply_move(state, move)
            distance, estimate = show(f"after {step}: {move}", state)
            ok = distance <= step and estimate <= distance
            all_ok = all_ok and ok
        print(f"  reached in {len(moves)} moves; oracle says "
              f"{optimal_distance(state)} back to the goal\n")

    print("ALL TRACES CONSISTENT" if all_ok else "SOME TRACES FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
