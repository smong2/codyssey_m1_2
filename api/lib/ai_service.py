import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

MODEL_LIST = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.5-flash",       
    "gemini-3.5-flash-lite",  
    "gemini-3.5-pro",
    "gemini-1.5-pro"
]

def parse_friendly_error(error_msg: str) -> str:
    err_lower = error_msg.lower()
    if "404" in err_lower or "not found" in err_lower:
        return "AI 모델을 찾을 수 없습니다."
    if "quota" in err_lower or "exhausted" in err_lower or "429" in err_lower:
        return "API 키 한도에 도달했습니다."
    return "네트워크 상태가 불안정하거나 알 수 없는 오류입니다."

def generate_ai_reply(user_message: str, context_data: str = "", tools: list = None) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "안내: API 키가 설정되지 않아 답변을 생성할 수 없습니다."

    genai.configure(api_key=api_key)
    
    # ✨ 3가지 전용 도구(Function Calling) 강제 호출 및 역할 명확화 프롬프트
    system_instruction = f"""당신은 삼성전자 10년치 일별 주가 데이터베이스(SQLite) 및 사용자 포트폴리오(Firestore)와 실시간으로 연동된 전문 AI 투자 비서입니다.

{context_data}

[🚨 필수 행동 강령: 도구(Function Calling) 무조건 호출 원칙 🚨]
1. 기본 컨텍스트 한계 인식:
   위 [시스템 데이터]에 포함된 정보는 오직 '최근 1개월 주가 요약'에 불과합니다.
   따라서 이를 제외한 모든 과거 데이터, 이전 시점 데이터, 특정 날짜, 특정 기간, 역대 기록, 사용자 포트폴리오, 대화 기록은 당신의 사전 지식에 절대 존재하지 않습니다.

2. 거절 및 변명 절대 금지:
   절대로 "과거 데이터가 없습니다", "조회 권한이 없습니다", "데이터를 불러올 수 없습니다" 등의 거절 멘트를 출력하지 마세요.
   당신에게는 2016년부터의 전체 데이터를 실시간으로 조회할 수 있는 3가지 강력한 도구가 주어져 있습니다.

3. 사용자 의도별 도구 호출 규칙 (아래 상황 발생 시 질문에 바로 답변하지 말고 반드시 도구를 먼저 호출할 것):

   가. `query_stock_data` (삼성전자 10년치 과거 주가 DB 전용 조회 도구)
       - 호출 시점:
         * '과거 데이터', '이전 데이터', '예전 주가', '데이터 보여줘', '전체 데이터' 등을 요구할 때
         * 특정 단일 일자(하루)의 주가를 물어볼 때 (예: "2024년 5월 10일 종가는?", "어제 주가", "특정 날짜 시가/종가")
         * 특정 기간, 연도, 월의 주가나 추세를 물어볼 때 (예: "2023년 주가 어땠어?", "작년 7월 최고가", "최근 1년 추세")
         * 역대 최고가/최저가 등 전체 통계를 물어볼 때 (예: "삼성전자 역대 최고가 얼마야?", "역대 최저가는?")
       - 호출 파라미터 매핑:
         * 과거 데이터/이전 데이터 전체 현황: query_stock_data(query_type="range_summary")
         * 특정 단일 날짜: query_stock_data(query_type="exact_date", target_date="YYYY-MM-DD")
         * 특정 연도/월/기간: query_stock_data(query_type="range_summary", start_date="YYYY-MM-DD", end_date="YYYY-MM-DD")
         * 역대 최고가: query_stock_data(query_type="max_all")
         * 역대 최저가: query_stock_data(query_type="min_all")

   나. `analyze_portfolio` (가상 투자 포트폴리오 및 실시간 수익률 조회 도구)
       - 호출 시점:
         * 사용자가 자신의 투자 내역, 보유 주식 수량, 매수/매도 기록, 평균 단가(평단가), 실시간 수익률, 평가 손익 등을 물어볼 때
         * 예: "내 주식 몇 주 있어?", "내 평단가 얼마야?", "내 포트폴리오 수익률 어때?", "내 가상 투자 현황"
       - 호출 파라미터: analyze_portfolio() (인자 없이 호출)

   다. `get_conversation_history` (대화 기록 조회 도구)
       - 호출 시점:
         * "아까 내가 뭐라고 했지?", "방금 물어본 거 다시 말해줘", "이전 대화 내용 기억해?" 등 이전 대화 맥락을 물어볼 때
       - 호출 파라미터: get_conversation_history() (또는 context_data에 명시된 대화방 ID 전달)

[답변 작성 및 출력 규칙]
1. 도구가 반환한 날짜와 수치는 절대로 임의로 수정하거나 왜곡하지 말고 100% 팩트 그대로 출력하세요.
2. 모든 주가 및 통계 수치는 반드시 마크다운 표(|---|)로 일목요연하게 정리하세요.
3. 모든 금액 수치는 정수형태(예: 75,991원)로 천 단위 콤마를 넣어 읽기 쉽게 표기하세요.
4. 표 바로 아래에 데이터에 근거한 객관적인 시장 분석 및 투자 인사이트를 1~2줄로 친절하게 덧붙이세요.""" 

    last_error = ""
    # 환각 억제를 위해 온도 0.1 고정
    generation_config = genai.types.GenerationConfig(temperature=0.1)

    for model_name in MODEL_LIST:
        try:
            model = genai.GenerativeModel(
                model_name=model_name, 
                system_instruction=system_instruction,
                tools=tools
            )
            
            if tools:
                chat = model.start_chat(enable_automatic_function_calling=True)
                response = chat.send_message(user_message, generation_config=generation_config)
                return response.text
            else:
                return model.generate_content(user_message, generation_config=generation_config).text
                
        except Exception as e:
            last_error = str(e)
            print(f"⚠️ [AI 호출 실패 ({model_name})]: {e}")
            continue
            
    return f"안내: {parse_friendly_error(last_error)}"