#!/usr/bin/env python3
"""
🎓 MCP(Model Context Protocol) 쉽게 이해하기 인터랙티브 튜토리얼
================================================================
이 스크립트는 복잡한 이론 대신, AI 에이전트와 MCP 서버가 실제로
어떻게 대화하고 도구를 사용하는지 눈으로 보고 체험할 수 있게 만든 안내 프로그램입니다.
"""

import subprocess
import json
import sys
import os
import time

# 콘솔 컬러 상수
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"

def print_header(title):
    line = "=" * 65
    print(f"\n{C_BOLD}{C_CYAN}{line}")
    print(f"  {title}")
    print(f"{line}{C_RESET}\n")

def print_client_msg(msg):
    print(f"{C_BOLD}{C_BLUE}🤖 [AI 클라이언트 (Antigravity/Gemini)] 발신:{C_RESET}")
    print(f"{C_BLUE}{json.dumps(msg, indent=2, ensure_ascii=False)}{C_RESET}\n")

def print_server_msg(msg):
    print(f"{C_BOLD}{C_GREEN}🏢 [MCP 서버 (Samsung Stock Assistant)] 수신 및 응답:{C_RESET}")
    print(f"{C_GREEN}{json.dumps(msg, indent=2, ensure_ascii=False)}{C_RESET}\n")

def pause_for_user():
    print(f"{C_YELLOW}👉 [Enter]를 누르면 다음 단계로 진행합니다...{C_RESET}", end="", flush=True)
    try:
        input()
    except EOFError:
        print()
        time.sleep(0.5)

def run_tutorial():
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api", "mcp_server.py")
    if not os.path.exists(server_path):
        print(f"❌ 오류: 서버 파일을 찾을 수 없습니다: {server_path}")
        return

    # MCP 서버 백그라운드 구동 (stdio 파이프 연결)
    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    req_id = 1

    def call_mcp(method, params=None, is_notification=False):
        nonlocal req_id
        payload = {"jsonrpc": "2.0", "method": method}
        if not is_notification:
            payload["id"] = req_id
            req_id += 1
        if params is not None:
            payload["params"] = params

        proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        proc.stdin.flush()

        if is_notification:
            return None

        line = proc.stdout.readline()
        if not line:
            return {}
        return json.loads(line.strip())

    try:
        # ==========================================================
        # 0단계: 개념 소개
        # ==========================================================
        print_header("💡 MCP(Model Context Protocol)란 무엇일까요?")
        print(f"1. 왜 MCP가 필요할까요?{C_RESET}")
        print("   • 일반 AI(Gemini, ChatGPT)는 우리의 내부 DB나 최신 주가를 알지 못합니다.")
        print("   • 그렇다고 10년치 대용량 데이터를 AI 프롬프트에 매번 다 넣으면 비용이 폭증하고 느려집니다.")
        print(f"   • 그래서 AI에게 {C_BOLD}'필요할 때 우리 컴퓨터의 프로그램을 실행할 수 있는 손발'{C_RESET}을 달아주는 표준 규격이 바로 {C_MAGENTA}MCP{C_RESET}입니다.")
        print(f"\n{C_BOLD}2. MCP의 비유: 'AI를 위한 표준 USB-C 케이블'{C_RESET}")
        print("   • 마우스, 키보드, 모니터가 USB-C 규격만 맞으면 어떤 컴퓨터에도 바로 꽂히듯,")
        print("   • 주가 DB, 포트폴리오 연산기 등 우리가 만든 도구도 MCP 규격만 맞추면")
        print("   • Antigravity, Gemini, Cursor, Claude 등 어떤 AI에도 바로 연결됩니다!\n")
        pause_for_user()

        # ==========================================================
        # 1단계: 핸드셰이크 (악수하기)
        # ==========================================================
        print_header("🤝 [1단계: 악수하기] AI와 서버가 처음 만나 인사합니다 (initialize)")
        print("AI 클라이언트가 MCP 서버에게 '안녕! 통신 규격을 맞추자'고 요청합니다.\n")

        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "My-AI-Assistant", "version": "1.0.0"}
            }
        }
        print_client_msg(init_req)
        init_res = call_mcp("initialize", init_req["params"])
        print_server_msg(init_res)

        print(f"📖 {C_BOLD}이해 포인트:{C_RESET}")
        print("   서버가 자신의 이름('samsung-stock-agent-mcp')과 프로토콜 버전을 알려주며")
        print("   서로 연결할 준비가 완료되었음을 확인했습니다.\n")

        # initialized 알림 전송
        call_mcp("notifications/initialized", is_notification=True)
        pause_for_user()

        # ==========================================================
        # 2단계: 도구 메뉴판 확인 (tools/list)
        # ==========================================================
        print_header("📋 [2단계: 메뉴판 확인] 서버가 가진 도구 목록을 살펴봅니다 (tools/list)")
        print("AI가 서버에게 '너 어떤 일들을 도와줄 수 있니?'라고 물어봅니다.\n")

        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        print_client_msg(list_req)
        list_res = call_mcp("tools/list")
        print_server_msg(list_res)

        tools = list_res.get("result", {}).get("tools", [])
        print(f"📖 {C_BOLD}이해 포인트:{C_RESET}")
        print(f"   서버가 {len(tools)}개의 도구(기술) 목록을 AI에게 전달했습니다:")
        for t in tools:
            print(f"   👉 {C_CYAN}{t['name']}{C_RESET}: {t['description']}")
        print("\n   이제 AI는 사용자가 질문했을 때 어떤 도구를 써야 할지 알게 되었습니다.\n")
        pause_for_user()

        # ==========================================================
        # 3단계: 실제 도구 호출 (tools/call)
        # ==========================================================
        print_header("🎯 [3단계: 도구 호출] AI가 판단하여 서버에게 조회를 요청합니다 (tools/call)")
        print(f"{C_BOLD}상황 연출:{C_RESET}")
        print("사용자가 AI에게 질문합니다: 🗣️ \"2024년 4월 15일 삼성전자 주가 얼마였어?\"")
        print("AI의 생각: '내 학습 데이터는 부정확하니, MCP 서버의 query_stock_data 도구에 2024-04-15를 넘겨야겠다!'\n")

        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "query_stock_data",
                "arguments": {
                    "query_type": "exact_date",
                    "target_date": "2024-04-15"
                }
            }
        }
        print_client_msg(call_req)
        call_res = call_mcp("tools/call", call_req["params"])
        print_server_msg(call_res)

        result_text = call_res.get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"📖 {C_BOLD}최종 결과:{C_RESET}")
        print("   서버가 로컬 SQLite DB(10년치 2,445건)에서 꺼내온 실제 팩트 데이터를 전달했습니다.")
        print(f"\n🤖 {C_BOLD}AI가 사용자에게 보낼 최종 답변:{C_RESET}")
        print(f"   \"2024년 4월 15일 삼성전자 종가는 78,870원이었습니다! (시가 78,870원, 고가 78,870원)\"\n")
        pause_for_user()

        # ==========================================================
        # 4단계: 인터랙티브 실습 메뉴
        # ==========================================================
        while True:
            print_header("🎮 [4단계: 직접 체험해보기] 원하는 도구를 직접 실행해보세요")
            print("1. 특정 날짜 주가 조회해보기 (예: 2023-01-02, 2024-05-10)")
            print("2. 삼성전자 역대 최고 종가 알아보기")
            print("3. 가상 주식 매수 후 실시간 수익률 분석해보기")
            print("4. 튜토리얼 종료")
            print("-" * 65)
            try:
                choice = input(f"{C_YELLOW}원하는 번호를 입력하세요 (1~4): {C_RESET}").strip()
            except EOFError:
                print("\n🎉 입력을 종료합니다.")
                break

            if choice == "1":
                try:
                    target = input("조회하고 싶은 날짜 (YYYY-MM-DD, 예: 2024-01-02): ").strip()
                except EOFError:
                    target = "2024-01-02"
                if not target:
                    target = "2024-01-02"
                res = call_mcp("tools/call", {
                    "name": "query_stock_data",
                    "arguments": {"query_type": "exact_date", "target_date": target}
                })
                ans = res.get("result", {}).get("content", [{}])[0].get("text", "")
                print(f"\n{C_GREEN}{ans}{C_RESET}\n")

            elif choice == "2":
                res = call_mcp("tools/call", {
                    "name": "query_stock_data",
                    "arguments": {"query_type": "max_all"}
                })
                ans = res.get("result", {}).get("content", [{}])[0].get("text", "")
                print(f"\n{C_GREEN}{ans}{C_RESET}\n")

            elif choice == "3":
                print("\n[가상 시나리오]: 70,000원에 삼성전자 10주를 매수한 경우")
                res = call_mcp("tools/call", {
                    "name": "analyze_portfolio",
                    "arguments": {
                        "portfolio_data": [
                            {"date": "2024-01-02", "type": "buy", "quantity": 10, "price": 70000}
                        ]
                    }
                })
                ans = res.get("result", {}).get("content", [{}])[0].get("text", "")
                print(f"\n{C_GREEN}{ans}{C_RESET}\n")

            elif choice == "4" or choice.lower() == "q":
                print("\n🎉 MCP 튜토리얼을 마칩니다! 수고하셨습니다.")
                break
            else:
                print("잘못된 입력입니다. 1~4번 중 선택해주세요.")

    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=2)

if __name__ == "__main__":
    run_tutorial()
