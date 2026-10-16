FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 실제 모델(IMAGE_GENERATOR=diffusers)을 쓸 때만 설치
ARG INSTALL_ML=false
COPY requirements-ml.txt .
RUN if [ "$INSTALL_ML" = "true" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi

COPY app ./app

EXPOSE 11000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "11000", "--reload"]
