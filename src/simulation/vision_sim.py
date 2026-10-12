"""Simulated Vision Sensor for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 1.2: BaseVision subclass, observes ArenaPhysics and outputs immutable State.
"""

from typing import Tuple, List, Optional
from src.core.interfaces import BaseVision
from src.core.models import State, Puck
from src.simulation.physics import ArenaPhysics


class SimulatedVision(BaseVision):
    """
    Virtual top-down vision sensor observing the ArenaPhysics ground truth.
    Produces read-only State snapshots.
    """

    def __init__(self, physics: ArenaPhysics):
        self.physics = physics

    def capture_state(self, match_time: float, my_team: str = "red") -> State:
        opp_team = "blue" if my_team.lower() == "red" else "red"

        my_pose = self.physics.get_robot_pose(my_team) or ((0.0, 0.0), 0.0)
        opp_pose = self.physics.get_robot_pose(opp_team) or ((0.0, 0.0), 0.0)
        opp_vel = self.physics.get_robot_velocity(opp_team) or (0.0, 0.0)

        # Create immutable Puck DTOs
        pucks = [Puck(id=p.id, x=p.x, y=p.y) for p in self.physics.pucks]

        return State(
            my_pos=my_pose[0],
            my_theta=my_pose[1],
            opp_pos=opp_pose[0],
            opp_theta=opp_pose[1],
            opp_vel=opp_vel,
            pucks=pucks,
            match_time=match_time,
            my_team=my_team
        )

    def get_state(self) -> State:
        """Convenience method returning latest state for red team at t=0.0."""
        return self.capture_state(match_time=0.0, my_team="red")

    def get_robot_pose(self, team: str) -> Optional[Tuple[Tuple[float, float], float]]:
        return self.physics.get_robot_pose(team)

    def get_pucks(self) -> List[Puck]:
        return self.physics.pucks
