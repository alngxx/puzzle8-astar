import csv
import gc
import io
import random
from collections import Counter

import pytest

import puzzle8.bench as bench
from puzzle8.bench import (
    BUCKETS,
    ComparisonError,
    format_table,
    run_comparison,
    sample_bucket,
    summarise,
    write_csv,
)
from puzzle8.board import parse_state
from puzzle8.heuristics import linear_conflict, manhattan
from puzzle8.oracle import optimal_distance, states_at_depth
from puzzle8.search import SearchResult, astar


# --- Sampling by exact depth -------------------------------------------------

def test_states_at_depth_are_exactly_that_deep():
    for depth in (0, 1, 7, 31):
        pool = states_at_depth(depth)
        assert pool and all(optimal_distance(s) == depth for s in pool)
    assert len(states_at_depth(31)) == 2
    assert states_at_depth(32) == []


@pytest.mark.parametrize("name, low, high", BUCKETS)
def test_samples_are_at_their_stated_depth_within_the_bucket(name, low, high):
    sample = sample_bucket(low, high, 20, random.Random(1))
    assert len(sample) == 20
    assert len({s for s, _ in sample}) == 20  # no duplicates
    for state, depth in sample:
        assert low <= depth <= high
        assert optimal_distance(state) == depth  # the oracle's word, not a walk length


def test_samples_spread_evenly_over_depths():
    counts = Counter(d for _, d in sample_bucket(25, 31, 20, random.Random(1)))
    # 7 depths share 20 states; depth 31 has only 2 states in total, so it
    # gives 2 and the others make up the rest -- 3 each, evenly.
    assert counts == {25: 3, 26: 3, 27: 3, 28: 3, 29: 3, 30: 3, 31: 2}


def test_small_bucket_returns_every_state_rather_than_repeating():
    sample = sample_bucket(0, 2, 100, random.Random(1))
    assert len(sample) == 1 + 2 + 4


def test_sampling_is_reproducible_with_a_seed():
    a = sample_bucket(15, 20, 10, random.Random(7))
    b = sample_bucket(15, 20, 10, random.Random(7))
    assert a == b


# --- Correctness check baked into the comparison -----------------------------

def test_every_run_is_at_its_oracle_depth():
    runs = run_comparison(per_bucket=3, seed=5)
    assert len(runs) == 3 * len(BUCKETS)
    for run in runs:
        for result in run.results.values():
            assert result.length == run.depth


def test_a_non_optimal_path_stops_the_comparison(monkeypatch):
    # Pretend the search returned a valid path two moves too long: "UD" at
    # the goal moves the blank up from its corner and straight back. The
    # comparison must refuse to report numbers built on it.
    real_astar = bench.astar

    def padded(state, heuristic):
        r = real_astar(state, heuristic=heuristic)
        return SearchResult(r.path + "UD", r.nodes_expanded, r.nodes_generated,
                            r.max_frontier, r.seconds)

    monkeypatch.setattr(bench, "astar", padded)
    with pytest.raises(ComparisonError, match="oracle says"):
        run_comparison(per_bucket=1, seed=5)


def test_an_illegal_path_stops_the_comparison(monkeypatch):
    def nonsense(state, heuristic):
        return SearchResult("UUUU", 0, 1, 1, 0.0)
    monkeypatch.setattr(bench, "astar", nonsense)
    with pytest.raises(ComparisonError, match="not legal|does not reach"):
        run_comparison(per_bucket=1, seed=5)


# --- Summary and output ------------------------------------------------------

def test_summary_counts_the_exceptions_honestly():
    runs = run_comparison(per_bucket=4, seed=5)
    for summary in summarise(runs):
        in_bucket = [r for r in runs if r.bucket == summary.bucket]
        worse = sum(r.results["linear"].nodes_expanded > r.results["manhattan"].nodes_expanded
                    for r in in_bucket)
        assert summary.second_worse == worse
        assert summary.n == len(in_bucket)


def test_known_exception_state_is_counted_not_hidden():
    # 760584312 is one of the states where linear conflict expands more
    # (tests/test_heuristic_comparison.py). A bucket holding just that state
    # must report it in the table, not smooth it over.
    state = parse_state("760584312")
    run = bench.Run("only", 26, state, {
        "manhattan": astar(state, heuristic=manhattan),
        "linear": astar(state, heuristic=linear_conflict),
    })
    summary, = summarise([run], buckets=(("only", 26, 26),))
    assert summary.second_worse == 1
    table = format_table([summary], per_bucket=1, seed=0)
    assert "linear expanded more nodes than manhattan on 1 of 1 states" in table


def test_table_mentions_every_bucket_and_the_check():
    runs = run_comparison(per_bucket=2, seed=5)
    table = format_table(summarise(runs), per_bucket=2, seed=5)
    for name, low, high in BUCKETS:
        assert f"{name}" in table and f"{low}-{high}" in table
    assert "every path checked" in table
    assert "seed 5" in table


def test_csv_has_one_row_per_state():
    runs = run_comparison(per_bucket=2, seed=5)
    buffer = io.StringIO()
    write_csv(runs, buffer)
    rows = list(csv.reader(io.StringIO(buffer.getvalue())))
    assert rows[0][:3] == ["bucket", "depth", "state"]
    assert "manhattan_expanded" in rows[0] and "linear_expanded" in rows[0]
    assert len(rows) == 1 + len(runs)
    for row, run in zip(rows[1:], runs):
        assert int(row[1]) == run.depth
        assert row[2] == "".join(map(str, run.state))


def test_garbage_collector_is_restored_even_after_a_failure(monkeypatch):
    # Paused during timing; it must come back on however the run ends.
    assert gc.isenabled()
    run_comparison(per_bucket=1, seed=5)
    assert gc.isenabled()

    def nonsense(state, heuristic):
        return SearchResult("UUUU", 0, 1, 1, 0.0)
    monkeypatch.setattr(bench, "astar", nonsense)
    with pytest.raises(ComparisonError):
        run_comparison(per_bucket=1, seed=5)
    assert gc.isenabled()
