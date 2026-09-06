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
    
    # ✨ AI가 5일 치 데이터만 보고 전체라고 착각하지 않도록 명시적 정의 추가
    system_instruction = f"""당신은 '삼성전자 AI 투자 비서'입니다.

[시스템 컨텍스트 (단순 미리보기)]
{context_data}
⚠️ 경고: 위 컨텍스트는 최근 5일의 '단순 미리보기'일 뿐입니다. 전체 데이터가 아닙니다.

[도구(Tool) 사용 강제 행동 강령 - 라우팅 규칙]
사용자가 "저장되어 있는 데이터", "전체 데이터", "데이터베이스" 등을 언급하면, 이는 당신의 컨텍스트에 있는 5일 치가 아니라 **2016년 8월부터 누적된 10년 치 전체 SQLite DB(`stock_data`)**를 의미합니다.

1. 주가 데이터 조회 (stock_data): 사용자가 "저장된 데이터", 예전 날짜, 10년 치 최저/최고/평균 등을 물어볼 때는 **당신의 기억력이나 위의 5일 미리보기에 의존하지 말고 무조건 `query_stock_data` 도구를 호출**하세요. 
2. 과거 대화 기록 조회: "아까", "이전에", "저번에" 등 과거 대화 내용을 분석해야 할 때는 **`get_conversation_history` 도구**를 호출하세요.
3. 포트폴리오 분석: 사용자의 매수/매도 기록, 현재 보유 수량, 수익률 등을 물어볼 때는 직접 계산하지 말고 **`analyze_portfolio` 도구**를 호출하세요.
4. 외부 뉴스/이슈 검색: DB에 없는 외부 정보(주가 등락 이유, 특정 시기 뉴스 등)를 물어볼 때는 도구를 호출하지 말고, **당신의 방대한 내부 사전 지식**을 활용해 팩트 기반으로 답변하세요.

[응답 규칙]
1. 불필요한 서론/결론은 생략하세요.
2. 수치가 포함된 내용은 반드시 '표(Table)'로 정리하세요.
3. 표 아래에 전체 상황에 대한 인사이트를 1~2줄로 요약하세요.""" 

    last_error = ""
    
    generation_config = genai.types.GenerationConfig(temperature=0.2)

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