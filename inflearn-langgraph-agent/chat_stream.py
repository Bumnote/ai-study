from dotenv import load_dotenv
import streamlit as st
from trading_graph import graph 
from typing import Callable, TypeVar
import inspect

from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit.delta_generator import DeltaGenerator

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정
st.set_page_config(page_title="LangGraph + Streamlit", page_icon=":robot:")

# Streamlit UI 구성
st.title("주식 분석 멀티 에이전트 시스템")
st.markdown("""
이 앱은 멀티 에이전트 시스템을 사용하여 주식을 분석합니다. 
주식 티커와 질문을 입력하시면 종합적인 분석 결과를 제공해드립니다.
""")

# 세션 상태 초기화: 메시지 히스토리를 저장할 리스트
if 'message_list' not in st.session_state:
    st.session_state.message_list = []

# 이전 대화 내역 표시
for message in st.session_state.message_list:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 사용자 입력 받기
user_input = st.chat_input("주식 티커와 질문을 입력하세요 (예: 'AAPL에 투자해야 할까요?')")

def get_streamlit_cb(parent_container: DeltaGenerator) -> BaseCallbackHandler:
    """
    Streamlit과 LangChain ChatLLM을 완벽하게 통합하는 콜백 핸들러를 생성합니다.
    토큰, 모델 응답, 중간 단계 등의 출력을 제공된 Streamlit 컨테이너에 업데이트합니다.
    Streamlit 콜백에서 자주 발생하는 NoSessionContext() 오류를 해결합니다.

    Args:
        parent_container (DeltaGenerator): LLM 상호작용 중 텍스트가 렌더링될 Streamlit 컨테이너
    Returns:
        BaseCallbackHandler: ChatLLM과 완벽하게 통합된 StreamlitCallbackHandler 인스턴스
    """
    # 제네릭 타입 힌팅을 위한 타입 변수 정의
    fn_return_type = TypeVar('fn_return_type')

    def add_streamlit_context(fn: Callable[..., fn_return_type]) -> Callable[..., fn_return_type]:
        """
        데코레이터: 함수가 Streamlit 실행 컨텍스트 내에서 실행되도록 보장합니다.
        콜백 함수 내에서 Streamlit 컴포넌트와 상호작용할 때 필요한 세션 컨텍스트를 추가합니다.

        Args:
            fn (Callable[..., fn_return_type]): 데코레이트할 콜백 메서드
        Returns:
            Callable[..., fn_return_type]: Streamlit 컨텍스트가 설정된 데코레이트된 함수
        """
        ctx = get_script_run_ctx()

        def wrapper(*args, **kwargs) -> fn_return_type:
            """
            래퍼 함수: Streamlit 컨텍스트를 추가하고 원본 함수를 호출합니다.
            NoSessionContext() 오류를 해결하기 위해 올바른 컨텍스트를 사용하도록 보장합니다.

            Args:
                *args: 원본 함수에 전달할 위치 인자
                **kwargs: 원본 함수에 전달할 키워드 인자
            Returns:
                fn_return_type: 원본 함수의 결과
            """
            add_script_run_ctx(ctx=ctx)
            return fn(*args, **kwargs)

        return wrapper

    # Streamlit의 StreamlitCallbackHandler 인스턴스 생성
    st_cb = StreamlitCallbackHandler(parent_container)

    # StreamlitCallbackHandler의 모든 메서드를 순회하며 콜백 메서드 래핑
    for method_name, method_func in inspect.getmembers(st_cb, predicate=inspect.ismethod):
        if method_name.startswith('on_'):  # LLM 이벤트에 응답하는 콜백 메서드 식별
            # 각 콜백 메서드를 Streamlit 컨텍스트 설정으로 래핑
            setattr(st_cb, method_name, add_streamlit_context(method_func))

    return st_cb

def invoke_our_graph(st_messages, callables):
    """
    컴파일된 그래프를 외부에서 호출하는 함수입니다.
    
    Args:
        st_messages: Streamlit 메시지 리스트
        callables: 콜백 함수 리스트
    Returns:
        그래프 실행 결과
    """
    # 그래프 실행을 위한 설정 구성
    config = {
        'configurable': {
            'thread_id': '1234'
        },
        "callbacks": callables,
    }
    
    # callables가 리스트인지 확인
    if not isinstance(callables, list):
        raise TypeError("callables must be a list")
    
    # 현재 메시지와 콜백 설정으로 그래프 호출
    return graph.invoke({"messages": st_messages}, config=config)

# 사용자 입력이 있을 경우 처리
if user_input:
    # 사용자 메시지를 세션 상태에 추가하고 UI에 표시
    st.session_state.message_list.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    
    # AI 응답 처리 및 그래프 이벤트 핸들링
    with st.chat_message("assistant"):
        # AI 응답을 시각적으로 업데이트하기 위한 플레이스홀더
        msg_placeholder = st.empty()
        
        # 스트리밍 메시지와 기타 이벤트를 위한 새로운 플레이스홀더 생성
        st_callback = get_streamlit_cb(st.empty())
        
        # 그래프 실행 및 응답 받기
        response = invoke_our_graph(st.session_state.message_list, [st_callback])
        
        # 마지막 메시지 추출 및 처리
        last_msg = response["messages"][-1].content
        st.session_state.message_list.append({"role": "assistant", "content": last_msg})
        
        # UI 업데이트: 최종 응답 표시
        msg_placeholder.write(last_msg)
    