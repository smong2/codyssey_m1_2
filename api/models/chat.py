import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from api.core.security import check_malicious_input, sanitize_text

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="사용자 질문 메시지 (1자 이상 1,000자 이하)"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="대화방 세션 ID (영숫자, 하이픈, 언더스코어 조합)"
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if check_malicious_input(v, field_name="ChatRequest.message"):
            raise ValueError("질문 내용에 악성 스크립트 또는 허용되지 않은 태그가 포함되어 있습니다.")
        return sanitize_text(v)

    @field_validator("conversation_id")
    @classmethod
    def validate_conv_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "":
            v = v.strip()
            if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', v):
                raise ValueError("대화방 ID는 영문, 숫자, 하이픈(-), 언더스코어(_)로 구성된 64자 이내여야 합니다.")
        return v

class ConversationTitleUpdate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="대화방 변경 제목 (1자 이상 100자 이하)"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if check_malicious_input(v, field_name="ConversationTitleUpdate.title"):
            raise ValueError("제목에 허용되지 않은 스크립트 또는 태그가 포함되어 있습니다.")
        return sanitize_text(v)

class ConversationCreate(BaseModel):
    title: str = Field(
        default="새 대화",
        min_length=1,
        max_length=100,
        description="대화방 초기 제목"
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="초기 메시지 목록"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return sanitize_text(v)
