# streamlit_rag_dashboard.py
import streamlit as st
from langchain_core.messages import HumanMessage
from agents.rag_agent import rag_agent_node

# =============================
# ⚙️ 기본 페이지 설정
# =============================
st.set_page_config(page_title="RAG Agent Dashboard", page_icon="🧠", layout="wide")

st.title("🧠 RAG Agent (Retrieval-Augmented Generation)")
st.caption("Pinecone에 저장된 Notion 문서를 기반으로 LLM이 답변을 생성합니다.")

# =============================
# 🧭 UI 구성
# =============================
query = st.text_area("💬 질문을 입력하세요:", placeholder="예: 최근 회의에서 논의된 Pinecone 관련 내용은?")
run_button = st.button("🔍 검색 및 답변 생성", type="primary")

col1, col2 = st.columns([0.5, 0.5])
answer_box = st.container()

# =============================
# 🚀 실행 로직
# =============================
if run_button and query.strip():
    with st.spinner("검색 및 답변 생성 중..."):
        try:
            # LangGraph 상태 시뮬레이션
            state = {
                "messages": [HumanMessage(content=query)],
                "routing_context": {}
            }

            result = rag_agent_node(state)
            answer = result["answer"]
            references = result.get("references", [])

            with answer_box:
                st.subheader("🧠 답변 결과")
                st.write(answer)

                if references:
                    st.markdown("#### 📚 참조 문서")
                    for ref in references:
                        st.markdown(f"- {ref}")

        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
else:
    st.info("질문을 입력한 후 [🔍 검색 및 답변 생성] 버튼을 눌러주세요.")
