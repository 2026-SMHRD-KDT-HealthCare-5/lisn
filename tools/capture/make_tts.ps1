# 시연영상 내레이션을 만듭니다 — Windows 내장 한국어 음성
#
# 왜 WinRT 인가
#   `System.Speech` 로도 되지만 그건 **SAPI5 Desktop 음성**을 씁니다.
#   WinRT(`Windows.Media.SpeechSynthesis`)는 같은 이름의 **OneCore 음성**을
#   쓰는데 억양이 덜 기계적입니다. 둘 다 「Microsoft Heami」로 보이지만
#   실제 엔진이 다릅니다.
#
# ⚠ **네트워크를 쓰지 않습니다.** 발표장 인터넷이 끊겨도 다시 만들 수 있습니다.
#   대신 온라인 신경망 음성(Edge/Azure)만큼 자연스럽지는 않습니다. 더 좋은
#   음성이 필요하면 **사람이 직접 녹음**하는 편이 낫습니다 — 정신건강 서비스
#   소개라 목소리의 온도가 내용의 일부입니다.
#
# 사용:
#   powershell -ExecutionPolicy Bypass -File tools/capture/make_tts.ps1
#   → tts/01.wav ... 각 구간별 파일

param(
    [string]$OutDir = "$PSScriptRoot\..\..\..\tts",
    [int]$Rate = 0   # -10 ~ 10. 0 이 기본
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# ---------------------------------------------------------------------------
#  WinRT 비동기 호출을 PowerShell 5.1 에서 기다리는 도우미
#
#  ⚠ PS 5.1 에는 await 가 없어서, `AsTask` 제네릭 메서드를 리플렉션으로
#    찾아 직접 부릅니다. 이게 없으면 IAsyncOperation 이 그대로 반환돼
#    스트림을 못 읽습니다.
# ---------------------------------------------------------------------------
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($op, $type) {
    $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
    $t.Wait(-1) | Out-Null
    $t.Result
}

[Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null

$syn = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$ko = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
      Where-Object { $_.Language -like 'ko*' } | Select-Object -First 1
if (-not $ko) { throw "한국어 음성이 없습니다. 설정 > 시간 및 언어 > 음성 에서 한국어 음성을 추가하세요." }
$syn.Voice = $ko

function Say([string]$name, [string]$text) {
    # SSML 로 속도를 조절합니다. 평문으로 보내면 기본 속도 고정입니다.
    $pct = if ($Rate -eq 0) { "default" } else { "{0:+0;-0}%" -f ($Rate * 8) }
    $ssml = @"
<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='ko-KR'>
<prosody rate='$pct'>$text</prosody>
</speak>
"@
    $stream = Await $syn.SynthesizeSsmlToStreamAsync($ssml) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $size = $stream.Size
    $rd = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
    Await $rd.LoadAsync($size) ([uint32]) | Out-Null
    $bytes = New-Object byte[] $size
    $rd.ReadBytes($bytes)
    $path = Join-Path $OutDir "$name.wav"
    [IO.File]::WriteAllBytes($path, $bytes)
    $sec = [math]::Round((Get-Item $path).Length / 32000.0, 1)   # 16kHz 16bit mono 근사
    "  {0,-6} {1,5}s  {2}" -f $name, $sec, $text.Substring(0, [Math]::Min(30, $text.Length))
}

# ---------------------------------------------------------------------------
#  구간별 내레이션
#
#  ⚠ **길이를 구간에 맞춰 썼습니다.** 넘치면 잘리는 게 아니라 다음 구간으로
#    밀려 화면과 어긋납니다. 문장을 고치면 길이를 다시 재세요.
#  ⚠ 숫자는 **읽는 대로** 적습니다("3초"가 아니라 "삼 초"). 안 그러면
#    음성이 「삼십초」처럼 붙여 읽는 일이 있습니다.
# ---------------------------------------------------------------------------
"내레이션 생성 (음성: $($ko.DisplayName))"

Say "00" "귀기울임. 먼저 말을 거는 정서 케어입니다."

Say "01" ("사용자는 앱을 열지 않았습니다. 수면이 닷새째 무너진 것을, 시스템이 먼저 알아챕니다. " +
          "알림을 누르면 첫 마디가 이미 준비되어 있습니다. " +
          "무엇을 보고 말을 걸었는지도 함께 보여줍니다. 감시가 아니라, 관심으로 읽히도록.")

Say "02" ("성격은 둘 중에 고릅니다. 따스한 공감형과, 현실적인 조언형. " +
          "서버는 위기 판정과 응답 생성을 동시에 돌립니다. 순서대로 하면 삼 초를 넘기기 때문입니다.")

Say "02b" "위기가 확인되면 챗봇 답변을 버립니다. 위로가, 위험을 덮지 않게."

Say "03" ("수면과 활동량, 심박을 모읍니다. 개인 기준선에서 얼마나 벗어났는지를 봅니다. " +
          "데이터가 사흘치에 못 미치면 정상이라고 말하지 않습니다. 모르는 것과, 괜찮은 것은 다릅니다.")

Say "04" ("관리자는 위험도 분포를 한 화면에서 봅니다. 위험한 사람이 위로 옵니다. " +
          "채팅에서 감지한 위기도 여기 기록됩니다. 미평가 인원은, 정상으로 세지 않습니다.")

Say "99" "귀기울임. 감지한 것을, 사람에게 닿게 합니다."

"완료 → $OutDir"
