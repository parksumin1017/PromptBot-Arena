"""Unit tests for Cubic Hermite Spline Trajectory Generation.

Verifies:
- Cubic Hermite Spline formulation
- 30-step profile length, time step (dt = 1/60s)
- Velocity and angular velocity bounds (v <= 150 mm/s, |omega| <= pi rad/s)
- Case A obtuse angle bypass (P_via calculation)
- Case B wall-stuck scraping
"""

import math
import pytest
from src.core.trajectory import (
    hermite_point,
    sample_spline_profile,
    generate_move_to_profile,
    generate_push_profile,
    compute_p_via,
    handle_wall_stuck_puck,
    V_MAX,
    OMEGA_MAX,
    HORIZON_STEPS
)


def test_hermite_boundary_points():
    p0 = (100.0, 200.0)
    p1 = (300.0, 200.0)
    m0 = (200.0, 0.0)
    m1 = (200.0, 0.0)

    start = hermite_point(p0, m0, p1, m1, 0.0)
    end = hermite_point(p0, m0, p1, m1, 1.0)
    mid = hermite_point(p0, m0, p1, m1, 0.5)

    assert start[0] == pytest.approx(100.0)
    assert start[1] == pytest.approx(200.0)
    assert end[0] == pytest.approx(300.0)
    assert end[1] == pytest.approx(200.0)
    assert mid[0] == pytest.approx(200.0)
    assert mid[1] == pytest.approx(200.0)


def test_profile_bounds():
    p0 = (100.0, 200.0)
    theta0 = 0.0
    p1 = (400.0, 300.0)
    theta1 = 1.0

    waypoints = sample_spline_profile(p0, theta0, p1, theta1)
    assert len(waypoints) == HORIZON_STEPS

    for wp in waypoints:
        assert 0.0 <= wp.v <= V_MAX + 1e-3, f"Speed {wp.v} exceeded V_MAX {V_MAX}"
        assert abs(wp.omega) <= OMEGA_MAX + 1e-3, f"Omega {wp.omega} exceeded OMEGA_MAX {OMEGA_MAX}"


def test_case_a_p_via_calculation():
    # Robot is at (100, 200), puck at (200, 200), pushing backwards to (100, 200) -> 180 deg reversal!
    robot_pos = (100.0, 200.0)
    puck_pos = (200.0, 200.0)
    u_push = (-1.0, 0.0)  # Push left

    p_via = compute_p_via(robot_pos, puck_pos, u_push)
    assert p_via is not None

    # Normal should be perpendicular (in y direction: lateral offset 45mm)
    # Long offset is 15mm behind puck in direction opposite to u_push (+15 in x)
    assert abs(p_via[1] - 200.0) == pytest.approx(45.0)
    assert p_via[0] == pytest.approx(215.0)


def test_case_b_wall_stuck_puck():
    # Puck stuck near bottom wall (y = 390, wall at 400)
    puck_pos = (300.0, 390.0)
    # Attempting to push deeper into bottom wall (300, 450) -> should be impossible
    impossible = handle_wall_stuck_puck(puck_pos, (300.0, 450.0))
    assert impossible is None

    # Attempting to push parallel towards blue zone -> should project towards center
    scraping = handle_wall_stuck_puck(puck_pos, (500.0, 390.0))
    assert scraping is not None
    assert scraping[1] == pytest.approx(200.0)  # Projected away from wall
