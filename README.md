# 프롬프트 봇 아레나 (PromptBot Arena)

> **"프롬프트만으로 로봇에게 지시하여 게임을 단계별로 공략하는 아레나"**  
> 종합설계 II (Capstone Design II) 프로젝트

---

## 📖 문서 바로가기

* [프로젝트 제안서 (Proposal)](docs/proposal.md): 연구 배경, 선행 연구 차별점, 예산 계획 (제출 원본)
* [시스템 명세 및 아키텍처 (System Specification)](docs/overview.md): Action Primitives API 규격, 물리 규격, 코딩 규칙
* [앞으로 할 일 목록 (To-Do List)](docs/todo.md): 주차별 마일스톤 및 예정 작업 백로그
* [작업 완료 내역 및 진행 로그 (Work Progress)](docs/progress.md): 날짜별 완료 작업 내역 및 변경 일지

---

## 🚀 Getting Started

### 1. 개발 환경 활성화 (Conda)
본 프로젝트는 **Python 3.11** 기반의 Anaconda 가상환경 `arena`를 사용합니다.

```bash
conda activate arena
pip install -r requirements.txt
```

### 2. 2D 가상 시뮬레이터 (Digital Twin) 실행
키보드로 로봇을 직접 조종하거나 자율 액션(푸시, 이동) 물리 반응을 테스트합니다.

```bash
python scripts/test_sim_keyboard.py
```
* **조작키**:
  * `WASD` 또는 `방향키`: 플레이어(Red) 로봇 직접 주행
  * `Space`: 안전 정지 (Emergency Stop)
  * `1`, `2`, `3`: 0, 1, 2번 퍽을 Blue 진영으로 푸시하는 자율 궤적 테스트
  * `0`: 홈 기지(100, 200)로 복귀
  * `R`: 경기장 및 퍽 리셋
  * `ESC`: 종료

### 3. 물리 엔진 및 시뮬레이션 단위 테스트
```bash
pytest tests/test_simulation_physics.py
```

---

## 📁 디렉터리 구조 및 파일별 역할

```text
PromptBot-Arena/
├── docs/                             # 프로젝트 문서 및 설계 사양 (SSOT 원칙 관리)
│   ├── proposal.md                   # 종합설계 II 정식 제안서 (연구 배경 및 차별점, 불변 기준)
│   ├── overview.md                   # 시스템 아키텍처, Action Primitives API 명세, 물리 규격
│   ├── todo.md                       # 앞으로 진행할 작업 백로그 (Backlog)
│   ├── progress.md                   # 완료된 작업 상세 내역 및 변경 일지 (Work Done)
│   └── presentation_guide.md         # 주간 발표 PPT 제작 지침서 (요청 시에만 열람)
├── src/                              # 핵심 소스 코드
│   ├── core/                         # 시뮬레이터와 실물 로봇이 100% 공유하는 코어 모듈
│   │   ├── models.py                 # 핵심 데이터 모델 (Puck, State, ActionCommand, ActionType)
│   │   ├── interfaces.py             # 추상 인터페이스 (BaseRobot, BaseVision, BaseAgent)
│   │   ├── primitives.py             # 표준 Action Primitives (push, move_to, stop, will_collide 등)
│   │   └── agents.py                 # 제어 주체 캡슐화 (CodePolicyAgent, ManualActionAgent)
│   └── simulation/                   # 2D Digital Twin 가상 물리 시뮬레이터
│       ├── physics.py                # 2륜 차동 기구학 적분, 쿨롱 마찰, OBB 및 V-범퍼 접촉 물리
│       ├── robot_sim.py              # BaseRobot 구현체 (60 FPS 저수준 궤적 추종기 및 Safe Stop)
│       ├── vision_sim.py             # BaseVision 구현체 (0.5초 주기 State 추출기)
│       └── arena_sim.py              # Pygame 2D 렌더러, 경기 HUD 대시보드 및 메인 게임 루프
├── scripts/                          # 실행 및 사용자 인터랙션 스크립트
│   ├── test_sim_keyboard.py          # 키보드 직접 조작 및 에이전트 전환(수동 API / 자율 코드) 테스트
│   └── run_cli_control.py            # 터미널 실시간 텍스트 API 제어 콘솔 (대화형 REPL)
├── tests/                            # pytest 자동화 단위/통합 테스트 스위트 (18종)
│   ├── test_simulation_physics.py    # 기구학 및 강체 접촉 물리 연산 테스트 (7종)
│   ├── test_action_primitives.py     # Action Primitives 및 will_collide 외삽 테스트 (6종)
│   └── test_agents.py                # 에이전트 캡슐화 및 시뮬레이터 연동 테스트 (5종)
├── requirements.txt                  # 파이썬 의존성 패키지 목록
├── .env.example                      # LLM API 키 환경 변수 템플릿
├── .gitignore                        # Git 추적 제외 목록
└── README.md                         # 프로젝트 대문 및 전체 파일 구조 안내
```
