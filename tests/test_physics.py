"""Unit tests for 2D Physics Engine and Simulation Stability.

Verifies:
- Arena wall clamping
- 60 FPS numerical integration
- Rigid contact pushing
- 60s headless simulation completion without crash or deadlock
"""

import math
import pytest
from src.simulation.physics import ArenaPhysics, DifferentialDriveModel
from src.simulation.arena_sim import ArenaSimulator
from src.core.interfaces import CodePolicyAgent
from src.strategies.sample_policy import policy_step as sample_policy


def test_differential_drive_speed_bounds():
    drive = DifferentialDriveModel()
    # Request extreme speed exceeding limits
    v_l, v_r = drive.compute_wheel_speeds(target_v=500.0, target_omega=20.0)
    assert max(abs(v_l), abs(v_r)) <= drive.max_speed + 1e-3


def test_arena_robot_wall_clamping():
    physics = ArenaPhysics()
    # Place robot outside boundaries
    clamped_x, clamped_y = physics.constrain_robot_to_arena(-10.0, -10.0, theta=0.0)
    assert clamped_x >= 25.0
    assert clamped_y >= 25.0

    clamped_x2, clamped_y2 = physics.constrain_robot_to_arena(700.0, 500.0, theta=0.0)
    assert clamped_x2 <= (600.0 - 25.0)
    assert clamped_y2 <= (400.0 - 25.0)


def test_puck_friction_stops_sliding():
    physics = ArenaPhysics()
    # Give puck initial speed
    physics._pucks[0].vx = 100.0
    dt = 1.0 / 60.0

    # Step for 1 second
    for _ in range(60):
        physics.step(dt)

    # Puck should be at rest due to Coulomb drag (1960 mm/s^2 stops 100mm/s in ~0.05s)
    puck0 = physics.pucks[0]
    assert physics._pucks[0].vx == 0.0
    assert physics._pucks[0].vy == 0.0


def test_60_second_headless_simulation_no_crash():
    """Verify 60s match (3600 frames @ 60 FPS) completes without crash or freeze."""
    simulator = ArenaSimulator(headless=True, target_fps=60)
    agent = CodePolicyAgent(policy_func=sample_policy)
    simulator.set_agents(red_agent=agent, blue_agent=None)

    dt = 1.0 / 60.0
    # Simulate full 60 seconds (3600 steps)
    for _ in range(3600):
        simulator.step(dt)

    assert simulator.match_time == pytest.approx(60.0, abs=0.1)
    red_pucks, blue_pucks = simulator.get_zone_counts()
    assert (red_pucks + blue_pucks) == 3


def test_puck_pinned_to_wall_cannot_escape():
    """Verify puck never escapes arena boundary even when continuously pushed into wall."""
    physics = ArenaPhysics()
    # Place blue robot facing right wall, puck in front
    physics.robots["blue"].x = 550.0
    physics.robots["blue"].y = 200.0
    physics.robots["blue"].theta = 0.0
    physics._pucks[0].x = 580.0
    physics._pucks[0].y = 200.0
    physics.set_robot_velocity("blue", 140.0, 0.0)

    dt = 1.0 / 60.0
    for _ in range(180):  # 3 seconds of continuous hard push into wall
        physics.step(dt)
        p = physics._pucks[0]
        assert 10.0 <= p.x <= (physics.width - 10.0)
        assert 10.0 <= p.y <= (physics.height - 10.0)
