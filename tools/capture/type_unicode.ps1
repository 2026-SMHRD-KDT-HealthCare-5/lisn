# 에뮬레이터에 한글을 입력합니다 — adb 로는 안 되는 것
#
# 왜 필요한가
#   `adb shell input text` 는 **ASCII 만** 넣습니다. 에뮬레이터에 한글 IME 도
#   없습니다(LatinIME · 음성 입력 둘뿐). 그래서 위기 발화·페르소나 비교처럼
#   한글을 쳐야 하는 컷을 스크립트로 못 찍었습니다.
#
#   외부 IME APK 를 받아 설치하는 것은 하지 않습니다.
#
#   대신 **호스트 키보드로 넣습니다.** 에뮬레이터는 물리 키보드 입력을 게스트로
#   넘기고, Win32 `SendInput` 의 `KEYEVENTF_UNICODE` 는 **임의의 유니코드 문자**를
#   키 이벤트로 만들어 줍니다. 한글 IME 없이 글자를 직접 밀어 넣는 방식입니다.
#
# ⚠ **에뮬레이터 창이 앞으로 나옵니다.** 입력이 그 창으로 가야 하므로 어쩔 수
#   없습니다. 돌리는 동안 다른 창을 만지지 마세요 — 글자가 그쪽으로 갑니다.
#
# ⚠ 앱에서 **입력창을 먼저 눌러 커서를 세워** 두어야 합니다. 이 스크립트는
#   글자만 보내고 어디에 들어갈지는 정하지 않습니다.
#
# 사용:
#   powershell -File tools/capture/type_unicode.ps1 -Text "죽고 싶다는 생각이 들어요"
#   powershell -File tools/capture/type_unicode.ps1 -Text "..." -DelayMs 60 -Enter

param(
    [Parameter(Mandatory = $true)][string]$Text,
    [int]$DelayMs = 45,
    [string]$WindowTitle = "Android Emulator",
    [switch]$Enter
)

$sig = @'
using System;
using System.Runtime.InteropServices;

public static class U {
    [StructLayout(LayoutKind.Sequential)]
    public struct KEYBDINPUT {
        public ushort wVk; public ushort wScan; public uint dwFlags;
        public uint time; public IntPtr dwExtraInfo;
    }
    [StructLayout(LayoutKind.Explicit, Size = 40)]
    public struct INPUT {
        [FieldOffset(0)] public uint type;
        [FieldOffset(8)] public KEYBDINPUT ki;
    }

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint SendInput(uint n, INPUT[] p, int cb);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr h, int c);

    const uint KEYEVENTF_KEYUP    = 0x0002;
    const uint KEYEVENTF_UNICODE  = 0x0004;

    // 유니코드 문자 하나를 누름/뗌 두 이벤트로 보냅니다.
    // ⚠ 서로게이트 페어(이모지 등)는 두 워드를 각각 보내야 하는데,
    //   한글은 BMP 안에 있어 한 워드로 끝납니다.
    public static void Char(char c) {
        INPUT[] inp = new INPUT[2];
        inp[0].type = 1;
        inp[0].ki.wScan = (ushort)c;
        inp[0].ki.dwFlags = KEYEVENTF_UNICODE;
        inp[1] = inp[0];
        inp[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
        SendInput(2, inp, Marshal.SizeOf(typeof(INPUT)));
    }

    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr pid);
    [DllImport("user32.dll")]
    static extern bool AttachThreadInput(uint a, uint b, bool attach);
    [DllImport("kernel32.dll")]
    static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")]
    static extern bool BringWindowToTop(IntPtr h);

    // ⚠ **SetForegroundWindow 는 그냥 부르면 막힙니다.** Windows 는 지금
    //   포그라운드가 아닌 프로세스가 창을 앞으로 끌어오는 것을 거부합니다
    //   (포커스 도둑질 방지). 실제로 아무 일도 안 일어나고 조용히 실패합니다.
    //
    //   표준 우회는 **현재 포그라운드 창의 입력 스레드에 붙었다가 떼는 것**
    //   입니다. 붙어 있는 동안은 같은 입력 큐를 쓰므로 호출이 허용됩니다.
    public static bool Focus(IntPtr h) {
        ShowWindow(h, 9);   // SW_RESTORE — 최소화돼 있으면 되살립니다
        uint me = GetCurrentThreadId();
        uint fg = GetWindowThreadProcessId(GetForegroundWindow(), IntPtr.Zero);
        if (fg != me) AttachThreadInput(fg, me, true);
        BringWindowToTop(h);
        bool ok = SetForegroundWindow(h);
        if (fg != me) AttachThreadInput(fg, me, false);
        return ok;
    }

    public static bool IsForeground(IntPtr h) { return GetForegroundWindow() == h; }
}
'@

Add-Type -TypeDefinition $sig -ErrorAction Stop

$proc = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowTitle*" } | Select-Object -First 1
if (-not $proc) {
    Write-Error "창을 찾지 못했습니다: *$WindowTitle*"
    exit 1
}

[U]::Focus($proc.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 700

# ⚠ **포커스가 실제로 갔는지 확인하고 시작합니다.** 실패한 줄 모르고 글자를
#   보내면 **다른 창에 타이핑됩니다.** 조용히 실패하는 게 제일 나쁩니다.
if (-not [U]::IsForeground($proc.MainWindowHandle)) {
    Write-Error "에뮬레이터 창을 앞으로 못 가져왔습니다. 창을 한 번 클릭한 뒤 다시 돌리세요."
    exit 2
}

foreach ($ch in $Text.ToCharArray()) {
    [U]::Char($ch)
    Start-Sleep -Milliseconds $DelayMs
}

if ($Enter) {
    Start-Sleep -Milliseconds 300
    # 전송은 adb 로 누르는 편이 확실합니다 — Enter 키 처리는 앱마다 다릅니다.
    Write-Output "ENTER_REQUESTED"
}

Write-Output "TYPED:$($Text.Length)"
