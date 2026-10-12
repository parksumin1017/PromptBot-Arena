"""Pygame-based 2D Digital Twin Simulator for PromptBot Arena.

Strictly implements specifications from docs/design.md:
- Section 1.1: 2-tier execution architecture (0.5s Tactical Horizon, 60 FPS Control Step)
- Section 2.1: 600x400 mm arena geometry and Core Pusher zone scoring
- Section 2.2: 50x50 mm robot with V-shaped bumper and 2-tone LED rendering
"""

import math
from typing import List, Tuple, Optional
import pygame

from src.core.models import Puck, State, ActionCommand
from src.core.interfaces import BaseAgent
from src.simulation.physics import ArenaPhysics
from src.simulation.robot_sim import SimulatedRobot
from src.simulation.vision_sim import SimulatedVision
from src.simulation.referee import CorePusherReferee, MatchStatus, MatchResult


class ArenaSimulator:
    """
    2D Digital Twin Simulator.
    - Arena size: 600 mm x 400 mm
    - 2 Robots: Red (Player), Blue (Boss)
    - 3 Pucks: Diameter 20 mm
    - 60 FPS control step execution consuming 30-step trajectory profiles
    - 0.5s (2 Hz) tactical decision interval
    """

    ARENA_WIDTH_MM = 600.0
    ARENA_HEIGHT_MM = 400.0
    MIDLINE_X_MM = 300.0

    def __init__(
        self,
        scale: float = 1.5,           # 1 mm = 1.5 px (900 x 600 px viewport)
        headless: bool = False,       # Headless mode for automated tests
        target_fps: int = 60
    ):
        self.scale = scale
        self.headless = headless
        self.target_fps = target_fps

        self.view_w = int(self.ARENA_WIDTH_MM * self.scale)
        self.view_h = int(self.ARENA_HEIGHT_MM * self.scale)
        self.hud_h = 60
        self.win_w = self.view_w
        self.win_h = self.view_h + self.hud_h

        # 1. Physics Engine Ground Truth
        self.physics = ArenaPhysics(
            arena_width=self.ARENA_WIDTH_MM,
            arena_height=self.ARENA_HEIGHT_MM,
            puck_radius=10.0,
            robot_radius=27.0
        )

        # 2. Simulated Robot Actuators
        self.red_robot = SimulatedRobot(
            robot_id="robot_red",
            team="red",
            physics=self.physics,
            color_front=(255, 40, 40),
            color_rear=(255, 140, 190),
            initial_pos=(100.0, 200.0),
            initial_theta=0.0
        )

        self.blue_robot = SimulatedRobot(
            robot_id="robot_blue",
            team="blue",
            physics=self.physics,
            color_front=(40, 100, 255),
            color_rear=(100, 210, 255),
            initial_pos=(500.0, 200.0),
            initial_theta=math.pi
        )

        # 3. Vision Sensor
        self.vision = SimulatedVision(self.physics)

        # 4. Agent Controllers
        self.red_agent: Optional[BaseAgent] = None
        self.blue_agent: Optional[BaseAgent] = None

        # 5. Timing & State
        self.match_time = 0.0
        self.decision_timer = 0.0
        self.decision_interval = 0.5  # 2 Hz
        self.max_match_time = 60.0
        self.is_paused = False

        # 6. Official Match Referee
        self.referee = CorePusherReferee(max_match_time=self.max_match_time)
        self.match_result: MatchResult = self.referee.update(0.0, self.physics.pucks)

        # Pygame resources
        self.screen = None
        self.clock = None
        self.font = None
        self.font_small = None
        self.font_title = None

        if not self.headless:
            pygame.init()
            self.screen = pygame.display.set_mode((self.win_w, self.win_h))
            pygame.display.set_caption("PromptBot Arena - 2D Digital Twin Simulator")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont("Consolas,Malgun Gothic,Arial", 16)
            self.font_small = pygame.font.SysFont("Consolas,Malgun Gothic,Arial", 13)
            self.font_title = pygame.font.SysFont("Consolas,Malgun Gothic,Arial", 20, bold=True)

    def to_screen_coords(self, x_mm: float, y_mm: float) -> Tuple[int, int]:
        """Convert arena mm coordinates to screen px coordinates."""
        sx = int(x_mm * self.scale)
        sy = int(y_mm * self.scale) + self.hud_h
        return sx, sy

    def set_agents(self, red_agent: Optional[BaseAgent] = None, blue_agent: Optional[BaseAgent] = None) -> None:
        """Register tactical agents for Red and Blue robots."""
        if red_agent is not None:
            self.red_agent = red_agent
        if blue_agent is not None:
            self.blue_agent = blue_agent

    @property
    def pucks(self) -> List[Puck]:
        """Return read-only Puck DTOs."""
        return self.physics.pucks

    def reset(self) -> None:
        """Reset the match and arena state."""
        self.physics.reset()
        self.red_robot.set_action(ActionCommand(command_type="stop", target=(0.0, 0.0)))
        self.blue_robot.set_action(ActionCommand(command_type="stop", target=(0.0, 0.0)))
        self.match_time = 0.0
        self.decision_timer = 0.0
        self.match_result = self.referee.update(0.0, self.physics.pucks)

    def step(self, dt: float) -> None:
        """Update 60 FPS control step and 0.5s tactical horizon."""
        if self.is_paused:
            return

        self.match_time += dt

        # Update official match state through referee
        self.match_result = self.referee.update(self.match_time, self.pucks)

        # Halt robots if match finished
        if self.match_result.status == MatchStatus.FINISHED:
            self.red_robot.send_velocity(0.0, 0.0)
            self.blue_robot.send_velocity(0.0, 0.0)
            self.physics.step(dt)
            return

        # 1. 0.5s Tactical Decision Step (2 Hz) for autonomous AI agents
        self.decision_timer += dt
        is_tactical_tick = (self.decision_timer >= self.decision_interval or self.match_time <= dt)

        if is_tactical_tick:
            self.decision_timer = 0.0

            if self.red_agent is not None and not getattr(self.red_agent, "is_realtime", False):
                red_state = self.vision.capture_state(self.match_time, my_team="red")
                self.red_robot.set_action(self.red_agent.get_action(red_state))

            if self.blue_agent is not None and not getattr(self.blue_agent, "is_realtime", False):
                blue_state = self.vision.capture_state(self.match_time, my_team="blue")
                self.blue_robot.set_action(self.blue_agent.get_action(blue_state))

        # Real-time Interactive Agents (e.g. Keyboard player @ 60 FPS with 0 latency)
        if self.red_agent is not None and getattr(self.red_agent, "is_realtime", False):
            red_state = self.vision.capture_state(self.match_time, my_team="red")
            self.red_robot.set_action(self.red_agent.get_action(red_state))

        if self.blue_agent is not None and getattr(self.blue_agent, "is_realtime", False):
            blue_state = self.vision.capture_state(self.match_time, my_team="blue")
            self.blue_robot.set_action(self.blue_agent.get_action(blue_state))

        # 2. 60 FPS Low-level Trajectory Profile Execution
        step_idx = int(self.decision_timer / dt)

        # Red robot execution
        red_act = self.red_robot.current_action
        if red_act and red_act.waypoints:
            idx = 0 if getattr(self.red_agent, "is_realtime", False) else min(len(red_act.waypoints) - 1, max(0, step_idx))
            wp = red_act.waypoints[idx]
            self.red_robot.send_velocity(wp.v, wp.omega)
        else:
            self.red_robot.send_velocity(0.0, 0.0)

        # Blue robot execution
        blue_act = self.blue_robot.current_action
        if blue_act and blue_act.waypoints:
            idx = 0 if getattr(self.blue_agent, "is_realtime", False) else min(len(blue_act.waypoints) - 1, max(0, step_idx))
            wp = blue_act.waypoints[idx]
            self.blue_robot.send_velocity(wp.v, wp.omega)
        else:
            self.blue_robot.send_velocity(0.0, 0.0)

        # 3. Integrate 60 FPS Physics Step
        self.physics.step(dt)

    def get_zone_counts(self) -> Tuple[int, int]:
        """Return (red_zone_pucks, blue_zone_pucks) count for Core Pusher."""
        red_count = sum(1 for p in self.pucks if p.zone == "red")
        blue_count = sum(1 for p in self.pucks if p.zone == "blue")
        return red_count, blue_count

    def render(self) -> None:
        """Render 2D viewport."""
        if self.headless or self.screen is None:
            return

        self.screen.fill((20, 24, 30))

        # 1. Top HUD Dashboard
        hud_rect = pygame.Rect(0, 0, self.win_w, self.hud_h)
        pygame.draw.rect(self.screen, (15, 17, 22), hud_rect)
        pygame.draw.line(self.screen, (40, 48, 60), (0, self.hud_h), (self.win_w, self.hud_h), 2)

        # Match Timer
        time_rem = max(0.0, self.max_match_time - self.match_time)
        timer_text = f"TIME: {time_rem:04.1f}s"
        t_surf = self.font_title.render(timer_text, True, (255, 215, 0))
        self.screen.blit(t_surf, (20, 16))

        # Red Status (Left-Center)
        red_act = self.red_robot.current_action
        if self.red_robot.is_safe_stopped:
            red_text = "RED: SAFE STOP"
            red_color = (255, 90, 90)
        elif getattr(self.red_agent, "is_realtime", False):
            if red_act and red_act.waypoints:
                wp = red_act.waypoints[0]
                if abs(wp.v) > 5.0 and abs(wp.omega) > 0.1:
                    red_text = "RED: DRIVE+TURN"
                elif wp.v > 5.0:
                    red_text = "RED: FORWARD"
                elif wp.v < -5.0:
                    red_text = "RED: BACKWARD"
                elif wp.omega < -0.1:
                    red_text = "RED: TURN LEFT"
                elif wp.omega > 0.1:
                    red_text = "RED: TURN RIGHT"
                else:
                    red_text = "RED: STOP"
            else:
                red_text = "RED: STOP"
            red_color = (255, 130, 130)
        elif red_act:
            red_text = f"RED: {red_act.command_type.upper()}"
            red_color = (255, 130, 130)
        else:
            red_text = "RED: IDLE"
            red_color = (180, 180, 180)

        r_surf = self.font_small.render(red_text, True, red_color)
        self.screen.blit(r_surf, (155, 20))

        # Core Pusher Score
        red_zone_pucks, blue_zone_pucks = self.get_zone_counts()
        red_score = blue_zone_pucks
        blue_score = red_zone_pucks

        score_text = f"RED {red_score} : {blue_score} BLUE"
        s_surf = self.font_title.render(score_text, True, (240, 240, 240))
        s_rect = s_surf.get_rect(center=(self.win_w // 2, self.hud_h // 2))
        self.screen.blit(s_surf, s_rect)

        # Blue Policy Status (Right)
        blue_act = self.blue_robot.current_action
        if self.blue_robot.is_safe_stopped:
            blue_text = "BLUE: SAFE STOP"
            blue_color = (255, 90, 90)
        elif getattr(self.blue_agent, "is_realtime", False):
            if blue_act and blue_act.waypoints:
                wp = blue_act.waypoints[0]
                if abs(wp.v) > 5.0 and abs(wp.omega) > 0.1:
                    blue_text = "BLUE: DRIVE+TURN"
                elif wp.v > 5.0:
                    blue_text = "BLUE: FORWARD"
                elif wp.v < -5.0:
                    blue_text = "BLUE: BACKWARD"
                elif wp.omega < -0.1:
                    blue_text = "BLUE: TURN LEFT"
                elif wp.omega > 0.1:
                    blue_text = "BLUE: TURN RIGHT"
                else:
                    blue_text = "BLUE: STOP"
            else:
                blue_text = "BLUE: STOP"
            blue_color = (100, 180, 255)
        elif blue_act:
            cmd = blue_act.command_type.upper()
            if cmd == "PUSH":
                p_info = f"#{blue_act.target_puck_id}" if blue_act.target_puck_id is not None else ""
                blue_text = f"BLUE: PUSH {p_info} → ({int(blue_act.target[0])},{int(blue_act.target[1])})"
            elif cmd == "MOVE_TO":
                blue_text = f"BLUE: MOVE → ({int(blue_act.target[0])},{int(blue_act.target[1])})"
            else:
                blue_text = f"BLUE: {cmd}"
            blue_color = (100, 180, 255)
        else:
            blue_text = "BLUE: IDLE"
            blue_color = (160, 170, 185)

        b_surf = self.font_small.render(blue_text, True, blue_color)
        self.screen.blit(b_surf, (self.win_w - 290, 20))

        # 2. Arena Floor
        arena_rect = pygame.Rect(0, self.hud_h, self.view_w, self.view_h)
        pygame.draw.rect(self.screen, (28, 32, 40), arena_rect)

        # 50mm grid lines
        grid_step = int(50.0 * self.scale)
        for gx in range(0, self.view_w, grid_step):
            pygame.draw.line(self.screen, (34, 40, 50), (gx, self.hud_h), (gx, self.win_h), 1)
        for gy in range(self.hud_h, self.win_h, grid_step):
            pygame.draw.line(self.screen, (34, 40, 50), (0, gy), (self.view_w, gy), 1)

        # Midline (x = 300 mm)
        mid_x, _ = self.to_screen_coords(self.MIDLINE_X_MM, 0)
        pygame.draw.line(self.screen, (100, 115, 135), (mid_x, self.hud_h), (mid_x, self.win_h), 2)

        # Center circle
        mid_cy = self.hud_h + self.view_h // 2
        pygame.draw.circle(self.screen, (50, 60, 75), (mid_x, mid_cy), int(40 * self.scale), 2)

        # Arena wall boundary
        pygame.draw.rect(self.screen, (180, 190, 205), arena_rect, 4)

        # 3. Pucks (White LED)
        for p in self.pucks:
            px, py = self.to_screen_coords(p.x, p.y)
            pr = int(10.0 * self.scale)
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), pr)
            p_id_surf = self.font_small.render(str(p.id), True, (20, 20, 20))
            self.screen.blit(p_id_surf, (px - p_id_surf.get_width() // 2, py - p_id_surf.get_height() // 2))

        # 4. Robots
        self._render_robot(self.red_robot)
        self._render_robot(self.blue_robot)

        # 5. Match Finished Overlay Banner
        if self.match_result.status == MatchStatus.FINISHED:
            banner_h = 70
            banner_y = self.hud_h + (self.view_h - banner_h) // 2
            banner_surf = pygame.Surface((self.win_w, banner_h), pygame.SRCALPHA)
            banner_surf.fill((10, 12, 16, 230))
            self.screen.blit(banner_surf, (0, banner_y))

            res_text = self.match_result.message
            w_surf = self.font_title.render(res_text, True, (255, 215, 0))
            w_rect = w_surf.get_rect(center=(self.win_w // 2, banner_y + banner_h // 2))
            self.screen.blit(w_surf, w_rect)

        pygame.display.flip()
        if self.clock:
            self.clock.tick(self.target_fps)

    def _render_robot(self, robot: SimulatedRobot) -> None:
        """Render 50x50 mm robot with V-bumper notch and LEDs."""
        rx, ry = self.to_screen_coords(robot.x, robot.y)
        theta = robot.theta
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        half_w = 25.0 * self.scale
        half_h = 25.0 * self.scale
        notch_u = 15.0 * self.scale
        notch_w = 18.0 * self.scale
        ux, uy = cos_t, sin_t
        nx, ny = -sin_t, cos_t

        # ㄷ-channel robot vertices (outer & inner forks)
        c_fl_outer = (rx + half_w * ux - half_h * nx, ry + half_w * uy - half_h * ny)
        c_fl_inner = (rx + half_w * ux - notch_w * nx, ry + half_w * uy - notch_w * ny)
        c_bl_corner = (rx + notch_u * ux - notch_w * nx, ry + notch_u * uy - notch_w * ny)
        c_br_corner = (rx + notch_u * ux + notch_w * nx, ry + notch_u * uy + notch_w * ny)
        c_fr_inner = (rx + half_w * ux + notch_w * nx, ry + half_w * uy + notch_w * ny)
        c_fr_outer = (rx + half_w * ux + half_h * nx, ry + half_w * uy + half_h * ny)
        c_rr = (rx - half_w * ux + half_h * nx, ry - half_w * uy + half_h * ny)
        c_rl = (rx - half_w * ux - half_h * nx, ry - half_w * uy - half_h * ny)

        # Body polygon
        body_color = (45, 50, 60) if robot.team == "red" else (40, 48, 62)
        border_color = (220, 60, 60) if robot.team == "red" else (60, 120, 240)
        body_poly = [c_fl_outer, c_fl_inner, c_bl_corner, c_br_corner, c_fr_inner, c_fr_outer, c_rr, c_rl]
        pygame.draw.polygon(self.screen, body_color, body_poly)
        pygame.draw.polygon(self.screen, border_color, body_poly, 2)

        # ㄷ-bumper white highlight along the inner channel
        pygame.draw.lines(self.screen, (240, 240, 240), False, [c_fl_inner, c_bl_corner, c_br_corner, c_fr_inner], 3)

        # Front LED (+18mm)
        led_f_dist = 18.0 * self.scale
        led_fx = int(rx + led_f_dist * ux)
        led_fy = int(ry + led_f_dist * uy)
        pygame.draw.circle(self.screen, robot.color_front, (led_fx, led_fy), int(5 * self.scale))
        pygame.draw.circle(self.screen, (255, 255, 255), (led_fx, led_fy), int(2 * self.scale))

        # Rear LED (-18mm)
        led_r_dist = -18.0 * self.scale
        led_rx = int(rx + led_r_dist * ux)
        led_ry = int(ry + led_r_dist * uy)
        pygame.draw.circle(self.screen, robot.color_rear, (led_rx, led_ry), int(4 * self.scale))
        pygame.draw.circle(self.screen, (255, 255, 255), (led_rx, led_ry), int(1.5 * self.scale))
