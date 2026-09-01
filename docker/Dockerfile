# FastAPI 구동을 위한 Python 공식 경량 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 업데이트 및 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 설치 (yfinance 등 분석 도구 포함)
# 실제 환경에 맞게 필요한 패키지를 나열합니다.
RUN pip install --no-cache-dir fastapi uvicorn firebase-admin python-dotenv pydantic pandas yfinance

# 컨테이너 내 포트 노출 (사용자 요청: 8090)
EXPOSE 8090

# FastAPI 실행 명령어
# src/lib/main.py 파일 내에 app 객체가 있다고 가정합니다.
# uvicorn이 8090 포트로 모든 IP(0.0.0.0)에서 접속 가능하도록 실행합니다.
CMD ["uvicorn", "src.lib.main:app", "--host", "0.0.0.0", "--port", "8090", "--reload"]