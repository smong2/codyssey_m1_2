import sqlite3
import statistics
import calendar
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
try:
    from firebase_admin import firestore
except ImportError:
    firestore = None
from api.core.database import get_firestore_client, get_sqlite_connection
from api.core.config import DB_PATH

def get_cached_stock_data_with_version() -> List[Dict[str, Any]]:
    """로컬 SQLite 캐시 데이터를 조회하고 필요 시 Firestore와 버전 동기화합니다."""
    db = get_firestore_client()
    remote_version = None
    if db is not None:
        try:
            meta_doc = db.collection("metadata").document("stock_status").get()
            remote_version = str(meta_doc.to_dict().get("version", 1)) if meta_doc.exists else "1"
        except Exception as e:
            print(f"⚠️ Firestore 메타데이터 조회 경고: {e}")

    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM meta WHERE key = 'version'")
    row = cursor.fetchone()
    local_version = row[0] if row else "0"

    cursor.execute("SELECT COUNT(*) FROM stock_data")
    count = cursor.fetchone()[0]

    # 로컬 캐시가 존재하고 버전이 일치하거나, Firestore 연결이 없는 경우 로컬 SQLite 데이터 반환
    if count > 0 and (db is None or remote_version is None or local_version == remote_version):
        cursor.execute("SELECT date, open, high, low, close, value FROM stock_data ORDER BY date DESC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "date": r[0], "open": r[1], "high": r[2],
                "low": r[3], "close": r[4], "value": r[5]
            } for r in rows
        ]

    # Firestore에서 최신 데이터를 가져와 SQLite에 동기화
    if db is not None:
        try:
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
            cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('version', ?)", (remote_version or "1",))
            conn.commit()
            conn.close()
            return items
        except Exception as e:
            print(f"⚠️ Firestore stock_data 동기화 실패 (로컬 캐시 사용): {e}")

    # Firestore 동기화 실패 시 로컬 캐시 반환
    if count > 0:
        cursor.execute("SELECT date, open, high, low, close, value FROM stock_data ORDER BY date DESC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "date": r[0], "open": r[1], "high": r[2],
                "low": r[3], "close": r[4], "value": r[5]
            } for r in rows
        ]

    conn.close()
    return []

def calculate_stock_summary(limit: int = 100) -> Dict[str, Any]:
    """주가 데이터 요약 통계(MDD, 변동성, 추세 등)를 산출합니다."""
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
        if p > peak:
            peak = p
        dd = (p - peak) / peak if peak else 0
        if dd < max_drawdown:
            max_drawdown = dd
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

def parse_flexible_date(date_str: str) -> str:
    """한글/다양한 날짜 형식을 YYYY-MM-DD 형식으로 안전하게 정규화합니다."""
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

def auto_expand_dates(start_date: str, end_date: str, target_date: str) -> Tuple[str, str, str]:
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

def query_stock_data(
    query_type: str = "range_summary",
    start_date: str = "",
    end_date: str = "",
    target_date: str = "",
    intent: str = "",
    **kwargs
) -> str:
    """[삼성전자 10년치 주가 DB 조회 도구] AI 에이전트 전용 Function Calling 도구"""
    q_type = (intent or query_type or "range_summary").strip().lower()
    start_date, end_date, target_date = auto_expand_dates(start_date, end_date, target_date)

    conn = get_sqlite_connection()
    cursor = conn.cursor()
    notice_header = "[💡 시스템 알림: SQLite 주가 데이터베이스(10년치 데이터 기록)를 성공적으로 조회했습니다.]\n\n"

    def fmt_p(val) -> str:
        try:
            return f"{int(float(val)):,}"
        except (ValueError, TypeError):
            return str(val)

    try:
        # 1. 역대 최고 종가
        if any(k in q_type for k in ["max", "highest", "peak", "최고"]):
            cursor.execute("SELECT date, close, value FROM stock_data WHERE close IS NOT NULL OR value IS NOT NULL")
            rows = cursor.fetchall()
            if rows:
                max_row = max(rows, key=lambda r: float(r[1] if r[1] is not None else r[2]))
                max_val = max_row[1] if max_row[1] is not None else max_row[2]
                return notice_header + f"삼성전자 역대 최고 종가: {fmt_p(max_val)}원 (기록일자: {max_row[0]})"

        # 2. 역대 최저 종가
        if any(k in q_type for k in ["min", "lowest", "bottom", "최저"]):
            cursor.execute("SELECT date, close, value FROM stock_data WHERE (close IS NOT NULL AND close > 0) OR (value IS NOT NULL AND value > 0)")
            rows = cursor.fetchall()
            if rows:
                min_row = min(rows, key=lambda r: float(r[1] if r[1] is not None else r[2]))
                min_val = min_row[1] if min_row[1] is not None else min_row[2]
                return notice_header + f"삼성전자 역대 최저 종가: {fmt_p(min_val)}원 (기록일자: {min_row[0]})"

        # 3. 특정 단일 일자 조회 (휴장일 자동 역추적 폴백)
        if target_date or any(k in q_type for k in ["exact", "target", "single", "day", "date", "특정"]):
            lookup_date = target_date or start_date
            if lookup_date:
                cursor.execute(
                    "SELECT date, open, high, low, close, value FROM stock_data WHERE date = ?",
                    (lookup_date,)
                )
                row = cursor.fetchone()
                if row:
                    return notice_header + (
                        f"[{row[0]} 삼성전자 주가 기록]\n"
                        f"- 종가: {fmt_p(row[4] or row[5])}원\n"
                        f"- 시가: {fmt_p(row[1] or row[5])}원 | 고가: {fmt_p(row[2] or row[5])}원 | 저가: {fmt_p(row[3] or row[5])}원"
                    )

                cursor.execute(
                    "SELECT date, open, high, low, close, value FROM stock_data WHERE date < ? ORDER BY date DESC LIMIT 1",
                    (lookup_date,)
                )
                prev_row = cursor.fetchone()
                if prev_row:
                    return notice_header + (
                        f"[{lookup_date}]는 증시 휴장일(주말/공휴일)이거나 거래 기록이 없는 날짜입니다.\n"
                        f"가장 가까운 직전 영업일인 [{prev_row[0]}]의 종가는 {fmt_p(prev_row[4] or prev_row[5])}원이었습니다."
                    )

        # 4. 기간 조회 (범위 통계 및 테이블)
        if start_date:
            sql = "SELECT date, open, high, low, close, value FROM stock_data WHERE date >= ?"
            params = [start_date]
            if end_date:
                sql += " AND date <= ?"
                params.append(end_date)
            sql += " ORDER BY date DESC"

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            if rows:
                p_list = [float(r[4] if r[4] is not None else r[5]) for r in rows]
                period_str = f"{rows[-1][0]} ~ {rows[0][0]}" if len(rows) > 1 else rows[0][0]
                max_price = max(p_list)
                min_price = min(p_list)
                avg_price = sum(p_list) / len(p_list)
                start_p = p_list[-1]
                end_p = p_list[0]
                period_return = ((end_p - start_p) / start_p) * 100 if start_p else 0

                top_rows = rows[:10]
                table_lines = ["| 날짜 | 종가 | 시가 | 고가 | 저가 |", "| :--- | :--- | :--- | :--- | :--- |"]
                for r in top_rows:
                    table_lines.append(f"| {r[0]} | {fmt_p(r[4] or r[5])}원 | {fmt_p(r[1] or r[5])}원 | {fmt_p(r[2] or r[5])}원 | {fmt_p(r[3] or r[5])}원 |")
                table_text = "\n".join(table_lines)
                if len(rows) > 10:
                    table_text += f"\n... (총 {len(rows)}개 거래일 중 최근 10개 표시)"

                return notice_header + (
                    f"[{period_str} 기간 주가 통계 (총 {len(rows)}거래일)]\n"
                    f"- 기간 시작 종가: {fmt_p(start_p)}원 | 기간 최종 종가: {fmt_p(end_p)}원 (수익률: {period_return:+.2f}%)\n"
                    f"- 기간 내 최고가: {fmt_p(max_price)}원 | 최저가: {fmt_p(min_price)}원 | 평균가: {fmt_p(avg_price)}원\n\n"
                    f"**상세 거래 기록 표:**\n{table_text}"
                )

        # 5. 기본 10년치 개요
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM stock_data")
        cnt, min_d, max_d = cursor.fetchone()
        cursor.execute("SELECT date, close, value FROM stock_data ORDER BY date DESC LIMIT 5")
        recent_rows = cursor.fetchall()
        recent_text = "\n".join([f"  * {r[0]}: {fmt_p(r[1] or r[2])}원" for r in recent_rows])

        return notice_header + (
            f"[삼성전자 10년치 전체 주가 DB 보유 현황]\n"
            f"- 보유 기간: {min_d} ~ {max_d} (총 {cnt:,} 거래일)\n"
            f"- 최근 5거래일 종가:\n{recent_text}\n\n"
            f"💡 특정 연도(예: 2023년)나 특정 일자(예: 2024-05-10)를 지정하시면 상세한 분석 결과를 얻으실 수 있습니다."
        )
    finally:
        conn.close()
