from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
try:
    from firebase_admin import firestore
except ImportError:
    firestore = None
from api.core.database import get_firestore_client
from api.models.data import DataItem
from api.services.stock_service import get_cached_stock_data_with_version, calculate_stock_summary

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("", summary="주가 데이터 목록 조회")
def get_stock_data(limit: int = Query(30, ge=1, le=2500, description="조회할 데이터 개수 (1~2,500)")):
    try:
        items = get_cached_stock_data_with_version()
        results = items[:limit]
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")

@router.get("/summary", summary="주가 데이터 요약 통계 산출")
def get_data_summary(limit: int = Query(100, ge=1, le=2500, description="통계 산출 대상 데이터 개수")):
    try:
        summary_result = calculate_stock_summary(limit=limit)
        return summary_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", summary="새 분석 데이터 추가")
def add_data(item: DataItem):
    try:
        db = get_firestore_client()
        if db is None:
            raise HTTPException(status_code=503, detail="Firebase 데이터베이스에 연결할 수 없습니다.")

        doc_data = {
            "date": item.date,
            "value": item.value,
            "close": item.value,
            "memo": item.memo,
            "open": item.value,
            "high": item.value,
            "low": item.value,
            "created_at": datetime.now().isoformat()
        }
        _, doc_ref = db.collection("stock_data").add(doc_data)
        try:
            db.collection("metadata").document("stock_status").set(
                {"version": firestore.Increment(1)}, merge=True
            )
        except Exception:
            pass
        return {"status": "success", "message": "데이터가 성공적으로 추가되었습니다.", "id": doc_ref.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 추가 실패: {str(e)}")

@router.put("/{doc_id}", summary="기존 분석 데이터 수정")
def update_data(doc_id: str, item: DataItem):
    try:
        db = get_firestore_client()
        if db is None:
            raise HTTPException(status_code=503, detail="Firebase 데이터베이스에 연결할 수 없습니다.")

        doc_ref = db.collection("stock_data").document(doc_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="해당 데이터를 찾을 수 없습니다.")

        update_dict = {
            "date": item.date,
            "value": item.value,
            "close": item.value,
            "memo": item.memo,
            "updated_at": datetime.now().isoformat()
        }
        doc_ref.update(update_dict)
        try:
            db.collection("metadata").document("stock_status").set(
                {"version": firestore.Increment(1)}, merge=True
            )
        except Exception:
            pass
        return {"status": "success", "message": "데이터가 성공적으로 수정되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 수정 실패: {str(e)}")

@router.delete("/{doc_id}", summary="기존 분석 데이터 삭제")
def delete_data(doc_id: str):
    try:
        db = get_firestore_client()
        if db is None:
            raise HTTPException(status_code=503, detail="Firebase 데이터베이스에 연결할 수 없습니다.")

        doc_ref = db.collection("stock_data").document(doc_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="해당 데이터를 찾을 수 없습니다.")

        doc_ref.delete()
        try:
            db.collection("metadata").document("stock_status").set(
                {"version": firestore.Increment(1)}, merge=True
            )
        except Exception:
            pass
        return {"status": "success", "message": "데이터가 성공적으로 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 삭제 실패: {str(e)}")
