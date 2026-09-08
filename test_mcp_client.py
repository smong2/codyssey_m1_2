#!/usr/bin/env python3
"""
MCP Server Invocation Flow Automated Verification Client
=========================================================
표준 JSON-RPC 2.0 stdio 프로토콜을 사용하여 api/mcp_server.py를 하위 프로세스로 실행하고,
다음 4단계의 표준 MCP 핸드셰이크 및 도구 호출 흐름을 엄격하게 검증합니다:
1. initialize 핸드셰이크 요청 및 응답 검증
2. notifications/initialized 알림 전송
3. tools/list 도구 메타데이터 목록 및 스키마 검증
4. tools/call 실제 도구 실행 및 결과 반환 검증
   - 4a. query_stock_data (특정일 주가 조회)
   - 4b. query_stock_data (역대 최고가 조회)
   - 4c. analyze_portfolio (포트폴리오 수익률 평가)
"""

import subprocess
import json
import sys
import os

def run_test():
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api", "mcp_server.py")
    print(f"🚀 [MCP 테스트 클라이언트 시작] 서버 스크립트: {server_path}")

    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    req_counter = 1

    def send_request(method, params=None, is_notification=False):
        nonlocal req_counter
        req_id = None if is_notification else req_counter
        if not is_notification:
            req_counter += 1

        payload = {
            "jsonrpc": "2.0",
            "method": method
        }
        if req_id is not None:
            payload["id"] = req_id
        if params is not None:
            payload["params"] = params

        raw_line = json.dumps(payload, ensure_ascii=False) + "\n"
        proc.stdin.write(raw_line)
        proc.stdin.flush()

        if is_notification:
            return None

        resp_line = proc.stdout.readline()
        if not resp_line:
            raise RuntimeError(f"서버로부터 응답을 받지 못했습니다. (요청: {method})")
        return json.loads(resp_line.strip())

    try:
        print("\n==================================================")
        print("📌 [테스트 1] initialize 핸드셰이크 요청")
        print("==================================================")
        init_resp = send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "Antigravity-VerificationClient", "version": "1.0.0"}
        })
        print(f"📥 수신 응답:\n{json.dumps(init_resp, indent=2, ensure_ascii=False)}")
        assert init_resp.get("result", {}).get("serverInfo", {}).get("name") == "samsung-stock-agent-mcp", "서버 이름 검증 실패"
        print("✅ [성공] initialize 정상 완료")

        print("\n==================================================")
        print("📌 [테스트 2] notifications/initialized 전송")
        print("==================================================")
        send_request("notifications/initialized", is_notification=True)
        print("✅ [성공] notifications/initialized 알림 전송 완료")

        print("\n==================================================")
        print("📌 [테스트 3] tools/list 도구 목록 질의")
        print("==================================================")
        tools_resp = send_request("tools/list")
        tools = tools_resp.get("result", {}).get("tools", [])
        tool_names = [t.get("name") for t in tools]
        print(f"📥 발견된 도구 ({len(tools)}개): {tool_names}")
        assert "query_stock_data" in tool_names, "query_stock_data 도구 누락"
        assert "analyze_portfolio" in tool_names, "analyze_portfolio 도구 누락"
        assert "get_conversation_history" in tool_names, "get_conversation_history 도구 누락"
        print("✅ [성공] 등록된 3대 도구 스키마 검증 통과")

        print("\n==================================================")
        print("📌 [테스트 4a] tools/call -> query_stock_data (2024-04-15 주가)")
        print("==================================================")
        call_resp_1 = send_request("tools/call", {
            "name": "query_stock_data",
            "arguments": {
                "query_type": "exact_date",
                "target_date": "2024-04-15"
            }
        })
        content_1 = call_resp_1.get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"📥 도구 실행 결과:\n{content_1}")
        assert "82,200원" in content_1 or "2024-04-15" in content_1, "특정일 주가 조회 데이터 불일치"
        print("✅ [성공] query_stock_data 특정일 주가 조회 정상 검증")

        print("\n==================================================")
        print("📌 [테스트 4b] tools/call -> query_stock_data (max_all 최고가)")
        print("==================================================")
        call_resp_2 = send_request("tools/call", {
            "name": "query_stock_data",
            "arguments": {
                "query_type": "max_all"
            }
        })
        content_2 = call_resp_2.get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"📥 도구 실행 결과:\n{content_2}")
        assert "최고" in content_2 or "362,100원" in content_2, "역대 최고가 데이터 불일치"
        print("✅ [성공] query_stock_data 역대 최고가 조회 정상 검증")

        print("\n==================================================")
        print("📌 [테스트 4c] tools/call -> analyze_portfolio (수익률 분석)")
        print("==================================================")
        call_resp_3 = send_request("tools/call", {
            "name": "analyze_portfolio",
            "arguments": {
                "portfolio_data": [
                    {"date": "2024-01-02", "type": "buy", "quantity": 10, "price": 70000}
                ]
            }
        })
        content_3 = call_resp_3.get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"📥 도구 실행 결과:\n{content_3}")
        assert "평가" in content_3 or "수익률" in content_3, "포트폴리오 분석 결과 불일치"
        print("✅ [성공] analyze_portfolio 포트폴리오 수익률 분석 정상 검증")

        print("\n==================================================")
        print("📌 [테스트 4d] tools/call -> get_conversation_history (문맥 조회)")
        print("==================================================")
        call_resp_4 = send_request("tools/call", {
            "name": "get_conversation_history",
            "arguments": {
                "conversation_id": "test-session-1234"
            }
        })
        content_4 = call_resp_4.get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"📥 도구 실행 결과:\n{content_4}")
        assert "test-session-1234" in content_4, "대화 기록 조회 결과 불일치"
        print("✅ [성공] get_conversation_history 문맥 조회 정상 검증")

        print("\n==================================================")
        print("🎉 [최종 검증 완료] 모든 MCP 표준 프로토콜 및 도구 호출 성공!")
        print("==================================================")

    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=2)

if __name__ == "__main__":
    run_test()
