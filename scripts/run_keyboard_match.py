"""Run Match: Level 2 Boss (Red) vs Keyboard Human Player (Blue).

Demonstrates plug-and-play modular agent swapping:
- Red Robot : Level 2 Boss AI (Autonomous Greedy Pusher)
- Blue Robot: Keyboard Player (Direct WASD / Arrow Keys control, no curves/prediction)
- Referee   : 60s Core Pusher Official Rules
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame
from src.core.interfaces import CodePolicyAgent
from src.simulation.arena_sim import ArenaSimulator
from src.strategies.boss.level2 import policy_step as boss_level2_policy_step
from src.strategies.keyboard_agent import KeyboardAgent


def main():
    simulator = ArenaSimulator(scale=1.5, headless=False, target_fps=60)

    # Plug-and-play: Red is Level 2 Boss, Blue is Keyboard Human Player
    red_agent = CodePolicyAgent(policy_func=boss_level2_policy_step, agent_name="Red_BossLv2")
    blue_agent = KeyboardAgent(linear_speed=140.0, angular_speed=3.0, control_scheme="both", agent_name="Blue_Human")

    simulator.set_agents(red_agent=red_agent, blue_agent=blue_agent)

    running = True
    clock = pygame.time.Clock()
    dt = 1.0 / 60.0

    print("===========================================================")
    print("  PromptBot Arena: Boss vs Keyboard Match")
    print("  RED Team  : Level 2 Greedy Boss AI")
    print("  BLUE Team : YOU (Keyboard Player - WASD or Arrow Keys)")
    print("  Controls  : W/S (Forward/Back), A/D (Turn Left/Right)")
    print("              SPACE (Pause/Resume), R (Reset), ESC (Quit)")
    print("===========================================================")

    while running and simulator.match_time < simulator.max_match_time:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    simulator.is_paused = not simulator.is_paused
                elif event.key == pygame.K_r:
                    simulator.reset()

        simulator.step(dt)
        simulator.render()
        clock.tick(60)

    # Official Referee Result Report
    res = simulator.match_result
    print("===========================================================")
    print(f"  {res.message}")
    print(f"  Match Time: {res.match_time:.1f}s / Winner: {res.winner.value.upper()}")
    print(f"  Final Score: RED {res.score.red_score} : {res.score.blue_score} BLUE")
    print("===========================================================")
    pygame.quit()


if __name__ == "__main__":
    main()
