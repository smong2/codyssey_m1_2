from fastapi import APIRouter, HTTPException
from api.models.chat import ConversationCreate, ConversationTitleUpdate
from api.services.chat_service import (
    list_conversations,
    get_conversation_detail,
    create_new_conversation,
    delete_conversation_session,
    update_session_title
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.get("", summary="대화방 목록 조회")
def get_conversations():
    try:
        results = list_conversations()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", summary="새 대화 세션 수동 저장")
def create_conversation(data: ConversationCreate):
    try:
        new_id = create_new_conversation(data.title, data.messages)
        return {"status": "success", "message": "대화가 성공적으로 저장되었습니다.", "id": new_id}
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대화 저장 실패: {str(e)}")

@router.get("/{conv_id}", summary="특정 대화 상세 내역 조회")
def get_conversation(conv_id: str):
    try:
        detail = get_conversation_detail(conv_id)
        if detail is not None:
            return {"status": "success", "data": detail}
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{conv_id}", summary="특정 대화방 삭제")
def delete_conversation(conv_id: str):
    try:
        delete_conversation_session(conv_id)
        return {"status": "success", "message": "삭제되었습니다."}
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{conv_id}", summary="대화방 제목 수정")
def update_title(conv_id: str, data: ConversationTitleUpdate):
    try:
        update_session_title(conv_id, data.title)
        return {"status": "success"}
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
