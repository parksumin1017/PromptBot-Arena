"""Level 2 Boss AI Strategy: Greedy Pusher.

Designed for Blue Team robot in Core Pusher matches.
Behavior:
1. Greedily selects the nearest puck to itself.
2. Directs a push toward the opponent (Red) territory target (150.0, 200.0).
3. Evaluates will_collide; if dangerous, maneuvers to a defensive side waypoint.
"""

from src.core.models import State, ActionCommand
from src.core.primitives import (
    push, move_to, stop, will_collide,
    get_closest_puck
)


def policy_step(state: State) -> ActionCommand:
    """
    Level 2 Boss tactical policy (Blue Team).
    0.5s tactical decision step.
    """
    # 1. Find the closest puck among all pucks on field
    target_puck = get_closest_puck(state.pucks, state.my_pos)
    if target_puck is None:
        return stop()

    # 2. Push target point: Center-deep into opponent territory
    # If Red team -> push toward Blue territory (450, 200)
    # If Blue team -> push toward Red territory (150, 200)
    target_x = 450.0 if state.my_team == "red" else 150.0
    opponent_target = (target_x, 200.0)
    action = push(target_puck, opponent_target)

    # 3. Collision guard: if path poses collision risk, bypass via flank
    if will_collide(action):
        defense_x = 150.0 if state.my_team == "red" else 450.0
        bypass_target = (defense_x, 80.0) if state.my_pos[1] > 200.0 else (defense_x, 320.0)
        action = move_to(bypass_target)

    return action
