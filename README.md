# codyssey_m1_2

# AI Agent 개발: 나만의 AI 비서 구축

# 🚀 삼성전자 AI 투자 비서 (Samsung Stock Insight Agent)

본 서비스는 삼성전자의 10년치 주가 데이터를 바탕으로 사용자의 투자를 돕는 AI 비서입니다. 일반적인 AI가 모르는 과거 통계 데이터와 사용자의 가상 투자 기록을 결합하여 맞춤형 인사이트를 제공합니다.

## 🌟 주요 기능

1. **데이터 기반 AI 채팅**: 10년치 통계 요약을 바탕으로 주가 흐름 및 미래 시나리오 예측 (AI Function Calling 적용)
2. **가상 투자 포트폴리오 (CRUD)**: 과거 특정 시점의 매수/매도 기록을 관리하고 현재 수익률 확인
3. **실시간 데이터 요약 및 시각화**: 현재 주가 위치, 최근 추세, 변동성 등 핵심 지표 자동 계산 및 Chart.js 기반 주가 추세선 시각화 제공
4. **대화 기록 저장**: AI와의 이전 대화 내용을 언제든 다시 불러오기
5. **UX 고도화 (보너스)**: 다크 모드 토글 지원, 주가 데이터 CSV 내보내기 기능 제공

## 🤖 AI 도구 호출 (Function Calling) 및 멀티채널 연동 (보너스 과제)

본 프로젝트는 LLM의 한계를 극복하고 효율적인 데이터 처리를 위해 Function Calling과 MCP(Model Context Protocol) 기반 아키텍처를 도입했습니다.

### 1. 어떤 근거로 어떤 도구를 호출했는가? (Rationale)

- **`get_stock_summary(days)` 도구**
  - **호출 근거:** LLM에게 10년치 일일 주가 데이터(약 2,500건)를 통째로 프롬프트에 주입하는 것은 심각한 토큰 낭비와 문맥 유실(Lost in the Middle)을 유발합니다. 따라서 사용자가 특정 기간의 주가(최고가, 최저가, 평균 등)를 묻는 경우, 백엔드의 SQLite 캐시를 통해 계산된 정확한 통계 요약값만 동적으로 호출하여 할당량 초과를 방지하고 답변의 정확도를 극대화했습니다.
- **`get_portfolio_status()` 도구**
  - **호출 근거:** 사용자의 실시간 가상 매수/매도 기록과 현재 주가를 비교하여 정확한 수익률을 계산하기 위해, 필요 시 AI가 직접 사용자의 최신 포트폴리오 데이터를 조회하도록 구성했습니다.

### 2. 호출 흐름 다이어그램 (Invocation Flow)

이 시스템은 외부 채널(MCP Client)에서도 동일하게 도구를 호출할 수 있도록 설계되어 멀티채널 연동을 지원합니다.

```text
[사용자 / 외부 채널 (MCP Client)]
       │ (1) 질문: "10년 내 최저가는 얼마야?"
       ▼
[Gemini AI 모델]
       │ (2) 판단: 내부 지식 및 단기 데이터로 답변 불가 ➔ Tool Call 요청
       ▼
[FastAPI 백엔드 (MCP Server 연동)]
       │ (3) 실행: SQLite 쿼리 연산 (SELECT MIN(close) ...) 수행
       ▼
[SQLite 로컬 캐시 DB]
       │ (4) 결과 반환: 최저가 및 해당 날짜 데이터
       ▼
[Gemini AI 모델]
       │ (5) 데이터 기반 자연어 답변 합성
       ▼
[사용자 화면]
```

## 🛠 기술 스택

- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (Tailwind-like Custom CSS), Chart.js
- **Backend**: FastAPI, Pydantic, yfinance, Firebase Admin SDK, SQLite (캐싱)
- **AI/LLM**: Google Gemini API (Context Injection & Function Calling 적용)
- **Database**: Google Firebase Firestore, 로컬 SQLite
- **Infrastructure & Deployment**: Docker, Render (API), Vercel (Web)

## 🔗 배포 URL

- **Frontend (Vercel)**: [Vercel 배포 주소 입력]
- **Backend API (Render)**: [Render 배포 주소 입력]
- **API Documentation (Swagger)**: [Render 배포 주소]/docs

## 📁 프로젝트 구조

```text
my_ai_assistant/
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile          # 단일 도커파일 (로컬 및 Render 배포용)
├── web/                    # [Vercel 배포 타겟] 프론트엔드 UI 영역
│   ├── index.html          # 메인 뷰 (채팅, 차트, 데이터 관리)
│   ├── css/
│   │   └── style.css       # 커스텀 CSS & 다크모드
│   └── js/
│       ├── api.js          # 백엔드 통신 모듈 (fetch)
│       ├── app.js          # 공통 UI 및 초기화 로직
│       ├── data.js         # 데이터 CRUD 및 차트 렌더링
│       └── chat.js         # 채팅 UI 로직
├── api/                    # [Render 배포 타겟] FastAPI 백엔드 영역
│   ├── main.py             # FastAPI 진입점 및 라우팅 설정
│   ├── lib/                # 비즈니스 로직 라이브러리
│   │   ├── collect_data.py # 주가 데이터 수집기
│   │   ├── database.py     # Firestore CRUD 로직
│   │   └── ai_service.py   # AI Function Calling 로직
│   ├── .env                # 로컬 환경 변수
│   ├── .env_sample
│   └── serviceAccountKey.json
├── start.sh
└── README.md
```

## ⚙️ 로컬 실행 방법 (Docker 기반)

본 프로젝트는 Docker를 활용하여 로컬 개발 환경과 배포 환경의 일관성을 유지합니다.

1. **저장소 클론**

   ```bash
   git clone https://github.com/smong2/codyssy_m1_2.git
   cd codyssy_m1_2
   ```

2. **환경 변수 및 키 설정**
   - `api/.env_sample` 파일을 복사하여 `api/.env` 파일을 생성합니다.
   - Firebase 서비스 계정 키(`serviceAccountKey.json`)를 `api/` 디렉토리 내에 위치시킵니다.
   - `start.sh` 를 실행해서 docker 환경을 활성화합니다. (실행이 되지 않으면 실행권한을 부여해야 함)

   **📋 환경 변수 목록 (`api/.env`)**
   - `GEMINI_API_KEY`: Google Gemini API 인증 키
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: Firebase 서비스 계정 키 (JSON 문자열 또는 경로)
   - `API_BASE_URL`: 프론트엔드에서 참조할 백엔드 주소 (로컬 구동 시 `http://localhost:8090`)
   - `ALLOWED_ORIGINS`: CORS 허용 도메인 목록 (예: `http://localhost:3000, https://[Vercel주소].vercel.app`)

3. **Docker Compose 실행** 최상위 디렉토리(root)에서 아래 명령어를 실행하여 컨테이너를 빌드하고 실행합니다.

   ```bash
   start.sh (실행가능이 아닌 경우 실행권한을 주고 실행합니다)
   ```

4. **서비스 접속**
   - **Frontend UI**: `http://localhost:3000`
   - **Backend API Docs (Swagger)**: `http://localhost:8090/docs`

## 📸 실행 스크린샷

- **데이터 요약 및 채팅 화면** (Chart.js 시각화 및 다크모드 적용 모습 포함)
- **투자 기록 관리(CRUD) 화면** (데이터 추가/수정/삭제 및 내보내기 버튼 동작 확인)
- **대화 내역 불러오기 화면**
