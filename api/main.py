from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
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

# CORS 설정 (프론트엔드 연동 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConversationTitleUpdate(BaseModel):
    title: str

# Firebase Firestore 클라이언트 초기화 함수 (로컬 및 Render 환경 자동 대응)
def get_firestore_client():
    if not firebase_admin._apps:
        firebase_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        try:
            if firebase_env and firebase_env.strip().startswith("{"):
                # Render 환경: 환경 변수 속 JSON 텍스트 파싱
                cred_dict = json.loads(firebase_env)
                cred = credentials.Certificate(cred_dict)
            else:
                # 로컬 환경: 파일 경로 기반 인증
                base_dir = os.path.dirname(os.path.abspath(__file__))
                default_key_path = os.path.join(base_dir, "serviceAccountKey.json")
                key_path = firebase_env if firebase_env else default_key_path
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"❌ Firebase 초기화 오류: {e}")
    return firestore.client()

@app.get("/")
def health_check():
    """서버 정상 작동 확인용 헬스체크 엔드포인트"""
    return {
        "status": "success",
        "message": "🚀 AI Investment Assistant 백엔드가 정상적으로 구동 중입니다!"
    }

@app.get("/api/data")
def get_stock_data(limit: int = Query(30, description="조회할 데이터 개수")):
    """
    Firestore의 'stock_data' 컬렉션에서 주가 시계열 데이터를 조회합니다.
    (과제 표준 API 경로 /api/data 준수)
    """
    try:
        db = get_firestore_client()
        # 최근 날짜 순으로 정렬하여 지정된 개수(limit)만큼 조회
        docs = db.collection("stock_data").order_by("date", direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        results = []
        for doc in docs:
            results.append(doc.to_dict())
            
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")

# Pydantic 데이터 검증 모델
# 1. 가상 투자 스키마 (매수/매도 구분 추가)
class PortfolioItem(BaseModel):
    trade_type: Literal["buy", "sell"] = "buy" # 기본값 매수
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

# --- 신규 API: 요약/통계 정보 (보너스 과제) ---
@app.get("/api/data/summary")
def get_data_summary(limit: int = 100):
    """지정된 기간의 주가 통계 요약 및 추가 지표(변동성) 제공"""
    try:
        db = get_firestore_client()
        docs = db.collection("stock_data").order_by("date", direction=firestore.Query.DESCENDING).limit(limit).stream()
        items = [doc.to_dict() for doc in docs]
        
        if not items:
            return {"status": "error", "message": "데이터가 없습니다."}
            
        prices = [item.get("close", item.get("value", 0)) for item in items]
        dates = [item["date"] for item in items]
        
        # 기본 통계
        max_p = max(prices)
        min_p = min(prices)
        avg_p = sum(prices) / len(prices)
        
        # 보너스 지표: 가격 변동성(표준편차)
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # 최근 추세
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
                "volatility": round(volatility, 2) # 보너스 지표
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

@app.post("/api/chat")
def chat_with_ai(request: ChatRequest):
    """Gemini 챗봇 응답 (포트폴리오 + 최근 주가 흐름 문맥 주입)"""
    try:
        db = get_firestore_client()
        
        # 1. 포트폴리오 데이터 조회
        docs = db.collection("portfolio").order_by("date", direction=firestore.Query.DESCENDING).stream()
        portfolio_items = [doc.to_dict() for doc in docs]
        
        # 2. 최근 주가 데이터 5일치 조회 (수익률 계산 및 추세 파악용)
        stock_docs = db.collection("stock_data").order_by("date", direction=firestore.Query.DESCENDING).limit(5).stream()
        stock_items = [doc.to_dict() for doc in stock_docs]
        
        # 3. AI 문맥(Context) 조립
        context_data = "[최근 5일 삼성전자 주가 흐름]\n"
        if stock_items:
            latest_price = stock_items[0]['value']
            context_data += f"현재 기준(가장 최근 종가): {latest_price:,}원 ({stock_items[0]['date']})\n"
            for item in stock_items:
                context_data += f"- {item['date']} : {item['value']:,}원\n"
        else:
            context_data += "주가 데이터를 불러오지 못했습니다.\n"

        context_data += "\n[현재 사용자의 모의 투자 포트폴리오 보유 내역]\n"
        if portfolio_items:
            for item in portfolio_items:
                context_data += f"- 매수일: {item['date']}, 매수 단가: {item['price']:,}원, 수량: {item['quantity']}주\n"
        else:
            context_data += "현재 등록된 투자 기록이 없습니다.\n"
            
        reply = generate_ai_reply(request.message, context_data)
        
        # (이하 대화 저장 로직은 기존과 동일)
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
    """사이드바에 표시할 과거 대화 목록 조회"""
    try:
        db = get_firestore_client()
        docs = db.collection("conversations").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
        results = [{"id": doc.id, "title": doc.to_dict().get("title", "새 대화")} for doc in docs]
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conv_id}")
def get_conversation_detail(conv_id: str):
    """특정 대화방의 전체 과거 메시지 불러오기"""
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

# --- 채팅방 제목 수정 API ---
@app.put("/api/conversations/{conv_id}")
def update_conversation_title(conv_id: str, data: ConversationTitleUpdate):
    try:
        db = get_firestore_client()
        db.collection("conversations").document(conv_id).update({"title": data.title})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))