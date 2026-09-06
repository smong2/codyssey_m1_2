# 1. 파이썬 표준 라이브러리 (Standard Library)
import json
import os
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

# ==========================================
# 🛠️ AI Function Calling 용 신규 도구 3종 세트
# ==========================================

def query_stock_data(intent: str, start_date: str = None, end_date: str = None, target_date: str = None) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    where_clause = ""
    params = []
    if start_date and end_date:
        where_clause = "WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]
    elif target_date:
        where_clause = "WHERE date = ?"
        params = [target_date]
        
    try:
        if intent == 'oldest':
            cursor.execute("SELECT MIN(date) FROM stock_data")
            return f"DB 내 가장 오래된 주가 데이터 날짜: {cursor.fetchone()[0]}"
        elif intent == 'newest':
            cursor.execute("SELECT MAX(date) FROM stock_data")
            return f"DB 내 가장 최신 주가 데이터 날짜: {cursor.fetchone()[0]}"
        elif intent == 'min':
            cursor.execute(f"SELECT date, close FROM stock_data {where_clause} ORDER BY close ASC LIMIT 1", params)
            row = cursor.fetchone()
            return f"조회된 최저가: {int(row[1]):,}원 (기록일: {row[0]})" if row else "해당 기간에 데이터가 없습니다."
        elif intent == 'max':
            cursor.execute(f"SELECT date, close FROM stock_data {where_clause} ORDER BY close DESC LIMIT 1", params)
            row = cursor.fetchone()
            return f"조회된 최고가: {int(row[1]):,}원 (기록일: {row[0]})" if row else "해당 기간에 데이터가 없습니다."
        elif intent == 'average':
            cursor.execute(f"SELECT AVG(close) FROM stock_data {where_clause}", params)
            row = cursor.fetchone()
            return f"해당 기간 평균가: {int(row[0]):,}원" if row and row[0] else "해당 기간에 데이터가 없습니다."
        elif intent == 'specific_date':
            cursor.execute(f"SELECT date, open, high, low, close, value FROM stock_data {where_clause}", params)
            row = cursor.fetchone()
            return f"{row[0]} 주가 정보 - 시가:{row[1]}, 고가:{row[2]}, 저가:{row[3]}, 종가:{row[4]}" if row else "해당 날짜에 데이터가 없거나 2016년 8월 이전입니다."
        else:
            return "지원하지 않는 intent 입니다."
    finally:
        conn.close()

def analyze_portfolio() -> str:
    db = get_firestore_client()
    docs = db.collection("portfolio").order_by("date").stream()
    
    total_buy_qty = 0
    total_buy_amount = 0
    total_sell_qty = 0
    total_sell_amount = 0
    
    for doc in docs:
        item = doc.to_dict()
        qty = item.get("quantity", 0)
        price = item.get("price", 0)
        if item.get("trade_type", "buy") == "buy":
            total_buy_qty += qty
            total_buy_amount += (qty * price)
        else:
            total_sell_qty += qty
            total_sell_amount += (qty * price)
            
    current_qty = total_buy_qty - total_sell_qty
    avg_price = total_buy_amount / total_buy_qty if total_buy_qty > 0 else 0
    realized_profit = total_sell_amount - (avg_price * total_sell_qty)
    
    return f"""[현재 포트폴리오 분석 결과 (서버 자동 계산)]
- 누적 매수: {total_buy_qty}주 (총 {total_buy_amount:,}원)
- 누적 매도: {total_sell_qty}주 (총 {total_sell_amount:,}원)
- 현재 보유 수량: {current_qty}주 (평균 단가: {int(avg_price):,}원)
- 확정(실현) 수익금: {int(realized_profit):,}원"""

def get_conversation_history(conversation_id: str) -> str:
    if not conversation_id or conversation_id == "None":
        return "현재 대화방은 새로 시작되었으므로 이전 대화 기록이 존재하지 않습니다."
        
    db = get_firestore_client()
    doc = db.collection("conversations").document(conversation_id).get()
    if not doc.exists:
        return "해당 대화 기록을 찾을 수 없습니다."
        
    messages = doc.to_dict().get("messages", [])
    history_text = "[과거 대화 내역 원본]\n"
    for msg in messages:
        role = "사용자" if msg.get("role") == "user" else "AI"
        history_text += f"- {role}: {msg.get('content')}\n"
        
    return history_text

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

# ✨ 보너스 과제: 요약 통계 지표 확장 (기간 수익률, MDD 추가)
@app.get("/api/data/summary")
def get_data_summary(limit: int = 100):
    try:
        items = get_cached_stock_data_with_version()
        items = items[:limit]
        
        if not items:
            return {"status": "error", "message": "데이터가 없습니다."}
            
        prices = [item.get("close", item.get("value", 0)) for item in items]
        dates = [item["date"] for item in items]
        
        # 최신->과거 순서를 과거->최신(연대기) 순으로 변환하여 금융 연산 수행
        chrono_prices = prices[::-1]
        
        max_p = max(prices)
        min_p = min(prices)
        avg_p = sum(prices) / len(prices)
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # 1. 기간 수익률 계산
        start_price = chrono_prices[0]
        end_price = chrono_prices[-1]
        return_rate = ((end_price - start_price) / start_price) * 100 if start_price else 0
        
        # 2. MDD(최대 낙폭) 계산
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 🚀 가상 투자 (포트폴리오) CRUD
# ==========================================

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

# ==========================================
# 🚀 AI 채팅 및 대화 기록 관리
# ==========================================

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

class ConversationTitleUpdate(BaseModel):
    title: str

@app.post("/api/chat")
def chat_with_ai(request: ChatRequest):
    try:
        db = get_firestore_client()
        
        # 1. 최근 1개월(30영업일) 주가 데이터 조회
        all_stock = get_cached_stock_data_with_version()
        stock_items = all_stock[:30]
        
        # ✨ 보너스 과제: AI에 '원시 데이터' 대신 백엔드에서 미리 연산한 '요약 통계 정보'를 주입
        context_data = "[미리보기: 최근 1개월 삼성전자 주가 요약 (전체 과거 데이터는 도구 호출 필수)]\n"
        
        if stock_items:
            prices = [item.get('close', item.get('value', 0)) for item in stock_items]
            chrono_prices = prices[::-1]
            max_p = max(prices)
            min_p = min(prices)
            avg_p = sum(prices) / len(prices)
            
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
            
            # AI 프롬프트에 분석된 통계 지표 직접 주입
            context_data += f"- 기준일: {stock_items[-1]['date']} ~ {stock_items[0]['date']}\n"
            context_data += f"- 최근 종가: {end_price:,}원\n"
            context_data += f"- 최고/최저가: {max_p:,}원 / {min_p:,}원 (평균: {int(avg_p):,}원)\n"
            context_data += f"- 기간 수익률: {round(return_rate, 2)}%\n"
            context_data += f"- 최대 낙폭(MDD): {round(mdd, 2)}%\n"
            context_data += "=> 이 요약 통계를 바탕으로 현재 단기 주가 흐름의 강약 및 리스크를 분석해 주세요.\n"
        else:
            context_data += "주가 데이터를 불러오지 못했습니다.\n"

        # 3. 이전 대화를 불러올 수 있도록 현재 대화방 ID 주입
        current_conv_id = request.conversation_id or "None"
        context_data += f"\n[현재 접속된 대화방 상태]\n- 대화방 ID: {current_conv_id}\n(과거 대화를 조회할 때 이 ID를 파라미터로 사용하세요.)\n"
            
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