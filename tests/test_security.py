"""Unit tests for AST Security Sandbox and Watchdog Timeout.

Strictly verifies quantitative goals from proposal Section 2.2:
- 100% blocking rate for unauthorized APIs across 30 test cases
- Watchdog timeout stops infinite loops
"""

import time
import pytest
from src.core.models import State, Puck
from src.core.primitives import stop
from src.core.security import validate_policy_ast, execute_policy_with_watchdog


# 30 Unauthorized / Malicious Test Cases
MALICIOUS_SNIPPETS = [
    # 1-5: Import variations
    "import os\ndef policy_step(state):\n    return stop()",
    "import sys\ndef policy_step(state):\n    return stop()",
    "from subprocess import Popen\ndef policy_step(state):\n    return stop()",
    "from math import sqrt\ndef policy_step(state):\n    return stop()",
    "import time\ndef policy_step(state):\n    return stop()",

    # 6-10: File I/O and Built-in Execution
    "def policy_step(state):\n    open('/tmp/test', 'w')\n    return stop()",
    "def policy_step(state):\n    eval('1 + 1')\n    return stop()",
    "def policy_step(state):\n    exec('x = 1')\n    return stop()",
    "def policy_step(state):\n    compile('x=1', '', 'exec')\n    return stop()",
    "def policy_step(state):\n    globals()['secret'] = 1\n    return stop()",

    # 11-15: Reflection and Dunders
    "def policy_step(state):\n    getattr(state, '__class__')\n    return stop()",
    "def policy_step(state):\n    state.__class__.__bases__[0]\n    return stop()",
    "def policy_step(state):\n    x = state.__dict__\n    return stop()",
    "def policy_step(state):\n    setattr(state, 'my_pos', (0,0))\n    return stop()",
    "def policy_step(state):\n    delattr(state, 'my_pos')\n    return stop()",

    # 16-20: Forbidden Loop Constructs
    "def policy_step(state):\n    while True:\n        pass\n    return stop()",
    "def policy_step(state):\n    while state.match_time < 10:\n        pass\n    return stop()",
    "def policy_step(state):\n    for i in range(100):\n        pass\n    return stop()",
    "def policy_step(state):\n    for p in state.pucks:\n        pass\n    return stop()",
    "def policy_step(state):\n    while 1:\n        return stop()",

    # 21-25: Unauthorized Function Calls
    "def policy_step(state):\n    print('hello')\n    return stop()",
    "def policy_step(state):\n    input('prompt')\n    return stop()",
    "def policy_step(state):\n    exit(0)\n    return stop()",
    "def policy_step(state):\n    quit()\n    return stop()",
    "def policy_step(state):\n    help()\n    return stop()",

    # 26-30: Structural/Syntax violations
    "x = 1",  # Missing policy_step
    "def foo(state):\n    return stop()",  # Wrong function name
    "def policy_step():\n    return stop()",  # Syntax valid, handled
    "class Exploit:\n    pass\ndef policy_step(state):\n    return stop()",
    "def policy_step(state):\n    with open('file') as f:\n        pass\n    return stop()"
]


def test_ast_security_blocks_all_30_cases():
    """Verify 100% blocking rate across 30 unauthorized code cases."""
    blocked_count = 0
    for idx, snippet in enumerate(MALICIOUS_SNIPPETS):
        is_valid, err = validate_policy_ast(snippet)
        if not is_valid:
            blocked_count += 1
        else:
            print(f"Failed to block case #{idx + 1}: {snippet}")

    blocking_rate = (blocked_count / len(MALICIOUS_SNIPPETS)) * 100.0
    assert blocking_rate == 100.0, f"Expected 100% blocking rate, got {blocking_rate}% ({blocked_count}/{len(MALICIOUS_SNIPPETS)})"


def test_ast_security_allows_valid_policy():
    valid_code = """
def policy_step(state):
    puck = get_closest_puck(state.pucks, state.my_pos)
    if puck is not None:
        return push(puck, (450.0, 200.0))
    return stop()
"""
    is_valid, err = validate_policy_ast(valid_code)
    assert is_valid is True, f"Valid code was unexpectedly rejected: {err}"


def test_ast_security_allows_local_helper_function():
    code_with_helper = """
def policy_step(state):
    def clamp(v, lo, hi):
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v
    target_x = clamp(state.my_pos[0] + 50.0, 50.0, 550.0)
    return move_to((target_x, 200.0))
"""
    is_valid, err = validate_policy_ast(code_with_helper)
    assert is_valid is True, f"Local helper function was unexpectedly rejected: {err}"


def test_watchdog_timeout_on_infinite_loop():
    """Verify watchdog timeout halts execution within 100ms."""
    def infinite_loop_policy(state):
        while True:
            time.sleep(0.01)
        return stop()

    dummy_state = State(
        my_pos=(100.0, 200.0),
        my_theta=0.0,
        opp_pos=(500.0, 200.0),
        opp_theta=0.0,
        opp_vel=(0.0, 0.0),
        pucks=[],
        match_time=0.0
    )

    start_t = time.time()
    action = execute_policy_with_watchdog(infinite_loop_policy, dummy_state, timeout=0.100)
    elapsed = time.time() - start_t

    # Watchdog should cut off around 100ms and return stop()
    assert elapsed < 0.250
    assert action.command_type == "stop"
