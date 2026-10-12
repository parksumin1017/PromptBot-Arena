"""Unit tests for CorePusherReferee (Match Rules and Outcome Determination).

Verifies 100% rule determination accuracy for proposal milestone.
"""

import pytest
from src.core.models import Puck
from src.simulation.referee import CorePusherReferee, MatchStatus, MatchWinner


def test_evaluate_zones():
    referee = CorePusherReferee()
    pucks = [
        Puck(id=0, x=100.0, y=200.0),  # Red zone
        Puck(id=1, x=299.9, y=200.0),  # Red zone
        Puck(id=2, x=300.0, y=200.0),  # Blue zone
    ]
    red_count, blue_count = referee.evaluate_zones(pucks)
    assert red_count == 2
    assert blue_count == 1


def test_calculate_score():
    referee = CorePusherReferee()
    pucks = [
        Puck(id=0, x=450.0, y=100.0),  # In Blue zone -> Red point
        Puck(id=1, x=500.0, y=200.0),  # In Blue zone -> Red point
        Puck(id=2, x=150.0, y=300.0),  # In Red zone  -> Blue point
    ]
    score = referee.calculate_score(pucks)
    assert score.red_score == 2
    assert score.blue_score == 1
    assert score.pucks_in_red == 1
    assert score.pucks_in_blue == 2


def test_match_not_started():
    referee = CorePusherReferee()
    pucks = [Puck(id=0, x=300.0, y=200.0)]
    res = referee.update(match_time=0.0, pucks=pucks)
    assert res.status == MatchStatus.NOT_STARTED
    assert res.winner == MatchWinner.NONE
    assert res.time_remaining == 60.0


def test_match_in_progress():
    referee = CorePusherReferee()
    pucks = [
        Puck(id=0, x=450.0, y=100.0),
        Puck(id=1, x=500.0, y=200.0),
        Puck(id=2, x=150.0, y=300.0),
    ]
    res = referee.update(match_time=30.0, pucks=pucks)
    assert res.status == MatchStatus.IN_PROGRESS
    assert res.winner == MatchWinner.NONE
    assert res.time_remaining == 30.0
    assert res.score.red_score == 2
    assert res.score.blue_score == 1


def test_match_finished_red_wins():
    referee = CorePusherReferee(max_match_time=60.0)
    # Red pushed 2 pucks into Blue zone
    pucks = [
        Puck(id=0, x=400.0, y=100.0),
        Puck(id=1, x=500.0, y=200.0),
        Puck(id=2, x=100.0, y=200.0),
    ]
    res = referee.update(match_time=60.0, pucks=pucks)
    assert res.status == MatchStatus.FINISHED
    assert res.winner == MatchWinner.RED
    assert res.time_remaining == 0.0
    assert "RED WINS" in res.message


def test_match_finished_blue_wins():
    referee = CorePusherReferee(max_match_time=60.0)
    # Blue pushed 2 pucks into Red zone
    pucks = [
        Puck(id=0, x=100.0, y=100.0),
        Puck(id=1, x=200.0, y=200.0),
        Puck(id=2, x=500.0, y=200.0),
    ]
    res = referee.update(match_time=60.1, pucks=pucks)
    assert res.status == MatchStatus.FINISHED
    assert res.winner == MatchWinner.BLUE
    assert "BLUE WINS" in res.message


def test_match_finished_draw():
    referee = CorePusherReferee(max_match_time=60.0)
    # Equal pucks in both zones
    pucks = [
        Puck(id=0, x=100.0, y=100.0),  # in Red
        Puck(id=1, x=500.0, y=200.0),  # in Blue
    ]
    res = referee.update(match_time=60.0, pucks=pucks)
    assert res.status == MatchStatus.FINISHED
    assert res.winner == MatchWinner.DRAW
    assert "DRAW" in res.message
