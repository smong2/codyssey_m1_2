from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
try:
    from firebase_admin import firestore
except ImportError:
    firestore = None
from api.core.database import get_firestore_client
from api.services.stock_service import get_cached_stock_data_with_version, query_stock_data
from api.services.portfolio_service import analyze_portfolio
from api.lib.ai_service import generate_ai_reply

_CURRENT_ACTIVE_CONV_ID: str = ""

def get_conversation_history(conversation_id: str = "") -> str:
    """[대화 기록 조회 도구] AI 에이전트 전용 Function Calling 도구"""
    global _CURRENT_ACTIVE_CONV_ID
    target_id = conversation_id if (conversation_id and conversation_id != "None") else _CURRENT_ACTIVE_CONV_ID

    if not target_id or target_id == "None":
        return "[💡 시스템 알림: 새로 시작된 대화방이므로 이전 대화 기록이 존재하지 않습니다.]"

    db = get_firestore_client()
    if db is None:
        return f"[💡 시스템 알림: 대화방 '{target_id}' 기록을 조회할 수 없습니다 (Firebase 미연결).]"

    try:
        doc = db.collection("conversations").document(target_id).get()
        if doc.exists:
            messages = doc.to_dict().get("messages", [])
            if not messages:
                return "[💡 시스템 알림: 이전 대화 내역이 비어 있습니다.]"
            recent_msgs = messages[-6:]
            history_text = "\n".join([f"- [{m.get('role')}]: {m.get('content')}" for m in recent_msgs])
            return f"[💡 시스템 알림: 대화방({target_id})의 직전 대화 기록]\n{history_text}"
        return f"[💡 시스템 알림: 대화방({target_id})의 이전 대화 기록을 찾을 수 없습니다.]"
    except Exception as e:
        return f"[💡 시스템 알림: 대화 기록 조회 중 오류가 발생했습니다: {str(e)}]"

def process_chat_message(message: str, conversation_id: Optional[str] = None) -> Tuple[str, str]:
    """사용자의 채팅 메시지를 처리하고 AI 응답 및 대화방 ID를 반환합니다."""
    global _CURRENT_ACTIVE_CONV_ID
    _CURRENT_ACTIVE_CONV_ID = conversation_id or ""

    all_stock = get_cached_stock_data_with_version()
    stock_items = all_stock[:30]

    context_data = "[최근 1개월 삼성전자 주가 기초 데이터 (참고용 요약)]\n"
    if stock_items:
        prices = [item.get('close', item.get('value', 0)) for item in stock_items]
        chrono_prices = prices[::-1]
        max_p = max(prices)
        min_p = min(prices)
        avg_p = sum(prices) / len(prices)
        start_price = chrono_prices[0]
        end_price = chrono_prices[-1]
        return_rate = ((end_price - start_price) / start_price) * 100 if start_price else 0

        context_data += f"- 기준일: {stock_items[-1]['date']} ~ {stock_items[0]['date']}\n"
        context_data += f"- 최근 종가: {end_price:,}원\n"
        context_data += f"- 최고/최저가: {max_p:,}원 / {min_p:,}원 (평균: {int(avg_p):,}원)\n"
        context_data += f"- 기간 수익률: {round(return_rate, 2)}%\n"
    else:
        context_data += "주가 데이터를 불러오지 못했습니다.\n"

    current_conv_id = conversation_id or "None"
    context_data += (
        f"\n[현재 접속된 대화방 상태]\n"
        f"- 대화방 ID: {current_conv_id}\n"
        f"- 🚨 필수 원칙: 위 기초 데이터 외에 '과거 데이터', '이전 데이터', '특정일', '특정 기간(연도/월)', '역대 최고/최저가'를 물어보면 자의적으로 답변하지 말고 반드시 query_stock_data 도구를 호출하여 조회하세요.\n"
        f"- 포트폴리오(투자 내역, 수익률, 평단가) 질문은 analyze_portfolio 도구를, 이전 대화 내용은 get_conversation_history 도구를 호출하세요.\n"
    )

    ai_tools = [query_stock_data, analyze_portfolio, get_conversation_history]
    reply = generate_ai_reply(message, context_data, tools=ai_tools)

    db = get_firestore_client()
    timestamp = datetime.now().isoformat()
    conv_id = conversation_id or f"session-{int(datetime.now().timestamp())}"

    if db is not None:
        try:
            if conversation_id:
                conv_ref = db.collection("conversations").document(conversation_id)
                conv_ref.update({
                    "updated_at": timestamp,
                    "messages": firestore.ArrayUnion([
                        {"role": "user", "content": message},
                        {"role": "ai", "content": reply}
                    ])
                })
                conv_id = conversation_id
            else:
                title = message[:15] + "..." if len(message) > 15 else message
                _, doc_ref = db.collection("conversations").add({
                    "title": title,
                    "updated_at": timestamp,
                    "messages": [
                        {"role": "user", "content": message},
                        {"role": "ai", "content": reply}
                    ]
                })
                conv_id = doc_ref.id
        except Exception as e:
            print(f"⚠️ 대화 Firestore 저장 실패: {e}")

    return reply, conv_id

def list_conversations() -> List[Dict[str, Any]]:
    """모든 대화방 목록을 최신순으로 조회합니다."""
    db = get_firestore_client()
    if db is None:
        return []
    try:
        docs = db.collection("conversations").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
        return [{"id": doc.id, "title": doc.to_dict().get("title", "새 대화")} for doc in docs]
    except Exception as e:
        print(f"⚠️ list_conversations 오류: {e}")
        return []

def get_conversation_detail(conv_id: str) -> Optional[Dict[str, Any]]:
    """특정 대화방의 상세 내역을 반환합니다."""
    db = get_firestore_client()
    if db is None:
        return None
    doc = db.collection("conversations").document(conv_id).get()
    return doc.to_dict() if doc.exists else None

def create_new_conversation(title: str, messages: List[Dict[str, Any]]) -> str:
    """새 대화 세션을 생성하고 ID를 반환합니다."""
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Firebase 데이터베이스에 연결할 수 없습니다.")
    timestamp = datetime.now().isoformat()
    _, doc_ref = db.collection("conversations").add({
        "title": title,
        "updated_at": timestamp,
        "messages": messages
    })
    return doc_ref.id

def delete_conversation_session(conv_id: str) -> bool:
    """특정 대화 세션을 삭제합니다."""
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Firebase 데이터베이스에 연결할 수 없습니다.")
    db.collection("conversations").document(conv_id).delete()
    return True

def update_session_title(conv_id: str, new_title: str) -> bool:
    """대화 세션 제목을 수정합니다."""
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Firebase 데이터베이스에 연결할 수 없습니다.")
    db.collection("conversations").document(conv_id).update({"title": new_title})
    return True
