import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

MODEL_LIST = [
    "gemini-3.5-flash",       # 1순위: 빠르고 효율적인 기본 모델
    "gemini-3.5-flash-lite",  # 2순위: 더 가벼운 예비(Fallback) 모델
    "gemini-3.5-pro"          # 3순위: 고성능 예비 모델
]

def parse_friendly_error(error_msg: str) -> str:
    """에러 메시지를 사용자 친화적으로 번역"""
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
    
    # ✨ AI의 완벽한 도구 통제를 위한 시스템 프롬프트 (조건 명확화)
    system_instruction = f"""당신은 '삼성전자 AI 투자 비서'입니다.

[시스템 컨텍스트 (단순 최근 1개월 미리보기)]
{context_data}

[🚨 필수 도구(Function) 사용 규칙 🚨]
당신은 완벽한 팩트 체크를 위해 아래 3가지 도구를 반드시 사용해야 합니다. 사용자가 과거 데이터를 물어볼 때 절대 "조회 불가"나 "범위 초과"라고 답하지 말고 무조건 도구를 호출하세요!

1. 과거 주가 조회 도구 (`query_stock_data`):
   - 조건: 사용자가 특정 연도, 특정 월(예: 2026년 7월), 특정일의 종가/최고가/최저가/거래량을 물어볼 때.
   - 행동: 절대 내부 지식으로 지어내지 말고, 이 도구에 날짜 파라미터(`start_date`, `end_date`)를 세팅하여 호출하세요.
   
2. 포트폴리오 조회 도구 (`analyze_portfolio`):
   - 조건: 사용자가 본인의 "가상 투자", "포트폴리오", "매수/매도 기록", "수익률", "보유 수량"을 언급할 때.
   - 행동: 당신이 임의로 계산하지 말고, 이 도구를 호출하여 서버에서 정확히 계산된 값을 받아오세요.

3. 과거 채팅 기록 조회 도구 (`get_conversation_history`):
   - 조건: "아까 말한거", "저번에", "이전 대화" 등 과거 채팅 문맥을 물어볼 때.
   - 행동: 현재 대화방 ID를 이용해 이 도구를 호출하세요.

[응답 규칙]
1. 수치가 포함된 내용은 깔끔한 마크다운 표(|---|)로 정리하세요.
2. 불필요한 사과나 변명("죄송합니다", "조회 불가입니다" 등)을 하지 마세요. 도구를 쓰면 다 알 수 있습니다.""" 

    last_error = ""
    # 환각 방지를 위해 온도 0.1로 고정
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
            continue
            
    return f"안내: {parse_friendly_error(last_error)}"