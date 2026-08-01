# =====================================================================
#  귀기울임(LISN) — 개발 환경 점검
#
#  사용법:  .\tools\check-env.ps1
#  각자 PC에서 실행해 무엇이 설치되어 있는지 표로 확인합니다.
# =====================================================================

$ErrorActionPreference = 'SilentlyContinue'

function Get-ToolInfo {
    param([string]$Name, [string]$Command, [string]$VersionArg, [string]$Purpose, [string]$Owner)

    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        return [pscustomobject]@{
            도구 = $Name; 상태 = 'X'; 버전 = '-'; 용도 = $Purpose; 담당 = $Owner
        }
    }

    $ver = $null
    try {
        $raw = & $Command $VersionArg 2>$null | Select-Object -First 1
        if ($raw) { $ver = ($raw -replace '\s+', ' ').Trim() }
    } catch { }

    # 실행은 되는데 버전이 안 나오면 정상 설치가 아님.
    # 대표적으로 Windows의 Microsoft Store 스텁(python.exe)이 여기 걸린다.
    if (-not $ver) {
        $note = '(실행 불가 - 미설치)'
        if ($cmd.Source -like '*WindowsApps*') { $note = '(MS Store 스텁 - 실제 미설치)' }
        return [pscustomobject]@{
            도구 = $Name; 상태 = '!'; 버전 = $note; 용도 = $Purpose; 담당 = $Owner
        }
    }

    return [pscustomobject]@{
        도구 = $Name; 상태 = 'O'; 버전 = $ver; 용도 = $Purpose; 담당 = $Owner
    }
}

Write-Host ''
Write-Host '  귀기울임(LISN) 개발 환경 점검' -ForegroundColor Cyan
Write-Host '  ---------------------------------------------------------------'
Write-Host ''

$results = @(
    Get-ToolInfo 'Git'        'git'     '--version' '버전 관리'                  '전원'
    Get-ToolInfo 'Python'     'python'  '--version' '서버·전처리 (3.12 로 고정)'  '김건영·윤일준'
    Get-ToolInfo 'pip'        'pip'     '--version' 'Python 패키지'              '김건영·윤일준'
    Get-ToolInfo 'PostgreSQL' 'psql'    '--version' 'DB 서버 (17 로 고정)'       '윤일준·이응균'
    Get-ToolInfo 'Node.js'    'node'    '--version' 'React 관리자 대시보드'      '함은선'
    Get-ToolInfo 'npm'        'npm'     '--version' 'Node 패키지'                '함은선'
    Get-ToolInfo 'Flutter'    'flutter' '--version' '사용자 앱'                  '함은선'
    Get-ToolInfo 'Dart'       'dart'    '--version' 'Flutter 런타임'             '함은선'
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

    $libs = [ordered]@{
        'fastapi'    = '서버 (backend · ai/server)'
        'uvicorn'    = '서버 실행'
        'sqlalchemy' = '모델 (backend)'
        'asyncpg'    = 'DB 드라이버 - psycopg2 아님'
        'pydantic'   = 'DTO'
        'openai'     = 'LLM (Gemini 도 이 SDK 로 붙음)'
        'pytest'     = '테스트'
        'pandas'     = '(선택) 전처리 - ai/preprocess'
        'numpy'      = '(선택) 전처리'
        'sklearn'    = '(선택) 전처리 - 개인별 정규화'
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
$missing = @($results | Where-Object { $_.상태 -ne 'O' -and $_.담당 -ne '-' } | ForEach-Object { $_.도구 })
Write-Host ''
Write-Host '  O = 정상 / ! = 명령은 있으나 실행 불가 / X = 없음' -ForegroundColor DarkGray
Write-Host ''
if ($missing.Count -gt 0) {
    Write-Host ('  설치 필요: ' + ($missing -join ', ')) -ForegroundColor Yellow
} else {
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
