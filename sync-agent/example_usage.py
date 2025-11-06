# example_usage.py
"""
통합 시스템 실행 예시
"""

from langchain_core.messages import HumanMessage
from main_graph import build_graph


def example_sync():
    """동기화 예시"""
    print("\n" + "="*70)
    print("예시 1: Notion 동기화")
    print("="*70 + "\n")
    
    app = build_graph()
    
    initial_state = {
        "messages": [HumanMessage(content="노션 문서를 동기화해주세요")],
        "next_agent": "",
        "routing_context": {},
        "sync_triggered": False,
        "synced_pages": [],
        "failed_pages": [],
        "last_synced_at": ""
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ 동기화 완료")
    print("="*70)
    print(f"\n{result['messages'][-1].content}\n")


def example_rag():
    """RAG 검색 예시"""
    print("\n" + "="*70)
    print("예시 2: 문서 검색")
    print("="*70 + "\n")
    
    app = build_graph()
    
    initial_state = {
        "messages": [HumanMessage(content="지난 회의록에서 API 관련 논의 내용 알려줘")],
        "next_agent": "",
        "routing_context": {},
        "sync_triggered": False,
        "synced_pages": [],
        "failed_pages": [],
        "last_synced_at": ""
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ 검색 완료")
    print("="*70)
    print(f"\n{result['messages'][-1].content}\n")


def example_chitchat():
    """일반 대화 예시"""
    print("\n" + "="*70)
    print("예시 3: 일반 대화")
    print("="*70 + "\n")
    
    app = build_graph()
    
    initial_state = {
        "messages": [HumanMessage(content="안녕하세요! 오늘 날씨 좋네요")],
        "next_agent": "",
        "routing_context": {},
        "sync_triggered": False,
        "synced_pages": [],
        "failed_pages": [],
        "last_synced_at": ""
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ 대화 완료")
    print("="*70)
    print(f"\n{result['messages'][-1].content}\n")


def interactive_mode():
    """대화형 모드"""
    print("\n" + "🤖 " + "="*66)
    print("  Notion Document Processing System - Interactive Mode")
    print("  (종료: 'quit' 또는 'exit')")
    print("="*70 + "\n")
    
    app = build_graph()
    
    while True:
        user_input = input("\n👤 You: ").strip()
        
        if user_input.lower() in ["quit", "exit", "종료"]:
            print("\n👋 시스템을 종료합니다.\n")
            break
        
        if not user_input:
            continue
        
        state = {
            "messages": [HumanMessage(content=user_input)],
            "next_agent": "",
            "routing_context": {},
            "sync_triggered": False,
            "synced_pages": [],
            "failed_pages": [],
            "last_synced_at": ""
        }
        
        try:
            result = app.invoke(state)
            response = result['messages'][-1].content
            print(f"\n🤖 Assistant:\n{response}\n")
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sync":
            example_sync()
        elif command == "rag":
            example_rag()
        elif command == "chat":
            example_chitchat()
        elif command == "interactive":
            interactive_mode()
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: sync, rag, chat, interactive")
    else:
        print("\n사용법:")
        print("  python example_usage.py sync        # 동기화 테스트")
        print("  python example_usage.py rag         # RAG 검색 테스트")
        print("  python example_usage.py chat        # 일반 대화 테스트")
        print("  python example_usage.py interactive # 대화형 모드")
        print()
        
        # 기본: 동기화 실행
        example_sync()