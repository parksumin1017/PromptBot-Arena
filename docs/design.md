# System Technical Design Specification: PromptBot Arena

본 문서는 **프롬프트 봇 아레나(PromptBot Arena)** 프로젝트의 물리 엔진, 기구학, 궤적 생성 알고리즘, Action Primitives API, 보안 샌드박스 및 소프트웨어-하드웨어 결합 구조에 관한 **엄밀한 엔지니어링 설계 명세서**입니다.

모든 소스 코드 구현은 본 문서에 명시된 수학적 모델, 상태 전이 규칙, 파라미터 규격을 오차 없이 준수해야 하며, 본 문서에 합의되지 않은 임의의 휴리스틱 수치나 비인가 모듈의 추가를 엄격히 금지합니다.

---

## 1. 시스템 계층 구조 및 역할 분리 (System Architecture)

본 시스템은 **2단계 계층적 실행 구조(Hierarchical Two-tier Architecture)**와 **소프트웨어-하드웨어 완전 분리(Software-Hardware Decoupling)** 원칙을 따릅니다.

```text
[ 1단계: 관측 데이터 생성 (Observation Layer) ]
  • 가상 환경: SimulatedVision (ArenaPhysics 물리 상태 읽기)
  • 실물 환경: WebcamVision (탑뷰 웹캠 OpenCV HSV LED 트래킹)
        │
        ▼ (동일한 State 데이터 객체 생성: my_pos, my_theta, opp_pos, pucks)
[ 2단계: 전술 판단 계층 (Tactical Layer, 2 Hz / 0.5초 주기) ]
  • 정책 함수 실행: policy_step(state) -> ActionCommand
      - 파이썬 정책 스크립트 (작성 주체가 인간이든 LLM이든 시스템 입장에서는 완전히 동일한 파이썬 스크립트)
      - (또는 대화형 CLI 환경에서는 사용자가 터미널에 입력한 즉시 명령)
        │
        ▼ policy_step(state) 실행
     Action Primitives API 호출 (push, move_to, stop)
        │
        ▼ (push, move_to 내부에서 Cubic Hermite 3차 곡선 보간)
     향후 0.5초간 30개 웨이포인트(속도 v, 각속도 omega) 생성
        │
        ▼ will_collide 사전 충돌 예측 (위험 시 속도 0 Safe Stop)
     ActionCommand (0.5초 주행 프로파일)
        │
        ▼
[ 3단계: 저수준 실행 계층 (Execution Layer, 60 FPS / 16.6ms 주기) ]
  0.5초 궤적의 30개 속도 명령 (v_k, omega_k)을 매 16.6ms마다 순차 실행:
  • 실물 하드웨어: PC가 매 스텝 속도 명령을 ESP32에 무선 전송 (로봇 모터 구동)
  • 가상 시뮬레이터: 물리엔진(ArenaPhysics)이 매 스텝 속도를 기구학/충돌 역학에 반영하여 수치 적분
```

### 1.1 계층별 주기 및 인터페이스 규격

1. **전술 판단 주기 (Tactical Horizon, $T_H = 0.5\text{ s}$, $f = 2\text{ Hz}$)**:
   - 정책 함수 `policy_step(state: State) -> ActionCommand`가 0.5초마다 1회 호출됩니다.
   - **스크립트의 동일성**: 정책 코드는 작성 주체(인간 개발자 vs LLM)와 무관하게 시스템 관점에서는 **완전히 동일한 파이썬 스크립트 객체(`Callable[[State], ActionCommand]`)**입니다.
   - **실행 시간 및 타임아웃(Watchdog)**: 정상적인 정책 연산은 $1\text{ ms}$ 내외로 종료되며, 무한 루프(`while True` 등)로 인한 시스템 먹통을 방지하기 위해 런타임 타임아웃(Watchdog)은 **$100\text{ ms}$**로 강제 차단됩니다.
   - **ActionCommand의 역할**: 정책 작성자는 고수준 명령(`return push(...)` 또는 `return move_to(...)`)을 반환하며, 반환된 `ActionCommand` 객체 내부에는 저수준 제어기가 60 FPS로 바퀴에 바로 인가할 수 있도록 계산된 향후 0.5초간의 30개 속도 시계열 $[(v_1, \omega_1), \dots, (v_{30}, \omega_{30})]$이 캡슐화되어 담깁니다.

2. **저수준 실행 주기 (Control Step, $\Delta t = 1/60\text{ s} \approx 16.67\text{ ms}$, $f = 60\text{ Hz}$)**:
   - `ActionCommand`에 담긴 30개의 $(v_k, \omega_k)$ 속도 명령은 매 16.6ms마다 하나씩 소비됩니다.
   - **실물 환경**: PC 제어기가 매 스텝의 $(v_k, \omega_k)$를 ESP32에 무선 패킷(ESP-NOW/UDP)으로 전송하며, ESP32는 모터 PWM으로 변환하여 바퀴를 구동합니다. (로봇 하드웨어는 위치를 적분하지 않으며 순수 속도 추종만 수행합니다).
   - **시뮬레이터 환경**: 물리 엔진(`ArenaPhysics`)이 해당 스텝의 $(v_k, \omega_k)$를 받아 2륜 차동 기구학 및 충돌 반발 역학을 60 FPS로 **수치 적분(Numerical Integration)**하여 가상 로봇의 새 위치를 계산합니다.
   - **Receding Horizon Control (RHC)** 원칙에 따라, 로봇은 매 0.5초마다 새로 관측된 `State`를 바탕으로 계산된 최신 0.5초 궤적을 덮어써 실행하므로 누적 오차가 보정됩니다.

### 1.2 모듈별 단일 책임 원칙 (Single Responsibility Principle)

| 모듈 | 책임 및 상태 소유 (Ownership) | 금지 사항 |
|:---|:---|:---|
| **`State`, `Puck`** | 매 0.5초마다 비전 인터페이스(`BaseVision`)가 측정한 로봇 및 퍽의 위치·각도 좌표를 담은 **읽기 전용 데이터(Read-only)**. | 내부 계산 로직 보유 금지, 외부에서 필드 값 임의 수정(`state.my_pos = ...`) 금지 |
| **`BaseRobot`** | 순수 모터 액추에이터 인터페이스 (`send_velocity(v, omega)`, `stop()`). 실물 ESP32 또는 시뮬레이션 로봇에 대응. | 위치/각도 $(x, y, \theta)$ 저장 금지, 자체 기구학 적분 금지 |
| **`BaseVision`** | 경기장 관측 추상 인터페이스 (`get_state() -> State`).<br>• 가상: `SimulatedVision` (ArenaPhysics에서 추출)<br>• 실물: `WebcamVision` (HSV 웹캠 트래킹) | 로봇 구동 명령 전송 금지 |
| **`ArenaPhysics`** | **시뮬레이션 전용 단일 진실 공급원(Single Source of Truth)**. 모든 엔티티의 실제 좌표 및 충돌 역학 소유. | 사용자 정책 코드(`policy_step`)에 직접 노출 금지 |
| **`push`, `move_to`**| `Action Primitives`의 이동 함수. 내부에서 Cubic Hermite Spline을 사용하여 부드러운 30-step 속도 프로파일을 생성. | 임의의 if-else 좌표 하드코딩 금지 |

---

## 2. 물리 제원 및 파라미터 명세 (Physical Specification)

모든 단위는 **$\text{mm}$, $\text{s}$, $\text{rad}$, $\text{kg}$** 표준 단위를 사용합니다.

### 2.1 경기장 규격 (Arena Geometry)
- **내경 크기**: 가로 $W = 600.0\text{ mm}$, 세로 $H = 400.0\text{ mm}$
- **좌표계**: 좌상단 원점 $(0, 0)$, 우하단 $(600, 400)$
  - $x$축: $0 \to 600$ (Red 진영 $\to$ Blue 진영 방향)
  - $y$축: $0 \to 400$ (상단 벽 $\to$ 하단 벽 방향)
  - 각도 $\theta$: $x$축 양의 방향($\to$) 기준 $0\text{ rad}$, 반시계 방향이 양(+)의 각도 ($-\pi \le \theta \le \pi$)
- **진영 분할**:
  - 중앙선: $x_{\text{mid}} = 300.0\text{ mm}$
  - Red 진영 (플레이어): $0.0 \le x < 300.0$
  - Blue 진영 (보스/상대): $300.0 \le x \le 600.0$
- **외벽**: 높이 $60.0\text{ mm}$, 반발계수 $e_{\text{wall}} = 0.5$, 마찰계수 $\mu_{\text{wall}} = 0.3$

### 2.2 로봇 플랫폼 제원 (Robot Specifications)
- **외형**: 가로 $50.0\text{ mm} \times$ 세로 $50.0\text{ mm} \times$ 높이 $50.0\text{ mm}$ (정육면체)
- **질량**: $M_{\text{robot}} = 0.150\text{ kg}$ ($150\text{ g}$)
- **기준점 (`pos`)**: 로봇 두 구동 바퀴의 기구학적 회전 중심축 $(x_c, y_c)$
- **구동 한계**:
  - 최대 선속도: $v_{\max} = 150.0\text{ mm/s}$
  - 최대 각속도: $\omega_{\max} = \pi\text{ rad/s} \approx 3.1416\text{ rad/s}$
  - 최대 가속도: $a_{\max} = 300.0\text{ mm/s}^2$
  - 최대 각가속도: $\alpha_{\max} = 2\pi\text{ rad/s}^2 \approx 6.2832\text{ rad/s}^2$
- **전면 V자 범퍼 기하 구조**:
  - 외측 끝단 (폭 $50.0\text{ mm}$): 회전 중심 기준 전방 $+25.0\text{ mm}$
  - 중앙 포집 홈: 회전 중심 기준 전방 $+15.0\text{ mm}$ (홈 깊이 $10.0\text{ mm}$)
  - 범퍼 포집 각도: $\pm 30^\circ$ 경사각 형성

### 2.3 퍽 제원 (Puck Specifications)
- **외형**: 원통형 실린더, 지름 $D = 20.0\text{ mm}$ (반지름 $R_{\text{puck}} = 10.0\text{ mm}$)
- **질량**: $M_{\text{puck}} = 0.010\text{ kg}$ ($10\text{ g}$)
- **바닥 마찰**: 쿨롱 마찰 모델 $\mu_{\text{floor}} = 0.20$, 감쇠 가속도 $a_{\text{drag}} = \mu_{\text{floor}} g \approx 1960.0\text{ mm/s}^2$
- **반발계수**: 로봇-퍽 충돌 $e_{\text{puck}} = 0.30$

### 2.4 안전 여유 및 충돌 판정 기준 (Safety Margins)
- **로봇 - 로봇 충돌 반경**:
  - 로봇 외접원 반지름: $R_{\text{robot\_circum}} = \sqrt{25^2 + 25^2} \approx 35.36\text{ mm}$
  - 안전 정지 임계 거리: $D_{\text{robot-robot}} = 55.0\text{ mm}$ (외접원 2개 접촉 시 $70.7\text{ mm}$ 대비 모서리 회전 고려 보수적 기준)
- **로봇 - 퍽 충돌 반경 (비접촉 이동 시)**:
  - 안전 정지 임계 거리: $D_{\text{robot-puck}} = 38.0\text{ mm}$ (로봇 중심-외벽 $25\text{ mm}$ + 퍽 반지름 $10\text{ mm}$ + 안전 버퍼 $3\text{ mm}$)
- **로봇 - 경기장 외벽 안전 거리**:
  - 벽면 접근 한계: $D_{\text{robot-wall}} = 27.0\text{ mm}$ (로봇 반폭 $25\text{ mm}$ + 여유 $2\text{ mm}$)

---

## 3. 이동 명령(`push`, `move_to`) 내부의 곡선 궤적 보간 공식: Cubic Hermite Spline

### 3.1 개념 및 적용 범위 (Definition & Scope)
* **적용 범위**: **오직 `move_to`와 `push` 함수 내부에서만 사용**됩니다. (`stop`은 속도 0을 반환하므로 곡선 연산 불필요)
* **도입 배경 및 개념**:
  * 2륜 차동 구동 로봇은 각도가 틀어져 있을 때 제자리 회전 후 직진하는 식의 뚝뚝 끊기는 방식을 쓰면 채터링과 각도 오차 누적(데드락)이 발생합니다.
  * 따라서 자동차가 핸들을 매끄럽게 돌리며 차선을 변경하듯, **"시작 위치 + 시작 헤딩각"**에서 **"목표 위치 + 도착 시 헤딩각"**까지 부드럽게 이어지는 곡선을 그릴 수 있는 표준 보간 기법인 **3차 에르미트 스플라인(Cubic Hermite Spline)**을 사용합니다.

### 3.2 3차 에르미트 스플라인 수식 (Mathematical Formulation)

시작점 $P_0 = (x_0, y_0)$에서의 시작 진행 방향 벡터를 $M_0$, 목표점 $P_1 = (x_1, y_1)$에서의 목표 진행 방향 벡터를 $M_1$이라 할 때, 정규화된 매개변수 $s \in [0, 1]$에 대한 2차원 좌표 곡선 $P(s)$는 다음과 같습니다.

$$P(s) = h_{00}(s) P_0 + h_{10}(s) M_0 + h_{01}(s) P_1 + h_{11}(s) M_1$$

기저 함수(Basis functions):
$$\begin{aligned}
h_{00}(s) &= 2s^3 - 3s^2 + 1 \\
h_{10}(s) &= s^3 - 2s^2 + s \\
h_{01}(s) &= -2s^3 + 3s^2 \\
h_{11}(s) &= s^3 - s^2
\end{aligned}$$

접선 벡터(속도 방향) $P'(s) = \frac{dP}{ds}$:
$$P'(s) = (6s^2 - 6s) P_0 + (3s^2 - 4s + 1) M_0 + (-6s^2 + 6s) P_1 + (3s^2 - 2s) M_1$$

### 3.2 Action Primitive별 경계 조건 (Boundary Conditions)

#### 1) `move_to(target)`
- **시작 조건**:
  - $P_0 = (x_{\text{robot}}, y_{\text{robot}})$
  - $M_0 = L \cdot (\cos\theta_{\text{robot}}, \sin\theta_{\text{robot}})$, 여기서 스케일 $L = \|P_1 - P_0\|$
- **종료 조건**:
  - $P_1 = (x_{\text{target}}, y_{\text{target}})$
  - $M_1 = L \cdot \frac{P_1 - P_0}{\|P_1 - P_0\|}$ (목표점을 향해 부드럽게 진입)

#### 2) `push(puck, target)`
- **푸시 방향 단위 벡터**:
  $$\vec{u}_{\text{push}} = \frac{P_{\text{target}} - P_{\text{puck}}}{\|P_{\text{target}} - P_{\text{puck}}\|}, \quad \theta_{\text{push}} = \text{atan2}(u_{\text{push}, y}, u_{\text{push}, x})$$
- **V-범퍼 포집 접촉점 ($P_{\text{contact}}$)**:
  - 퍽 중심 $P_{\text{puck}}$에서 푸시 반대 방향으로 $d_{\text{contact}} = 25.0\text{ mm}$ (범퍼 홈 깊이 $15\text{ mm}$ + 퍽 반경 $10\text{ mm}$) 떨어진 지점:
  $$P_{\text{contact}} = P_{\text{puck}} - d_{\text{contact}} \cdot \vec{u}_{\text{push}}$$
- **2단계 복합 궤적 생성**:
  1. **접근 구간 (Approach Phase)**: $P_0(현재 로봇) \to P_{\text{contact}}$, 끝단 접선 벡터는 반드시 $\vec{u}_{\text{push}}$와 일치 ($M_1 = L_1 \cdot \vec{u}_{\text{push}}$).
  2. **밀기 구간 (Push Phase)**: $P_{\text{contact}} \to P_{\text{puck}} \to P_{\text{target}}$, 직선 또는 완만한 호를 그리며 퍽을 목표 지점으로 압송.

### 3.3 2륜 차동 기구학 역변환 및 프로파일링 (Kinematics & Profiling)

스플라인 곡선 상에서 0.5초 동안 진행할 호의 길이 $S_{\text{horizon}} = \min(L_{\text{total}}, v_{\max} \cdot T_H) \le 75.0\text{ mm}$를 산출합니다.

이를 $\Delta t = 1/60\text{ s}$ 간격의 30개 이산 스텝으로 분할하여 각 스텝 $k \in \{1, \dots, 30\}$에 대해:
1. 곡선 상의 위치 $(x_k, y_k)$ 및 접선 각도 $\theta_k = \text{atan2}(P'_y(s_k), P'_x(s_k))$ 추출.
2. 각속도 $\omega_k = \frac{\theta_k - \theta_{k-1}}{\Delta t}$ 계산 (단, $|\omega_k| \le \omega_{\max}$ 클리핑).
3. 선속도 $v_k = \frac{\|P(s_k) - P(s_{k-1})\|}{\Delta t}$ 계산 (단, $v_k \le v_{\max}$ 클리핑).
4. 좌/우 휠 속도 변환 ($W_{\text{tread}} = 40.0\text{ mm}$):
   $$v_{L, k} = v_k - \frac{\omega_k W_{\text{tread}}}{2}, \quad v_{R, k} = v_k + \frac{\omega_k W_{\text{tread}}}{2}$$

---

## 4. 기하학적 엣지 케이스 및 예외 처리 정책 (Edge Cases Policy)

### 4.1 Case A: 급격한 접근각 (Obtuse/Perpendicular Angle)
- **발생 조건**:
  - 로봇 위치 $P_{\text{robot}}$, 퍽 위치 $P_{\text{puck}}$, 목표 위치 $P_{\text{target}}$에 대해:
  - 푸시 단위 벡터: $\vec{u}_{\text{push}} = \frac{P_{\text{target}} - P_{\text{puck}}}{\|P_{\text{target}} - P_{\text{puck}}\|}$
  - 로봇$\to$퍽 벡터: $\vec{v}_{\text{rp}} = \frac{P_{\text{puck}} - P_{\text{robot}}}{\|P_{\text{puck}} - P_{\text{robot}}\|}$
  - 두 벡터의 내적 $\vec{v}_{\text{rp}} \cdot \vec{u}_{\text{push}} < \cos(60^\circ) = 0.5$ (즉, 각도 차이가 $60^\circ$를 초과하거나 로봇이 퍽의 전면/측면에 있어 직진 시 퍽을 엉뚱한 방향으로 칠 위험이 있는 경우).

- **$P_{\text{via}}$ (우회 경유점) 산출 수식**:
  1. **푸시 법선 단위 벡터(좌측 수직 방향)**:
     $$\vec{n}_{\text{push}} = (-u_{\text{push}, y}, u_{\text{push}, x})$$
  2. **로봇의 현재 횡방향 위치(Side) 판별**:
     $$d_{\text{side}} = (P_{\text{robot}} - P_{\text{puck}}) \cdot \vec{n}_{\text{push}}$$
     $$s = +1 \quad (\text{if } d_{\text{side}} \ge 0), \quad s = -1 \quad (\text{if } d_{\text{side}} < 0)$$
  3. **경유점 $P_{\text{via}}$ 좌표 계산**:
     - 횡방향 이격 거리: $R_{\text{lat}} = R_{\text{robot}} + R_{\text{puck}} + \text{buffer} = 25 + 10 + 10 = 45.0\text{ mm}$
     - 종방향 후방 거리: $d_{\text{long}} = 15.0\text{ mm}$
     $$P_{\text{via}}(s) = P_{\text{puck}} - d_{\text{long}} \vec{u}_{\text{push}} + s \cdot R_{\text{lat}} \vec{n}_{\text{push}}$$

- **벽면 간섭 검증 및 반대쪽 우회(Fallback)**:
  - 경기장 안전 영역: $x \in [27.0, 573.0]\text{ mm}, \; y \in [27.0, 373.0]\text{ mm}$
  - 만약 $P_{\text{via}}(s)$가 안전 영역을 침범하면, 반대편 $P_{\text{via}}(-s)$를 검사하여 안전하면 반대 방향으로 우회합니다.
  - 양쪽 모두 벽면에 막혀 있을 경우(코너 구석), 퍽 우회 경로 생성이 불가능하므로 무리한 주행을 차단하고 `ActionCommand.is_safe = False`로 설정하여 즉시 **제자리 정지(Safe Stop)**합니다.

### 4.2 Case B: 벽면 밀착 퍽 (Wall-stuck Puck)
- **상황**: 퍽 중심과 4면 외벽 사이의 수직 거리가 $d_{\text{wall}} < 35.0\text{ mm}$인 경우 (로봇 폭 $50\text{ mm}$의 반폭 $25\text{ mm} +$ 퍽 반경 $10\text{ mm} = 35\text{ mm}$이므로 로봇이 퍽과 벽 사이에 들어갈 물리적 공간이 없음).
- **공식 정책**:
  - 벽면 뒤로의 진입을 시도하지 않습니다.
  - **비스듬한 긁어내기 (Scraping Push)**: 벽면과 평행한 접선 방향 성분으로 $P_{\text{target}}$을 자동 투영하여 벽면을 따라 퍽을 긁어내 중앙 열린 공간으로 유도합니다.
  - 만약 지정된 목표 지점이 벽면을 향하고 있다면 밀기가 원천 불가능하므로 무리한 구동을 중단하고 `Safe Stop`을 반환합니다.

### 4.3 Case C: 충돌 위험 감지 및 세이프 스톱 (Collision Guard & Safe Stop)
- **상황**: 생성된 30-step 궤적 상의 임의의 시점 $t_k \in [0, 0.5\text{ s}]$에서:
  1. 상대 로봇의 현재 위치 $P_{\text{opp}}$와 속도 벡터 $\vec{v}_{\text{opp}}$를 선형 외삽한 $P_{\text{opp}}(t_k) = P_{\text{opp}} + \vec{v}_{\text{opp}} \cdot t_k$와의 거리가 $D_{\text{robot-robot}} < 55.0\text{ mm}$인 경우.
  2. 푸시 대상 퍽 외의 다른 퍽과의 거리가 $D_{\text{robot-puck}} < 38.0\text{ mm}$인 경우.
- **공식 정책**:
  - `will_collide(action)`은 즉시 `True`를 반환합니다.
  - 해당 `ActionCommand`는 내부적으로 즉시 선속도 및 각속도를 0으로 설정하여 로봇을 **제자리에 정지(Safe Stop)**시키고 충돌 로그를 기록합니다.

---

## 5. Action Primitives API 명세 (Interface Specification)

### 5.1 데이터 모델 (Data Models)

```python
from dataclasses import dataclass
from typing import Tuple, List, Optional

@dataclass(frozen=True)
class Waypoint:
    x: float          # [mm]
    y: float          # [mm]
    theta: float      # [rad]
    v: float          # [mm/s]
    omega: float      # [rad/s]

@dataclass
class ActionCommand:
    command_type: str                  # 'push', 'move_to', 'stop'
    target: Tuple[float, float]        # 목표 좌표 (x, y) [mm]
    waypoints: List[Waypoint]          # 30-step 궤적 프로파일
    is_safe: bool = True               # 충돌 위험 여부 (False 시 Safe Stop)
    safe_stop_reason: Optional[str] = None
    target_puck_id: Optional[int] = None

@dataclass(frozen=True)
class Puck:
    id: int
    x: float
    y: float

    @property
    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @property
    def zone(self) -> str:
        return 'red' if self.x < 300.0 else 'blue'

@dataclass(frozen=True)
class State:
    my_pos: Tuple[float, float]        # (x, y) [mm]
    my_theta: float                    # [rad]
    opp_pos: Tuple[float, float]       # (x, y) [mm]
    opp_theta: float                   # [rad]
    opp_vel: Tuple[float, float]       # (vx, vy) [mm/s]
    pucks: List[Puck]                  # 길이 3의 리스트
    match_time: float                  # [s] (0.0 ~ 60.0)
    my_team: str = 'red'               # 'red' 또는 'blue'
```

### 5.2 함수 시그니처 및 계약 (Function Contracts)

```python
def push(puck: Puck, target: Tuple[float, float]) -> ActionCommand:
    """
    선택한 퍽을 target 좌표로 보내기 위한 3차 에르미트 스플라인 궤적을 산출하고
    향후 0.5초(30 스텝)의 주행 프로파일을 반환합니다.
    내부에서 충돌 위험 검사를 수행하여 위험 시 Safe Stop 프로파일로 대체됩니다.
    """

def move_to(target: Tuple[float, float]) -> ActionCommand:
    """
    로봇 단독으로 target 좌표로 이동하는 3차 에르미트 스플라인 궤적을 산출하고
    향후 0.5초(30 스텝)의 주행 프로파일을 반환합니다.
    내부에서 충돌 위험 검사를 수행하여 위험 시 Safe Stop 프로파일로 대체됩니다.
    """

def stop() -> ActionCommand:
    """
    모든 속도를 0으로 인가하여 제자리에 즉각 정지하는 ActionCommand를 반환합니다.
    """

def will_collide(action: ActionCommand) -> bool:
    """
    전달받은 action이 0.5초 이내에 상대 로봇이나 다른 퍽과 충돌할 위험이 있어
    Safe Stop 상태에 돌입하는지 여부를 반환합니다 (action.is_safe == False).
    """

def get_dist(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """두 좌표 간의 2차원 유클리드 거리(mm)를 반환합니다."""

def get_closest_puck(pucks: List[Puck], to_pos: Tuple[float, float]) -> Puck:
    """to_pos 좌표에서 가장 거리가 가까운 Puck 1개를 반환합니다."""

def get_pucks_in_zone(pucks: List[Puck], zone: str = 'red') -> List[Puck]:
    """zone ('red' 또는 'blue')에 위치한 Puck 객체들의 리스트를 반환합니다."""
```

---

## 6. AST 보안 샌드박스 명세 (Security Sandbox Specification)

LLM이 생성한 Python 정책 코드가 시스템 자원을 침해하거나 무한 대기에 빠지는 것을 100% 차단합니다.

### 6.1 화이트리스트 노드 검사 (`ast.NodeVisitor`)
- **허용 AST 노드**:
  - 모듈 및 함수: `Module`, `FunctionDef`, `arguments`, `arg`, `Return`
  - 제어문: `If`, `Pass` (단, `While`, `For`는 무한루프 위험으로 기본 차단하거나 최대 루프 카운터 강제)
  - 연산식: `Assign`, `Name`, `Load`, `Store`, `Constant`, `Tuple`, `List`, `Compare`, `BoolOp`, `BinOp`, `UnaryOp`
  - 함수 호출: `Call` (단, 호출 대상 `func`은 사전 인가된 빌트인 함수 목록으로 한정)
- **절대 차단 목록 (즉시 거부 및 예외 발생)**:
  - `Import`, `ImportFrom` (모든 외부 라이브러리 로드 금지)
  - `Attribute` 접근 중 `__` (더블 언더스코어 던더 속성 접근 원천 차단)
  - 시스템 내장 함수: `eval`, `exec`, `open`, `compile`, `globals`, `locals`, `getattr`, `setattr`, `delattr`
  - 무한루프 유발 가능 구문: `while True`, 재귀 함수 호출

### 6.2 실행 타임아웃 샌드박스 (Watchdog Execution)
- 정책 함수는 `policy_step(state)` 단일 함수로 제한됩니다.
- 실행 타임아웃은 **$100\text{ ms}$**로 엄격히 제한되며, 시간 초과 시 `TimeoutError`를 발생시키고 로봇은 `stop()` 상태를 유지합니다.

---

## 7. 소프트웨어-하드웨어 결합 검증 계획 (Validation & Parity)

1. **시뮬레이션-하드웨어 1:1 패리티**:
   - `TrajectoryPlanner` 및 `primitives.py`는 시뮬레이터와 실물 로봇 PC 노드에서 **단 1바이트의 차이도 없이 동일한 코드**로 구동됩니다.
   - 가상 환경에서 검증된 `policy_step` 코드는 실물 환경에서 재컴파일이나 수정 없이 즉시 작동합니다.
2. **정량적 검증 기준 (Proposal 2.2장 연동)**:
   - 궤적 계산 지연: $1\text{ ms}$ 이하
   - AST 분석 차단율: 인가되지 않은 시스템 호출에 대해 $100\%$ 차단
   - 60초 무교착 완주율: 30회 연속 시뮬레이션 테스트에서 $95\%$ 이상 달성

---

## 8. 프로젝트 파일 및 디렉터리 구조 명세 (Project File Structure)

모든 소스 코드는 아래에 명시된 파일 구조와 단일 책임 원칙을 엄격히 따라야 하며, 명세되지 않은 임의의 파일이나 모듈을 생성할 수 없습니다.

```text
project/
├── docs/                               # 프로젝트 기획 및 기술 문서 (Markdown)
│   ├── overview.md                     # 시스템 개요 및 정량 지표 명세
│   ├── proposal.md                     # 연구 제안서
│   ├── design.md                       # 기술 설계 명세서 (본 문서)
│   ├── progress.md                     # 개발 진행 상황 보고서
│   └── todo.md                         # 주차별 백로그 및 작업 목록
│
├── src/                                # 핵심 소스 코드
│   ├── core/                           # 플랫폼 비종속 코어 (가상/실물 100% 공용)
│   │   ├── __init__.py
│   │   ├── models.py                   # State, Puck, Waypoint, ActionCommand (불변 데이터 객체)
│   │   ├── interfaces.py               # BaseRobot, BaseVision, BaseAgent (추상 베이스 클래스)
│   │   ├── trajectory.py               # Cubic Hermite Spline 보간 및 30-step 프로파일 생성
│   │   ├── primitives.py               # push, move_to, stop, will_collide 등 표준 Action API
│   │   └── security.py                 # AST NodeVisitor 화이트리스트 검사 및 Watchdog 타임아웃
│   │
│   ├── simulation/                     # 2D Digital Twin 가상 환경 모듈
│   │   ├── __init__.py
│   │   ├── physics.py                  # ArenaPhysics (강체 물리, 차동 기구학, 60 FPS 수치 적분)
│   │   ├── robot_sim.py                # SimulatedRobot(BaseRobot 상속, 물리엔진 속도 전달)
│   │   ├── vision_sim.py               # SimulatedVision(BaseVision 상속, 물리엔진 관측 State 생성)
│   │   └── arena_sim.py                # ArenaSimulator (Pygame 렌더러 및 60 FPS 제어 루프 구동)
│   │
│   ├── hardware/                       # 실물 하드웨어 연동 모듈 (Week 4 이후 구현)
│   │   ├── __init__.py
│   │   ├── esp32_robot.py              # PhysicalRobot(BaseRobot 상속, 무선 패킷 송신)
│   │   └── webcam_vision.py            # WebcamVision(BaseVision 상속, 탑뷰 HSV LED 트래커)
│   │
│   └── strategies/                     # 정책 스크립트 모음
│       ├── __init__.py
│       ├── sample_policy.py            # 기본 플레이어 예시 전략 (def policy_step(state))
│       └── boss/                       # 1~10단계 적응형 상대 보스 정책 스크립트
│
├── scripts/                            # 실행 스크립트
│   └── run_sim.py                      # 시뮬레이터 실행 진입점 (지정된 정책 간 경기 구동)
│
├── tests/                              # 정량 지표 검증 단위/통합 테스트
│   ├── test_primitives.py              # Action Primitives 입출력 규격 및 계약 검증
│   ├── test_trajectory.py              # Hermite Spline 속도/각속도 물리 한계 검증
│   ├── test_security.py                # AST 샌드박스 비인가 API 차단 100% 검증 (30회 테스트)
│   └── test_physics.py                 # 충돌 반발 및 60초 무교착 시뮬레이션 검증
│
├── requirements.txt                    # 필수 의존성 라이브러리 목록
└── README.md                           # 프로젝트 소개 및 실행 가이드
```

### 8.1 파일별 세부 역할 및 의존 관계 (Dependencies)

| 파일 경로 | 소속 계층 | 주요 클래스 / 함수 | 허용 의존성 (Imports) |
|:---|:---|:---|:---|
| `src/core/models.py` | Core Data | `Puck`, `State`, `Waypoint`, `ActionCommand` | `dataclasses`, `typing` (표준 라이브러리만 허용) |
| `src/core/interfaces.py`| Core Abstract | `BaseRobot`, `BaseVision`, `BaseAgent` | `abc`, `typing`, `src.core.models` |
| `src/core/trajectory.py`| Core Math | `generate_hermite_spline`, `sample_trajectory_profile` | `math`, `typing`, `src.core.models` |
| `src/core/primitives.py`| Core API | `push`, `move_to`, `stop`, `will_collide`, `get_dist` 등 | `math`, `typing`, `src.core.models`, `src.core.trajectory` |
| `src/core/security.py`  | Core Security | `ASTSecurityValidator`, `run_with_timeout` | `ast`, `typing`, `threading` |
| `src/simulation/physics.py` | Sim Physics | `ArenaPhysics` | `math`, `typing`, `numpy` |
| `src/simulation/robot_sim.py` | Sim Actuator | `SimulatedRobot(BaseRobot)` | `src.core.interfaces`, `src.simulation.physics` |
| `src/simulation/vision_sim.py`| Sim Observer | `SimulatedVision(BaseVision)` | `src.core.interfaces`, `src.core.models`, `src.simulation.physics` |
| `src/simulation/arena_sim.py` | Sim Loop/UI | `ArenaSimulator` | `pygame`, `src.core.*`, `src.simulation.*` |

