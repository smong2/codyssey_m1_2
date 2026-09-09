from fastapi import APIRouter, HTTPException
from api.models.portfolio import PortfolioItem
from api.services.portfolio_service import get_portfolio_list, add_portfolio_item, delete_portfolio_item

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.get("", summary="가상 포트폴리오 목록 조회")
def get_portfolio():
    try:
        results = get_portfolio_list()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", summary="가상 포트폴리오 거래 내역 추가")
def create_portfolio(item: PortfolioItem):
    try:
        new_id = add_portfolio_item(item)
        return {"status": "success", "message": "추가되었습니다.", "id": new_id}
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}", summary="가상 포트폴리오 거래 내역 삭제")
def remove_portfolio(doc_id: str):
    try:
        delete_portfolio_item(doc_id)
        return {"status": "success", "message": "삭제되었습니다."}
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
