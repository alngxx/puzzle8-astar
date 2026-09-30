"""Manhattan vs linear conflict, compared through A*."""

import random
from collections import deque

import pytest

import puzzle8.search as search
from puzzle8.board import GOAL, apply_moves, neighbours, parse_state
from puzzle8.heuristics import linear_conflict, manhattan
from puzzle8.oracle import distances, optimal_distance
from puzzle8.search import astar


# --- Same answers ------------------------------------------------------------

def test_both_heuristics_find_the_true_optimum():
    # Both are admissible, so any length mismatch means a broken heuristic.
    rng = random.Random(41052)
    for state in rng.sample(sorted(distances()), 200):
        by_manhattan = astar(state, heuristic=manhattan)
        by_lc = astar(state, heuristic=linear_conflict)
        assert by_manhattan.length == by_lc.length == optimal_distance(state), state
        assert apply_moves(state, by_lc.path) == GOAL


# --- Fewer expansions ---------------------------------------------------------

# Scrambled states used elsewhere in the suite, not picked for their counts.
SCRAMBLED = ["724506831", "573146820", "806547231", "867254301", "647850321"]


@pytest.mark.parametrize("text", SCRAMBLED)
def test_linear_conflict_expands_no_more_than_manhattan(text):
    state = parse_state(text)
    by_manhattan = astar(state, heuristic=manhattan)
    by_lc = astar(state, heuristic=linear_conflict)
    assert by_lc.nodes_expanded <= by_manhattan.nodes_expanded


# --- ...but not on every state, and why that is still correct ----------------

# Every state in random.Random(41052).sample(sorted(distances()), 3000) where
# linear conflict expands more nodes than Manhattan. Dominance only bounds the
# f < C* expansions; the surplus is tie-breaking at f = C*.
MORE_EXPANSIONS_UNDER_LC = [
    "230856174", "760584312", "148720653", "740531826", "841537062", "751832640",
    "628340175", "236015784", "041785263", "306572184", "041238675", "751480326",
]


def _expanded_states(monkeypatch, start, heuristic):
    """Run the real search, recording each state it expands."""
    expanded = []
    real_neighbours = search.neighbours

    def recording(state):  # search calls neighbours() once per expansion
        expanded.append(state)
        return real_neighbours(state)

    monkeypatch.setattr(search, "neighbours", recording)
    result = astar(start, heuristic=heuristic)
    monkeypatch.setattr(search, "neighbours", real_neighbours)
    assert len(expanded) == result.nodes_expanded
    return set(expanded), result


def _distances_from(start):
    """BFS from `start`: g*(s) for every state, independent of A*."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for _, nxt in neighbours(state):
            if nxt not in dist:
                dist[nxt] = dist[state] + 1
                queue.append(nxt)
    return dist


@pytest.mark.parametrize("text", MORE_EXPANSIONS_UNDER_LC)
def test_extra_expansions_are_all_ties_at_the_optimal_cost(monkeypatch, text):
    start = parse_state(text)
    cost = optimal_distance(start)
    g = _distances_from(start)
    by_manhattan, m_result = _expanded_states(monkeypatch, start, manhattan)
    by_lc, lc_result = _expanded_states(monkeypatch, start, linear_conflict)

    # The anomaly being explained.
    assert lc_result.nodes_expanded > m_result.nodes_expanded

    for expanded, h in ((by_manhattan, manhattan), (by_lc, linear_conflict)):
        below = {s for s in expanded if g[s] + h(s) < cost}
        # Expanded exactly the states with f < C*, computed independently...
        assert below == {s for s in g if g[s] + h(s) < cost}
        # ...and nothing beyond C*, so the rest are ties at exactly C*.
        assert all(g[s] + h(s) == cost for s in expanded - below)

    # Every state linear conflict is forced to expand, Manhattan is too.
    lc_below = {s for s in by_lc if g[s] + linear_conflict(s) < cost}
    m_below = {s for s in by_manhattan if g[s] + manhattan(s) < cost}
    assert lc_below <= m_below

    # LC's f = C* band is smaller too; A* just explores more of it.
    def band(h):
        return sum(g[s] + h(s) == cost for s in g)
    assert band(linear_conflict) < band(manhattan)
