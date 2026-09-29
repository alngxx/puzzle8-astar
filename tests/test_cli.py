import re
import subprocess
import sys
from pathlib import Path

import pytest

import puzzle8.cli as cli
from puzzle8.bench import BUCKETS
from puzzle8.board import GOAL, apply_moves, parse_state
from puzzle8.cli import main
from puzzle8.oracle import optimal_distance

REPO = Path(__file__).resolve().parent.parent


def run(capsys, *argv):
    code = main(list(argv))
    out, err = capsys.readouterr()
    # Whatever happened, the user never sees a Python traceback.
    assert "Traceback" not in out + err
    return code, out, err


def moves_from(out):
    match = re.search(r"^Moves:\s+([UDLR]+)$", out, re.MULTILINE)
    return match.group(1) if match else ""


# --- solve --------------------------------------------------------------------

@pytest.mark.parametrize("heuristic", ["manhattan", "linear"])
def test_solve_prints_a_path_that_replays_to_the_goal(capsys, heuristic):
    code, out, _ = run(capsys, "solve", "724506831", "--heuristic", heuristic)
    assert code == 0
    assert "Solution:    20 moves (optimal)" in out
    path = moves_from(out)
    assert len(path) == 20 == optimal_distance(parse_state("724506831"))
    assert apply_moves(parse_state("724506831"), path) == GOAL


def test_default_heuristic_is_manhattan(capsys):
    _, out, _ = run(capsys, "solve", "724506831")
    assert "Heuristic:   manhattan" in out


def test_solve_already_solved(capsys):
    code, out, _ = run(capsys, "solve", "123456780")
    assert code == 0
    assert "0 moves" in out and "already solved" in out


def test_stats(capsys):
    _, out, _ = run(capsys, "solve", "867254301", "--stats")
    for label in ("Nodes expanded:", "Nodes generated:", "Max frontier:", "Time:"):
        assert label in out
    assert "Nodes expanded:   6744" in out  # deterministic, matches test_search


def test_no_stats_without_the_flag(capsys):
    _, out, _ = run(capsys, "solve", "724506831")
    assert "Nodes expanded" not in out


def test_show_boards_prints_every_state_on_the_path(capsys):
    _, out, _ = run(capsys, "solve", "123405786", "--show-boards")
    # UL from the goal made this state, so the solution is 2 moves: RD.
    assert moves_from(out) == "RD"
    assert "start   1 R     2 D" in out
    assert "1 2 3   1 2 3   1 2 3\n4 . 5   4 5 .   4 5 6\n7 8 6   7 8 6   7 8 ." in out


def test_accepts_the_parser_s_other_formats(capsys):
    code, out, _ = run(capsys, "solve", "1 2 3 4 5 6 7 0 8")
    assert code == 0 and "1 move (optimal)" in out


# --- unsolvable ---------------------------------------------------------------

def test_unsolvable_exits_1_with_the_inversion_count(capsys):
    code, out, _ = run(capsys, "solve", "213456780")
    assert code == 1
    assert "1 inversion (odd)" in out
    assert "No search was run" in out


def test_unsolvable_plural(capsys):
    code, out, _ = run(capsys, "solve", "321456780")
    assert code == 1 and "3 inversions (odd)" in out


# --- malformed input ----------------------------------------------------------

@pytest.mark.parametrize("text, message", [
    ("12345678", "expected 9 tiles, got 8"),
    ("1234567890", "expected 9 tiles, got 10"),
    ("113456780", "duplicate tile 1"),
    ("12345678x", "invalid tile 'x'"),
    ("12345678²", "invalid tile '²'"),
    ("123456789", "missing blank"),
])
def test_malformed_state_exits_2_with_a_specific_message(capsys, text, message):
    code, out, err = run(capsys, "solve", text)
    assert code == 2
    assert out == ""
    assert err.startswith("error: ") and message in err


@pytest.mark.parametrize("argv", [
    [],                                          # no command
    ["frobnicate"],                              # unknown command
    ["solve"],                                   # missing state
    ["solve", "724506831", "--heuristic", "x"],  # unknown heuristic
    ["random"],                                  # missing --depth
    ["random", "--depth", "five"],               # non-integer depth
])
def test_bad_arguments_exit_2(capsys, argv):
    code, _, err = run(capsys, *argv)
    assert code == 2
    assert "error:" in err


def test_help_exits_0(capsys):
    code, out, _ = run(capsys, "--help")
    assert code == 0 and "solve" in out and "compare" in out


# --- random -------------------------------------------------------------------

@pytest.mark.parametrize("depth", [0, 1, 12, 31])
def test_random_state_is_at_exactly_that_depth(capsys, depth):
    code, out, _ = run(capsys, "random", "--depth", str(depth), "--seed", "3")
    assert code == 0
    assert optimal_distance(parse_state(out.strip())) == depth


def test_random_is_reproducible_with_a_seed(capsys):
    _, first, _ = run(capsys, "random", "--depth", "20", "--seed", "7")
    _, second, _ = run(capsys, "random", "--depth", "20", "--seed", "7")
    assert first == second


def test_random_prints_only_the_state(capsys):
    # So that `solve $(python -m puzzle8 random --depth 20)` works.
    _, out, _ = run(capsys, "random", "--depth", "20", "--seed", "7")
    assert re.fullmatch(r"[0-8]{9}\n", out)


@pytest.mark.parametrize("depth", ["-1", "32"])
def test_random_rejects_impossible_depths(capsys, depth):
    code, _, err = run(capsys, "random", "--depth", depth)
    assert code == 2 and "between 0 and 31" in err


# --- compare ------------------------------------------------------------------

def test_compare_prints_the_table(capsys):
    code, out, _ = run(capsys, "compare", "--per-bucket", "2", "--seed", "1")
    assert code == 0
    for bucket, _, _ in BUCKETS:
        assert bucket in out
    assert "every path checked" in out
    assert "pass --seed" not in out  # a seed was given


def test_compare_without_seed_says_how_to_reproduce(capsys):
    _, out, _ = run(capsys, "compare", "--per-bucket", "1")
    assert "pass --seed" in out


def test_compare_writes_csv(capsys, tmp_path):
    target = tmp_path / "out.csv"
    code, out, _ = run(capsys, "compare", "--per-bucket", "2", "--seed", "1",
                       "--csv", str(target))
    assert code == 0
    lines = target.read_text().splitlines()
    rows = 2 * len(BUCKETS)  # 2 states in each bucket
    assert len(lines) == 1 + rows  # plus the header
    assert f"Wrote {rows} rows" in out


def test_compare_unwritable_csv_exits_2_before_running(capsys, tmp_path):
    code, out, err = run(capsys, "compare", "--csv", str(tmp_path / "no" / "such" / "dir.csv"))
    assert code == 2
    assert "cannot write" in err
    assert out == ""  # failed up front, no table


def test_compare_rejects_zero_per_bucket(capsys):
    code, _, err = run(capsys, "compare", "--per-bucket", "0")
    assert code == 2 and "at least 1" in err


# --- errors that are bugs, not input ----------------------------------------------

def test_internal_error_is_one_line_exit_3(capsys, monkeypatch):
    def broken(state, heuristic):
        raise RuntimeError("simulated bug")
    monkeypatch.setattr(cli, "astar", broken)
    code, out, err = run(capsys, "solve", "724506831")
    assert code == 3
    assert err.strip() == "internal error: RuntimeError: simulated bug"


def test_a_path_that_misses_the_goal_is_caught(capsys, monkeypatch):
    real = cli.astar

    def wrong(state, heuristic):
        r = real(state, heuristic=heuristic)
        return type(r)(r.path[:-1], r.nodes_expanded, r.nodes_generated,
                       r.max_frontier, r.seconds)
    monkeypatch.setattr(cli, "astar", wrong)
    code, out, err = run(capsys, "solve", "724506831")
    assert code == 3
    assert "does not reach the goal" in err
    assert out == ""  # nothing claimed as a solution


# --- python -m puzzle8, end to end ---------------------------------------------

@pytest.mark.parametrize("argv, expected_code", [
    (["solve", "867254301"], 0),
    (["solve", "213456780"], 1),
    (["solve", "12345678x"], 2),
])
def test_module_entry_point(argv, expected_code):
    proc = subprocess.run([sys.executable, "-m", "puzzle8", *argv],
                          cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == expected_code
    assert "Traceback" not in proc.stdout + proc.stderr
