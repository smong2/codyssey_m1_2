import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import json

# 1. 환경 변수 로드
load_dotenv()

# 2. Firebase 초기화 함수 (중복 초기화 방지)
def initialize_firebase():
    if not firebase_admin._apps:
        # 1. 환경 변수에서 값 가져오기
        firebase_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        
        try:
            # 2. 만약 환경 변수 값이 파일 경로가 아니라 '{'로 시작하는 JSON 텍스트 전체라면 (Render 배포 환경)
            if firebase_env and firebase_env.strip().startswith("{"):
                cred_dict = json.loads(firebase_env)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("🔥 Firebase 초기화 성공 (Render 환경 변수 JSON 텍스트 사용)!")
            
            # 3. 파일 경로이거나 환경변수에 값이 없으면 파일에서 읽기 (로컬 개발 환경)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                default_key_path = os.path.join(base_dir, "..", "serviceAccountKey.json")
                key_path = firebase_env if firebase_env else default_key_path
                
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                print(f"🔥 Firebase 초기화 성공 (로컬 파일 경로: {key_path})!")
                
        except Exception as e:
            print(f"❌ Firebase 초기화 실패: {e}")
            exit(1)
            
    return firestore.client()

# 3. 주식 데이터 수집 및 Firestore('stock_data') 업로드 핵심 함수
def fetch_and_save_stock_data(period: str = "10y", start: str = None, end: str = None):
    db = initialize_firebase()
    ticker = "005930.KS"  # 삼성전자 종목 코드
    
    if start and end:
        print(f"📈 yfinance 수집 중 (기간 지정): {start} ~ {end}")
        df = yf.download(ticker, start=start, end=end, interval="1d")
    else:
        print(f"📈 yfinance 수집 중 (기본 period: {period})")
        df = yf.download(ticker, period=period, interval="1d")
    
    if df.empty:
        print("❌ 수집된 데이터가 없습니다. 날짜나 네트워크를 확인해주세요.")
        return 0

    # MultiIndex 컬럼 구조 평탄화 (yfinance 버전 호환성 처리)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 결측치 제거
    df = df.dropna(subset=['Close'])
    
    print(f"✨ 총 {len(df)}개의 데이터 포인트를 확보했습니다. Firestore('stock_data')에 업로드를 시작합니다...")

    collection_ref = db.collection("stock_data")
    batch = db.batch()
    batch_count = 0
    total_saved = 0

    for index, row in df.iterrows():
        # 날짜 포맷 변환 (YYYY-MM-DD)
        date_str = index.strftime("%Y-%m-%d")
        close_price = float(row['Close'])
        open_price = float(row['Open']) if 'Open' in row and not pd.isna(row['Open']) else 0
        high_price = float(row['High']) if 'High' in row and not pd.isna(row['High']) else 0
        low_price = float(row['Low']) if 'Low' in row and not pd.isna(row['Low']) else 0
        volume = int(row['Volume']) if 'Volume' in row and not pd.isna(row['Volume']) else 0
        
        memo_str = f"시가:{open_price}, 고가:{high_price}, 저가:{low_price}, 거래량:{volume}"
        
        # SQLite 캐싱 및 박스 차트(캔들스틱) 대응을 위해 OHLC 데이터를 개별 필드로 분리 저장
        doc_data = {
            "date": date_str,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "value": close_price,  # 기존 코드 하위 호환성 유지용
            "volume": volume,
            "memo": memo_str       # 기존 문자열 압축 정보
        }
        
        doc_ref = collection_ref.document(date_str)
        batch.set(doc_ref, doc_data)
        batch_count += 1
        total_saved += 1

        # Firestore Batch 제한(500개) 안전선 준수 (400개마다 커밋)
        if batch_count >= 400:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    # 남은 데이터 일괄 커밋
    if batch_count > 0:
        batch.commit()

    print(f"🎉 'stock_data' 컬렉션에 총 {total_saved}건 업로드 완료!")

    # ================================================================
    # 🚀 신규 로직: 데이터 수집 완료 후 메타데이터(버전) 증가
    # ================================================================
    if total_saved > 0:
        try:
            meta_ref = db.collection("metadata").document("stock_status")
            # firestore.Increment(1)을 사용하면 기존 버전에 +1을 더함 (문서가 없으면 1로 자동 생성됨)
            meta_ref.set({"version": firestore.Increment(1)}, merge=True)
            print("🔄 [Cache Sync] 메타데이터 버전 업데이트 완료! 백엔드의 SQLite 캐시가 자동으로 무효화 및 갱신됩니다.")
        except Exception as e:
            print(f"⚠️ 메타데이터 버전 업데이트 실패: {e}")

    return total_saved

# 4. CLI 직접 실행 시 진입점
if __name__ == "__main__":
    fetch_and_save_stock_data(period="10y")