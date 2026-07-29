# 개발환경 세팅 가이드

> 귀기울임(LISN) 팀 전원용. **역할 구분 없이 모두 같은 환경**으로 맞춥니다.
> 처음 하시는 분 기준으로 썼습니다. 위에서부터 순서대로 따라오시면 됩니다.
>
> **전체 3~4시간** 정도 걸립니다. Flutter 가 제일 오래 걸려요.
> 막히면 혼자 붙잡고 있지 마시고 **에러 화면 그대로 캡처해서 단톡방에** 올려주세요.

> ### 📱 체크하면서 따라가는 웹 버전
> https://claude.ai/code/artifact/e4b77109-56a4-41d7-9def-fe98add9ec8c
>
> 진행 상황이 저장되고 명령어 복사 버튼이 있어 **팀원 안내용으로는 이쪽이 편합니다.**
> 폰에서도 읽히니 설치는 PC, 가이드는 폰으로 보셔도 됩니다.

> ### ✏️ 내용을 고칠 때
> **이 파일(`docs/SETUP.md`)이 원본입니다.** 여기를 먼저 고치고 웹 버전에 반영하세요.
> 두 곳이 어긋나면 이 파일을 기준으로 봅니다.

---

## 진행 체크리스트

- [ ] 1. Git
- [ ] 2. Python 3.12
- [ ] 3. Node.js
- [ ] 4. Android Studio
- [ ] 5. Flutter
- [ ] 6. DBeaver
- [ ] 7. PostgreSQL
- [ ] 8. Python 라이브러리
- [ ] 9. 저장소 받기
- [ ] 10. 공용 DB 접속 확인

---

# 1단계 · 설치

순서를 지켜주세요. 앞 단계가 있어야 뒤 단계가 됩니다.

## 1. Git

https://git-scm.com/download/win

"Click here to download" 눌러 받고, 설치 창은 계속 **Next** 눌러 기본값 그대로 두시면 됩니다.

## 2. Python 3.12

https://www.python.org/downloads/

> ### ⚠ 여기서 제일 많이 실수합니다
> 설치 첫 화면 **맨 아래 `Add python.exe to PATH` 체크박스를 반드시 체크**하고 Install 을 누르세요.
> 이걸 놓치면 나중에 `python` 명령을 못 찾아서 **처음부터 다시 설치**해야 합니다.

페이지 맨 위의 최신 버전 말고 **3.12** 로 받아주세요. 페이지를 아래로 내리면 버전 목록이 있습니다. 최신 버전은 PyTorch 가 아직 지원하지 않을 수 있습니다.

## 3. Node.js

https://nodejs.org/

왼쪽 **LTS** 버전으로 받고 계속 Next 기본값으로 설치.

## 4. Android Studio

https://developer.android.com/studio

설치 후 처음 실행하면 SDK 다운로드 화면이 뜹니다. **Standard** 선택하고 계속 진행하세요. 용량이 커서 시간이 걸립니다.

## 5. Flutter

**팀 구글드라이브에 올려둔 압축파일**을 쓰세요. 공식 사이트에서 받지 않으셔도 됩니다.

[구글드라이브 공유 폴더](https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW)

### 5-1. 압축 풀기

`C:\src\flutter` 에 풀어주세요. 압축을 풀면 `C:\src\flutter\bin` 폴더가 보여야 정상입니다.

> ### ⚠ 위치를 꼭 지켜주세요
> - `C:\Program Files` 밑에 풀면 **권한 때문에 안 됩니다**
> - 경로에 **한글이나 띄어쓰기가 들어가도 안 됩니다** → 바탕화면 ✗, 내 문서 ✗

### 5-2. PATH 등록

아래 순서 그대로 클릭하시면 됩니다.

1. 윈도우 키 누르고 **`환경 변수`** 라고 검색
2. **시스템 환경 변수 편집** 클릭
3. 오른쪽 아래 **[환경 변수]** 버튼 클릭
4. 아래쪽 **시스템 변수** 목록에서 **`Path`** 를 클릭하고 **[편집]**
5. **[새로 만들기]** 누르고 `C:\src\flutter\bin` 입력
6. **[확인]** 을 창마다 눌러서 전부 닫기

### 5-3. 확인

윈도우 키 → `powershell` 검색해서 실행 → 아래 입력

```
flutter doctor
```

항목이 쭉 나오는데 `[√]` 표시면 정상입니다. `[X]` 나 `[!]` 가 있으면 그 화면을 캡처해서 올려주세요.

> **"flutter 를 찾을 수 없습니다" 라고 나오면** 열려있던 터미널을 **완전히 닫고 새로 여세요.** PATH 는 터미널을 새로 열어야 적용됩니다.

## 6. DBeaver

https://dbeaver.io/download/

**Community Edition - Windows (installer)** 받아서 설치. DB 조회용 프로그램이며 2단계에서 씁니다.

## 7. PostgreSQL

https://www.postgresql.org/download/windows/

"Download the installer" 클릭 → **16 또는 17** 버전.

설치 중 비밀번호 입력 화면이 나오면 아무거나 정하고 **메모만 해두세요.** 우리는 공용 DB 를 쓸 거라 이 비밀번호는 거의 쓸 일이 없습니다. 포트는 기본값 `5432` 그대로 두세요.

> `psql` 명령이 필요해서 설치합니다.

## 8. Python 라이브러리

윈도우 키 → `powershell` 검색해서 실행하고, 아래 한 줄을 통째로 복사해 붙여넣고 엔터.

```
pip install torch lightgbm scikit-learn pandas numpy fastapi uvicorn psycopg2-binary openai
```

> **10분 넘게 멈춘 것처럼 보여도 정상입니다.** `torch` 가 2GB 가 넘어서 오래 걸립니다. 진행 표시가 없어도 끊지 마세요. 마지막에 `Successfully installed` 가 나오면 완료입니다.

---

# 2단계 · 저장소 받기

## 9-1. 폴더 만들기

프로젝트를 둘 폴더를 하나 만드세요. 예: `C:\project`

> 한글과 띄어쓰기가 없는 경로로 만들어주세요.

## 9-2. 그 폴더에서 PowerShell 열기

1. 만든 폴더를 **파일 탐색기**로 엽니다
2. 위쪽 **주소창**(`C:\project` 라고 써있는 칸)을 클릭
3. 글자를 지우고 **`powershell`** 이라고 입력한 뒤 엔터

검은 창(PowerShell)이 **그 폴더 위치에서** 열립니다.

> 이 방법은 윈도우 버전과 상관없이 똑같이 동작합니다.

## 9-3. 저장소 내려받기

아래 한 줄을 복사해서 붙여넣고 엔터. **PowerShell 에서 붙여넣기는 마우스 오른쪽 클릭**입니다.

```
git clone https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn.git
```

`C:\project\lisn` 폴더가 생기면 성공입니다.

## 9-4. 설치 상태 점검

```
cd lisn
```

```
.\tools\check-env.ps1
```

무엇이 설치됐고 무엇이 없는지 표로 나옵니다.

| 표시 | 뜻 |
|---|---|
| `O` | 정상 |
| `X` | 없음 |
| `!` | 명령은 있는데 실행이 안 됨 (대개 설치가 덜 된 경우) |

> **"이 시스템에서 스크립트를 실행할 수 없습니다" 라는 빨간 글씨가 뜨면** 아래를 먼저 입력하고 엔터 친 다음, 위 명령을 다시 실행하세요.
>
> ```
> Set-ExecutionPolicy -Scope Process Bypass
> ```

## 9-5. 이후 최신으로 받는 법

`lisn` 폴더에서 PowerShell 열고

```
git pull
```

---

# 3단계 · 공용 DB 접속

학교에서 받은 **공용 PostgreSQL** 을 씁니다. 각자 로컬에 DB 를 만들 필요는 없습니다.

> ### 🔑 접속 정보는 여기 적지 않습니다
> 우리 저장소는 **공개(public) 저장소**라 누구나 볼 수 있습니다.
> **접속 정보는 단톡방 공지 또는 [Notion 프로젝트 페이지](https://app.notion.com/p/3ab02025254781d18e1ac402a0f59d77)** 를 확인하세요.

## 10-1. DBeaver 로 접속

1. DBeaver 실행
2. 왼쪽 위 **콘센트 모양 아이콘(+)** 클릭 · 또는 메뉴 **[데이터베이스] → [새 데이터베이스 연결]**
3. 목록에서 **PostgreSQL** 선택하고 **[다음]**
4. 단톡방 공지의 접속 정보를 입력
   - **Port 는 기본값 `5432` 가 아닙니다.** 공지에 적힌 포트로 꼭 바꿔주세요
5. 아래쪽 **[Test Connection]** 클릭
   - 드라이버를 받으라는 창이 뜨면 **[Download]** 클릭 (처음 한 번만)
   - **Connected** 가 나오면 성공
6. **[완료]** 클릭

## 10-2. 꼭 지켜주세요

> ### ⚠ `db/schema.sql` 은 실행하지 마세요
> **이응균(PM)이 한 번만 실행합니다.** 공용 DB 라서 각자 실행하면 "테이블이 이미 있다"고 충돌합니다.

> ### ⚠ 접속 정보를 GitHub 에 올리지 마세요
> 공개 저장소라 커밋하는 순간 누구나 볼 수 있습니다.
> 코드에 직접 쓰지 마시고 **`.env` 파일로 빼주세요.** `.env` 는 커밋되지 않게 설정돼 있습니다.

---

# 마무리 · 확인 부탁

세팅이 끝나면 아래 두 가지를 캡처해서 **단톡방에** 올려주세요.

1. `.\tools\check-env.ps1` 실행 결과
2. `flutter doctor` 실행 결과

---

# 막혔을 때

혼자 오래 붙잡고 계시지 마세요. 아래는 자주 나오는 것들이라 바로 해결됩니다.

| 증상 | 원인과 해결 |
|---|---|
| `python 을 찾을 수 없습니다` | 설치할 때 `Add python.exe to PATH` 를 체크 안 한 경우. Python 을 **다시 설치**하면서 체크하세요 |
| `python` 쳤는데 **마이크로소프트 스토어**가 열림 | 실제로는 설치가 안 된 상태입니다. 위 2번으로 다시 설치하세요 |
| `flutter 를 찾을 수 없습니다` | 터미널을 완전히 닫고 새로 열면 대부분 해결됩니다 |
| 스크립트 실행 불가 (빨간 글씨) | `Set-ExecutionPolicy -Scope Process Bypass` 먼저 실행 |
| `pip install` 이 멈춘 것 같음 | `torch` 가 2GB 넘어서 그렇습니다. 끊지 말고 기다리세요 |
| DBeaver 접속 실패 | **Port 번호**를 먼저 확인하세요. 기본값 5432 가 아닙니다 |

---

# 링크 모음

| | |
|---|---|
| GitHub | https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn |
| Notion | https://app.notion.com/p/3ab02025254781d18e1ac402a0f59d77 |
| 구글드라이브 | https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW |
