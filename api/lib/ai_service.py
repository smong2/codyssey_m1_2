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
    """Gemini API를 호출하여 답변을 생성합니다. (Function Calling 지원)"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "안내: API 키가 설정되지 않아 답변을 생성할 수 없습니다. 시스템 관리자에게 문의해 주세요."

    genai.configure(api_key=api_key)
    
    # ✨ AI의 과거 데이터 환각(Hallucination) 방지를 위한 강력 통제 프롬프트
    system_instruction = f"""당신은 '삼성전자 AI 투자 비서'입니다.

[시스템 컨텍스트 (단순 미리보기)]
{context_data}

[도구(Tool) 사용 강제 행동 강령 - 매우 중요]
⚠️ 당신은 과거 주가 데이터를 조회할 때 절대 "조회 불가", "제공된 시스템 데이터 범위 초과", "알 수 없습니다"라고 대답해서는 안 됩니다.

1. 주가 데이터 조회: 사용자가 위의 1개월 미리보기 컨텍스트에 없는 과거의 특정 연도, 특정 월(예: 2026년 7월), 특정일의 데이터를 물어보면, 당신의 사전 지식을 추측하지 말고 **반드시 `query_stock_data` 도구를 호출**하세요!
   - (규칙) 사용자가 특정 달(예: "2026년 7월")을 물어보면: intent="summary", start_date="2026-07-01", end_date="2026-07-31" 로 날짜 범위를 변환하여 도구를 호출하세요.
2. 과거 대화 기록 조회: "아까", "이전에", "저번에" 등 과거 대화 내용을 분석해야 할 때는 **`get_conversation_history` 도구**를 호출하세요.
3. 포트폴리오 분석: 사용자의 매수/매도 기록, 현재 보유 수량, 수익률 등을 물어볼 때는 직접 계산하지 말고 **`analyze_portfolio` 도구**를 호출하세요.
4. 외부 뉴스/이슈 검색: 주가 하락/상승 이유, 특정 시기의 반도체 뉴스 등 DB에 없는 외부 정보는 당신의 방대한 내부 사전 지식을 활용해 팩트 기반으로 답변하세요.

[응답 규칙]
1. 불필요한 서론/결론은 생략하세요.
2. 수치가 포함된 내용은 반드시 '마크다운 표(|---|)' 기법을 사용해 예쁘게 정리하세요.
3. 표 아래에 전체 상황에 대한 인사이트를 1~2줄로 요약하세요.""" 

    last_error = ""
    
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