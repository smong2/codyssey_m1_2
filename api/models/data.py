from pydantic import BaseModel, Field, field_validator
from api.core.security import validate_date_format, check_malicious_input, sanitize_text

class DataItem(BaseModel):
    date: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="기준 일자 (YYYY-MM-DD)",
        examples=["2024-05-10"]
    )
    value: float = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="주가 또는 수치 (0원 초과 10,000,000원 이하)"
    )
    memo: str = Field(
        default="",
        max_length=200,
        description="분석 메모 (최대 200자, XSS 스크립트 차단)"
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return validate_date_format(v)

    @field_validator("memo")
    @classmethod
    def validate_and_sanitize_memo(cls, v: str) -> str:
        if not v:
            return ""
        if check_malicious_input(v, field_name="DataItem.memo"):
            raise ValueError("악성 스크립트 또는 허용되지 않은 태그가 감지되었습니다.")
        return sanitize_text(v)
