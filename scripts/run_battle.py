"""Interactive Natural Language Prompt-to-Battle Launcher for PromptBot Arena.

Workflow:
1. User enters natural language strategy prompt in CLI.
2. Standardized LLMPlanner (Postech School API or configured provider) generates code.
3. AST Security validator audits generated Python code.
4. Player CodePolicyAgent battles against Level 2 Boss in 60s Core Pusher arena.
5. Official Referee reports outcome.
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
from src.strategies.boss.level2 import policy_step as boss_level2_policy_step


def main():
    print("==================================================================")
    print("   🎮 PromptBot Arena: Prompt-to-Battle Interactive Arena")
    print("==================================================================")

    # 1. Initialize Standardized LLM Planner
    planner = LLMPlanner()
    client_name = planner.client.__class__.__name__
    print(f"[*] Active LLM Provider: {client_name}")

    # 2. Get Natural Language Strategy Prompt
    default_prompt = "우리 진영에 있는 가장 가까운 공을 찾아서 상대 골대로 밀어줘. 상대와 부딪힐 것 같으면 사이드로 돌아가."
    print(f"\n[?] 로봇에게 지시할 전술 프롬프트를 입력하세요.")
    print(f"    (그냥 Enter를 누르면 기본 예시 전술로 진행됩니다)")
    user_input = input(f"    입력 > ").strip()
    prompt = user_input if user_input else default_prompt

    print(f"\n[*] 입력된 프롬프트: \"{prompt}\"")
    print(f"[*] LLM 코드 변환 요청 중...")

    # 3. Generate Agent & Validate AST
    agent, latency, error = planner.create_agent_from_prompt(prompt, agent_name="Player_CaP")

    print(f"[*] 변환 소요 시간: {latency:.2f}초")
    if error:
        print(f"[!] 경고: {error}")
        print("[!] 안전을 위해 로봇이 정지(Safe Stop) 상태로 출전합니다.")
    else:
        print("[+] AST 정적 보안 검사 통과! 승인된 policy_step 함수가 로봇에 탑재되었습니다.")
        if getattr(agent, "code_str", None):
            print("\n--- [생성된 파이썬 정책 코드] ---")
            print(agent.code_str)
            print("----------------------------------\n")

    # 4. Setup Simulator with Player vs Level 2 Boss
    simulator = ArenaSimulator(scale=1.5, headless=False, target_fps=60)
    simulator.set_agents(
        red_agent=agent,
        blue_agent=None  # We'll wrap Level 2 boss
    )
    from src.core.interfaces import CodePolicyAgent
    boss_agent = CodePolicyAgent(policy_func=boss_level2_policy_step, agent_name="Blue_Boss_Lv2")
    simulator.set_agents(red_agent=agent, blue_agent=boss_agent)

    print("[*] 60초 디지털 트윈 배틀 시뮬레이터를 시작합니다.")
    print("    컨트롤: SPACE (일시정지/재개), R (경기 리셋), ESC (종료)")

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
    print(f"  최종 스코어: RED(플레이어) {res.score.red_score} : {res.score.blue_score} BLUE(보스)")
    print("==================================================================")
    pygame.quit()


if __name__ == "__main__":
    main()
