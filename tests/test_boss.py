"""Unit tests for Boss AI Strategies (Level 2 Greedy Pusher)."""

import math
from src.core.models import State, Puck, ActionCommand
from src.core.interfaces import CodePolicyAgent
from src.core.primitives import set_current_state
from src.strategies.boss.level2 import policy_step as level2_policy_step


def test_level2_boss_returns_valid_action():
    state = State(
        my_pos=(500.0, 200.0),
        my_theta=math.pi,
        opp_pos=(100.0, 200.0),
        opp_theta=0.0,
        opp_vel=(0.0, 0.0),
        pucks=[
            Puck(id=0, x=400.0, y=200.0),
            Puck(id=1, x=300.0, y=100.0),
            Puck(id=2, x=200.0, y=300.0),
        ],
        match_time=1.0,
        my_team="blue"
    )

    set_current_state(state)
    action = level2_policy_step(state)
    assert isinstance(action, ActionCommand)
    assert action.command_type in ["push", "move_to", "stop"]
    assert len(action.waypoints) == 30


def test_level2_boss_in_code_policy_agent():
    agent = CodePolicyAgent(level2_policy_step)
    state = State(
        my_pos=(450.0, 150.0),
        my_theta=-math.pi / 2,
        opp_pos=(150.0, 150.0),
        opp_theta=0.0,
        opp_vel=(0.0, 0.0),
        pucks=[
            Puck(id=0, x=300.0, y=200.0),
            Puck(id=1, x=300.0, y=100.0),
            Puck(id=2, x=300.0, y=300.0),
        ],
        match_time=5.0,
        my_team="blue"
    )

    action = agent.get_action(state)
    assert isinstance(action, ActionCommand)
    assert len(action.waypoints) == 30
