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

def generate_ai_reply(user_message: str, context_data: str = "") -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "안내: API 키가 설정되지 않아 답변을 생성할 수 없습니다. 시스템 관리자에게 문의해 주세요."

    genai.configure(api_key=api_key)
    
    system_instruction = f"""당신은 '삼성전자 AI 투자 비서'입니다.
[시스템 데이터]
{context_data}

[응답 규칙]
1. 불필요한 서론/결론은 생략하세요.
2. 수익 계산, 통계 등 수치가 포함된 내용은 반드시 '표(Table)'로 깔끔하게 정리하세요.
3. 표 바로 아래에 전체 상황에 대한 요약/인사이트를 1~2줄로 아주 짧게 덧붙이세요.""" 

    last_error = ""
    for model_name in MODEL_LIST:
        try:
            model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
            return model.generate_content(user_message).text
        except Exception as e:
            last_error = str(e)
            continue
            
    return f"안내: {parse_friendly_error(last_error)}" 