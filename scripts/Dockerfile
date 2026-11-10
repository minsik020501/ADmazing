# font-prep 서비스용 이미지 (scripts/prepare_fonts.py 실행 환경)
# 스크립트와 manifest는 docker-compose.yml에서 마운트한다
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
