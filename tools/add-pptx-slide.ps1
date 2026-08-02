<#
.SYNOPSIS
    PPTX 에 슬라이드를 추가합니다. 기존 슬라이드를 복제하는 방식입니다.

.DESCRIPTION
    PowerPoint 로 다시 저장하지 않으므로 **임베드 폰트가 풀리지 않습니다.**
    발표자료 PPTX 를 PowerPoint 에서 저장했다가 폰트가 0개가 된 적이 있습니다
    (5.5MB -> 0.3MB).

    새로 그리지 않고 **복제**하는 이유:
      - 레이아웃·테마·서식이 그대로 따라옵니다
      - 화면설계서는 15장이 모두 같은 틀(제목 + 화면 이미지 + 콜아웃)이라
        복제 후 글자만 갈아끼우면 됩니다
      - 빈 슬라이드를 만들면 자리표시자 좌표를 손으로 맞춰야 합니다

    추가 후에는 tools\patch-pptx-text.ps1 로 글자를 바꾸세요.

.PARAMETER Path
    대상 PPTX.

.PARAMETER CloneFrom
    복제할 원본 슬라이드. **화면에 보이는 순서**(1부터)입니다.
    파일명(slideN.xml)의 N 이 아닙니다 - 둘은 자주 어긋납니다.

.PARAMETER Count
    몇 장 추가할지. 기본 1.

.PARAMETER InsertAfter
    이 위치 뒤에 넣습니다(1부터). 생략하면 맨 뒤.
    0 을 주면 맨 앞에 들어갑니다.

.PARAMETER WhatIf
    실제로 쓰지 않고 무엇을 할지만 보여줍니다.

.EXAMPLE
    .\tools\add-pptx-slide.ps1 -Path .\Documents\화면설계서_귀기울임.pptx -CloneFrom 15 -Count 6

.NOTES
    ⚠ 노트 슬라이드는 복제하지 않습니다. 노트는 원본 슬라이드로 **역참조**를
      갖고 있어서(notesSlideN.xml.rels -> ../slides/slideN.xml), 그대로 복제하면
      노트 하나를 두 슬라이드가 공유하면서 역참조는 한쪽만 가리키는 상태가
      됩니다. PowerPoint 가 "복구가 필요합니다"를 띄웁니다.

    ⚠ 이미지는 **공유**합니다. 복제본이 원본과 같은 media 파일을 가리킵니다.
      한쪽 이미지를 바꾸려면 새 media 를 추가하고 그 슬라이드의 .rels 만
      고쳐야 합니다. 지금은 화면 캡처를 PowerPoint 에서 직접 갈아끼우는 것이
      더 빠릅니다.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][int]$CloneFrom,
    [int]$Count = 1,
    [int]$InsertAfter = -1
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$NS_R    = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
$NS_P    = 'http://schemas.presentationml.org/2006/main'
$T_SLIDE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide'
$T_NOTES = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide'
$CT_SLIDE = 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'

function Read-Entry {
    param($Zip, [string]$Name)
    $entry = $Zip.GetEntry($Name)
    if ($null -eq $entry) { throw "파트를 찾을 수 없습니다: $Name" }
    $reader = New-Object System.IO.StreamReader($entry.Open(), [System.Text.Encoding]::UTF8)
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Write-Entry {
    param($Zip, [string]$Name, [string]$Content)
    # Update 모드에서 기존 항목을 바꾸려면 지우고 다시 만들어야 합니다.
    $existing = $Zip.GetEntry($Name)
    if ($null -ne $existing) { $existing.Delete() }
    $entry = $Zip.CreateEntry($Name)
    $stream = $entry.Open()
    try {
        # ⚠ BOM 없는 UTF-8 이어야 합니다. BOM 이 붙으면 PowerPoint 가
        #   파트를 못 읽고 "복구가 필요합니다"가 뜹니다.
        $enc = New-Object System.Text.UTF8Encoding($false)
        $bytes = $enc.GetBytes($Content)
        $stream.Write($bytes, 0, $bytes.Length)
    } finally { $stream.Dispose() }
}

if (-not (Test-Path $Path)) { throw "파일이 없습니다: $Path" }
if ($Count -lt 1) { throw "-Count 는 1 이상이어야 합니다" }

$full = (Resolve-Path $Path).Path
# 검증을 통과한 뒤에만 원본을 갈아치웁니다. 중간에 실패해도 원본은 그대로입니다.
#
# ⚠ -WhatIf:$false 가 필요합니다. SupportsShouldProcess 를 켜면 $WhatIfPreference
#   가 안에서 부르는 cmdlet 까지 전파돼, -WhatIf 를 줬을 때 작업본 자체가
#   만들어지지 않고 "파트를 찾을 수 없습니다"로 죽습니다. 이건 임시 파일이라
#   미리보기 대상이 아닙니다.
$work = [System.IO.Path]::GetTempFileName()
Remove-Item $work -Force -WhatIf:$false
$work = "$work.pptx"
Copy-Item $full $work -WhatIf:$false

$added = @()
$zip = [System.IO.Compression.ZipFile]::Open($work, 'Update')
try {
    $presXml  = Read-Entry $zip 'ppt/presentation.xml'
    $presRels = Read-Entry $zip 'ppt/_rels/presentation.xml.rels'
    $types    = Read-Entry $zip '[Content_Types].xml'

    # ---- 표시 순서 -> 슬라이드 파일 --------------------------------------
    $relDoc = [xml]$presRels
    $relMap = @{}
    foreach ($r in $relDoc.Relationships.Relationship) {
        if ($r.Type -eq $T_SLIDE) { $relMap[$r.Id] = $r.Target }
    }

    $sldIdMatches = [regex]::Matches($presXml, '<p:sldId\s+id="(\d+)"\s+r:id="([^"]+)"\s*/>')
    if ($sldIdMatches.Count -eq 0) { throw 'sldIdLst 를 읽지 못했습니다' }

    $order = @()
    foreach ($m in $sldIdMatches) { $order += $m.Groups[2].Value }

    if ($CloneFrom -lt 1 -or $CloneFrom -gt $order.Count) {
        throw "-CloneFrom 은 1..$($order.Count) 범위여야 합니다 (현재 슬라이드 $($order.Count)장)"
    }
    if ($InsertAfter -eq -1) { $InsertAfter = $order.Count }
    if ($InsertAfter -lt 0 -or $InsertAfter -gt $order.Count) {
        throw "-InsertAfter 는 0..$($order.Count) 범위여야 합니다"
    }

    $srcTarget = $relMap[$order[$CloneFrom - 1]]      # 예: slides/slide15.xml
    $srcName   = "ppt/$srcTarget"
    $srcRels   = "ppt/slides/_rels/" + [System.IO.Path]::GetFileName($srcTarget) + ".rels"
    Write-Host "복제 원본: $srcName (표시 순서 $CloneFrom 번째)" -ForegroundColor Cyan

    $srcXml     = Read-Entry $zip $srcName
    $srcRelsXml = Read-Entry $zip $srcRels

    # ---- 다음에 쓸 번호들 ------------------------------------------------
    $maxSlideNo = 0
    foreach ($e in $zip.Entries) {
        if ($e.FullName -match '^ppt/slides/slide(\d+)\.xml$') {
            $n = [int]$Matches[1]
            if ($n -gt $maxSlideNo) { $maxSlideNo = $n }
        }
    }
    $maxRid = 0
    foreach ($r in $relDoc.Relationships.Relationship) {
        if ($r.Id -match '^rId(\d+)$') {
            $n = [int]$Matches[1]
            if ($n -gt $maxRid) { $maxRid = $n }
        }
    }
    $maxSldId = 255
    foreach ($m in $sldIdMatches) {
        $n = [int]$m.Groups[1].Value
        if ($n -gt $maxSldId) { $maxSldId = $n }
    }

    # ---- 노트 관계를 뗀 rels 를 만듭니다 ---------------------------------
    $cloneRels = [regex]::Replace(
        $srcRelsXml,
        '<Relationship[^>]*Type="' + [regex]::Escape($T_NOTES) + '"[^>]*/>',
        ''
    )
    if ($cloneRels -eq $srcRelsXml) {
        Write-Host '  (원본에 노트 슬라이드가 없습니다)' -ForegroundColor DarkGray
    } else {
        Write-Host '  노트 슬라이드 관계를 제외했습니다 (역참조가 원본을 가리킵니다)' -ForegroundColor DarkGray
    }

    # ---- 추가 ------------------------------------------------------------
    $newSldIds = @()
    for ($i = 1; $i -le $Count; $i++) {
        $slideNo = $maxSlideNo + $i
        $rid     = 'rId' + ($maxRid + $i)
        $sldId   = $maxSldId + $i
        $partName = "ppt/slides/slide$slideNo.xml"

        if ($PSCmdlet.ShouldProcess($partName, '슬라이드 추가')) {
            Write-Entry $zip $partName $srcXml
            Write-Entry $zip "ppt/slides/_rels/slide$slideNo.xml.rels" $cloneRels
        }

        # [Content_Types].xml
        $override = '<Override PartName="/' + $partName + '" ContentType="' + $CT_SLIDE + '"/>'
        $types = $types -replace '</Types>', ($override + '</Types>')

        # ppt/_rels/presentation.xml.rels
        $newRel = '<Relationship Id="' + $rid + '" Type="' + $T_SLIDE +
                  '" Target="slides/slide' + $slideNo + '.xml"/>'
        $presRels = $presRels -replace '</Relationships>', ($newRel + '</Relationships>')

        $newSldIds += '<p:sldId id="' + $sldId + '" r:id="' + $rid + '"/>'
        $added += "슬라이드 $slideNo (id=$sldId, $rid)"
    }

    # ---- presentation.xml 의 sldIdLst 에 위치 지정 삽입 -------------------
    if ($InsertAfter -eq 0) {
        $anchor = $sldIdMatches[0].Value
        $presXml = $presXml.Replace($anchor, (($newSldIds -join '') + $anchor))
    } else {
        $anchor = $sldIdMatches[$InsertAfter - 1].Value
        $presXml = $presXml.Replace($anchor, ($anchor + ($newSldIds -join '')))
    }

    if ($PSCmdlet.ShouldProcess($full, '등록 정보 갱신')) {
        Write-Entry $zip 'ppt/presentation.xml' $presXml
        Write-Entry $zip 'ppt/_rels/presentation.xml.rels' $presRels
        Write-Entry $zip '[Content_Types].xml' $types
    }
} finally {
    $zip.Dispose()
}

if ($WhatIfPreference) {
    Remove-Item $work -Force
    Write-Host "`n-WhatIf 라 아무것도 쓰지 않았습니다." -ForegroundColor Yellow
    return
}

# =====================================================================
#  검증 - 통과해야만 원본을 갈아치웁니다
# =====================================================================
Write-Host "`n검증 중..." -ForegroundColor Cyan
$problems = @()
$zip = [System.IO.Compression.ZipFile]::Open($work, 'Read')
try {
    $names = @{}
    foreach ($e in $zip.Entries) { $names[$e.FullName] = $true }

    $presXml  = Read-Entry $zip 'ppt/presentation.xml'
    $presRels = Read-Entry $zip 'ppt/_rels/presentation.xml.rels'
    $types    = Read-Entry $zip '[Content_Types].xml'

    # 1. 모든 XML 파트가 파싱되는가
    foreach ($e in $zip.Entries) {
        if ($e.FullName -like '*.xml' -or $e.FullName -like '*.rels') {
            try { [xml](Read-Entry $zip $e.FullName) | Out-Null }
            catch { $problems += "XML 파싱 실패: $($e.FullName)" }
        }
    }

    # 2. Content_Types 의 Override 가 실제 파트를 가리키는가
    foreach ($m in [regex]::Matches($types, 'PartName="/([^"]+)"')) {
        if (-not $names.ContainsKey($m.Groups[1].Value)) {
            $problems += "Content_Types 가 없는 파트를 가리킵니다: $($m.Groups[1].Value)"
        }
    }

    # 3. 슬라이드 파트마다 Override 가 있는가
    #    ⚠ 빠뜨리면 PowerPoint 가 그 슬라이드를 통째로 무시합니다.
    foreach ($e in $zip.Entries) {
        if ($e.FullName -match '^ppt/slides/slide\d+\.xml$') {
            if ($types -notlike "*PartName=`"/$($e.FullName)`"*") {
                $problems += "Content_Types 에 Override 가 없습니다: $($e.FullName)"
            }
        }
    }

    # 4. sldIdLst 의 r:id 가 전부 해석되는가 + 슬라이드 파일이 있는가
    $relDoc = [xml]$presRels
    $relMap = @{}
    foreach ($r in $relDoc.Relationships.Relationship) { $relMap[$r.Id] = $r.Target }
    $slideCount = 0
    foreach ($m in [regex]::Matches($presXml, '<p:sldId\s+id="(\d+)"\s+r:id="([^"]+)"\s*/>')) {
        $slideCount++
        $rid = $m.Groups[2].Value
        if (-not $relMap.ContainsKey($rid)) {
            $problems += "sldIdLst 의 $rid 가 presentation.xml.rels 에 없습니다"
        } elseif (-not $names.ContainsKey("ppt/" + $relMap[$rid])) {
            $problems += "$rid 이 가리키는 파일이 없습니다: $($relMap[$rid])"
        }
    }

    # 5. sldId 값이 중복되지 않는가 (중복이면 PowerPoint 가 거부합니다)
    $ids = @()
    foreach ($m in [regex]::Matches($presXml, '<p:sldId\s+id="(\d+)"')) { $ids += $m.Groups[1].Value }
    $dupes = $ids | Group-Object | Where-Object { $_.Count -gt 1 }
    foreach ($d in $dupes) { $problems += "sldId 중복: $($d.Name)" }

    # 6. 각 슬라이드의 r:id/r:embed 가 자기 .rels 안에서 해석되는가
    #    ⚠ 여기가 깨지면 이미지가 빨간 X 로 뜹니다.
    foreach ($e in $zip.Entries) {
        if ($e.FullName -notmatch '^ppt/slides/slide\d+\.xml$') { continue }
        $sname = [System.IO.Path]::GetFileName($e.FullName)
        $rpath = "ppt/slides/_rels/$sname.rels"
        if (-not $names.ContainsKey($rpath)) {
            $problems += "관계 파일이 없습니다: $rpath"
            continue
        }
        $sxml = Read-Entry $zip $e.FullName
        $rxml = [xml](Read-Entry $zip $rpath)
        $have = @{}
        foreach ($r in $rxml.Relationships.Relationship) { $have[$r.Id] = $true }
        foreach ($m in [regex]::Matches($sxml, 'r:(?:id|embed|link)="([^"]+)"')) {
            if (-not $have.ContainsKey($m.Groups[1].Value)) {
                $problems += "$sname 의 $($m.Groups[1].Value) 를 .rels 에서 못 찾습니다"
            }
        }
    }

    Write-Host "  슬라이드 $slideCount 장 / 전체 파트 $($zip.Entries.Count) 개"
} finally {
    $zip.Dispose()
}

if ($problems.Count -gt 0) {
    Write-Host "`n검증 실패 - 원본은 그대로 두었습니다." -ForegroundColor Red
    $problems | Select-Object -Unique | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`n실패한 결과물: $work" -ForegroundColor DarkGray
    exit 1
}

Move-Item $work $full -Force
Write-Host "  검증 통과" -ForegroundColor Green
Write-Host "`n추가했습니다:" -ForegroundColor Green
$added | ForEach-Object { Write-Host "  $_" }
Write-Host @"

다음으로 할 일
  1. PowerPoint 로 열어 슬라이드가 제대로 붙었는지 확인
  2. tools\patch-pptx-text.ps1 로 제목·콜아웃 글자 교체
  3. 화면 캡처 이미지는 PowerPoint 에서 직접 교체
     (복제본은 원본과 같은 이미지를 공유합니다)
"@ -ForegroundColor DarkGray
