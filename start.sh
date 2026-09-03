#!/bin/bash

# 1. api/.env 파일이 존재하는지 확인
if [ ! -f "api/.env" ]; then
    echo "🔍 api/.env 파일이 존재하지 않습니다."
    
    # 2. api/.env_sample 파일이 있는지 확인 후 복사
    if [ -f "api/.env_sample" ]; then
        cp api/.env_sample api/.env
        echo "📋 .env_sample을 복사하여 api/.env 파일을 자동 생성했습니다!"
        echo "⚠️  주의: 생성된 api/.env 파일에 본인의 실제 API 키(OPENAI_API_KEY 등)를 입력한 뒤 다시 실행해주세요."
        exit 1
    else
        echo "❌ 오류: 복사할 api/.env_sample 파일이 존재하지 않습니다."
        exit 1
    fi
else
    echo "✅ api/.env 파일이 확인되었습니다."
fi

# 3. Docker Compose 빌드 및 실행
echo "🚀 Docker 컨테이너를 빌드하고 실행합니다..."
docker compose -f docker/docker-compose.yml up --build -d