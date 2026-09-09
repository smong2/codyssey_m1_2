import sys
import os

# 모듈 탐색 경로 보정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import PORT, ALLOWED_ORIGINS
from api.core.database import init_sqlite_db
from api.core.security import SecurityLoggingMiddleware
from api.routers import data_router, portfolio_router, chat_router, conversations_router

# 하위 호환성을 위한 모델 re-export
from api.models.data import DataItem
from api.models.portfolio import PortfolioItem
from api.models.chat import ChatRequest, ConversationCreate, ConversationTitleUpdate

# FastAPI 애플리케이션 초기화
app = FastAPI(
    title="Samsung Stock AI Investment Assistant API",
    description="삼성전자 10년치 주가 데이터 및 포트폴리오 분석 AI 비서 백엔드 서비스",
    version="2.0.0"
)

# 1. 보안 모니터링 및 헤더 주입 미들웨어 등록
app.add_middleware(SecurityLoggingMiddleware)

# 2. CORS 미들웨어 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 데이터베이스 초기화 (SQLite 스키마 보장)
init_sqlite_db()

# 4. 기능별 APIRouter 등록 (계층형 라우팅)
app.include_router(data_router)
app.include_router(portfolio_router)
app.include_router(chat_router)
app.include_router(conversations_router)

# 5. 루트 헬스체크 엔드포인트
@app.get("/", summary="백엔드 서비스 헬스체크")
def root():
    return {
        "status": "success",
        "message": "🚀 AI Investment Assistant 백엔드가 정상적으로 구동 중입니다!",
        "version": "2.0.0",
        "architecture": "Layered Architecture (Routers, Services, Models, Core)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=PORT, reload=True)