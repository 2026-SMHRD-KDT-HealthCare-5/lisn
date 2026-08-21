# 개발환경 세팅 가이드

> 귀기울임(LISN) 팀 전원용. **역할 구분 없이 모두 같은 환경**으로 맞춥니다.
> **최종 갱신** 2026.08.03 — 실제로 막혔던 지점(psql PATH · psql 인코딩 · 시스템
> 이미지 없음 · **로그인할 계정이 없음**)을 각 단계에 넣었습니다.
>
> 처음 하시는 분 기준으로 썼습니다. **위에서부터 순서대로** 따라오시면 됩니다.
> 앞 단계를 건너뛰면 뒤 단계가 안 됩니다.

**전체 3~4시간** 정도 걸립니다. Android Studio 와 Flutter 가 제일 오래 걸려요.

> 막히면 혼자 붙잡고 있지 마시고 **에러 화면을 그대로 캡처해서 단톡방에** 올려주세요.
> 아래 「막혔을 때」에 자주 나오는 것들을 모아뒀습니다.

---

## 진행 체크리스트

**1단계 · 프로그램 설치**

- [ ] 1. Git
- [ ] 2. Python 3.12
- [ ] 3. Node.js
- [ ] 4. Android Studio
- [ ] 5. Flutter
- [ ] 6. PostgreSQL
- [ ] 7. DBeaver

**2단계 · 프로젝트 준비**

- [ ] 8. 저장소 받기
- [ ] 9. 파이썬 가상환경 만들기
- [ ] 10. 의존성 설치
- [ ] 11. DB 연결 설정

**3단계 · 실행**

- [ ] 12. 에뮬레이터 만들기
- [ ] 13. 전체 실행해보기
- [ ] 14. 로그인할 계정 만들기 ← **빠뜨리면 앱에서 아무것도 못 합니다**

---

# ⚠ 시작 전에 — 폴더 위치부터 정하세요

프로젝트를 **`C:\LISN`** 에 두시길 권합니다.

> ### 경로에 한글이나 띄어쓰기가 있으면 안 됩니다
>
> 바탕화면(`C:\Users\...\바탕 화면\`)이나 내 문서에 두면 **실제로 깨집니다.**
>
> | 증상 | 원인 |
> |---|---|
> | `flutter analyze` 가 그냥 죽음 (`exit 255`) | 분석 서버가 한글 경로에서 메시지를 잘라먹습니다 |
> | 안드로이드 빌드 실패 | AGP 가 한글 경로를 막습니다 |
>
> 실제로 겪어서 `C:\LISN` 으로 옮겼습니다. **한글 경로로 되돌리지 마세요.**

OneDrive 동기화 폴더 안도 피하세요. 파일 잠금 문제가 생깁니다.

---

# 1단계 · 프로그램 설치

## 1. Git

https://git-scm.com/download/win

"Click here to download" 눌러 받고, 설치 창은 계속 **Next** 로 기본값 그대로 두시면 됩니다.

---

## 2. Python 3.12

> **왜 3.12 인가요**
> 팀원 간 재현성을 위해 버전을 고정합니다. 다른 버전도 설치는 되지만 의존성 결과가
> 달라질 수 있어 프로젝트 환경에는 섞지 않습니다.

### 먼저 — 아나콘다가 있는지 확인하세요

윈도우 키를 누르고 <kbd>anaconda</kbd> 라고 검색해보세요.

| 검색 결과 | 방법 |
|---|---|
| **`Anaconda PowerShell Prompt`** 가 보인다 | **방법 A** |
| 아무것도 안 나온다 | **방법 B** |

### 방법 A · 아나콘다가 있는 경우

python.org 에서 따로 받을 필요가 없습니다.

**① 터미널 열기** — 윈도우 키 → <kbd>Anaconda PowerShell Prompt</kbd>

> **일반 PowerShell 이 아니라 이걸 쓰세요.** 일반 PowerShell 에서는 `conda` 명령이 안 됩니다.

**② 3.12 환경 만들기**

```
conda create -n lisn python=3.12 -y
```

**③ 활성화**

```
conda activate lisn
```

프롬프트 맨 앞에 **`(lisn)`** 이 붙으면 성공입니다.

> **이 환경은 9번에서 딱 한 번만 씁니다.** 프로젝트는 저장소 안에 별도 가상환경
> (`.venv`)을 만들어 쓰기 때문에, **이후로는 `conda activate` 를 할 필요가 없습니다.**

### 방법 B · 아나콘다가 없는 경우

https://www.python.org/downloads/

> ### ⚠ 여기서 제일 많이 실수합니다
> 설치 첫 화면 **맨 아래 `Add python.exe to PATH` 를 반드시 체크**하고 Install 을 누르세요.
> 놓치면 나중에 `python` 명령을 못 찾아 **처음부터 다시 설치**해야 합니다.

> ### ⚠ 페이지 맨 위 노란 버튼을 누르지 마세요
> 그건 최신 버전입니다. **`Python 3.12.10`** 을 받으세요.
>
> 1. 아래로 스크롤 → **`Looking for a specific release?`** 표
> 2. 왼쪽 파란 링크 **`Python 3.12.10`** 클릭 (옆의 Download 버튼 말고)
> 3. 열린 페이지 **맨 아래** `Files` 표
> 4. **`Windows installer (64-bit)`** 클릭

### 확인 — 건너뛰지 마세요

```
python --version
```

`Python 3.12.x` 가 나와야 합니다.

| 다른 게 나오면 | 할 일 |
|---|---|
| `3.13`·`3.11` 등 다른 버전 | 방법 A 면 `conda activate lisn` 을 안 하신 겁니다 |
| **마이크로소프트 스토어**가 열림 | 실제로는 설치가 안 된 상태입니다. 방법 B 로 다시 설치 |
| `python 을 찾을 수 없습니다` | `Add python.exe to PATH` 를 체크 안 하신 겁니다. 다시 설치 |

---

## 3. Node.js

https://nodejs.org/

왼쪽 **LTS** 버전으로 받고 계속 Next 기본값으로 설치.

관리자 관제 웹(React)을 돌리는 데 씁니다.

---

## 4. Android Studio

https://developer.android.com/studio

설치 후 처음 실행하면 SDK 다운로드 화면이 뜹니다. **Standard** 를 선택하고 계속
진행하세요. 용량이 커서 시간이 걸립니다.

> 앱은 Android 전용입니다. Health Connect 가 Android 전용 API 라서 iOS 는 범위 밖입니다.

---

## 5. Flutter

**팀 구글드라이브의 압축파일**을 쓰세요. 공식 사이트에서 받지 않으셔도 됩니다.

[구글드라이브 공유 폴더](https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW)

### 5-1. 압축 풀기

**`C:\src\flutter`** 에 풀어주세요. `C:\src\flutter\bin` 폴더가 보이면 정상입니다.

> ### ⚠ 위치를 꼭 지켜주세요
> - `C:\Program Files` 밑은 **권한 때문에 안 됩니다**
> - 경로에 **한글·띄어쓰기가 있으면 안 됩니다** → 바탕화면 ✗, 내 문서 ✗

### 5-2. PATH 등록

1. 윈도우 키 → **`환경 변수`** 검색
2. **시스템 환경 변수 편집** 클릭
3. 오른쪽 아래 **[환경 변수]**
4. 아래쪽 **시스템 변수** 목록에서 **`Path`** → **[편집]**
5. **[새로 만들기]** → `C:\src\flutter\bin` 입력
6. **[확인]** 을 창마다 눌러 전부 닫기

### 5-3. 확인

터미널을 **완전히 닫고 새로 연 뒤**:

```
flutter doctor
```

`[√]` 표시면 정상입니다. `[X]`·`[!]` 가 있으면 그 화면을 캡처해 올려주세요.

> **「flutter 를 찾을 수 없습니다」** → 터미널을 새로 여세요. PATH 는 새 터미널부터 적용됩니다.

---

## 6. PostgreSQL

https://www.postgresql.org/download/windows/

"Download the installer" → **17** 버전. 팀 전원 같은 버전으로 맞춥니다.

설치 중 비밀번호 입력 화면이 나오면 정하고 **메모해두세요.** 포트는 기본값 `5432` 그대로.

### 설치가 끝나면 `Stack Builder` 창이 뜹니다 → **Cancel**

> ### ⚠ 아무것도 체크하지 말고 취소하세요
> 특히 **`Database Server` 아래 다른 버전(v14·v15·v16·v18)을 절대 체크하지 마세요.**
> 서버가 여러 개 깔려 포트가 충돌하고, 어느 쪽에 연결됐는지 헷갈려 원인 찾기가 어려워집니다.

### PATH 등록 — 이 단계를 꼭 하세요

> **PostgreSQL 설치 프로그램은 `bin` 폴더를 PATH 에 자동 등록하지 않습니다.**
> 그래서 설치를 마쳐도 `psql` 이 「찾을 수 없습니다」로 나옵니다. **고장이 아닙니다.**

5-2 와 같은 방법으로 `C:\Program Files\PostgreSQL\17\bin` 을 추가하세요.

```
psql --version
```

`psql (PostgreSQL) 17.x` 가 나오면 정상입니다.

---

## 7. DBeaver

https://dbeaver.io/download/

**Community Edition - Windows (installer)** 받아서 설치. DB 를 눈으로 보는 도구입니다.

---

# 2단계 · 프로젝트 준비

## 8. 저장소 받기

### 8-1. 폴더에서 PowerShell 열기

1. 파일 탐색기로 **`C:\`** 를 엽니다
2. 위쪽 **주소창**을 클릭
3. 글자를 지우고 **`powershell`** 이라고 입력한 뒤 엔터

검은 창이 그 위치에서 열립니다.

### 8-2. 내려받기

```
git clone https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn.git LISN
```

`C:\LISN` 폴더가 생기면 성공입니다.

```
cd C:\LISN
```

### 8-3. 설치 상태 점검

```
.\tools\check-env.ps1
```

무엇이 설치됐는지 표로 나옵니다.

| 표시 | 뜻 |
|---|---|
| `O` | 정상 |
| `X` | 없음 |
| `!` | 명령은 있는데 실행이 안 됨 (대개 설치가 덜 된 경우) |

> **「이 시스템에서 스크립트를 실행할 수 없습니다」** 라는 빨간 글씨가 뜨면 아래를 먼저
> 실행하고 다시 시도하세요.
>
> ```
> Set-ExecutionPolicy -Scope Process Bypass
> ```

---

## 9. 파이썬 가상환경 만들기

프로젝트 전용 파이썬 환경을 **저장소 안에** 만듭니다.

> **왜 따로 만드나요**
> 다른 수업·과제의 파이썬 환경을 건드리지 않기 위해서입니다. 그리고 실행 스크립트가
> 이 `.venv` 를 직접 부르기 때문에, 만들어두면 **매번 환경을 활성화할 필요가 없습니다.**

**아나콘다를 쓰신 분(방법 A)** 은 `Anaconda PowerShell Prompt` 에서 `conda activate lisn`
을 먼저 하고 아래를 실행하세요. **이 한 번만 필요합니다.**

```powershell
cd C:\LISN
```

```powershell
python -m venv .venv
```

`C:\LISN\.venv` 폴더가 생기면 성공입니다.

---

## 10. 의존성 설치

### 10-1. 파이썬

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

> **`torch`·`lightgbm` 은 설치하지 않습니다.** 이번 과제에서는 AI 모델을 학습하지 않기로
> 확정했습니다(근거는 [`ai/README.md`](../ai/README.md)). 2GB 짜리 다운로드를 받을 필요가
> 없습니다.
>
> 전처리 스크립트를 직접 돌릴 분만 추가로 설치하세요.
> ```powershell
> .\.venv\Scripts\python.exe -m pip install pandas numpy scikit-learn
> ```

### 10-2. Flutter

```powershell
cd frontend\app
```

```powershell
flutter pub get
```

```powershell
cd ..\..
```

#### ⚠ `google-services.json` 은 저장소에 없습니다 — 각자 받으세요

FCM 푸시 설정 파일입니다. **이 저장소는 공개**라 `.gitignore` 로 막아뒀습니다.

1. [Firebase 콘솔](https://console.firebase.google.com) → 프로젝트 **`lisn-952c8`**
   ⚠ 예전엔 `lisn-be2e8` 로 적혀 있었습니다. **2026.08.21 에 실제 프로젝트
   ID 로 정정**했습니다 — 콘솔에서 프로젝트 이름이 아니라 **프로젝트 ID**
   (설정 톱니바퀴 → 일반 탭 상단)로 확인하세요.
2. 프로젝트 설정 → 내 앱 → Android 앱 **`com.lisn.maeume`**
3. `google-services.json` 내려받기
4. **`frontend/app/android/app/`** 에 넣기

**콘솔 접근에 2단계 인증이 필수입니다.** 구글 계정 전체에 적용되는 설정이니
백업 코드를 꼭 따로 저장하세요.

> **없어도 앱은 뜹니다.** 푸시만 죽고 나머지는 전부 정상입니다. 로그에
> 이렇게 찍히면 그 상태입니다 — 고장이 아닙니다.

#### ⚠ 서버 발송용 키도 따로 필요합니다 — `backend/firebase-service-account.json`

**위 `google-services.json` 과는 다른 파일입니다.** 그건 앱이 토큰을
받는 데 쓰고, 이건 **서버가 그 토큰으로 실제 푸시를 쏘는 데** 씁니다
(2026.08.21, `services/push.py` · 구현_갭 갭 1 해소).

1. Firebase 콘솔 → 프로젝트 **`lisn-952c8`** → 톱니바퀴 → **프로젝트 설정**
2. 상단 탭 **서비스 계정(Service accounts)**
3. **새 비공개 키 생성(Generate new private key)**
4. 받은 JSON 파일을 **`backend/firebase-service-account.json`** 이름으로 저장

⚠ **이 파일은 `google-services.json` 보다 훨씬 민감합니다.** 클라이언트 키가
아니라 프로젝트에 서버 권한으로 접근하는 비공개 키입니다. `.gitignore` 가
`backend/firebase-service-account*.json` · `**/firebase-adminsdk*.json` 을
막아두지만, 절대 채팅·이슈·PR 설명에 내용을 붙여넣지 마세요.

**없어도 서버는 뜹니다.** 선제 접촉(`MLCM_220`)은 세션을 그대로 선생성하고,
발송만 `OUTREACH_LOGS.skip_reason = 'fcm_토큰_없음'`(토큰 자체가 없을 때)
또는 `'fcm_발송_실패'`(키가 없거나 잘못됐을 때)로 남습니다.
>
> ```
> [푸시] Firebase 초기화 실패 — 푸시 없이 계속합니다: ...
> ```
>
> 다만 **`flutter build apk` 는 실패합니다.** `google-services` Gradle
> 플러그인이 파일을 못 찾으면 빌드를 멈춥니다. 빌드까지 하려면 받으세요.

### 10-3. 관리자 웹

```powershell
cd frontend\admin
```

```powershell
npm install
```

```powershell
cd ..\..
```

---

## 11. DB 연결 설정

### 11-1. `.env` 만들기

```powershell
Copy-Item backend\.env.example backend\.env
```

`backend\.env` 를 메모장으로 열어 아래를 채웁니다.

| 키 | 값 |
|---|---|
| `DATABASE_URL` | 아래 11-2 참고 |
| `JWT_SECRET` | 아무 긴 문자열 |
| `ENCRYPTION_KEY` | 아래 명령으로 생성 |

```powershell
.\.venv\Scripts\python.exe -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
```

> **`.env` 는 절대 커밋하지 마세요.** 공개 저장소라 올리는 순간 누구나 볼 수 있고,
> 지워도 커밋 기록에 남습니다. `.gitignore` 에 들어 있어 자동으로 막히지만,
> 강제로 `git add` 하면 들어갑니다.
>
> **LLM 키(`GEMINI_API_KEY`)는 팀장이 개인적으로 전달합니다.** 단톡방에 올리지 마세요.

### 11-2. 어느 DB 에 붙나요

**두 가지가 있고, 상황에 따라 씁니다.**

| | 캠퍼스 공용 DB | 내 PC 로컬 DB |
|---|---|---|
| 언제 | **기본값 — 평소 개발·통합 테스트** | **시연·영상 촬영 전용** |
| 스키마 | PM 이 이미 넣어뒀습니다 | 직접 넣어야 합니다 |
| 접속 정보 | 단톡방 공지 · Notion | `localhost:5432` |

> ### 시연은 로컬로 합니다 (2026.08.04 확정)
>
> 시연 영상 촬영에서 로컬로 동작을 확인했고, **8/28 최종 발표도 로컬로 갑니다.**
> 이유가 셋입니다.
>
> - **성능 예산에 여유가 없습니다.** `NFR-DV-001` 이 2899ms / 3000ms 로
>   **101ms** 남습니다. 한 요청에 DB 왕복이 여러 번이라 원격이면 통과로
>   보고한 요건이 시연 중에 깨질 수 있습니다
> - **발표장 망을 신뢰할 수 없습니다.** 공용 DB 는 포트가 기본값이 아니라
>   방화벽에 막히기 쉽고, 끊기면 시연이 멈춥니다
> - **남이 건드릴 수 있습니다.** `schema.sql` 에 `IF NOT EXISTS` 가 없어
>   시연 중 누가 다시 돌리면 충돌합니다
>
> 평소 개발이 공용 DB 인 것은 그대로입니다. **목적이 다릅니다** — 공용은
> 「4명이 같은 스키마를 보는 것」, 시연은 「그 순간 확실히 도는 것」입니다.
>
> ⚠ **시연 1주 전에 로컬로 통째로 리허설하세요.** 당일 처음 로컬로 돌리면
> 「DB 없음」·「시드 안 들어감」·「인코딩 깨짐」이 그때 나옵니다.

#### 공용 DB 로 붙기 — **기본값입니다** (2026.08.05 재확인)

접속 정보를 `DATABASE_URL` 에 넣으면 끝입니다.

```
DATABASE_URL=postgresql+asyncpg://아이디:비밀번호@주소:포트/DB이름
```

> ### ⚠ 포트가 기본값 `5432` 가 아닙니다
> 접속 실패 문의의 대부분이 여기서 나옵니다. 공지의 포트로 바꾸세요.

> ### ⚠ `db/schema.sql` 을 실행하지 마세요
> **PM 이 한 번만 실행합니다.** 각자 실행하면 「테이블이 이미 있다」고 충돌합니다.

> ### ⚠ 시드 스크립트를 공용 DB 에 넣지 마세요
> `seed_demo_persona.sql`·`cleanup_test_accounts.sql` 은 **로컬 전용**입니다.
> 공용에 넣으면 **팀 전원 화면에 데모 데이터가 나타나거나 남의 계정이 지워집니다.**

#### 로컬 DB 로 붙기 — **시연 준비 때만** (2026.08.05)

혼자 실험하거나 데모 데이터를 넣어보고 싶을 때 씁니다.

**아래 블록을 통째로** 붙여넣으세요. 한 줄씩 나눠 실행하면 `$psql` 과
`PGCLIENTENCODING` 이 이어지지 않습니다.

```powershell
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
$env:PGCLIENTENCODING = 'UTF8'
& $psql -U postgres -c "CREATE DATABASE lisn;"
& $psql -U postgres -d lisn -f db\schema.sql
& $psql -U postgres -d lisn -f db\seed_healing_contents.sql
& $psql -U postgres -d lisn -f db\seed_demo_persona.sql
```

> ### ⚠ 여기서 세 번 막힙니다. 셋 다 위 블록이 이미 피해 갑니다
>
> **① `psql` 을 인식할 수 없습니다** — 6번의 PATH 등록을 안 했거나, 등록하고
> 터미널을 새로 안 연 것입니다. 전체 경로로 부르면 PATH 와 무관하게 됩니다.
>
> **② `0xe2 0x80 바이트로 조합된 문자(인코딩: "UHC")…`** — 한글 Windows 콘솔은
> 코드페이지가 949 라 psql 이 `client_encoding=UHC` 로 붙습니다. `db/*.sql` 은
> UTF-8 이고 주석에 `—`·`·`·`⚠` 가 들어 있어 변환하다 깨집니다.
> `$env:PGCLIENTENCODING = 'UTF8'` 이 이걸 막습니다.
> **이 오류가 나면 그 뒤가 통째로 안 들어갑니다.** 처음부터 다시 실행하세요.
>
> **③ `"users" 이름의 릴레이션이 없습니다`** — 시드를 `schema.sql` 보다 먼저
> 실행한 것입니다. 위 순서를 지키면 나지 않습니다.

```
DATABASE_URL=postgresql+asyncpg://postgres:설치할때정한비밀번호@localhost:5432/lisn
```

> 비밀번호에 `@` `:` `/` `#` 이 있으면 URL 인코딩이 필요합니다. `@` → `%40`

넣은 것이 무엇인지:

| 파일 | 없으면 |
|---|---|
| `schema.sql` | 아무것도 안 됩니다. 8개 테이블 + `EMOTIONS` 9종 |
| `seed_healing_contents.sql` | `CAUTION` 액션의 콘텐츠 추천이 빕니다 |
| `seed_demo_persona.sql` | 홈·리포트·관제 화면이 전부 빕니다 |

> 데모 페르소나는 14일치 라이프로그와 판정이 들어 있어 홈·리포트·관제 화면이 비지 않습니다.
> **날짜가 바뀌면 다시 실행하세요** — 오늘 데이터가 「어제」가 되어 홈이 비어 보입니다.

### 11-3. DBeaver 로 확인 (선택)

1. DBeaver 실행 → 왼쪽 위 **콘센트 모양 아이콘(+)**
2. **PostgreSQL** 선택 → **[다음]**
3. 접속 정보 입력 (**공용 DB 는 포트를 꼭 바꾸세요**)
4. **[Test Connection]** → 드라이버 받으라는 창이 뜨면 **[Download]**
5. **Connected** 가 나오면 **[완료]**

---

# 3단계 · 실행

## 12. 에뮬레이터 만들기

앱을 띄우려면 안드로이드 화면이 필요합니다.

```powershell
flutter emulators
```

목록에 **`lisn`** 이 있으면 만들 필요 없습니다. 없으면:

```powershell
flutter emulators --create --name lisn
```

켜기 — **40초~1분** 걸립니다.

```powershell
flutter emulators --launch lisn
```

확인:

```powershell
flutter devices
```

`sdk gphone64 x86 64 (mobile) • emulator-5554` 가 보이면 준비된 것입니다.

> **「emulator exited with code 1」** 이 나오면 **이미 켜져 있는 것**입니다.
> `flutter devices` 로 확인해보세요.

### ⚠ `No suitable Android AVD system images are available`

`flutter emulators --create` 는 **시스템 이미지를 받아주지 않습니다.** 안드로이드
스튜디오를 Standard 로 설치해도 이미지가 안 깔려 있을 수 있고, 그러면 이 명령은
그냥 실패합니다. 둘 중 하나로 푸세요.

**방법 A · Android Studio 의 Device Manager** — 이쪽이 쉽습니다.
기기를 만들 때 시스템 이미지를 같이 내려받습니다. 잘 모르겠으면 A 로 가세요.

**방법 B · 명령으로**

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
& "$env:LOCALAPPDATA\Android\Sdk\cmdline-tools\latest\bin\sdkmanager.bat" "system-images;android-34;google_apis_playstore;x86_64"
flutter emulators --create --name lisn
```

| 여기서 나는 오류 | 이유 |
|---|---|
| `sdkmanager 를 인식할 수 없습니다` | Android SDK 도구도 PATH 에 없습니다. 위처럼 전체 경로로 부르세요 |
| `JAVA_HOME is not set` | **Flutter 는 Android Studio 의 JDK 를 스스로 찾지만 `sdkmanager`·`avdmanager` 는 `JAVA_HOME` 만 봅니다.** 위 첫 줄이 그걸 채웁니다 |

> `sdkmanager` 가 라이선스 동의를 물어보면 `y` 를 치세요.
> `$env:JAVA_HOME` 은 **그 창에서만** 유지됩니다. 계속 쓰려면 5-2 와 같은 방법으로
> 시스템 환경 변수에 `JAVA_HOME` 을 등록하세요.

### PC 키보드로 타이핑하려면 — 기본은 안 됩니다

`flutter emulators --create` 로 만든 AVD 는 **`hw.keyboard=no`** 가 기본입니다.
그래서 이메일·비밀번호를 **화면 키보드를 하나씩 눌러** 넣어야 합니다. 고장이
아니라 설정입니다.

`%USERPROFILE%\.android\avd\<AVD이름>.avd\config.ini` 에서 한 줄을 바꾸세요.

```powershell
$cfg = "$env:USERPROFILE\.android\avd\lisn.avd\config.ini"
Copy-Item $cfg "$cfg.bak"
(Get-Content $cfg) -replace '^hw\.keyboard=no$','hw.keyboard=yes' | Set-Content $cfg -Encoding ASCII
```

**에뮬레이터를 껐다 켜야 적용됩니다.** 앱과 로그인 세션은 AVD 안에 남아 있어
그대로입니다. 적용됐는지는 이걸로 봅니다 — `keysexposed-qwerty` 가 보여야 합니다.
안 바뀌었으면 `keyshidden-nokeys` 로 나옵니다.

```powershell
adb shell am get-config
```

> **한글은 여전히 화면 키보드로 전환해야 합니다.** 지구본 아이콘을 누르세요.
> PC 의 한/영 키는 에뮬레이터로 넘어가지 않습니다.
>
> PC 에서 복사한 텍스트는 `Ctrl+V` 로 에뮬레이터에 붙여넣을 수 있습니다.

### ⚠ 에뮬레이터에는 Health Connect 가 없습니다

걸음·수면 수집(`MLCM_200`)은 **에뮬레이터에서 데이터가 안 옵니다.** 고장이 아닙니다.
로그에 이렇게 찍히면 정상입니다.

```
I/flutter: [동기화] SyncResult(SyncOutcome.permissionDenied, sent=0, queued=0)
```

앱·화면·다른 기능은 전부 정상 동작합니다. 실제 수집 확인은 **Health Connect 가 있는
안드로이드 실기기**가 필요합니다.

---

## 13. 전체 실행해보기

저장소 루트(`C:\LISN`)에서 **한 줄**이면 됩니다.

```powershell
.\tools\start-dev.ps1
```

백엔드 · AI 추론 서버 · 관리자 웹 · Flutter 앱이 **각각 별도 창**에서 시작됩니다.

| | 주소 |
|---|---|
| 백엔드 API 문서 | http://127.0.0.1:8000/docs |
| AI 추론 서버 | http://127.0.0.1:8001/health |
| 관리자 관제 웹 | http://localhost:5173 |
| 앱 | 에뮬레이터 화면 |

종료는 각 창에서 `Ctrl+C` 를 누른 뒤 창을 닫습니다.

**실행하지 않고 준비 상태만 보려면:**

```powershell
.\tools\start-dev.ps1 -Check
```

> VS Code 를 쓰시면 `lisn.code-workspace` 를 열고 `Ctrl+Shift+B` 만 눌러도 같습니다.

> ### ⚠ 관리자 웹은 5173 포트여야 합니다
> 백엔드가 그 주소만 허용합니다. 이전 창이 5173 을 잡고 있으면 새 창이 **5174 로 뜨고
> 요청이 전부 막힙니다.** 400 이 계속 나면 주소창의 포트부터 보세요.

### 13-1. 잘 떴는지는 `/health/db` 로 확인하세요

**브라우저 주소창**에 아래를 넣으세요.

<pre>http://127.0.0.1:8000/health/db</pre>

`{"status":"ok","database":"connected"}` 가 나와야 합니다.

> ### ⚠ 주소를 PowerShell 창에 붙여넣지 마세요
> 「`http://127.0.0.1:8000/health/db` 용어가 cmdlet, 함수, 스크립트 파일 또는
> 실행할 수 있는 프로그램 이름으로 인식되지 않습니다」가 납니다. **고장이 아니라
> 주소는 명령이 아니기 때문입니다.** 이 문서의 주소는 전부 브라우저용입니다.
>
> 터미널에서 확인하고 싶으면 이렇게 씁니다.
>
> ```powershell
> (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/db).Content
> ```
>
> 브라우저를 띄우려면 `start http://127.0.0.1:8000/health/db`

> ### ⚠ `/docs` 로 확인하면 안 됩니다
> Swagger 는 **DB 가 안 붙어도 열립니다.** 그래서 `/docs` 가 떴다고 넘어가면,
> 앱에서 로그인할 때 응답이 10초를 넘겨 **「서버 응답이 지연되고 있습니다」**만
> 뜹니다. 네트워크나 에뮬레이터 문제로 보이지만 아닙니다.

---

## 14. 로그인할 계정 만들기

**여기를 빠뜨리면 앱을 띄워도 아무것도 못 합니다.** 실제로 여기서 오래 막혔습니다.

DB 를 새로 만들면 **계정이 하나도 없습니다.** `docs/진행/작업이력.md` 에 적힌
`admin@lisn.dev` · `user@lisn.dev` 는 **PM PC 의 로컬 DB 에서 손으로 만든 것이고
시드에 들어 있지 않습니다.** 새 PC 에서 그 주소로 로그인하면 당연히 실패합니다.

### 14-1. 일반 사용자

| 방법 | 계정 |
|---|---|
| 앱에서 **회원가입** (권장) | 본인이 정합니다 |
| `seed_demo_persona.sql` 을 넣었다면 | `demo.crisis@lisn-test.example` / `rldnfdla` |

> 데모 계정에는 14일치 라이프로그와 판정이 붙어 있어 홈·리포트가 비지 않습니다.
> 다만 **`role` 이 `USER`** 라 관리자 웹에는 못 들어갑니다.

### 14-2. 관리자 웹에 들어가려면

관리자 웹은 `role='ADMIN'` 인 계정만 세션을 허용합니다. **먼저 앱에서 회원가입**한
뒤, 그 계정을 승격하세요. 승격할 계정이 없으면 아무 일도 일어나지 않습니다.

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d lisn -c "UPDATE users SET role='ADMIN' WHERE email='you@example.com';"
```

> ### ⚠ `you@example.com` 을 가입한 주소로 바꿔서 실행하세요
>
> 자리표시자를 한글로 두고 그대로 실행하면 이 오류가 납니다.
>
> ```
> 오류:  "UTF8" 인코딩에 사용할 수 없는 문자가 있음: 0xba
> ```
>
> PowerShell 이 네이티브 명령에 한글을 CP949 바이트로 넘기는데 psql 은 UTF-8 로
> 읽기 때문입니다. **`-c` 안에는 한글을 넣지 마세요.** 11-2 의 파일 읽기와
> 방향만 반대인 같은 문제입니다.

`UPDATE 1` 이 나오면 성공, `UPDATE 0` 이면 그 주소가 DB 에 없는 것입니다.
계정 목록은 이렇게 봅니다.

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d lisn -c "SELECT email, role FROM users;"
```

> 승격은 API 에 **즉시** 반영됩니다(`require_admin` 이 JWT 가 아니라 DB 의 `role` 을
> 읽습니다). 다만 **관리자 웹은 다시 로그인해야 합니다** — 로그인 응답의 `role` 로
> 세션 저장 여부를 정하기 때문에, 승격 전에 로그인해 뒀다면 세션 자체가 없습니다.

> ### ⚠ `ADMIN` 계정을 시드에 넣지 않은 것은 의도한 것입니다
> 이 저장소는 공개라, 시드에 넣는 순간 관리자 비밀번호가 공개됩니다.
> 각자 자기 계정을 승격해서 쓰세요.

> **공용 DB 를 쓰신다면** 승격 SQL 을 직접 돌리지 마시고 PM 에게 요청하세요.
> 11-2 의 「시드 스크립트를 공용 DB 에 넣지 마세요」와 같은 이유입니다.

---

## 앱의 특정 화면만 보고 싶을 때

로그인부터 눌러 들어가지 않아도 됩니다.

```powershell
C:\LISN\tools\show-screen.ps1 report
```

인자 없이 실행하면 화면 목록이 나옵니다.

```
login  reset  join  home  chat  lifelog  setting  report  emergency
```

> **절대 경로로 적은 것은 의도한 것입니다.** `.\tools\...` 는 저장소 루트에 있을 때만
> 되고, `frontend\app` 안에서 치면 못 찾습니다.

> ⚠ 이 스크립트는 **개발용 자동 로그인**을 씁니다. 제출·시연 빌드를 만들 때는 쓰지
> 마세요. 자세한 내용은 [`frontend/app/README.md`](../frontend/app/README.md).

---

# 마무리 · 확인 부탁

세팅이 끝나면 아래 두 가지를 캡처해서 **단톡방에** 올려주세요.

1. `.\tools\check-env.ps1` 결과
2. `flutter doctor` 결과

---

# 자주 쓰는 명령

| 하고 싶은 것 | 명령 |
|---|---|
| 최신 코드 받기 | `git pull` |
| 전체 실행 | `.\tools\start-dev.ps1` |
| 준비 상태만 확인 | `.\tools\start-dev.ps1 -Check` |
| 설치 상태 점검 | `.\tools\check-env.ps1` |
| 특정 앱 화면 보기 | `C:\LISN\tools\show-screen.ps1 <이름>` |
| 에뮬레이터 켜기 | `flutter emulators --launch lisn` |
| 백엔드 테스트 | `cd backend` 후 `..\.venv\Scripts\python.exe -m pytest -q` |
| 앱 테스트 | `cd frontend\app` 후 `flutter test` |

---

# 막혔을 때

혼자 오래 붙잡지 마세요. 아래는 자주 나오는 것들입니다.

## 설치

| 증상 | 원인과 해결 |
|---|---|
| `python 을 찾을 수 없습니다` | `Add python.exe to PATH` 를 체크 안 하신 겁니다. **다시 설치**하면서 체크 |
| `python` 쳤는데 **스토어**가 열림 | 실제로 설치가 안 된 상태입니다. 2번으로 다시 설치 |
| `flutter 를 찾을 수 없습니다` | 터미널을 **완전히 닫고 새로** 여세요. PATH 는 새 터미널부터 적용됩니다 |
| `psql 을 찾을 수 없습니다` | **정상입니다.** PostgreSQL 은 PATH 를 자동 등록하지 않습니다. 6번의 PATH 등록을 하세요 |
| `conda 를 찾을 수 없습니다` | 일반 PowerShell 을 여신 겁니다. **`Anaconda PowerShell Prompt`** 로 여세요 |
| 스크립트 실행 불가 (빨간 글씨) | `Set-ExecutionPolicy -Scope Process Bypass` 먼저 실행 |
| PostgreSQL 설치 후 `Stack Builder` | 아무것도 체크하지 말고 **Cancel** |
| `sdkmanager 를 인식할 수 없습니다` | Android SDK 도구도 PATH 에 없습니다. 12번의 전체 경로를 쓰세요 |
| `JAVA_HOME is not set` | `sdkmanager`·`avdmanager` 는 `JAVA_HOME` 만 봅니다. 12번 방법 B |
| 에뮬레이터에 **PC 키보드로 타이핑이 안 됨** | AVD 기본값이 `hw.keyboard=no` 입니다. 12번 「PC 키보드로 타이핑하려면」 |

## DB 넣기

| 증상 | 원인과 해결 |
|---|---|
| `0xe2 0x80 바이트로 조합된 문자(인코딩: "UHC")` | 콘솔 코드페이지가 949 라 psql 이 UHC 로 붙었습니다. `$env:PGCLIENTENCODING='UTF8'` 먼저. **그 뒤가 통째로 안 들어가니 처음부터 다시** |
| `"users" 이름의 릴레이션이 없습니다` | 시드를 `schema.sql` 보다 먼저 실행했습니다. 11-2 순서대로 |
| `"lisn" 데이터베이스가 없습니다` | `CREATE DATABASE lisn;` 을 안 했습니다 |
| `"UTF8" 인코딩에 사용할 수 없는 문자가 있음: 0xba` | `-c "..."` 안에 **한글**을 넣으셨습니다. 자리표시자를 실제 값(영문)으로 바꾸세요. 14-2 |
| 오류 메시지가 `?ㅻ쪟` 처럼 깨져 보임 | 콘솔 코드페이지가 949 라 UTF-8 메시지가 깨집니다. 내용만 안 보일 뿐 **동작에는 영향 없습니다.** `chcp 65001` 로 정상화 |

## 실행

| 증상 | 원인과 해결 |
|---|---|
| `No pubspec.yaml file found` | `flutter run` 은 **`frontend\app`** 에서 실행해야 합니다 |
| `.\tools\... 를 인식할 수 없습니다` | 저장소 루트(`C:\LISN`)가 아닌 곳에서 치신 겁니다. 절대 경로를 쓰세요 |
| `http://... 를 인식할 수 없습니다` | **주소는 명령이 아닙니다.** 브라우저 주소창에 넣으세요 (13-1) |
| `ModuleNotFoundError` | 전역 파이썬으로 실행하신 겁니다. **`.\.venv\Scripts\python.exe`** 를 쓰세요 |
| `emulator exited with code 1` | 이미 켜져 있는 것입니다. `flutter devices` 로 확인 |
| 관리자 웹에서 요청이 전부 실패 | 포트가 **5174** 로 떴을 수 있습니다. 남은 창을 닫고 다시 실행 |
| 앱은 뜨는데 데이터가 안 보임 | 백엔드가 안 떠 있거나 시드를 안 넣은 상태입니다 |
| 앱 로그인 — **이메일 또는 비밀번호가 올바르지 않습니다** | 그 계정이 이 PC 의 DB 에 없습니다. **14번** |
| 앱 로그인 — **서버 응답이 지연되고 있습니다** | 둘 중 하나. ① 앱에 박힌 `API_BASE_URL` 이 엉뚱한 주소(아래 참고) ② 백엔드가 DB 에 못 붙음 → `/health/db` |
| 앱 로그인 — **서버에 연결할 수 없습니다** | 연결 자체가 거부됐습니다. 백엔드 창이 살아 있는지 보세요 |
| 홈의 수면·걸음이 전부 `-` | 데모 시드가 하루 지났습니다. `seed_demo_persona.sql` 을 다시 실행 |
| DB 연결 오류 | **PostgreSQL 로그를 먼저** 보세요 — `C:\Program Files\PostgreSQL\17\data\log\` |
| DBeaver 접속 실패 | **포트 번호**를 먼저 확인하세요. 공용 DB 는 5432 가 아닙니다 |

> ### 관리자 웹은 되는데 앱만 안 되면 — 앱에 박힌 주소를 보세요
>
> 관리자 웹은 브라우저에서 `localhost:8000` 을 쓰지만, **앱은 빌드할 때 박힌
> `API_BASE_URL` 을 씁니다.** 실기기용 IP 를 넣어 한 번 구우면 그 설치본은
> 에뮬레이터에서도 계속 그 주소로 나가고, 없는 주소면 10초 뒤
> 「서버 응답이 지연되고 있습니다」만 뜹니다. 2026.08.03 에 여기서 막혔습니다.
>
> 로그인 버튼을 누른 직후 호스트에서 확인하세요. `SYN_SENT` 로 남는 상대 주소가
> **앱에 박힌 주소**입니다.
>
> ```powershell
> netstat -ano | Select-String ":8000"
> ```
>
> 고치려면 `--dart-define` 없이 다시 설치합니다(`frontend\app` 에서 `flutter run`).
> **컴파일 시점 상수라 핫 리로드로는 안 바뀝니다.**

> ### 에뮬레이터가 호스트를 못 봐서 그런 것이 아닙니다
>
> 앱이 서버에 못 붙는 것처럼 보이면 에뮬레이터 네트워크를 의심하기 쉬운데,
> **거기가 아닙니다.** 에뮬레이터의 `10.0.2.2` 는 호스트의 `127.0.0.1` 로
> 이어지므로 백엔드가 `127.0.0.1:8000` 에만 열려 있어도 닿습니다.
>
> 2026.08.03 에 에뮬레이터 Chrome 으로 `http://10.0.2.2:8000/health/db` 를 열어
> `connected` 를 직접 확인했습니다. **여기를 파느라 시간을 쓰지 마세요.**
> 계정(14번)과 `/health/db` 를 먼저 보세요.
>
> 실기기는 다릅니다 — `10.0.2.2` 가 통하지 않아 주소를 **두 곳**에 넣어야 합니다
> (루트 [`README.md`](../README.md) 「실기기에서 …」 항목).

## 관리자 화면

| 증상 | 원인과 해결 |
|---|---|
| 로그인은 되는데 403 | **DB 의 `role` 이 `ADMIN` 이어야** 합니다. 관리자 웹은 승격 후 **재로그인**이 필요합니다 |
| 관제 화면이 텅 비어 있음 | 판정 이력이 없어서입니다. 로컬이면 `seed_demo_persona.sql` 을 넣으세요 |

---

# 링크 모음

| | |
|---|---|
| GitHub | https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn |
| Notion | https://app.notion.com/p/3ab02025254781d18e1ac402a0f59d77 |
| 구글드라이브 | https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW |

**저장소 안에서 더 볼 것**

| 파일 | 용도 |
|---|---|
| [`docs/SESSION-HANDOFF.md`](SESSION-HANDOFF.md) | 현재 진행 상황·남은 일 |
| [`backend/README.md`](../backend/README.md) | 서버 규칙과 함정 |
| [`frontend/app/README.md`](../frontend/app/README.md) | 앱 규칙과 함정 |
| [`frontend/admin/README.md`](../frontend/admin/README.md) | 관리자 웹 규칙과 함정 |
