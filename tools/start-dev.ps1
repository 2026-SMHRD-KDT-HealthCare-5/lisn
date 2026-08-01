# =====================================================================
#  귀기울임(LISN) — 통합 개발 서버 실행
#
#  루트에서 실행:  .\tools\start-dev.ps1
#  준비 상태 확인: .\tools\start-dev.ps1 -Check
# =====================================================================

[CmdletBinding()]
param(
    [ValidateSet('All', 'Backend', 'Ai', 'Admin', 'Flutter')]
    [string]$Service = 'All',
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot 'backend'
$adminPath = Join-Path $repoRoot 'frontend\admin'
$flutterPath = Join-Path $repoRoot 'frontend\app'
$aiPath = Join-Path $repoRoot 'ai\server'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'

function Get-ServiceIssues {
    param([string]$Target)

    $issues = [System.Collections.Generic.List[string]]::new()

    if ($Target -in @('All', 'Backend')) {
        if (-not (Test-Path (Join-Path $backendPath '.env'))) {
            $issues.Add('backend\.env 없음: Copy-Item backend\.env.example backend\.env 실행 후 실제 DB 정보를 입력하세요.')
        }
        if (-not (Test-Path $venvPython)) {
            $issues.Add('.venv 없음: python -m venv .venv 후 .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt 를 실행하세요.')
        }
    }

    # AI 추론 서버는 backend 와 같은 .venv 를 씁니다. 의존성(fastapi·uvicorn·
    # pydantic·asyncpg)이 backend 의 부분집합이라 따로 만들 이유가 없습니다.
    # All 일 때는 위 Backend 검사가 같은 항목을 이미 봤으므로 중복으로 넣지 않습니다.
    if ($Target -eq 'Ai') {
        if (-not (Test-Path $venvPython)) {
            $issues.Add('.venv 없음: python -m venv .venv 후 .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt 를 실행하세요.')
        }
        if (-not (Test-Path (Join-Path $backendPath '.env'))) {
            $issues.Add('backend\.env 없음: AI 서버가 여기서 DATABASE_URL 을 읽습니다.')
        }
    }

    if ($Target -in @('All', 'Admin')) {
        if (-not (Get-Command 'npm.cmd' -ErrorAction SilentlyContinue)) {
            $issues.Add('npm 없음: Node.js LTS를 설치하세요.')
        }
        if (-not (Test-Path (Join-Path $adminPath 'node_modules'))) {
            $issues.Add('관리자 웹 의존성 없음: npm install --prefix frontend\admin 을 실행하세요.')
        }
    }

    if ($Target -in @('All', 'Flutter')) {
        if (-not (Get-Command 'flutter.bat' -ErrorAction SilentlyContinue)) {
            $issues.Add('Flutter 없음: Flutter SDK의 bin 경로를 PATH에 추가하세요.')
        }
        if (-not (Test-Path (Join-Path $flutterPath '.dart_tool\package_config.json'))) {
            $issues.Add('Flutter 의존성 없음: frontend\app에서 flutter pub get을 실행하세요.')
        }
    }

    return $issues
}

function Assert-ServiceReady {
    param([string]$Target)

    $issues = @(Get-ServiceIssues -Target $Target)
    if ($issues.Count -gt 0) {
        Write-Host ''
        Write-Host '실행 준비가 더 필요합니다.' -ForegroundColor Yellow
        foreach ($issue in $issues) {
            Write-Host "  - $issue" -ForegroundColor Yellow
        }
        Write-Host ''
        Write-Host '위 항목을 해결한 뒤 다시 실행하세요.' -ForegroundColor Yellow
        exit 1
    }
}

function Set-WindowTitle {
    param([string]$Title)

    try {
        $Host.UI.RawUI.WindowTitle = $Title
    } catch {
        # 제목 변경을 지원하지 않는 터미널에서는 무시합니다.
    }
}

Assert-ServiceReady -Target $Service

if ($Check) {
    Write-Host "[$Service] 실행 준비 완료" -ForegroundColor Green
    exit 0
}

if ($Service -eq 'All') {
    $shellPath = (Get-Process -Id $PID).Path
    $scriptArgument = "`"$PSCommandPath`""

    foreach ($target in @('Backend', 'Ai', 'Admin', 'Flutter')) {
        Start-Process `
            -FilePath $shellPath `
            -WorkingDirectory $repoRoot `
            -ArgumentList @(
                '-NoExit',
                '-ExecutionPolicy', 'Bypass',
                '-File', $scriptArgument,
                '-Service', $target
            )
    }

    Write-Host ''
    Write-Host '백엔드, AI 추론 서버, 관리자 웹, Flutter 실행 창을 열었습니다.' -ForegroundColor Green
    Write-Host '종료할 때는 각 창에서 Ctrl+C를 누른 뒤 창을 닫으세요.'
    exit 0
}

switch ($Service) {
    'Backend' {
        Set-WindowTitle 'LISN Backend :8000'
        Set-Location $backendPath
        Write-Host 'FastAPI 시작: http://127.0.0.1:8000/docs' -ForegroundColor Cyan
        & $venvPython -m uvicorn app.main:app --reload
    }
    'Ai' {
        Set-WindowTitle 'LISN AI :8001'
        # ai/server 는 .env 를 스스로 읽지 않습니다(pydantic-settings 미사용).
        # 넘겨주지 않으면 기본값 postgres:postgres 로 붙었다가 인증 실패합니다.
        $envFile = Join-Path $backendPath '.env'
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*DATABASE_URL\s*=\s*(.+?)\s*$') {
                $env:DATABASE_URL = $Matches[1].Trim('"').Trim("'")
            }
        }
        if (-not $env:DATABASE_URL) {
            Write-Host 'backend\.env 에 DATABASE_URL 이 없습니다.' -ForegroundColor Yellow
            exit 1
        }
        Set-Location $aiPath
        Write-Host 'AI 추론 서버 시작: http://127.0.0.1:8001/health' -ForegroundColor Cyan
        Write-Host '⚠ 판정은 규칙 기반 임시값입니다 (model_version=rule-placeholder-v0)' -ForegroundColor DarkYellow
        & $venvPython -m uvicorn main:app --reload --port 8001
    }
    'Admin' {
        Set-WindowTitle 'LISN Admin :5173'
        Set-Location $adminPath
        Write-Host '관리자 웹 시작: http://localhost:5173' -ForegroundColor Cyan
        & npm.cmd run dev
    }
    'Flutter' {
        Set-WindowTitle 'LISN Flutter'
        Set-Location $flutterPath
        Write-Host 'Flutter 앱 시작 (연결된 기기 또는 에뮬레이터 필요)' -ForegroundColor Cyan
        & flutter.bat run
    }
}

exit $LASTEXITCODE
