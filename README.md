# codyssey_m1_2
# AI Agent 개발: 나만의 AI 비서 구축

# 🚀 삼성전자 AI 투자 비서 (Samsung Stock Insight Agent)

본 서비스는 삼성전자의 10년치 주가 데이터를 바탕으로 사용자의 투자를 돕는 AI 비서입니다. 일반적인 AI가 모르는 과거 통계 데이터와 사용자의 가상 투자 기록을 결합하여 맞춤형 인사이트를 제공합니다.

## 🌟 주요 기능
1. **데이터 기반 AI 채팅**: 10년치 통계 요약을 바탕으로 주가 흐름 및 미래 시나리오 예측
2. **가상 투자 포트폴리오 (CRUD)**: 과거 특정 시점의 매수 기록을 관리하고 현재 수익률 확인
3. **실시간 데이터 요약**: 현재 주가 위치, 최근 추세, 변동성 등 핵심 지표 자동 계산
4. **대화 기록 저장**: AI와의 이전 대화 내용을 언제든 다시 불러오기

## 🛠 기술 스택
- **Frontend**: Vanilla JavaScript, HTML5, CSS3, Chart.js
- **Backend**: FastAPI, Pydantic, Firebase Admin SDK
- **AI/LLM**: OpenAI API (Context Injection 기법 적용)
- **Database**: Google Firebase Firestore
- **Deployment**: Render (API), Vercel (Web)

## 🔗 배포 URL
- **Frontend**: [Vercel 배포 주소 입력]
- **Backend API**: [Render 배포 주소 입력]
- **API Documentation**: [Render 배포 주소]/docs

## ⚙️ 로컬 실행 방법
1. 저장소 클론
   ```bash
   git clone https://github.com/smong2/codyssy_m1_2.git

2. 가상환경 및 패키지
   python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. .env

📋 환경 변수 목록
OPENAI_API_KEY: OpenAI API 인증 키
FIREBASE_SERVICE_ACCOUNT_JSON: Firebase 서비스 계정 키 (JSON 문자열 또는 경로)
API_BASE_URL: 프론트엔드에서 참조할 백엔드 주소


4. 실행
uvicorn main:app --reload

5. 📸  실행스크린샷

데이터 요약 및 채팅 화면
투자 기록 관리(CRUD) 화면
대화 내역 불러오기 화면
