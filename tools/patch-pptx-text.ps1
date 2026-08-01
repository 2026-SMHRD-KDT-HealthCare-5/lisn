Add-Type -AssemblyName System.IO.Compression.FileSystem

# 저장소 위치를 기준으로 잡는다. 절대경로를 박아 두면 다른 PC·다른 폴더에서 못 돈다
# (실제로 저장소를 C:\LISN 으로 옮겼을 때 여기서 깨졌다).
$f = Join-Path (Split-Path -Parent $PSScriptRoot) 'Documents\화면설계서_귀기울임.pptx'

if (-not (Test-Path $f)) {
    Write-Host "대상 파일이 없습니다: $f" -ForegroundColor Yellow
    exit 1
}

# 슬라이드별 교체 쌍. 정확히 1건 매칭될 때만 적용한다.
$plan = @{
    'slide1.xml' = @(
        # 표지 작성일자 — 셀이 '2026. 07. 2' + '9' 로 쪼개져 있음
        @('<a:t>2026. 07. 2</a:t>', '<a:t>2026. 07. 30</a:t>'),
        @('<a:t>9</a:t>',           '<a:t></a:t>')
    )
    'slide2.xml' = @(
        # 변경이력 v0.5 작성일자 — '2026.07.2' + '8'
        @('<a:t>2026.07.2</a:t>', '<a:t>2026.07.28</a:t>'),
        @('<a:t>8</a:t>',         '<a:t></a:t>')
    )
    'slide10.xml' = @(
        # MAIN_JOIN_03 — 화면설명이 MAIN_JOIN_02 복사본이었음
        @('<a:t> 계정 정보 입력: </a:t>',
          '<a:t> 가입 완료 안내 및 수집 항목: 필수(활동량·수면)와 선택(체성분) 구분 표시</a:t>'),
        @('<a:t>이메일</a:t>',                        '<a:t></a:t>'),
        @('<a:t> 및 비밀번호/비밀번호 확인 입력 </a:t>', '<a:t></a:t>'),

        @('<a:t> 사용자 인적사항: 이름, 생년월일, 성별 입력</a:t>',
          '<a:t> 항목별 동의 체크박스: 필수·선택 항목에 대해 개별 동의를 받음</a:t>'),

        @('<a:t> 중복 확인 버튼: 입력한 </a:t>',
          '<a:t> 연동하기 버튼: Health Connect 권한 요청 창 호출 후 연동 상태 저장</a:t>'),
        @('<a:t>이메일을</a:t>',                    '<a:t></a:t>'),
        @('<a:t> DB와 대조해서 중복하는 </a:t>',      '<a:t></a:t>'),
        @('<a:t>이메일이</a:t>',                    '<a:t></a:t>'),
        @('<a:t> 있는지 확인</a:t>',                 '<a:t></a:t>'),

        @('<a:t> 회원가입 완료 버튼: 정보 유효성 검증 후 홈 화면으로 이동</a:t>',
          '<a:t> 건너뛰기: 연동 없이 홈으로 이동. 이후 설정(MAIN_SETTING_01)에서 연동 가능</a:t>'),

        # 화면이름 / 화면개요 / 유스케이스 ID / 메뉴경로
        @('<a:t>회원가입 </a:t>',    '<a:t>웨어러블 연동 </a:t>'),
        @('<a:t>완료 화면</a:t>',    '<a:t>설정 화면</a:t>'),
        @('<a:t>회원가입 완료와 동시에</a:t>',
          '<a:t>회원가입 완료 후 스마트워치·체성분계 수집 항목에 동의하고 </a:t>'),
        @('<a:t>웨어러블 기기를 연동할 수 있는 페이지</a:t>',
          '<a:t>Health Connect 연동 권한을 설정하는 화면</a:t>'),
        @('<a:t>MLCM_10</a:t>',      '<a:t>MLCM_110</a:t>'),
        @('<a:t>0</a:t>',            '<a:t></a:t>'),
        @('<a:t>로그인/약관동의/회원가입 정보 입력</a:t>',
          '<a:t>로그인/약관동의/회원가입 정보 입력/웨어러블 연동</a:t>')
    )
    # 항목이 하나면 PowerShell 이 배열을 펼쳐버리므로 앞에 쉼표를 붙여 강제한다
    'slide13.xml' = ,@('<a:t>500</a:t>', '<a:t>400</a:t>')
    'slide14.xml' = @(
        # MAIN_LIFELOG_01 — 화면설명이 홈 대시보드 복사본이었음
        @('<a:t> 오늘의 감정: 대표 감정 이모지, 정서 점수 및 긍정/중립/부정 상태 분포</a:t>',
          '<a:t> 조회 기간 선택: 일·주·월 단위 전환 및 최종 동기화 시각 표시</a:t>'),
        @('<a:t> 라이프로그 요약: 수면 시간, 걸음 수, HRV 스트레스 요약 지표</a:t>',
          '<a:t> 활동량 차트: 걸음 수·이동 거리·소모 칼로리 기간별 추이</a:t>'),
        @('<a:t> AI 한줄 요약: LLM 기반 일일 감정 종합 리포트 및 반응 피드백</a:t>',
          '<a:t> 수면 차트: 단계별(깊은수면·얕은수면·REM·각성) 구성과 수면 효율</a:t>'),
        @('<a:t> 추천 콘텐츠: 사용자 컨디션 맞춤형 영상(3-4-1), 음악(3-4-2), 운동(3-4-3)</a:t>',
          '<a:t> 생체 지표 차트: 심박수·심박변이도(HRV) 기간별 추이</a:t>'),
        @('<a:t> 하단 네비게이션 바: [홈], [AI 챗봇], [라이프로그], [설정] 4개 고정 메뉴</a:t>',
          '<a:t> 체성분 기록: 체중·체지방·근육량·기초대사량 측정 이력</a:t>'),
        @('<a:t>500</a:t>', '<a:t>200</a:t>'),
        @('<a:t>나의 라이프로그 히스토리를 볼 수 있는 화면</a:t>',
          '<a:t>수집된 라이프로그를 기간별로 조회하는 화면. 활동량·수면·생체 지표·체성분을 차트로 확인</a:t>'),
        @('<a:t>홈</a:t>', '<a:t>라이프로그</a:t>')
    )
}

# 단독 '-' 런 제거 대상 (slide7 은 원래 없음 -> 그 서식에 맞춘다)
$dashSlides = @('slide8.xml','slide9.xml','slide10.xml','slide11.xml','slide12.xml','slide13.xml','slide14.xml','slide15.xml')
$dashRx = '<a:r>(?:(?!</?a:r>)[\s\S])*?<a:t>-</a:t></a:r>'

$zip = [IO.Compression.ZipFile]::Open($f, 'Update')
try {
    $names = @($plan.Keys) + $dashSlides | Sort-Object -Unique
    foreach ($name in $names) {
        $entry = $zip.Entries | Where-Object { $_.FullName -eq "ppt/slides/$name" }
        if (-not $entry) { Write-Host "없음: $name"; continue }

        $reader = New-Object IO.StreamReader($entry.Open())
        $xml = $reader.ReadToEnd()
        $reader.Close()

        $ok = 0; $skip = 0
        if ($plan.ContainsKey($name)) {
            foreach ($p in $plan[$name]) {
                $c = ([Regex]::Matches($xml, [Regex]::Escape($p[0]))).Count
                if ($c -eq 1) { $xml = $xml.Replace($p[0], $p[1]); $ok++ }
                else {
                    $skip++
                    $s = [string]$p[0]
                    Write-Host ("  [SKIP {0}건] {1} :: {2}" -f $c, $name, $s.Substring(0, [Math]::Min(38, $s.Length)))
                }
            }
        }

        $dashN = 0
        if ($dashSlides -contains $name) {
            $dashN = ([Regex]::Matches($xml, $dashRx)).Count
            $xml = [Regex]::Replace($xml, $dashRx, '')
        }

        $stream = $entry.Open()
        $stream.SetLength(0)
        $writer = New-Object IO.StreamWriter($stream, (New-Object System.Text.UTF8Encoding($false)))
        $writer.Write($xml); $writer.Flush(); $writer.Close()

        "{0,-13} 교체 {1,2}건 / 건너뜀 {2,2}건 / '-' 제거 {3,2}개" -f $name, $ok, $skip, $dashN
    }
}
finally { $zip.Dispose() }
