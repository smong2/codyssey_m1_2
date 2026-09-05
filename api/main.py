from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import sqlite3
from dotenv import load_dotenv
from pydantic import BaseModel
from api.lib.ai_service import generate_ai_reply
from datetime import datetime
from typing import Literal
import statistics

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
    """SQLite 캐시 테이블 및 메타 테이블 초기화"""
    # 디렉토리가 없으면 생성 방어 로직 추가
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 주가 데이터를 저장할 테이블 (OHLC 형태 반영)
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
    
    # 2. 버전 및 상태를 관리할 메타 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

# 서버 시작 시 SQLite 초기화 실행
init_sqlite_db()

def get_cached_stock_data_with_version():
    """
    Firebase의 메타 버전과 SQLite의 버전을 비교하여
    필요할 때만 Firebase에서 10년치 데이터를 동기화하는 함수
    """
    db = get_firestore_client()
    
    # 1. Firebase에서 최신 원격 버전 가져오기 (문서 1개 읽기)
    meta_doc = db.collection("metadata").document("stock_status").get()
    remote_version = str(meta_doc.to_dict().get("version", 1)) if meta_doc.exists else "1"
    
    # 2. 로컬 SQLite에 저장된 버전 가져오기
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM meta WHERE key = 'version'")
    row = cursor.fetchone()
    local_version = row[0] if row else "0"
    
    cursor.execute("SELECT COUNT(*) FROM stock_data")
    count = cursor.fetchone()[0]
    
    # 3. Cache Hit: 버전이 일치하고, 로컬 데이터가 존재하면 SQLite에서 즉시 반환
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
    
    # 4. Cache Miss (Sync): 버전이 다르거나 데이터가 없으면 Firebase에서 전체 조회 후 SQLite 갱신
    docs = db.collection("stock_data").order_by("date", direction=firestore.Query.DESCENDING).limit(2500).stream()
    items = []
    
    cursor.execute("DELETE FROM stock_data") # 기존 로컬 캐시 삭제
    
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
# 🚀 API 엔드포인트
# ==========================================

@app.get("/")
def health_check():
    """서버 정상 작동 확인용 헬스체크 엔드포인트"""
    return {
        "status": "success",
        "message": "🚀 AI Investment Assistant 백엔드가 정상적으로 구동 중입니다!"
    }

@app.get("/api/data")
def get_stock_data(limit: int = Query(30, description="조회할 데이터 개수")):
    """주가 데이터 조회 (SQLite 캐시 적용)"""
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
    """지정된 기간의 주가 통계 요약 (SQLite 캐시 적용)"""
    try:
        items = get_cached_stock_data_with_version()
        items = items[:limit]
        
        if not items:
            return {"status": "error", "message": "데이터가 없습니다."}
            
        prices = [item.get("close", item.get("value", 0)) for item in items]
        dates = [item["date"] for item in items]
        
        max_p = max(prices)
        min_p = min(prices)
        avg_p = sum(prices) / len(prices)
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        trend = "유지"
        if len(prices) >= 2:
            trend = "상승" if prices[0] > prices[1] else "하락" if prices[0] < prices[1] else "유지"

        return {
            "status": "success",
            "summary": {
                "period": f"{dates[-1]} ~ {dates[0]}",
                "count": len(prices),
                "max": max_p,
                "min": min_p,
                "average": round(avg_p, 2),
                "trend": trend,
                "volatility": round(volatility, 2)
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
    """가상 포트폴리오 조회"""
    try:
        db = get_firestore_client()
        docs = db.collection("portfolio").order_by("date", direction=firestore.Query.ASCENDING).stream()
        results = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio")
def add_portfolio(item: PortfolioItem):
    """가상 투자 기록 추가"""
    try:
        db = get_firestore_client()
        doc_ref = db.collection("portfolio").document()
        doc_ref.set(item.dict())
        return {"status": "success", "message": "추가되었습니다.", "id": doc_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/portfolio/{doc_id}")
def delete_portfolio(doc_id: str):
    """가상 투자 기록 삭제"""
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
    """Gemini 챗봇 응답 (문맥 주입 + SQLite 캐시 적용)"""
    try:
        db = get_firestore_client()
        
        # 1. 포트폴리오 데이터 조회
        docs = db.collection("portfolio").order_by("date", direction=firestore.Query.DESCENDING).stream()
        portfolio_items = [doc.to_dict() for doc in docs]
        
        # 2. 최근 주가 데이터 5일치 조회 (SQLite 캐시 사용)
        all_stock = get_cached_stock_data_with_version()
        stock_items = all_stock[:5]
        
        # 3. AI 문맥(Context) 조립
        context_data = "[최근 5일 삼성전자 주가 흐름]\n"
        if stock_items:
            latest_price = stock_items[0].get('close', stock_items[0].get('value', 0))
            context_data += f"현재 기준(가장 최근 종가): {latest_price:,}원 ({stock_items[0]['date']})\n"
            for item in stock_items:
                price = item.get('close', item.get('value', 0))
                context_data += f"- {item['date']} : {price:,}원\n"
        else:
            context_data += "주가 데이터를 불러오지 못했습니다.\n"

        context_data += "\n[현재 사용자의 모의 투자 포트폴리오 보유 내역]\n"
        if portfolio_items:
            for item in portfolio_items:
                trade_type_kr = "매수" if item.get('trade_type', 'buy') == 'buy' else "매도"
                context_data += f"- {trade_type_kr}일: {item['date']}, 단가: {item['price']:,}원, 수량: {item['quantity']}주\n"
        else:
            context_data += "현재 등록된 투자 기록이 없습니다.\n"
            
        reply = generate_ai_reply(request.message, context_data)
        
        # 4. Firestore에 대화 기록 저장
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
    """사이드바 과거 대화 목록 조회"""
    try:
        db = get_firestore_client()
        docs = db.collection("conversations").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
        results = [{"id": doc.id, "title": doc.to_dict().get("title", "새 대화")} for doc in docs]
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conv_id}")
def get_conversation_detail(conv_id: str):
    """특정 대화방 메시지 불러오기"""
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
    """특정 대화방 삭제"""
    try:
        db = get_firestore_client()
        db.collection("conversations").document(conv_id).delete()
        return {"status": "success", "message": "삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/conversations/{conv_id}")
def update_conversation_title(conv_id: str, data: ConversationTitleUpdate):
    """채팅방 제목 수정"""
    try:
        db = get_firestore_client()
        db.collection("conversations").document(conv_id).update({"title": data.title})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))