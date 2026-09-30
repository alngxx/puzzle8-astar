"""Depth-bucketed comparison of Manhattan and linear conflict.

States are sampled at exact oracle depths, not by random walks. Every path is
checked against the oracle before its numbers count.
"""

import csv
import gc
import random
import statistics
from dataclasses import dataclass

from puzzle8.board import GOAL, IllegalMoveError, apply_moves
from puzzle8.heuristics import linear_conflict, manhattan
from puzzle8.oracle import states_at_depth
from puzzle8.search import astar

BUCKETS = (("shallow", 5, 10), ("medium", 15, 20), ("deep", 21, 24), ("hard", 25, 31))
HEURISTICS = (("manhattan", manhattan), ("linear", linear_conflict))
DEFAULT_PER_BUCKET = 20
METRICS = ("expanded", "generated", "ms")


class ComparisonError(RuntimeError):
    """A heuristic returned a path that is invalid or not optimal."""


@dataclass(frozen=True)
class Run:
    bucket: str
    depth: int
    state: tuple
    results: dict  # heuristic name -> SearchResult


@dataclass(frozen=True)
class BucketSummary:
    bucket: str
    low: int
    high: int
    n: int
    stats: dict          # heuristic name -> metric -> (median, mean)
    ratios: dict         # metric -> (median ratio, mean ratio), first / second
    second_worse: int    # states where the second heuristic expanded more nodes


def sample_bucket(low, high, n, rng):
    """Up to n (state, depth) pairs, spread evenly over depths low..high.

    Depths take turns so rare ones aren't swamped (depth 31 has 2 states,
    depth 25 has 15578). Uniform without replacement within each depth.
    """
    pools = {d: states_at_depth(d) for d in range(low, high + 1)}
    quota = dict.fromkeys(pools, 0)
    chosen = 0
    while chosen < n:
        progressed = False
        for depth, pool in pools.items():
            if chosen < n and quota[depth] < len(pool):
                quota[depth] += 1
                chosen += 1
                progressed = True
        if not progressed:
            break  # the bucket holds fewer than n states
    return [(state, depth)
            for depth, pool in pools.items()
            for state in rng.sample(pool, quota[depth])]


def _check(state, depth, name, result):
    label = "".join(map(str, state))
    try:
        end = apply_moves(state, result.path)
    except IllegalMoveError as e:
        raise ComparisonError(f"{name} on {label}: path is not legal ({e})") from None
    if end != GOAL:
        raise ComparisonError(f"{name} on {label}: path does not reach the goal")
    if result.length != depth:
        raise ComparisonError(
            f"{name} on {label}: {result.length} moves, but the oracle says {depth}")


def run_comparison(per_bucket=DEFAULT_PER_BUCKET, seed=None,
                   buckets=BUCKETS, heuristics=HEURISTICS):
    """Solve each sampled state with every heuristic; return the runs."""
    rng = random.Random(seed)
    # Untimed warm-up: the first search in a process runs ~2x slower.
    for _, heuristic in heuristics:
        astar(states_at_depth(10)[0], heuristic=heuristic)
    # Pause GC while timing, as timeit does: its pauses inflated mean times.
    # The search creates no reference cycles, so memory is still freed.
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        runs = []
        for bucket, low, high in buckets:
            for state, depth in sample_bucket(low, high, per_bucket, rng):
                results = {}
                for name, heuristic in heuristics:
                    result = astar(state, heuristic=heuristic)
                    _check(state, depth, name, result)
                    results[name] = result
                runs.append(Run(bucket, depth, state, results))
    finally:
        if was_enabled:
            gc.enable()
    return runs


def _metric(result, metric):
    if metric == "expanded":
        return result.nodes_expanded
    if metric == "generated":
        return result.nodes_generated
    return result.seconds * 1000


def summarise(runs, buckets=BUCKETS, heuristics=HEURISTICS):
    first, second = heuristics[0][0], heuristics[1][0]
    summaries = []
    for bucket, low, high in buckets:
        in_bucket = [r for r in runs if r.bucket == bucket]
        if not in_bucket:
            continue
        stats = {}
        for name, _ in heuristics:
            stats[name] = {}
            for metric in METRICS:
                values = [_metric(r.results[name], metric) for r in in_bucket]
                stats[name][metric] = (statistics.median(values), statistics.fmean(values))
        ratios = {}
        for metric in METRICS:
            (med_a, mean_a), (med_b, mean_b) = stats[first][metric], stats[second][metric]
            ratios[metric] = (_ratio(med_a, med_b), _ratio(mean_a, mean_b))
        worse = sum(r.results[second].nodes_expanded > r.results[first].nodes_expanded
                    for r in in_bucket)
        summaries.append(BucketSummary(bucket, low, high, len(in_bucket), stats, ratios, worse))
    return summaries


def _ratio(a, b):
    return a / b if b else float("nan")


def _num(value, metric):
    if metric == "ms":
        return f"{value:.2f}"
    return f"{value:.0f}" if value == int(value) else f"{value:.1f}"


def format_table(summaries, per_bucket, seed, heuristics=HEURISTICS):
    first, second = heuristics[0][0], heuristics[1][0]
    lines = [
        f"Depth-bucketed comparison: {first} vs {second}",
        f"seed {seed}, up to {per_bucket} states per bucket, spread evenly over its depths",
        "(depth 31 has only 2 states in the whole puzzle, so it supplies at most 2)",
        "every path checked: length equals the oracle depth and replays to the goal",
        "",
        f"{'':<30}{'nodes expanded':^20}{'nodes generated':^20}{'time (ms)':^20}".rstrip(),
        f"{'bucket':<9}{'depths':<7}{'n':>3}  {'heuristic':<9}"
        + f"{'median':>10}{'mean':>10}" * 3,
    ]
    for s in summaries:
        prefix = f"{s.bucket:<9}{f'{s.low}-{s.high}':<7}{s.n:>3}  "
        blank = " " * len(prefix)
        for i, (name, _) in enumerate(heuristics):
            cells = "".join(f"{_num(s.stats[name][m][0], m):>10}{_num(s.stats[name][m][1], m):>10}"
                            for m in METRICS)
            lines.append((prefix if i == 0 else blank) + f"{name:<9}" + cells)
        cells = "".join(f"{s.ratios[m][0]:>10.2f}{s.ratios[m][1]:>10.2f}" for m in METRICS)
        lines.append(blank + f"{'ratio':<9}" + cells)
        lines.append(blank + f"{second} expanded more nodes than {first} "
                     f"on {s.second_worse} of {s.n} states")
        lines.append("")
    lines.append(f"ratio = {first} / {second}: above 1 means {second} did less work.")
    lines.append("Times are wall-clock and noisy, especially below 0.1 ms. They include")
    lines.append(f"computing the heuristic, which costs more for {second}, so the time")
    lines.append("ratio usually trails the node ratio.")
    return "\n".join(lines)


def write_csv(runs, file, heuristics=HEURISTICS):
    """One row per sampled state, with each heuristic's raw numbers."""
    writer = csv.writer(file)
    header = ["bucket", "depth", "state"]
    for name, _ in heuristics:
        header += [f"{name}_expanded", f"{name}_generated",
                   f"{name}_max_frontier", f"{name}_ms"]
    writer.writerow(header)
    for run in runs:
        row = [run.bucket, run.depth, "".join(map(str, run.state))]
        for name, _ in heuristics:
            r = run.results[name]
            row += [r.nodes_expanded, r.nodes_generated, r.max_frontier,
                    f"{r.seconds * 1000:.3f}"]
        writer.writerow(row)
