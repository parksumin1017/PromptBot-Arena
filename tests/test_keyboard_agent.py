from collections import defaultdict
import math
from unittest.mock import patch
import pygame
from src.core.models import State, Puck, ActionCommand
from src.strategies.keyboard_agent import KeyboardAgent


def test_keyboard_agent_idle():
    agent = KeyboardAgent(linear_speed=120.0, angular_speed=2.5)
    state = State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(500.0, 200.0),
        opp_theta=math.pi,
        opp_vel=(0.0, 0.0),
        pucks=[],
        match_time=0.0,
        my_team="red"
    )

    fake_keys = defaultdict(bool)
    with patch("pygame.key.get_pressed", return_value=fake_keys):
        action = agent.get_action(state)

    assert isinstance(action, ActionCommand)
    assert len(action.waypoints) == 30
    assert all(wp.v == 0.0 and wp.omega == 0.0 for wp in action.waypoints)


def test_keyboard_agent_forward():
    agent = KeyboardAgent(linear_speed=120.0, angular_speed=2.5)
    state = State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(500.0, 200.0),
        opp_theta=math.pi,
        opp_vel=(0.0, 0.0),
        pucks=[],
        match_time=0.0,
        my_team="red"
    )

    fake_keys = defaultdict(bool)
    fake_keys[pygame.K_w] = True

    with patch("pygame.key.get_pressed", return_value=fake_keys):
        action = agent.get_action(state)

    assert isinstance(action, ActionCommand)
    assert len(action.waypoints) == 30
    assert all(wp.v == 120.0 and wp.omega == 0.0 for wp in action.waypoints)


def test_keyboard_agent_turn():
    agent = KeyboardAgent(linear_speed=120.0, angular_speed=2.5)
    state = State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(500.0, 200.0),
        opp_theta=math.pi,
        opp_vel=(0.0, 0.0),
        pucks=[],
        match_time=0.0,
        my_team="blue"
    )

    fake_keys = defaultdict(bool)
    fake_keys[pygame.K_LEFT] = True

    with patch("pygame.key.get_pressed", return_value=fake_keys):
        action = agent.get_action(state)

    assert isinstance(action, ActionCommand)
    assert len(action.waypoints) == 30
    assert all(wp.v == 0.0 and wp.omega == -2.5 for wp in action.waypoints)
