"""Unit tests for standardized LLM Planner and Client Adapters."""

import math
from unittest.mock import MagicMock
from src.core.models import State, Puck, ActionCommand
from src.core.llm_clients import (
    BaseLLMClient, MockLLMClient, PostechSchoolLLMClient,
    create_llm_client
)
from src.core.llm_planner import LLMPlanner


def test_mock_client_generation():
    client = MockLLMClient()
    resp = client.generate("사이드로 우회해서 돌아가")
    assert "def policy_step" in resp
    assert "move_to" in resp


def test_llm_planner_with_mock():
    planner = LLMPlanner(client=MockLLMClient())
    agent, latency, err = planner.create_agent_from_prompt("가까운 공으로 가서 상대 쪽으로 밀어줘")

    assert err is None
    assert latency >= 0.0
    assert agent is not None

    # Test executing generated agent
    state = State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(500.0, 200.0),
        opp_theta=math.pi,
        opp_vel=(0.0, 0.0),
        pucks=[Puck(id=0, x=200.0, y=200.0)],
        match_time=0.0,
        my_team="red"
    )
    action = agent.get_action(state)
    assert isinstance(action, ActionCommand)
    assert len(action.waypoints) == 30


def test_llm_planner_ast_rejection_fail_safe():
    # Mock an insecure LLM response
    bad_client = MagicMock(spec=BaseLLMClient)
    bad_client.generate.return_value = """```python
import os
def policy_step(state: State) -> ActionCommand:
    os.system('malicious')
    return stop()
```"""

    planner = LLMPlanner(client=bad_client)
    agent, latency, err = planner.create_agent_from_prompt("악성 코드 주입 시도")

    assert err is not None
    assert "AST Security Check Failed" in err

    # Agent should fail-safe to stop
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
    action = agent.get_action(state)
    assert action.command_type == "stop"


def test_create_llm_client_factory():
    mock_c = create_llm_client("mock")
    assert isinstance(mock_c, MockLLMClient)

    postech_c = create_llm_client("postech", api_key="dummy_key", model_type="gemini")
    assert isinstance(postech_c, PostechSchoolLLMClient)
    assert postech_c.model_type == "gemini"
