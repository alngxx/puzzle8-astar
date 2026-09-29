# puzzle8-astar

An optimal solver for the 8-puzzle (the 3×3 sliding-tile puzzle), using A*
search with two heuristics: **Manhattan distance** and **Manhattan + linear
conflict**. Everything is checked against a breadth-first search of the entire
state space, which gives the true optimal distance for every one of the
181,440 solvable states.

Also included: a command-line tool, and a comparison of how much work each
heuristic saves at different puzzle depths.

## Requirements

- Python 3.10 or newer. The solver uses only the standard library.
- [pytest](https://pytest.org), only for running the tests.

There is no install step. Clone the repository and run everything from its root
folder:

```bash
cd puzzle8-astar
python3 -m pip install pytest    # only needed for the tests
python3 -m puzzle8 --help
```

## How states are written

A state is 9 digits, read row by row, with `0` for the blank. The goal is
`123456780`:

```
1 2 3
4 5 6
7 8 .
```

Solutions are strings of `U`, `D`, `L`, `R`, the direction **the blank**
moves. `L` means the blank slides left (and the tile beside it slides right).

## Worked example

**1. Get a puzzle.** Ask for a random state exactly 20 moves from solved:

```
$ python3 -m puzzle8 random --depth 20 --seed 7
461503827
```

The depth is exact. The state is drawn from the oracle's list of every state
20 moves out, not produced by 20 random moves, which could land closer.

**2. Solve it**, and ask for search statistics:

```
$ python3 -m puzzle8 solve 461503827 --stats
Start:       461503827
Heuristic:   manhattan
Solution:    20 moves (optimal)
Moves:       URDLLDRRULLDRULURDRD
             (U/D/L/R = the direction the blank moves)

Nodes expanded:   413
Nodes generated:  674
Max frontier:     256
Time:             0.81 ms
```

**3. Solve it again with the stronger heuristic.** It finds the same 20-move
solution but expands 172 states instead of 413:

```
$ python3 -m puzzle8 solve 461503827 --heuristic linear --stats
Start:       461503827
Heuristic:   linear
Solution:    20 moves (optimal)
Moves:       URDLLDRRULLDRULURDRD
             (U/D/L/R = the direction the blank moves)

Nodes expanded:   172
Nodes generated:  287
Max frontier:     115
Time:             0.51 ms
```

**4. Watch a solution play out.** `--show-boards` prints every board along the
way (a short puzzle, to keep it readable):

```
$ python3 -m puzzle8 solve 123805476 --show-boards
Start:       123805476
Heuristic:   manhattan
Solution:    6 moves (optimal)
Moves:       LDRURD
             (U/D/L/R = the direction the blank moves)

start   1 L     2 D     3 R     4 U     5 R     6 D
1 2 3   1 2 3   1 2 3   1 2 3   1 2 3   1 2 3   1 2 3
8 . 5   . 8 5   4 8 5   4 8 5   4 . 5   4 5 .   4 5 6
4 7 6   4 7 6   . 7 6   7 . 6   7 8 6   7 8 6   7 8 .
```

**5. Try an impossible one.** Swapping two tiles of the goal gives a state that
can never be solved. It is rejected at once, without searching:

```
$ python3 -m puzzle8 solve 213456780
Unsolvable: 213456780 has 1 inversion (odd).
Every move keeps the inversion count's parity, and the goal has 0,
so only states with an even count can reach it. No search was run.
```

**6. Compare the heuristics at scale** with `python3 -m puzzle8 compare --seed 41052`;
see [compare](#compare) below for the output.

The two commands combine too. `random` prints only the state, so this solves a
fresh 12-move puzzle:

```bash
python3 -m puzzle8 solve "$(python3 -m puzzle8 random --depth 12)"
```

## Commands

### `solve`

```
python3 -m puzzle8 solve STATE [--heuristic manhattan|linear] [--stats] [--show-boards]
```

| Option | Meaning |
|---|---|
| `STATE` | 9 digits, e.g. `867254301`. Spaced or comma-separated forms work too if quoted: `"8 6 7 2 5 4 3 0 1"`. |
| `--heuristic` | `manhattan` (default) or `linear` (Manhattan + linear conflict). |
| `--stats` | Also print nodes expanded, nodes generated, largest frontier, and time. |
| `--show-boards` | Also print every board along the solution. |

Every solution is replayed from the start state before it is printed, so the
tool never reports a path it has not checked reaches the goal.

Bad input gets a specific one-line message and exit code 2:

```
$ python3 -m puzzle8 solve 12345678
error: expected 9 tiles, got 8
$ python3 -m puzzle8 solve 113456780
error: duplicate tile 1
$ python3 -m puzzle8 solve 12345678x
error: invalid tile 'x': tiles must be digits 0-8
```

### `random`

```
python3 -m puzzle8 random --depth D [--seed S]
```

Prints one state exactly `D` moves from the goal (0 to 31), chosen uniformly
among all such states. With `--seed`, the same state comes back every time.

### `compare`

```
python3 -m puzzle8 compare [--per-bucket N] [--seed S] [--csv PATH]
```

Samples states in four depth buckets: shallow (5–10 moves), medium (15–20),
deep (21–24) and hard (25–31). Deep is where a random puzzle most likely
lands: depths 21–24 hold 47% of all solvable states. It solves each state with
both heuristics and reports the median and mean work.

- **Sampling.** Each bucket takes `N` states (default 20), spread evenly over
  its depths and drawn uniformly within each depth. Depths are exact, taken
  from the oracle. Depth 31 has only 2 states in the whole puzzle, so it
  contributes at most 2.
- **Built-in correctness check.** Every path from both heuristics must be as
  long as the oracle's optimal distance and must replay to the goal.
  Otherwise the command stops with an error rather than printing numbers.
- **`--csv`** writes one row per state with both heuristics' raw numbers, for
  your own plots.
- **No `--seed`?** A random one is picked and printed, so any run can be
  repeated.

```
$ python3 -m puzzle8 compare --seed 41052
Depth-bucketed comparison: manhattan vs linear
seed 41052, up to 20 states per bucket, spread evenly over its depths
(depth 31 has only 2 states in the whole puzzle, so it supplies at most 2)
every path checked: length equals the oracle depth and replays to the goal

                                 nodes expanded     nodes generated        time (ms)
bucket   depths   n  heuristic    median      mean    median      mean    median      mean
shallow  5-10    20  manhattan       7.5       8.4      17.5      17.7      0.02      0.02
                     linear          7.5       8.2      17.5      17.4      0.03      0.03
                     ratio          1.00      1.02      1.00      1.02      0.65      0.67
                     linear expanded more nodes than manhattan on 0 of 20 states

medium   15-20   20  manhattan       122     164.4     204.5     271.9      0.21      0.30
                     linear         71.5      87.5     123.5     147.8      0.20      0.24
                     ratio          1.71      1.88      1.66      1.84      1.06      1.28
                     linear expanded more nodes than manhattan on 0 of 20 states

deep     21-24   20  manhattan     418.5     593.4       683     958.1      0.75      1.08
                     linear          221     289.1     366.5     473.2      0.59      0.77
                     ratio          1.89      2.05      1.86      2.02      1.28      1.39
                     linear expanded more nodes than manhattan on 0 of 20 states

hard     25-31   20  manhattan    3498.5    4078.2    5492.5    6336.2      6.75      7.82
                     linear       1800.5    2155.3      2856    3396.4      4.89      5.90
                     ratio          1.94      1.89      1.92      1.87      1.38      1.33
                     linear expanded more nodes than manhattan on 0 of 20 states

ratio = manhattan / linear: above 1 means linear did less work.
Times are wall-clock and noisy, especially below 0.1 ms. They include
computing the heuristic, which costs more for linear, so the time
ratio usually trails the node ratio.
```

Node counts are the same on every machine and every run with the same seed.
Times are not: they depend on the machine, and a single system hiccup can
visibly move a mean, so medians are the safer time figures. In one
`--per-bucket 200 --seed 41052` run, a single deep-bucket search took 142 ms
instead of its usual 2 ms. That one search dragged the bucket's mean time ratio
to 0.78, suggesting linear was slower, while the median ratio stayed at 1.26. Python's garbage collector is paused while searches are timed (as
`timeit` does). Its collections otherwise landed inside individual searches
and inflated the means.

**Reading the results.** On shallow puzzles linear conflict saves no nodes and
costs time: each search takes about 1.5× as long (time ratio 0.65–0.67),
because every estimate costs more and there is almost nothing to prune. From
medium depth on it pays off. The figures below come from a
`--per-bucket 200 --seed 41052 --csv` run, taking Manhattan ÷ linear for each
state separately and then the median (interquartile range in brackets):

| Bucket | Nodes expanded | Time |
|---|---|---|
| shallow | 1.00 (1.00–1.00) | 0.67 (0.64–0.69) |
| medium | 1.63 (1.40–1.88) | 1.08 (0.93–1.25) |
| deep | 1.96 (1.66–2.29) | 1.33 (1.10–1.53) |
| hard | 1.91 (1.79–2.09) | 1.35 (1.25–1.47) |

That is about 40% fewer nodes on medium puzzles and roughly half on deep and
hard ones. Time improves less than nodes, because each estimate costs more to
compute. On a quarter of medium puzzles the time ratio is below 0.93, so there
linear is slower overall.

It does **not** expand fewer nodes on every single state. Two samples, drawn
differently, so their rates are reported separately rather than pooled:

- **Uniform over all solvable states:** 12 of 3,000 (0.4%, 95% interval
  roughly 0.2–0.7%). These are the 12 states in
  `tests/test_heuristic_comparison.py`, which says how to regenerate them.
- **The depth-bucketed run above:** 3 of 800. There were 2 in medium and 1 in
  deep, and linear expanded between 2 and 49 more nodes on them.

This is expected, and the table counts it rather than hiding it. A* must expand every state whose estimated total
cost f is below the optimal cost C*. Linear conflict is never below
Manhattan, so the states it must expand are always a subset of Manhattan's.
But states with f exactly equal to C* are expanded or not depending on
tie-breaking, and there linear conflict can be unlucky.
`tests/test_heuristic_comparison.py` checks this explanation state by state.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Solved, or `random` / `compare` finished. |
| 1 | The state is unsolvable (rejected before any search). |
| 2 | Bad input: malformed state, unknown option, impossible depth, CSV path that can't be written. |
| 3 | Internal error, i.e. a bug. Reported as one line, never a Python traceback. |

## Running the tests

```bash
python3 -m pytest
```

This runs 147 tests in about 10 seconds. Where it's feasible, properties are
checked over **all 181,440 solvable states** rather than a sample:

| File | What it checks |
|---|---|
| `tests/test_board.py` | Parsing (including rejection of non-ASCII digits), moves, the solvability rule. |
| `tests/test_oracle.py` | The BFS finds exactly the 181,440 even-parity states, and the longest optimal solution is 31 moves (a known property of the puzzle). |
| `tests/test_heuristics.py` | Both heuristics never overestimate, never change by more than 1 per move (consistency), and match a from-scratch recalculation, on every state. Also shows that the naive "+2 per conflicting pair" version of linear conflict overestimates. |
| `tests/test_search.py` | A* matches the oracle on 200 random states and both 31-move puzzles. Every path is replayed, not trusted. |
| `tests/test_heuristic_comparison.py` | Both heuristics give identical optimal lengths. Where linear conflict expands more nodes, the extra ones are all ties at f = C*. |
| `tests/test_bench.py` | Sampling hits exact depths, and a wrong or illegal path stops the comparison. |
| `tests/test_cli.py` | Every command, flag and exit code, including that no traceback ever reaches the user. |

## Other scripts

Hand-checkable printouts, run from the repo root:

| Script | Shows |
|---|---|
| `scripts/check_solvability.py` | The inversion-parity rule, with every inverted pair listed. |
| `scripts/check_oracle.py` | Short move sequences from the goal, board by board, with the oracle's distance and the heuristic's estimate at each step. |
| `scripts/demonstrate_invariants.py` | What breaks without A*'s safeguards. Removing duplicate detection costs 202× the work on one state. A closed set combined with an inconsistent heuristic returns a 17-move path where 13 is optimal. It is a demonstration only: the deliberately broken search and heuristic live in the script, not in the solver. |

## Project layout

| File | Role |
|---|---|
| `puzzle8/board.py` | States, parsing, moves, solvability (inversion parity). |
| `puzzle8/oracle.py` | Breadth-first search out from the goal: the true distance of every solvable state. It shares no code with A*. |
| `puzzle8/heuristics.py` | `manhattan` and `linear_conflict`. |
| `puzzle8/search.py` | A*: a heap ordered by (f, h, insertion order), lazy deletion, goal test on pop, closed set. |
| `puzzle8/bench.py` | The depth-bucketed comparison. |
| `puzzle8/cli.py` | The command-line interface (`python3 -m puzzle8`). |
