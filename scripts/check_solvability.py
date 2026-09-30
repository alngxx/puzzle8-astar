"""Print each case's inverted pairs so the parity rule can be checked by hand.

Run from the repo root: python scripts/check_solvability.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puzzle8.board import GOAL, apply_moves, format_board, inversions, is_solvable, parse_state

# (state, moves from goal that produce it, or None if claimed unreachable)
CASES = [
    ("123456708", "L"),        # 1 horizontal move: tile order unchanged
    ("123405786", "UL"),       # vertical move jumps 6 past 7 and 8: +2 inversions
    ("213456780", None),       # swap 1 and 2: 1 inversion
    ("321456780", None),       # reverse 1 2 3: 3 inversions
]


def inverted_pairs(state):
    tiles = [t for t in state if t != 0]
    return [(a, b) for i, a in enumerate(tiles) for b in tiles[i + 1:] if a > b]


def main():
    all_ok = True
    for text, moves in CASES:
        state = parse_state(text)
        pairs = inverted_pairs(state)
        count = inversions(state)
        solvable = is_solvable(state)

        print(f"State {text}")
        print("  " + format_board(state).replace("\n", "\n  "))
        print(f"  tiles without blank: {' '.join(str(t) for t in state if t != 0)}")
        print(f"  inverted pairs:      {pairs if pairs else 'none'}")
        print(f"  inversion count:     {count} ({'even' if count % 2 == 0 else 'odd'})")
        print(f"  is_solvable:         {solvable}")

        ok = len(pairs) == count
        if moves is not None:
            reached = apply_moves(GOAL, moves) == state
            print(f"  reachable from goal: moves {moves!r} -> {'yes' if reached else 'NO'}")
            ok = ok and reached and solvable
        else:
            print("  reachable from goal: not expected (odd parity)")
            ok = ok and not solvable
        print(f"  consistent:          {'OK' if ok else 'MISMATCH'}\n")
        all_ok = all_ok and ok

    print("ALL CASES CONSISTENT" if all_ok else "SOME CASES FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
