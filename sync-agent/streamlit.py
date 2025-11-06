# streamlit_sync_dashboard.py
import streamlit as st
import asyncio
import time
from langchain_core.messages import HumanMessage
from agents.sync_agent import sync_agent_node

# =============================
# ⚙️ 기본 페이지 설정
# =============================
st.set_page_config(page_title="Sync Agent Dashboard", page_icon="🧠", layout="wide")

st.title("🧠 Notion Sync Agent 실시간 대시보드")
st.caption("LangGraph 기반 Sync Agent의 단계별 진행 상태 및 로그를 실시간으로 확인할 수 있습니다.")

# =============================
# 🧭 Session State 초기화
# =============================
if "logs" not in st.session_state:
    st.session_state.logs = []
if "progress" not in st.session_state:
    st.session_state.progress = 0
if "is_running" not in st.session_state:
    st.session_state.is_running = False


def log(msg: str, level="info"):
    """로그를 실시간으로 Streamlit에 표시"""
    st.session_state.logs.append((level, msg))
    placeholder.markdown(f"🟢 {msg}")


def update_progress(pct: int, label: str):
    """진행률 및 상태 업데이트"""
    st.session_state.progress = pct
    progress_bar.progress(pct, text=f"{label} ({pct}%)")
    time.sleep(0.3)


# =============================
# 🖥️ UI 레이아웃 구성
# =============================
col1, col2 = st.columns([0.4, 0.6])

with col1:
    st.subheader("⚙️ 설정")
    last_sync_at = st.text_input(
        "마지막 동기화 시각 (ISO 형식, 예: 2025-11-05T09:30:00Z)",
        value="",
        placeholder="비워두면 전체 문서 동기화"
    )
    st.divider()
    run_button = st.button("🚀 동기화 시작", type="primary", use_container_width=True)
    clear_button = st.button("🧹 로그 초기화", use_container_width=True)

with col2:
    st.subheader("📊 동기화 진행 상태")
    progress_bar = st.progress(0)
    placeholder = st.empty()
    log_area = st.container()
    result_box = st.container()

if clear_button:
    st.session_state.logs = []
    st.session_state.progress = 0
    placeholder.empty()
    progress_bar.progress(0, text="대기 중")

# =============================
# 🚀 동기화 실행 (비동기)
# =============================
# 🚀 동기화 실행 (비동기)
if run_button and not st.session_state.is_running:
    st.session_state.is_running = True
    st.session_state.logs = []
    placeholder.empty()
    result_box.empty()

    async def run_sync():
        try:
            update_progress(5, "Notion MCP 서버 연결 중...")
            log("🔌 Notion MCP 서버에 연결합니다...")

            # LangGraph state 형태로 초기화
            state = {
                "messages": [HumanMessage(content="노션 데이터를 동기화해줘")],
                "routing_context": {"last_sync_at": last_sync_at}
            }

            update_progress(15, "페이지 메타데이터 수집 중...")
            log("📥 Notion 페이지 메타데이터를 수집 중입니다...")

            # ✅ 실제 에이전트 실행 (비동기 함수 호출)
            result = await sync_agent_node(state)

            update_progress(70, "Pinecone Embedding 저장 중...")
            log("🧠 Embedding & VectorStore 저장 중...")

            update_progress(100, "완료 ✅")
            log("🎉 동기화 작업이 성공적으로 완료되었습니다!")

            with result_box:
                st.success("✅ 동기화 완료!")
                st.info(f"📅 마지막 동기화 시각: {state['routing_context']['last_sync_at']}")
                st.write("### 📄 동기화된 문서 목록")
                for item in result.get("synced_pages", []):
                    st.markdown(f"- **{item}**")

        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
            log(f"❌ 오류 발생: {e}", level="error")

        finally:
            st.session_state.is_running = False
            update_progress(100, "대기 중")

    # ✅ Streamlit-safe async 실행
    try:
        asyncio.run(run_sync())
    except RuntimeError:
        # 이미 루프가 있는 경우 fallback
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_sync())