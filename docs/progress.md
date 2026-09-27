# Work Progress: 프롬프트 봇 아레나 (PromptBot Arena)

본 문서는 **이미 수행하여 완료된 작업 내역(Work Done)**과 시스템 변경 이력을 누적 기록하는 작업 일지입니다.  
앞으로 진행할 작업(할 일) 목록은 [todo.md](docs/todo.md)를 참조합니다.

---

## 📊 작업 완료 내역 요약 (Summary of Completed Tasks)

| 완료일 | 항목 | 세부 내용 | 산출물 / 커밋 |
|:---|:---|:---|:---|
| **2026-09-27** | 프로젝트 구조화 및 문서 체계화 | `docs/` 폴더 분리, 제안서 복사, 사양서 및 진행 관리 문서 수립 | `docs/proposal.md`, `docs/overview.md`, `docs/todo.md`, `docs/progress.md` |
| **2026-09-27** | 물리 규격 명세화 | 경기장($600\times400\text{ mm}$, 외벽 $60\text{ mm}$) 및 로봇($50\times50\times50\text{ mm}$) 치수 확정 및 `overview.md` 반영 | `docs/overview.md` |
| **2026-09-27** | 보안 및 환경 설정 | Git 제외 파일(`.gitignore`) 작성 및 토큰/환경변수 분리 | `.gitignore`, `.env`, `.env.example` |
| **2026-09-27** | Git 형상 관리 및 원격 연동 | 로컬 저장소 초기화 및 GitHub 원격 저장소(`PromptBot-Arena`) 생성 및 동기화 완료 | [GitHub: parksumin1017/PromptBot-Arena](https://github.com/parksumin1017/PromptBot-Arena) |
| **2026-09-27** | 개발 환경 구성 | Anaconda 가상환경(`arena`, Python 3.11.16) 생성 완료 | Conda env `arena` |

---

## 📝 일자별 상세 작업 로그 (Daily Work Log)

### 2026년 9월 27일 (일) - 프로젝트 착수 및 환경 셋업

#### 1. 보안 및 환경 격리 설정
* GitHub Personal Access Token(PAT)을 로컬 환경 변수 파일([.env](file:///c:/Users/박수민/Desktop/종합설계II/.env))에 분리 저장.
* [.gitignore](file:///c:/Users/박수민/Desktop/종합설계II/.gitignore)를 작성하여 `.env`, `*.token`, 빌드 캐시 등이 원격에 유출되지 않도록 차단.
* 협업 및 클론용 환경변수 템플릿([.env.example](file:///c:/Users/박수민/Desktop/종합설계II/.env.example)) 생성.

#### 2. 프로젝트 문서 체계 정립 (SSOT 단일 진실 공급원 준수)
* [README.md](file:///c:/Users/박수민/Desktop/종합설계II/README.md): 프로젝트 대문 및 실행 가이드 (`conda activate arena`) 명시.
* [docs/proposal.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/proposal.md): 종합설계 II 제출 원본 제안서 아카이빙 (불변 기준 문서).
* [docs/overview.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/overview.md): 시스템 기술 사양서 (Action Primitives API 명세, $600\times400\text{ mm}$ 경기장, $50\times50\times50\text{ mm}$ 로봇, LED 색상 규격).
* [docs/todo.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/todo.md): 앞으로 진행할 작업 백로그 (Week 1 최우선 과제 및 주차별 마일스톤).
* [docs/progress.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/progress.md): 이미 완료된 작업 내역 및 일자별 작업 로그.

#### 3. Git 형상 관리 및 원격 저장소 동기화
* 로컬 Git 초기화 (`main` 브랜치) 및 GitHub 원격 저장소 연동 완료.

#### 4. 파이썬 가상환경 생성
* C-확장 패키지(OpenCV, Pygame 등) 호환성이 가장 안정적인 **Anaconda `arena` (Python 3.11.16)** 가상환경 생성 완료.
