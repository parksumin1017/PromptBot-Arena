"""Trajectory Generation using Cubic Hermite Spline for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 2.2: Physical Limits (v_max = 150.0 mm/s, omega_max = pi rad/s, a_max = 300.0 mm/s^2, alpha_max = 2*pi rad/s^2)
- Section 3: Cubic Hermite Spline formulation and 30-step (0.5s @ 60 FPS) profiling
- Section 4.1: Case A (Obtuse/perpendicular angle via-point P_via bypass)
- Section 4.2: Case B (Wall-stuck puck scraping projection)
"""

import math
from typing import Tuple, List, Optional
from src.core.models import Waypoint, normalize_angle


# ---------------------------------------------------------------------------
# Physical and Geometric Constants (docs/design.md Section 2)
# ---------------------------------------------------------------------------
V_MAX = 150.0              # [mm/s]
OMEGA_MAX = math.pi        # [rad/s] (~3.1416 rad/s)
A_MAX = 300.0              # [mm/s^2]
ALPHA_MAX = 2.0 * math.pi  # [rad/s^2] (~6.2832 rad/s^2)
HORIZON_STEPS = 30         # 30 steps per 0.5s horizon @ 60 FPS
DT = 1.0 / 60.0            # 16.666... ms
HORIZON_TIME = 0.5         # [s]

ARENA_WIDTH = 600.0        # [mm]
ARENA_HEIGHT = 400.0       # [mm]
ROBOT_SAFE_WALL_MARGIN = 27.0  # [mm]
PUCK_WALL_MARGIN = 35.0        # [mm] (25mm robot half + 10mm puck radius)

CONTACT_OFFSET = 25.0      # [mm] (15mm bumper notch + 10mm puck radius)
BYPASS_LATERAL_OFFSET = 45.0  # [mm] (25mm robot + 10mm puck + 10mm buffer)
BYPASS_LONG_OFFSET = 15.0     # [mm]


# ---------------------------------------------------------------------------
# 3.1 Cubic Hermite Spline Formulation
# ---------------------------------------------------------------------------

def hermite_point(
    p0: Tuple[float, float],
    m0: Tuple[float, float],
    p1: Tuple[float, float],
    m1: Tuple[float, float],
    s: float
) -> Tuple[float, float]:
    """Calculate 2D position P(s) on Cubic Hermite Spline for parameter s in [0, 1]."""
    s2 = s * s
    s3 = s2 * s
    h00 = 2.0 * s3 - 3.0 * s2 + 1.0
    h10 = s3 - 2.0 * s2 + s
    h01 = -2.0 * s3 + 3.0 * s2
    h11 = s3 - s2

    x = h00 * p0[0] + h10 * m0[0] + h01 * p1[0] + h11 * m1[0]
    y = h00 * p0[1] + h10 * m0[1] + h01 * p1[1] + h11 * m1[1]
    return (x, y)


def hermite_tangent(
    p0: Tuple[float, float],
    m0: Tuple[float, float],
    p1: Tuple[float, float],
    m1: Tuple[float, float],
    s: float
) -> Tuple[float, float]:
    """Calculate tangent vector P'(s) = dP/ds on Cubic Hermite Spline."""
    s2 = s * s
    dh00 = 6.0 * s2 - 6.0 * s
    dh10 = 3.0 * s2 - 4.0 * s + 1.0
    dh01 = -6.0 * s2 + 6.0 * s
    dh11 = 3.0 * s2 - 2.0 * s

    dx = dh00 * p0[0] + dh10 * m0[0] + dh01 * p1[0] + dh11 * m1[0]
    dy = dh00 * p0[1] + dh10 * m0[1] + dh01 * p1[1] + dh11 * m1[1]
    return (dx, dy)


def compute_spline_length(
    p0: Tuple[float, float],
    m0: Tuple[float, float],
    p1: Tuple[float, float],
    m1: Tuple[float, float],
    num_samples: int = 50
) -> float:
    """Numerically approximate the arc length of the Hermite spline."""
    total_len = 0.0
    prev_pt = p0
    for i in range(1, num_samples + 1):
        s = i / float(num_samples)
        curr_pt = hermite_point(p0, m0, p1, m1, s)
        total_len += math.hypot(curr_pt[0] - prev_pt[0], curr_pt[1] - prev_pt[1])
        prev_pt = curr_pt
    return total_len


# ---------------------------------------------------------------------------
# 3.3 Trajectory Profiling (30 Waypoints @ 60 FPS)
# ---------------------------------------------------------------------------

def sample_spline_profile(
    p0: Tuple[float, float],
    theta0: float,
    p1: Tuple[float, float],
    theta1: float,
    current_v: float = 0.0,
    current_omega: float = 0.0,
    steps: int = HORIZON_STEPS,
    dt: float = DT
) -> List[Waypoint]:
    """
    Generate 30 discrete Waypoint steps for the 0.5s horizon from Cubic Hermite Spline.
    Enforces V_MAX, OMEGA_MAX, A_MAX, and ALPHA_MAX limits.
    """
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    scale = max(dist, 10.0)

    m0 = (scale * math.cos(theta0), scale * math.sin(theta0))
    m1 = (scale * math.cos(theta1), scale * math.sin(theta1))

    total_arc_len = compute_spline_length(p0, m0, p1, m1)
    if total_arc_len < 1e-4:
        # Already at target
        return [Waypoint(x=p0[0], y=p0[1], theta=theta0, v=0.0, omega=0.0) for _ in range(steps)]

    waypoints: List[Waypoint] = []
    sim_v = current_v
    sim_omega = current_omega
    curr_s = 0.0
    prev_theta = theta0

    for step in range(1, steps + 1):
        if curr_s >= 1.0:
            # Reached end of spline
            waypoints.append(Waypoint(x=p1[0], y=p1[1], theta=theta1, v=0.0, omega=0.0))
            continue

        # Target linear speed
        target_v = V_MAX
        # Deceleration ramp if approaching end of spline
        remaining_dist = (1.0 - curr_s) * total_arc_len
        stopping_dist = (sim_v * sim_v) / (2.0 * A_MAX + 1e-6)
        if remaining_dist < stopping_dist + 5.0:
            target_v = max(0.0, math.sqrt(max(0.0, 2.0 * A_MAX * remaining_dist)))

        # Enforce linear acceleration limit
        dv = target_v - sim_v
        max_dv = A_MAX * dt
        dv = max(-max_dv, min(max_dv, dv))
        sim_v = max(0.0, min(V_MAX, sim_v + dv))

        # Advance parameter s along arc
        ds = (sim_v * dt) / total_arc_len if total_arc_len > 1e-4 else 1.0
        curr_s = min(1.0, curr_s + ds)

        # Compute point and tangent angle
        pos = hermite_point(p0, m0, p1, m1, curr_s)
        tangent = hermite_tangent(p0, m0, p1, m1, curr_s)
        if math.hypot(tangent[0], tangent[1]) > 1e-4:
            target_theta = math.atan2(tangent[1], tangent[0])
        else:
            target_theta = theta1

        # Angular velocity to track tangent
        d_theta = normalize_angle(target_theta - prev_theta)
        target_omega = d_theta / dt
        target_omega = max(-OMEGA_MAX, min(OMEGA_MAX, target_omega))

        # Enforce angular acceleration limit
        d_omega = target_omega - sim_omega
        max_d_omega = ALPHA_MAX * dt
        d_omega = max(-max_d_omega, min(max_d_omega, d_omega))
        sim_omega = max(-OMEGA_MAX, min(OMEGA_MAX, sim_omega + d_omega))

        prev_theta = normalize_angle(prev_theta + sim_omega * dt)

        waypoints.append(Waypoint(
            x=pos[0],
            y=pos[1],
            theta=prev_theta,
            v=sim_v,
            omega=sim_omega
        ))

    return waypoints


# ---------------------------------------------------------------------------
# High-Level Profile Generators for move_to and push
# ---------------------------------------------------------------------------

def generate_move_to_profile(
    robot_pos: Tuple[float, float],
    robot_theta: float,
    target_pos: Tuple[float, float]
) -> List[Waypoint]:
    """Generate 30-step profile for move_to(target)."""
    dx = target_pos[0] - robot_pos[0]
    dy = target_pos[1] - robot_pos[1]
    target_theta = math.atan2(dy, dx) if math.hypot(dx, dy) > 1e-3 else robot_theta

    return sample_spline_profile(
        p0=robot_pos,
        theta0=robot_theta,
        p1=target_pos,
        theta1=target_theta
    )


def is_within_safe_arena(pos: Tuple[float, float]) -> bool:
    """Check if point is inside the safe robot arena bounds."""
    return (
        ROBOT_SAFE_WALL_MARGIN <= pos[0] <= (ARENA_WIDTH - ROBOT_SAFE_WALL_MARGIN) and
        ROBOT_SAFE_WALL_MARGIN <= pos[1] <= (ARENA_HEIGHT - ROBOT_SAFE_WALL_MARGIN)
    )


def compute_p_via(
    robot_pos: Tuple[float, float],
    puck_pos: Tuple[float, float],
    u_push: Tuple[float, float]
) -> Optional[Tuple[float, float]]:
    """
    Compute Case A bypass waypoint P_via strictly following docs/design.md Section 4.1.
    Returns None if both sides are blocked by arena walls.
    """
    # Left normal: n_push = (-u_y, u_x)
    n_push = (-u_push[1], u_push[0])

    # Side of robot relative to push line
    rp_x = robot_pos[0] - puck_pos[0]
    rp_y = robot_pos[1] - puck_pos[1]
    side_dot = rp_x * n_push[0] + rp_y * n_push[1]
    primary_s = 1.0 if side_dot >= 0.0 else -1.0

    # Candidate 1: Preferred side
    cand1 = (
        puck_pos[0] - BYPASS_LONG_OFFSET * u_push[0] + primary_s * BYPASS_LATERAL_OFFSET * n_push[0],
        puck_pos[1] - BYPASS_LONG_OFFSET * u_push[1] + primary_s * BYPASS_LATERAL_OFFSET * n_push[1]
    )
    if is_within_safe_arena(cand1):
        return cand1

    # Candidate 2: Opposite side (Fallback)
    cand2 = (
        puck_pos[0] - BYPASS_LONG_OFFSET * u_push[0] - primary_s * BYPASS_LATERAL_OFFSET * n_push[0],
        puck_pos[1] - BYPASS_LONG_OFFSET * u_push[1] - primary_s * BYPASS_LATERAL_OFFSET * n_push[1]
    )
    if is_within_safe_arena(cand2):
        return cand2

    # Both sides blocked by arena walls
    return None


def handle_wall_stuck_puck(
    puck_pos: Tuple[float, float],
    target_pos: Tuple[float, float]
) -> Optional[Tuple[float, float]]:
    """
    Case B: Wall-stuck puck scraping projection (docs/design.md Section 4.2).
    If puck is within 35mm of any wall, project target parallel to the wall.
    Returns None if push target points directly into wall (unpushable).
    """
    px, py = puck_pos
    tx, ty = target_pos

    near_left = px < PUCK_WALL_MARGIN
    near_right = px > (ARENA_WIDTH - PUCK_WALL_MARGIN)
    near_top = py < PUCK_WALL_MARGIN
    near_bottom = py > (ARENA_HEIGHT - PUCK_WALL_MARGIN)

    if not (near_left or near_right or near_top or near_bottom):
        return target_pos  # Not wall-stuck

    # If pushing directly into the wall, impossible -> return None
    if (near_left and tx < px) or (near_right and tx > px):
        return None
    if (near_top and ty < py) or (near_bottom and ty > py):
        return None

    # Project to parallel direction (scrape along wall towards arena center)
    proj_x, proj_y = tx, ty
    if near_left or near_right:
        # Keep y component, clamp x towards open field
        proj_x = 300.0
    if near_top or near_bottom:
        # Keep x component, clamp y towards open field
        proj_y = 200.0

    return (proj_x, proj_y)


def generate_push_profile(
    robot_pos: Tuple[float, float],
    robot_theta: float,
    puck_pos: Tuple[float, float],
    target_pos: Tuple[float, float]
) -> Tuple[List[Waypoint], bool, Optional[str]]:
    """
    Generate 30-step profile for push(puck, target) strictly following docs/design.md:
    - V-bumper contact point: P_contact = P_puck - 25mm * u_push
    - Case A check (angle > 60 deg): bypass via P_via
    - Case B check (wall-stuck puck): scraping projection
    Returns: (waypoints, is_safe, reason)
    """
    # 1. Check Case B (Wall-stuck)
    adjusted_target = handle_wall_stuck_puck(puck_pos, target_pos)
    if adjusted_target is None:
        # Target pushes directly into wall: Safe Stop
        stop_pts = [Waypoint(x=robot_pos[0], y=robot_pos[1], theta=robot_theta, v=0.0, omega=0.0) for _ in range(HORIZON_STEPS)]
        return (stop_pts, False, "Puck is stuck against wall and target points into wall.")

    target_pos = adjusted_target

    # Push unit vector
    p_dx = target_pos[0] - puck_pos[0]
    p_dy = target_pos[1] - puck_pos[1]
    push_len = math.hypot(p_dx, p_dy)
    if push_len < 1e-3:
        stop_pts = [Waypoint(x=robot_pos[0], y=robot_pos[1], theta=robot_theta, v=0.0, omega=0.0) for _ in range(HORIZON_STEPS)]
        return (stop_pts, True, "Already at push target.")

    u_push = (p_dx / push_len, p_dy / push_len)
    theta_push = math.atan2(u_push[1], u_push[0])

    # Contact point behind puck (25mm behind along push direction)
    p_contact = (
        puck_pos[0] - CONTACT_OFFSET * u_push[0],
        puck_pos[1] - CONTACT_OFFSET * u_push[1]
    )

    # Vector from robot to puck
    rp_dx = puck_pos[0] - robot_pos[0]
    rp_dy = puck_pos[1] - robot_pos[1]
    rp_len = math.hypot(rp_dx, rp_dy)
    if rp_len < 1e-3:
        v_rp = u_push
    else:
        v_rp = (rp_dx / rp_len, rp_dy / rp_len)

    # 2. Check Case A: Obtuse / steep approach angle (cos(60 deg) = 0.5)
    dot_rp_push = v_rp[0] * u_push[0] + v_rp[1] * u_push[1]
    dist_to_contact = math.hypot(p_contact[0] - robot_pos[0], p_contact[1] - robot_pos[1])

    if dot_rp_push < 0.5 and dist_to_contact > 15.0:
        # Needs bypass via P_via
        p_via = compute_p_via(robot_pos, puck_pos, u_push)
        if p_via is None:
            # Trarapped in corner: Safe Stop
            stop_pts = [Waypoint(x=robot_pos[0], y=robot_pos[1], theta=robot_theta, v=0.0, omega=0.0) for _ in range(HORIZON_STEPS)]
            return (stop_pts, False, "Bypass P_via blocked by arena walls on both sides.")

        # Curve to P_via first
        target_theta_via = math.atan2(p_contact[1] - p_via[1], p_contact[0] - p_via[0])
        profile = sample_spline_profile(
            p0=robot_pos,
            theta0=robot_theta,
            p1=p_via,
            theta1=target_theta_via
        )
        return (profile, True, None)

    # Normal Approach Phase or Push Phase
    if dist_to_contact > 10.0:
        # Approach to P_contact with end tangent aligned to theta_push
        profile = sample_spline_profile(
            p0=robot_pos,
            theta0=robot_theta,
            p1=p_contact,
            theta1=theta_push
        )
    else:
        # In contact: Push Phase towards target_pos
        profile = sample_spline_profile(
            p0=robot_pos,
            theta0=robot_theta,
            p1=target_pos,
            theta1=theta_push
        )

    return (profile, True, None)


def create_safe_stop_profile(
    robot_pos: Tuple[float, float],
    robot_theta: float
) -> List[Waypoint]:
    """Generate 30-step zero-velocity profile for Safe Stop."""
    return [
        Waypoint(x=robot_pos[0], y=robot_pos[1], theta=robot_theta, v=0.0, omega=0.0)
        for _ in range(HORIZON_STEPS)
    ]
