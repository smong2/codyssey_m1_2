import os
from typing import List, Dict, Any, Optional
try:
    from firebase_admin import firestore
except ImportError:
    firestore = None
from api.core.database import get_firestore_client, get_sqlite_connection
from api.models.portfolio import PortfolioItem

def get_portfolio_list() -> List[Dict[str, Any]]:
    """사용자의 가상 투자 포트폴리오 목록을 반환합니다."""
    db = get_firestore_client()
    if db is None:
        return []
    try:
        query = db.collection("portfolio")
        if firestore is not None:
            docs = query.order_by("date", direction=firestore.Query.ASCENDING).stream()
        else:
            docs = query.order_by("date").stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        print(f"⚠️ get_portfolio_list 오류: {e}")
        return []

def add_portfolio_item(item: PortfolioItem) -> str:
    """새 가상 투자 거래 기록을 등록하고 ID를 반환합니다."""
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Firebase 데이터베이스에 연결할 수 없습니다.")
    doc_ref = db.collection("portfolio").document()
    doc_ref.set(item.model_dump() if hasattr(item, "model_dump") else item.dict())
    return doc_ref.id

def delete_portfolio_item(doc_id: str) -> bool:
    """특정 가상 투자 거래 기록을 삭제합니다."""
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Firebase 데이터베이스에 연결할 수 없습니다.")
    db.collection("portfolio").document(doc_id).delete()
    return True

def analyze_portfolio(portfolio_data: Optional[List[Dict[str, Any]]] = None, trades: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
    """[가상 포트폴리오 분석 도구] AI 에이전트 전용 Function Calling 도구"""
    notice_header = "[💡 시스템 알림: 사용자의 가상 투자 포트폴리오 분석을 완료했습니다.]\n\n"

    # SQLite에서 최신 시장가 조회
    latest_price = 0
    latest_date = ""
    try:
        conn = get_sqlite_connection()
        c = conn.cursor()
        c.execute("SELECT date, close, value FROM stock_data ORDER BY date DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            latest_date = row[0]
            latest_price = int(float(row[1] if row[1] is not None else row[2]))
    except Exception:
        pass

    # 직접 인자로 거래 목록이 전달된 경우
    items = portfolio_data or trades or kwargs.get("portfolio_data") or kwargs.get("trades")
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

    # Firestore에서 실제 포트폴리오 조회
    docs = get_portfolio_list()
    if docs:
        total_buy_qty, total_buy_amount = 0, 0.0
        total_sell_qty, total_sell_amount = 0, 0.0
        for item in docs:
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

    return notice_header + (
        f"[가상 포트폴리오 상태]\n"
        f"- 현재 등록된 활성 포트폴리오 기록이 없습니다.\n"
        f"- 현재 삼성전자 기준 주가({latest_date}): {latest_price:,}원\n"
        f"- 웹 대시보드(http://localhost:3000)의 '나의 가상 투자 기록'에서 매수/매도 내역을 추가하시면 실시간 수익률과 평가 손익을 연동하여 분석할 수 있습니다."
    )
