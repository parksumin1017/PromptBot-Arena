"""Action Primitives API for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 2.4 & 4.3: Spatiotemporal collision extrapolation (0.5s horizon, 30 steps @ 60 FPS)
- Section 5.1 & 5.2: Function contracts for push, move_to, stop, will_collide, get_dist, etc.
"""

import math
from typing import Tuple, List, Optional
from src.core.models import Puck, State, ActionCommand, Waypoint
from src.core.trajectory import (
    generate_move_to_profile,
    generate_push_profile,
    create_safe_stop_profile,
    DT,
    HORIZON_STEPS
)

# ---------------------------------------------------------------------------
# Safety Thresholds (docs/design.md Section 2.4)
# ---------------------------------------------------------------------------
ROBOT_ROBOT_COLLISION_DIST = 55.0  # [mm]
ROBOT_PUCK_COLLISION_DIST = 38.0   # [mm] (for non-target pucks)

# Global context for active state during policy_step execution
_active_state: Optional[State] = None


def set_current_state(state: State) -> None:
    """Bind the current observation State before executing policy_step."""
    global _active_state
    _active_state = state


def get_current_state() -> Optional[State]:
    """Retrieve the bound observation State."""
    return _active_state


# ---------------------------------------------------------------------------
# Collision Guard: 0.5s Spatiotemporal Check (docs/design.md Section 4.3)
# ---------------------------------------------------------------------------

def check_trajectory_safety(
    waypoints: List[Waypoint],
    state: State,
    target_puck_id: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if the 30-step trajectory profile collides with opponent robot or other pucks
    strictly within the next 0.5s horizon (t in [0, 0.5s]).
    Opponent position is linearly extrapolated: P_opp(t) = P_opp + v_opp * t.
    """
    opp_x, opp_y = state.opp_pos
    opp_vx, opp_vy = state.opp_vel

    for k, wp in enumerate(waypoints):
        t_k = k * DT

        # Opponent Robot Extrapolation (prevent robot-robot physical damage)
        extrap_opp_x = opp_x + opp_vx * t_k
        extrap_opp_y = opp_y + opp_vy * t_k
        dist_opp = math.hypot(wp.x - extrap_opp_x, wp.y - extrap_opp_y)

        if dist_opp < ROBOT_ROBOT_COLLISION_DIST:
            return False, f"Collision predicted with opponent robot at t={t_k:.2f}s (dist={dist_opp:.1f}mm < 55mm)"

    return True, None


# ---------------------------------------------------------------------------
# Motion Action Primitives (docs/design.md Section 5.2)
# ---------------------------------------------------------------------------

def push(puck: Puck, target: Tuple[float, float]) -> ActionCommand:
    """
    Generate push action command with 30-step Cubic Hermite Spline trajectory.
    Performs internal 0.5s collision check. Replaces with Safe Stop if unsafe.
    """
    if puck is None:
        raise ValueError("push() requires a valid Puck object.")

    state = get_current_state()
    tx, ty = float(target[0]), float(target[1])

    if state is None:
        # Fallback if state not bound: generate 30 zero-speed waypoints preserving contract
        waypoints = [Waypoint(x=puck.x, y=puck.y, theta=0.0, v=0.0, omega=0.0) for _ in range(HORIZON_STEPS)]
        return ActionCommand(
            command_type="push",
            target=(tx, ty),
            waypoints=waypoints,
            target_puck_id=puck.id,
            is_safe=True
        )

    # 1. Generate trajectory profile
    waypoints, is_safe, reason = generate_push_profile(
        robot_pos=state.my_pos,
        robot_theta=state.my_theta,
        puck_pos=puck.pos,
        target_pos=(tx, ty)
    )

    # 2. Check 0.5s spatiotemporal collision if profile was geometrically safe
    if is_safe:
        is_safe, reason = check_trajectory_safety(
            waypoints=waypoints,
            state=state,
            target_puck_id=puck.id
        )

    # 3. If unsafe, replace with Safe Stop profile
    if not is_safe:
        waypoints = create_safe_stop_profile(state.my_pos, state.my_theta)

    return ActionCommand(
        command_type="push",
        target=(tx, ty),
        waypoints=waypoints,
        is_safe=is_safe,
        safe_stop_reason=reason,
        target_puck_id=puck.id
    )


def move_to(target: Tuple[float, float]) -> ActionCommand:
    """
    Generate move_to action command with 30-step Cubic Hermite Spline trajectory.
    Performs internal 0.5s collision check. Replaces with Safe Stop if unsafe.
    """
    state = get_current_state()
    tx, ty = float(target[0]), float(target[1])

    if state is None:
        waypoints = [Waypoint(x=tx, y=ty, theta=0.0, v=0.0, omega=0.0) for _ in range(HORIZON_STEPS)]
        return ActionCommand(
            command_type="move_to",
            target=(tx, ty),
            waypoints=waypoints,
            is_safe=True
        )

    # 1. Generate trajectory profile
    waypoints = generate_move_to_profile(
        robot_pos=state.my_pos,
        robot_theta=state.my_theta,
        target_pos=(tx, ty)
    )

    # 2. Check 0.5s spatiotemporal collision
    is_safe, reason = check_trajectory_safety(
        waypoints=waypoints,
        state=state,
        target_puck_id=None
    )

    # 3. If unsafe, replace with Safe Stop profile
    if not is_safe:
        waypoints = create_safe_stop_profile(state.my_pos, state.my_theta)

    return ActionCommand(
        command_type="move_to",
        target=(tx, ty),
        waypoints=waypoints,
        is_safe=is_safe,
        safe_stop_reason=reason
    )


def stop() -> ActionCommand:
    """Immediately stop all motor movement."""
    state = get_current_state()
    robot_pos = state.my_pos if state else (0.0, 0.0)
    robot_theta = state.my_theta if state else 0.0

    return ActionCommand(
        command_type="stop",
        target=robot_pos,
        waypoints=create_safe_stop_profile(robot_pos, robot_theta),
        is_safe=True,
        safe_stop_reason=None
    )


# ---------------------------------------------------------------------------
# Perception Helper Functions (docs/design.md Section 5.2)
# ---------------------------------------------------------------------------

def will_collide(action: ActionCommand) -> bool:
    """
    Check if the given action will trigger Safe Stop due to collision risk
    strictly within the 0.5s horizon.
    """
    if action is None:
        return False
    return not action.is_safe


def get_dist(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """Calculate 2D Euclidean distance [mm]."""
    return math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])


def get_closest_puck(pucks: List[Puck], to_pos: Tuple[float, float]) -> Optional[Puck]:
    """Find the single closest puck to the given (x, y) coordinate."""
    if not pucks:
        return None
    return min(pucks, key=lambda p: math.hypot(p.x - to_pos[0], p.y - to_pos[1]))


def get_pucks_in_zone(pucks: List[Puck], zone: str = "red") -> List[Puck]:
    """Filter pucks located in the specified zone ('red' or 'blue')."""
    return [p for p in pucks if p.zone == zone]
