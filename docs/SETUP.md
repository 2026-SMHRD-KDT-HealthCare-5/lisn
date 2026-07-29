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

> **버전이 왜 3.12 여야 하나요**
> 최신 버전(3.13 · 3.14)은 **PyTorch 가 아직 지원하지 않습니다.** 그대로 진행하면 8번에서 `torch` 만 조용히 빠지고, **AI 모델을 돌릴 때가 되어서야** 문제를 발견하게 됩니다.

### 먼저 — 아나콘다가 있는지 확인하세요

윈도우 키를 누르고 <kbd>anaconda</kbd> 라고 검색해보세요.

| 검색 결과 | 진행할 방법 |
|---|---|
| **`Anaconda PowerShell Prompt`** 가 보인다 | **방법 1** (훨씬 간단합니다) |
| 아무것도 안 나온다 | **방법 2** |

---

### 방법 1 · 아나콘다가 있는 경우 ★권장

python.org 에서 따로 받을 필요가 **전혀 없습니다.** 가상환경 하나만 만들면 끝입니다.

**① 터미널 열기** — 윈도우 키 → <kbd>Anaconda PowerShell Prompt</kbd> 검색해서 실행

> **일반 PowerShell 이 아니라 이걸 쓰세요.** 일반 PowerShell 에서는 `conda activate` 가 동작하지 않습니다.

**② 환경 만들기**

```
conda create -n lisn python=3.12 -y
```

**③ 환경 활성화**

```
conda activate lisn
```

프롬프트 맨 앞에 **`(lisn)`** 이 붙으면 성공입니다.

```
(lisn) PS C:\Users\사용자명>
```

> ### ⚠ 터미널을 새로 열 때마다 `conda activate lisn` 을 해야 합니다
> 이걸 빠뜨리면 `base` 환경에서 명령이 돌아가서, 설치한 라이브러리를 못 찾습니다.
> **프롬프트 앞에 `(lisn)` 이 있는지 매번 확인하는 습관**을 들이세요.

**④ VS Code 를 쓰신다면 인터프리터도 맞춰주세요**

`Ctrl` + `Shift` + `P` → `Python: Select Interpreter` 입력 → 목록에서 **`lisn`** 선택

> 이걸 안 하면 VS Code 가 다른 파이썬으로 코드를 실행해서 **"터미널에선 되는데 실행하면 안 된다"** 상태가 됩니다.

**왜 이쪽이 나은가**

- 3.12.7 을 찾아 헤맬 필요가 없습니다
- **다른 수업·과제의 파이썬 환경을 건드리지 않습니다**
- 팀원 전원이 같은 명령을 쓰므로 버전이 저절로 통일됩니다
- PATH 등록, Microsoft Store 문제를 겪지 않습니다

---

### 방법 2 · 아나콘다가 없는 경우

https://www.python.org/downloads/

> ### ⚠ 여기서 제일 많이 실수합니다
> 설치 첫 화면 **맨 아래 `Add python.exe to PATH` 체크박스를 반드시 체크**하고 Install 을 누르세요.
> 이걸 놓치면 나중에 `python` 명령을 못 찾아서 **처음부터 다시 설치**해야 합니다.

> ### ⚠ 페이지 맨 위의 노란 버튼을 누르지 마세요
> 그 버튼은 **최신 버전**을 받습니다.
>
> **`Python 3.12.7` 을 받으세요** — 버전까지 정확히 이것입니다.
> 1. 페이지를 아래로 스크롤해서 **`Looking for a specific release?`** 표를 찾습니다
> 2. 목록에서 왼쪽 파란 링크 **`Python 3.12.7`** 클릭 (옆의 Download 버튼 말고 링크 쪽)
> 3. 열린 페이지를 **맨 아래까지** 내려서 `Files` 표를 찾습니다
> 4. **`Windows installer (64-bit)`** 클릭 → `python-3.12.7-amd64.exe`
>
> `Windows embeddable package` 나 `ARM64` 가 아닙니다. **`Windows installer (64-bit)`** 입니다.

> ### 왜 하필 3.12.7 인가요 — 더 최신 3.12 를 고르면 막힙니다
> 목록에는 `3.12.13`(2026.03) 처럼 더 최신 3.12 가 있지만, **이들에는 Windows 설치 파일이 없습니다.** 소스 코드(`tar.gz`)만 올라와 있어서 눌러도 받을 게 없습니다.
>
> Python 은 버전이 `security` 단계에 들어가면 보안 패치를 소스로만 배포합니다. 3.12 는 2024년 10월에 그 단계로 넘어갔고, **직전 릴리스인 3.12.7 이 마지막 Windows 설치 파일**입니다.
> (3.12.13 페이지 원문: "binary installers are no longer provided for it")

---

### 공통 · 버전 확인 (건너뛰지 마세요)

**어디서 확인하나요**

1. 키보드의 **윈도우 키**를 누릅니다 (시작 메뉴가 열립니다)
2. 타이핑합니다 — **방법 1** 은 <kbd>Anaconda PowerShell Prompt</kbd> · **방법 2** 는 <kbd>powershell</kbd>
3. 검색 결과에 뜨는 프로그램을 클릭합니다
4. 창이 열리면 아래를 입력하고 엔터

> **방법 1 이신 분은 `conda activate lisn` 을 먼저 하세요.** 프롬프트에 `(lisn)` 이 붙은 상태여야 합니다.

```
python --version
```

> 폴더 위치는 상관없습니다. 어디서 실행하든 결과는 같습니다.

**`Python 3.12.x` 가 나와야 정상입니다.** (방법 2 는 정확히 `3.12.7`)

### 다른 결과가 나왔다면

| 나온 결과 | 무슨 뜻인가 | 해야 할 일 |
|---|---|---|
| `Python 3.12.x` | 정상 | 다음 단계로 |
| `Python 3.13.x` · `3.14.x` 등 다른 버전 | 방법 1: 환경이 활성화 안 됨 · 방법 2: 잘못 받음 | **①** |
| `Python` 만 뜨고 숫자가 없음 | Microsoft Store 가짜 파일 | **②** |
| Microsoft Store 창이 열림 | Python 이 실제로는 없습니다 | **②** |
| `python 을 찾을 수 없습니다` | PATH 미등록 | **②** |
| `conda 를 찾을 수 없습니다` | 일반 PowerShell 을 여신 겁니다 | **③** |

---

#### ① 3.12 가 아닌 다른 버전이 나올 때

**방법 1(아나콘다)로 하신 경우** — 십중팔구 **환경 활성화를 안 하신 것**입니다.

프롬프트 앞에 `(lisn)` 이 있는지 보세요. 없으면:

```
conda activate lisn
```

`(lisn)` 이 붙었는데도 3.12 가 아니면 환경을 다시 만드세요.

```
conda create -n lisn python=3.12 -y --force
```

**방법 2(python.org)로 하신 경우** — 아래 둘 중 하나로 해결하세요.

- **기존 버전을 지우지 않고 골라 쓰기 (권장)** — 3.12.7 을 추가 설치한 뒤, 앞으로 `python` 대신 `py -3.12` 를 씁니다. 8번 명령도 `py -3.12 -m pip install ...` 로 바뀝니다. 다른 프로그램이 기존 버전을 쓰고 있을 수 있어 이쪽이 안전합니다.
- **기존 버전 제거** — 윈도우 키 → <kbd>앱</kbd> 검색 → **설치된 앱** 에서 `Python 3.13`·`3.14` 를 제거한 뒤 3.12.7 설치. 매번 `py -3.12` 를 붙이는 게 번거로우면 이쪽. 단 다른 프로젝트가 깨질 수 있습니다.

#### ② 버전이 아예 안 나올 때

**Microsoft Store 창이 열리거나 `Python` 만 뜨는 경우**

윈도우에 기본으로 들어있는 **가짜 `python.exe`** 가 잡히는 것입니다. 재설치로는 해결되지 않습니다.

1. 윈도우 키 → <kbd>앱 실행 별칭</kbd> 검색 → **앱 실행 별칭 관리**
2. **`python.exe`** 와 **`python3.exe`** 를 찾아 **끄기** 로 바꿉니다
3. 터미널을 완전히 닫고 새로 연 뒤 다시 확인

> 이 설정을 안 끄면 진짜 Python 을 설치해도 계속 가짜가 먼저 잡힙니다.

**`python 을 찾을 수 없습니다` 만 나오는 경우**

`Add python.exe to PATH` 를 체크하지 않고 설치하신 겁니다. 설치 파일을 다시 실행해 **체크하고 재설치**하는 게 가장 간단합니다.

직접 등록하시려면 7번의 PATH 등록과 같은 방법으로 **아래 두 경로를 모두** 추가하세요. (`<사용자명>` 은 본인 윈도우 계정 폴더 이름)

```
C:\Users\<사용자명>\AppData\Local\Programs\Python\Python312
C:\Users\<사용자명>\AppData\Local\Programs\Python\Python312\Scripts
```

> `Scripts` 까지 넣어야 `pip` 도 동작합니다. 하나만 넣으면 `python` 은 되는데 `pip` 이 안 되는 상태가 됩니다.

#### ③ `conda 를 찾을 수 없습니다`

일반 PowerShell 을 여신 것입니다. **`Anaconda PowerShell Prompt`** 로 다시 여세요.

일반 PowerShell 에서도 쓰고 싶으시면 `Anaconda PowerShell Prompt` 에서 아래를 한 번 실행하고 터미널을 새로 열면 됩니다.

```
conda init powershell
```

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

"Download the installer" 클릭 → **17** 버전을 받으세요. 팀 전원 같은 버전으로 맞춥니다. (아래 PATH 경로가 17 기준입니다)

설치 중 비밀번호 입력 화면이 나오면 아무거나 정하고 **메모만 해두세요.** 우리는 공용 DB 를 쓸 거라 이 비밀번호는 거의 쓸 일이 없습니다. 포트는 기본값 `5432` 그대로 두세요.

> `psql` 명령이 필요해서 설치합니다.

### 설치가 끝나면 `Stack Builder` 창이 뜹니다 → **Cancel**

> ### ⚠ 아무것도 체크하지 말고 취소하세요
> Stack Builder 는 설치 후 자동으로 뜨는 **선택 사항 도구**입니다. 여기 있는 것 중 우리 프로젝트에 필요한 건 하나도 없습니다.
>
> 특히 **`Database Server` 아래의 다른 버전(v14 · v15 · v16 · v18)을 절대 체크하지 마세요.** PostgreSQL 서버가 여러 개 깔려서 포트가 충돌하고, 어느 쪽에 연결됐는지 헷갈려 나중에 문제 원인을 찾기 어려워집니다. 방금 설치한 **17 하나면 충분**합니다.
>
> `psqlODBC` 도 필요 없습니다. Python 은 `psycopg2` 로 접속합니다.
> pgAdmin(GUI 관리 도구)은 본 설치 프로그램에 이미 포함되어 함께 설치됩니다.

### PATH 등록 — 이 단계를 꼭 하세요

> **PostgreSQL 설치 프로그램은 `bin` 폴더를 PATH 에 자동으로 추가하지 않습니다.**
> 그래서 설치를 마쳐도 `psql` 명령이 "찾을 수 없습니다"로 나옵니다. **고장이 아니라 원래 그렇습니다.**
> 직접 등록해야 합니다.

5-2 와 같은 방법입니다.

1. 윈도우 키 누르고 <kbd>환경 변수</kbd> 검색 → **시스템 환경 변수 편집**
2. **[환경 변수]** → 아래쪽 **시스템 변수** 목록에서 <kbd>Path</kbd> → **[편집]**
3. **[새로 만들기]** → `C:\Program Files\PostgreSQL\17\bin` 입력
4. **[확인]** 을 창마다 눌러 전부 닫기
5. **터미널을 완전히 닫고 새로 열기**

> 폴더가 실제로 있는지는 파일 탐색기에서 `C:\Program Files\PostgreSQL` 를 열어보면 확인됩니다.
> 안에 `17` 이 아닌 다른 숫자 폴더가 있다면 다른 버전을 설치하신 것이니, 경로의 숫자를 그것으로 바꾸세요.

### 설치 확인

```
psql --version
```

`psql (PostgreSQL) 17.x` 처럼 나오면 정상입니다.

> 여전히 찾을 수 없다고 나오면 → 터미널을 새로 열었는지, 경로에 오타가 없는지 확인하세요.
> `C:\Program Files\PostgreSQL` 폴더 자체가 없다면 설치가 완료되지 않은 것이니 다시 설치하세요.

## 8. Python 라이브러리

> ### 시작 전 확인
> **방법 1(아나콘다)** — `Anaconda PowerShell Prompt` 를 열고 **`conda activate lisn` 을 먼저** 하세요. 프롬프트에 **`(lisn)`** 이 붙어 있어야 합니다. 안 붙은 채로 설치하면 `base` 환경에 깔려서 나중에 못 찾습니다.
> **방법 2(python.org)** — 윈도우 키 → `powershell` 로 실행하면 됩니다.

아래 한 줄을 통째로 복사해 붙여넣고 엔터.

```
pip install torch lightgbm scikit-learn pandas numpy fastapi uvicorn psycopg2-binary openai
```

> 방법 2 에서 `py -3.12` 를 쓰기로 하신 분은 `py -3.12 -m pip install ...` 로 실행하세요.

> **10분 넘게 멈춘 것처럼 보여도 정상입니다.** `torch` 가 2GB 가 넘어서 오래 걸립니다. 진행 표시가 없어도 끊지 마세요.

### 설치 확인 — `torch` 가 들어갔는지 꼭 보세요

```
python -c "import torch; print(torch.__version__)"
```

버전 번호가 나오면 정상입니다.

> ### ⚠ `ModuleNotFoundError: No module named 'torch'` 가 나오면
> **Python 버전이 3.12 가 아닙니다.** PyTorch 가 지원하지 않는 버전이라 `torch` 만 조용히 빠지고 나머지는 설치됩니다.
> `Successfully installed` 가 떠도 그 목록에 `torch` 가 없으면 안 깔린 겁니다.
>
> 2번으로 돌아가 **Python 3.12** 를 설치한 뒤 이 단계를 다시 실행하세요.
> **AI 모델링 작업 전체가 `torch` 위에서 돌아가므로 넘어가면 안 됩니다.**

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
>
> **아나콘다를 쓰시는 분(방법 1)도 이 단계는 일반 PowerShell 로 하시면 됩니다.** `git clone` 은 파이썬과 무관합니다. 다만 아래 9-4 의 `check-env.ps1` 은 `Anaconda PowerShell Prompt` 에서 `conda activate lisn` 후 실행해야 파이썬 항목이 제대로 잡힙니다.

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
| PostgreSQL 설치 후 `Stack Builder` 창이 뜸 | 아무것도 체크하지 말고 **Cancel**. 특히 다른 버전 서버(v14·v15·v16·v18)를 깔면 포트가 충돌합니다 |
| `psql` 을 찾을 수 없습니다 | **정상입니다.** PostgreSQL 설치 프로그램은 PATH 를 자동 등록하지 않습니다. 7번의 PATH 등록 단계를 하세요 |
| `conda 를 찾을 수 없습니다` | 일반 PowerShell 을 여신 겁니다. **`Anaconda PowerShell Prompt`** 로 여세요 |
| 설치한 라이브러리를 못 찾음 (`ModuleNotFoundError`) | `conda activate lisn` 을 안 하신 겁니다. 프롬프트에 **`(lisn)`** 이 붙어 있는지 확인하세요 |
| VS Code 에서만 실행이 안 됨 | 인터프리터가 다릅니다. `Ctrl+Shift+P` → `Python: Select Interpreter` → `lisn` 선택 |
| `torch` 만 설치가 안 됨 | Python 이 3.12 가 아닙니다. `python --version` 확인 후 3.12 로 다시 설치하세요 |
| 휠 파일명에 `cp313`·`cp314` 가 보임 | Python 3.13·3.14 를 받으신 겁니다. 3.12 여야 `cp312` 로 나옵니다 |
| 3.12 릴리스 페이지에 `.exe` 가 없음 | `3.12.8` 이상을 고르신 겁니다. 이들은 소스 전용이라 설치 파일이 없습니다. **`3.12.7`** 로 가세요 |
| DBeaver 접속 실패 | **Port 번호**를 먼저 확인하세요. 기본값 5432 가 아닙니다 |

---

# 링크 모음

| | |
|---|---|
| GitHub | https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn |
| Notion | https://app.notion.com/p/3ab02025254781d18e1ac402a0f59d77 |
| 구글드라이브 | https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW |
