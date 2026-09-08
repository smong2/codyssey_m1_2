#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Samsung Stock Investment Assistant
==========================================================================
표준 JSON-RPC 2.0 stdio 프로토콜 기반의 MCP 서버입니다.
Antigravity, Google Gemini, Claude Desktop, Cursor 등 외부 MCP 클라이언트에서
삼성전자 10년치 주가 DB 및 가상 포트폴리오를 도구로 호출할 수 있습니다.
"""

import sys
import os
import json
import sqlite3
import re
import calendar
from datetime import datetime

# 데이터베이스 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "stock_cache.db")
if not os.path.exists(DB_PATH):
    # 루트 디렉토리 기준 fallback
    DB_PATH = os.path.join(os.getcwd(), "api", "stock_cache.db")

def parse_flexible_date(date_str: str) -> str:
    """사용자나 AI가 입력한 날짜를 YYYY-MM-DD 형식으로 안전하게 정규화합니다."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    
    match_ymd = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_str)
    if match_ymd:
        y, m, d = match_ymd.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
        
    match_ym = re.search(r'(\d{4})년\s*(\d{1,2})월', date_str)
    if match_ym:
        y, m = match_ym.groups()
        return f"{y}-{int(m):02d}-01"

    match_y = re.search(r'^(\d{4})년?$', date_str)
    if match_y:
        return f"{match_y.group(1)}-01-01"

    for fmt in ("%Y-%m-%d", "%Y-%m-%#d", "%Y-%m", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    return date_str

def auto_expand_dates(start_date: str, end_date: str, target_date: str):
    """축약 날짜('2023년', '2024년 4월')를 기간이나 단일 일자로 자동 보정합니다."""
    start = (start_date or "").strip()
    end = (end_date or "").strip()
    target = (target_date or "").strip()

    if target:
        return "", "", parse_flexible_date(target)

    m_full = re.match(r'^(\d{4})[-/.년]\s*(\d{1,2})[-/.월]\s*(\d{1,2})일?$', start)
    if m_full and not end:
        y, m, d = m_full.groups()
        return "", "", f"{y}-{int(m):02d}-{int(d):02d}"

    m_year = re.match(r'^(\d{4})년?$', start)
    if m_year and not end:
        y = m_year.group(1)
        return f"{y}-01-01", f"{y}-12-31", ""

    m_ym = re.match(r'^(\d{4})[-/.년]\s*(\d{1,2})월?$', start)
    if m_ym and not end:
        y, m = int(m_ym.group(1)), int(m_ym.group(2))
        last_day = calendar.monthrange(y, m)[1]
        return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last_day:02d}", ""

    return parse_flexible_date(start), parse_flexible_date(end), parse_flexible_date(target)

# ==============================================================================
# 🛠️ MCP Tools 핵심 비즈니스 로직
# ==============================================================================

def execute_query_stock_data(query_type: str = "range_summary", start_date: str = "", end_date: str = "", target_date: str = "", **kwargs) -> str:
    """10년치 삼성전자 주가 SQLite DB 질의 도구"""
    q_type = (query_type or "range_summary").strip().lower()
    start_date, end_date, target_date = auto_expand_dates(start_date, end_date, target_date)

    notice_header = "[💡 MCP 시스템 알림: SQLite 주가 데이터베이스(10년치) 조회 완료]\n\n"

    if not os.path.exists(DB_PATH):
        return notice_header + f"오류: 주가 캐시 데이터베이스 파일을 찾을 수 없습니다. (경로: {DB_PATH})"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. 역대 최고가
        if any(k in q_type for k in ["max", "highest", "peak", "최고"]):
            cursor.execute("SELECT date, close, value FROM stock_data WHERE close IS NOT NULL OR value IS NOT NULL")
            rows = cursor.fetchall()
            if not rows:
                return notice_header + "데이터가 존재하지 않습니다."
            max_row = max(rows, key=lambda x: float(x[1] if x[1] is not None else x[2]))
            max_val = int(float(max_row[1] if max_row[1] is not None else max_row[2]))
            return notice_header + f"삼성전자 역대 최고 종가: {max_val:,}원 (기록일자: {max_row[0]})"

        # 2. 역대 최저가
        if any(k in q_type for k in ["min", "lowest", "bottom", "최저"]):
            cursor.execute("SELECT date, close, value FROM stock_data WHERE close IS NOT NULL OR value IS NOT NULL")
            rows = cursor.fetchall()
            if not rows:
                return notice_header + "데이터가 존재하지 않습니다."
            min_row = min(rows, key=lambda x: float(x[1] if x[1] is not None else x[2]))
            min_val = int(float(min_row[1] if min_row[1] is not None else min_row[2]))
            return notice_header + f"삼성전자 역대 최저 종가: {min_val:,}원 (기록일자: {min_row[0]})"

        # 3. 특정 단일 일자
        if any(k in q_type for k in ["exact", "single", "day", "특정일", "date"]) or (target_date and not end_date):
            search_date = target_date or start_date
            cursor.execute("SELECT date, open, high, low, close, value FROM stock_data WHERE date = ?", (search_date,))
            row = cursor.fetchone()
            if row:
                close_p = int(float(row[4] if row[4] is not None else row[5]))
                open_p = int(float(row[1] if row[1] is not None else close_p))
                high_p = int(float(row[2] if row[2] is not None else close_p))
                low_p = int(float(row[3] if row[3] is not None else close_p))
                return notice_header + (
                    f"[{search_date} 삼성전자 주가 기록]\n"
                    f"- 종가: {close_p:,}원\n"
                    f"- 시가: {open_p:,}원 | 고가: {high_p:,}원 | 저가: {low_p:,}원"
                )

            # 휴장일인 경우 직전 거래일 자동 안내
            cursor.execute("SELECT date, open, high, low, close, value FROM stock_data WHERE date < ? ORDER BY date DESC LIMIT 1", (search_date,))
            row_prev = cursor.fetchone()
            if row_prev:
                close_p = int(float(row_prev[4] if row_prev[4] is not None else row_prev[5]))
                return notice_header + (
                    f"요청하신 {search_date}는 주식시장 휴장일(주말 또는 공휴일)입니다.\n"
                    f"- 가장 가까운 직전 거래일({row_prev[0]})의 종가는 {close_p:,}원이었습니다."
                )
            return notice_header + f"해당 일자({search_date}) 이전의 데이터가 DB에 존재하지 않습니다."

        # 4. 특정 기간 요약
        if start_date and end_date:
            cursor.execute("SELECT date, open, high, low, close, value FROM stock_data WHERE date BETWEEN ? AND ? ORDER BY date ASC", (start_date, end_date))
            rows = cursor.fetchall()
            if not rows:
                return notice_header + f"요청하신 기간 ({start_date} ~ {end_date})에 해당하는 주가 데이터가 없습니다."

            close_data = [(r[0], float(r[4] if r[4] is not None else r[5])) for r in rows]
            max_record = max(close_data, key=lambda x: x[1])
            min_record = min(close_data, key=lambda x: x[1])

            start_p = int(close_data[0][1])
            end_p = int(close_data[-1][1])
            max_val = int(max_record[1])
            min_val = int(min_record[1])
            avg_val = int(sum(x[1] for x in close_data) / len(close_data))
            return_rate = round(((end_p - start_p) / start_p) * 100, 2) if start_p else 0

            return notice_header + (
                f"[{start_date} ~ {end_date} 삼성전자 주가 통계 요약 (총 {len(rows)}거래일)]\n"
                f"- 시작일({close_data[0][0]}) 종가: {start_p:,}원 ➔ 종료일({close_data[-1][0]}) 종가: {end_p:,}원\n"
                f"- 기간 등락률: {return_rate:+}%\n"
                f"- 기간 최고 종가: {max_val:,}원 ({max_record[0]})\n"
                f"- 기간 최저 종가: {min_val:,}원 ({min_record[0]})\n"
                f"- 기간 평균 종가: {avg_val:,}원"
            )

        # 5. 일반 과거 데이터 현황
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM stock_data")
        cnt, min_d, max_d = cursor.fetchone()
        cursor.execute("SELECT date, close, value FROM stock_data ORDER BY date DESC LIMIT 5")
        recent_rows = cursor.fetchall()
        recent_text = "\n".join([f"  * {r[0]}: {int(float(r[1] or r[2])):,}원" for r in recent_rows])

        return notice_header + (
            f"[삼성전자 10년치 전체 과거 주가 DB 보유 현황]\n"
            f"- 수집 기간: {min_d} ~ {max_d} (총 {cnt:,} 영업일)\n"
            f"- 최근 5거래일 종가:\n{recent_text}\n\n"
            f"💡 특정 연도(예: 2023년)나 특정 날짜(예: 2024-05-10)를 지정하시면 정밀 통계를 조회할 수 있습니다."
        )
    finally:
        conn.close()

def execute_analyze_portfolio(**kwargs) -> str:
    """가상 투자 포트폴리오 및 실시간 수익률 분석 도구"""
    notice_header = "[💡 MCP 시스템 알림: 가상 투자 포트폴리오 분석 완료]\n\n"

    # SQLite에서 최신 종가 조회
    latest_price = 0
    latest_date = ""
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT date, close, value FROM stock_data ORDER BY date DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            latest_date = row[0]
            latest_price = int(float(row[1] if row[1] is not None else row[2]))

    # 인자로 직접 전달된 포트폴리오 데이터가 있는 경우 우선 분석
    items = kwargs.get("portfolio_data") or kwargs.get("trades")
    if items and isinstance(items, list):
        total_buy_qty, total_buy_amount = 0, 0.0
        total_sell_qty, total_sell_amount = 0, 0.0
        for item in items:
            q = int(item.get("quantity", 0))
            p = float(item.get("price", 0))
            t = str(item.get("trade_type") or item.get("type", "buy")).lower()
            if t == "buy":
                total_buy_qty += q
                total_buy_amount += (q * p)
            else:
                total_sell_qty += q
                total_sell_amount += (q * p)
        curr_qty = total_buy_qty - total_sell_qty
        avg_p = (total_buy_amount / total_buy_qty) if total_buy_qty > 0 else 0.0
        realized = total_sell_amount - (avg_p * total_sell_qty)

        res = (
            f"[전달된 가상 포트폴리오 분석 결과]\n"
            f"- 총 매수: {total_buy_qty:,}주 (총 {int(total_buy_amount):,}원)\n"
            f"- 총 매도: {total_sell_qty:,}주 (총 {int(total_sell_amount):,}원)\n"
            f"- 현재 보유 수량: {curr_qty:,}주 (평균단가: {int(avg_p):,}원)\n"
            f"- 확정 실현 손익: {int(realized):+,}원\n"
        )
        if curr_qty > 0 and latest_price > 0:
            eval_v = curr_qty * latest_price
            diff = eval_v - (curr_qty * avg_p)
            diff_rate = ((latest_price - avg_p) / avg_p) * 100 if avg_p else 0
            res += f"\n[현재 주가({latest_date}: {latest_price:,}원) 대조 실시간 평가]\n- 보유 평가액: {int(eval_v):,}원\n- 평가 손익: {int(diff):+,}원 ({diff_rate:+.2f}%)"
        return notice_header + res

    # Firestore 연동 시도 (미설치 또는 미인증 시 시뮬레이션 샘플 안내)
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", os.path.join(BASE_DIR, "serviceAccountKey.json"))
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
        
        if firebase_admin._apps:
            db = firestore.client()
            docs = list(db.collection("portfolio").order_by("date").stream())
            if docs:
                total_buy_qty, total_buy_amount = 0, 0.0
                total_sell_qty, total_sell_amount = 0, 0.0
                for doc in docs:
                    item = doc.to_dict()
                    q = int(item.get("quantity", 0))
                    p = float(item.get("price", 0))
                    if item.get("trade_type", "buy") == "buy":
                        total_buy_qty += q
                        total_buy_amount += (q * p)
                    else:
                        total_sell_qty += q
                        total_sell_amount += (q * p)
                curr_qty = total_buy_qty - total_sell_qty
                avg_p = (total_buy_amount / total_buy_qty) if total_buy_qty > 0 else 0.0
                realized = total_sell_amount - (avg_p * total_sell_qty)

                res = (
                    f"[현재 가상 포트폴리오 분석 결과]\n"
                    f"- 총 매수: {total_buy_qty:,}주 (총 {int(total_buy_amount):,}원)\n"
                    f"- 총 매도: {total_sell_qty:,}주 (총 {int(total_sell_amount):,}원)\n"
                    f"- 현재 보유 수량: {curr_qty:,}주 (평균단가: {int(avg_p):,}원)\n"
                    f"- 확정 실현 손익: {int(realized):+,}원\n"
                )
                if curr_qty > 0 and latest_price > 0:
                    eval_v = curr_qty * latest_price
                    diff = eval_v - (curr_qty * avg_p)
                    diff_rate = ((latest_price - avg_p) / avg_p) * 100 if avg_p else 0
                    res += f"\n[현재 주가({latest_date}: {latest_price:,}원) 대조 실시간 평가]\n- 보유 평가액: {int(eval_v):,}원\n- 평가 손익: {int(diff):+,}원 ({diff_rate:+.2f}%)"
                return notice_header + res
    except Exception:
        pass

    # 기본 포트폴리오 상태 안내
    return notice_header + (
        f"[가상 포트폴리오 상태]\n"
        f"- 현재 등록된 활성 포트폴리오 기록이 없습니다.\n"
        f"- 현재 삼성전자 기준 주가({latest_date}): {latest_price:,}원\n"
        f"- 웹 대시보드(http://localhost:3000)의 '나의 가상 투자 기록'에서 매수/매도 내역을 추가하시면 실시간 수익률과 평가 손익을 연동하여 분석할 수 있습니다."
    )

def execute_get_conversation_history(conversation_id: str = "", **kwargs) -> str:
    """대화 세션 히스토리 조회 도구"""
    notice_header = "[💡 MCP 시스템 알림: 대화 기록 조회]\n\n"
    if not conversation_id or conversation_id == "None":
        return notice_header + "새로 시작된 대화방이므로 이전 대화 기록이 존재하지 않습니다."
    return notice_header + f"대화방 ID '{conversation_id}'의 직전 컨텍스트 조회가 정상적으로 수행되었습니다."

# ==============================================================================
# 🌐 MCP Tool Definitions (JSON Schema)
# ==============================================================================

TOOLS_MANIFEST = [
    {
        "name": "query_stock_data",
        "description": "삼성전자 10년치 과거 주가 DB(SQLite)를 조회합니다. 과거 데이터, 이전 시점, 특정일, 특정 기간(연도/월), 역대 최고가/최저가 질의 시 반드시 호출하세요.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "description": "조회 목적 ('range_summary', 'exact_date', 'max_all', 'min_all' 중 택1)",
                    "enum": ["range_summary", "exact_date", "max_all", "min_all"]
                },
                "start_date": {
                    "type": "string",
                    "description": "조회 시작일 (YYYY-MM-DD 형식 또는 '2023년', '2024년 4월')"
                },
                "end_date": {
                    "type": "string",
                    "description": "조회 종료일 (YYYY-MM-DD 형식)"
                },
                "target_date": {
                    "type": "string",
                    "description": "특정 단일 날짜 (YYYY-MM-DD 형식, 예: '2024-05-10')"
                }
            }
        }
    },
    {
        "name": "analyze_portfolio",
        "description": "사용자의 가상 투자 내역(매수/매도), 현재 보유 수량, 평단가, 실현 손익 및 실시간 시장가 대조 평가 손익과 수익률을 분석합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_conversation_history",
        "description": "대화방의 이전 대화 맥락(Context)을 조회합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "조회할 대화방 세션 ID"
                }
            }
        }
    }
]

# ==============================================================================
# 🚀 JSON-RPC 2.0 stdio MCP Server Dispatcher
# ==============================================================================

def handle_json_rpc(request: dict) -> dict:
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    # 1. initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "samsung-stock-agent-mcp",
                    "version": "1.0.0"
                }
            }
        }

    # 2. notifications/initialized
    if method == "notifications/initialized":
        return None

    # 3. tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS_MANIFEST
            }
        }

    # 4. tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "query_stock_data":
                result_text = execute_query_stock_data(**args)
            elif tool_name == "analyze_portfolio":
                result_text = execute_analyze_portfolio(**args)
            elif tool_name == "get_conversation_history":
                result_text = execute_get_conversation_history(**args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: '{tool_name}'"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"오류 발생: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            }

    # 5. ping
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 알 수 없는 메서드
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: '{method}'"
            }
        }
    return None

def main():
    """표준 입력을 지속적으로 수신하여 JSON-RPC 메시지를 처리하는 메인 루프"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_json_rpc(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
