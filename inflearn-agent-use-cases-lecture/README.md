# 회사에서 바로 쓰는 업무자동화 AI 에이전트 (w. n8n, LangGraph)

이 저장소는 [**회사에서 바로 쓰는 업무자동화 AI 에이전트 (w. n8n, LangGraph)**](https://inf.run/kRHJy) 강의의 소스코드와 실습 자료를 포함하고 있습니다.

## 📚 강의 개요

이 강의는 실무에서 바로 활용할 수 있는 AI 에이전트를 n8n과 LangGraph를 사용하여 구축하는 방법을 다룹니다. Workflow부터 시작해서 점차 고도화된 Agent까지, 단계별로 학습할 수 있도록 구성되어 있습니다.

## 🎯 학습 목표

- **n8n을 활용한 워크플로우 자동화** 마스터하기
- **LangGraph를 통한 AI 에이전트** 구현 방법 익히기
- **실무 적용 가능한 사례들**을 통한 실전 경험 쌓기
- **Workflow에서 Agent로의 전환** 과정 이해하기

## 📋 커리큘럼

### 1️⃣ 강의 소개
- 강의 기획 의도와 커리큘럼 설명

### 2️⃣ n8n은 어디에 쓸 수 있나요?
- n8n 기본 개념과 로컬호스트 구동
- AWS 배포 방법 (야매버전 & 정석버전)

### 3️⃣ Workflow: 이메일 작성 도우미
- 이메일 답장 여부 검증 봇
- Context를 고려한 이메일 답장 드래프트 작성
- n8n Chat UI 활용 이메일 봇
- n8n API와 Streamlit 연동 이메일 작성 봇

### 4️⃣ Workflow: 우리 회사 기사 검색
- Brave API 활용 뉴스 감정 분석 (Google Sheets 연동)
- 네이버 뉴스 스크랩 (Notion 연동)

### 5️⃣ Agent: 사내 QnA 봇
- 구글 드라이브 + n8n 데이터 전처리
- 파이썬을 활용한 고급 데이터 전처리
- LangGraph 기본 개념 (state, node, edge)
- LangGraph로 구현하는 사내 QnA 봇
- Workflow에서 Agent로의 전환

### 6️⃣ Text-to-SQL: 어제 서울에서 가장 많이 팔린 물건은?
- Text-to-SQL 기본 개념
- n8n으로 구현하는 Text-to-SQL
- 단계별 개선 과정 (1차, 2차)
- 슬랙봇 연동

### 7️⃣ Agent: GitHub 코드 리뷰 에이전트Whisper & MCP 활용
- Model Context Protocol(MCP) 이해
- MCP를 활용한 코드리뷰 에이전트 생성

### 8️⃣ 영상 요약 시스템: OpenAI 
- OpenAI Whisper를 활용한 영상 요약
- Notion MCP 활용으로 영상 요약 내용 저장하기
- YouTube 영상 요약하기



## 📁 저장소 구조

```
agent-use-cases/
├── 📓 강의 노트북 파일들
│   ├── 14.1 파이썬을 활용한 데이터 전처리.ipynb
│   ├── 14.2 파이썬을 활용한 데이터 전처리.ipynb
│   ├── 16. LangGraph로 구현하는 사내 QnA 봇.ipynb
│   ├── 17. Workflow -> Agent 전환하기.ipynb
│   ├── 24. MCP를 활용한 코드리뷰 에이전트 생성하기.ipynb
│   ├── 25. OpenAI Whisper를 활용한 영상 요약.ipynb
│   ├── 26. Notion MCP 활용으로 영상 요약 내용 저장하기.ipynb
│   └── 27. YouTube 영상 요약하기.ipynb
│
├── 🐍 Python 실습 파일
│   └── 9. n8n API와 Streamlit으로 만드는 이메일 작성 봇.py
│
├── 📄 사내 문서 (한국어)
│   └── documents/
│       ├── IT 지원 가이드.pdf
│       ├── 경비 관리 가이드.pdf
│       ├── 법률 및 준수 정책.pdf
│       ├── 전결 규정.pdf
│       ├── 직원 복리후생 및 복지 FAQ.pdf
│       ├── 직원 복리후생 및 복지 가이드.pdf
│       └── 직원 핸드북 및 인사 정책.pdf
│
├── 📄 사내 문서 (영어 제목)
│   └── documents_with_english_titles/
│
├── 📝 전처리된 마크다운 파일
│   └── output/
│
└── ⚙️ 프로젝트 설정
    ├── pyproject.toml
    ├── uv.lock
    └── README.md
```

## 🚀 시작하기

### 필요 조건

- Python 3.8+
- n8n 계정 (또는 로컬 설치)
- OpenAI API 키 (또는 다른 LLM API)

### 설치 방법

1. 저장소 클론
```bash
git clone <repository-url>
cd agent-use-cases
```

2. 의존성 설치 (uv 사용 권장)
```bash
uv sync
```

또는 pip 사용:
```bash
pip install -r requirements.txt
```

3. Jupyter Notebook 실행
```bash
jupyter lab
```

## 📚 학습 가이드

1. **순차적 학습**: 커리큘럼 순서대로 진행하는 것을 권장합니다.
2. **실습 중심**: 각 섹션의 노트북 파일을 직접 실행해보세요.
3. **문서 활용**: `documents/` 폴더의 사내 문서들은 QnA 봇 실습에 사용됩니다.
4. **점진적 발전**: Workflow부터 시작해서 Agent까지 단계별로 학습하세요.

## 🔗 관련 링크

- [강의 상세 정보](https://www.kangsium.com/agent-use-cases-with-n8n-and-langgraph)
- [n8n 공식 문서](https://docs.n8n.io/)
- [LangGraph 문서](https://langchain-ai.github.io/langgraph/)

## 📧 문의

강의나 코드 관련 문의사항이 있으시면 언제든지 연락해 주세요.

---

**⭐ 이 강의가 도움이 되셨다면 스타를 눌러주세요!**
