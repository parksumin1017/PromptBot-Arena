"""Simulation Runner for PromptBot Arena.

Strictly implements execution specification from docs/design.md Section 8.
Runs a 60-second Core Pusher match in the Digital Twin simulator.
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
from src.strategies.sample_policy import policy_step as red_policy_step
from src.strategies.boss.level2 import policy_step as blue_level2_policy_step


def main():
    simulator = ArenaSimulator(scale=1.5, headless=False, target_fps=60)

    # Register Red Player Policy and Blue Level 2 Boss Policy
    red_agent = CodePolicyAgent(policy_func=red_policy_step, agent_name="RedPlayer")
    blue_agent = CodePolicyAgent(policy_func=blue_level2_policy_step, agent_name="BlueBoss_Lv2")
    simulator.set_agents(red_agent=red_agent, blue_agent=blue_agent)

    running = True
    clock = pygame.time.Clock()
    dt = 1.0 / 60.0

    print("===========================================================")
    print("  PromptBot Arena Simulator Launched")
    print("  Red Agent : Sample Policy (Player)")
    print("  Blue Agent: Level 2 Greedy Pusher (Boss)")
    print("  Controls  : SPACE (Pause/Resume), R (Reset), ESC (Quit)")
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
    print(f"  Score Breakdown: RED {res.score.red_score} : {res.score.blue_score} BLUE")
    print("===========================================================")
    pygame.quit()


if __name__ == "__main__":
    main()
