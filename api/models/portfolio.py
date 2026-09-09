from typing import Literal
from pydantic import BaseModel, Field, field_validator
from api.core.security import validate_date_format

class PortfolioItem(BaseModel):
    trade_type: Literal["buy", "sell"] = Field(
        default="buy",
        description="매수(buy) 또는 매도(sell) 거래 유형"
    )
    date: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="거래 일자 (YYYY-MM-DD)",
        examples=["2024-01-02"]
    )
    price: float = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="체결 단가 (0원 초과 10,000,000원 이하)"
    )
    quantity: int = Field(
        ...,
        gt=0,
        le=1_000_000,
        description="체결 수량 (1주 이상 1,000,000주 이하)"
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return validate_date_format(v)
