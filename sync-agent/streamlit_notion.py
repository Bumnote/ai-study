import streamlit as st
import asyncio

# ========================================
# ✅ MCP 서버의 로컬 함수 직접 import
# ----------------------------------------
# notion_mcp_server.py 안에 다음 함수들이 정의되어 있어야 합니다:
#   get_all_metadata_local()
#   get_page_content_local(page_id)
#   update_page_summary_local(page_id, summary)
# ----------------------------------------
from tools.notion_mcp_server import (
    get_all_metadata,
    get_page_content,
    update_page_summary,
)

# ========================================
# ⚙️ Streamlit 기본 설정
# ========================================
st.set_page_config(page_title="📘 Notion MCP Local Dashboard", page_icon="🧠", layout="wide")
st.title("📘 Notion MCP Local Dashboard")
st.caption("로컬에서 MCP Tool 함수를 직접 호출하여 테스트하는 대시보드입니다.")

# ========================================
# 🧠 비동기 안전 실행 헬퍼
# ========================================
def run_async(func, *args, **kwargs):
    """Streamlit 환경에서 안전하게 async/동기 함수 실행"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Streamlit의 비동기 루프 위에서 task 예약
            future = asyncio.ensure_future(func(*args, **kwargs))
            loop.run_until_complete(future)
        else:
            return loop.run_until_complete(func(*args, **kwargs))
    except RuntimeError:
        return asyncio.run(func(*args, **kwargs))
    except TypeError:
        # 비동기 함수가 아닌 경우 그냥 실행
        return func(*args, **kwargs)

# ========================================
# 🧭 탭 구성
# ========================================
tab1, tab2, tab3 = st.tabs(["📄 전체 메타데이터", "🔍 페이지 내용 보기", "🧠 요약문 추가"])

# ========================================
# 📄 1️⃣ 전체 메타데이터
# ========================================
with tab1:
    st.subheader("📄 Notion 전체 페이지 메타데이터 조회")

    if st.button("🔄 전체 메타데이터 가져오기", use_container_width=True):
        with st.spinner("Notion API에서 데이터를 가져오는 중..."):
            try:
                res = run_async(get_all_metadata)
                if not res:
                    st.error("❌ 데이터 응답이 없습니다.")
                elif "error" in res:
                    st.error(f"❌ 오류 발생: {res['error']}")
                else:
                    st.success(f"✅ {res['count']}개의 페이지를 가져왔습니다.")
                    st.dataframe(res["results"], use_container_width=True, hide_index=True)
                    with st.expander("📦 원본 JSON 보기"):
                        st.json(res)
            except Exception as e:
                st.error(f"❌ 실행 중 오류 발생: {e}")

# ========================================
# 🔍 2️⃣ 특정 페이지 내용 보기
# ========================================
with tab2:
    st.subheader("🔍 특정 페이지 내용 가져오기")
    page_id = st.text_input("📘 Notion 페이지 ID 입력", placeholder="예: 25310f5b-107a-818c-970f-000becd1980c")

    if st.button("📥 페이지 내용 가져오기", use_container_width=True):
        if not page_id.strip():
            st.warning("⚠️ 페이지 ID를 입력해주세요.")
        else:
            with st.spinner("페이지 내용을 불러오는 중..."):
                try:
                    res = run_async(get_page_content, page_id)
                    if not res:
                        st.error("❌ 데이터 응답이 없습니다.")
                    elif "error" in res:
                        st.error(f"❌ 오류 발생: {res['error']}")
                    else:
                        st.success("✅ 페이지 내용을 성공적으로 가져왔습니다.")
                        text = res.get("text", "")
                        st.text_area("📄 페이지 내용:", text, height=400)
                except Exception as e:
                    st.error(f"❌ 실행 중 오류 발생: {e}")

# ========================================
# 🧠 3️⃣ 페이지 요약문 추가
# ========================================
with tab3:
    st.subheader("🧠 Notion 페이지에 요약문 추가")

    col1, col2 = st.columns(2)
    with col1:
        page_id = st.text_input("📘 페이지 ID", key="summary_page_id")
    with col2:
        summary = st.text_input("📝 추가할 요약문", placeholder="예: Redis 캐시 구조 변경 요약")

    if st.button("✅ 요약문 추가", use_container_width=True):
        if not page_id.strip() or not summary.strip():
            st.warning("⚠️ 페이지 ID와 요약문을 모두 입력해주세요.")
        else:
            with st.spinner("Notion 페이지에 요약문 추가 중..."):
                try:
                    res = run_async(update_page_summary, page_id, summary)
                    if not res:
                        st.error("❌ 데이터 응답이 없습니다.")
                    elif "error" in res:
                        st.error(f"❌ 오류 발생: {res['error']}")
                    else:
                        st.success(f"✅ {res['page_id']} 페이지에 요약문이 추가되었습니다.")
                except Exception as e:
                    st.error(f"❌ 실행 중 오류 발생: {e}")
