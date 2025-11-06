# utils/document_classifier.py
import os
from langchain.chat_models.base import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

# =====================================
# ⚙️ 환경 설정
# =====================================
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
llm = init_chat_model(MODEL, model_provider="openai")

# =====================================
# 🧠 classify_document 함수
# =====================================
def classify_document(state: dict):
    """
    문서 내용을 기반으로 문서 유형을 분류합니다.
    입력: {"text": str, "file_path": str}
    출력: {"doc_type": str, "text": str, "file_path": str}
    """
    text = state["text"][:2000]  # 너무 긴 문서는 앞부분만 사용 (LLM context 절약)

    prompt = f"""
    아래 문서의 성격을 분류하세요.

    [가능한 카테고리: "회의록", "기술 회의", "회고록"]

    1. 회의록
        - 일정, 기획, 진행상황, 업무 조율 등 '회의 중 논의된 내용' 중심의 문서
        - 예시: "다음 스프린트 일정은 10월 5일로 확정했다.", "요구사항 명세 변경에 대한 논의"

    2. 기술 회의
        - 시스템 구조, 아키텍처 설계, 성능 개선, 기술 스택, API 설계 등
        - 예시: "Redis 캐시 구조 변경", "DB 인덱스 튜닝", "Spring Boot 구조 개선 논의"
        - '성능 개선', '기술 검토', '아키텍처', '리팩토링' 등의 단어가 포함된 경우 기술 회의로 분류

    3. 회고록
        - 지난 기간 동안의 활동을 되돌아보며 배운 점, 잘한 점, 아쉬운 점 등을 서술하는 문서
        - 예시: "이번 스프린트에서 협업의 중요성을 느꼈다.", "성과와 개선점을 공유하며 회고를 진행했다."
        - '지난 프로젝트', '이번 스프린트 회고', '느낀 점', '배운 점' 등의 단어가 포함된 경우 회고록으로 분류

    [분류 규칙]
    - 문서에 '성능 개선', 'API 설계', '기술 검토', 'DB', '서버', '아키텍처' 등의 단어가 포함되어 있다면 → 기술 회의로 분류
    - 문서에 '일정', '회의', '기획', '참석자', '논의' 등의 단어가 주로 등장하면 → 회의록으로 분류
    - 문서에 '회고', '지난', '성과', '느낀 점', '배운 점'이 등장하고, 과거 시제의 문장이 많다면 → 회고록으로 분류
    - 두 가지 이상 혼합되어 있으면, 기술 관련 논의가 포함된 경우 기술 회의로 우선 분류

    [출력 형식]
    문서 유형만 아래 중 하나로 출력하세요:
    - 회의록
    - 기술 회의
    - 회고록

    ---
    [문서 내용]
    {text}
    """

    result = llm.invoke([
        SystemMessage(content="문서의 내용을 분석하여 문서의 유형을 결정하는 문서 분류기입니다."),
        HumanMessage(content=prompt)
    ])

    answer = result.content.strip()
    doc_type = None

    for c in ["회의록", "기술 회의", "회고록"]:
        if c in answer:
            doc_type = c
            break

    if not doc_type:
        doc_type = "미분류"
        print("⚠️ 분류 실패: 기본값 '미분류'로 처리합니다.")

    print(f"📝 분류 결과: {doc_type}")
    return {
        "doc_type": doc_type,
        "text": state["text"],
        "file_path": state["file_path"]
    }
