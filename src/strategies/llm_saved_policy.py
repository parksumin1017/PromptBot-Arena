"""Pre-generated LLM Policy Strategy for Blue Team.

Generated from prompt:
"우리 블루 진영에 있는 퍽 중 가장 가까운 퍽을 찾아 상대 레드 진영(150, 200)으로 밀어줘.
 만약 내 위치가 벽(y < 60 또는 y > 340 또는 x > 540)에 너무 가까우면 먼저 중앙(300, 200)으로 빠져나온 뒤 밀고,
 상대 로봇과 부딪힐 것 같으면 사이드로 우회해."

Used for offline demonstration and testing without API token consumption.
"""

from src.core.models import State, ActionCommand
from src.core.primitives import (
    push, move_to, stop, will_collide,
    get_dist, get_closest_puck, get_pucks_in_zone
)


def policy_step(state: State) -> ActionCommand:
    # Targets: push 3 pucks into opponent territory
    if state.my_team == 'blue':
        push_target = (150.0, 200.0)
        my_zone = 'blue'
    else:
        push_target = (450.0, 200.0)
        my_zone = 'red'

    center = (300.0, 200.0)

    def clamp(v, lo, hi):
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v

    def pick_side_y(y):
        # Choose a side lane away from current y to help pass around opponent
        if y <= 200.0:
            return 320.0
        return 80.0

    def safe_move(target_xy):
        act = move_to(target_xy)
        if not will_collide(act):
            return act
        # If direct path collides, try a side-lane waypoint first
        side_y = pick_side_y(state.my_pos[1])
        wp1 = (clamp(state.my_pos[0], 60.0, 540.0), side_y)
        act1 = move_to(wp1)
        if not will_collide(act1):
            return act1
        # If still risky, try side lane at center x
        wp2 = (300.0, side_y)
        act2 = move_to(wp2)
        if not will_collide(act2):
            return act2
        # Last resort
        return stop()

    # If too close to walls, retreat to center first
    x, y = state.my_pos
    if (y < 60.0) or (y > 340.0) or (x > 540.0):
        return safe_move(center)

    # Find the closest puck in our zone
    zone_pucks = get_pucks_in_zone(state.pucks, my_zone)
    puck = get_closest_puck(zone_pucks, state.my_pos)
    if puck is None:
        return safe_move(center)

    # Try pushing; if collision risk, detour via a side lane near the puck
    push_act = push(puck, push_target)
    if not will_collide(push_act):
        return push_act

    side_y = pick_side_y(state.my_pos[1])
    detour_x = clamp(puck.x, 60.0, 540.0)
    detour = (detour_x, side_y)
    return safe_move(detour)
