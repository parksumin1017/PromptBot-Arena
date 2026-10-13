"""Run Match: Keyboard Human Player (Red) vs LLM Saved Policy (Blue).

Offline Demonstration Launcher:
- No LLM API tokens required (Instant launch).
- RED Team  : YOU (Keyboard Human Player - WASD or Arrow Keys)
- BLUE Team : LLM Autonomous Policy (Pre-generated Code-as-Policies strategy)
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
from src.strategies.keyboard_agent import KeyboardAgent
from src.strategies.llm_saved_policy import policy_step as blue_llm_policy_step


def main():
    print("==================================================================")
    print("  🎮 PromptBot Arena: Human (Red) vs LLM Policy (Blue) Match")
    print("  [오프라인 즉시 시연 모드 - API 토큰 소모 없음]")
    print("==================================================================")

    # 1. Setup Red (Keyboard Human) and Blue (Saved LLM Agent)
    simulator = ArenaSimulator(scale=1.5, headless=False, target_fps=60)
    red_agent = KeyboardAgent(
        linear_speed=140.0,
        angular_speed=3.0,
        control_scheme="both",
        agent_name="Red_Human_Player"
    )

    blue_agent = CodePolicyAgent(
        policy_func=blue_llm_policy_step,
        agent_name="Blue_LLM_Saved"
    )

    simulator.set_agents(red_agent=red_agent, blue_agent=blue_agent)

    print("[+] 블루 로봇: 기존 LLM 생성 정책(공격 푸시 & 사이드 우회) 탑재 완료!")
    print("==================================================================")
    print("  경기 조작 안내:")
    print("  - RED 로봇 (당신) : W/S (전진/후진), A/D 또는 방향키 (좌/우 회전)")
    print("  - BLUE 로봇 (상대) : LLM 자율 정책 구동 (60초 Core Pusher)")
    print("  - 단축키: SPACE (일시정지/재개), R (리셋), ESC (종료)")
    print("==================================================================")

    running = True
    clock = pygame.time.Clock()
    dt = 1.0 / 60.0

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

    # 2. Official Referee Report
    res = simulator.match_result
    print("\n==================================================================")
    print(f"  {res.message}")
    print(f"  경기 시간: {res.match_time:.1f}초 | 공식 승자: {res.winner.value.upper()}")
    print(f"  최종 스코어: RED(키보드 당신) {res.score.red_score} : {res.score.blue_score} BLUE(LLM 로봇)")
    print("==================================================================")
    pygame.quit()


if __name__ == "__main__":
    main()
