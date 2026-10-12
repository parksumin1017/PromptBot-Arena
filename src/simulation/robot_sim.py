"""Simulated Robot Actuator for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 1.2: BaseRobot subclass, purely sends velocity commands to ArenaPhysics.
"""

from typing import Tuple, Optional
from src.core.interfaces import BaseRobot
from src.core.models import ActionCommand
from src.simulation.physics import ArenaPhysics


class SimulatedRobot(BaseRobot):
    """
    2-wheel differential drive simulated robot actuator.
    Pure actuator: forwards velocity commands to ArenaPhysics.
    """

    def __init__(
        self,
        robot_id: str,
        team: str,
        physics: ArenaPhysics,
        color_front: Tuple[int, int, int] = (255, 30, 30),
        color_rear: Tuple[int, int, int] = (255, 150, 180),
        initial_pos: Optional[Tuple[float, float]] = None,
        initial_theta: Optional[float] = None
    ):
        self.robot_id = robot_id
        self.team = team
        self.physics = physics

        self.color_front = color_front
        self.color_rear = color_rear

        if initial_pos is not None and team in self.physics.robots:
            self.physics.robots[team].x, self.physics.robots[team].y = initial_pos
        if initial_theta is not None and team in self.physics.robots:
            self.physics.robots[team].theta = initial_theta

        self.current_action: ActionCommand = ActionCommand(command_type="stop", target=(0.0, 0.0))
        self.is_safe_stopped = False

    def send_velocity(self, v: float, omega: float) -> None:
        """Apply linear velocity v and angular velocity omega to the physics engine."""
        self.physics.set_robot_velocity(self.team, v, omega)

    def emergency_stop(self) -> None:
        """Emergency stop: set velocities to zero."""
        self.is_safe_stopped = True
        self.physics.set_robot_velocity(self.team, 0.0, 0.0)

    def set_action(self, action: ActionCommand) -> None:
        """Assign new 0.5s ActionCommand."""
        self.current_action = action
        self.is_safe_stopped = not action.is_safe

    # Read-only properties for renderer convenience
    @property
    def x(self) -> float:
        pose = self.physics.get_robot_pose(self.team)
        return pose[0][0] if pose else 0.0

    @property
    def y(self) -> float:
        pose = self.physics.get_robot_pose(self.team)
        return pose[0][1] if pose else 0.0

    @property
    def theta(self) -> float:
        pose = self.physics.get_robot_pose(self.team)
        return pose[1] if pose else 0.0
