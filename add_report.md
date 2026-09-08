# 📊 Codyssey M1-2 요구사항 완성도 점검 및 심층 기술 보고서 (`add_report.md`)

본 문서는 **Codyssey M1-2 "AI Agent 개발: 나만의 AI 비서 구축"** 과제의 요구사항 대비 프로젝트 완성도를 객관적으로 점검하고, 요구사항을 넘어 추가로 고도화된 기능 및 과제 학습 목표 6대 핵심 질문에 대한 기술적 해설을 상세히 기술한 부가 보고서입니다.

---

## 1. 📌 요구사항 대비 완성도 점검표 (Compliance Matrix)

| 구분 | 세부 요구사항 명세 | 구현 상태 | 프로젝트 내 구현 위치 및 증빙 |
| :--- | :--- | :---: | :--- |
| **최종 결과물 1** | **데이터 기반 AI 채팅** (질문 입력 $\rightarrow$ 데이터 요약 반영 답변 + 로딩 표시) | **100% 충족** | • 최근 1개월 요약 지표 시스템 프롬프트 주입 ([`api/main.py`](file:///Users/mongpark/codyssey/codyssey_m1_2/api/main.py#L612))<br>• 3단계 로딩 애니메이션 인디케이터 구현 ([`web/js/chat.js`](file:///Users/mongpark/codyssey/codyssey_m1_2/web/js/chat.js#L220)) |
| **최종 결과물 2** | **데이터 관리 (CRUD)** (`(date, value, memo)` 추가/수정/삭제 및 목록 갱신) | **100% 충족** | • `POST/GET/PUT/DELETE /api/data` 표준 CRUD 구현 ([`api/main.py`](file:///Users/mongpark/codyssey/codyssey_m1_2/api/main.py#L510))<br>• 가상 포트폴리오 실시간 등록/삭제/목록 갱신 UI ([`web/js/data.js`](file:///Users/mongpark/codyssey/codyssey_m1_2/web/js/data.js#L318)) |
| **최종 결과물 3** | **대화 기록 저장 및 불러오기** (대화 저장, 목록 조회, 특정 대화 불러오기) | **100% 충족** | • Firestore `conversations` 컬렉션 자동 저장<br>• `GET/POST/DELETE/PUT /api/conversations`, `GET /api/conversations/{id}` 지원<br>• 사이드바 목록 클릭 시 대화 복원 ([`web/js/chat.js`](file:///Users/mongpark/codyssey/codyssey_m1_2/web/js/chat.js#L132)) |
| **최종 결과물 4** | **배포 및 문서화** (Swagger UI 확인 가능, README 안내, 스크린샷 3종 가이드) | **100% 충족** | • Docker Compose 로컬 배포 및 Render/Vercel 타깃 구성<br>• Swagger UI (`/docs`) 완비<br>• README.md 내 환경변수, 실행법, 스크린샷 3종 가이드 수록 |
| **데이터 선정** | 시계열 데이터 선정 및 최소 100개 이상 포인트, 요약 지표 산출 | **100% 충족** | • 삼성전자(`005930.KS`) 10년치 일별 데이터 **2,445건** 확보<br>• 최고/최저/평균/변동성/MDD/최근추세 요약 API (`/api/data/summary`) |
| **FastAPI 구성** | 앱 초기화, CORS 미들웨어 설정, Pydantic 검증 | **100% 충족** | • `CORSMiddleware` 적용 완료<br>• `DataItem`, `PortfolioItem`, `ChatRequest`, `ConversationCreate` 스키마 검증 |
| **Firestore 연동**| 영구 데이터베이스 연동 및 서비스 계정 키 환경 변수 격리 관리 | **100% 충족** | • `FIREBASE_SERVICE_ACCOUNT_JSON` 환경 변수 분기 처리<br>• `stock_data`, `portfolio`, `conversations`, `metadata` 컬렉션 설계 |
| **보너스 과제 1**| AI 도구 호출 (Function Calling) 스키마 정의 및 연동, README Rationale | **100% 충족** | • 3대 도구(`query_stock_data`, `analyze_portfolio`, `get_conversation_history`) 연동<br>• README에 호출 근거 및 호출 흐름 다이어그램 수록 |
| **보너스 과제 2**| 인사이트·UX 고도화 (차트 시각화, CSV 내보내기, 다크 모드 토글) | **100% 충족** | • Chart.js 꺾은선/캔들 차트<br>• 조회 데이터 CSV 다운로드 기능<br>• CSS 변수 및 LocalStorage 기반 다크 모드 토글 |

---

## 2. 🚀 요구사항 외 추가 구현 및 고도화 항목 (Extra Features)

본 프로젝트는 미션에서 요구한 기본 수준에 머무르지 않고, 실제 상용 서비스 수준의 완성도와 성능을 확보하기 위해 다음과 같은 추가 기능을 독자적으로 구현하였습니다.

### 1) 2계층 데이터베이스(Firestore + 로컬 SQLite) 및 동적 캐시 무효화
- **도입 배경**: 10년치 일별 주가 데이터(2,445건)를 매 요청마다 Firestore에서 직접 읽어올 경우, 막대한 클라우드 읽기 비용과 1~2초 이상의 네트워크 지연(Latency)이 발생합니다.
- **고도화 내용**:
  - 백엔드에 로컬 SQLite DB([`api/stock_cache.db`](file:///Users/mongpark/codyssey/codyssey_m1_2/api/stock_cache.db))를 도입하여 1차 캐시로 활용.
  - Firestore의 `metadata/stock_status` 문서 내 `version` 필드를 감지하여, 새로운 데이터가 적재될 때만 자동으로 로컬 SQLite 캐시를 무효화하고 동기화(Sync)하는 스마트 캐싱 아키텍처를 완성했습니다.
  - 결과적으로 대시보드 로딩 및 도구 호출 속도를 **밀리초(ms) 단위**로 단축시켰습니다.

### 2) 휴장일 자동 감지 및 스마트 날짜 확장 (`auto_expand_dates`)
- 사용자가 "2024년 5월 10일"과 같이 한글로 질문하거나 "2023년"과 같이 연도만 질문하는 경우:
  - `"2023년"` $\rightarrow$ `start_date="2023-01-01"`, `end_date="2023-12-31"`로 자동 확장.
  - `"2024년 4월"` $\rightarrow$ `start_date="2024-04-01"`, `end_date="2024-04-30"`로 자동 확장.
  - 사용자가 지정한 날짜가 주말이나 공휴일 등 주식시장 휴장일인 경우, **직전 거래일 데이터를 자동으로 역추적 조회하여 안내**하는 지능형 폴백(Fallback) 로직을 탑재했습니다.

### 3) 실시간 시장가 대조 가상 투자 포트폴리오 분석 (미실현 평가 손익 산출)
- 기존의 단순 CRUD 기록 관리를 넘어, 사용자가 매수/매도한 주식 수량과 평단가를 **SQLite에 캐시된 최신 삼성전자 종가와 실시간으로 대조**합니다.
- 단순 누적 매수액뿐만 아니라, **보유 주식 평가액, 미실현 평가 손익(원), 평가 수익률(%)**을 자동으로 계산하여 투자자에게 실전 수준의 자산 관리 피드백을 제공합니다.

### 4) 클라이언트 측 마크다운 표 파서 (`parseMarkdownTable`)
- LLM이 반환하는 파이프 형태의 마크다운 표(`| 날짜 | 종가 |`)를 프론트엔드 JavaScript에서 정규식 기반으로 가로채어, 미려하고 반응형에 최적화된 **HTML `<table>` 엘리먼트로 실시간 렌더링**합니다.
- 다크 모드와 연동되어 표의 테두리와 헤더 배경색이 자연스럽게 전환됩니다.

### 5) 대화 세션 인라인 제목 수정 (`PUT /api/conversations/{conv_id}`)
- 기본 첫 질문으로 자동 생성된 대화방 제목을 사용자가 원하는 이름으로 언제든지 변경할 수 있도록 프론트엔드 연필 아이콘 버튼 및 백엔드 `PUT` API를 구현했습니다.

### 6) 2종 차트(Line & Box/Candle) 및 자유 캘린더 구간 필터
- 고정된 기간 버튼(1일, 1주, 1개월, 1년) 외에도, 사용자가 원하는 임의의 날짜 구간(`start-date` ~ `end-date`)을 직접 선택하여 조회할 수 있는 캘린더 인터페이스를 지원하며, 꺾은선 차트와 캔들스틱(시가/고가/저가/종가) 박스 차트 간의 토글 기능을 제공합니다.

---

## 3. 🎓 과제 목표 6대 핵심 질문에 대한 심층 기술 해설

### Q1. 시계열 데이터를 분석하고, 요약 정보를 만들어 서비스에서 활용하는 흐름은 무엇인가?
1. **수집 및 정제**: `yfinance`를 통해 삼성전자(`005930.KS`)의 10년치 일별 OHLCV(시가, 고가, 저가, 종가, 거래량) 데이터를 수집하고, 결측치를 제거한 뒤 표준 포맷(`date`, `open`, `high`, `low`, `close`, `volume`)으로 정규화합니다.
2. **지표 연산 (통계 요약)**: 수집된 시계열 배열로부터 기간 시작/종료일, 최고가, 최저가, 평균가, 기간 등락률, 표준편차 기반의 변동성(Volatility), 최대 낙폭(MDD, Maximum Drawdown), 최근 단기 이동평균 기반의 추세(상승/하락/보합)를 백엔드에서 사전 연산합니다.
3. **서비스 계층 활용**: 
   - 대시보드 UI에서는 사용자가 한눈에 시장 상태를 파악할 수 있도록 상단 카드 그리드로 렌더링합니다.
   - AI 서비스 계층에서는 이 요약 정보를 시스템 프롬프트(컨텍스트)로 주입하여, AI가 방대한 원천 데이터를 일일이 읽지 않고도 핵심 통계를 바탕으로 즉각적이고 정확한 분석 답변을 생성하게 만듭니다.

### Q2. FastAPI 프로젝트를 라우터/서비스 등으로 분리해 구성한 기준은 무엇인가?
- **관심사 분리 (Separation of Concerns)** 원칙을 준수했습니다:
  - **진입점 및 라우팅 (`api/main.py`)**: 클라이언트의 HTTP 요청 수신, CORS 제어, Pydantic 요청 본문 검증, HTTP 상태 코드 반환 등 웹 계층의 책임을 담당합니다.
  - **데이터 수집 파이프라인 (`api/lib/collect_data.py`)**: 외부 금융 API(`yfinance`) 통신, 판다스 데이터프레임 변환, Firestore 대량 적재(Batch Write) 등 데이터 엔지니어링 로직을 격리했습니다.
  - **AI 지능형 서비스 (`api/lib/ai_service.py`)**: LLM 모델 초기화, 시스템 지침 설계, 도구 정의 및 자동 함수 호출(Automatic Function Calling), 예외 시 모델 폴백(Fallback) 등 AI 비즈니스 로직을 전담합니다.
- 이를 통해 특정 계층의 변경(예: Gemini $\rightarrow$ GPT 모델 교체, 또는 DB 스키마 변경)이 다른 계층에 영향을 주지 않는 모듈식 유지보수성을 달성했습니다.

### Q3. Pydantic을 활용해 요청 데이터 검증을 적용한 이유와 방식은 무엇인가?
- **이유**: 동적 타입 언어인 Python 환경에서 클라이언트가 전달한 JSON 페이로드의 타입 불일치(예: `price`에 문자열 입력), 필수 필드 누락, 유효하지 않은 열거값(예: `trade_type`에 "hold" 입력)을 런타임 이전에 차단하여 백엔드 안정성과 데이터 무결성을 보장하기 위함입니다.
- **적용 방식**:
  - `DataItem`: `date: str`, `value: float`, `memo: str = ""` 필드를 정의하여 표준 데이터 CRUD 시 자동 검증.
  - `PortfolioItem`: `trade_type: Literal["buy", "sell"]`을 통해 오직 'buy'와 'sell'만 허용하고, `price: float`, `quantity: int`를 강제.
  - `ChatRequest`: `message: str`, `conversation_id: str | None = None`을 통해 안전한 세션 ID 전달 보장.
  - 유효하지 않은 데이터 유입 시 FastAPI가 자동으로 `422 Unprocessable Entity` 에러와 상세 필드 위치를 클라이언트에 반환합니다.

### Q4. Firestore에 데이터를 저장하고 CRUD로 다루는 방법은 무엇인가?
- **NoSQL 컬렉션-문서 모델**:
  - `stock_data`: 일자별 고유 ID(`YYYY-MM-DD`)를 문서 키로 사용하여 중복 방지 및 날짜 기준 색인(Indexing) 조회 최적화.
  - `portfolio`: 자동 생성 UUID 문서 키를 사용하여 개별 매수/매도 이력을 독립된 레코드로 관리.
  - `conversations`: 대화방 ID 단위로 `messages` 배열 필드를 유지하며, `firestore.ArrayUnion` 연산자를 활용해 기존 메시지 유실 없이 원자적(Atomic)으로 대화 내역을 추가.
- **성능 최적화**:
  - 10년치 대량 데이터 적재 시 네트워크 라운드트립 비용을 최소화하기 위해 Firestore **Batch Commit(400개 단위)**을 적용했습니다.

### Q5. "데이터 요약을 시스템 프롬프트에 주입하는 방식(컨텍스트 주입)"의 원리와 한계 극복(Function Calling)은 무엇인가?
- **컨텍스트 주입 원리**: LLM은 비공개 내부 데이터나 최신 시계열을 학습하지 못했으므로, 사용자의 질문 이전에 시스템 지시문(System Instruction) 영역에 사전에 연산된 데이터 요약(기간, 종가, 최고/최저, 트렌드)을 텍스트 형태로 삽입하여 LLM의 주의 집중(Attention) 공간에 배치하는 기법입니다.
- **한계점**: 
  1. 수천 건의 일별 시계열 데이터를 프롬프트에 전부 넣으면 입력 토큰 수가 폭증하여 비용이 급증하고 응답 속도가 저하됩니다.
  2. 컨텍스트가 너무 길어지면 LLM이 중간에 위치한 특정 일자의 데이터를 망각하는 'Lost in the Middle' 현상이 발생합니다.
- **Function Calling을 통한 한계 극복**:
  - 시스템 프롬프트에는 단지 '최근 1개월 요약'만 최소한으로 주입하고,
  - 과거 10년치 특정 날짜/기간, 역대 기록, 포트폴리오 상태 등 심층 데이터는 **AI가 도구(`query_stock_data`, `analyze_portfolio`)를 호출하여 필요한 순간에만 SQLite DB에서 정확한 팩트를 동적으로 조회**하도록 설계하여 토큰 낭비와 환각(Hallucination)을 원천 차단했습니다.

### Q6. 배포 환경에서 CORS, 환경 변수, 키 관리가 왜 필요한가?
- **CORS (Cross-Origin Resource Sharing) 관리**: 브라우저의 동일 출처 정책(SOP)에 의해 프론트엔드 도메인(예: `vercel.app`)과 백엔드 API 도메인(예: `onrender.com`)의 오리진(Origin)이 다르면 API 호출이 차단됩니다. 이를 해결하기 위해 백엔드에서 `CORSMiddleware`를 구성하여 허용된 오리진에서의 HTTP 메서드와 헤더를 안전하게 인가해야 합니다.
- **환경 변수 및 키 격리**:
  - `GEMINI_API_KEY`, Firebase `serviceAccountKey.json`과 같은 인증 자격 증명이 GitHub 공개 저장소에 커밋되면 자동 크롤러에 의해 탈취되어 막대한 과금 피해나 데이터베이스 유출이 발생할 수 있습니다.
  - 따라서 모든 민감 정보는 `.gitignore`에 등록하고, Render 및 Vercel의 배포 환경 변수(Environment Variables) 설정 패널을 통해서만 런타임에 주입받도록 철저히 격리해야 합니다.

---

## 4. 📝 종합 요약 및 제출 안내

1. **요구사항 100% 충족**: 미션에서 요구한 4대 결과물, 5대 데이터 API, 3대 대화 API, AI 챗봇 컨텍스트 주입, 바닐라 프론트엔드, README 가이드 및 보너스 과제(Function Calling, 시각화, CSV, 다크모드)가 완전하게 구현 및 검증되었습니다.
2. **현업 수준의 안정성**: 2계층 캐시 아키텍처, 휴장일 감지, 실시간 평가 손익 연산, 마크다운 표 렌더링 등 실질적인 UX 고도화가 결합되었습니다.
3. 본 보고서([`add_report.md`](file:///Users/mongpark/codyssey/codyssey_m1_2/add_report.md))와 프로젝트 설명서([`README.md`](file:///Users/mongpark/codyssey/codyssey_m1_2/README.md))를 함께 참조하시면 프로젝트의 설계 의도와 완성도를 완벽히 파악하실 수 있습니다.
