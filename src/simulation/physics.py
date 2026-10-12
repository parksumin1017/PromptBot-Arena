"""2D Physics Engine and Differential Drive Kinematics for PromptBot Arena Digital Twin.

Strictly implements specifications from docs/design.md:
- Section 2.1: Arena Geometry (600x400 mm, walls 60mm, e_wall = 0.5)
- Section 2.2: Robot Specifications (50x50 mm, v_max = 150 mm/s, omega_max = pi rad/s,
                a_max = 300 mm/s^2, alpha_max = 2*pi rad/s^2, tread = 40 mm)
- Section 2.3: Puck Specifications (radius 10 mm, mass 10g, friction decel = 1960 mm/s^2, e_puck = 0.3)
"""

import math
from typing import Tuple, List, Optional
from src.core.models import Puck, normalize_angle
from src.core.trajectory import V_MAX, OMEGA_MAX, A_MAX, ALPHA_MAX


class DifferentialDriveModel:
    """Differential drive kinematics and acceleration limits for 2-wheel robot."""

    def __init__(
        self,
        wheel_base: float = 40.0,      # Tread width [mm]
        max_speed: float = V_MAX,      # 150.0 mm/s
        max_omega: float = OMEGA_MAX,  # pi rad/s
        max_accel: float = A_MAX,      # 300.0 mm/s^2
        max_alpha: float = ALPHA_MAX   # 2*pi rad/s^2
    ):
        self.L = wheel_base
        self.max_speed = max_speed
        self.max_omega = max_omega
        self.max_accel = max_accel
        self.max_alpha = max_alpha

        self.current_v = 0.0
        self.current_omega = 0.0

    def compute_wheel_speeds(self, target_v: float, target_omega: float) -> Tuple[float, float]:
        """Convert linear and angular velocities to left/right wheel speeds."""
        v_l = target_v - (self.L / 2.0) * target_omega
        v_r = target_v + (self.L / 2.0) * target_omega

        v_max = self.max_speed
        max_wheel = max(abs(v_l), abs(v_r))
        if max_wheel > v_max and max_wheel > 0:
            scale = v_max / max_wheel
            v_l *= scale
            v_r *= scale

        return v_l, v_r

    def update_kinematics(
        self,
        x: float,
        y: float,
        theta: float,
        target_v: float,
        target_omega: float,
        dt: float
    ) -> Tuple[float, float, float, float, float]:
        """Integrate 2-wheel kinematics forward with acceleration limits."""
        # 1. Linear acceleration limit
        dv = target_v - self.current_v
        max_dv = self.max_accel * dt
        dv = max(-max_dv, min(max_dv, dv))
        self.current_v += dv

        # 2. Angular acceleration limit
        d_omega = target_omega - self.current_omega
        max_d_omega = self.max_alpha * dt
        d_omega = max(-max_d_omega, min(max_d_omega, d_omega))
        self.current_omega += d_omega

        # 3. Clip velocity bounds
        self.current_v = max(-self.max_speed, min(self.max_speed, self.current_v))
        self.current_omega = max(-self.max_omega, min(self.max_omega, self.current_omega))

        # 4. Runge-Kutta / Midpoint 2nd order numerical integration
        d_theta = self.current_omega * dt
        mid_theta = theta + d_theta * 0.5
        new_theta = normalize_angle(theta + d_theta)

        new_x = x + self.current_v * math.cos(mid_theta) * dt
        new_y = y + self.current_v * math.sin(mid_theta) * dt

        return new_x, new_y, new_theta, self.current_v, self.current_omega


class RobotPhysicalState:
    """Mutable physical state of a robot inside the physics world."""
    def __init__(self, robot_id: str, team: str, initial_pos: Tuple[float, float], initial_theta: float):
        self.robot_id = robot_id
        self.team = team
        self.x, self.y = initial_pos
        self.theta = initial_theta
        self.target_v = 0.0
        self.target_omega = 0.0
        self.drive = DifferentialDriveModel()

    def set_target_velocity(self, v: float, omega: float) -> None:
        self.target_v = v
        self.target_omega = omega

    @property
    def pose(self) -> Tuple[Tuple[float, float], float]:
        return (self.x, self.y), self.theta

    @property
    def velocity_vector(self) -> Tuple[float, float]:
        v = self.drive.current_v
        return v * math.cos(self.theta), v * math.sin(self.theta)


class PuckPhysicalState:
    """Mutable physical state of a puck inside the physics world."""
    def __init__(self, puck_id: int, x: float, y: float, radius: float = 10.0):
        self.id = puck_id
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = radius


class ArenaPhysics:
    """Single Source of Truth 2D rigid-body simulation for PromptBot Arena."""

    def __init__(
        self,
        arena_width: float = 600.0,
        arena_height: float = 400.0,
        puck_radius: float = 10.0,           # Radius 10 mm (Diameter 20 mm)
        robot_radius: float = 27.0,          # 50x50 box equivalent radius
        puck_friction_decel: float = 1960.0, # mu_floor * g = 0.20 * 9800 mm/s^2
        puck_restitution: float = 0.3,       # e_puck = 0.30
        wall_restitution: float = 0.5        # e_wall = 0.50
    ):
        self.width = arena_width
        self.height = arena_height
        self.puck_radius = puck_radius
        self.robot_radius = robot_radius
        self.puck_friction_decel = puck_friction_decel
        self.puck_restitution = puck_restitution
        self.wall_restitution = wall_restitution

        self.robots = {
            "red": RobotPhysicalState("robot_red", "red", (100.0, 200.0), 0.0),
            "blue": RobotPhysicalState("robot_blue", "blue", (500.0, 200.0), math.pi)
        }
        self._pucks: List[PuckPhysicalState] = [
            PuckPhysicalState(0, 300.0, 100.0, puck_radius),
            PuckPhysicalState(1, 300.0, 200.0, puck_radius),
            PuckPhysicalState(2, 300.0, 300.0, puck_radius)
        ]

    @property
    def pucks(self) -> List[Puck]:
        """Return immutable read-only Puck DTOs."""
        return [Puck(id=p.id, x=p.x, y=p.y) for p in self._pucks]

    def set_robot_velocity(self, team: str, v: float, omega: float) -> None:
        """Apply commanded target velocity for a robot."""
        if team in self.robots:
            self.robots[team].set_target_velocity(v, omega)

    def get_robot_pose(self, team: str) -> Optional[Tuple[Tuple[float, float], float]]:
        """Return ((x, y), theta) pose ground truth."""
        if team in self.robots:
            return self.robots[team].pose
        return None

    def get_robot_velocity(self, team: str) -> Optional[Tuple[float, float]]:
        """Return (vx, vy) ground truth."""
        if team in self.robots:
            return self.robots[team].velocity_vector
        return None

    def reset(self) -> None:
        """Reset all entities to default match setup."""
        self.robots["red"].x, self.robots["red"].y = 100.0, 200.0
        self.robots["red"].theta = 0.0
        self.robots["red"].target_v = 0.0
        self.robots["red"].target_omega = 0.0
        self.robots["red"].drive.current_v = 0.0
        self.robots["red"].drive.current_omega = 0.0

        self.robots["blue"].x, self.robots["blue"].y = 500.0, 200.0
        self.robots["blue"].theta = math.pi
        self.robots["blue"].target_v = 0.0
        self.robots["blue"].target_omega = 0.0
        self.robots["blue"].drive.current_v = 0.0
        self.robots["blue"].drive.current_omega = 0.0

        self._pucks = [
            PuckPhysicalState(0, 300.0, 100.0, self.puck_radius),
            PuckPhysicalState(1, 300.0, 200.0, self.puck_radius),
            PuckPhysicalState(2, 300.0, 300.0, self.puck_radius)
        ]

    def step(self, dt: float) -> None:
        """Integrate 60 FPS physics step."""
        red = self.robots["red"]
        blue = self.robots["blue"]

        # 1. Kinematics integration
        red.x, red.y, red.theta, _, _ = red.drive.update_kinematics(
            red.x, red.y, red.theta, red.target_v, red.target_omega, dt
        )
        blue.x, blue.y, blue.theta, _, _ = blue.drive.update_kinematics(
            blue.x, blue.y, blue.theta, blue.target_v, blue.target_omega, dt
        )

        # 2. Arena wall clamping for robots
        red.x, red.y = self.constrain_robot_to_arena(red.x, red.y, red.theta)
        blue.x, blue.y = self.constrain_robot_to_arena(blue.x, blue.y, blue.theta)

        # 3. Robot-robot collision separation
        pos_r, pos_b = self.handle_robot_robot_collision(
            (red.x, red.y), (blue.x, blue.y), red.theta, blue.theta
        )
        red.x, red.y = pos_r
        blue.x, blue.y = pos_b

        # 4. Puck kinematics, friction, and wall bounces
        self.update_pucks(self._pucks, dt)

        # 5. V-bumper & body collision with pucks
        self.handle_robot_puck_interaction(
            red.x, red.y, red.theta, red.drive.current_v, red.drive.current_omega, self._pucks, dt
        )
        self.handle_robot_puck_interaction(
            blue.x, blue.y, blue.theta, blue.drive.current_v, blue.drive.current_omega, self._pucks, dt
        )

        # 6. Hard constraint: Prevent pucks from ever tunneling outside arena walls
        self.clamp_pucks_to_arena(self._pucks)

    def clamp_pucks_to_arena(self, pucks: List[PuckPhysicalState]) -> None:
        """Strictly contain pucks inside arena boundaries with bounce/clamping."""
        for p in pucks:
            r = p.radius
            if p.x - r < 0.0:
                p.x = r
                if p.vx < 0.0:
                    p.vx = -p.vx * self.wall_restitution
            elif p.x + r > self.width:
                p.x = self.width - r
                if p.vx > 0.0:
                    p.vx = -p.vx * self.wall_restitution

            if p.y - r < 0.0:
                p.y = r
                if p.vy < 0.0:
                    p.vy = -p.vy * self.wall_restitution
            elif p.y + r > self.height:
                p.y = self.height - r
                if p.vy > 0.0:
                    p.vy = -p.vy * self.wall_restitution

            # Hard guarantee: Puck center strictly clamped within valid physical boundaries
            p.x = max(r, min(self.width - r, p.x))
            p.y = max(r, min(self.height - r, p.y))

    def constrain_robot_to_arena(self, x: float, y: float, theta: float = 0.0) -> Tuple[float, float]:
        """Clamp robot within arena walls accounting for orientation."""
        cos_t = abs(math.cos(theta))
        sin_t = abs(math.sin(theta))
        margin = 25.0 * (cos_t + sin_t)
        clamped_x = max(margin, min(self.width - margin, x))
        clamped_y = max(margin, min(self.height - margin, y))
        return clamped_x, clamped_y

    def update_pucks(self, pucks: List[PuckPhysicalState], dt: float) -> None:
        """Update puck position, apply ground Coulomb drag, and bounce off walls."""
        for p in pucks:
            p.x += p.vx * dt
            p.y += p.vy * dt

            # Coulomb ground drag
            speed = math.hypot(p.vx, p.vy)
            if speed > 0.0:
                new_speed = max(0.0, speed - self.puck_friction_decel * dt)
                if new_speed < 5.0:
                    p.vx = 0.0
                    p.vy = 0.0
                else:
                    scale = new_speed / speed
                    p.vx *= scale
                    p.vy *= scale

            # Wall boundaries
            r = p.radius
            if p.x - r < 0.0:
                p.x = r
                p.vx = -p.vx * self.wall_restitution
            elif p.x + r > self.width:
                p.x = self.width - r
                p.vx = -p.vx * self.wall_restitution

            if p.y - r < 0.0:
                p.y = r
                p.vy = -p.vy * self.wall_restitution
            elif p.y + r > self.height:
                p.y = self.height - r
                p.vy = -p.vy * self.wall_restitution

        # Puck-puck collisions
        for i in range(len(pucks)):
            for j in range(i + 1, len(pucks)):
                p1 = pucks[i]
                p2 = pucks[j]
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                dist = math.hypot(dx, dy)
                min_dist = p1.radius + p2.radius

                if dist < min_dist and dist > 1e-4:
                    overlap = min_dist - dist
                    nx = dx / dist
                    ny = dy / dist

                    p1.x -= nx * overlap * 0.5
                    p1.y -= ny * overlap * 0.5
                    p2.x += nx * overlap * 0.5
                    p2.y += ny * overlap * 0.5

                    rel_vx = p2.vx - p1.vx
                    rel_vy = p2.vy - p1.vy
                    vel_along_normal = rel_vx * nx + rel_vy * ny

                    if vel_along_normal < 0:
                        impulse = -(1.0 + self.puck_restitution) * vel_along_normal * 0.5
                        p1.vx -= impulse * nx
                        p1.vy -= impulse * ny
                        p2.vx += impulse * nx
                        p2.vy += impulse * ny

    def handle_robot_puck_interaction(
        self,
        rx: float,
        ry: float,
        rtheta: float,
        rv: float,
        romega: float,
        pucks: List[PuckPhysicalState],
        dt: float
    ) -> None:
        """
        Pure rigid-body contact dynamics between robot V-bumper / body and pucks.
        5 segments forming the robot perimeter:
        1. V-bumper left incline: (15, 0) -> (25, -25)
        2. V-bumper right incline: (15, 0) -> (25, 25)
        3. Left side: (25, -25) -> (-25, -25)
        4. Right side: (25, 25) -> (-25, 25)
        5. Rear: (-25, -25) -> (-25, 25)
        """
        cos_t = math.cos(rtheta)
        sin_t = math.sin(rtheta)
        ux, uy = cos_t, sin_t
        nx, ny = -sin_t, cos_t

        robot_segments = [
            # ㄷ-shaped bumper channel (prevents puck lateral slip-out during turns)
            ((15.0, -18.0), (15.0, 18.0)),   # inner back wall
            ((15.0, -18.0), (25.0, -18.0)),  # left guide wall (fork)
            ((15.0, 18.0), (25.0, 18.0)),    # right guide wall (fork)
            ((25.0, -18.0), (25.0, -25.0)),  # front-left tip
            ((25.0, 18.0), (25.0, 25.0)),    # front-right tip
            # Body perimeter
            ((25.0, -25.0), (-25.0, -25.0)), # left side
            ((25.0, 25.0), (-25.0, 25.0)),   # right side
            ((-25.0, -25.0), (-25.0, 25.0))  # rear
        ]

        for p in pucks:
            dx = p.x - rx
            dy = p.y - ry
            u = dx * ux + dy * uy
            w = dx * nx + dy * ny
            pr = p.radius

            total_delta_u = 0.0
            total_delta_w = 0.0
            total_imp_x = 0.0
            total_imp_y = 0.0
            collision_count = 0

            for (A_u, A_w), (B_u, B_w) in robot_segments:
                seg_u = B_u - A_u
                seg_w = B_w - A_w
                seg_len_sq = seg_u * seg_u + seg_w * seg_w
                if seg_len_sq < 1e-6:
                    continue

                t = max(0.0, min(1.0, ((u - A_u) * seg_u + (w - A_w) * seg_w) / seg_len_sq))
                closest_u = A_u + t * seg_u
                closest_w = A_w + t * seg_w

                diff_u = u - closest_u
                diff_w = w - closest_w
                dist = math.hypot(diff_u, diff_w)

                if dist < pr and dist > 1e-4:
                    overlap = pr - dist
                    norm_u = diff_u / dist
                    norm_w = diff_w / dist

                    total_delta_u += norm_u * overlap
                    total_delta_w += norm_w * overlap
                    collision_count += 1

                    world_nx = norm_u * ux + norm_w * nx
                    world_ny = norm_u * uy + norm_w * ny

                    rc_x = closest_u * ux + closest_w * nx
                    rc_y = closest_u * uy + closest_w * ny

                    v_rot_x = -romega * rc_y
                    v_rot_y = romega * rc_x
                    v_surf_x = rv * ux + v_rot_x
                    v_surf_y = rv * uy + v_rot_y

                    rel_vn = (p.vx - v_surf_x) * world_nx + (p.vy - v_surf_y) * world_ny
                    if rel_vn < 0.0:
                        restitution = self.puck_restitution
                        impulse = -(1.0 + restitution) * rel_vn
                        total_imp_x += impulse * world_nx
                        total_imp_y += impulse * world_ny

            if collision_count > 0:
                u += total_delta_u
                w += total_delta_w
                p.vx += total_imp_x
                p.vy += total_imp_y

            # Prevent puck from tunneling into or through robot body
            if -25.0 <= u < 15.0 and abs(w) <= 25.0:
                u = 15.0 + pr

            # Limit puck speed to realistic physical envelope
            speed = math.hypot(p.vx, p.vy)
            if speed > 350.0:
                scale = 350.0 / speed
                p.vx *= scale
                p.vy *= scale

            p.x = rx + u * ux + w * nx
            p.y = ry + u * uy + w * ny

    def handle_robot_robot_collision(
        self,
        r1_pos: Tuple[float, float],
        r2_pos: Tuple[float, float],
        r1_theta: float = 0.0,
        r2_theta: float = 0.0
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Oriented bounding box separation between robots."""
        x1, y1 = r1_pos
        x2, y2 = r2_pos
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)

        if dist < 1e-4:
            return (x1 - 1.0, y1), (x2 + 1.0, y2)

        nx = dx / dist
        ny = dy / dist

        proj_r1 = 25.0 * (abs(math.cos(r1_theta) * nx + math.sin(r1_theta) * ny) +
                          abs(-math.sin(r1_theta) * nx + math.cos(r1_theta) * ny))
        proj_r2 = 25.0 * (abs(math.cos(r2_theta) * nx + math.sin(r2_theta) * ny) +
                          abs(-math.sin(r2_theta) * nx + math.cos(r2_theta) * ny))

        min_dist = max(50.0, proj_r1 + proj_r2)

        if dist < min_dist:
            overlap = min_dist - dist
            x1 -= nx * overlap * 0.5
            y1 -= ny * overlap * 0.5
            x2 += nx * overlap * 0.5
            y2 += ny * overlap * 0.5

        return (x1, y1), (x2, y2)
