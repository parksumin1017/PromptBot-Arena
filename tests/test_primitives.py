"""Unit tests for Action Primitives API.

Verifies:
- push, move_to, stop return valid ActionCommand with 30-step Waypoint profile
- will_collide correctly identifies spatiotemporal collision risks within 0.5s
- get_dist, get_closest_puck, get_pucks_in_zone contracts
"""

import pytest
from src.core.models import Puck, State, ActionCommand
from src.core.primitives import (
    push, move_to, stop, will_collide,
    get_dist, get_closest_puck, get_pucks_in_zone,
    set_current_state
)


@pytest.fixture
def sample_state():
    pucks = [
        Puck(id=0, x=300.0, y=100.0),
        Puck(id=1, x=200.0, y=200.0),
        Puck(id=2, x=450.0, y=300.0)
    ]
    return State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(500.0, 200.0),
        opp_theta=3.1415,
        opp_vel=(-50.0, 0.0),
        pucks=pucks,
        match_time=1.0,
        my_team="red"
    )


def test_get_dist():
    assert get_dist((0.0, 0.0), (30.0, 40.0)) == pytest.approx(50.0)


def test_get_closest_puck(sample_state):
    closest = get_closest_puck(sample_state.pucks, (110.0, 200.0))
    assert closest is not None
    assert closest.id == 1  # Puck 1 is at (200, 200)


def test_get_pucks_in_zone(sample_state):
    red_pucks = get_pucks_in_zone(sample_state.pucks, "red")
    blue_pucks = get_pucks_in_zone(sample_state.pucks, "blue")
    assert len(red_pucks) == 1
    assert red_pucks[0].id == 1
    assert len(blue_pucks) == 2


def test_stop_primitive(sample_state):
    set_current_state(sample_state)
    action = stop()
    assert isinstance(action, ActionCommand)
    assert action.command_type == "stop"
    assert len(action.waypoints) == 30
    for wp in action.waypoints:
        assert wp.v == 0.0
        assert wp.omega == 0.0


def test_move_to_safe(sample_state):
    set_current_state(sample_state)
    action = move_to((150.0, 100.0))
    assert isinstance(action, ActionCommand)
    assert action.command_type == "move_to"
    assert len(action.waypoints) == 30
    assert action.is_safe is True
    assert will_collide(action) is False


def test_push_safe(sample_state):
    set_current_state(sample_state)
    target_puck = sample_state.pucks[1]  # at (200, 200)
    action = push(target_puck, (450.0, 200.0))
    assert isinstance(action, ActionCommand)
    assert action.command_type == "push"
    assert len(action.waypoints) == 30
    assert action.target_puck_id == 1
    assert action.is_safe is True


def test_will_collide_with_opponent():
    # Opponent rushing directly towards our trajectory path
    pucks = [Puck(id=0, x=300.0, y=100.0)]
    danger_state = State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(160.0, 200.0),      # Only 60mm away
        opp_theta=3.1415,
        opp_vel=(-100.0, 0.0),        # Moving directly into us
        pucks=pucks,
        match_time=1.0,
        my_team="red"
    )
    set_current_state(danger_state)
    action = move_to((200.0, 200.0))

    assert action.is_safe is False
    assert will_collide(action) is True
    assert action.waypoints[0].v == 0.0  # Converted to Safe Stop
