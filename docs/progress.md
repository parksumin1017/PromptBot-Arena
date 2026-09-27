# Project Progress: 프롬프트 봇 아레나 (PromptBot Arena)

> **프로젝트 기간**: 2026년 2학기 (Week 1 ~ Week 15)  
> **최종 갱신일**: 2026-09-27  
> **현재 단계**: Week 1 (시스템 환경 구축 및 가상 시뮬레이터/CaP 코어 설계)

---

## 📌 마일스톤 개요 (Milestone Roadmap)

| 주차 | 기간 | 주요 목표 | 상태 |
|:---|:---|:---|:---:|
| **Week 1** | 9월 4주 | 로컬 환경 셋업, 2D 시뮬레이터 뼈대, AST 보안 파서 및 CaP 프롬프트 템플릿 설계 | 🟡 진행 중 |
| **Week 2~3** | 10월 1~2주 | 2D 시뮬레이터 완성, 웹캠 HSV 비전 알고리즘 검증, 하드웨어 부품 주문/조립 준비 | ⚪ 대기 |
| **Week 4~6** | 10월 3~5주 | 2륜 로봇 1차 조립, 무선 제어(ESP-NOW/UDP) 통신 안정화, CaP 기본 주행 연동 | ⚪ 대기 |
| **Week 7** | 10월 말 | **[중간 점검]** 하드웨어-비전-기초 CaP 통합 시연 ("공으로 가라" 등 자율 추적) | ⚪ 대기 |
| **Week 8~10** | 11월 초·중순 | 메인 배틀(Core Pusher) 완성, 1~10단계 적응형 보스 탑재, AST 샌드박스 완비 | ⚪ 대기 |
| **Week 11~13** | 11월 말·12월 초 | 60초 배틀 완주율(95%+) 및 판정 정확도(100%) 검증, 추가 배틀 모드 확장 | ⚪ 대기 |
| **Week 14** | 12/11 | **[최종 시연 Demo Day]** 2-로봇 실시간 피지컬 배틀 및 자연어 프롬프팅 최종 시연 | ⚪ 대기 |
| **Week 15** | 12/29 | Final Report 제출 및 최종 마무리 | ⚪ 대기 |

---

## 🚀 Week 1 진행 상황 (현재 주차: 2026-09-27 ~ )

### 1. 환경 및 형상 관리
- [x] 프로젝트 제안서(`docs/proposal.md`) 아카이빙
- [x] `.gitignore` 작성 (보안 토큰, 가상환경, 빌드 캐시 배제)
- [x] GitHub 연동 준비 (토큰 `.env` 안전 저장 및 로컬 설정)
- [x] Git 로컬 저장소 초기화 (`git init`) 및 첫 커밋 생성
- [ ] GitHub 원격 저장소(`origin`) 연동 및 push

### 2. 가상 시뮬레이터 (Digital Twin - 컴퓨터 한 대 개발용)
- [ ] Python 가상환경(`.venv`) 구성 및 의존성 패키지 설치 (`pygame`, `numpy`, `opencv-python` 등)
- [ ] 책상 경기장 규격(가로:세로 비율) 2D 시뮬레이션 창 렌더링
- [ ] 아군 로봇, 상대 로봇, 퍽(Puck) 3개 객체 모델링
- [ ] 2륜 차동 구동(Differential Drive) 기구학 ($v, \omega \to x, y, \theta$) 구현
- [ ] 경기장 벽면 및 퍽-로봇 간 기초 충돌/밀기 물리 엔진 구현

### 3. Code-as-Policies(CaP) 파이프라인
- [ ] Action Primitives 인터페이스 명세 확정 (`get_my_pose`, `get_puck_positions`, `move_to`, `push_to` 등)
- [ ] LLM 프롬프트 템플릿(System Prompt + Few-shot) 설계
- [ ] LLM API 연동 (Gemini / OpenAI 등) 및 파싱 레이어 구축

### 4. AST 보안 샌드박스
- [ ] `ast.NodeVisitor` 기반 문법 분석기 구현 (비인가 API, import, eval 차단)
- [ ] 30회 테스트 셋 대상 차단율 100% 검증 스크립트 작성
- [ ] 실행 타임아웃(Watchdog) 데코레이터 구현

---

## 📝 주간 변경 이력 (Changelog)

### [2026-09-27]
- 제안서 파일 `docs/` 디렉터리 구조로 정리
- 보안 설정(`.gitignore`, `.env`, `.env.example`) 구축
- 주간 진행 상황 추적 문서(`docs/progress.md`) 및 시스템 기술 사양서(`docs/overview.md`) 수립
