# System Specification & Architecture: PromptBot Arena

본 문서는 **프롬프트 봇 아레나(PromptBot Arena)** 프로젝트의 핵심 기술 명세, 시스템 아키텍처, Action Primitives API 표준, 개발 규칙을 정리한 공식 레퍼런스 문서입니다.

---

## 1. 프로젝트 핵심 개요

* **프로젝트명**: 프롬프트 봇 아레나 (PromptBot Arena)
* **목표**: 책상 위 경기장에 배치된 실물 로봇 2대와 컴퓨터가 연동되어, 플레이어가 **자연어 프롬프트만으로 로봇에게 전략을 지시**하여 상대 로봇(1~10단계 적응형 보스)을 단계별로 공략하는 피지컬 컴퓨팅 아레나 구축.
* **메인 게임 종목 (Core Pusher)**: 60초 제한시간 동안 경기장 중앙선($x=300\text{ mm}$) 너머 상대 진영으로 3개의 퍽을 더 많이 밀어 넣어 두는 팀이 승리 (골대 없음).
* **핵심 철학**:
  1. **No-Coding Mental Model**: 코드 문법 에러 디버깅이 아닌, 목표·우선순위·제약 조건을 구조화하는 고차원 프롬프팅 사고력 집중.
  2. **Dynamic Physical Feedback Loop**: 실물 로봇의 물리적 상호작용 및 실시간 승패를 통해 자연어 지시의 논리적 결함을 즉각 확인.
  3. **Code-as-Policies(CaP) 패러다임**: 자연어 $\to$ 실행 가능한 Python 정책 코드 자동 생성.

---

## 2. 정량적 검증 목표 (제안서 2.2장)

| 구분 | 평가 항목 | 목표 수치 | 검증 방법 |
|:---|:---|:---|:---|
| **실시간 센싱·제어** | 비전 트래킹 및 제어 루프 레이턴시 | • 비전 처리 **20 ms 이하 (60 FPS)**<br>• 무선 RTT **10 ms 이하** (손실률 0.5% 이하) | 웹캠 프레임 캡처부터 5개 객체 좌표 추출 및 로봇 제어 패킷 RTT 로그 |
| **LLM 파이프라인** | 정책 코드 변환 지연 및 안전성 | • 변환 지연 **5.0초 이하**<br>• 비인가 API 차단율 **100%** | 사용자 입력 후 스크립트 파싱 시간 및 30회 테스트 셋 AST 정적 분석 |
| **경기 구동 안정성** | 60초 배틀 무중단 완주율 | **95% 이상** | 30회 경기 중 크래시 및 교착(Deadlock) 없는 완주율 |
| **게임 룰 자동 판정** | 승패 및 구역 판정 정확도 | **100%** | 비전 기반 경기 종료 시 판정과 실제 물리 상태 일치율 |

---

## 3. 계층적 2단계 실행 아키텍처 (Hierarchical Loop)

채터링(고주파 진동)을 방지하고 무선 통신 부하를 최적화하기 위해, **고수준 전술 판단 주기**와 **저수준 물리 궤적 추종 주기**를 계층적으로 분리합니다.

```text
[ 1단계: 경기 시작 전 1회 (LLM 파이프라인) ]
사용자 자연어 지시 ──► LLM (CaP) ──► AST 보안 검증 ──► def policy_step(state) 함수 탑재

[ 2단계: 경기 진행 중 (계층적 실행 루프) ]
┌── [고수준 전술 판단] (0.5초 주기 / 2 Hz)
│     • 최신 센서 관측값(State)을 받아 policy_step(state) 실행 (1ms 이내)
│     • 0.5초 동안 수행할 모션 명령(ActionCommand: push 또는 move_to) 결정
│     ▼
└── [저수준 궤적 추종] (60 FPS / 매 16.6ms)
      • 하위 제어기(시뮬레이터 / ESP32 펌웨어)가 2륜 차동 기구학에 맞춘 곡선 궤적 실시간 추종
      • N20 모터 PWM 인가 및 물리 업데이트
```

---

## 4. 데이터 구조: `State` 및 `Puck`

```python
class Puck:
    """경기장 내 퍽 객체 (지름 40 mm)"""
    id: int          # 퍽 번호 (0, 1, 2)
    x: float         # x 좌표 (mm, 0 ~ 600)
    y: float         # y 좌표 (mm, 0 ~ 400)
    
    @property
    def pos(self) -> tuple[float, float]:
        """(x, y) 좌표 튜플 반환"""
        return (self.x, self.y)
        
    @property
    def zone(self) -> str:
        """현재 위치한 진영 ('red': x < 300, 'blue': x >= 300)"""
        return 'red' if self.x < 300.0 else 'blue'


class State:
    """0.5초마다 policy_step에 전달되는 실시간 센서 관측값"""
    my_pos: tuple[float, float]       # 내 로봇 회전 중심 좌표 (x, y) [mm]
    my_theta: float                   # 내 로봇 헤딩 각도 [rad] (0 rad: 우측 Blue 방향)
    
    opp_pos: tuple[float, float]      # 상대 로봇 회전 중심 좌표 (x, y) [mm]
    opp_theta: float                  # 상대 로봇 헤딩 각도 [rad]
    opp_vel: tuple[float, float]      # 상대 로봇의 현재 이동 속도 벡터 (vx, vy) [mm/s]
    
    pucks: list[Puck]                 # 필드 위 모든 퍽 리스트 (3개)
    match_time: float                 # 경기 경과 시간 (초, 0.0 ~ 60.0)
    my_team: str = 'red'              # 소속 팀 ('red' 또는 'blue')
```

---

## 5. Action Primitives API 명세 (표준 인터페이스)

### 5.1 모션 명령 (Action Commands)
로봇을 물리적으로 구동하는 명령입니다. **두 함수 모두 내부에서 충돌 위험을 자체 검사하며, 충돌 위험 시 제자리에 멈춰 서서(Safe Stop) 하드웨어를 보호합니다.**

* **`push(puck: Puck, target: tuple[float, float]) -> ActionCommand`**
  * **설명**: 해당 퍽을 목표 좌표(`target`)로 보내기 위한 최적의 곡선 궤적을 선행 계산하고, 첫 0.5초 동안 구동하는 공 제어 명령.
  * **내부 안전 검사 (Internal Safety Guard)**: 0.5초 주행 궤적 상에서 상대 로봇(속도 감안 시공간 교차 추돌)이나 다른 퍽과의 충돌 위험이 감지되면 즉시 **제자리에 멈춰 서서 대기(Safe Stop)**합니다.
  * **활용 예시**:
    * 상대 진영으로 밀기: `push(puck, target=(450, 200))`
    * 상단 벽으로 걷어내기: `push(puck, target=(puck.x, 0))`
    * 하단 벽으로 걷어내기: `push(puck, target=(puck.x, 400))`

* **`move_to(target: tuple[float, float]) -> ActionCommand`**
  * **설명**: 퍽 없이 로봇 혼자 목표 좌표(`target`)로 가장 부드럽게 도달하는 2륜 곡선 궤적을 계산하여 첫 0.5초 동안 주행하는 명령.
  * **내부 안전 검사**: 이동 궤적 상에 충돌 위험 감지 시 즉시 제자리에 멈춰 섭니다.
  * **활용 예시**:
    * 상대의 길목을 피해 사이드(`target=(150, 80)`)로 우회 이동할 때
    * 우리 진영 수비 위치(`target=(100, 200)`)로 복귀할 때

* **`stop() -> ActionCommand`**
  * **설명**: 모터를 즉시 정지시킵니다.

### 5.2 인지 및 사전 충돌 검사 (Perception & Pre-check)
* **`will_collide(action: ActionCommand) -> bool`**
  * **설명**: 전달받은 `action`(`push` 또는 `move_to`)을 실행할 경우, 향후 0.5초 동안 상대 로봇(이동 속도 벡터 외삽)이나 다른 퍽과 충돌할 위험이 있는지 사전에 판별합니다.
  * **반환값**: 충돌 위험으로 로봇이 멈춰 서게 될 상황이면 `True`, 안전하면 `False`.
  * **활용**: 로봇이 멈춰 서기 전에 사이드로 우회하거나 다른 퍽으로 타깃을 전환하는 조건문 분기에 사용.
* **`get_closest_puck(pucks: list[Puck], to_pos: tuple[float, float]) -> Puck`**
  * **설명**: 지정한 좌표(`to_pos`)에서 가장 가까운 퍽 1개를 찾아 반환합니다.
* **`get_pucks_in_zone(pucks: list[Puck], zone: str = 'red') -> list[Puck]`**
  * **설명**: 특정 진영(`zone`) 안에 위치한 퍽들의 목록을 반환합니다.
* **`get_dist(pos1: tuple[float, float], pos2: tuple[float, float]) -> float`**
  * **설명**: 두 좌표 간의 유클리드 거리(mm)를 반환합니다.

---

## 6. 하드웨어 및 능동 발광 LED 규격

* **경기장 (Arena)**:
  * 외경/내경 크기: **가로 600 mm × 세로 400 mm** (외벽 높이 **60 mm**, 골대 없음)
  * 좌표계 기준: 좌상단 $(0, 0)$ ~ 우하단 $(600, 400)$ [mm]
  * 중앙선: $x = 300\text{ mm}$
  * **Red 진영 (좌측)**: $0 \le x < 300$ (싱글 플레이어 기본 진영)
  * **Blue 진영 (우측)**: $300 < x \le 600$ (상대 보스 / 2P 진영)
* **로봇 기구부 (Robot)**:
  * 외형 치수: **50 mm × 50 mm × 50 mm** (초소형 큐브 플랫폼)
  * **위치 기준점 (`pos`)**: **로봇 큐브의 기구학적 회전 중심 (두 구동 바퀴의 중심축)**
  * 전면 구조: 퍽 포집용 V자형 가이드 범퍼 (회전 중심에서 전방 $+25\text{ mm}$ 돌출)
  * 구동계: N20 마이크로 기어 모터 2개 (ESP32 PWM 속도 제어)
* **능동 발광 LED 색상 규격 (탑뷰 비전 인식)**:
  * **Red 팀 (내 로봇)**: **빨강(전방) / 분홍(후방)** 투톤 고휘도 LED
  * **Blue 팀 (상대 로봇)**: **파랑(전방) / 하늘(후방)** 투톤 고휘도 LED
  * **퍽 (Puck)**: **흰색(White)** 고휘도 LED
* **제어 보드**: ESP32 계열 (무선 통신 연동)

---

## 7. 개발 및 코드 작성 규칙

1. **소프트웨어-하드웨어 추상화(Decoupling)**:
   * 모든 로직은 `Simulator`와 `PhysicalRobot`이 동일한 기본 인터페이스(`BaseRobot`, `BaseVision`)를 상속하도록 설계합니다.
   * 이렇게 함으로써 하드웨어가 없는 첫 주에도 시뮬레이터 환경에서 100% 동일한 제어 알고리즘을 완성할 수 있습니다.
2. **보안 우선 원칙 (AST & Secrets)**:
   * 절대 비밀 토큰이나 API 키를 소스 코드에 하드코딩하지 않습니다 (`.env` 활용).
   * LLM 생성 코드는 반드시 AST 정적 검사와 Watchdog 타임아웃을 거쳐 실행합니다.
