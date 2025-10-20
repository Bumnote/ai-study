# 🧠 AI Lab

> **ai-study**  
> 인공지능의 다양한 기술을 직접 구현하고, 강의와 교재를 통해 학습하는 실험실입니다.  
> 단순한 모델 사용에 그치지 않고, 원리부터 응용까지 실습 중심으로 개념을 탐구하고 정리합니다.

---

## 🔬 실험 주제별 정리

| 주제 | 설명 | 링크 |
|------|------|------|
| LLM-Basics | OpenAI API 및 Transformer 기본 구조 실험 | [바로가기](./llm-basics/README.md) |
| Prompt-Engineering | 프롬프트 설계와 최적화 기법 | [바로가기](./prompt-engineering/README.md) |
| Embedding-RAG | 벡터 임베딩과 검색 기반 생성(RAG) 구조 실습 | [바로가기](./embedding-rag/README.md) |
| Vision | OpenAI Vision·CLIP 등 이미지 이해 모델 실험 | [바로가기](./vision/README.md) |
| Speech | STT/TTS 모델 실습 (Whisper, Piper, etc.) | [바로가기](./speech/README.md) |
| Agent | LangChain·CrewAI 기반 다중 에이전트 구조 실험 | [바로가기](./agent/README.md) |
| Fine-Tuning | 모델 미세조정 실습 (GPT, LLaMA, Gemma 등) | [바로가기](./fine-tuning/README.md) |
| Evaluation | AI 성능 측정 및 품질 평가 (BLEU, Rouge 등) | [바로가기](./evaluation/README.md) |
| Ethics & Safety | AI 윤리·편향·프롬프트 보안 실험 | [바로가기](./ethics-safety/README.md) |

---

## 🧭 목적

- AI 및 LLM의 **핵심 개념을 직접 구현하며 이해**
- 단순 API 호출이 아닌 **모델 내부 구조와 데이터 흐름 분석**
- **실무 프로젝트에 응용 가능한 AI 패턴과 파이프라인 확보**

---

## 🧪 실험 방식

> 각 실험 디렉토리는 독립된 노트북(`.ipynb`) 또는 모듈형 프로젝트로 구성되어 있습니다.  
> `README.md`를 통해 개념, 코드, 실험 결과, 주의사항 등을 정리합니다.

✅ 실습 → 🔍 모델 분석 → 📘 개념 정리 → 💡 응용 프로젝트

---

## 🧩 프로젝트 예시

| 실험 주제 | 예시 프로젝트 |
|------------|----------------|
| LLM-Basics | OpenAI API 호출 및 Transformer 구조 시각화 |
| Embedding-RAG | 문서 검색 기반 챗봇 (PDF RAG) |
| Vision | 이미지 캡셔닝 (Image Captioning) 및 Vision QA |
| Agent | 다중 역할 기반 AI 팀 시뮬레이션 (PM, Dev, Designer) |
| Fine-Tuning | 사용자 감정 분석 모델 미세조정 |
| Ethics & Safety | 프롬프트 인젝션·편향 탐지 실험 |

---

## 🧑‍💻 실험 환경

- **Python**: 3.11+
- **IDE**: Jupyter Notebook / VSCode
- **필수 라이브러리**:
  - `openai`
  - `langchain`
  - `chromadb`
  - `transformers`
  - `torch`
  - `datasets`
  - `faiss-cpu`
- **환경 구성**:
  - Docker 기반 개발 환경 (`docker-compose.yml`)
  - `.env` 파일을 통한 API 키 관리
