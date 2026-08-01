# =====================================================================
#  귀기울임(LISN) — 앱의 원하는 화면을 바로 띄우기
#
#  화면설계서 캡처·화면 확인용입니다.
#
#  사용법:
#    .\tools\show-screen.ps1 report      원하는 화면으로
#    .\tools\show-screen.ps1             목록 보기
#    .\tools\show-screen.ps1 report -KeepLogin   현재 로그인 계정 유지
#
#  ⚠ 인증을 우회하는 개발 플래그를 씁니다. 제출·시연 빌드에는 쓰지 마세요.
#    상세는 frontend/app/lib/dev_screens.dart 상단 주석.
# =====================================================================

[CmdletBinding()]
param(
    [string]$Screen,

    # 기본은 데모 계정으로 다시 로그인합니다(DEV_LOGIN=force).
    # 지금 로그인한 계정 그대로 보고 싶을 때만 이 스위치를 주세요.
    [switch]$KeepLogin
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$appPath = Join-Path $repoRoot 'frontend\app'

# 화면 키는 lib/dev_screens.dart 의 devScreens 와 같아야 합니다.
$screens = [ordered]@{
    'login'     = 'MAIN_LOGIN_01     로그인'
    'reset'     = 'MAIN_LOGIN_02     비밀번호 재설정'
    'join'      = 'MAIN_JOIN_01~03   회원가입'
    'home'      = 'MAIN_HOME_01      홈'
    'chat'      = 'MAIN_CHAT_01·02   AI 챗봇'
    'lifelog'   = 'MAIN_LIFELOG_01   라이프로그'
    'setting'   = 'MAIN_SETTING_01·02 설정 (02는 하단으로 스크롤)'
    'report'    = 'MAIN_REPORT_01    정서 리포트'
    'emergency' = 'MAIN_EMERGENCY_01 긴급 상담'
}

function Show-Usage {
    Write-Host ''
    Write-Host '  앱의 원하는 화면을 바로 띄웁니다' -ForegroundColor Cyan
    Write-Host '  ---------------------------------------------------------------'
    foreach ($key in $screens.Keys) {
        Write-Host ('    {0,-10} {1}' -f $key, $screens[$key])
    }
    Write-Host ''
    Write-Host '  예)  .\tools\show-screen.ps1 report' -ForegroundColor DarkGray
    Write-Host ''
}

if (-not $Screen) {
    Show-Usage
    exit 0
}

if (-not $screens.Contains($Screen)) {
    Write-Host ''
    Write-Host "  '$Screen' 은(는) 없는 화면 키입니다." -ForegroundColor Yellow
    Show-Usage
    exit 1
}

# --- 에뮬레이터가 떠 있는지 확인 -------------------------------------
#
# flutter run 은 기기가 없으면 한참 기다리다 실패합니다. 먼저 알려줍니다.
# ⚠ 이미 떠 있는 AVD 를 --launch 로 또 켜면 exit 1 로 죽습니다.
#   그래서 "없을 때만" 켭니다.
$devices = & flutter.bat devices 2>&1 | Out-String
if ($devices -notmatch 'emulator-\d+') {
    Write-Host '  에뮬레이터가 없어 lisn 을 켭니다. 40초~1분 걸립니다...' -ForegroundColor Cyan
    Start-Process -FilePath 'flutter.bat' -ArgumentList @('emulators', '--launch', 'lisn') -NoNewWindow

    $waited = 0
    while ($waited -lt 120) {
        Start-Sleep -Seconds 5
        $waited += 5
        $devices = & flutter.bat devices 2>&1 | Out-String
        if ($devices -match 'emulator-\d+') { break }
        Write-Host "    기다리는 중... ${waited}초" -ForegroundColor DarkGray
    }

    if ($devices -notmatch 'emulator-\d+') {
        Write-Host ''
        Write-Host '  에뮬레이터가 뜨지 않았습니다.' -ForegroundColor Yellow
        Write-Host '  이미 떠 있는데 인식이 안 되면 창을 닫고 다시 실행해보세요.'
        exit 1
    }
    Write-Host '  에뮬레이터 준비 완료' -ForegroundColor Green
}

# --- 실행 -------------------------------------------------------------
$loginMode = if ($KeepLogin) { 'true' } else { 'force' }

Write-Host ''
Write-Host "  $($screens[$Screen])" -ForegroundColor Cyan
if (-not $KeepLogin) {
    Write-Host '  데모 계정으로 다시 로그인합니다 (demo.crisis@lisn-test.example)' -ForegroundColor DarkGray
    Write-Host '  데이터가 안 보이면 백엔드와 db\seed_demo_persona.sql 을 확인하세요.' -ForegroundColor DarkGray
}
Write-Host ''

Set-Location $appPath
& flutter.bat run "--dart-define=DEV_LOGIN=$loginMode" "--dart-define=SCREEN=$Screen"
