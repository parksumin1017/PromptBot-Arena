# To-Do List & Backlog: 프롬프트 봇 아레나 (PromptBot Arena)

본 문서는 **앞으로 진행해야 할 작업(할 일)**들을 우선순위와 주차별로 관리하는 백로그 문서입니다.  
작업이 완료되면 본 목록에서 삭제/체크 후, 상세 완료 내역은 [progress.md](docs/progress.md)에 기록합니다.

---

## 🔥 Week 1 최우선 작업 (컴퓨터 한 대 환경)

### 1. 가상환경 의존성 라이브러리 설치
- [ ] 핵심 패키지 설치 (`pygame`, `numpy`, `opencv-python`, `python-dotenv`)
- [ ] LLM 연동 패키지 설치 (`pydantic`, `google-genai`, `openai`)

### 2. 2D 가상 시뮬레이터(Digital Twin) 개발
- [ ] 책상 경기장 규격($600 \times 400\text{ mm}$, 외벽 $60\text{ mm}$) 2D 윈도우 생성 및 경계벽 렌더링
- [ ] 아군 로봇, 상대 로봇($50 \times 50\text{ mm}$), 퍽 3개 객체 모델링
- [ ] 2륜 차동 구동(Differential Drive) 기구학 모델링
- [ ] 로봇-벽면, 로봇-퍽 충돌 및 밀기(Push) 기초 물리 연산
- [ ] 키보드로 로봇을 직접 조작해보며 물리 반응 검증 스크립트 작성

### 3. Action Primitives & CaP 파이프라인
- [ ] 시뮬레이터 연동 표준 Action Primitives 구현
  - `get_my_pose()`, `get_opponent_pose()`, `get_puck_positions()`, `move_to()`, `push_to()`, `stop()`
- [ ] 시스템 프롬프트 및 Few-shot 예제 작성
- [ ] 자연어 입력 $\to$ `policy_step()` 파이썬 함수 생성 LLM 호출기 구현

### 4. AST 정적 분석 보안 샌드박스
- [ ] `ast.NodeVisitor` 기반 화이트리스트 검사기
  - 비인가 import, eval, exec, __builtins__, sys, os 원천 차단
- [ ] 무한루프 방지 실행 타임아웃(Watchdog) 데코레이터
- [ ] 30회 정상/악성 코드 테스트 셋 작성 및 차단율 100% 검증

---

## 📅 주차별 로드맵 (Upcoming Milestones)

### Week 2~3 (10월 초·중순)
- [ ] 웹캠 탑뷰 영상 캡처 및 HSV 능동 발광 LED 마스킹 알고리즘 구현
- [ ] 20 ms 이하(60 FPS) 고속 트래킹 연산 벤치마킹 및 튜닝
- [ ] 경기장 자재 및 로봇 부품 발주/수급

### Week 4~6 (10월 중·하순)
- [ ] 2륜 로봇 1차 조립 및 모터 드라이버 배선
- [ ] ESP32 무선 제어 통신(ESP-NOW/UDP) 안정화 (RTT 10 ms 이하 검증)
- [ ] 시뮬레이터에서 검증된 Action Primitives를 실물 로봇 모듈로 포팅

### Week 7 (10월 말 - 중간 점검)
- [ ] **[중간 점검 시연]**: 자연어 프롬프트("공으로 가라") $\to$ 실물 로봇의 자율 주행 및 추적 통합 시연

### Week 8~10 (11월 초·중순)
- [ ] Core Pusher(3개 퍽 진영 밀기) 메인 배틀 룰 엔진 완성
- [ ] 1~10단계 적응형 상대 보스 에이전트 전술 알고리즘 개발
- [ ] 단계별 승패에 따른 자동 난이도 승급 루프 구축

### Week 11~13 (11월 말·12월 초)
- [ ] 60초 배틀 완주율(95% 이상) 30회 연속 테스트 및 검증
- [ ] 비전 기반 승패 판정 정확도(100%) 검증
- [ ] 일정에 따라 추가 게임 모드(Core Striker, Core Guardian) 탑재

### Week 14~15 (12월)
- [ ] **[Week 14 Demo Day]**: 2-로봇 실시간 피지컬 배틀 및 프롬프팅 최종 실물 시연
- [ ] **[Week 15 Final Report]**: 정량 지표 데이터 분석 및 최종 보고서 작성
