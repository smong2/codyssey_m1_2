# 1. 파이썬 표준 라이브러리 (Standard Library)
import calendar
import json
import os
import re
import sqlite3
import statistics
from datetime import datetime
from typing import Literal

# 2. 외부 서드파티 라이브러리 (Third-party Packages)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
from pydantic import BaseModel

# 3. 로컬 프로젝트 내부 모듈 (Local Application)
from api.lib.ai_service import generate_ai_reply

# 전역 활성 대화방 ID (세션 추적 및 도구 기본값 제공용)
_CURRENT_ACTIVE_CONV_ID = ""

load_dotenv()

# FastAPI 앱 초기화
app = FastAPI(
    title="AI Investment Assistant API",
    description="삼성전자 AI 투자 비서 백엔드 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firebase Firestore 클라이언트 초기화 함수
def get_firestore_client():
    if not firebase_admin._apps:
        firebase_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        try:
            if firebase_env and firebase_env.strip().startswith("{"):
                cred_dict = json.loads(firebase_env)
                cred = credentials.Certificate(cred_dict)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                default_key_path = os.path.join(base_dir, "serviceAccountKey.json")
                key_path = firebase_env if firebase_env else default_key_path
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"❌ Firebase 초기화 오류: {e}")
    return firestore.client()

# ==========================================
# 🚀 SQLite 캐싱 로직 (Firestore 읽기 최적화)
# ==========================================
DB_PATH = "api/stock_cache.db"

def init_sqlite_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            value REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

init_sqlite_db()

def get_cached_stock_data_with_version():
    db = get_firestore_client()
    
    meta_doc = db.collection("metadata").document("stock_status").get()
    remote_version = str(meta_doc.to_dict().get("version", 1)) if meta_doc.exists else "1"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM meta WHERE key = 'version'")
    row = cursor.fetchone()
    local_version = row[0] if row else "0"
    
    cursor.execute("SELECT COUNT(*) FROM stock_data")
    count = cursor.fetchone()[0]
    
    if local_version == remote_version and count > 0:
        cursor.execute("SELECT date, open, high, low, close, value FROM stock_data ORDER BY date DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "date": r[0], "open": r[1], "high": r[2], 
                "low": r[3], "close": r[4], "value": r[5]
            } for r in rows
        ]
    
    docs = db.collection("stock_data").order_by("date", direction=firestore.Query.DESCENDING).limit(2500).stream()
    items = []
    
    cursor.execute("DELETE FROM stock_data")
    
    for doc in docs:
        data = doc.to_dict()
        items.append(data)
        cursor.execute("""
            INSERT OR REPLACE INTO stock_data (date, open, high, low, close, value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("date"),
            data.get("open", data.get("value")),
            data.get("high", data.get("value")),
            data.get("low", data.get("value")),
            data.get("close", data.get("value")),
            data.get("value", 0)
        ))
        
    cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('version', ?)", (remote_version,))
    conn.commit()
    conn.close()
    
    return items

def parse_flexible_date(date_str: str) -> str:
    """
    사용자나 AI가 '2024년 5월 10일', '2024년 5월', '2023년' 등으로 입력해도 
    알아서 YYYY-MM-DD 형식으로 안전하게 변환합니다.
    """
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    
    # 1. "2024년 5월 10일" 형태 파싱
    match_ymd = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_str)
    if match_ymd:
        y, m, d = match_ymd.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
        
    # 2. "2024년 5월" 형태 파싱 (월의 시작일인 01일로 자동 세팅)
    match_ym = re.search(r'(\d{4})년\s*(\d{1,2})월', date_str)
    if match_ym:
        y, m = match_ym.groups()
        return f"{y}-{int(m):02d}-01"

    # 3. "2023년" 형태 파싱 (연도의 시작일인 01-01로 세팅)
    match_y = re.search(r'^(\d{4})년?$', date_str)
    if match_y:
        return f"{match_y.group(1)}-01-01"

    # 4. 일반적인 YYYY-MM-DD, YYYY.MM.DD 등 포맷 파싱 시도
    for fmt in ("%Y-%m-%d", "%Y-%m-%#d", "%Y-%m", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    return date_str

def auto_expand_dates(start_date: str, end_date: str, target_date: str):
    """
    start_date, end_date, target_date의 누락이나 축약 형태(예: '2023년', '2024년 4월')를 분석하여
    단일 일자 조회인지, 기간 조회인지 자동으로 완성 및 보정합니다.
    """
    start = (start_date or "").strip()
    end = (end_date or "").strip()
    target = (target_date or "").strip()

    if target:
        return "", "", parse_flexible_date(target)

    # 1. start_date가 특정 단일 날짜(YYYY-MM-DD)이고 end가 없는 경우 -> 단일 날짜(target_date)로 간주
    m_full = re.match(r'^(\d{4})[-/.년]\s*(\d{1,2})[-/.월]\s*(\d{1,2})일?$', start)
    if m_full and not end:
        y, m, d = m_full.groups()
        return "", "", f"{y}-{int(m):02d}-{int(d):02d}"

    # 2. start_date가 연도(YYYY or YYYY년)이고 end가 없는 경우 -> 해당 연도 전체(1월 1일 ~ 12월 31일)로 확장
    m_year = re.match(r'^(\d{4})년?$', start)
    if m_year and not end:
        y = m_year.group(1)
        return f"{y}-01-01", f"{y}-12-31", ""

    # 3. start_date가 연-월(YYYY-MM or YYYY년 MM월)이고 end가 없는 경우 -> 해당 월 전체(1일 ~ 마지막일)로 확장
    m_ym = re.match(r'^(\d{4})[-/.년]\s*(\d{1,2})월?$', start)
    if m_ym and not end:
        y, m = int(m_ym.group(1)), int(m_ym.group(2))
        last_day = calendar.monthrange(y, m)[1]
        return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last_day:02d}", ""

    return parse_flexible_date(start), parse_flexible_date(end), parse_flexible_date(target)

# ==========================================
# 🛠️ AI Function Calling 용 신규 도구 3종 세트
# ==========================================
def query_stock_data(
    query_type: str = "range_summary",
    start_date: str = "",
    end_date: str = "",
    target_date: str = "",
    intent: str = "",
    **kwargs
) -> str:
    """[삼성전자 10년치 과거 주가 DB(SQLite) 전용 조회 도구]
    삼성전자의 2016년부터 현재까지의 전체 일별 주가(종가, 시가, 고가, 저가, 거래량 등)와 통계를 검색합니다.
    사용자가 '과거 데이터', '이전 데이터', '특정 날짜(특정일)', '특정 기간(연도/월)', '역대 최고가/최저가', '주가 통계' 등을 질문할 때 반드시 이 도구를 호출해야 합니다.

    Args:
        query_type: 조회 유형 ('range_summary', 'exact_date', 'max_all', 'min_all' 중 택1, 기본값: 'range_summary')
        start_date: 기간 시작일 (형식: YYYY-MM-DD, 예: '2023-01-01')
        end_date: 기간 종료일 (형식: YYYY-MM-DD, 예: '2023-12-31')
        target_date: 특정 단일 일자 (형식: YYYY-MM-DD, 예: '2024-05-10')
        intent: query_type과 동일한 보조 파라미터 (호환성용)
    """
    # 1. intent와 query_type 통합 및 파라미터 자동 정규화
    q_type = (intent or query_type or "range_summary").strip().lower()
    start_date, end_date, target_date = auto_expand_dates(start_date, end_date, target_date)

    print(f"\n🔍 [도구 실행] query_stock_data 호출됨")
    print(f"   - 정규화된 유형(query_type): {q_type}")
    print(f"   - 파라미터: start={start_date}, end={end_date}, target={target_date}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    notice_header = "[💡 시스템 알림: SQLite 주가 데이터베이스(10년치 데이터 기록)를 성공적으로 조회했습니다.]\n\n"

    try:
        # [유형 1] 역대 최고 종가
        if any(k in q_type for k in ["max", "highest", "peak", "최고"]):
            cursor.execute("SELECT date, close, value FROM stock_data WHERE close IS NOT NULL OR value IS NOT NULL")
            rows = cursor.fetchall()
            if not rows:
                return notice_header + "데이터가 존재하지 않습니다."
            max_row = max(rows, key=lambda x: float(x[1] if x[1] is not None else x[2]))
            max_val = int(float(max_row[1] if max_row[1] is not None else max_row[2]))
            return notice_header + f"삼성전자 역대 최고 종가: {max_val:,}원 (기록일자: {max_row[0]})\n🚨 AI 지시사항: 이 수치와 날짜를 사실 그대로 마크다운 표로 깔끔하게 정리하여 안내하세요."

        # [유형 2] 역대 최저 종가
        if any(k in q_type for k in ["min", "lowest", "bottom", "최저"]):
            cursor.execute("SELECT date, close, value FROM stock_data WHERE close IS NOT NULL OR value IS NOT NULL")
            rows = cursor.fetchall()
            if not rows:
                return notice_header + "데이터가 존재하지 않습니다."
            min_row = min(rows, key=lambda x: float(x[1] if x[1] is not None else x[2]))
            min_val = int(float(min_row[1] if min_row[1] is not None else min_row[2]))
            return notice_header + f"삼성전자 역대 최저 종가: {min_val:,}원 (기록일자: {min_row[0]})\n🚨 AI 지시사항: 이 수치와 날짜를 사실 그대로 마크다운 표로 깔끔하게 정리하여 안내하세요."

        # [유형 3] 특정 단일 일자(하루) 주가 조회
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
                    f"[{search_date} 삼성전자 주가 기록 (단일 일자)]\n"
                    f"- 종가: {close_p:,}원\n"
                    f"- 시가: {open_p:,}원\n"
                    f"- 고가: {high_p:,}원\n"
                    f"- 저가: {low_p:,}원\n"
                    f"🚨 AI 지시사항: 위 일자별 시가/고가/저가/종가 데이터를 마크다운 표로 제시하세요."
                )

            # 휴장일(주말/공휴일)인 경우 직전 거래일 자동 안내
            cursor.execute("SELECT date, open, high, low, close, value FROM stock_data WHERE date < ? ORDER BY date DESC LIMIT 1", (search_date,))
            row_prev = cursor.fetchone()
            if row_prev:
                close_p = int(float(row_prev[4] if row_prev[4] is not None else row_prev[5]))
                return notice_header + (
                    f"요청하신 {search_date}는 주식시장 휴장일(주말 또는 공휴일)입니다.\n"
                    f"- 가장 가까운 직전 거래일({row_prev[0]})의 종가는 {close_p:,}원이었습니다.\n"
                    f"🚨 AI 지시사항: 휴장일임을 안내하고 직전 거래일의 데이터를 친절히 설명하세요."
                )
            return notice_header + f"해당 일자({search_date}) 이전의 과거 데이터가 DB에 존재하지 않습니다."

        # [유형 4] 특정 기간/연도/월 주가 통계 및 흐름 조회
        if start_date and end_date:
            cursor.execute("SELECT date, open, high, low, close, value FROM stock_data WHERE date BETWEEN ? AND ? ORDER BY date ASC", (start_date, end_date))
            rows = cursor.fetchall()
            if not rows:
                return notice_header + f"요청하신 기간 ({start_date} ~ {end_date})에 해당하는 주가 데이터가 DB에 없습니다."

            close_data = [(r[0], float(r[4] if r[4] is not None else r[5])) for r in rows]
            high_data = [(r[0], float(r[2] if r[2] is not None else r[4])) for r in rows]
            low_data = [(r[0], float(r[3] if r[3] is not None else r[4])) for r in rows]

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
                f"- 해당 기간 시작일({close_data[0][0]}) 종가: {start_p:,}원\n"
                f"- 해당 기간 종료일({close_data[-1][0]}) 종가: {end_p:,}원\n"
                f"- 기간 내 등락률: {return_rate:+}%\n"
                f"- 기간 최고 종가: {max_val:,}원 (기록일자: {max_record[0]})\n"
                f"- 기간 최저 종가: {min_val:,}원 (기록일자: {min_record[0]})\n"
                f"- 기간 평균 종가: {avg_val:,}원\n"
                f"🚨 AI 지시사항: 위 통계 지표를 마크다운 표(|항목|값|)로 작성하고, 추세를 요약해 답변하세요."
            )

        # [유형 5] 일자 미지정 / 일반 '과거 데이터', '이전 데이터' 조회 요청
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM stock_data")
        cnt, min_d, max_d = cursor.fetchone()

        cursor.execute("SELECT date, close, value FROM stock_data WHERE close IS NOT NULL OR value IS NOT NULL")
        all_rows = cursor.fetchall()
        max_row = max(all_rows, key=lambda x: float(x[1] if x[1] is not None else x[2]))
        min_row = min(all_rows, key=lambda x: float(x[1] if x[1] is not None else x[2]))
        max_val = int(float(max_row[1] if max_row[1] is not None else max_row[2]))
        min_val = int(float(min_row[1] if min_row[1] is not None else min_row[2]))

        cursor.execute("SELECT date, open, high, low, close, value FROM stock_data ORDER BY date DESC LIMIT 5")
        recent_rows = cursor.fetchall()
        recent_list = []
        for r in recent_rows:
            c = int(float(r[4] if r[4] is not None else r[5]))
            recent_list.append(f"| {r[0]} | {c:,}원 |")
        recent_table = "\n".join(recent_list)

        return notice_header + (
            f"[삼성전자 10년치 전체 과거 주가 DB 보유 현황]\n"
            f"- 전체 수집 기간: {min_d} ~ {max_d} (총 {cnt:,} 영업일 데이터 확보)\n"
            f"- 10년 역대 최고 종가: {max_val:,}원 ({max_row[0]})\n"
            f"- 10년 역대 최저 종가: {min_val:,}원 ({min_row[0]})\n\n"
            f"[최근 5거래일 종가 요약]\n"
            f"| 날짜 | 종가 |\n"
            f"|---|---|\n"
            f"{recent_table}\n\n"
            f"💡 추가 안내: 특정 연도(예: 2023년), 특정 월(예: 2024년 4월), 혹은 특정 날짜(예: 2024년 5월 10일)를 말씀해주시면 해당 시점의 상세 통계를 즉시 확인해 드립니다.\n"
            f"🚨 AI 지시사항: 위 데이터와 최근 종가 표를 그대로 사용자에게 깔끔하게 보여주세요."
        )

    finally:
        conn.close()

def analyze_portfolio(**kwargs) -> str:
    """[사용자 포트폴리오(가상 투자 기록) 전용 조회 도구]
    사용자의 가상 투자 내역(매수/매도), 현재 보유 주식 수량, 총 투자금, 평균 매수가(평단가), 확정 실현 손익, 현재 주가와 대조한 실시간 평가 손익 및 수익률을 분석합니다.
    사용자가 '내 주식', '포트폴리오', '내 수익률', '평단가', '몇 주 갖고 있어?', '가상 투자 내역', '손익' 등을 질문할 때 반드시 이 도구를 호출하세요.
    """
    print(f"\n🔍 [도구 실행] analyze_portfolio 실행됨\n")
    notice_header = "[💡 시스템 알림: 파이어베이스 가상 투자 포트폴리오를 성공적으로 조회했습니다.]\n\n"
    
    try:
        db = get_firestore_client()
        docs = list(db.collection("portfolio").order_by("date").stream())
        
        if not docs:
            return notice_header + (
                "현재 등록된 가상 투자 기록이 없습니다.\n"
                "- 웹 대시보드의 '💼 나의 가상 투자 기록' 입력창에서 매수/매도 기록을 추가하시면 현재 주가와 연동된 실시간 수익률 및 평가 손익을 분석해 드릴 수 있습니다."
            )

        total_buy_qty = 0
        total_buy_amount = 0.0
        total_sell_qty = 0
        total_sell_amount = 0.0
        
        for doc in docs:
            item = doc.to_dict()
            qty = int(item.get("quantity", 0))
            price = float(item.get("price", 0))
            trade_type = item.get("trade_type", "buy")
            
            if trade_type == "buy":
                total_buy_qty += qty
                total_buy_amount += (qty * price)
            else:
                total_sell_qty += qty
                total_sell_amount += (qty * price)
                
        current_qty = total_buy_qty - total_sell_qty
        avg_price = (total_buy_amount / total_buy_qty) if total_buy_qty > 0 else 0.0
        realized_profit = total_sell_amount - (avg_price * total_sell_qty)

        # SQLite에서 가장 최신 종가 가져오기 (실시간 평가 손익 계산용)
        latest_price = 0
        latest_date = ""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT date, close, value FROM stock_data ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            latest_date = row[0]
            latest_price = int(float(row[1] if row[1] is not None else row[2]))

        result_text = (
            f"[가상 투자 포트폴리오 분석 결과]\n"
            f"- 누적 매수: {total_buy_qty:,}주 (총 {int(total_buy_amount):,}원)\n"
            f"- 누적 매도: {total_sell_qty:,}주 (총 {int(total_sell_amount):,}원)\n"
            f"- 현재 보유 수량: {current_qty:,}주\n"
            f"- 평균 매수 단가(평단가): {int(avg_price):,}원\n"
            f"- 확정 실현 손익: {int(realized_profit):+,}원\n"
        )

        if current_qty > 0 and latest_price > 0:
            eval_val = current_qty * latest_price
            invested_val = current_qty * avg_price
            unrealized_profit = eval_val - invested_val
            unrealized_rate = ((latest_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0.0

            result_text += (
                f"\n[현재 주가({latest_date} 기준: {latest_price:,}원) 대조 실시간 평가]\n"
                f"- 보유 주식 평가액: {int(eval_val):,}원\n"
                f"- 평가 손익(미실현 손익): {int(unrealized_profit):+,}원\n"
                f"- 평가 수익률: {unrealized_rate:+.2f}%\n"
            )
        elif current_qty == 0:
            result_text += "\n- 현재 보유 주식이 전량 매도되어 보유 수량은 0주입니다.\n"

        result_text += "\n🚨 AI 지시사항: 위 포트폴리오 현황을 마크다운 표로 가독성 높게 작성하여 투자자에게 답변하세요."
        return notice_header + result_text
    except Exception as e:
        return notice_header + f"포트폴리오 조회 중 오류가 발생했습니다: {str(e)}"

def get_conversation_history(conversation_id: str = "", **kwargs) -> str:
    """[과거 대화 기록(채팅 히스토리) 전용 조회 도구]
    이전 대화 맥락이나 과거 질문/답변 내용을 조회합니다.
    사용자가 '아까 내가 뭐라고 했지?', '방금 추천해준 가격이 뭐였어?', '이전 대화 내용 기억해?' 등 대화 히스토리를 물어볼 때 반드시 이 도구를 호출하세요.
    
    Args:
        conversation_id: 조회할 대화방 ID. 생략 시 현재 접속된 대화방의 이전 기록을 자동 조회합니다.
    """
    target_id = (conversation_id or "").strip()
    if not target_id or target_id == "None":
        target_id = _CURRENT_ACTIVE_CONV_ID

    print(f"\n🔍 [도구 실행] get_conversation_history 호출됨 | ID: {target_id}\n")
    notice_header = "[💡 시스템 알림: 파이어베이스 대화 기록(이전 채팅 내역)을 성공적으로 조회했습니다.]\n\n"
    
    if not target_id or target_id == "None":
        return notice_header + "현재 대화방은 새로 시작된 첫 번째 대화이므로 이전 대화 기록이 존재하지 않습니다."
        
    try:
        db = get_firestore_client()
        doc = db.collection("conversations").document(target_id).get()
        if not doc.exists:
            return notice_header + f"대화방 ID '{target_id}'에 해당하는 대화 기록을 찾을 수 없습니다."
            
        messages = doc.to_dict().get("messages", [])
        if not messages:
            return notice_header + "해당 대화방에 저장된 메시지가 아직 없습니다."

        history_text = notice_header + f"[대화방 ID: {target_id} 과거 대화 내역 (최근 순)]\n"
        # 최근 10개 메시지만 압축 추출하여 반환
        recent_messages = messages[-10:]
        for msg in recent_messages:
            role = "사용자" if msg.get("role") == "user" else "AI"
            history_text += f"- **{role}**: {msg.get('content')}\n"
            
        history_text += "\n🚨 AI 지시사항: 위 대화 내역을 바탕으로 사용자가 방금 질문한 문맥에 맞춰 정확하게 답변하세요."
        return history_text
    except Exception as e:
        return notice_header + f"대화 기록 조회 실패: {str(e)}"
# ==========================================
# 🚀 API 엔드포인트
# ==========================================

@app.get("/")
def health_check():
    return {
        "status": "success",
        "message": "🚀 AI Investment Assistant 백엔드가 정상적으로 구동 중입니다!"
    }

@app.get("/api/data")
def get_stock_data(limit: int = Query(30, description="조회할 데이터 개수")):
    try:
        items = get_cached_stock_data_with_version()
        results = items[:limit]
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")

@app.get("/api/data/summary")
def get_data_summary(limit: int = 100):
    try:
        items = get_cached_stock_data_with_version()
        items = items[:limit]
        
        if not items:
            return {"status": "error", "message": "데이터가 없습니다."}
            
        prices = [item.get("close", item.get("value", 0)) for item in items]
        dates = [item["date"] for item in items]
        chrono_prices = prices[::-1]
        
        max_p = max(prices)
        min_p = min(prices)
        avg_p = sum(prices) / len(prices)
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        start_price = chrono_prices[0]
        end_price = chrono_prices[-1]
        return_rate = ((end_price - start_price) / start_price) * 100 if start_price else 0
        
        peak = chrono_prices[0]
        max_drawdown = 0
        for p in chrono_prices:
            if p > peak: peak = p
            dd = (p - peak) / peak if peak else 0
            if dd < max_drawdown: max_drawdown = dd
        mdd = max_drawdown * 100
        
        trend = "유지"
        if len(prices) >= 2:
            trend = "상승" if prices[0] > prices[1] else "하락" if prices[0] < prices[1] else "유지"

        return {
            "status": "success",
            "summary": {
                "period": f"{dates[-1]} ~ {dates[0]}",
                "count": len(prices),
                "current_price": end_price,
                "max": max_p,
                "min": min_p,
                "average": round(avg_p, 2),
                "trend": trend,
                "volatility": round(volatility, 2),
                "return_rate": round(return_rate, 2),
                "mdd": round(mdd, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PortfolioItem(BaseModel):
    trade_type: Literal["buy", "sell"] = "buy"
    date: str
    price: float
    quantity: int

@app.get("/api/portfolio")
def get_portfolio():
    try:
        db = get_firestore_client()
        docs = db.collection("portfolio").order_by("date", direction=firestore.Query.ASCENDING).stream()
        results = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio")
def add_portfolio(item: PortfolioItem):
    try:
        db = get_firestore_client()
        doc_ref = db.collection("portfolio").document()
        doc_ref.set(item.dict())
        return {"status": "success", "message": "추가되었습니다.", "id": doc_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/portfolio/{doc_id}")
def delete_portfolio(doc_id: str):
    try:
        db = get_firestore_client()
        db.collection("portfolio").document(doc_id).delete()
        return {"status": "success", "message": "삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

class ConversationTitleUpdate(BaseModel):
    title: str

@app.post("/api/chat")
def chat_with_ai(request: ChatRequest):
    global _CURRENT_ACTIVE_CONV_ID
    _CURRENT_ACTIVE_CONV_ID = request.conversation_id or ""

    try:
        db = get_firestore_client()
        all_stock = get_cached_stock_data_with_version()
        stock_items = all_stock[:30]
        
        context_data = "[최근 1개월 삼성전자 주가 기초 데이터 (참고용 요약)]\n"
        
        if stock_items:
            prices = [item.get('close', item.get('value', 0)) for item in stock_items]
            chrono_prices = prices[::-1]
            max_p = max(prices)
            min_p = min(prices)
            avg_p = sum(prices) / len(prices)
            start_price = chrono_prices[0]
            end_price = chrono_prices[-1]
            return_rate = ((end_price - start_price) / start_price) * 100 if start_price else 0
            
            context_data += f"- 기준일: {stock_items[-1]['date']} ~ {stock_items[0]['date']}\n"
            context_data += f"- 최근 종가: {end_price:,}원\n"
            context_data += f"- 최고/최저가: {max_p:,}원 / {min_p:,}원 (평균: {int(avg_p):,}원)\n"
            context_data += f"- 기간 수익률: {round(return_rate, 2)}%\n"
        else:
            context_data += "주가 데이터를 불러오지 못했습니다.\n"

        current_conv_id = request.conversation_id or "None"
        context_data += (
            f"\n[현재 접속된 대화방 상태]\n"
            f"- 대화방 ID: {current_conv_id}\n"
            f"- 🚨 필수 원칙: 위 기초 데이터 외에 '과거 데이터', '이전 데이터', '특정일', '특정 기간(연도/월)', '역대 최고/최저가'를 물어보면 자의적으로 답변하지 말고 반드시 query_stock_data 도구를 호출하여 조회하세요.\n"
            f"- 포트폴리오(투자 내역, 수익률, 평단가) 질문은 analyze_portfolio 도구를, 이전 대화 내용은 get_conversation_history 도구를 호출하세요.\n"
        )
            
        ai_tools = [query_stock_data, analyze_portfolio, get_conversation_history]
        reply = generate_ai_reply(request.message, context_data, tools=ai_tools)
        
        timestamp = datetime.now().isoformat()
        if request.conversation_id:
            conv_ref = db.collection("conversations").document(request.conversation_id)
            conv_ref.update({
                "updated_at": timestamp,
                "messages": firestore.ArrayUnion([{"role": "user", "content": request.message}, {"role": "ai", "content": reply}])
            })
            conv_id = request.conversation_id
        else:
            title = request.message[:15] + "..." if len(request.message) > 15 else request.message
            _, doc_ref = db.collection("conversations").add({
                "title": title, "updated_at": timestamp,
                "messages": [{"role": "user", "content": request.message}, {"role": "ai", "content": reply}]
            })
            conv_id = doc_ref.id
            
        return {"status": "success", "reply": reply, "conversation_id": conv_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
def get_conversation_list():
    try:
        db = get_firestore_client()
        docs = db.collection("conversations").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
        results = [{"id": doc.id, "title": doc.to_dict().get("title", "새 대화")} for doc in docs]
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conv_id}")
def get_conversation_detail(conv_id: str):
    try:
        db = get_firestore_client()
        doc = db.collection("conversations").document(conv_id).get()
        if doc.exists:
            return {"status": "success", "data": doc.to_dict()}
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    try:
        db = get_firestore_client()
        db.collection("conversations").document(conv_id).delete()
        return {"status": "success", "message": "삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/conversations/{conv_id}")
def update_conversation_title(conv_id: str, data: ConversationTitleUpdate):
    try:
        db = get_firestore_client()
        db.collection("conversations").document(conv_id).update({"title": data.title})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))