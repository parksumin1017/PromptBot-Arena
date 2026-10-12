"""Core Data Models for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 1.2: Immutable read-only State and Puck (frozen dataclasses)
- Section 5.1: Waypoint, ActionCommand, Puck, State data structures
"""

from dataclasses import dataclass, field
import math
from typing import Tuple, List, Optional


def normalize_angle(theta: float) -> float:
    """Normalize angle to [-pi, pi] range."""
    while theta > math.pi:
        theta -= 2.0 * math.pi
    while theta < -math.pi:
        theta += 2.0 * math.pi
    return theta


@dataclass(frozen=True)
class Waypoint:
    """Discrete waypoint in the 0.5s horizon trajectory profile."""
    x: float          # [mm]
    y: float          # [mm]
    theta: float      # [rad]
    v: float          # [mm/s]
    omega: float      # [rad/s]


@dataclass
class ActionCommand:
    """High-level action command encapsulating a 0.5s (30-step) trajectory profile."""
    command_type: str                         # 'push', 'move_to', 'stop'
    target: Tuple[float, float]               # (x, y) [mm]
    waypoints: List[Waypoint] = field(default_factory=list)  # 30-step profile
    is_safe: bool = True                      # False if collision detected within 0.5s
    safe_stop_reason: Optional[str] = None
    target_puck_id: Optional[int] = None

    def __repr__(self) -> str:
        if self.command_type == "push":
            return f"ActionCommand(push, puck_id={self.target_puck_id}, target={self.target}, safe={self.is_safe})"
        elif self.command_type == "move_to":
            return f"ActionCommand(move_to, target={self.target}, safe={self.is_safe})"
        return f"ActionCommand(stop, safe={self.is_safe})"


@dataclass(frozen=True)
class Puck:
    """Field puck entity (Diameter 20 mm, Radius 10 mm)."""
    id: int
    x: float
    y: float

    @property
    def pos(self) -> Tuple[float, float]:
        """(x, y) position tuple [mm]."""
        return (self.x, self.y)

    @property
    def zone(self) -> str:
        """Current arena zone ('red': x < 300, 'blue': x >= 300)."""
        return "red" if self.x < 300.0 else "blue"


@dataclass(frozen=True)
class State:
    """Real-time sensor observation snapshot passed to policy_step every 0.5s."""
    my_pos: Tuple[float, float]        # (x, y) [mm]
    my_theta: float                    # [rad] (0 rad: toward positive x / blue zone)
    opp_pos: Tuple[float, float]       # (x, y) [mm]
    opp_theta: float                   # [rad]
    opp_vel: Tuple[float, float]       # (vx, vy) [mm/s]
    pucks: List[Puck]                  # 3 puck objects
    match_time: float                  # [s] (0.0 ~ 60.0)
    my_team: str = "red"               # 'red' or 'blue'

    def get_puck_by_id(self, puck_id: int) -> Optional[Puck]:
        """Helper to find puck by ID."""
        for p in self.pucks:
            if p.id == puck_id:
                return p
        return None
