# codyssey_m1_2

# AI Agent 개발: 나만의 AI 비서 구축

# 🚀 삼성전자 AI 투자 비서 (Samsung Stock Insight Agent)

본 서비스는 삼성전자의 10년치 주가 데이터를 바탕으로 사용자의 투자를 돕는 AI 비서입니다.[cite: 1] 일반적인 AI가 모르는 과거 통계 데이터와 사용자의 가상 투자 기록을 결합하여 맞춤형 인사이트를 제공합니다.[cite: 1]

## 🌟 주요 기능

1. **데이터 기반 AI 채팅**: 10년치 통계 요약을 바탕으로 주가 흐름 및 미래 시나리오 예측 (OpenAI Function Calling 적용)[cite: 1]
2. **가상 투자 포트폴리오 (CRUD)**: 과거 특정 시점의 매수 기록을 관리하고 현재 수익률 확인[cite: 1]
3. **실시간 데이터 요약 및 시각화**: 현재 주가 위치, 최근 추세, 변동성 등 핵심 지표 자동 계산 및 Chart.js 기반 주가 추세선 시각화 제공[cite: 1]
4. **대화 기록 저장**: AI와의 이전 대화 내용을 언제든 다시 불러오기[cite: 1]
5. **UX 고도화 (보너스)**: 다크 모드 토글 지원, 주가 데이터 CSV 내보내기 기능 제공

## 🛠 기술 스택

- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (Tailwind-like Custom CSS), Chart.js[cite: 1]
- **Backend**: FastAPI, Pydantic, yfinance, Firebase Admin SDK[cite: 1]
- **AI/LLM**: OpenAI API (Context Injection & Function Calling 적용)[cite: 1]
- **Database**: Google Firebase Firestore[cite: 1]
- **Infrastructure & Deployment**: Docker, Render (API), Vercel (Web)[cite: 1]

## 🔗 배포 URL

- **Frontend (Vercel)**: [Vercel 배포 주소 입력][cite: 1]
- **Backend API (Render)**: [Render 배포 주소 입력][cite: 1]
- **API Documentation (Swagger)**: [Render 배포 주소]/docs[cite: 1]

## 📁 프로젝트 구조

\`\`\`text my_ai_assistant/  
├── docker/  
│ ├── docker-compose.yml  
│ └── Dockerfile # 단일 도커파일 (로컬 및 Render 배포용)  
├── src/  
│ ├── index.html # 메인 뷰 (채팅, 차트, 데이터 관리)  
│ ├── css/  
│ │ └── utility.css # Tailwind-like 커스텀 CSS & 다크모드  
│ ├── js/  
│ │ ├── api.js # 백엔드 통신 모듈 (fetch)  
│ │ ├── ui.js # 다크모드, 차트 렌더링  
│ │ └── chat.js # 채팅 UI 로직  
│ ├── lib/ # 백엔드(FastAPI) 소스  
│ │ ├── main.py  
│ │ ├── database.py  
│ │ ├── routers/  
│ │ └── services/ # AI Function Calling 로직  
│ ├── .env # 로컬 환경 변수  
│ ├── .env_sample  
│ └── serviceAccountKey.json  
└── README.md  
\`\`\`

## ⚙️ 로컬 실행 방법 (Docker 기반)

본 프로젝트는 Docker를 활용하여 로컬 개발 환경과 배포 환경의 일관성을 유지합니다.

1. **저장소 클론**[cite: 1] \`\`\`bash git clone https://github.com/smong2/codyssy_m1_2.git cd codyssy_m1_2 \`\`\`

2. **환경 변수 및 키 설정**[cite: 1]
   - `src/.env_sample` 파일을 복사하여 `src/.env` 파일을 생성합니다.
   - Firebase 서비스 계정 키(`serviceAccountKey.json`)를 `src/` 디렉토리 내에 위치시킵니다.
   - `start.sh` 를 실행해서 docker 환경을 활성합니다. (실행이 되지 않으면 실행권한을 부여해야 함)

   **📋 환경 변수 목록 (`src/.env`)**
   - `OPENAI_API_KEY`: OpenAI API 인증 키[cite: 1]
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: Firebase 서비스 계정 키 (JSON 문자열 또는 경로)[cite: 1]
   - `API_BASE_URL`: 프론트엔드에서 참조할 백엔드 주소 (로컬 구동 시 `http://localhost:8090`)[cite: 1]
   - `ALLOWED_ORIGINS`: CORS 허용 도메인 목록 (예: `http://localhost:3000, https://[Vercel주소].vercel.app`)

3. **Docker Compose 실행** 최상위 디렉토리(root)에서 아래 명령어를 실행하여 컨테이너를 빌드하고 실행합니다. \`\`\`bash docker compose -f docker/docker-compose.yml up --build \`\`\`

4. **서비스 접속**
   - **Frontend UI**: `http://localhost:8090`
   - **Backend API Docs (Swagger)**: `http://localhost:8090/docs`

## 📸 실행 스크린샷[cite: 1]

- **데이터 요약 및 채팅 화면** (Chart.js 시각화 및 다크모드 적용 모습 포함)[cite: 1]
- **투자 기록 관리(CRUD) 화면** (데이터 추가/수정/삭제 및 내보내기 버튼 동작 확인)[cite: 1]
- **대화 내역 불러오기 화면**[cite: 1]
