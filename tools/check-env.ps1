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
    Get-ToolInfo 'Python'     'python'  '--version' 'AI 모델링 / FastAPI'        '김건영·윤일준'
    Get-ToolInfo 'pip'        'pip'     '--version' 'Python 패키지'              '김건영·윤일준'
    Get-ToolInfo 'PostgreSQL' 'psql'    '--version' 'DB 서버 (schema.sql 실행)'  '윤일준·이응균'
    Get-ToolInfo 'Node.js'    'node'    '--version' 'React 관리자 대시보드'      '함은선'
    Get-ToolInfo 'npm'        'npm'     '--version' 'Node 패키지'                '함은선'
    Get-ToolInfo 'Flutter'    'flutter' '--version' '사용자 앱'                  '함은선'
    Get-ToolInfo 'Dart'       'dart'    '--version' 'Flutter 런타임'             '함은선'
    Get-ToolInfo 'Docker'     'docker'  '--version' '(선택) 컨테이너 배포'       '-'
    Get-ToolInfo 'GitHub CLI' 'gh'      '--version' '(선택) PR·이슈 관리'        '-'
)

$results | Format-Table -AutoSize -Wrap

# --- Python 라이브러리 (Python이 있을 때만) ---
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host '  Python 라이브러리' -ForegroundColor Cyan
    Write-Host '  ---------------------------------------------------------------'
    $libs = @('torch', 'lightgbm', 'sklearn', 'pandas', 'numpy', 'fastapi', 'psycopg2', 'openai')
    $libResults = @()
    foreach ($lib in $libs) {
        $out = python -c "import $lib, sys; print(getattr($lib,'__version__','설치됨'))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $libResults += [pscustomobject]@{ 라이브러리 = $lib; 상태 = 'O'; 버전 = $out.Trim() }
        } else {
            $libResults += [pscustomobject]@{ 라이브러리 = $lib; 상태 = 'X'; 버전 = '-' }
        }
    }
    $libResults | Format-Table -AutoSize
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
