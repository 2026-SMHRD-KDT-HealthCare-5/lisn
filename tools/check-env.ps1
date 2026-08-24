# =====================================================================
#  귀기울임(LISN) — 개발 환경 점검
#
#  사용법:  .\tools\check-env.ps1
#  각자 PC에서 실행해 무엇이 설치되어 있는지 표로 확인합니다.
# =====================================================================

$ErrorActionPreference = 'SilentlyContinue'

# PATH 에는 없지만 실제로 찾아낸 도구들. 표가 아니라 아래 안내에서 알려준다.
# ⚠ 원소가 하나인 배열은 펼쳐지므로 담을 때 앞에 쉼표를 붙인다(`, @(...)`).
$script:PathHints = @()

function Get-ToolInfo {
    param([string]$Name, [string]$Command, [string]$VersionArg, [string]$Purpose, [string]$Owner,
          [string]$Expect, [string[]]$FallbackPaths)

    # PATH 에서 먼저 찾고, 없으면 알려진 설치 위치를 훑는다.
    #
    # ⚠ **설치돼 있는데 PATH 에만 없는 것을 'X(없음)' 으로 보고하면 안 된다.**
    #   2026.08.24 에 Flutter·PostgreSQL 이 멀쩡히 깔려 있는데도 X 로 나왔다.
    #   PostgreSQL 은 PATH 에 **디렉터리가 아니라 psql.exe 파일**이 들어가
    #   있던 것이 원인이었다. "없음" 으로 읽고 다시 설치하면 시간만 버린다.
    $exe = $null
    $onPath = $true
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if ($cmd) {
        $exe = $Command
    } else {
        $onPath = $false
        foreach ($p in $FallbackPaths) {
            if ($p -and (Test-Path -PathType Leaf $p)) { $exe = $p; break }
        }
    }

    if (-not $exe) {
        return [pscustomobject]@{
            도구 = $Name; 상태 = 'X'; 버전 = '-'; 용도 = $Purpose; 담당 = $Owner
        }
    }

    $ver = $null
    try {
        $raw = & $exe $VersionArg 2>$null | Select-Object -First 1
        if ($raw) { $ver = ($raw -replace '\s+', ' ').Trim() }
    } catch { }

    # ⚠ 길면 잘라낸다. Dart 는 첫 줄이 96자라 그대로 두면 표의 `용도`·`담당`
    #   열이 화면 밖으로 밀려 아예 안 보인다. 담당자를 못 보면 표의 의미가 없다.
    if ($ver -and $ver.Length -gt 42) { $ver = $ver.Substring(0, 41) + '~' }

    # 실행은 되는데 버전이 안 나오면 정상 설치가 아님.
    # 대표적으로 Windows의 Microsoft Store 스텁(python.exe)이 여기 걸린다.
    if (-not $ver) {
        $note = '(실행 불가 - 미설치)'
        if ($cmd -and $cmd.Source -like '*WindowsApps*') { $note = '(MS Store 스텁 - 실제 미설치)' }
        return [pscustomobject]@{
            도구 = $Name; 상태 = '!'; 버전 = $note; 용도 = $Purpose; 담당 = $Owner
        }
    }

    # 고정 버전과 대조한다.
    #
    # 팀이 버전을 고정해 둔 도구는 어긋나도 대개 **그냥 돌아가기 때문에**
    # 아무도 모른다. Flutter 가 그랬다 — 3.44 로 `pub get` 을 돌리면
    # pubspec.lock 이 조용히 5개 내려가고, 새 SDK 인 팀원이 받으면 도로
    # 올라간다. 실행은 되는데 lock 만 커밋마다 흔들린다.
    $state = 'O'
    $found = ([regex]'\d+(\.\d+)+').Match($ver).Value
    if ($Expect -and $found -and -not ($found -eq $Expect -or $found.StartsWith("$Expect."))) {
        $state = '!'
        $ver = "$ver  <- 기준 $Expect"
    }
    if (-not $onPath) {
        $state = '!'
        $ver = "$ver  <- PATH 에 없음"
        # 찾은 자리는 표 대신 아래 안내에서 알려준다. 표에 넣으면 열이 밀린다.
        $script:PathHints += , @($Name, (Split-Path -Parent $exe))
    }

    return [pscustomobject]@{
        도구 = $Name; 상태 = $state; 버전 = $ver; 용도 = $Purpose; 담당 = $Owner
    }
}

Write-Host ''
Write-Host '  귀기울임(LISN) 개발 환경 점검' -ForegroundColor Cyan
Write-Host '  ---------------------------------------------------------------'
Write-Host ''

# Flutter 는 설치 위치가 PC 마다 다르다. PATH 에 없을 때 훑을 후보들.
# `FLUTTER_BIN` 은 **실행 파일 전체 경로**다(tools/check_docs.py 와 같은 규약).
$flutterDirs = @('C:\flutter\bin', 'C:\src\flutter\bin',
                 (Join-Path $env:LOCALAPPDATA 'flutter\bin'),
                 (Join-Path $env:USERPROFILE 'flutter\bin')) | Where-Object { $_ }
$flutterFall = @($env:FLUTTER_BIN) + @($flutterDirs | ForEach-Object { Join-Path $_ 'flutter.bat' })
$dartFall    = @($env:DART_BIN)    + @($flutterDirs | ForEach-Object { Join-Path $_ 'dart.bat' })

# PostgreSQL 은 버전 폴더가 껴 있어 와일드카드로 찾는다.
$psqlFall = @(Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue |
              ForEach-Object { $_.FullName })

$results = @(
    Get-ToolInfo 'Git'        'git'     '--version' '버전 관리'                  '전원'
    Get-ToolInfo 'Python'     'python'  '--version' '서버·전처리 (3.12 로 고정)'  '김건영·윤일준' -Expect '3.12'
    Get-ToolInfo 'pip'        'pip'     '--version' 'Python 패키지'              '김건영·윤일준'
    Get-ToolInfo 'PostgreSQL' 'psql'    '--version' 'DB 서버 (17 로 고정)'       '윤일준·이응균' -Expect '17' -FallbackPaths $psqlFall
    Get-ToolInfo 'Node.js'    'node'    '--version' 'React 관리자 대시보드'      '함은선'
    Get-ToolInfo 'npm'        'npm'     '--version' 'Node 패키지'                '함은선'
    Get-ToolInfo 'Flutter'    'flutter' '--version' '사용자 앱 (3.47 로 고정)'    '함은선' -Expect '3.47' -FallbackPaths $flutterFall
    Get-ToolInfo 'Dart'       'dart'    '--version' 'Flutter 런타임 (3.13)'      '함은선' -Expect '3.13' -FallbackPaths $dartFall
    Get-ToolInfo 'Docker'     'docker'  '--version' '(선택) 컨테이너 배포'       '-'
    Get-ToolInfo 'GitHub CLI' 'gh'      '--version' '(선택) PR·이슈 관리'        '-'
)

$results | Format-Table -AutoSize -Wrap

# --- Python 라이브러리 ---
#
# 루트 .venv 가 있으면 그쪽을 본다. 서버는 전부 .venv 로 도는데 시스템 python 을
# 검사하면 "다 설치됐다"고 나오고도 서버가 못 뜬다.
#
# ⚠ psycopg2 를 찾지 않는다. 이 프로젝트는 **asyncpg** 를 쓴다.
#   torch·lightgbm 은 모델 학습을 하지 않기로 해서 필수가 아니다(ai/README.md).
$pyExe = Join-Path (Split-Path -Parent $PSScriptRoot) '.venv\Scripts\python.exe'
if (-not (Test-Path $pyExe)) { $pyExe = 'python' }

if ((Test-Path $pyExe) -or (Get-Command python -ErrorAction SilentlyContinue)) {
    $where = if ($pyExe -eq 'python') { '시스템 python' } else { '.venv' }
    Write-Host "  Python 라이브러리 ($where)" -ForegroundColor Cyan
    Write-Host '  ---------------------------------------------------------------'

    # ⚠ 위 표의 Python 행은 **시스템 python** 을 본다. 서버는 전부 .venv 로
    #   도는데, 윈도우에서 시스템 python 은 대개 MS Store 스텁이라 그 행만
    #   보면 정작 서버가 쓰는 인터프리터 버전을 영영 모른다. 3.12 고정이
    #   어긋나도 조용히 지나간다 — 여기서 따로 잰다.
    $pyVer = & $pyExe -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
    if ($pyVer) {
        $pyVer = $pyVer.Trim()
        if ($pyVer.StartsWith('3.12.')) {
            Write-Host "  인터프리터: Python $pyVer" -ForegroundColor DarkGray
        } else {
            Write-Host "  인터프리터: Python $pyVer  <- 기준 3.12 와 다릅니다" -ForegroundColor Yellow
        }
    }

    # ⚠ **backend/requirements.txt 와 맞춰 두세요.** 목록이 뒤처지면 빠진
    #   패키지를 여기서 못 잡습니다. 2026.08.24 에 `firebase-admin` 이
    #   requirements 에는 있는데 venv 에 없었고, 이 목록에도 없어서 조용히
    #   지나갔습니다. `check_docs.py` 가 백엔드를 import 하다 실패하고 나서야
    #   드러났습니다.
    #
    # ⚠ **import 이름이 패키지 이름과 다릅니다.** `pyjwt`→`jwt`,
    #   `firebase-admin`→`firebase_admin`, `pytest-asyncio`→`pytest_asyncio`.
    #   왼쪽은 **import 이름**이어야 합니다.
    $libs = [ordered]@{
        'fastapi'           = '서버 (backend · ai/server)'
        'uvicorn'           = '서버 실행'
        'sqlalchemy'        = '모델 (backend)'
        'asyncpg'           = 'DB 드라이버 - psycopg2 아님'
        'pydantic'          = 'DTO'
        'pydantic_settings' = '설정 로딩'
        'email_validator'   = '이메일 검증'
        'bcrypt'            = '비밀번호 해시'
        'jwt'               = 'JWT (패키지명은 pyjwt)'
        'cryptography'      = '암호화'
        'openai'            = 'LLM (Gemini 도 이 SDK 로 붙음)'
        'firebase_admin'    = 'FCM 발송 - 없으면 check_docs 가 깨집니다'
        'httpx'             = 'HTTP 클라이언트'
        'pytest'            = '테스트'
        'pytest_asyncio'    = '비동기 테스트'
        'pandas'            = '(선택) 전처리 - ai/preprocess'
        'numpy'             = '(선택) 전처리'
        'sklearn'           = '(선택) 전처리 - 개인별 정규화'
    }

    $libResults = @()
    foreach ($lib in $libs.Keys) {
        $out = & $pyExe -c "import $lib; print(getattr($lib,'__version__','설치됨'))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $libResults += [pscustomobject]@{
                라이브러리 = $lib; 상태 = 'O'; 버전 = $out.Trim(); 용도 = $libs[$lib]
            }
        } else {
            $libResults += [pscustomobject]@{
                라이브러리 = $lib; 상태 = 'X'; 버전 = '-'; 용도 = $libs[$lib]
            }
        }
    }
    $libResults | Format-Table -AutoSize -Wrap

    Write-Host '  없으면:  .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt' -ForegroundColor DarkGray
    Write-Host '  (선택) 표시는 전처리 스크립트용입니다 - 서버는 없어도 뜹니다' -ForegroundColor DarkGray
    Write-Host ''
}

# --- 요약 ---
# ⚠ '없음' 과 '손봐야 함' 을 갈라서 보고한다. 버전이 어긋나거나 PATH 에만
#   없는 것을 "설치 필요" 로 뭉뚱그리면, 이미 깔린 것을 또 깔게 된다.
$missing = @($results | Where-Object { $_.상태 -eq 'X' -and $_.담당 -ne '-' } | ForEach-Object { $_.도구 })
$broken  = @($results | Where-Object { $_.상태 -eq '!' -and $_.담당 -ne '-' } | ForEach-Object { $_.도구 })
Write-Host ''
Write-Host '  O = 정상 / ! = 있으나 손봐야 함 (버전 불일치·PATH 누락·실행 불가) / X = 없음' -ForegroundColor DarkGray
Write-Host ''
if ($missing.Count -gt 0) {
    Write-Host ('  설치 필요: ' + ($missing -join ', ')) -ForegroundColor Yellow
}
if ($broken.Count -gt 0) {
    Write-Host ('  손봐야 함: ' + ($broken -join ', ') + '   (위 표의 <- 표시를 보세요)') -ForegroundColor Yellow
}
if ($script:PathHints.Count -gt 0) {
    Write-Host ''
    Write-Host '  아래는 설치돼 있는데 PATH 에만 없습니다. 다시 설치하지 마세요.' -ForegroundColor Yellow
    foreach ($h in $script:PathHints) { Write-Host ("    {0,-11} {1}" -f $h[0], $h[1]) -ForegroundColor DarkGray }
    Write-Host '    PATH 에는 실행 파일이 아니라 위 디렉터리를 넣어야 합니다.' -ForegroundColor DarkGray
}
if ($missing.Count -eq 0 -and $broken.Count -eq 0) {
    Write-Host '  필수 도구가 모두 설치되어 있습니다.' -ForegroundColor Green
}

Write-Host ''
Write-Host '  설치 링크'
Write-Host '    Python      https://www.python.org/downloads/   (Add to PATH 체크 필수)'
Write-Host '    PostgreSQL  https://www.postgresql.org/download/windows/'
Write-Host '    Node.js     https://nodejs.org/'
Write-Host '    Flutter     https://docs.flutter.dev/get-started/install/windows'
Write-Host '    DBeaver     https://dbeaver.io/download/         (DB 클라이언트, 서버 아님)'
Write-Host ''
Write-Host ''

# 마지막 python import 실패가 $LASTEXITCODE 에 남아 실패한 것처럼 보인다.
# 이 스크립트는 게이트가 아니라 보고서다.
exit 0
