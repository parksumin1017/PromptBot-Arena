# Work Progress: 프롬프트 봇 아레나 (PromptBot Arena)

본 문서는 **이미 수행하여 완료된 작업 내역(Work Done)**과 시스템 변경 이력을 누적 기록하는 작업 일지입니다.  
앞으로 진행할 작업(할 일) 목록은 [todo.md](docs/todo.md)를 참조합니다.

---

## 📊 작업 완료 내역 요약 (Summary of Completed Tasks)

| 완료일 | 항목 | 세부 내용 | 산출물 / 커밋 |
|:---|:---|:---|:---|
| **2026-09-27** | 프로젝트 구조화 및 문서 체계화 | `docs/` 폴더 분리, 제안서 복사, 사양서 및 진행 관리 문서 수립 | `docs/proposal.md`, `docs/overview.md`, `docs/todo.md`, `docs/progress.md` |
| **2026-09-27** | 보안 및 환경 설정 | Git 제외 파일(`.gitignore`) 작성 및 토큰/환경변수 분리 | `.gitignore`, `.env`, `.env.example` |
| **2026-09-27** | Git 형상 관리 및 원격 연동 | 로컬 저장소 초기화 및 GitHub 원격 저장소(`PromptBot-Arena`) 생성 및 첫 푸시 완료 | `https://github.com/parksumin1017/PromptBot-Arena` |

---

## 📝 일자별 상세 작업 로그 (Daily Work Log)

### 2026년 9월 27일 (일) - 프로젝트 착수 및 초기 셋업

#### 1. 보안 및 환경 격리 설정
* GitHub Personal Access Token(PAT)과 사용자 계정 정보를 로컬 환경 변수 파일([.env](file:///c:/Users/박수민/Desktop/종합설계II/.env))에 분리 저장.
* [.gitignore](file:///c:/Users/박수민/Desktop/종합설계II/.gitignore)를 작성하여 `.env`, `*.token`, 가상환경(`.venv`), 파이썬 캐시(`__pycache__`) 등이 Git에 추적되거나 유출되지 않도록 원천 차단.
* 협업 및 추후 배포를 위한 템플릿 파일([.env.example](file:///c:/Users/박수민/Desktop/종합설계II/.env.example)) 생성.

#### 2. 프로젝트 문서 체계 정립 ([docs/](file:///c:/Users/박수민/Desktop/종합설계II/docs))
* [docs/proposal.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/proposal.md): 종합설계 II 제출 원본 제안서 복사 및 아카이빙.
* [docs/overview.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/overview.md): 개발 실무에 필요한 핵심 기술 사양서(정량 목표, Action Primitives API 명세, LED 비전 규격, 코딩 규칙) 작성.
* [docs/todo.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/todo.md): 향후 수행할 주차별 작업(할 일) 목록 독립 분리.
* [docs/progress.md](file:///c:/Users/박수민/Desktop/종합설계II/docs/progress.md): 완료된 작업 내역 및 히스토리 기록용 문서 정비.
* [README.md](file:///c:/Users/박수민/Desktop/종합설계II/README.md): 프로젝트 홈 및 문서 네비게이션 링크 구성.

#### 3. Git 형상 관리
* `git init` 실행 및 기본 브랜치를 `main`으로 지정.
* 1차 초기화 커밋(`docs: initialize project with proposal, specs, and progress tracker`) 완료.
