# infra — 배포

귀기울임을 NCP(네이버클라우드플랫폼) VM 1대에 Docker Compose 로 올립니다.
"왜 이 구성인가"는 [`docs/결정/배포_아키텍처.md`](../docs/결정/배포_아키텍처.md)
에 있습니다. 여기는 "어떻게"만 다룹니다.

> **처음 하신다는 전제로 씁니다.** 콘솔 화면 이름은 NCP 업데이트로 바뀔 수
> 있으니, 아래 "무엇을 찾는지"를 기준으로 비슷한 메뉴를 찾으세요.

---

## 0. 시작 전에 준비할 것

로컬(이 PC)에 이미 있는 것:
- `backend/.env` — 채워진 상태(로컬 개발용 값 그대로 두면 됩니다. 배포용으로
  바뀌어야 하는 값은 compose 가 덮어씁니다 — 3절 참고)
- `backend/firebase-service-account.json` — FCM 발송용 키(8/21 에 이미 검증된 것)
- Node.js — 관리자 웹 빌드용 (`node --version` 으로 확인, 이 PC 는 v24.14.1)

없으면 시작할 수 없는 것 — 미리 확인하세요:
- NCP 계정에 **크레딧이 실제로 잡혀 있는지** — 마이페이지 → 결제 관리 →
  크레딧 조회. 크레딧 종류(교육용 등)에 따라 **사용 가능한 상품이 제한**될
  수 있습니다. 이 문서의 Compute Server 가 그 크레딧으로 결제되는 상품인지
  콘솔에서 확인하세요.

---

## 1. NCP 콘솔 — 확인·설정할 것 (자세히)

### 1-1. 프로젝트 환경: VPC

NCP 는 **Classic**과 **VPC** 두 환경이 있습니다(콘솔 좌측 상단에서 전환).
**VPC 를 쓰세요** — 서브넷·ACG(보안그룹)를 세분화할 수 있어 "내부 DB 포트는
막고 443만 연다"가 명확해집니다. 계정에 VPC 환경이 없으면 콘솔에서
"VPC 시작하기" 같은 안내가 뜹니다.

### 1-2. VPC·Subnet 생성

- **VPC** 하나 생성 (예: `lisn-vpc`, CIDR `10.0.0.0/16` 기본값 그대로 둬도 됩니다)
- **Subnet** 하나 생성 — **Public** 으로 만드세요(서버가 공인 IP 를 받으려면
  Public Subnet 이어야 합니다). Internet Gateway 는 VPC 생성 시 자동으로
  붙습니다.

### 1-3. ACG (Access Control Group) — NCP 의 보안그룹

Server → ACG 메뉴에서 새로 만들거나 기본 ACG 를 수정합니다. **인바운드
규칙**을 이렇게 두세요:

| 프로토콜 | 포트 | 접근 소스 | 용도 |
|---|---|---|---|
| TCP | 22 | 내 IP 만 (`내ip/32`) | SSH — **0.0.0.0/0 으로 열지 마세요** |
| TCP | 80 | 0.0.0.0/0 | HTTP (인증서 발급·리다이렉트용) |
| TCP | 443 | 0.0.0.0/0 | HTTPS — 앱·관리자 웹이 실제로 쓰는 포트 |

⚠ **8000·8001·5432 는 어떤 규칙도 추가하지 마세요.** backend·ai-server·
postgres 는 컨테이너 내부 네트워크로만 통신합니다(docker-compose.yml 에
`ports:` 를 안 준 이유). ACG 에 아예 없으면 외부에서 원천적으로 접근이
안 됩니다 — 이게 `NFR-DE-002` "전송 구간 보호"를 인프라 레벨에서 한 번 더
보장합니다.

내 IP 확인: 브라우저에서 `내 ip 확인` 검색하면 나옵니다. 집·학교를 오가면
IP 가 바뀌니, SSH 규칙은 필요할 때마다 갱신하거나 처음엔 넉넉히
(예: 학교 공인 IP 대역)로 잡아두세요.

### 1-4. Server(Compute) 생성

Server → 서버 생성:

- **서버 이미지**: Ubuntu Server 22.04 (또는 24.04)
- **서버 타입**: Standard, **최소 vCPU 2 / RAM 4GB**
  (postgres + backend + ai-server + nginx 4개 컨테이너가 동시에 뜹니다.
  2GB 는 빡빡합니다 — 빌드 중 OOM 으로 죽는 사례가 흔합니다)
- **스토리지**: 기본 50GB 로 충분. **암호화 옵션이 있으면 켜세요** —
  `NFR-DE-002` (2) "클라우드 환경에 배포하는 경우 데이터베이스 볼륨의
  디스크 암호화 옵션을 활성화한다"를 문서 그대로 만족시키는 지점입니다
- **인증키**: 신규 생성 → **.pem 파일을 다운로드받고 안전한 곳에 보관**
  (재발급 안 됩니다. 잃어버리면 서버 재생성해야 할 수 있습니다).
  절대 이 저장소 안에 두지 마세요 — `.gitignore` 가 `*.pem` 을 막아주긴
  하지만, 애초에 저장소 폴더 밖(예: 이 PC 의 `~/.ssh/`)에 두는 습관이 낫습니다
- **공인 IP**: "신규 할당"을 체크하세요 — 이게 없으면 SSH 도, 앱도 서버에
  못 닿습니다
- **네트워크**: 위에서 만든 VPC·Public Subnet·ACG 선택

생성 후 콘솔에 뜨는 **공인 IP 를 적어두세요** — 앞으로 계속 씁니다
(아래 `<공인IP>` 자리).

### 1-5. SSH 접속 확인

```bash
chmod 600 다운받은키.pem
ssh -i 다운받은키.pem ubuntu@<공인IP>
```

(계정명이 `ubuntu` 가 아니라 `root` 인 이미지도 있습니다 — 콘솔의 서버 상세
정보에 "접속 계정"이 적혀 있습니다.)

접속이 안 되면 대부분 ACG 의 22번 규칙이거나, Public Subnet 이 아니거나,
공인 IP 미할당입니다 — 1-3·1-2·1-4 순서로 되짚어 보세요.

### 1-6. 도메인 — 새로 안 사도 됩니다

Let's Encrypt 인증서는 **실제로 해석되는 도메인**만 있으면 됩니다. 공인 IP
가 `203.0.113.1` 이라면:

```
203-0-113-1.nip.io
```

이 그대로 그 IP 로 해석되는 공개 도메인입니다(nip.io 서비스가 IP 를 도메인
안에 인코딩해서 응답하는 방식이라 별도 등록이 필요 없습니다). 비용 0원,
설정 0분 — 4일짜리 일정엔 이쪽을 권합니다. 나중에 정식 도메인을 사면
NCP Global DNS 에서 A 레코드만 이 IP 로 바꿔주면 됩니다.

---

## 2. 서버 안에서 — Docker 설치

SSH 로 접속한 상태에서:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 여기서 한 번 로그아웃 후 재접속해야 docker 명령에 sudo 가 안 붙습니다
exit
```

다시 접속해서 확인:

```bash
ssh -i 다운받은키.pem ubuntu@<공인IP>
docker --version
docker compose version
```

---

## 3. 저장소·시크릿을 서버로

### 3-1. 코드

```bash
git clone https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn.git
cd lisn/infra
```

### 3-2. compose 변수

```bash
cp .env.example .env
nano .env   # POSTGRES_PASSWORD 를 채웁니다
```

### 3-3. 백엔드 시크릿 (로컬 PC 에서 서버로 올림)

이 PC(Windows)에서 PowerShell로:

```powershell
scp -i C:\경로\다운받은키.pem backend\.env ubuntu@<공인IP>:~/lisn/backend/.env
scp -i C:\경로\다운받은키.pem backend\firebase-service-account.json ubuntu@<공인IP>:~/lisn/backend/firebase-service-account.json
```

⚠ **이 두 파일이 서버에 없으면 `docker compose up` 이 이상하게 실패합니다.**
Docker 는 마운트하려는 파일이 없으면 그 자리에 빈 **디렉터리**를 만들어
버립니다 — `firebase-service-account.json`이 파일이 아니라 폴더가 돼서
`firebase_admin`이 JSON 파싱 에러를 던집니다. 반드시 compose 를 올리기
**전에** scp 를 끝내세요.

### 3-4. backend/.env 에서 배포용으로 바꿀 값

로컬 개발용 `.env` 를 그대로 올렸다면, 서버 쪽에서 이 두 개만 SSH 로
`nano ~/lisn/backend/.env` 로 고치세요(`DATABASE_URL`·`AI_SERVER_URL` 은
docker-compose.yml 이 자동으로 덮어쓰므로 안 건드려도 됩니다):

```
LLM_PROVIDER=openai      # 시연·정확도 검사는 OpenAI 가 정본(CLAUDE.md)
OPENAI_API_KEY=<실제 키>
```

`PASSWORD_RESET_LOG_TOKEN` 은 `false` 그대로 두세요 — 켜두면 로그를 보는
사람이 누구 계정이든 비밀번호를 바꿀 수 있습니다.

`CORS_ORIGINS` 는 **안 건드려도 됩니다.** 관리자 웹을 같은 nginx 가 같은
도메인에서 정적으로 서빙하므로(4절), 브라우저 입장에서는 같은 출처(same
origin) 라 CORS 자체가 적용되지 않습니다.

---

## 4. 관리자 웹 빌드 — 로컬(이 PC)에서

nginx 가 컨테이너 안에서 빌드하지 않습니다. **이 PC 에서 미리 빌드해서
서버로 올립니다.**

```powershell
cd frontend\admin
$env:VITE_API_BASE_URL = "https://<도메인>/api/v1"
npm run build
scp -i C:\경로\다운받은키.pem -r dist ubuntu@<공인IP>:~/lisn/frontend/admin/dist
```

`<도메인>` 은 1-6 에서 정한 `203-0-113-1.nip.io` 형태(또는 실제 도메인)입니다.

---

## ⚠ `docker compose config` 를 함부로 돌리지 마세요

문법을 확인하려고 `docker compose config` 를 실행하면, `env_file` 로 지정한
`backend/.env` 의 **실제 값(API 키·JWT_SECRET·ENCRYPTION_KEY 등)을 그대로
평문으로 출력**합니다. 터미널 로그·화면 공유·캡처 어디에든 남으면 그 순간
유출입니다. 실제로 2026.08.24 에 이 명령으로 검증하다가 대화 세션 기록에
실키가 남은 적이 있습니다 — 그 키들은 재발급했습니다.

문법만 확인하려면:
```bash
docker compose config --services   # 서비스 이름만 나옵니다. 값은 안 보임
```
정말 전체 구성을 봐야 하면 출력을 화면에 띄우지 말고 파일로만 받아 바로
지우세요:
```bash
docker compose config > /tmp/check.yml && rm /tmp/check.yml   # 확인 후 즉시 삭제
```

## 5. 최초 기동 (HTTP 상태로)

서버에서:

```bash
cd ~/lisn/infra
docker compose up -d --build
docker compose ps        # 4개 컨테이너 모두 Up 인지 확인
docker compose logs backend --tail 50
```

이 시점엔 `infra/nginx/lisn.conf` 가 HTTP 전용 버전이라 `http://<공인IP>/`
로 이미 접속이 됩니다(관리자 웹 화면이 뜨는지 확인). `curl` 로도 확인:

```bash
curl http://<공인IP>/health
```

---

## 6. HTTPS 발급

certbot 을 컨테이너로 한 번만 실행해 인증서를 받습니다. nginx 가 이미 떠
있어야 하고(5절 완료 후), `/.well-known/acme-challenge/` 경로가 응답해야
합니다.

```bash
docker run --rm \
  -v lisn_certbot-etc:/etc/letsencrypt \
  -v lisn_certbot-www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d <도메인> \
  --email <본인이메일> --agree-tos --no-eff-email
```

성공하면 `/etc/letsencrypt/live/<도메인>/` 에 인증서가 생깁니다. 이제
nginx 설정을 HTTPS 버전으로 바꿉니다:

```bash
cd ~/lisn/infra
cp nginx/lisn-ssl.conf.sample nginx/lisn.conf
sed -i "s/__DOMAIN__/<도메인>/g" nginx/lisn.conf
docker compose restart nginx
curl -I https://<도메인>/health
```

**인증서 갱신** — Let's Encrypt 인증서는 90일마다 만료됩니다. crontab 에
한 줄 추가해 두세요:

```bash
crontab -e
# 아래 한 줄 추가 (매주 월요일 03:00)
0 3 * * 1 docker run --rm -v lisn_certbot-etc:/etc/letsencrypt -v lisn_certbot-www:/var/www/certbot certbot/certbot renew --webroot -w /var/www/certbot && docker compose -f ~/lisn/infra/docker-compose.yml restart nginx
```

---

## 7. 검증

⚠ `tools/smoke_mvp.py` 는 **여기 못 씁니다.** `BASE = 'http://127.0.0.1:8000/...'`,
`AI = 'http://127.0.0.1:8001'` 로 주소가 코드에 박혀 있고, 8001(AI 서버)은
설계상 로컬에서만 열립니다(위 「내부 통신 전용」). 이 스크립트는 **로컬
개발 PC 에서 로컬 서버를 대상으로 돌리는 용도**이니 그대로 남겨두고, 아래
방법으로 클라우드를 확인하세요:

- `https://<도메인>/` — 관리자 웹 로그인 화면
- `https://<도메인>/docs` — FastAPI Swagger, 라우터 33개 뜨는지
- `https://<도메인>/health` — `{"status": "ok"}` 류 응답
- 관리자 웹에서 실제 로그인 → 대시보드까지 눈으로 확인 (API 프록시·CORS·
  빌드 세 가지가 한 번에 검증됩니다)

**Flutter 앱을 이 서버로 연결**하려면 release APK 를 다시 빌드합니다:

```powershell
cd frontend\app
flutter build apk --release --dart-define=API_BASE_URL=https://<도메인>
```

HTTPS 라 `network_security_config.xml` 의 `<domain>` 목록을 안 건드려도
됩니다 — 그 파일은 **평문(HTTP) 예외 목록**이라 HTTPS 는 애초에 안 거칩니다
(로컬 실기기 연동 때 IP 를 두 곳에 넣어야 했던 번거로움이 여기선 없습니다).

---

## 8. 운영 팁

**로그 보기**
```bash
docker compose logs -f backend
docker compose logs -f ai-server
```

**재기동(코드 갱신 후)**
```bash
cd ~/lisn/infra
git -C ~/lisn pull
docker compose up -d --build
```

**크레딧 절약** — 발표 전후로만 쓸 거면, 안 쓰는 시간엔 서버를 **정지**
(콘솔의 Server → 서버 정지)하세요. 정지 중엔 컴퓨팅 요금이 안 나갑니다
(스토리지 요금은 별도로 계속 나갈 수 있으니 콘솔에서 요금 체계를 확인하세요).
공인 IP 를 "고정 IP"로 안 걸어두면 정지 후 재시작 시 IP 가 바뀔 수 있으니,
바뀌면 도메인(nip.io)과 앱 빌드도 다시 맞춰야 합니다 — 데모 직전엔 정지하지
않는 걸 권합니다.

**폴백** — 클라우드에 문제가 생기면 CLAUDE.md 의 원래 방식(로컬 PC 에서
`uvicorn` 직접 실행)으로 즉시 되돌릴 수 있습니다. 그러니 **로컬 실행
경로를 발표 직전까지 없애지 마세요.**

---

## 9. 자주 나는 에러

| 증상 | 원인 | 해결 |
|---|---|---|
| `docker compose up` 이 backend 에서 계속 재시작 | `backend/.env` 를 안 올렸거나 `firebase-service-account.json` 이 디렉터리로 잡힘 | 3-3 절 다시, `ls -la ~/lisn/backend/` 로 파일인지 확인 |
| SSH 접속 안 됨 | ACG 22번 규칙 · Public Subnet 미설정 · 공인 IP 미할당 | 1-3 → 1-2 → 1-4 순서로 확인 |
| `502 Bad Gateway` | backend 컨테이너가 아직 안 뜸(postgres healthcheck 대기 중) | `docker compose ps` 로 상태 확인, 30초~1분 기다렸다 재시도 |
| certbot 이 챌린지 실패 | ACG 80번이 안 열렸거나 도메인이 그 IP 로 안 풀림 | `curl http://<도메인>/.well-known/acme-challenge/test` 로 nginx 까지 닿는지 먼저 확인 |
| 관리자 웹은 뜨는데 로그인이 안 됨 | `VITE_API_BASE_URL` 을 안 넣고 빌드함(기본값이 `localhost:8000`으로 굳어버림) | 4절대로 다시 빌드해 `dist/` 를 새로 올림 |
