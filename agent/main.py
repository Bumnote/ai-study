"""
Main Entry Point - Supervisor Agent 기반 통합 시스템
"""
import asyncio
from supervisor_agent import create_integrated_agent_with_supervisor
from langchain_core.messages import HumanMessage


async def run_supervisor_system(user_input: str):
    """
    Supervisor Agent 시스템 실행
    """
    print("="*70)
    print("🚀 Supervisor Agent 시스템 시작")
    print("="*70)
    print(f"\n👤 사용자 입력: {user_input}\n")
    
    # 통합 시스템 생성
    agent_system = create_integrated_agent_with_supervisor()
    
    # 초기 상태
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "next_agent": "",
        "routing_context": {},
        "sync_triggered": False
    }
    
    try:
        # 에이전트 실행
        final_state = await agent_system.ainvoke(initial_state)
        
        print("\n" + "="*70)
        print("✅ 처리 완료")
        print("="*70)
        
        # 최종 응답 출력
        if final_state.get("messages"):
            last_message = final_state["messages"][-1]
            print(f"\n🤖 응답:\n{last_message.content}\n")
        
        # 라우팅 정보 출력
        if final_state.get("routing_context"):
            context = final_state["routing_context"]
            print(f"📍 라우팅: {context.get('selected_agent', 'N/A')}")
        
        # 동기화 여부 출력
        if final_state.get("sync_triggered"):
            print("🔄 자동 동기화 실행됨")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


async def interactive_mode():
    """
    대화형 모드 - 지속적으로 사용자 입력 받기
    """
    print("="*70)
    print("🎯 Supervisor Agent - 대화형 모드")
    print("="*70)
    print("\n명령어:")
    print("  - 'quit' 또는 'exit': 종료")
    print("  - 일반 질문: 자동으로 적절한 에이전트로 라우팅됩니다")
    print("\n예시:")
    print("  - '지난주 회의 내용 찾아줘' → RAG Agent")
    print("  - '회의록 작성해줘' → MCP Create Agent")
    print("  - 'Notion 동기화해줘' → Sync Agent")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input("💬 입력: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', '종료']:
                print("\n👋 시스템을 종료합니다.")
                break
            
            await run_supervisor_system(user_input)
            print()  # 빈 줄 추가
            
        except KeyboardInterrupt:
            print("\n\n👋 시스템을 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}\n")


# 테스트 시나리오
async def test_scenarios():
    """
    다양한 시나리오 테스트
    """
    scenarios = [
        # RAG 시나리오
        "지난주 회의 내용 찾아줘",
        "프로젝트 문서에서 배포 일정 검색해줘",
        
        # MCP Create 시나리오
        "오늘 회의록 작성해줘",
        "GitHub에서 catchTable 저장소 분석해줘",
        "Discord에 프로젝트 진행 상황 공유해줘",
        
        # Sync 시나리오
        "Notion 동기화 상태 확인해줘",
        "최신 페이지 동기화해줘",
        "전체 동기화 실행해줘",
        
        # 복합 시나리오
        "회의록 작성하고 Discord에 공유해줘",
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*70}")
        print(f"테스트 시나리오 {i}/{len(scenarios)}")
        print(f"{'='*70}")
        
        await run_supervisor_system(scenario)
        
        # 다음 시나리오 전 대기
        await asyncio.sleep(2)


async def main():
    """
    메인 함수 - 실행 모드 선택
    """
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "test":
            print("🧪 테스트 모드 실행\n")
            await test_scenarios()
        
        elif mode == "single":
            if len(sys.argv) > 2:
                user_input = " ".join(sys.argv[2:])
                await run_supervisor_system(user_input)
            else:
                print("❌ 사용법: python main.py single '질문 내용'")
        
        else:
            print(f"❌ 알 수 없는 모드: {mode}")
            print("사용법:")
            print("  python main.py               # 대화형 모드")
            print("  python main.py test          # 테스트 모드")
            print("  python main.py single '질문'  # 단일 질문 모드")
    
    else:
        # 기본: 대화형 모드
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())