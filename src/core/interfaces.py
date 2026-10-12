"""Abstract Interfaces and Base Implementations for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 1.2: BaseRobot (pure actuator), BaseVision (pure observer), BaseAgent (policy brain)
- Section 8.1: Software-Hardware Decoupling interfaces
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Callable, Dict, Any
from src.core.models import ActionCommand, State, Puck
from src.core.primitives import (
    push, move_to, stop, will_collide,
    get_dist, get_closest_puck, get_pucks_in_zone,
    set_current_state
)
from src.core.security import validate_policy_ast, execute_policy_with_watchdog


class BaseRobot(ABC):
    """
    Pure motor actuator interface.
    The robot does NOT track its own position or integrate kinematics.
    It purely receives velocity commands from the host PC.
    """

    @abstractmethod
    def send_velocity(self, v: float, omega: float) -> None:
        """Apply linear velocity v [mm/s] and angular velocity omega [rad/s]."""
        pass

    @abstractmethod
    def emergency_stop(self) -> None:
        """Immediately stop all motor hardware."""
        pass


class BaseVision(ABC):
    """
    Pure arena observer interface.
    Captures top-down arena view and produces read-only State snapshots.
    """

    @abstractmethod
    def get_state(self) -> State:
        """Return the latest read-only State snapshot of the arena."""
        pass

    @abstractmethod
    def capture_state(self, match_time: float, my_team: str = "red") -> State:
        """Capture and return State snapshot at the given match time."""
        pass


class BaseAgent(ABC):
    """
    Tactical decision maker interface (evaluates policy every 0.5s).
    """

    @abstractmethod
    def get_action(self, state: State) -> ActionCommand:
        """Given current State observation, return ActionCommand for the next 0.5s."""
        pass

    def reset(self) -> None:
        """Reset internal agent state if needed at match start."""
        pass


class CodePolicyAgent(BaseAgent):
    """
    Executes a Python policy script adhering to:
    def policy_step(state: State) -> ActionCommand: ...
    Supports both human-written scripts and LLM-generated code strings.
    Validates AST security and enforces Watchdog timeout.
    """

    def __init__(
        self,
        policy_func: Optional[Callable[[State], ActionCommand]] = None,
        code_str: Optional[str] = None,
        agent_name: str = "CodePolicyAgent"
    ):
        self.agent_name = agent_name
        self.policy_func = policy_func
        self.code_str = code_str

        if code_str:
            self.load_code(code_str)

    def load_code(self, code_str: str) -> None:
        """Validate AST and load policy_step from code string."""
        self.code_str = code_str
        is_valid, error = validate_policy_ast(code_str)
        if not is_valid:
            raise ValueError(f"Security validation failed: {error}")

        safe_globals: Dict[str, Any] = {
            "__builtins__": {
                "min": min, "max": max, "abs": abs, "round": round,
                "len": len, "float": float, "int": int, "bool": bool,
                "range": range
            },
            "push": push,
            "move_to": move_to,
            "stop": stop,
            "will_collide": will_collide,
            "get_dist": get_dist,
            "get_closest_puck": get_closest_puck,
            "get_pucks_in_zone": get_pucks_in_zone,
            "State": State,
            "Puck": Puck,
            "ActionCommand": ActionCommand
        }
        local_scope: Dict[str, Any] = {}
        exec(code_str, safe_globals, local_scope)

        if "policy_step" not in local_scope:
            raise ValueError("The provided code must define 'def policy_step(state):'")

        self.policy_func = local_scope["policy_step"]

    def set_function(self, func: Callable[[State], ActionCommand]) -> None:
        """Set a Python policy callable directly."""
        self.policy_func = func

    def get_action(self, state: State) -> ActionCommand:
        """Run policy_step with bound state context and watchdog timeout."""
        if self.policy_func is None:
            return stop()

        # Bind state context for push() and move_to()
        set_current_state(state)

        # Run with 100ms watchdog
        return execute_policy_with_watchdog(self.policy_func, state)
