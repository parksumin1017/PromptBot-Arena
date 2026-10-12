"""Direct Keyboard Controller Agent for PromptBot Arena.

Pure manual keyboard teleoperation without spline interpolation or collision prediction:
- Responds purely to user keystrokes (WASD or Arrow keys).
- Generates straight linear velocity (v) and angular velocity (omega).
- Fills 30 control waypoints with constant velocity profile (no Hermite curve, no will_collide).
"""

import pygame
from typing import Optional
from src.core.models import State, ActionCommand, Waypoint
from src.core.interfaces import BaseAgent


class KeyboardAgent(BaseAgent):
    """
    Direct Keyboard Control Agent.
    Strictly follows BaseAgent interface without autonomous curve planning or collision guards.
    """

    def __init__(
        self,
        linear_speed: float = 120.0,     # mm/s
        angular_speed: float = 2.5,      # rad/s
        control_scheme: str = "both",    # "wasd", "arrows", or "both"
        agent_name: str = "KeyboardAgent"
    ):
        self.linear_speed = linear_speed
        self.angular_speed = angular_speed
        self.control_scheme = control_scheme
        self.agent_name = agent_name
        self.is_realtime = True

    def get_action(self, state: State) -> ActionCommand:
        """Read active keys and produce 30-step constant velocity ActionCommand."""
        try:
            keys = pygame.key.get_pressed()
        except Exception:
            keys = ()

        v = 0.0
        omega = 0.0

        # Linear speed: Forward / Backward
        up = False
        down = False
        left = False
        right = False

        def is_pressed(k: int) -> bool:
            try:
                return bool(keys[k])
            except (IndexError, KeyError, TypeError):
                return False

        if self.control_scheme in ("wasd", "both"):
            up = up or is_pressed(pygame.K_w)
            down = down or is_pressed(pygame.K_s)
            left = left or is_pressed(pygame.K_a)
            right = right or is_pressed(pygame.K_d)

        if self.control_scheme in ("arrows", "both"):
            up = up or is_pressed(pygame.K_UP)
            down = down or is_pressed(pygame.K_DOWN)
            left = left or is_pressed(pygame.K_LEFT)
            right = right or is_pressed(pygame.K_RIGHT)

        if up and not down:
            v = self.linear_speed
        elif down and not up:
            v = -self.linear_speed

        if left and not right:
            omega = -self.angular_speed
        elif right and not left:
            omega = self.angular_speed

        # Build 30 waypoints integrating straight / turning motion (dt = 1/60s)
        import math
        dt = 1.0 / 60.0
        curr_x, curr_y = state.my_pos
        curr_theta = state.my_theta
        waypoints = []
        for _ in range(30):
            curr_x += v * math.cos(curr_theta) * dt
            curr_y += v * math.sin(curr_theta) * dt
            curr_theta += omega * dt
            waypoints.append(Waypoint(x=curr_x, y=curr_y, theta=curr_theta, v=v, omega=omega))

        cmd_type = "keyboard_move" if (v != 0.0 or omega != 0.0) else "stop"

        return ActionCommand(
            command_type=cmd_type,
            target=(curr_x, curr_y),
            waypoints=waypoints,
            is_safe=True
        )
