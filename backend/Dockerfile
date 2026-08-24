# 비즈니스 서버 컨테이너.
#
# CLAUDE.md 가 Python 을 3.12 로 고정하므로 여기도 3.12 를 씁니다 — 로컬
# 개발 환경과 다른 버전으로 배포하면 "로컬에선 되는데 서버에선 안 된다"의
# 원인이 됩니다.
#
# ⚠ .env · firebase-service-account.json 은 여기서 COPY 하지 않습니다.
#   이미지에 시크릿을 구우면 이미지를 어디로 옮기든 그 값이 따라갑니다.
#   둘 다 infra/docker-compose.yml 이 런타임에 마운트합니다
#   (.dockerignore 로 빌드 컨텍스트에서도 원천 제외).
FROM python:3.12-slim

WORKDIR /app

# bcrypt · cryptography 는 대개 manylinux 사전빌드 wheel 이 있어 gcc 가
# 필요 없습니다. 배포 아키텍처가 달라 wheel 이 없으면 아래 줄의 주석을
# 풀고 다시 빌드하세요.
# RUN apt-get update && apt-get install -y --no-install-recommends gcc \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --reload 는 로컬 개발 전용입니다. 배포에서 켜두면 파일 변경 감시가
# 불필요한 리소스를 먹고, 컨테이너 안에서는 어차피 파일이 안 바뀝니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
