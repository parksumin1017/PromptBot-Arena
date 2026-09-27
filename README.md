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
```

---

## 📁 디렉터리 구조

```text
종합설계II/
├── docs/                 # 프로젝트 문서 및 설계 사양 (SSOT 원칙 관리)
│   ├── proposal.md       # 종합설계 II 정식 제안서 (불변 기준)
│   ├── overview.md       # 시스템 아키텍처 및 Action Primitives 명세
│   ├── todo.md           # 앞으로 할 일 목록 (Backlog)
│   ├── progress.md       # 이미 완료한 작업 일지 (Work Done)
│   └── presentation_guide.md # 주간 발표 PPT 제작 지침서 (요청 시에만 열람)
├── .env.example          # 환경 변수 템플릿
├── .gitignore            # Git 제외 파일 목록
└── README.md             # 프로젝트 대문 및 실행 가이드
```
