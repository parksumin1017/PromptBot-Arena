# 프롬프트 봇 아레나 (PromptBot Arena)

> **"프롬프트만으로 로봇에게 지시하여 게임을 단계별로 공략하는 아레나"**  
> 종합설계 II (Capstone Design II) 프로젝트

---

## 📖 문서 바로가기

* [프로젝트 제안서 (Proposal)](docs/proposal.md)
* [시스템 명세 및 아키텍처 (System Specification)](docs/overview.md)
* [주간 개발 진행 상황 (Weekly Progress)](docs/progress.md)

---

## 🛠️ 프로젝트 개요

본 프로젝트는 자연어 프롬프트만으로 2륜 소형 로봇에게 전술적 지시를 내려 상대 보스 로봇을 공략하는 피지컬 컴퓨팅 교육 플랫폼입니다.
**Code-as-Policies(CaP)** 패러다임을 소형 로봇 환경에 적용하여, 사용자의 자연어 명령을 안전한 파이썬 정책 스크립트로 변환하고 60 FPS 실시간 루프에서 구동합니다.

---

## 📁 디렉터리 구조

```text
종합설계II/
├── docs/                 # 프로젝트 문서 및 설계 사양
│   ├── proposal.md       # 종합설계 II 정식 제안서
│   ├── overview.md       # 시스템 아키텍처 및 Action Primitives 명세
│   └── progress.md       # 주간 개발 마일스톤 및 체크리스트
├── .env.example          # 환경 변수 템플릿
├── .gitignore            # Git 제외 파일 목록
└── README.md
```
