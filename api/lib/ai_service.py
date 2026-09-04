import os
import google.generativeai as genai

def generate_ai_reply(user_message: str, context_data: str = "") -> str:
    """Gemini API를 호출하여 문맥 정보와 함께 사용자 질문에 대한 답변을 생성합니다."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY가 올바르게 설정되지 않았습니다. .env 파일을 확인해주세요.")

    genai.configure(api_key=api_key)
    
    # 💡 핵심: 시스템 프롬프트에 사용자의 현재 상황(Context)을 강제로 주입합니다.
    system_instruction = f"""당신은 '삼성전자 AI 투자 비서'입니다.
사용자에게 다정하고 전문적인 어조로 주식 시장과 삼성전자에 대한 인사이트를 제공합니다.
답변은 간결하고 가독성 좋게 작성하되, '투자에 대한 최종 판단과 책임은 본인에게 있다'는 뉘앙스를 자연스럽게 포함해주세요.

[시스템이 제공하는 사용자 현재 데이터 (절대적인 사실로 간주할 것)]
{context_data}

위 데이터를 바탕으로 사용자의 질문에 정확하고 개인화된 답변을 제공하세요. 사용자가 자신의 투자 내역이나 수익을 물어보면 이 데이터를 기반으로 계산하여 답변하고, 데이터가 비어있다면 일반적인 조언을 제공하세요."""

    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        system_instruction=system_instruction
    )
    
    response = model.generate_content(user_message)
    return response.text