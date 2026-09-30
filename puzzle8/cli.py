"""Command-line interface: python -m puzzle8 {solve,random,compare}.

Exit codes: 0 ok, 1 unsolvable, 2 bad input, 3 internal error.
"""

import argparse
import random
import sys

from puzzle8.bench import (
    DEFAULT_PER_BUCKET,
    ComparisonError,
    format_table,
    run_comparison,
    summarise,
    write_csv,
)
from puzzle8.board import (
    GOAL,
    ParseError,
    apply_moves,
    format_board,
    inversions,
    is_solvable,
    parse_state,
)
from puzzle8.heuristics import linear_conflict, manhattan
from puzzle8.oracle import states_at_depth
from puzzle8.search import astar

EXIT_OK = 0
EXIT_UNSOLVABLE = 1
EXIT_BAD_INPUT = 2
EXIT_INTERNAL = 3

HEURISTICS = {"manhattan": manhattan, "linear": linear_conflict}
MAX_DEPTH = 31
BOARDS_PER_ROW = 7


class BadInput(Exception):
    """User error, reported in one line with exit code 2."""


def _label(state):
    return "".join(map(str, state))


# --- solve --------------------------------------------------------------------

def cmd_solve(args):
    try:
        state = parse_state(args.state)
    except ParseError as e:
        raise BadInput(str(e)) from None

    if not is_solvable(state):
        count = inversions(state)
        print(f"Unsolvable: {_label(state)} has {count} inversion{'' if count == 1 else 's'} "
              f"(odd).")
        print("Every move keeps the inversion count's parity, and the goal has 0,")
        print("so only states with an even count can reach it. No search was run.")
        return EXIT_UNSOLVABLE

    result = astar(state, heuristic=HEURISTICS[args.heuristic])
    # Replay the path rather than trust it.
    if apply_moves(state, result.path) != GOAL:
        raise AssertionError("search returned a path that does not reach the goal")

    print(f"Start:       {_label(state)}")
    print(f"Heuristic:   {args.heuristic}")
    print(f"Solution:    {result.length} move{'' if result.length == 1 else 's'} (optimal)")
    if result.path:
        print(f"Moves:       {result.path}")
        print("             (U/D/L/R = the direction the blank moves)")
    else:
        print("Moves:       none, already solved")

    if args.stats:
        print()
        print(f"Nodes expanded:   {result.nodes_expanded}")
        print(f"Nodes generated:  {result.nodes_generated}")
        print(f"Max frontier:     {result.max_frontier}")
        print(f"Time:             {result.seconds * 1000:.2f} ms")

    if args.show_boards:
        print()
        print(_board_sequence(state, result.path))
    return EXIT_OK


def _board_sequence(state, path):
    """Every board along the path, several to a row."""
    blocks = [("start", state)]
    for step, move in enumerate(path, start=1):
        state = apply_moves(state, move)
        blocks.append((f"{step} {move}", state))

    rows = []
    for i in range(0, len(blocks), BOARDS_PER_ROW):
        chunk = blocks[i:i + BOARDS_PER_ROW]
        boards = [format_board(s).split("\n") for _, s in chunk]
        lines = ["   ".join(f"{label:<5}" for label, _ in chunk)]
        for r in range(3):
            lines.append("   ".join(board[r] for board in boards))
        rows.append("\n".join(line.rstrip() for line in lines))
    return "\n\n".join(rows)


# --- random -------------------------------------------------------------------

def cmd_random(args):
    if not 0 <= args.depth <= MAX_DEPTH:
        raise BadInput(f"--depth must be between 0 and {MAX_DEPTH}, got {args.depth}")
    # Sampled from the oracle: a D-move random walk can end closer than D.
    state = random.Random(args.seed).choice(states_at_depth(args.depth))
    print(_label(state))
    return EXIT_OK


# --- compare ------------------------------------------------------------------

def cmd_compare(args):
    if args.per_bucket < 1:
        raise BadInput(f"--per-bucket must be at least 1, got {args.per_bucket}")
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)

    # Open first so a bad path fails before the run, not after.
    csv_file = None
    if args.csv:
        try:
            csv_file = open(args.csv, "w", newline="")
        except OSError as e:
            raise BadInput(f"cannot write {args.csv}: {e.strerror}") from None

    try:
        try:
            runs = run_comparison(per_bucket=args.per_bucket, seed=seed)
        except ComparisonError as e:
            print(f"comparison failed its correctness check: {e}", file=sys.stderr)
            return EXIT_INTERNAL
        print(format_table(summarise(runs), args.per_bucket, seed))
        if args.seed is None:
            print(f"\n(pass --seed {seed} to reproduce this sample)")
        if csv_file:
            write_csv(runs, csv_file)
            print(f"\nWrote {len(runs)} rows to {args.csv}")
    finally:
        if csv_file:
            csv_file.close()
    return EXIT_OK


# --- entry point --------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m puzzle8",
        description="Optimal 8-puzzle solver (A*) and heuristic comparison.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    solve = commands.add_parser("solve", help="solve one state optimally")
    solve.add_argument("state", help='9 digits, 0 for the blank, e.g. "867254301"')
    solve.add_argument("--heuristic", choices=sorted(HEURISTICS), default="manhattan")
    solve.add_argument("--stats", action="store_true",
                       help="print nodes expanded/generated, max frontier, time")
    solve.add_argument("--show-boards", action="store_true",
                       help="print every board along the solution")
    solve.set_defaults(run=cmd_solve)

    rand = commands.add_parser("random", help="print a random state at an exact depth")
    rand.add_argument("--depth", type=int, required=True,
                      help=f"optimal distance from the goal, 0-{MAX_DEPTH}")
    rand.add_argument("--seed", type=int, help="for a reproducible choice")
    rand.set_defaults(run=cmd_random)

    comp = commands.add_parser("compare", help="depth-bucketed heuristic comparison")
    comp.add_argument("--per-bucket", type=int, default=DEFAULT_PER_BUCKET,
                      help=f"states per bucket (default {DEFAULT_PER_BUCKET})")
    comp.add_argument("--seed", type=int, help="for a reproducible sample")
    comp.add_argument("--csv", metavar="PATH", help="also write per-state rows here")
    comp.set_defaults(run=cmd_compare)
    return parser


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse has already printed the message.
        return e.code if isinstance(e.code, int) else EXIT_BAD_INPUT

    try:
        return args.run(args)
    except BadInput as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as e:  # a bug; still no traceback
        print(f"internal error: {type(e).__name__}: {e}", file=sys.stderr)
        return EXIT_INTERNAL
