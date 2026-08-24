# AI 추론 서버 컨테이너. 내부 통신 전용이라 밖으로 포트를 열지 않습니다
# (infra/docker-compose.yml · infra/nginx 어느 쪽도 8001 을 공개하지 않습니다).
#
# backend/Dockerfile 과 베이스 이미지를 맞춥니다 — 두 서버가 같은 파이썬
# 버전이어야 "서버마다 결과가 다르다" 같은 원인을 배제할 수 있습니다.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# main.py 는 backend/.env 를 파일로 읽으려 시도합니다(로컬 개발용 경로).
# 컨테이너에는 그 파일이 없지만, main.py 의 load_dotenv 는 파일이 없으면
# 조용히 넘어가고 os.getenv 로 폴백합니다 — compose 의 environment: 로 준
# DATABASE_URL 이 그대로 쓰입니다. 별도 조치가 필요 없습니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
