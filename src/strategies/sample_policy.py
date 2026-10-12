"""Sample Player Policy for PromptBot Arena.

Strictly follows the policy_step interface from docs/design.md:
def policy_step(state: State) -> ActionCommand: ...
"""

from src.core.models import State, ActionCommand
from src.core.primitives import (
    push, move_to, stop, will_collide,
    get_closest_puck, get_pucks_in_zone
)


def policy_step(state: State) -> ActionCommand:
    """
    Sample baseline policy:
    1. Select the closest puck still in the Red (our) zone.
    2. If all pucks are already in Blue zone, push the closest puck deeper.
    3. Push toward the opponent territory target (450, 200).
    4. If collision is predicted, safe stop or maneuver.
    """
    red_pucks = get_pucks_in_zone(state.pucks, zone="red")
    if red_pucks:
        target_puck = get_closest_puck(red_pucks, state.my_pos)
    else:
        target_puck = get_closest_puck(state.pucks, state.my_pos)

    if target_puck is None:
        return stop()

    # Target: deep into blue zone
    push_target = (450.0, 200.0)
    action = push(target_puck, push_target)

    # If push has collision risk, maneuver to side
    if will_collide(action):
        safe_bypass = (150.0, 100.0) if state.my_pos[1] > 200.0 else (150.0, 300.0)
        action = move_to(safe_bypass)

    return action
