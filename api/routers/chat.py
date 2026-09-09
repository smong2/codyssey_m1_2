from fastapi import APIRouter, HTTPException
from api.models.chat import ChatRequest
from api.services.chat_service import process_chat_message

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", summary="데이터 기반 AI 대화")
def chat_endpoint(request: ChatRequest):
    try:
        reply, conv_id = process_chat_message(
            message=request.message,
            conversation_id=request.conversation_id
        )
        return {
            "status": "success",
            "reply": reply,
            "conversation_id": conv_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
