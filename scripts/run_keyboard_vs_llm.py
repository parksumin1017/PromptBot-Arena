"""Run Match: Keyboard Human Player (Red) vs LLM Agent (Blue).

Demonstrates human-vs-AI battle where:
- RED Team  : YOU (Keyboard Human Player - WASD or Arrow Keys)
- BLUE Team : LLM Agent (Code-as-Policies generated from natural language prompt)
- Referee   : 60s Core Pusher Official Rules
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame
from src.core.llm_planner import LLMPlanner
from src.simulation.arena_sim import ArenaSimulator
from src.strategies.keyboard_agent import KeyboardAgent


def main():
    print("==================================================================")
    print("  🎮 PromptBot Arena: Human (Red) vs LLM Agent (Blue) Match")
    print("==================================================================")

    # 1. Initialize LLM Planner for Blue Robot
    planner = LLMPlanner()
    client_name = planner.client.__class__.__name__
    print(f"[*] Active LLM Provider: {client_name}")

    # 2. Get Natural Language Strategy Prompt for Blue Robot
    default_prompt = "블루 팀으로서 우리 진영에 가까운 퍽을 상대 레드 진영(150, 200)으로 밀어줘. 상대 로봇과 충돌 위험이 있으면 사이드로 회피해."
    print(f"\n[?] 블루 팀(LLM 로봇)에게 탑재할 전략 프롬프트를 입력하세요.")
    print(f"    (그냥 Enter를 누르면 기본 전략 프롬프트로 진행됩니다)")
    user_input = input(f"    입력 > ").strip()
    prompt = user_input if user_input else default_prompt

    print(f"\n[*] 입력된 블루 팀 프롬프트: \"{prompt}\"")
    print(f"[*] LLM 코드 변환 요청 중...")

    # 3. Generate Policy Code & Validate AST
    blue_agent, latency, error = planner.create_agent_from_prompt(prompt, agent_name="Blue_LLM_Agent")

    print(f"[*] 변환 소요 시간: {latency:.2f}초")
    if error:
        print(f"[!] API/보안 경고: {error}")
        print("[*] API 토큰 소진 또는 타임아웃 감지 -> 사전에 검증된 저장된 LLM 정책 코드로 자동 전환합니다!")
        from src.strategies.llm_saved_policy import policy_step as fallback_policy_step
        blue_agent = CodePolicyAgent(policy_func=fallback_policy_step, agent_name="Blue_LLM_Saved_Fallback")
        print("[+] 기존 검증 LLM 정책(공격 푸시 & 사이드 우회) 탑재 완료!")
    else:
        print("[+] AST 정적 보안 검사 통과! 블루 로봇에 자율 정책이 탑재되었습니다.")
        if getattr(blue_agent, "code_str", None):
            print("\n--- [LLM이 생성한 블루 팀 파이썬 정책 코드] ---")
            print(blue_agent.code_str)
            print("------------------------------------------------\n")

    # 4. Setup Red (Keyboard Human) and Blue (LLM Agent)
    simulator = ArenaSimulator(scale=1.5, headless=False, target_fps=60)
    red_agent = KeyboardAgent(
        linear_speed=140.0,
        angular_speed=3.0,
        control_scheme="both",
        agent_name="Red_Human_Player"
    )

    simulator.set_agents(red_agent=red_agent, blue_agent=blue_agent)

    print("==================================================================")
    print("  경기 조작 안내:")
    print("  - RED 로봇 (당신) : W/S (전진/후진), A/D 또는 방향키 (좌/우 회전)")
    print("  - BLUE 로봇 (상대) : LLM 실시간 코드 자율 구동")
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

    # 5. Official Referee Report
    res = simulator.match_result
    print("\n==================================================================")
    print(f"  {res.message}")
    print(f"  경기 시간: {res.match_time:.1f}초 | 공식 승자: {res.winner.value.upper()}")
    print(f"  최종 스코어: RED(키보드 당신) {res.score.red_score} : {res.score.blue_score} BLUE(LLM 로봇)")
    print("==================================================================")
    pygame.quit()


if __name__ == "__main__":
    main()
