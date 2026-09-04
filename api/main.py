from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from api.lib.ai_service import generate_ai_reply

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
class PortfolioItem(BaseModel):
    date: str
    price: float
    quantity: int

@app.get("/api/portfolio")
def get_portfolio():
    """가상 투자 기록 조회"""
    try:
        db = get_firestore_client()
        docs = db.collection("portfolio").order_by("date", direction=firestore.Query.DESCENDING).stream()
        results = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio")
def add_portfolio(item: PortfolioItem):
    """가상 투자 기록 추가"""
    try:
        db = get_firestore_client()
        # Firestore가 자동으로 고유 문서 ID 생성
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

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat_with_ai(request: ChatRequest):
    """Gemini를 활용한 챗봇 응답 엔드포인트 (문맥 주입 적용)"""
    try:
        db = get_firestore_client()
        
        # 1. Firestore에서 사용자의 가상 투자 포트폴리오 내역 조회
        docs = db.collection("portfolio").order_by("date", direction=firestore.Query.DESCENDING).stream()
        portfolio_items = [doc.to_dict() for doc in docs]
        
        # 2. AI에게 넘겨줄 문맥 데이터(Context) 문자열 구성
        context_data = "현재 사용자의 가상 투자 포트폴리오 보유 내역:\n"
        if portfolio_items:
            for item in portfolio_items:
                total_price = item['price'] * item['quantity']
                context_data += f"- 매수일: {item['date']}, 매수 단가: {item['price']:,}원, 수량: {item['quantity']}주 (총 투자금: {total_price:,}원)\n"
        else:
            context_data += "현재 등록된 투자 기록이 없습니다.\n"
            
        # 3. AI 서비스 호출 시 구성한 문맥 데이터(context_data)를 함께 전달
        reply = generate_ai_reply(request.message, context_data)
        
        return {"status": "success", "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))